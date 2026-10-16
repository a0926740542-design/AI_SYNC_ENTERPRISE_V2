import time
from pathlib import Path
from app.config_loader import ConfigLoader
from app.logger import Logger
from app.core.sync_engine import SyncEngine

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'config.json'

def main():
    config = ConfigLoader(CONFIG).load()
    logger = Logger(config['log_folder'])
    engine = SyncEngine(config['source_folder'], config['backup_folder'], logger, config.get('version_folder'))
    try:
        engine.start()
        logger.system('AI_SYNC Enterprise Started')
        print(config.get('project_name', 'AI_SYNC Enterprise'))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping...')
    finally:
        engine.stop()
        logger.system('AI_SYNC Enterprise Stopped')

if __name__ == '__main__':
    main()
