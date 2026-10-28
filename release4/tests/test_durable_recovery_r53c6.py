"""C6 phase 4 batch 2: durable replacement intent survives backup loss."""
import pytest
from app.bidirectional_simulator import TwoFolderSimulator, digest
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    db = tmp_path / "state" / "sync.db"
    return TwoFolderSimulator(laptop, home, db), laptop, home, db


def test_missing_displaced_backup_still_blocks_recovery(tmp_path, monkeypatch):
    sim, laptop, home, db = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    def crash(*args):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(sim.state, "finish_transfer", crash)
    with pytest.raises(RuntimeError, match="simulated crash"):
        sim.reconcile()
    backups = list(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    assert len(backups) == 1
    backups[0].unlink()
    restarted = TwoFolderSimulator(laptop, home, db)
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()
    assert restarted.state.pending_transfers()
    assert restarted.state.replacement_intents()["A101.dwg"] == digest(a)
    assert a.read_bytes() == b"new"
    assert b.read_bytes() == b"new"


def test_pending_replacement_intent_with_mismatched_target_fails_closed(tmp_path):
    sim, laptop, home, db = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    sim.state.stage_transfer("A101.dwg", "laptop_to_home", digest(a))
    sim.state.mark_replacement_intent("A101.dwg", digest(a))
    b.write_bytes(b"unexpected-third-party-edit")
    restarted = TwoFolderSimulator(laptop, home, db)
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()
    assert b.read_bytes() == b"unexpected-third-party-edit"
    assert restarted.state.baseline("A101.dwg") != digest(a)
    assert restarted.state.pending_transfers()


def test_successful_replacement_clears_durable_intent(tmp_path):
    sim, laptop, home, db = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    assert sim.reconcile()["copied"] == [("laptop_to_home", "A101.dwg")]
    assert sim.state.replacement_intents() == {}
    assert sim.state.pending_transfers() == []
