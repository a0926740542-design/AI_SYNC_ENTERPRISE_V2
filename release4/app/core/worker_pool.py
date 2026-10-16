"""Debounced file-copy worker: each event postpones its path until quiet."""
import logging
import threading
import time
from pathlib import Path
class WorkerPool:
    def __init__(self, callback, logger=None, settle_seconds=0.75):
        self.callback = callback
        self.logger = logger
        self.settle_seconds = settle_seconds
        self._pending = {}
        self._condition = threading.Condition()
        self._thread = None
        self._accepting = False
    @property
    def running(self):
        return self._accepting
    def start(self):
        with self._condition:
            if self._accepting: return
            if self._thread is not None: raise RuntimeError('WorkerPool cannot restart after stop')
            self._accepting = True
            self._thread = threading.Thread(target=self._run, name='AI-SYNC-Worker', daemon=False)
            self._thread.start()
    def submit(self, filepath):
        filepath = str(Path(filepath).resolve())
        with self._condition:
            if not self._accepting: return False
            self._pending[filepath] = time.monotonic() + self.settle_seconds
            self._condition.notify()
            return True
    def pending_jobs(self):
        with self._condition: return len(self._pending)
    def stop(self):
        with self._condition:
            if not self._accepting: return
            self._accepting = False
            self._condition.notify_all()
        self._thread.join()
    def _run(self):
        while True:
            with self._condition:
                while True:
                    if not self._pending:
                        if not self._accepting: return
                        self._condition.wait()
                        continue
                    path, due = min(self._pending.items(), key=lambda item: item[1])
                    remaining = due - time.monotonic()
                    if remaining > 0 and self._accepting:
                        self._condition.wait(remaining)
                        continue
                    del self._pending[path]
                    break
            try:
                self.callback(path)
            except Exception as exc:
                if self.logger: self.logger.error(f'Worker failed: {path}: {exc}')
                else: logging.exception('Worker failed for %s', path)
