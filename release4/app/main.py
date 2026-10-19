import os
import time
from pathlib import Path
from app.config_loader import ConfigLoader
from app.logger import Logger
from app.core.sync_engine import SyncEngine
from app.process_lock import ProcessLock, LockBusy

CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'config.json'

def main():
    config = ConfigLoader(CONFIG).load()
    logger = Logger(config['log_folder'])
    key = '|'.join(str(Path(config[name]).resolve()).casefold() for name in
                   ('source_folder', 'backup_folder', 'version_folder'))
    guard = ProcessLock('instance:' + key)
    try:
        guard.acquire()
    except LockBusy as exc:
        message = f'AI_SYNC already running for these folders; PID={os.getpid()}; {exc}'
        logger.error(message)
        print(message)
        return 2
    engine = None
    try:
        engine = SyncEngine(config['source_folder'], config['backup_folder'], logger, config.get('version_folder'))
        engine.start()
        logger.system(f'AI_SYNC Enterprise Started PID={os.getpid()}')
        print(config.get('project_name', 'AI_SYNC Enterprise'), flush=True)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping...')
    finally:
        try:
            if engine is not None:
                engine.stop()
            logger.system(f'AI_SYNC Enterprise Stopped PID={os.getpid()}')
        finally:
            guard.release()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
