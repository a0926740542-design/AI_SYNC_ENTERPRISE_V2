"""R5.3-C3 simulation-only single-process lock and source stability checks."""
import contextlib
import os
from pathlib import Path
import time


@contextlib.contextmanager
def exclusive_run_lock(path):
    """Non-blocking advisory OS lock; use one shared lock path per pair of roots."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Open without reading the byte Windows may already have locked.
    # A newly created file needs one byte before msvcrt.locking can lock it.
    try:
        with path.open("a+b") as stream:
            if os.name == "nt":
                import msvcrt
                try:
                    if path.stat().st_size == 0:
                        stream.seek(0)
                        stream.write(b"0")
                        stream.flush()
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise RuntimeError("Another simulator reconciliation is running") from exc
                try:
                    yield
                finally:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise RuntimeError("Another simulator reconciliation is running") from exc
                try:
                    yield
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def stable_file(path, interval=0.05):
    """Reject changing files and Windows files not available for exclusive read."""
    path = Path(path)
    before = path.stat()
    time.sleep(interval)
    after = path.stat()
    signature = lambda stat: (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if signature(before) != signature(after):
        raise RuntimeError("Source changed while settling")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel32.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        handle = create(str(path), 0x80000000, 0, None, 3, 0x80, None)
        invalid = ctypes.c_void_p(-1).value
        if handle is None or handle == invalid:
            raise RuntimeError("Source file is locked by another application")
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle(handle)
    if signature(path.stat()) != signature(after):
        raise RuntimeError("Source changed after exclusive-open check")
