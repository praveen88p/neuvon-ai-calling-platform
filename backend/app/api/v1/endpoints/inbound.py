"""Provider-agnostic inbound call routing endpoint.

Architecture
------------
Every telephony provider (Plivo, Twilio, Vobiz, …) is assigned a unique
Answer URL that encodes the Dograh ``config_id``:

    https://<host>/api/v1/telephony/inbound/route/{config_id}

This allows our router to immediately know *which provider* is calling
without any guesswork — the config record holds the ``provider`` type.

Flow
----
1. Provider receives inbound call on one of our numbers.
2. Provider POSTs to our Answer URL:
       POST /api/v1/telephony/inbound/route/{config_id}
   with provider-specific form fields (To/from/CallSid/etc.).
3. We extract the ``To`` number using a provider-specific field extractor.
4. We look up ``inbound_workflow_id`` for that number from our local DB
   (fast — single Supabase query, no Dograh round-trip in the hot path).
5. We proxy the original request body to Dograh's inbound endpoint with
   ``?workflow_id=<id>`` appended.
6. We return Dograh's PlivoXML / TwiML response directly to the provider.

Adding a new provider
---------------------
1. Add a ``ProviderAdapter`` subclass below (or a dict entry in
   ``PROVIDER_ADAPTERS``).
2. Set that provider's Answer URL / Webhook URL in their dashboard to:
       https://<host>/api/v1/telephony/inbound/route/{config_id}
That's it — no other code changes needed.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
from fastapi import APIRouter, Path, Request, Response
from fastapi.responses import PlainTextResponse

from app.core.logging import logger
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin

router = APIRouter(prefix="/telephony/inbound", tags=["inbound"])

# Dograh hosted inbound endpoint — we proxy to this with ?workflow_id=<id>
_DOGRAH_INBOUND_URL = "https://api.dograh.com/api/v1/telephony/inbound/run"

# Fallback workflow when no per-number assignment is found.
# Should be a generic inbound agent that says "wrong number" / handles edge cases.
_FALLBACK_WORKFLOW_ID = 9458  # "Lead qualificatipn01 - inbound"


# ── Provider adapters ─────────────────────────────────────────────────────────

def _norm(number: str) -> str:
    """Strip whitespace → bare E.164, e.g. '+912269851695'."""
    return re.sub(r"\s+", "", number or "")


class ProviderAdapter(ABC):
    """Knows how to extract call metadata from a specific provider's webhook."""

    @abstractmethod
    def extract_to(self, form: dict[str, Any]) -> str:
        """Return the dialled number (our number) from the webhook payload."""

    @abstractmethod
    def extract_from(self, form: dict[str, Any]) -> str:
        """Return the caller's number from the webhook payload."""

    def extract_call_id(self, form: dict[str, Any]) -> str:
        """Return a provider-specific call ID for logging (best-effort)."""
        return (
            form.get("CallUUID")          # Plivo
            or form.get("CallSid")        # Twilio
            or form.get("call_id")        # generic
            or form.get("session_id")     # Vobiz / others
            or ""
        )


class PlivoAdapter(ProviderAdapter):
    """Plivo webhook fields: To, From, CallUUID, Direction, …"""

    def extract_to(self, form: dict[str, Any]) -> str:
        return _norm(form.get("To") or form.get("to") or "")

    def extract_from(self, form: dict[str, Any]) -> str:
        return _norm(form.get("From") or form.get("from") or "")


class TwilioAdapter(ProviderAdapter):
    """Twilio webhook fields: To, From, CallSid, Direction, …"""

    def extract_to(self, form: dict[str, Any]) -> str:
        # Twilio sends E.164 in 'To' and also 'Called'
        return _norm(form.get("To") or form.get("Called") or "")

    def extract_from(self, form: dict[str, Any]) -> str:
        return _norm(form.get("From") or form.get("Caller") or "")


class VobizAdapter(ProviderAdapter):
    """Vobiz webhook fields — update field names once confirmed with Vobiz docs."""

    def extract_to(self, form: dict[str, Any]) -> str:
        # Common patterns: 'to', 'destination', 'called_number'
        return _norm(
            form.get("to")
            or form.get("destination")
            or form.get("called_number")
            or form.get("To")
            or ""
        )

    def extract_from(self, form: dict[str, Any]) -> str:
        return _norm(
            form.get("from")
            or form.get("caller")
            or form.get("calling_number")
            or form.get("From")
            or ""
        )


class GenericAdapter(ProviderAdapter):
    """Best-effort fallback for unknown providers — tries common field names."""

    def extract_to(self, form: dict[str, Any]) -> str:
        for key in ("To", "to", "destination", "called_number", "dialed_number", "dst"):
            if form.get(key):
                return _norm(form[key])
        return ""

    def extract_from(self, form: dict[str, Any]) -> str:
        for key in ("From", "from", "caller", "calling_number", "src"):
            if form.get(key):
                return _norm(form[key])
        return ""


# Registry — add new providers here as you integrate them
PROVIDER_ADAPTERS: dict[str, ProviderAdapter] = {
    "plivo":   PlivoAdapter(),
    "twilio":  TwilioAdapter(),
    "vobiz":   VobizAdapter(),
    # "bandwidth": BandwidthAdapter(),
    # "signalwire": SignalWireAdapter(),
}

_GENERIC_ADAPTER = GenericAdapter()


def _get_adapter(provider: str | None) -> ProviderAdapter:
    """Return the right adapter, falling back to GenericAdapter."""
    if provider:
        adapter = PROVIDER_ADAPTERS.get(provider.lower().strip())
        if adapter:
            return adapter
        logger.warning("inbound.unknown_provider", provider=provider)
    return _GENERIC_ADAPTER


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _get_provider_for_config(config_id: int) -> str | None:
    """Fetch provider type from our local telephony_configs table."""
    try:
        db = get_insforge_admin()
        rows = (
            await db.database.from_("telephony_configs")
            .select("provider")
            .eq("dograh_config_id", config_id)
            .execute()
        )
        rows = rows if isinstance(rows, list) else []
        if rows:
            return rows[0].get("provider")
    except Exception as exc:
        logger.warning("inbound.config_lookup_failed", config_id=config_id, error=str(exc))
    return None


async def _lookup_workflow_id(config_id: int, to_number_normalized: str) -> int:
    """Return inbound_workflow_id for *to_number_normalized* within *config_id*.

    Lookup order:
    1. Local DB — fast path (single query, no external calls)
    2. Dograh API — slow fallback for numbers added before migration 007
    3. Hard-coded fallback workflow ID
    """
    # ── 1. Local DB ───────────────────────────────────────────────────────
    try:
        db = get_insforge_admin()
        # Get our local config UUID from dograh_config_id
        config_rows = (
            await db.database.from_("telephony_configs")
            .select("id")
            .eq("dograh_config_id", config_id)
            .execute()
        )
        config_rows = config_rows if isinstance(config_rows, list) else []
        if config_rows:
            local_config_id = config_rows[0]["id"]
            num_rows = (
                await db.database.from_("phone_numbers")
                .select("inbound_workflow_id")
                .eq("telephony_config_id", local_config_id)
                .eq("number_normalized", to_number_normalized)
                .execute()
            )
            num_rows = num_rows if isinstance(num_rows, list) else []
            if num_rows and num_rows[0].get("inbound_workflow_id"):
                wid = int(num_rows[0]["inbound_workflow_id"])
                logger.info(
                    "inbound.route_local",
                    config_id=config_id,
                    to=to_number_normalized,
                    workflow_id=wid,
                )
                return wid
    except Exception as exc:
        logger.warning("inbound.local_lookup_failed", to=to_number_normalized, error=str(exc))

    # ── 2. Dograh API (slow fallback) ─────────────────────────────────────
    try:
        client = DograhClient()
        nums_resp = await client.list_phone_numbers(config_id)
        phone_list = (
            nums_resp.get("phone_numbers", [])
            if isinstance(nums_resp, dict)
            else nums_resp
        )
        for phone in phone_list:
            addr = _norm(
                phone.get("address_normalized") or phone.get("address", "")
            )
            if addr == to_number_normalized:
                wid = phone.get("inbound_workflow_id")
                if wid:
                    logger.info(
                        "inbound.route_dograh",
                        config_id=config_id,
                        to=to_number_normalized,
                        workflow_id=wid,
                    )
                    return int(wid)
    except Exception as exc:
        logger.error(
            "inbound.dograh_lookup_failed",
            config_id=config_id,
            to=to_number_normalized,
            error=str(exc),
        )

    # ── 3. Fallback ───────────────────────────────────────────────────────
    logger.warning(
        "inbound.route_fallback",
        config_id=config_id,
        to=to_number_normalized,
        fallback=_FALLBACK_WORKFLOW_ID,
    )
    return _FALLBACK_WORKFLOW_ID


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/route/{config_id}",
    include_in_schema=True,
    summary="Per-number inbound call router (provider-agnostic)",
    description=(
        "Public webhook — set this as the Answer URL / Webhook URL for each "
        "telephony configuration in its provider dashboard. The {config_id} "
        "path parameter identifies which provider is calling."
    ),
)
async def route_inbound_call(
    request: Request,
    config_id: int = Path(..., description="Dograh telephony configuration ID"),
) -> Response:
    """Provider-agnostic inbound router.

    Set the Answer URL on your telephony provider to:
        POST https://<your-host>/api/v1/telephony/inbound/route/<config_id>

    Replace <config_id> with the Dograh telephony configuration ID for that
    provider (visible in the Dograh Telephony page → Configuration ID field).
    """
    # Parse incoming webhook body
    form_data: dict[str, Any] = {}
    try:
        form_data = dict(await request.form())
    except Exception:
        pass

    # Identify provider from DB and pick the right adapter
    provider = await _get_provider_for_config(config_id)
    adapter  = _get_adapter(provider)

    to_number   = adapter.extract_to(form_data)
    from_number = adapter.extract_from(form_data)
    call_id     = adapter.extract_call_id(form_data)

    logger.info(
        "inbound.received",
        config_id=config_id,
        provider=provider or "unknown",
        to=to_number,
        from_number=from_number,
        call_id=call_id,
    )

    if not to_number:
        logger.warning(
            "inbound.no_to_number",
            config_id=config_id,
            provider=provider,
            form_keys=list(form_data.keys()),
        )

    workflow_id = await _lookup_workflow_id(config_id, to_number)

    # Proxy to Dograh's inbound endpoint with the resolved workflow
    dograh_url = f"{_DOGRAH_INBOUND_URL}?workflow_id={workflow_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            dograh_resp = await http.post(
                dograh_url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        logger.info(
            "inbound.proxied",
            config_id=config_id,
            provider=provider,
            to=to_number,
            workflow_id=workflow_id,
            dograh_status=dograh_resp.status_code,
        )
        return Response(
            content=dograh_resp.content,
            status_code=dograh_resp.status_code,
            media_type=dograh_resp.headers.get("content-type", "application/xml"),
        )

    except Exception as exc:
        logger.error(
            "inbound.proxy_failed",
            config_id=config_id,
            provider=provider,
            to=to_number,
            workflow_id=workflow_id,
            error=str(exc),
        )
        # Graceful hangup — provider-neutral XML that both Plivo and Twilio understand
        fallback_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Speak>We are sorry, the service is temporarily unavailable. "
            "Please try again later.</Speak>"
            "<Hangup/>"
            "</Response>"
        )
        return PlainTextResponse(
            content=fallback_xml,
            status_code=200,
            media_type="application/xml",
        )


# ── Legacy compatibility route (no config_id) ─────────────────────────────────
# Kept so any existing Plivo Answer URL without a config_id still works.
# Tries to find the number across ALL configs — slower.

@router.post(
    "/route",
    include_in_schema=False,
)
async def route_inbound_call_legacy(request: Request) -> Response:
    """Legacy route — no config_id. Searches all configs for the To number.

    Prefer the /{config_id} route for new integrations.
    """
    form_data: dict[str, Any] = {}
    try:
        form_data = dict(await request.form())
    except Exception:
        pass

    # Try common To field names
    to_raw = (
        form_data.get("To")
        or form_data.get("to")
        or form_data.get("destination")
        or ""
    )
    to_number = _norm(to_raw)

    logger.info("inbound.legacy_received", to=to_number)

    # Search all configs
    workflow_id = _FALLBACK_WORKFLOW_ID
    try:
        client = DograhClient()
        configs = (await client.list_telephony_configs()).get("configurations", [])
        for config in configs:
            cfg_id = config.get("id")
            found = await _lookup_workflow_id(cfg_id, to_number)
            if found != _FALLBACK_WORKFLOW_ID:
                workflow_id = found
                break
    except Exception as exc:
        logger.error("inbound.legacy_lookup_failed", to=to_number, error=str(exc))

    dograh_url = f"{_DOGRAH_INBOUND_URL}?workflow_id={workflow_id}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            dograh_resp = await http.post(
                dograh_url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        return Response(
            content=dograh_resp.content,
            status_code=dograh_resp.status_code,
            media_type=dograh_resp.headers.get("content-type", "application/xml"),
        )
    except Exception as exc:
        logger.error("inbound.legacy_proxy_failed", error=str(exc))
        fallback_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response><Hangup/></Response>"
        )
        return PlainTextResponse(content=fallback_xml, status_code=200, media_type="application/xml")
