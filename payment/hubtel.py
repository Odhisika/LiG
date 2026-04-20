# payment/hubtel.py
import requests
import base64
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class HubtelException(Exception):
    """Custom exception for Hubtel errors"""
    pass


class Hubtel:
    """
    Hubtel Online Checkout integration.
    Uses Basic Auth (ClientID:ClientSecret) directly — no OAuth token needed.
    Endpoint: https://payproxyapi.hubtel.com/items/initiate
    """

    BASE_URL = "https://payproxyapi.hubtel.com"

    def __init__(self):
        self.client_id = getattr(settings, 'HUBTEL_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'HUBTEL_CLIENT_SECRET', '')
        self.merchant_account = getattr(settings, 'HUBTEL_MERCHANT_ACCOUNT_NUMBER', '')

        if not self.client_id or not self.client_secret:
            raise HubtelException("Hubtel credentials (HUBTEL_CLIENT_ID / HUBTEL_CLIENT_SECRET) are not configured.")

    def _get_auth_header(self):
        """Generate Basic Auth header: base64(clientId:clientSecret)"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(
        self,
        amount,
        description,
        customer_email,
        customer_name,
        reference,
        callback_url=None,
        cancellation_url=None,
        **kwargs,
    ):
        """
        Initiate a Hubtel Online Checkout payment.

        Args:
            amount (float): Amount in GHS (e.g. 10.00)
            description (str): Short description of the purchase
            customer_email (str): Customer email address
            customer_name (str): Customer full name
            reference (str): Your unique invoice / order ID
            callback_url (str): URL Hubtel will POST the result to
            cancellation_url (str): URL to redirect when customer cancels

        Returns:
            tuple: (success: bool, data: dict)
        """
        url = f"{self.BASE_URL}/items/initiate"

        payload = {
            "merchantAccountNumber": self.merchant_account,
            "description": description,
            "clientReference": reference,
            "callbackUrl": callback_url or "",
            "returnUrl": callback_url or "",
            "cancellationUrl": cancellation_url or callback_url or "",
            "totalAmount": float(amount),
            "customerName": customer_name,
            "customerEmail": customer_email,
            "customerMsisdn": "",           # Optional phone — leave blank unless you have it
        }

        logger.info(f"Hubtel initiate request → {url} | ref={reference} | amount={amount}")

        try:
            response = requests.post(
                url,
                headers=self._get_auth_header(),
                json=payload,
                timeout=30,
            )

            # Log raw response for easier debugging
            logger.info(f"Hubtel response [{response.status_code}]: {response.text[:500]}")

            # Handle authentication failure (empty body)
            if response.status_code == 401:
                logger.error("Hubtel 401 Unauthorized — check HUBTEL_CLIENT_ID and HUBTEL_CLIENT_SECRET in your Hubtel merchant dashboard.")
                return False, {"message": "Hubtel authentication failed (401). Your API keys are invalid or not activated for Online Checkout."}

            if response.status_code == 403:
                logger.error("Hubtel 403 Forbidden — your account may not be enabled for Online Checkout.")
                return False, {"message": "Hubtel rejected the request (403). Contact Hubtel support to enable Online Checkout on your account."}

            if not response.text.strip():
                logger.error(f"Hubtel returned empty body with status {response.status_code}")
                return False, {"message": f"Hubtel returned an empty response (HTTP {response.status_code})."}

            result = response.json()

            # Hubtel returns status 200 with a "ResponseCode" field
            # Success codes: "0000" or status "Success"
            status_ok = (
                result.get("status", "").lower() in ("success", "successfull")
                or str(result.get("ResponseCode", "")) == "0000"
                or response.status_code == 200
            )

            if status_ok and result.get("data"):
                data = result["data"]
                checkout_url = data.get("checkoutUrl") or data.get("CheckoutUrl", "")
                token = data.get("clientReference") or reference

                if not checkout_url:
                    logger.error(f"Hubtel returned no checkoutUrl: {result}")
                    return False, {"message": "No checkout URL returned by Hubtel."}

                logger.info(f"Hubtel checkout URL: {checkout_url}")
                return True, {
                    "checkout_url": checkout_url,
                    "token": token,
                    "reference": reference,
                }
            else:
                message = (
                    result.get("message")
                    or result.get("Message")
                    or result.get("ResponseMessage")
                    or "Hubtel initialization failed"
                )
                logger.error(f"Hubtel init failed: {result}")
                return False, {"message": message}

        except requests.exceptions.ConnectionError:
            logger.error("Hubtel: Could not connect to payproxyapi.hubtel.com")
            return False, {"message": "Could not connect to Hubtel. Check your internet connection."}
        except requests.exceptions.Timeout:
            logger.error("Hubtel: Request timed out")
            return False, {"message": "Hubtel request timed out. Please try again."}
        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel API request failed: {str(e)}")
            return False, {"message": f"Network error: {str(e)}"}
        except ValueError as e:
            logger.error(f"Hubtel: Failed to parse JSON response: {str(e)}")
            return False, {"message": "Invalid response from Hubtel."}
        except Exception as e:
            logger.error(f"Unexpected Hubtel error: {str(e)}")
            return False, {"message": "An unexpected error occurred with Hubtel."}

    def verify_transaction(self, reference):
        """
        Check the status of a Hubtel transaction by clientReference.

        Args:
            reference (str): The clientReference used when initiating

        Returns:
            tuple: (success: bool, data: dict or None)
        """
        url = f"{self.BASE_URL}/items/status/{reference}"

        logger.info(f"Hubtel verify → {url}")

        try:
            response = requests.get(
                url,
                headers=self._get_auth_header(),
                timeout=30,
            )

            logger.info(f"Hubtel verify response [{response.status_code}]: {response.text[:500]}")

            result = response.json()

            if result.get("status", "").lower() in ("success", "successfull") or response.status_code == 200:
                data = result.get("data", {})
                tx_status = (
                    data.get("status", "")
                    or data.get("TransactionStatus", "")
                ).lower()

                if tx_status in ("success", "completed", "approved", "successfull"):
                    return True, {
                        "status": "success",
                        "amount": float(data.get("amount", data.get("Amount", 0))),
                        "channel": data.get("paymentType", "mobile_money"),
                        "customer_name": data.get("customerName", ""),
                        "customer_email": data.get("customerEmail", ""),
                        "transaction_id": data.get("transactionId", reference),
                        "reference": reference,
                        "currency": "GHS",
                        "paid_at": data.get("paidAt", ""),
                    }
                elif tx_status in ("pending", "initiated", "processing"):
                    return False, {"status": "pending", "message": "Payment is still pending."}
                else:
                    return False, {"status": tx_status, "message": f"Payment {tx_status}."}
            else:
                return False, result

        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel verify request failed for {reference}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error verifying Hubtel payment {reference}: {str(e)}")
            return False, None
