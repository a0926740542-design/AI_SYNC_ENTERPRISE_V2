"""C6 phase 4 batch 7: actual process death and transaction failure tests."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_review_r53c6 import prepare_review
from app.recovery_closure_r53c6 import close_verified_replacement
from app.recovery_audit_status_r53c6 import inspect_closure_requests
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def scenario(tmp_path, monkeypatch):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    database = tmp_path / "state" / "sync.db"
    sim = TwoFolderSimulator(laptop, home, database)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    def stop(*args):
        raise RuntimeError("stop after swap")
    with monkeypatch.context() as patch:
        patch.setattr(sim.state, "finish_transfer", stop)
        with pytest.raises(RuntimeError, match="stop after swap"):
            sim.reconcile()
    return sim, a, b, next(home.glob(BACKUP_PREFIX + "*A101.dwg"))


CHILD = """
import os,sys
from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_closure_r53c6 import close_verified_replacement
sim=TwoFolderSimulator(sys.argv[1],sys.argv[2],sys.argv[3])
sim.state.finish_transfer=lambda *args: os._exit(79)
close_verified_replacement(sim,'A101.dwg',sys.argv[4],'engineer','controlled termination test')
"""


def test_actual_exit_after_audit_before_sqlite_commit(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", CHILD, str(sim.laptop), str(sim.home),
         str(sim.database), fingerprint],
        cwd=root, env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 79, result.stderr
    restarted = TwoFolderSimulator(sim.laptop, sim.home, sim.database)
    assert inspect_closure_requests(restarted)[-1]["status"] == "CLOSURE_REQUEST_PENDING_MANUAL_REVIEW"
    assert restarted.state.pending_transfers()
    assert restarted.state.replacement_intents()
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()
    assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (b"new", b"new", b"old")


def test_sqlite_commit_failure_keeps_pending_and_audit_request(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    def fail(*args):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(sim.state, "finish_transfer", fail)
    with pytest.raises(RuntimeError, match="database unavailable"):
        close_verified_replacement(sim, "A101.dwg", fingerprint, "engineer", "reviewed")
    assert sim.state.pending_transfers()
    assert inspect_closure_requests(sim)[-1]["status"] == "CLOSURE_REQUEST_PENDING_MANUAL_REVIEW"


def test_completed_closure_audit_not_claimed_as_proof(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    close_verified_replacement(sim, "A101.dwg", fingerprint, "engineer", "reviewed")
    assert inspect_closure_requests(sim)[-1]["status"] == "NO_PENDING_STATE_VERIFY_EXTERNALLY"
    assert not sim.state.pending_transfers()


def test_external_edit_after_review_prevents_closure(tmp_path, monkeypatch):
    sim, a, b, backup = scenario(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    b.write_bytes(b"third-party edit")
    with pytest.raises(RuntimeError, match="evidence changed"):
        close_verified_replacement(sim, "A101.dwg", fingerprint, "engineer", "reviewed")
    assert sim.state.pending_transfers()
    assert b.read_bytes() == b"third-party edit"
