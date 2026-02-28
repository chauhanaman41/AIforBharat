"""
AIforBharat — Local Event Bus
==============================
In-memory event bus for local development. Replaces Apache Kafka.
Supports publish/subscribe pattern with async handlers.
In production, this would be swapped for Kafka/NATS.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Coroutine
from shared.models import EventMessage, EventType

logger = logging.getLogger("event_bus")


class LocalEventBus:
    """
    In-memory async event bus for local development.
    Replaces Apache Kafka / Redis Streams for MVP.
    
    Features:
    - Async publish/subscribe
    - Wildcard (*) subscriptions
    - Event history for debugging
    - Dead letter queue for failed handlers
    """

    def __init__(self, max_history: int = 1000):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[EventMessage] = []
        self._dead_letter: list[dict] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        logger.info("Local event bus initialized")

    def subscribe(self, event_type: str, handler: Callable[..., Coroutine]):
        """
        Subscribe a handler to an event type.
        Use '*' to subscribe to all events.
        """
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to '{event_type}'")

    def unsubscribe(self, event_type: str, handler: Callable):
        """Remove a handler from an event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: EventMessage):
        """
        Publish an event to all matching subscribers.
        Matches both specific event types and wildcard (*) subscribers.
        """
        async with self._lock:
            # Store in history (bounded)
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type

        # Collect matching handlers
        handlers = list(self._subscribers.get(event_type, []))
        handlers.extend(self._subscribers.get("*", []))

        logger.info(
            f"Publishing event {event_type} from {event.source_engine} "
            f"to {len(handlers)} handler(s)"
        )

        # Execute handlers concurrently
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed for {event_type}: {e}")
                self._dead_letter.append({
                    "event": event.model_dump(),
                    "handler": handler.__name__,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })

    def get_history(self, event_type: str = None, limit: int = 50) -> list[EventMessage]:
        """Get recent event history, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        return events[-limit:]

    def get_dead_letters(self, limit: int = 50) -> list[dict]:
        """Get recent dead letter queue entries."""
        return self._dead_letter[-limit:]

    def get_stats(self) -> dict:
        """Get event bus statistics."""
        return {
            "total_events_published": len(self._history),
            "active_subscriptions": {k: len(v) for k, v in self._subscribers.items()},
            "dead_letter_count": len(self._dead_letter),
        }


# ── Singleton event bus instance ──────────────────────────────────────────────
event_bus = LocalEventBus()
