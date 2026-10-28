"""Batch 9: Windows write-exclusion during verified recovery closure."""
import os

import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_review_r53c6 import prepare_review
from app.recovery_closure_r53c6 import close_verified_replacement
from app.recovery_windows_guard_r53c6 import hold_read_only_no_writers
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def scenario(tmp_path, monkeypatch):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    sim = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    with monkeypatch.context() as patch:
        def interrupt(*args):
            raise RuntimeError("stop")
        patch.setattr(sim.state, "finish_transfer", interrupt)
        with pytest.raises(RuntimeError, match="stop"):
            sim.reconcile()
    return sim, a, b, next(home.glob(BACKUP_PREFIX + "*A101.dwg"))


@pytest.mark.skipif(os.name != "nt", reason="Windows file sharing semantics")
def test_windows_guard_denies_writer_and_allows_hashing(tmp_path):
    from app.bidirectional_simulator import digest
    a = tmp_path / "A101.dwg"
    a.write_bytes(b"test")
    with hold_read_only_no_writers([a]):
        assert digest(a)
        with pytest.raises(PermissionError):
            a.write_bytes(b"overwrite")
    assert a.read_bytes() == b"test"
    a.write_bytes(b"after release")


@pytest.mark.skipif(os.name != "nt", reason="Windows file sharing semantics")
def test_windows_existing_writer_denies_guard(tmp_path):
    import ctypes
    from ctypes import wintypes
    a = tmp_path / "A101.dwg"
    a.write_bytes(b"test")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel32.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    handle = create(str(a), 0x40000000, 0, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value
    try:
        with pytest.raises(RuntimeError, match="locked or unavailable"):
            with hold_read_only_no_writers([a]):
                pass
    finally:
        close(handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows file sharing semantics")
def test_windows_guard_remains_active_during_sqlite_commit(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    original = sim.state.finish_transfer
    def check_locked(*args):
        for path in (a, b, backup):
            with pytest.raises(PermissionError):
                path.write_bytes(b"unexpected")
        return original(*args)
    monkeypatch.setattr(sim.state, "finish_transfer", check_locked)
    result = close_verified_replacement(sim, "A101.dwg", fingerprint, "engineer", "verified")
    assert result["status"] == "CLOSED"
    assert not sim.state.pending_transfers()
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (b"new", b"new", b"old")


def test_guard_does_not_change_successful_closure(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    result = close_verified_replacement(sim, "A101.dwg", fingerprint, "engineer", "verified")
    assert result["status"] == "CLOSED"
    assert not sim.state.pending_transfers()
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (b"new", b"new", b"old")
