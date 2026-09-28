import shutil
from pathlib import Path


class FileCopier:
    """
    Enterprise File Copier

    負責：
    - 建立目的資料夾
    - 複製檔案
    - 回傳成功 / 失敗

    不負責：
    - Logger
    - Version
    - Audit
    """

    def __init__(self, backup_folder):
        self.backup_folder = Path(backup_folder)

    def copy(self, source_file):

        source = Path(source_file)

        if not source.exists():
            return False

        destination = self.backup_folder / source.name

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(source, destination)

        return True