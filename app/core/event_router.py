"""
event_router.py
AI_SYNC Enterprise V3

負責：
- 接收 Watchdog Event
- 過濾資料夾事件
- 過濾重複事件
- 將事件送入 WorkerPool

不負責：
- Copy
- Logger
- Version
- Audit
"""

from pathlib import Path

from app.core.event_deduplicator import EventDeduplicator


class EventRouter:

    def __init__(self, worker_pool):

        self.worker_pool = worker_pool
        self.deduplicator = EventDeduplicator()

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def route(self, event):

        # 忽略資料夾
        if event.is_directory:
            return

        filepath = str(Path(event.src_path).resolve())

        print(f"[Router] {filepath}")

        # 去除短時間重複事件
        if not self.deduplicator.should_process(filepath):

            print(f"[Deduplicated] {filepath}")
            return

        print(f"[Accepted] {filepath}")

        self.worker_pool.submit(filepath)