"""R5.3-C6 phase 4 batch 12: SQLite failures fail closed.

All writes occur under pytest temporary simulation roots. No production DWGs.
"""
import sqlite3

import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_closure_r53c6 import close_verified_replacement
from app.recovery_review_r53c6 import prepare_review
from app.recovery_audit_status_r53c6 import inspect_closure_requests
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def pending(tmp_path, monkeypatch):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    sim = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    with monkeypatch.context() as patch:
        def interrupted(*args):
            raise RuntimeError("interrupted after swap")
        patch.setattr(sim.state, "finish_transfer", interrupted)
        with pytest.raises(RuntimeError, match="interrupted after swap"):
            sim.reconcile()
    backup = next(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    return sim, a, b, backup


def assert_unchanged(sim, a, b, backup):
    restarted = TwoFolderSimulator(sim.laptop, sim.home, sim.database)
    assert restarted.state.pending_transfers()
    assert restarted.state.replacement_intents()
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (
        b"new", b"new", b"old"
    )
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()


def test_sqlite_exclusive_transaction_blocks_closure_without_clearing_pending(
        tmp_path, monkeypatch):
    sim, a, b, backup = pending(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    # A real second SQLite connection holds an exclusive transaction.
    # Force immediate failure so the test does not wait for the default timeout.
    original = sim.state._connect
    def immediate():
        connection = sqlite3.connect(sim.database, timeout=0)
        return connection
    with sqlite3.connect(sim.database, timeout=0) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")
        monkeypatch.setattr(sim.state, "_connect", immediate)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            close_verified_replacement(
                sim, "A101.dwg", fingerprint, "engineer", "locked database"
            )
    monkeypatch.setattr(sim.state, "_connect", original)
    assert_unchanged(sim, a, b, backup)


def test_sqlite_commit_failure_rolls_back_baseline_and_intent(
        tmp_path, monkeypatch):
    sim, a, b, backup = pending(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    baseline_before = sim.state.baseline("A101.dwg")
    original = sim.state.finish_transfer
    real_connect = sim.state._connect

    class FailingCommitConnection:
        def __init__(self, real):
            self.real = real
        def __enter__(self):
            self.real.__enter__()
            return self
        def __exit__(self, exc_type, exc, tb):
            # Roll back the real transaction after SQL statements are issued.
            self.real.rollback()
            self.real.close()
            raise sqlite3.OperationalError("simulated commit failure")
        def execute(self, *args, **kwargs):
            return self.real.execute(*args, **kwargs)

    def fail_only_during_finish(*args):
        with monkeypatch.context() as patch:
            patch.setattr(sim.state, "_connect",
                          lambda: FailingCommitConnection(real_connect()))
            return original(*args)

    monkeypatch.setattr(sim.state, "finish_transfer", fail_only_during_finish)
    with pytest.raises(sqlite3.OperationalError, match="simulated commit failure"):
        close_verified_replacement(
            sim, "A101.dwg", fingerprint, "engineer", "transaction rollback"
        )
    monkeypatch.setattr(sim.state, "finish_transfer", original)
    assert_unchanged(sim, a, b, backup)
    assert sim.state.baseline("A101.dwg") == baseline_before
    assert inspect_closure_requests(sim)[-1]["status"] == (
        "CLOSURE_REQUEST_PENDING_MANUAL_REVIEW"
    )


def test_corrupted_sqlite_copy_does_not_auto_reinitialize(tmp_path, monkeypatch):
    sim, a, b, backup = pending(tmp_path, monkeypatch)
    original_bytes = sim.database.read_bytes()
    # Damage only the isolated test database; preserve the original for cleanup.
    sim.database.write_bytes(b"not a sqlite database" + original_bytes[:32])
    try:
        with pytest.raises(sqlite3.DatabaseError):
            TwoFolderSimulator(sim.laptop, sim.home, sim.database)
        assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (
            b"new", b"new", b"old"
        )
        assert sim.database.read_bytes().startswith(b"not a sqlite database")
    finally:
        sim.database.write_bytes(original_bytes)


def test_malformed_audit_does_not_claim_closure(tmp_path, monkeypatch):
    sim, a, b, backup = pending(tmp_path, monkeypatch)
    audit = sim.database.parent / (sim.database.stem + "_recovery_audit.jsonl")
    audit.write_text('{"decision": "CLOSE_VERIFIED", invalid}\n', encoding="utf-8")
    rows = inspect_closure_requests(sim)
    assert rows[-1]["status"] == "MALFORMED_AUDIT_MANUAL_REVIEW"
    assert_unchanged(sim, a, b, backup)
