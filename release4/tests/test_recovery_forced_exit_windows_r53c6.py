"""R5.3-C6 phase 4 batch 11: real process termination under Windows DWG locks.

All paths are isolated pytest temporary roots. Never target production DWGs.
"""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_review_r53c6 import prepare_review
from app.recovery_audit_status_r53c6 import inspect_closure_requests
from app.replacement_backup_r53c6 import BACKUP_PREFIX
from app.recovery_windows_guard_r53c6 import hold_read_only_no_writers


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
        def interrupt(*args):
            raise RuntimeError("simulated post-swap interruption")
        patch.setattr(sim.state, "finish_transfer", interrupt)
        with pytest.raises(RuntimeError, match="post-swap interruption"):
            sim.reconcile()
    backup = next(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    return sim, a, b, backup


CHILD = """
import os, sys
from app.bidirectional_simulator import TwoFolderSimulator
from app.recovery_closure_r53c6 import close_verified_replacement
import app.recovery_closure_r53c6 as closure
sim=TwoFolderSimulator(sys.argv[1],sys.argv[2],sys.argv[3])
stage=sys.argv[5]
if stage == 'before_commit':
    sim.state.finish_transfer=lambda *args: os._exit(81)
elif stage == 'after_commit':
    original=sim.state.finish_transfer
    def exit_after(*args):
        original(*args)
        os._exit(82)
    sim.state.finish_transfer=exit_after
elif stage == 'audit_flush':
    original=closure.os.fsync
    def exit_on_fsync(fd):
        original(fd)
        os._exit(83)
    closure.os.fsync=exit_on_fsync
close_verified_replacement(sim,'A101.dwg',sys.argv[4],'engineer','process exit under Windows locks')
"""


@pytest.mark.skipif(os.name != "nt", reason="Windows process handle release")
@pytest.mark.parametrize("stage,exit_code,pending_expected", [
    ("audit_flush", 83, True),
    ("before_commit", 81, True),
    ("after_commit", 82, False),
])
def test_forced_exit_releases_windows_handles_and_preserves_state(
        tmp_path, monkeypatch, stage, exit_code, pending_expected):
    sim, a, b, backup = pending(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", CHILD, str(sim.laptop), str(sim.home),
         str(sim.database), fingerprint, stage],
        cwd=root, env=env, capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == exit_code, result.stderr
    # The terminated process must not leave any Windows read-share handle alive.
    with hold_read_only_no_writers((a, b, backup)):
        assert (a.read_bytes(), b.read_bytes(), backup.read_bytes()) == (
            b"new", b"new", b"old"
        )
    restarted = TwoFolderSimulator(sim.laptop, sim.home, sim.database)
    assert bool(restarted.state.pending_transfers()) is pending_expected
    assert bool(restarted.state.replacement_intents()) is pending_expected
    if pending_expected:
        assert inspect_closure_requests(restarted)[-1]["status"] == (
            "CLOSURE_REQUEST_PENDING_MANUAL_REVIEW"
        )
        with pytest.raises(RuntimeError, match="manual recovery"):
            restarted.reconcile()
    else:
        assert restarted.state.baseline("A101.dwg") is not None
        assert restarted.reconcile()["status"] == "online"


@pytest.mark.skipif(os.name != "nt", reason="Windows process handle release")
def test_terminated_process_does_not_leave_stale_writer_block(tmp_path, monkeypatch):
    sim, a, b, backup = pending(tmp_path, monkeypatch)
    fingerprint = prepare_review(sim, "A101.dwg")["fingerprint"]
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", CHILD, str(sim.laptop), str(sim.home),
         str(sim.database), fingerprint, "before_commit"],
        cwd=root, env=env, capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 81, result.stderr
    # Windows releases OS handles when the process exits. Restore original bytes
    # immediately so the simulated recovery evidence remains unchanged.
    with b.open("r+b") as stream:
        assert stream.read() == b"new"
    assert sim.state.pending_transfers()
    assert backup.read_bytes() == b"old"
