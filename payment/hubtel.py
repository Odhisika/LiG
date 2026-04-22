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

    Initiation endpoint : https://payproxyapi.hubtel.com/items/initiate
    Status check endpoint: https://api-txnstatus.hubtel.com/transactions/{TransactionId}/status
                           ?clientReference={clientReference}
    """

    INITIATE_URL = "https://payproxyapi.hubtel.com/items/initiate"
    STATUS_BASE_URL = "https://api-txnstatus.hubtel.com/transactions"

    def __init__(self):
        self.client_id = getattr(settings, 'HUBTEL_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'HUBTEL_CLIENT_SECRET', '')
        self.merchant_account = getattr(settings, 'HUBTEL_MERCHANT_ACCOUNT_NUMBER', '')

        if not self.client_id or not self.client_secret:
            raise HubtelException(
                "Hubtel credentials (HUBTEL_CLIENT_ID / HUBTEL_CLIENT_SECRET) are not configured."
            )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    def _get_auth_header(self):
        """Generate Basic Auth header: base64(clientId:clientSecret)"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Initiate checkout
    # ------------------------------------------------------------------
    def initialize_transaction(
        self,
        amount,
        description,
        customer_email,
        customer_name,
        reference,
        callback_url=None,
        return_url=None,
        cancellation_url=None,
        **kwargs,
    ):
        """
        Initiate a Hubtel Online Checkout payment.

        Args:
            amount (float)          : Amount in GHS
            description (str)       : Short description
            customer_email (str)    : Customer email
            customer_name (str)     : Customer full name
            reference (str)         : Your unique ref (clientReference)
            callback_url (str)      : Hubtel POSTs the result here (server-to-server)
            return_url (str)        : Browser redirect after payment
            cancellation_url (str)  : Browser redirect on cancel

        Returns:
            tuple: (success: bool, data: dict)
        """
        url = self.INITIATE_URL

        payload = {
            "merchantAccountNumber": self.merchant_account,
            "description": description,
            "clientReference": reference,
            "callbackUrl": callback_url or "",
            "returnUrl": return_url or callback_url or "",
            "cancellationUrl": cancellation_url or return_url or callback_url or "",
            "totalAmount": float(amount),
            "customerName": customer_name,
            "customerEmail": customer_email,
            "customerMsisdn": "",
        }

        logger.info(f"Hubtel initiate → {url} | ref={reference} | amount={amount}")

        try:
            response = requests.post(
                url,
                headers=self._get_auth_header(),
                json=payload,
                timeout=30,
            )

            logger.info(f"Hubtel initiate response [{response.status_code}]: {response.text[:500]}")

            if response.status_code == 401:
                logger.error("Hubtel 401 — check API credentials in dashboard.")
                return False, {"message": "Hubtel authentication failed (401). API keys invalid."}

            if response.status_code == 403:
                logger.error("Hubtel 403 — account not enabled for Online Checkout.")
                return False, {"message": "Hubtel rejected request (403). Contact Hubtel support."}

            if not response.text.strip():
                logger.error(f"Hubtel returned empty body [{response.status_code}]")
                return False, {"message": f"Hubtel returned empty response (HTTP {response.status_code})."}

            result = response.json()

            status_ok = (
                result.get("status", "").lower() in ("success", "successfull")
                or str(result.get("ResponseCode", "")) == "0000"
                or response.status_code == 200
            )

            if status_ok and result.get("data"):
                data = result["data"]
                checkout_url = data.get("checkoutUrl") or data.get("CheckoutUrl", "")

                # Extract Hubtel's own transaction/checkout ID — needed for status checks
                hubtel_id = (
                    data.get("checkoutId") or
                    data.get("CheckoutId") or
                    data.get("transactionId") or
                    data.get("TransactionId") or
                    data.get("salesId") or
                    data.get("SalesId") or
                    data.get("clientReference") or
                    reference
                )

                if not checkout_url:
                    logger.error(f"Hubtel returned no checkoutUrl: {result}")
                    return False, {"message": "No checkout URL returned by Hubtel."}

                logger.info(f"Hubtel checkout URL: {checkout_url} | hubtel_id: {hubtel_id}")
                return True, {
                    "checkout_url": checkout_url,
                    "token": hubtel_id,
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

    # ------------------------------------------------------------------
    # Verify transaction via api-txnstatus.hubtel.com
    # ------------------------------------------------------------------
    def verify_transaction(self, reference, transaction_id=None):
        """
        Check the status of a Hubtel transaction.

        Uses:
          GET https://api-txnstatus.hubtel.com/transactions/{transaction_id}/status
              ?clientReference={reference}

        If no transaction_id is provided, falls back to clientReference-only lookup.

        Args:
            reference (str)      : The clientReference (our internal ref / PAY_xxx)
            transaction_id (str) : Hubtel's TransactionId received in the callback

        Returns:
            tuple: (success: bool, data: dict | None)
        """
        if transaction_id:
            url    = f"{self.STATUS_BASE_URL}/{transaction_id}/status"
            params = {"clientReference": reference}
        else:
            # No TransactionId yet — query by clientReference only.
            # Some Hubtel environments support this; log clearly if it fails.
            url    = f"{self.STATUS_BASE_URL}/0/status"
            params = {"clientReference": reference}
            logger.warning(
                f"Hubtel verify: no TransactionId for ref={reference}. "
                "Attempting clientReference-only lookup. "
                "Ensure hubtel_webhook is properly receiving Hubtel POSTs."
            )

        logger.info(f"Hubtel verify → {url} | params={params}")

        try:
            response = requests.get(
                url,
                headers=self._get_auth_header(),
                params=params,
                timeout=30,
            )

            logger.info(f"Hubtel verify response [{response.status_code}]: {response.text[:600]}")

            if response.status_code == 401:
                logger.error("Hubtel status check: 401 Unauthorized")
                return False, {"message": "Hubtel authentication failed on status check."}

            if not response.text.strip():
                logger.error(f"Hubtel status: empty body [{response.status_code}]")
                return False, None

            result = response.json()

            # Hubtel status API wraps data inside a "data" key
            data = result.get("data") or result

            tx_status = (
                data.get("status")
                or data.get("Status")
                or data.get("TransactionStatus")
                or ""
            ).lower()

            logger.info(f"Hubtel tx status for ref={reference}: '{tx_status}'")

            if tx_status in ("success", "completed", "approved", "successfull"):
                return True, {
                    "status": "success",
                    "amount": float(
                        data.get("amount") or data.get("Amount") or 0
                    ),
                    "channel": data.get("paymentType") or data.get("channel") or "mobile_money",
                    "customer_name": data.get("customerName") or data.get("CustomerName") or "",
                    "customer_email": data.get("customerEmail") or data.get("CustomerEmail") or "",
                    "transaction_id": (
                        data.get("transactionId")
                        or data.get("TransactionId")
                        or transaction_id
                        or reference
                    ),
                    "reference": reference,
                    "currency": "GHS",
                    "paid_at": data.get("paidAt") or data.get("PaidAt") or "",
                }
            elif tx_status in ("pending", "initiated", "processing"):
                return False, {"status": "pending", "message": "Payment is still pending."}
            else:
                return False, {
                    "status": tx_status or "unknown",
                    "message": f"Payment status: {tx_status or 'unknown'}.",
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel verify request failed for ref={reference}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error verifying Hubtel payment ref={reference}: {str(e)}")
            return False, None
