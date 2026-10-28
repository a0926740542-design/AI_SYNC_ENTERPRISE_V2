"""R5.3-C6 phase 3: detect late writes using the displaced-file backup.

These tests prove post-replacement detection and preservation, NOT prevention.
"""
import pytest
import app.bidirectional_simulator as module
from app.bidirectional_simulator import TwoFolderSimulator
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


def test_late_destination_write_detected_and_preserved(tmp_path, monkeypatch):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"baseline")
    sim.reconcile()
    a.write_bytes(b"source-new")
    original = module.replace_with_backup

    def late_write(staged, target):
        # Simulates another process writing after final digest, before ReplaceFileW.
        b.write_bytes(b"third-party-late-write")
        return original(staged, target)

    monkeypatch.setattr(module, "replace_with_backup", late_write)
    with pytest.raises(RuntimeError, match="Late destination change detected"):
        sim.reconcile()
    backups = list(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"third-party-late-write"
    assert a.read_bytes() == b"source-new"
    assert b.read_bytes() == b"source-new"
    assert sim.state.pending_transfers()


def test_normal_replacement_does_not_raise_late_change(tmp_path):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"baseline")
    sim.reconcile()
    a.write_bytes(b"updated")
    assert sim.reconcile()["copied"] == [("laptop_to_home", "A101.dwg")]
    assert b.read_bytes() == b"updated"
    assert sim.state.pending_transfers() == []
