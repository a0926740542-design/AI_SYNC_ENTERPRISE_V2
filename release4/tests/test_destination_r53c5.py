"""R5.3-C5 destination safety regressions on isolated test folders."""
import os
import pytest
from app.bidirectional_simulator import TwoFolderSimulator, digest
from app.destination_safety_r53c5 import destination_preflight


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


@pytest.mark.skipif(os.name != "nt", reason="Windows share-mode test")
def test_locked_destination_rejected_without_overwrite(tmp_path):
    import ctypes
    from ctypes import wintypes
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel32.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    handle = create(str(b), 0x80000000, 0, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value
    try:
        with pytest.raises(PermissionError):
            sim.reconcile()
    finally:
        close(handle)
    assert b.read_bytes() == b"old"
    assert sim.state.pending_transfers() == []
    assert sim.reconcile()["copied"] == [("laptop_to_home", "A101.dwg")]
    assert b.read_bytes() == b"new"


def test_destination_preflight_allows_unlocked_file(tmp_path):
    target = tmp_path / "A101.dwg"
    target.write_bytes(b"original")
    with destination_preflight(target):
        assert target.read_bytes() == b"original"


def test_destination_change_after_preflight_is_rejected(tmp_path, monkeypatch):
    import app.bidirectional_simulator as module
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    original = module.digest
    reads = {"n": 0}
    def inject(path):
        if str(path) == str(b):
            reads["n"] += 1
            if reads["n"] == 2:
                b.write_bytes(b"third-party-update")
        return original(path)
    monkeypatch.setattr(module, "digest", inject)
    with pytest.raises(RuntimeError, match="Destination changed"):
        sim.reconcile()
    assert b.read_bytes() == b"third-party-update"
    assert sim.state.pending_transfers()
