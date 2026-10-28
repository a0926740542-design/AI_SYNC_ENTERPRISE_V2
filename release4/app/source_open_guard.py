"""Conservative Windows file-open check before publishing a staged copy.

An exclusive open rejects files with other open handles (including active writers).
It is a safety gate, not proof of application-level save completion.
"""
import ctypes
import os
from ctypes import wintypes


class SourceBusyError(OSError):
    pass


def assert_exclusively_openable(path):
    if os.name != "nt":
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                       wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    close = kernel32.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    handle = create(str(path), GENERIC_READ, 0, None, OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL, None)
    invalid = ctypes.c_void_p(-1).value
    if handle == invalid or handle is None:
        error = ctypes.get_last_error()
        raise SourceBusyError(f"Source is open, inaccessible, or busy: {path} (WinError {error})")
    close(handle)
