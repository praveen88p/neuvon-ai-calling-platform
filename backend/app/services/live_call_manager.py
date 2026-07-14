from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.live_call import LiveCallHeartbeat, LiveCallUpdate


class LiveCallManager:
    """Manages WebSocket connections and call status broadcasting.

    Uses Redis pub/sub when available. Falls back to in-memory
    broadcast for single-instance deployments.
    """

    CHANNEL = "neuvon:live_calls"
    HEARTBEAT_INTERVAL = 30  # seconds

    def __init__(self) -> None:
        # org_id -> set of WebSocket connections
        self._connections: dict[str, set] = {}
        self._redis = None
        self._subscriber_task: asyncio.Task | None = None

    async def connect_redis(self) -> bool:
        """Attempt Redis connection for pub/sub. Returns True if connected."""
        settings = get_settings()
        redis_url = settings.REDIS_URL

        if not redis_url or "your-" in redis_url:
            logger.info("live_calls.redis_skipped", reason="placeholder URL")
            return False

        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("live_calls.redis_connected")
            return True
        except Exception as exc:
            logger.warning("live_calls.redis_failed", error=str(exc))
            self._redis = None
            return False

    async def start_subscriber(self) -> None:
        """Start Redis pub/sub listener for cross-instance broadcasting."""
        if not self._redis:
            return

        async def _listen() -> None:
            try:
                pubsub = self._redis.pubsub()
                await pubsub.subscribe(self.CHANNEL)

                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        data = json.loads(message["data"])
                        org_id = data.get("organization_id", "")
                        await self._broadcast_to_org(org_id, data)
                    except Exception as exc:
                        logger.warning("live_calls.message_error", error=str(exc))
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.error("live_calls.subscriber_error", error=str(exc))

        self._subscriber_task = asyncio.create_task(_listen())

    async def stop(self) -> None:
        """Clean shutdown."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

        if self._redis:
            await self._redis.close()

    def register(self, org_id: str, websocket) -> None:
        """Register a WebSocket connection for an organization."""
        if org_id not in self._connections:
            self._connections[org_id] = set()
        self._connections[org_id].add(websocket)
        logger.info("live_calls.ws_connected", org_id=org_id)

    def unregister(self, org_id: str, websocket) -> None:
        """Remove a WebSocket connection."""
        if org_id in self._connections:
            self._connections[org_id].discard(websocket)
            if not self._connections[org_id]:
                del self._connections[org_id]
        logger.info("live_calls.ws_disconnected", org_id=org_id)

    async def publish_update(self, org_id: str, update: LiveCallUpdate) -> None:
        """Publish a call update to all connected clients for an org."""
        payload = update.model_dump()
        payload["organization_id"] = org_id

        if self._redis:
            try:
                await self._redis.publish(self.CHANNEL, json.dumps(payload))
                return
            except Exception as exc:
                logger.warning("live_calls.redis_publish_failed", error=str(exc))

        # Fallback: direct in-memory broadcast
        await self._broadcast_to_org(org_id, payload)

    async def _broadcast_to_org(self, org_id: str, data: dict) -> None:
        """Send message to all WebSocket connections for an org."""
        connections = self._connections.get(org_id, set()).copy()
        if not connections:
            return

        message = json.dumps(data)
        dead = set()

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        # Clean up dead connections
        for ws in dead:
            self.unregister(org_id, ws)

    async def send_heartbeat(self, org_id: str, websocket) -> None:
        """Send periodic heartbeat to a single client."""
        heartbeat = LiveCallHeartbeat(
            timestamp=datetime.now(timezone.utc).isoformat(),
            active_calls=len(self._connections.get(org_id, set())),
        )
        try:
            await websocket.send_text(heartbeat.model_dump_json())
        except Exception:
            pass

    def get_connection_count(self, org_id: str | None = None) -> int:
        """Get active connection count."""
        if org_id:
            return len(self._connections.get(org_id, set()))
        return sum(len(c) for c in self._connections.values())


# Singleton instance
_manager: LiveCallManager | None = None


def get_live_call_manager() -> LiveCallManager:
    """Get or create the singleton LiveCallManager."""
    global _manager
    if _manager is None:
        _manager = LiveCallManager()
    return _manager
