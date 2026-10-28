"""Phase 4 batch 4 recovery inventory tests: no changes to files or state."""
import pytest

from app.bidirectional_simulator import TwoFolderSimulator, digest
from app.recovery_inspector_r53c6 import inspect_recovery
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    db = tmp_path / "state" / "sync.db"
    return TwoFolderSimulator(laptop, home, db), laptop, home


def test_inspector_reports_displaced_backup_without_unlock(tmp_path, monkeypatch):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    def stop(*args):
        raise RuntimeError("stop before acknowledgement")
    monkeypatch.setattr(sim.state, "finish_transfer", stop)
    with pytest.raises(RuntimeError, match="stop before"):
        sim.reconcile()
    before_pending = sim.state.pending_transfers()
    before_intents = sim.state.replacement_intents()
    before_baseline = sim.state.baseline("A101.dwg")
    report = inspect_recovery(sim)
    assert report["mode"] == "READ_ONLY"
    assert report["record_count"] == 1
    row = report["records"][0]
    assert row["status"] == "MANUAL_REVIEW_REQUIRED"
    assert row["relative_path"] == "A101.dwg"
    assert row["pending_sha256"] == digest(a)
    assert row["laptop_sha256"] == digest(a)
    assert row["home_sha256"] == digest(b)
    assert len(row["backups"]) == 1
    assert row["backups"][0]["sha256"] == digest(
        next(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    )
    assert sim.state.pending_transfers() == before_pending
    assert sim.state.replacement_intents() == before_intents
    assert sim.state.baseline("A101.dwg") == before_baseline
    with pytest.raises(RuntimeError, match="manual recovery"):
        sim.reconcile()


def test_inspector_flags_missing_backup_and_mismatched_content(tmp_path):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    sim.state.stage_transfer("A101.dwg", "laptop_to_home", digest(a))
    sim.state.mark_replacement_intent("A101.dwg", digest(a))
    a.write_bytes(b"unexpected-laptop")
    b.write_bytes(b"unexpected-home")
    before = (a.read_bytes(), b.read_bytes(), sim.state.pending_transfers())
    report = inspect_recovery(sim)
    row = report["records"][0]
    assert "replacement_backup_missing_or_not_visible" in row["issues"]
    assert "expected_content_absent" in row["issues"]
    assert (a.read_bytes(), b.read_bytes(), sim.state.pending_transfers()) == before


def test_inspector_empty_state(tmp_path):
    sim, laptop, home = roots(tmp_path)
    assert inspect_recovery(sim) == {
        "mode": "READ_ONLY", "record_count": 0, "records": []
    }


def test_inspector_flags_orphan_intent(tmp_path):
    sim, laptop, home = roots(tmp_path)
    sim.state.mark_replacement_intent("A101.dwg", "deadbeef")
    row = inspect_recovery(sim)["records"][0]
    assert "orphan_replacement_intent" in row["issues"]
    assert "intent_digest_mismatch" in row["issues"]
