
# payment/paystack.py
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Paystack:
    base_url = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        if not self.secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY is not set in settings")

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(self, email, amount, reference, callback_url=None, metadata=None):
        """
        Initialize a Paystack transaction
        
        Args:
            email (str): Customer email
            amount (int): Amount in pesewas
            reference (str): Unique transaction reference
            callback_url (str, optional): URL to redirect after payment
            metadata (dict, optional): Additional data
            
        Returns:
            tuple: (success: bool, data: dict)
        """
        url = f"{self.base_url}/transaction/initialize"
        
        data = {
            "email": email,
            "amount": amount,
            "reference": reference,
        }
        
        if callback_url:
            data["callback_url"] = callback_url
            
        if metadata:
            data["metadata"] = metadata

        try:
            response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status'):
                return True, result.get('data', {})
            else:
                logger.error(f"Paystack initialization failed: {result}")
                return False, result
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request failed: {str(e)}")
            return False, {"message": "Network error occurred"}
        except Exception as e:
            logger.error(f"Unexpected error in Paystack initialization: {str(e)}")
            return False, {"message": "An unexpected error occurred"}

    def verify_payment(self, reference):
        """
        Verify a payment with Paystack
        
        Args:
            reference (str): Transaction reference
            
        Returns:
            tuple: (success: bool, data: dict or None)
        """
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') and result.get('data', {}).get('status') == "success":
                return True, result['data']
            else:
                logger.warning(f"Payment verification failed for {reference}: {result}")
                return False, result.get('data')
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification request failed for {reference}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error in payment verification for {reference}: {str(e)}")
            return False, None

    def get_transaction(self, transaction_id):
        """Get transaction details by ID"""
        url = f"{self.base_url}/transaction/{transaction_id}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status'):
                return True, result.get('data')
            return False, result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get transaction {transaction_id}: {str(e)}")
            return False, None






