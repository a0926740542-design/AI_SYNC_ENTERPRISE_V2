"""R5.3-C6 phase 4 batch 3: real child-process termination tests.

Only pytest tmp_path roots are used. os._exit terminates a CHILD interpreter,
never the pytest runner or any production synchronization service.
"""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.bidirectional_simulator import TwoFolderSimulator, digest
from app.replacement_backup_r53c6 import BACKUP_PREFIX


CHILD = """
import os
import sys
from app.bidirectional_simulator import TwoFolderSimulator
sim = TwoFolderSimulator(sys.argv[1], sys.argv[2], sys.argv[3])
phase = sys.argv[4]
if phase == 'after_swap':
    sim.state.finish_transfer = lambda *args: os._exit(73)
elif phase == 'before_swap':
    original = sim.state.mark_replacement_intent
    def exit_after_durable_intent(*args):
        original(*args)
        os._exit(74)
    sim.state.mark_replacement_intent = exit_after_durable_intent
else:
    raise ValueError(phase)
sim.reconcile()
raise AssertionError('Expected child termination')
"""


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    database = tmp_path / "state" / "sync.db"
    return TwoFolderSimulator(laptop, home, database), laptop, home, database


def run_child(laptop, home, database, phase):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", CHILD, str(laptop), str(home), str(database), phase],
        cwd=root, env=env, capture_output=True, text=True, timeout=20,
        check=False,
    )


def test_real_process_exit_after_swap_preserves_backup_and_pending(tmp_path):
    sim, laptop, home, database = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    original_baseline = sim.state.baseline("A101.dwg")
    a.write_bytes(b"new")
    result = run_child(laptop, home, database, "after_swap")
    assert result.returncode == 73, result.stderr
    restarted = TwoFolderSimulator(laptop, home, database)
    assert a.read_bytes() == b"new"
    assert b.read_bytes() == b"new"
    backups = list(home.glob(BACKUP_PREFIX + "*A101.dwg"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"old"
    assert restarted.state.baseline("A101.dwg") == original_baseline
    assert restarted.state.pending_transfers() == [
        ("A101.dwg", "laptop_to_home", digest(a))
    ]
    assert restarted.state.replacement_intents()["A101.dwg"] == digest(a)
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()
    assert b.read_bytes() == b"new"


def test_real_process_exit_after_intent_before_swap_fails_closed(tmp_path):
    sim, laptop, home, database = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    original_baseline = sim.state.baseline("A101.dwg")
    a.write_bytes(b"new")
    result = run_child(laptop, home, database, "before_swap")
    assert result.returncode == 74, result.stderr
    restarted = TwoFolderSimulator(laptop, home, database)
    assert a.read_bytes() == b"new"
    assert b.read_bytes() == b"old"
    assert restarted.state.baseline("A101.dwg") == original_baseline
    assert restarted.state.replacement_intents()["A101.dwg"] == digest(a)
    assert restarted.state.pending_transfers()
    with pytest.raises(RuntimeError, match="manual recovery"):
        restarted.reconcile()
    assert b.read_bytes() == b"old"
