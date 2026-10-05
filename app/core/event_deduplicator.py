"""
event_deduplicator.py
AI_SYNC Enterprise V3

負責：
- 過濾短時間內重複事件
"""

import time


class EventDeduplicator:

    def __init__(self, interval=3.0):

        self.interval = interval

        self.last_events = {}

    def should_process(self, filepath):

        now = time.time()

        last = self.last_events.get(filepath)

        if last is not None:

            if now - last < self.interval:
                return False

        self.last_events[filepath] = now

        return True