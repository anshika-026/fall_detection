"""In-process pub/sub that carries live events from the detection threads to the
websocket clients (dashboard, live monitoring). Publishing never blocks and never
raises: a slow or dead client only loses its own messages."""
from __future__ import annotations

import asyncio
import logging
import threading

log = logging.getLogger("hub")


class EventHub:
    def __init__(self):
        self._lock = threading.Lock()
        self._subs: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = set()

    def subscribe(self) -> tuple[asyncio.Queue, tuple]:
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        entry = (loop, q)
        with self._lock:
            self._subs.add(entry)
        return q, entry

    def unsubscribe(self, entry) -> None:
        with self._lock:
            self._subs.discard(entry)

    def publish(self, message: dict) -> None:
        with self._lock:
            subs = list(self._subs)
        for loop, q in subs:
            try:
                loop.call_soon_threadsafe(self._put, q, message)
            except RuntimeError:       # loop closed
                with self._lock:
                    self._subs.discard((loop, q))

    @staticmethod
    def _put(q: asyncio.Queue, message: dict) -> None:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            try:
                q.get_nowait()
                q.put_nowait(message)
            except Exception:  # noqa: S110
                pass

    @property
    def subscribers(self) -> int:
        return len(self._subs)


hub = EventHub()
