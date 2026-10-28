"""R5.3-C4 Windows DWG write/lock regression tests (simulation roots only)."""
import os
import pytest

from app.bidirectional_simulator import TwoFolderSimulator, digest
from app.sync_safety_r53c3 import stable_file


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


@pytest.mark.skipif(os.name != "nt", reason="Windows CreateFile share-mode test")
def test_windows_exclusive_writer_blocks_source(tmp_path):
    import ctypes
    from ctypes import wintypes
    path = tmp_path / "A101.dwg"
    path.write_bytes(b"writer-active")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0x40000000, 0, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    try:
        with pytest.raises(RuntimeError, match="locked"):
            stable_file(path, interval=0)
    finally:
        kernel32.CloseHandle(handle)
    stable_file(path, interval=0)


def test_writer_mutation_during_settle_never_copies(tmp_path, monkeypatch):
    import app.sync_safety_r53c3 as safety
    sim, laptop, home = roots(tmp_path)
    source = laptop / "A101.dwg"
    source.write_bytes(b"partial")
    def writer(_):
        source.write_bytes(b"finished-full-dwg")
    monkeypatch.setattr(safety.time, "sleep", writer)
    with pytest.raises(RuntimeError, match="changed"):
        sim.reconcile()
    assert not (home / "A101.dwg").exists()
    assert sim.state.pending_transfers() == []


def test_source_changes_during_transfer_keeps_destination_and_intent(tmp_path, monkeypatch):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"initial")
    sim.reconcile()
    a.write_bytes(b"next-version")
    original = sim._copy_verified
    def writer_during_copy(source, target, expected_hash, expected_target_hash=None):
        source.write_bytes(b"newer-version")
        return original(source, target, expected_hash, expected_target_hash)
    monkeypatch.setattr(sim, "_copy_verified", writer_during_copy)
    with pytest.raises(RuntimeError, match="Source changed"):
        sim.reconcile()
    assert b.read_bytes() == b"initial"
    assert sim.state.pending_transfers() == [
        ("A101.dwg", "laptop_to_home", digest(b"") if False else __import__("hashlib").sha256(b"next-version").hexdigest())
    ]
