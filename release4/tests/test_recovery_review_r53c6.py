"""R5.3-C6 batch 5: evidence-bound manual review, no implicit unlock."""
import json

import pytest

from app.bidirectional_simulator import TwoFolderSimulator, digest
from app.recovery_review_r53c6 import prepare_review, record_review


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    db = tmp_path / "state" / "sync.db"
    return TwoFolderSimulator(laptop, home, db), laptop, home, db


def pending(sim, laptop, home):
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    sim.state.stage_transfer("A101.dwg", "laptop_to_home", digest(a))
    sim.state.mark_replacement_intent("A101.dwg", digest(a))
    return a, b


def test_review_records_audit_without_clearing_pending(tmp_path):
    sim, laptop, home, db = roots(tmp_path)
    a, b = pending(sim, laptop, home)
    original = (a.read_bytes(), b.read_bytes(), sim.state.pending_transfers(),
                sim.state.replacement_intents(), sim.state.baseline("A101.dwg"))
    review = prepare_review(sim, "A101.dwg")
    entry = record_review(sim, "A101.dwg", review["fingerprint"],
                          "engineer", "HOLD", "Investigate backup")
    assert entry["status"] == "BLOCKED_UNCHANGED"
    audit = db.parent / "sync_recovery_audit.jsonl"
    assert json.loads(audit.read_text(encoding="utf-8").splitlines()[0]) == entry
    assert original == (a.read_bytes(), b.read_bytes(), sim.state.pending_transfers(),
                        sim.state.replacement_intents(), sim.state.baseline("A101.dwg"))
    with pytest.raises(RuntimeError, match="manual recovery"):
        sim.reconcile()


def test_review_rejects_stale_evidence_without_audit(tmp_path):
    sim, laptop, home, db = roots(tmp_path)
    a, b = pending(sim, laptop, home)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    b.write_bytes(b"external edit")
    with pytest.raises(RuntimeError, match="evidence changed"):
        record_review(sim, "A101.dwg", fingerprint, "engineer", "HOLD", "Check")
    assert not (db.parent / "sync_recovery_audit.jsonl").exists()
    assert b.read_bytes() == b"external edit"


@pytest.mark.parametrize("operator,decision,note", [
    ("", "HOLD", "note"),
    ("engineer", "UNLOCK", "note"),
    ("engineer", "HOLD", ""),
])
def test_review_requires_valid_human_decision(tmp_path, operator, decision, note):
    sim, laptop, home, db = roots(tmp_path)
    pending(sim, laptop, home)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    with pytest.raises(ValueError):
        record_review(sim, "A101.dwg", fingerprint, operator, decision, note)
    assert not (db.parent / "sync_recovery_audit.jsonl").exists()


def test_review_requires_existing_pending_record(tmp_path):
    sim, laptop, home, db = roots(tmp_path)
    with pytest.raises(ValueError, match="No unique"):
        prepare_review(sim, "A101.dwg")
