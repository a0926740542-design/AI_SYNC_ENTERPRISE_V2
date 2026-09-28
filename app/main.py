from config_loader import ConfigLoader
from logger import Logger

CONFIG = r"C:\AI_SYNC_ENTERPRISE_V2\config\config.json"


def main():

    config = ConfigLoader(CONFIG).load()

    logger = Logger(config["log_folder"])

    logger.system("Logger Started")
    logger.info("System Ready")
    logger.audit("Audit Ready")
    logger.error("Error Test")

    print("=" * 40)
    print(config["project_name"])
    print("=" * 40)
    print("Config Loaded Successfully")
    print("Logger Started")
    print()
    print("Source :", config["source_folder"])
    print("Backup :", config["backup_folder"])
    print("Version:", config["version_folder"])
    print("Logs   :", config["log_folder"])


if __name__ == "__main__":
    main()