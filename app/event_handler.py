import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler


class EventHandler(FileSystemEventHandler):

    def __init__(self, queue):

        super().__init__()

        self.queue = queue

        self.recent_events = {}

        # 同一檔案 0.5 秒內只允許一次
        self.event_interval = 3.0

    def on_created(self, event):

        if event.is_directory:
            return

        self._enqueue(event.src_path)

    def on_modified(self, event):

        if event.is_directory:
            return

        self._enqueue(event.src_path)

    def _enqueue(self, filepath):

        filepath = str(Path(filepath).resolve())

        now = time.time()

        last = self.recent_events.get(filepath)

        if last is not None:

            if now - last < self.event_interval:
                return

        self.recent_events[filepath] = now

        self.queue.put(filepath)