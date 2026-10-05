"""
sync_engine.py
AI_SYNC Enterprise V3

負責：
- 建立所有 Core 元件
- 管理整個同步引擎生命週期

不負責：
- Copy Logic
- Queue Logic
- Watchdog Event
"""

from app.file_copier import FileCopier
from app.core.worker_pool import WorkerPool
from app.core.event_router import EventRouter
from app.core.watchdog_handler import WatchdogHandler
from app.core.observer_manager import ObserverManager


class SyncEngine:

    def __init__(self, source_folder, backup_folder):

        self.source_folder = source_folder
        self.backup_folder = backup_folder

        # Core Components
        self.file_copier = FileCopier(backup_folder)

        self.worker_pool = WorkerPool(
            self.file_copier.copy
        )

        self.event_router = EventRouter(
            self.worker_pool
        )

        self.watchdog_handler = WatchdogHandler(
            self.event_router
        )

        self.observer_manager = ObserverManager(
            source_folder,
            self.watchdog_handler
        )