from pathlib import Path

import pytest

from app.bidirectional_simulator import TwoFolderSimulator, digest


def _setup(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


def test_conflict_snapshots_survive_restart_and_live_edits(tmp_path):
    sim, laptop, home = _setup(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"baseline")
    sim.reconcile()
    a.write_bytes(b"laptop-version")
    b.write_bytes(b"home-version")
    assert sim.reconcile()["conflicts"] == ["A101.dwg"]
    vault = tmp_path / "state" / "sync_conflicts"
    evidence = sorted(vault.rglob("*.snapshot"))
    assert len(evidence) == 2
    assert sorted(p.read_bytes() for p in evidence) == [b"home-version", b"laptop-version"]
    a.write_bytes(b"later-change")
    assert sorted(p.read_bytes() for p in evidence) == [b"home-version", b"laptop-version"]
    restarted = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    assert restarted.reconcile()["conflicts"] == ["A101.dwg"]
    assert len(list(vault.rglob("*.snapshot"))) == 3


def test_deleted_side_preserves_existing_side(tmp_path):
    sim, laptop, home = _setup(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"baseline")
    sim.reconcile()
    b.unlink()
    assert sim.reconcile()["conflicts"] == ["A101.dwg"]
    evidence = list((tmp_path / "state" / "sync_conflicts").rglob("*.snapshot"))
    assert len(evidence) == 1
    assert evidence[0].read_bytes() == b"baseline"
    assert not b.exists()


def test_conflict_snapshot_detects_corruption(tmp_path):
    sim, laptop, home = _setup(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"baseline")
    sim.reconcile()
    a.write_bytes(b"left")
    b.write_bytes(b"right")
    sim.reconcile()
    evidence = next((tmp_path / "state" / "sync_conflicts").rglob("laptop-*.snapshot"))
    evidence.write_bytes(b"corrupted")
    with pytest.raises(RuntimeError, match="corrupted"):
        sim.reconcile()
    assert a.read_bytes() == b"left"
    assert b.read_bytes() == b"right"
