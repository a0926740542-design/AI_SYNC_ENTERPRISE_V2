"""R5.3-C6 phase 4 batch 9: Windows write-exclusion handles.

Hold READ handles with FILE_SHARE_READ throughout the final digest and SQLite
commit. This rejects cooperating Windows writers but does not protect against
rename/delete, non-cooperating filesystem changes, or power loss. Simulation only.
"""
import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def hold_read_only_no_writers(paths):
    """Prevent normal Windows write opens until the caller completes its commit."""
    paths = [Path(p) for p in paths]
    if os.name != "nt":
        # On non-Windows, no equivalent Windows share-mode guarantee.
        yield
        return
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel32.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    invalid = ctypes.c_void_p(-1).value
    with contextlib.ExitStack() as stack:
        for path in sorted(paths, key=lambda p: str(p).lower()):
            # GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL.
            # FILE_SHARE_READ allows Python SHA256 reads but excludes write opens.
            handle = create(str(path), 0x80000000, 0x00000001,
                            None, 3, 0x80, None)
            if handle is None or handle == invalid:
                raise RuntimeError("Recovery DWG is locked or unavailable: " + str(path))
            stack.callback(close, handle)
        yield
