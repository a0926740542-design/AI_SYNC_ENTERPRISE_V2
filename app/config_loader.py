import json
from pathlib import Path


class ConfigLoader:

    def __init__(self, config_path):
        self.config_path = Path(config_path)

    def load(self):

        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}"
            )

        with open(
            self.config_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)