"""
event_router.py
AI_SYNC Enterprise V3

負責：
- 接收 Watchdog Event
- 過濾資料夾事件
- 將事件送入 Queue

不負責：
- Copy
- Logger
- Version
"""

from pathlib import Path


class EventRouter:

    def __init__(self, queue):

        self.queue = queue

    def route(self, event):

        if event.is_directory:
            return

        filepath = str(Path(event.src_path).resolve())

        self.queue.put(filepath)