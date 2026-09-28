from config_loader import ConfigLoader

CONFIG = r"C:\AI_SYNC_ENTERPRISE_V2\config\config.json"


def main():

    config = ConfigLoader(CONFIG).load()

    print("=" * 40)
    print(config["project_name"])
    print("=" * 40)
    print("Config Loaded Successfully")
    print()
    print("Source :", config["source_folder"])
    print("Backup :", config["backup_folder"])
    print("Version:", config["version_folder"])
    print("Logs   :", config["log_folder"])


if __name__ == "__main__":
    main()