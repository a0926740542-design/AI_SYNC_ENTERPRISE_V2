from pathlib import Path
from datetime import datetime


class Logger:

    def __init__(self, log_folder):

        self.log_folder = Path(log_folder)
        self.log_folder.mkdir(parents=True, exist_ok=True)

    def _write(self, filename, level, message):

        logfile = self.log_folder / filename

        with open(
            logfile,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
                f"[{level}] "
                f"{message}\n"
            )

    def info(self, message):
        self._write("transfer.log", "INFO", message)

    def system(self, message):
        self._write("system.log", "SYSTEM", message)

    def error(self, message):
        self._write("error.log", "ERROR", message)

    def audit(self, message):
        self._write("audit.log", "AUDIT", message)