from watchdog.observers import Observer

from event_handler import EventHandler
from queue_manager import QueueManager
from file_copier import FileCopier


class SyncEngine:

    def __init__(self, source_folder, backup_folder, logger):

        self.source_folder = source_folder
        self.logger = logger

        self.copier = FileCopier(backup_folder)

        self.queue = QueueManager(self._process_file)

        self.handler = EventHandler(self.queue)

        self.observer = Observer()

    def start(self):

        self.queue.start()

        self.observer.schedule(
            self.handler,
            self.source_folder,
            recursive=True
        )

        self.observer.start()

        self.logger.system("Sync Engine Started")

    def stop(self):

        self.observer.stop()
        self.observer.join()

        self.queue.stop()

        self.logger.system("Sync Engine Stopped")

    def _process_file(self, filepath):

        ok = self.copier.copy(filepath)

        if ok:
            self.logger.info(f"SYNC : {filepath}")
        else:
            self.logger.error(f"FAILED : {filepath}")