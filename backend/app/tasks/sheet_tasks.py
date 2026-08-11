"""Celery tasks for spreadsheet integration.

Tasks run in the background to poll sheet connections for new rows
and check scheduled callbacks.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.celery_app import get_celery_app
from app.core.logging import logger

celery = get_celery_app()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task.

    Creates a fresh event loop per invocation so that httpx/anyio connections
    are always bound to a live loop. Without this, a cached httpx.AsyncClient
    would hold references to a previously closed loop and crash with
    RuntimeError('Event loop is closed') on the second task run.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            # Cancel any remaining tasks before closing
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@celery.task(name="sheets.poll_all", bind=True, max_retries=0)
def poll_all_active_connections(self):
    """Poll ALL active sheet connections for new rows.

    Scheduled via Celery Beat every 60 seconds. Each connection
    is polled individually; errors in one don't affect others.
    """
    _run_async(_poll_all())


async def _poll_all():
    """Async implementation of poll_all_active_connections."""
    from app.integrations.insforge_client import get_insforge_admin
    from app.services.sheet_service import SheetService

    db = get_insforge_admin()

    # Fetch all active connections
    result = (
        await db.database.from_("sheet_connections")
        .select("id, organization_id")
        .eq("is_active", True)
        .execute()
    )
    connections = result if isinstance(result, list) else []

    if not connections:
        return

    logger.info("sheets.poll_all_start", count=len(connections))

    service = SheetService()
    total_new = 0

    for conn in connections:
        connection_id = conn["id"]
        try:
            new_count = await service.poll_for_new_leads(connection_id)
            total_new += new_count
        except Exception as exc:
            logger.error(
                "sheets.poll_one_failed",
                connection_id=connection_id,
                error=str(exc),
            )

    logger.info("sheets.poll_all_done", total_new_leads=total_new)


@celery.task(name="sheets.poll_one", bind=True, max_retries=2)
def poll_single_connection(self, connection_id: str):
    """Poll a single connection for new leads.

    Can be triggered manually or after a connection is created/resumed.
    """
    _run_async(_poll_one(connection_id))


async def _poll_one(connection_id: str):
    from app.services.sheet_service import SheetService

    service = SheetService()
    new_count = await service.poll_for_new_leads(connection_id)
    logger.info(
        "sheets.poll_one_done",
        connection_id=connection_id,
        new_leads=new_count,
    )


@celery.task(name="sheets.check_callbacks", bind=True, max_retries=0)
def check_due_callbacks(self):
    """Check for scheduled callbacks that are due and trigger calls.

    Runs every 60 seconds via Celery Beat.
    """
    _run_async(_check_callbacks())


async def _check_callbacks():
    """Async implementation of check_due_callbacks.

    Delegates to CallbackService which handles:
    - Agent UUID resolution
    - Dograh call triggering
    - Retry logic (up to MAX_RETRIES with RETRY_DELAY_MINUTES)
    - sheet_lead status update
    """
    from app.services.callback_service import CallbackService

    service = CallbackService()
    triggered = await service.fire_due_callbacks()

    if triggered > 0:
        logger.info("sheets.check_callbacks_done", triggered=triggered)
