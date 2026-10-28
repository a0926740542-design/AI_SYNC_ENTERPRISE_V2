"""Batch 8: deterministic external-write injections during closure.

These tests only touch pytest temporary simulation roots. The final
check-to-SQLite-commit interval is NOT atomic and remains unsafe for production.
"""
import pytest

import app.recovery_closure_r53c6 as closure
from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_review_r53c6 import prepare_review
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def setup_pending(tmp_path, monkeypatch):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    sim = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    with monkeypatch.context() as patch:
        def crash(*args):
            raise RuntimeError("simulated interrupted replacement")
        patch.setattr(sim.state, "finish_transfer", crash)
        with pytest.raises(RuntimeError, match="interrupted replacement"):
            sim.reconcile()
    backup = next(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    return sim, a, b, backup


def finish(sim, fingerprint):
    return closure.close_verified_replacement(
        sim, "A101.dwg", fingerprint, "engineer", "verified offline test"
    )


@pytest.mark.parametrize("target", ["laptop", "home", "backup"])
def test_external_write_during_audit_flush_blocks_closure(tmp_path, monkeypatch, target):
    sim, a, b, backup = setup_pending(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    victim = {"laptop": a, "home": b, "backup": backup}[target]
    original_fsync = closure.os.fsync
    called = [False]
    def injected_fsync(fd):
        original_fsync(fd)
        if not called[0]:
            called[0] = True
            victim.write_bytes(b"external edit after audit")
    monkeypatch.setattr(closure.os, "fsync", injected_fsync)
    with pytest.raises(RuntimeError, match="changed after audit write"):
        finish(sim, fingerprint)
    assert called[0]
    assert sim.state.pending_transfers()
    assert sim.state.replacement_intents()
    assert victim.read_bytes() == b"external edit after audit"


def test_successful_closure_still_works_after_second_verification(tmp_path, monkeypatch):
    sim, a, b, backup = setup_pending(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    assert finish(sim, fingerprint)["status"] == "CLOSED"
    assert sim.state.pending_transfers() == []
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (b"new", b"new", b"old")
