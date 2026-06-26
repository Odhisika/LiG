# Hubtel Payment Integration - UAT Reference Guide

This document provides the technical proof and data required for the Hubtel User Acceptance Testing (UAT).

## 1. Key Integration Files
These files in the codebase contain the Hubtel implementation logic:
- **`payment/hubtel.py`**: Contains the `Hubtel` class for API calls (`initiate` and `status`).
- **`payment/views.py`**: Contains the `hubtel_webhook` (server-to-server) and `verify_payment` (browser redirect) endpoints.
- **`payment/models.py`**: Manages the `Payment` record and state transitions.

---

## 2. Sample Transaction Status Check (API Response)
This is a real response captured from the logs for a successful transaction.

**Endpoint:** `GET https://rmsc.hubtel.com/v1/merchantaccount/merchants/{MerchantID}/transactions/status`

**Sample JSON:**
```json
{
  "ResponseCode": "0000",
  "Data": [
    {
      "StartDate": "2026-04-30T10:42:30.406882",
      "InvoiceStatus": "Success",
      "TransactionStatus": "Success",
      "TransactionId": "7c1bfc35aea749c1b6a01677276db4f6",
      "NetworkTransactionId": "80330087685",
      "CheckoutId": "7c1bfc35aea749c1b6a01677276db4f6",
      "InvoiceToken": "7c1bfc35aea749c1b6a01677276db4f6",
      "TransactionType": "RECEIVE-MONEY",
      "PaymentMethod": "MOBILE-MONEY",
      "ClientReference": "PAY_ACFF32874D09",
      "CountryCode": "GH",
      "CurrencyCode": "GHS",
      "TransactionAmount": 0.02,
      "Fee": 0.0,
      "AmountAfterFees": 0.01,
      "MobileNumber": "233593021696"
    }
  ]
}
```

---

## 3. Sample Callback/Webhook Payload
Your application handles callbacks via the `hubtel_webhook` view.

**Expected POST Structure:**
```json
{
  "Status": "Success",
  "ClientReference": "PAY_ACFF32874D09",
  "TransactionId": "7c1bfc35aea749c1b6a01677276db4f6",
  "Description": "Order 2026043011 - LiG Store",
  "Amount": 0.02,
  "Currency": "GHS"
}
```

---

## 4. Technical Integration Flow
1. **Initiate:** User clicks Pay $\rightarrow$ App sends order details to `payproxyapi.hubtel.com/items/initiate`.
2. **Redirect:** Hubtel returns a `checkoutUrl`; App redirects the user to complete payment.
3. **Webhook (Callback):** Hubtel sends an asynchronous `POST` to our `/payment/hubtel-webhook/` endpoint to confirm success.
4. **Verification:** App updates the `Payment` and `Order` status to `Successful` and `Paid`.
5. **Return:** User is redirected back to our site; App verifies the transaction ID one last time for security.

---

## 5. End-to-End Testing Script (Meeting Demo)
1. **Select Product:** Add item to cart and proceed to Checkout.
2. **Select Gateway:** Choose "Hubtel" and click "Complete Order".
3. **External Payment:** Complete the payment on the Hubtel Checkout page.
4. **Auto-Confirmation:** Show the user being redirected back to the "Success" page.
5. **Admin Proof:** Navigate to the Django Admin $\rightarrow$ Payments section to show the verified record.
6. **Live Logs:** (Optional) Show `tail -f logs/payments.log` to demonstrate the real-time API communication.


todo


1. Secrets exposed in .env — SECRET_KEY, Paystack (sk_test_*), Hubtel credentials, SMTP password, Google OAuth secrets — all real values. Rotate every single one.
2. Admin password in .env — admin12345 on line 42. Change immediately.
3. No Content Security Policy (CSP) — no protection against injected scripts
4. No 2FA/MFA — admin accounts have no second factor
5. No audit logging — no logging of admin actions, failed logins, etc.
6. DEBUG=True in production-ready .env — must be False before going live