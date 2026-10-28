"""R5.3-C5 destination preflight (simulator only).

A Windows no-sharing handle rejects busy DWGs. The handle must be released
before os.replace, so this does NOT eliminate the final TOCTOU window.
"""
import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def destination_preflight(path):
    path = Path(path)
    if os.name != "nt" or not path.exists():
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
    handle = create(str(path), 0x80000000, 0, None, 3, 0x80, None)
    if handle is None or handle == ctypes.c_void_p(-1).value:
        raise RuntimeError("Destination DWG is locked")
    try:
        yield
    finally:
        close(handle)
