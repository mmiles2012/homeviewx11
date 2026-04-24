"""Event bus for broadcasting state changes to WebSocket clients."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Simple pub/sub bus; each subscriber gets an asyncio.Queue."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Create and register a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        try:
            self._queues.remove(queue)
        except ValueError:
            pass

    async def emit(self, event_type: str, data: Any) -> None:
        """Broadcast an event to all subscribers."""
        event = {"type": event_type, "data": data}
        for queue in list(self._queues):
            try:
                await queue.put(event)
            except Exception as exc:
                logger.warning("Failed to deliver event to subscriber: %s", exc)
