"""Batch 6: manual closure only for fully verified offline replacement."""
import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_review_r53c6 import prepare_review
from app.recovery_closure_r53c6 import close_verified_replacement
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
    original = sim.state.finish_transfer
    def interrupt(*args):
        raise RuntimeError("interrupted after swap")
    monkeypatch.setattr(sim.state, "finish_transfer", interrupt)
    with pytest.raises(RuntimeError, match="interrupted"):
        sim.reconcile()
    monkeypatch.setattr(sim.state, "finish_transfer", original)
    backup = next(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    return sim, a, b, backup


def close(sim, fingerprint):
    return close_verified_replacement(sim, "A101.dwg", fingerprint, "engineer", "Verified both DWGs and backup")


def test_verified_recovery_closes_without_modifying_files(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    evidence = prepare_review(sim, "A101.dwg")
    before = (a.read_bytes(), b.read_bytes(), backup.read_bytes())
    result = close(sim, evidence["fingerprint"])
    assert result["status"] == "CLOSED"
    assert sim.state.pending_transfers() == []
    assert sim.state.replacement_intents() == {}
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == before
    assert sim.reconcile()["status"] == "online"


def test_stale_evidence_blocks_closure(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    b.write_bytes(b"external change")
    with pytest.raises(RuntimeError, match="evidence changed"):
        close(sim, fingerprint)
    assert sim.state.pending_transfers()


def test_missing_or_corrupt_backup_blocks_closure(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    backup.write_bytes(b"corrupted")
    with pytest.raises(RuntimeError, match="evidence changed"):
        close(sim, fingerprint)
    fresh = prepare_review(sim, "A101.dwg")["fingerprint"]
    with pytest.raises(RuntimeError, match="backup verification failed"):
        close(sim, fresh)
    assert sim.state.pending_transfers()


def test_no_authorization_or_double_closure(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    with pytest.raises(ValueError, match="Operator"):
        close_verified_replacement(sim, "A101.dwg", fingerprint, "", "reason")
    assert sim.state.pending_transfers()
    close(sim, fingerprint)
    with pytest.raises(RuntimeError, match="No unique pending"):
        close(sim, fingerprint)
