"""R5.3-C6 phase 4 crash-recovery guard tests (isolated roots only)."""
import pytest
from app.bidirectional_simulator import TwoFolderSimulator
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    database = tmp_path / "state" / "sync.db"
    return TwoFolderSimulator(laptop, home, database), laptop, home, database


def test_crash_after_replacement_blocks_automatic_acknowledgement(tmp_path, monkeypatch):
    sim, laptop, home, db = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")

    def simulated_crash(*args):
        raise RuntimeError("simulated crash before database commit")

    monkeypatch.setattr(sim.state, "finish_transfer", simulated_crash)
    with pytest.raises(RuntimeError, match="simulated crash"):
        sim.reconcile()
    assert a.read_bytes() == b"new"
    assert b.read_bytes() == b"new"
    assert len(list(home.glob(BACKUP_PREFIX + "*A101.dwg"))) == 1
    restarted = TwoFolderSimulator(laptop, home, db)
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()
    assert restarted.state.pending_transfers()
    assert b.read_bytes() == b"new"


def test_pending_first_install_without_backup_can_recover(tmp_path, monkeypatch):
    sim, laptop, home, db = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"new")

    def simulated_crash(*args):
        raise RuntimeError("simulated crash before database commit")

    monkeypatch.setattr(sim.state, "finish_transfer", simulated_crash)
    with pytest.raises(RuntimeError, match="simulated crash"):
        sim.reconcile()
    assert b.read_bytes() == b"new"
    restarted = TwoFolderSimulator(laptop, home, db)
    assert restarted.reconcile()["copied"] == []
    assert restarted.state.pending_transfers() == []
    assert restarted.state.baseline("A101.dwg") is not None
