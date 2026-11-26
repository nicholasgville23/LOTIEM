from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from queue import PriorityQueue
from typing import Callable

from .models import WeatherMessage


class BroadcastQueue:
    """Priority queue and manually controlled continuous broadcast loop."""
    def __init__(self, on_message: Callable[[WeatherMessage], None] | None = None):
        self._queue: PriorityQueue = PriorityQueue()
        self._counter = 0
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_message = on_message or (lambda message: None)
        self.current: WeatherMessage | None = None

    def enqueue(self, message: WeatherMessage) -> None:
        with self._lock:
            self._counter += 1
            self._queue.put((-int(message.priority), self._counter, message))

    def start(self, interval_seconds: int = 60) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._loop, args=(interval_seconds,),
                                        name="LOTIEM-BroadcastLoop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _loop(self, interval_seconds: int) -> None:
        while self._running.is_set():
            try:
                _, _, message = self._queue.get(timeout=1)
            except Exception:
                continue
            self.current = message
            try:
                self.on_message(message)
            finally:
                self.current = None
                self._queue.task_done()
            self._running.wait(max(0, interval_seconds))

    @property
    def queue_length(self) -> int:
        return self._queue.qsize()


class MessageArchive:
    def __init__(self, path: str = "runtime/messages.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message: WeatherMessage) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
