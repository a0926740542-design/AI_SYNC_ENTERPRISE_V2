import shutil
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


IGNORE_EXTENSIONS = {
    ".bak",
    ".sv$",
    ".dwl",
    ".dwl2",
    ".tmp"
}

SYNC_INTERVAL = 2.0


class SyncHandler(FileSystemEventHandler):

    def __init__(self, source_folder, backup_folder, logger):

        self.source = Path(source_folder)
        self.backup = Path(backup_folder)
        self.logger = logger

        self.last_sync = {}

    def on_created(self, event):

        if event.is_directory:
            return

        self.process_event(event.src_path)

    def on_modified(self, event):

        if event.is_directory:
            return

        self.process_event(event.src_path)

    def process_event(self, src_path):

        src = Path(src_path)

        if not self.should_sync(src):
            return

        self.copy_file(src)

    def should_sync(self, src):

        if not src.exists():
            return False

        if src.suffix.lower() in IGNORE_EXTENSIONS:
            return False

        now = time.time()

        last = self.last_sync.get(str(src), 0)

        if now - last < SYNC_INTERVAL:
            return False

        self.last_sync[str(src)] = now

        return True

    def copy_file(self, src):

        try:

            relative = src.relative_to(self.source)

            destination = self.backup / relative

            destination.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            shutil.copy2(src, destination)

            self.logger.info(f"SYNC : {relative}")

        except Exception as e:

            self.logger.error(str(e))


class SyncEngine:

    def __init__(
        self,
        source_folder,
        backup_folder,
        logger
    ):

        self.source_folder = source_folder

        self.observer = Observer()

        self.handler = SyncHandler(
            source_folder,
            backup_folder,
            logger
        )

    def start(self):

        self.observer.schedule(
            self.handler,
            self.source_folder,
            recursive=True
        )

        self.observer.start()

    def stop(self):

        self.observer.stop()
        self.observer.join()