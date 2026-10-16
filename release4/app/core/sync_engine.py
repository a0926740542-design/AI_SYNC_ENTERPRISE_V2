"""Coordinate observer, router, worker, and copier."""
from pathlib import Path
from app.file_copier import FileCopier
from app.core.worker_pool import WorkerPool
from app.core.event_router import EventRouter
from app.core.watchdog_handler import WatchdogHandler
from app.core.observer_manager import ObserverManager

class SyncEngine:
    def __init__(self, source_folder, backup_folder, logger=None, version_folder=None):
        self.source_folder = Path(source_folder).resolve()
        self.backup_folder = Path(backup_folder).resolve()
        if self.source_folder == self.backup_folder or self.source_folder in self.backup_folder.parents or self.backup_folder in self.source_folder.parents:
            raise ValueError('Source and backup directories must not overlap')
        self.logger = logger
        self.version_folder = Path(version_folder).resolve() if version_folder else None
        self._build_components()

    def _build_components(self):
        self.file_copier = FileCopier(self.backup_folder, self.source_folder, self.logger, self.version_folder)
        self.worker_pool = WorkerPool(self.file_copier.copy, logger=self.logger)
        self.event_router = EventRouter(self.worker_pool)
        self.watchdog_handler = WatchdogHandler(self.event_router)
        self.observer_manager = ObserverManager()
        self.observer_manager.schedule(self.watchdog_handler, self.source_folder, recursive=True)

    def start(self):
        if self.running:
            return
        if not self.source_folder.is_dir():
            raise FileNotFoundError(f'Source directory missing: {self.source_folder}')
        self.backup_folder.mkdir(parents=True, exist_ok=True)
        self.worker_pool.start()
        try:
            self.observer_manager.start()
        except Exception:
            self.worker_pool.stop()
            raise

    def stop(self):
        self.observer_manager.stop()
        self.worker_pool.stop()

    @property
    def running(self):
        return self.observer_manager.running
