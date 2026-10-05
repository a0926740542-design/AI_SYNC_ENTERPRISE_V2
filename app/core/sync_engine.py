class SyncEngine:

    def __init__(self, source_folder, backup_folder):

        self.source_folder = source_folder
        self.backup_folder = backup_folder

        # -------------------------------------------------
        # Core Components
        # -------------------------------------------------

        self.file_copier = FileCopier(
            backup_folder
        )

        self.worker_pool = WorkerPool(
            self.file_copier.copy
        )

        self.event_router = EventRouter(
            self.worker_pool
        )

        self.watchdog_handler = WatchdogHandler(
            self.event_router
        )

        self.observer_manager = ObserverManager()

        self.observer_manager.schedule(
            self.watchdog_handler,
            self.source_folder,
            recursive=True
        )

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def start(self):

        self.worker_pool.start()

        self.observer_manager.start()

    def stop(self):

        self.observer_manager.stop()

        self.worker_pool.stop()

    @property
    def running(self):

        return self.observer_manager.running