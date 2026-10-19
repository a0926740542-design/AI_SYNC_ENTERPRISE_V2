"""Windows inter-process locks, with a POSIX fallback for test environments."""
import hashlib
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import msvcrt
except ImportError:
    msvcrt = None
    import fcntl

class LockBusy(RuntimeError):
    pass

class ProcessLock:
    def __init__(self, key, directory=None):
        directory = Path(directory or (Path(tempfile.gettempdir()) / "ai_sync_locks"))
        directory.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
        self.path = directory / (digest + ".lock")
        self.handle = None

    def acquire(self, timeout=0):
        if self.handle is not None:
            raise RuntimeError("Lock already acquired")
        handle = open(self.path, "a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + timeout
            while True:
                try:
                    handle.seek(0)
                    if msvcrt is not None:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (OSError, IOError):
                    if time.monotonic() >= deadline:
                        raise LockBusy(f"Another AI_SYNC instance holds lock: {self.path}")
                    time.sleep(0.05)
            self.handle = handle
            return self
        except BaseException:
            handle.close()
            raise

    def release(self):
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if msvcrt is not None:
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()

@contextmanager
def locked(key, timeout=30):
    lock = ProcessLock(key)
    lock.acquire(timeout=timeout)
    try:
        yield
    finally:
        lock.release()
