"""
watchdog_handler.py
AI_SYNC Enterprise V3

負責：
- 接收 Watchdog Event
- 統一交給 EventRouter

不負責：
- Queue
- Copy
- Logger
"""

from watchdog.events import FileSystemEventHandler


class WatchdogHandler(FileSystemEventHandler):

    def __init__(self, router):

        super().__init__()

        self.router = router

    # -------------------------
    # Watchdog Events
    # -------------------------

    def on_created(self, event):

        self._process(event)

    def on_modified(self, event):

        self._process(event)

    def on_deleted(self, event):

        self._process(event)

    def on_moved(self, event):

        self._process(event)

    # -------------------------
    # Private
    # -------------------------

    def _process(self, event):

        self.router.route(event)