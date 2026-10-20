from __future__ import annotations

import threading

from app.services.collection_service import CollectionService


class CollectionScheduler:
    """Minute-level scheduler for sources explicitly enabled by a researcher."""

    def __init__(self, service: CollectionService | None = None, interval_seconds: int = 60) -> None:
        self.service = service or CollectionService()
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="collection-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.service.run_due_jobs()
            except Exception:
                # The schema may not be migrated yet or a remote source may be offline.
                # Individual job failures are persisted by CollectionService.
                continue


scheduler = CollectionScheduler()
