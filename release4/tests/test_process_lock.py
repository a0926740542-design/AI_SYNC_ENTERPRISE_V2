import multiprocessing
import time
from app.file_copier import FileCopier
from app.process_lock import ProcessLock, LockBusy

def _copy_worker(backup, source, version, file, gate):
    gate.wait()
    FileCopier(backup, source, version_folder=version).copy(file)

def test_two_processes_do_not_duplicate_versions(tmp_path):
    source, backup, version = (tmp_path / n for n in ('source', 'backup', 'version'))
    source.mkdir()
    target = source / 'A.txt'
    target.write_text('old', encoding='utf-8')
    copier = FileCopier(backup, source, version_folder=version)
    assert copier.copy(target)
    target.write_text('new', encoding='utf-8')
    ctx = multiprocessing.get_context('spawn')
    gate = ctx.Event()
    jobs = [ctx.Process(target=_copy_worker, args=(backup, source, version, target, gate)) for _ in range(3)]
    for job in jobs:
        job.start()
    gate.set()
    for job in jobs:
        job.join(15)
        assert job.exitcode == 0
    assert (backup / 'A.txt').read_text(encoding='utf-8') == 'new'
    versions = list(version.glob('*A.txt'))
    assert len(versions) == 1
    assert versions[0].read_text(encoding='utf-8') == 'old'

def test_single_instance_lock_rejects_second_process(tmp_path):
    lock1 = ProcessLock('instance-test', directory=tmp_path)
    lock2 = ProcessLock('instance-test', directory=tmp_path)
    lock1.acquire()
    try:
        try:
            lock2.acquire()
            assert False, 'Second lock should fail'
        except LockBusy:
            pass
    finally:
        lock1.release()
    lock2.acquire()
    lock2.release()
