"""
watchdog_handler.py
AI_SYNC Enterprise V3

負責：
- 接收 Watchdog Event
- 呼叫 EventRouter
"""

from watchdog.events import FileSystemEventHandler


class WatchdogHandler(FileSystemEventHandler):

    def __init__(self, router):

        super().__init__()

        self.router = router

    def on_created(self, event):
        self.router.route(event)

    def on_modified(self, event):
        self.router.route(event)

    def on_moved(self, event):
        self.router.route(event)

    def on_deleted(self, event):
        self.router.route(event)