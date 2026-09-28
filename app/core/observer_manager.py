"""
observer_manager.py
AI_SYNC Enterprise V3

負責：
- 建立 Watchdog Observer
- 啟動監控
- 停止監控

不負責：
- Queue
- Copy
- Logger
"""

from watchdog.observers import Observer


class ObserverManager:

    def __init__(self):

        self._observer = Observer()

        self._started = False

    @property
    def observer(self):
        return self._observer

    @property
    def running(self):
        return self._started

    def schedule(self, handler, path, recursive=True):

        self._observer.schedule(
            handler,
            path,
            recursive=recursive
        )

    def start(self):

        if self._started:
            return

        self._observer.start()

        self._started = True

    def stop(self):

        if not self._started:
            return

        self._observer.stop()

        self._observer.join()

        self._started = False