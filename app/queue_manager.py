from queue import Queue, Empty
from threading import Thread, Event
from pathlib import Path
import time


class QueueManager:
    """
    Enterprise Queue Manager

    功能：
    - Queue
    - 去除重複事件
    - Worker Thread
    - Callback
    """

    def __init__(self, callback):

        self.callback = callback

        self.queue = Queue()

        self.stop_event = Event()

        self.pending = set()

        self.worker = Thread(
            target=self._worker,
            daemon=True
        )

    def start(self):

        if not self.worker.is_alive():
            self.worker.start()

    def stop(self):

        self.stop_event.set()

        self.worker.join(timeout=2)

    def put(self, filepath):

        filepath = str(Path(filepath))

        if filepath in self.pending:
            return

        self.pending.add(filepath)

        self.queue.put(filepath)

    def _worker(self):

        while not self.stop_event.is_set():

            try:

                filepath = self.queue.get(timeout=0.5)

            except Empty:

                continue

            try:

                # 等待檔案穩定
                time.sleep(1)

                self.callback(filepath)

            finally:

                self.pending.discard(filepath)

                self.queue.task_done()