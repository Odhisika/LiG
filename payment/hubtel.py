# payment/hubtel.py
import requests
import base64
import json
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HubtelException(Exception):
    """Custom exception for Hubtel errors"""
    pass


class Hubtel:
    base_url = "https://api.hubtel.com"
    
    def __init__(self):
        self.client_id = settings.HUBTEL_CLIENT_ID
        self.client_secret = settings.HUBTEL_CLIENT_SECRET
        self.account_number = getattr(settings, 'HUBTEL_ACCOUNT_NUMBER', '')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Hubtel credentials not configured")
        
        self._access_token = None
        self._token_expiry = None

    def _get_auth_header(self):
        """Generate Basic Auth header for Hubtel API"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_bearer_headers(self):
        """Get headers with Bearer token"""
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_access_token(self):
        """Get or refresh Hubtel OAuth access token"""
        from datetime import datetime, timedelta
        
        if self._access_token and self._token_expiry:
            if datetime.now() < self._token_expiry:
                return self._access_token
        
        url = f"{self.base_url}/v2/oauth2/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(
                url, 
                headers={"Authorization": self._get_auth_header()},
                data=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            self._access_token = result.get('access_token')
            expires_in = result.get('expires_in', 3600)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel token request failed: {str(e)}")
            raise HubtelException("Failed to authenticate with Hubtel")
        except Exception as e:
            logger.error(f"Unexpected error getting Hubtel token: {str(e)}")
            raise HubtelException("Authentication error")

    def initialize_transaction(self, amount, description, customer_email, customer_name, reference, callback_url=None, mobile_money=False, channel='card'):
        """
        Initialize a Hubtel payment transaction
        
        Args:
            amount (float): Amount in GHS
            description (str): Payment description
            customer_email (str): Customer email
            customer_name (str): Customer name
            reference (str): Unique transaction reference
            callback_url (str, optional): URL to redirect after payment
            mobile_money (bool): Use mobile money instead of card
            channel (str): Payment channel (momo, card, all)
            
        Returns:
            tuple: (success: bool, data: dict)
        """
        url = f"{self.base_url}/v2/pos/onlinecheckout/mobile/initiate"
        
        # Hubtel uses amount in Ghana Cedis (not pesewas)
        data = {
            "description": description,
            "amount": float(amount),
            "customerEmail": customer_email,
            "customerName": customer_name,
            "primaryCallbackUrl": callback_url,
            "secondaryCallbackUrl": callback_url,
            "reference": reference,
            "paymentMethod": "mobile_money" if mobile_money else "card",
            "merchantAccountNumber": self.account_number,
        }
        
        # Add mobile money details if using momo
        if mobile_money:
            data["paymentMethod"] = "mobile_money"
            data["channels"] = ["momo"]
        
        try:
            response = requests.post(
                url,
                headers=self._get_bearer_headers(),
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') == 'success':
                response_data = result.get('data', {})
                checkout_token = response_data.get('token')
                
                # Hubtel checkout URL
                checkout_url = f"{self.base_url}/checkout/{checkout_token}"
                
                return True, {
                    'checkout_url': checkout_url,
                    'token': checkout_token,
                    'reference': reference
                }
            else:
                logger.error(f"Hubtel initialization failed: {result}")
                return False, {'message': result.get('message', 'Initialization failed')}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel API request failed: {str(e)}")
            return False, {'message': 'Network error occurred'}
        except HubtelException as e:
            logger.error(f"Hubtel authentication error: {str(e)}")
            return False, {'message': 'Payment gateway authentication error'}
        except Exception as e:
            logger.error(f"Unexpected error in Hubtel initialization: {str(e)}")
            return False, {'message': 'An unexpected error occurred'}

    def verify_transaction(self, reference):
        """
        Verify a Hubtel transaction by reference
        
        Args:
            reference (str): Transaction reference
            
        Returns:
            tuple: (success: bool, data: dict or None)
        """
        url = f"{self.base_url}/v2/pos/onlinecheckout/mobile/status/{reference}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_bearer_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') == 'success':
                data = result.get('data', {})
                status = data.get('status', '').lower()
                
                # Transaction statuses in Hubtel
                if status in ['completed', 'success', 'approved']:
                    return True, {
                        'status': 'success',
                        'amount': float(data.get('amount', 0)),
                        'channel': data.get('paymentMethod', 'mobile_money'),
                        'customer_name': data.get('customerName', ''),
                        'customer_email': data.get('customerEmail', ''),
                        'transaction_id': data.get('transactionId', reference),
                        'reference': reference,
                        'currency': 'GHS',
                        'paid_at': data.get('paidAt', ''),
                    }
                elif status in ['pending', 'initiated']:
                    return False, {'status': 'pending', 'message': 'Payment pending'}
                else:
                    return False, {'status': status, 'message': f'Payment {status}'}
            else:
                return False, result
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel verification request failed for {reference}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error in Hubtel verification for {reference}: {str(e)}")
            return False, None

    def get_transaction_status(self, token):
        """
        Get transaction status using Hubtel checkout token
        
        Args:
            token (str): Hubtel checkout token
            
        Returns:
            dict: Transaction status data
        """
        url = f"{self.base_url}/v2/pos/onlinecheckout/mobile/status/token/{token}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_bearer_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') == 'success':
                return result.get('data', {})
            return None
            
        except Exception as e:
            logger.error(f"Hubtel status check failed for token {token}: {str(e)}")
            return None
