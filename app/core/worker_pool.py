"""
worker_pool.py
AI_SYNC Enterprise V3

負責：
- 背景 Worker
- Queue 消費
- 執行工作

不負責：
- Watchdog
- Logger
- Copy Logic
"""

import queue
import threading


class WorkerPool:

    def __init__(self, callback):

        self.callback = callback

        self.tasks = queue.Queue()

        self.running = False

        self.worker = None

    def start(self):

        if self.running:
            return

        self.running = True

        self.worker = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.worker.start()

    def stop(self):

        self.running = False

        if self.worker:
            self.worker.join()

    def submit(self, filepath):

        self.tasks.put(filepath)

    def _run(self):

        while self.running:

            try:

                filepath = self.tasks.get(timeout=0.5)

            except queue.Empty:
                continue

            try:

                self.callback(filepath)

            finally:

                self.tasks.task_done()