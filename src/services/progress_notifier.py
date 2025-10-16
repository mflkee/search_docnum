import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from src.utils.logging_config import app_logger


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProgressNotifier:
    """Simple pub/sub broker to push task progress updates to listeners (SSE/EventSource)."""

    _listeners: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def subscribe(cls, task_id: str, *, max_queue_size: int = 100) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(max_queue_size)
        async with cls._lock:
            listeners = cls._listeners.setdefault(task_id, set())
            listeners.add(queue)
            app_logger.debug("ProgressNotifier: subscribed listener for task %s (total %d)", task_id, len(listeners))
        return queue

    @classmethod
    async def unsubscribe(cls, task_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with cls._lock:
            listeners = cls._listeners.get(task_id)
            if not listeners:
                return
            listeners.discard(queue)
            if not listeners:
                cls._listeners.pop(task_id, None)
            app_logger.debug(
                "ProgressNotifier: unsubscribed listener for task %s (remaining %d)",
                task_id,
                len(listeners) if listeners else 0,
            )

    @classmethod
    async def broadcast(cls, task_id: str, payload: dict[str, Any]) -> None:
        async with cls._lock:
            listeners = cls._listeners.get(task_id)
            if not listeners:
                return
            targets = list(listeners)

        payload = dict(payload)
        payload.setdefault("timestamp", _utc_iso())

        for queue in targets:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    app_logger.debug("ProgressNotifier: dropping update for task %s due to full queue", task_id)

    @staticmethod
    def serialize_event(payload: dict[str, Any]) -> bytes:
        body = json.dumps(payload, ensure_ascii=False)
        return f"data: {body}\n\n".encode("utf-8")

    @classmethod
    async def stream(cls, task_id: str, initial_payload: dict[str, Any]) -> AsyncIterator[bytes]:
        queue = await cls.subscribe(task_id)
        try:
            yield cls.serialize_event(initial_payload)
            while True:
                payload = await queue.get()
                yield cls.serialize_event(payload)
        except asyncio.CancelledError:
            raise
        finally:
            await cls.unsubscribe(task_id, queue)
