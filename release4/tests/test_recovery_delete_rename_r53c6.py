"""R5.3-C6 phase 4 batch 10: Windows delete/rename/replace denial.

Only disposable pytest simulation roots are touched. These tests validate
ordinary Windows file operations, not privileged bypasses or power-loss atomicity.
"""
import os

import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_closure_r53c6 import close_verified_replacement
from app.recovery_review_r53c6 import prepare_review
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def pending_replacement(tmp_path, monkeypatch):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    sim = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    with monkeypatch.context() as patch:
        def stop(*args):
            raise RuntimeError("simulated interrupted commit")
        patch.setattr(sim.state, "finish_transfer", stop)
        with pytest.raises(RuntimeError, match="interrupted commit"):
            sim.reconcile()
    backup = next(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    return sim, a, b, backup


@pytest.mark.skipif(os.name != "nt", reason="Windows share-delete behavior")
@pytest.mark.parametrize("operation", ["rename", "delete", "replace"])
def test_windows_protected_target_rejects_delete_rename_replace_during_commit(
        tmp_path, monkeypatch, operation):
    sim, a, b, backup = pending_replacement(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    replacement = tmp_path / "replacement.dwg"
    replacement.write_bytes(b"untrusted")
    original = sim.state.finish_transfer
    observed = [False]

    def attempt_operation(*args):
        observed[0] = True
        if operation == "rename":
            action = lambda: b.rename(b.with_name("renamed.dwg"))
        elif operation == "delete":
            action = b.unlink
        else:
            action = lambda: os.replace(replacement, b)
        with pytest.raises(OSError):
            action()
        assert b.read_bytes() == b"new"
        return original(*args)

    monkeypatch.setattr(sim.state, "finish_transfer", attempt_operation)
    result = close_verified_replacement(
        sim, "A101.dwg", fingerprint, "engineer", "Windows protected closure"
    )
    assert result["status"] == "CLOSED"
    assert observed[0]
    assert not sim.state.pending_transfers()
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (b"new", b"new", b"old")
    assert not b.with_name("renamed.dwg").exists()
    if operation == "replace":
        assert replacement.read_bytes() == b"untrusted"


@pytest.mark.skipif(os.name != "nt", reason="Windows share-delete behavior")
def test_windows_backup_cannot_be_deleted_during_commit(tmp_path, monkeypatch):
    sim, a, b, backup = pending_replacement(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    original = sim.state.finish_transfer
    observed = [False]

    def attempt_delete(*args):
        observed[0] = True
        with pytest.raises(OSError):
            backup.unlink()
        assert backup.read_bytes() == b"old"
        return original(*args)

    monkeypatch.setattr(sim.state, "finish_transfer", attempt_delete)
    result = close_verified_replacement(
        sim, "A101.dwg", fingerprint, "engineer", "Windows backup protection"
    )
    assert result["status"] == "CLOSED"
    assert observed[0]
    assert not sim.state.pending_transfers()
    assert backup.read_bytes() == b"old"
