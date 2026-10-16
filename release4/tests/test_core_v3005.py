import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from app.core.event_router import EventRouter
from app.core.worker_pool import WorkerPool
from app.core.sync_engine import SyncEngine
class CoreTests(unittest.TestCase):
    def test_worker_and_router_deduplicate(self):
        received = []
        worker = WorkerPool(received.append, settle_seconds=0.15)
        worker.start()
        with tempfile.TemporaryDirectory() as td:
            p = str(Path(td) / 'test.txt')
            router = EventRouter(worker)
            event = SimpleNamespace(is_directory=False, event_type='created', src_path=p)
            self.assertTrue(router.route(event))
            self.assertTrue(router.route(event))
        time.sleep(0.35)
        worker.stop()
        self.assertEqual(len(received), 1)
    def test_nested_file_sync(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'source'
            backup = Path(td) / 'backup'
            source.mkdir()
            engine = SyncEngine(source, backup)
            engine.start()
            try:
                nested = source / 'TEST'
                nested.mkdir()
                target = nested / 'A001.txt'
                target.write_text('test', encoding='utf-8')
                output = backup / 'TEST' / 'A001.txt'
                for _ in range(80):
                    if output.exists() and output.read_text(encoding='utf-8') == 'test': break
                    time.sleep(0.1)
                self.assertTrue(output.exists())
                self.assertEqual(output.read_text(encoding='utf-8'), 'test')
            finally:
                engine.stop()
