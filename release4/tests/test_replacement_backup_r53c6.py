"""R5.3-C6 phase 2 isolated tests: preserve displaced DWG bytes."""
from pathlib import Path
from app.bidirectional_simulator import TwoFolderSimulator
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


def test_existing_destination_replacement_keeps_original_backup(tmp_path):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"first-version")
    sim.reconcile()
    a.write_bytes(b"second-version")
    assert sim.reconcile()["copied"] == [("laptop_to_home", "A101.dwg")]
    assert b.read_bytes() == b"second-version"
    backups = list(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"first-version"


def test_displaced_backups_are_not_resynchronized(tmp_path):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    sim.reconcile()
    result = sim.reconcile()
    assert result["copied"] == []
    assert not list(laptop.glob(BACKUP_PREFIX + "*"))
    assert len(list(home.glob(BACKUP_PREFIX + "*"))) == 1
