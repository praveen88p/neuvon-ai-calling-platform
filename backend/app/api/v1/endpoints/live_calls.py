from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin
from app.services.live_call_manager import get_live_call_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/live-calls")
async def live_calls_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """WebSocket endpoint for real-time call status updates.

    Clients connect with JWT token in query param for authentication.
    Server pushes call updates and periodic heartbeats.
    """
    # Authenticate via JWT token
    user_context = await _authenticate_ws(token)
    if not user_context:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    org_id = user_context.get("organization_id", "")
    if not org_id:
        await websocket.close(code=4002, reason="No organization context")
        return

    await websocket.accept()

    manager = get_live_call_manager()
    manager.register(org_id, websocket)

    try:
        # Send initial heartbeat
        await manager.send_heartbeat(org_id, websocket)

        # Start heartbeat loop in background
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(manager, org_id, websocket)
        )

        try:
            # Keep connection alive — listen for client messages
            while True:
                data = await websocket.receive_text()
                # Client can send "ping" for manual keep-alive
                if data.strip().lower() == "ping":
                    await websocket.send_text('{"type": "pong"}')
        except WebSocketDisconnect:
            pass
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    except Exception as exc:
        logger.error("live_calls.ws_error", org_id=org_id, error=str(exc))
    finally:
        manager.unregister(org_id, websocket)


async def _heartbeat_loop(manager, org_id: str, websocket: WebSocket) -> None:
    """Send heartbeat every 30 seconds."""
    try:
        while True:
            await asyncio.sleep(manager.HEARTBEAT_INTERVAL)
            await manager.send_heartbeat(org_id, websocket)
    except asyncio.CancelledError:
        pass


async def _authenticate_ws(token: str) -> dict | None:
    """Validate JWT token and return user context dict."""
    try:
        admin = get_insforge_admin()
        session = await admin.auth.get_current_session(access_token=token)
        if not session or not session.user:
            return None

        user_id = str(session.user.id)

        rows = await admin.database.from_("users") \
            .select("id,organization_id,email,full_name,role,is_active") \
            .eq("id", user_id) \
            .execute()
        rows = rows if isinstance(rows, list) else []

        if not rows or not rows[0].get("is_active", False):
            return None

        return rows[0]

    except Exception as exc:
        logger.warning("live_calls.ws_auth_failed", error=str(exc))
        return None
