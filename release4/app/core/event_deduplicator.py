import threading
import time
class EventDeduplicator:
    def __init__(self, interval=1.0):
        self.interval = interval
        self.last_events = {}
        self._lock = threading.Lock()
    def should_process(self, filepath):
        now = time.monotonic()
        with self._lock:
            if now - self.last_events.get(filepath, float('-inf')) < self.interval:
                return False
            self.last_events[filepath] = now
            if len(self.last_events) > 10000:
                self.last_events = {p:t for p,t in self.last_events.items() if now-t < self.interval}
            return True
