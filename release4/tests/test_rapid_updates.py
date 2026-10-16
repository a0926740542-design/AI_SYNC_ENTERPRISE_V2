import time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from app.core.worker_pool import WorkerPool
from app.core.event_router import EventRouter
def test_last_write_survives_rapid_events():
    with TemporaryDirectory() as td:
        path = Path(td) / 'A004.txt'
        copied = []
        def callback(p): copied.append(Path(p).read_text(encoding='utf-8'))
        worker = WorkerPool(callback, settle_seconds=0.15)
        worker.start()
        router = EventRouter(worker)
        for i in range(1, 11):
            path.write_text(str(i), encoding='utf-8')
            assert router.route(SimpleNamespace(is_directory=False, event_type='modified', src_path=str(path)))
            time.sleep(0.025)
        time.sleep(0.4)
        worker.stop()
        assert copied[-1] == '10'
        assert copied == ['10']
