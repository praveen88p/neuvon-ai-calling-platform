from __future__ import annotations

import hmac
import hashlib

import razorpay

from app.core.config import get_settings
from app.core.logging import logger


def get_razorpay_client() -> razorpay.Client:
    """Create Razorpay client with credentials from settings."""
    settings = get_settings()
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


class RazorpayService:
    """Wrapper around the razorpay Python SDK for order + payment operations.

    Uses the official razorpay.Client — never calls Razorpay REST directly.
    Ref: https://github.com/razorpay/razorpay-python
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        # Webhook secret is configured separately in Razorpay Dashboard.
        # Falls back to key_secret if not set (dev convenience only).
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET or self.key_secret

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: str = "",
        notes: dict[str, str] | None = None,
    ) -> dict:
        """Create a Razorpay order.

        Args:
            amount: Amount in smallest currency unit (paisa for INR)
            currency: Three-letter ISO currency code
            receipt: Internal receipt reference
            notes: Key-value notes (max 15 pairs)

        Returns:
            Razorpay order dict with id, amount, status, etc.
        """
        order_data: dict = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        }
        if notes:
            order_data["notes"] = notes

        logger.info("razorpay.create_order", amount=amount, currency=currency, receipt=receipt)
        return self.client.order.create(data=order_data)

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify Razorpay payment signature using HMAC-SHA256.

        The expected signature is:
            HMAC_SHA256(razorpay_order_id + '|' + razorpay_payment_id, key_secret)
        """
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected = hmac.HMAC(
            self.key_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, razorpay_signature)

    def verify_webhook_signature(
        self, body: bytes, signature: str
    ) -> bool:
        """Verify Razorpay webhook signature.

        Uses the razorpay SDK's built-in utility.
        """
        try:
            self.client.utility.verify_webhook_signature(
                body.decode("utf-8"),
                signature,
                self.webhook_secret,
            )
            return True
        except razorpay.errors.SignatureVerificationError:
            logger.warning("razorpay.webhook_signature_invalid")
            return False

    def fetch_payment(self, payment_id: str) -> dict:
        """Fetch a single payment by ID."""
        return self.client.payment.fetch(payment_id)

    def fetch_order(self, order_id: str) -> dict:
        """Fetch a single order by ID."""
        return self.client.order.fetch(order_id)

    def fetch_order_payments(self, order_id: str) -> dict:
        """Fetch all payments for an order."""
        return self.client.order.payments(order_id)
