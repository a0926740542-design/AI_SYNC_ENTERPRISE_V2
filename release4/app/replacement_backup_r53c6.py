"""R5.3-C6 simulation-only replacement with recoverable displaced-file backup.

On Windows ReplaceFileW swaps the staged file and retains the *actual* file
that was displaced, even if it changed after the last SHA-256 check.
Backups live beside the target with a reserved name and must never be synced.
This preserves bytes; it does not prevent a last-moment concurrent overwrite.
"""
import ctypes
import os
from pathlib import Path
import shutil
import uuid


BACKUP_PREFIX = ".r53c6-displaced-"


def replace_with_backup(staged, target):
    staged, target = Path(staged), Path(target)
    if not target.is_file():
        raise RuntimeError("Destination disappeared before replacement")
    backup = target.with_name(BACKUP_PREFIX + uuid.uuid4().hex + "-" + target.name)
    if os.name == "nt":
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        replace = kernel32.ReplaceFileW
        replace.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                            wintypes.LPCWSTR, wintypes.DWORD,
                            wintypes.LPVOID, wintypes.LPVOID]
        replace.restype = wintypes.BOOL
        if not replace(str(target), str(staged), str(backup), 0, None, None):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        # Test-only fallback. This copy/replace sequence is NOT atomic.
        shutil.copy2(target, backup)
        os.replace(staged, target)
    return backup
