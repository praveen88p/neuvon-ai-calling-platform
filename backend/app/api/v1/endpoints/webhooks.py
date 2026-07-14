from __future__ import annotations

import json

from fastapi import APIRouter, Request

from app.schemas.webhook import DograhWebhookPayload, WebhookAckResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/dograh", response_model=WebhookAckResponse)
async def receive_dograh_webhook(
    request: Request,
) -> WebhookAckResponse:
    """Receive post-call webhook from Dograh.

    No auth dependency — webhooks are verified via HMAC signature.
    Endpoint is idempotent: processing the same payload twice
    produces the same result.
    """
    service = WebhookService()

    body = await service.verify_webhook_signature(request)

    raw = json.loads(body)
    payload = DograhWebhookPayload.model_validate(raw)

    return await service.process_dograh_webhook(payload)


@router.post("/razorpay")
async def receive_razorpay_webhook(request: Request) -> dict:
    """Receive payment webhook from Razorpay.

    No auth dependency — webhooks are verified via HMAC signature
    using the Razorpay SDK. Handles payment.captured events to
    mark billing records as paid.
    """
    from app.services.billing_service import BillingService

    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    service = BillingService()
    return await service.process_razorpay_webhook(body, signature)

