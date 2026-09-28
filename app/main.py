import time

from config_loader import ConfigLoader
from logger import Logger
from sync_engine import SyncEngine

CONFIG = r"C:\AI_SYNC_ENTERPRISE_V2\config\config.json"


def main():

    config = ConfigLoader(CONFIG).load()

    logger = Logger(config["log_folder"])

    logger.system("AI_SYNC Enterprise Started")

    engine = SyncEngine(
        config["source_folder"],
        config["backup_folder"],
        logger
    )

    engine.start()

    print("=" * 40)
    print(config["project_name"])
    print("=" * 40)
    print("Config Loaded Successfully")
    print("Logger Started")
    print("Sync Engine Started")
    print()
    print("Source :", config["source_folder"])
    print("Backup :", config["backup_folder"])
    print("Logs   :", config["log_folder"])
    print()
    print("Monitoring C:\\WORK ...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.system("AI_SYNC Enterprise Stopped")
        engine.stop()
        print("Stopped")


if __name__ == "__main__":
    main()