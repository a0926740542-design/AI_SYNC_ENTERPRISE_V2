"""Atomic backup replacement and exactly-one previous version per change."""
import filecmp
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from app.process_lock import locked

class FileCopier:
    def __init__(self, backup_folder, source_folder=None, logger=None, version_folder=None):
        self.backup_folder = Path(backup_folder).resolve()
        self.source_folder = Path(source_folder).resolve() if source_folder else None
        self.version_folder = Path(version_folder).resolve() if version_folder else None
        self.logger = logger
        if self.source_folder and (self.source_folder == self.backup_folder or self.source_folder in self.backup_folder.parents or self.backup_folder in self.source_folder.parents):
            raise ValueError('Source and backup must not overlap')
        if self.version_folder and (self.version_folder == self.backup_folder or self.version_folder in self.backup_folder.parents or self.backup_folder in self.version_folder.parents or (self.source_folder and (self.version_folder == self.source_folder or self.version_folder in self.source_folder.parents or self.source_folder in self.version_folder.parents))):
            raise ValueError('Version directory must be separate from source and backup')

    def copy(self, source_file):
        source = Path(source_file).resolve()
        if not source.is_file():
            return False
        relative = source.relative_to(self.source_folder) if self.source_folder else Path(source.name)
        destination = self.backup_folder / relative
        if source == destination or destination in source.parents:
            raise ValueError('Source and backup must be separate')
        destination.parent.mkdir(parents=True, exist_ok=True)
        # The lock spans compare, version snapshot and atomic replacement.
        # It also protects direct FileCopier calls from other processes.
        with locked('file:' + str(destination).casefold(), timeout=30):
            for attempt in range(3):
                temporary = None
                try:
                    fd, tmp = tempfile.mkstemp(prefix='.ai_sync_', suffix='.tmp', dir=destination.parent)
                    os.close(fd)
                    temporary = Path(tmp)
                    shutil.copy2(source, temporary)
                    if destination.is_file() and filecmp.cmp(temporary, destination, shallow=False):
                        return True
                    if destination.exists() and not destination.is_file():
                        raise ValueError(f'Backup destination is not a file: {destination}')
                    if destination.is_file() and self.version_folder:
                        version_dir = self.version_folder / relative.parent
                        version_dir.mkdir(parents=True, exist_ok=True)
                        version_name = f'{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid.uuid4().hex[:8]}_{relative.name}'
                        version_path = version_dir / version_name
                        shutil.copy2(destination, version_path)
                        if self.logger:
                            self.logger.info(f'VERSION : {relative} -> {version_path}')
                    os.replace(temporary, destination)
                    temporary = None
                    if self.logger:
                        self.logger.info(f'SYNC : {relative}')
                    return True
                except (PermissionError, OSError):
                    if attempt == 2:
                        raise
                    time.sleep(0.3 * (attempt + 1))
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        return False
