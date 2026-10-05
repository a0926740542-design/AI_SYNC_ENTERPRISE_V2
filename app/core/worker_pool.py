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

    # -------------------------
    # Public API
    # -------------------------

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

    def pending_jobs(self):

        return self.tasks.qsize()

    # -------------------------
    # Private
    # -------------------------

    def _run(self):

        while self.running:

            filepath = None

            # 等待工作
            try:

                filepath = self.tasks.get(timeout=0.5)

            except queue.Empty:

                continue

            # 執行工作
            try:

                self.callback(filepath)

            except Exception as ex:

                self._handle_error(filepath, ex)

            finally:

                if filepath is not None:
                    self.tasks.task_done()

    def _handle_error(self, filepath, exception):

        print("=" * 60)
        print("[Worker Error]")
        print(f"File : {filepath}")
        print(f"Error: {exception}")
        print("=" * 60)