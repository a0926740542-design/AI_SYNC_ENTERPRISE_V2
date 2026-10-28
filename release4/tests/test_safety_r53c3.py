import pytest

from app.bidirectional_simulator import TwoFolderSimulator
from app.sync_safety_r53c3 import exclusive_run_lock, stable_file


def test_second_run_lock_is_rejected(tmp_path):
    path = tmp_path / "sim.runlock"
    with exclusive_run_lock(path):
        with pytest.raises(RuntimeError, match="Another simulator"):
            with exclusive_run_lock(path):
                pass
    with exclusive_run_lock(path):
        pass


def test_file_changed_during_settle_is_rejected(tmp_path, monkeypatch):
    import app.sync_safety_r53c3 as safety
    path = tmp_path / "A101.dwg"
    path.write_bytes(b"original")
    def mutate(_):
        path.write_bytes(b"modified-and-longer")
    monkeypatch.setattr(safety.time, "sleep", mutate)
    with pytest.raises(RuntimeError, match="changed"):
        stable_file(path)


def test_reconcile_respects_external_run_lock(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    (laptop / "A101.dwg").write_bytes(b"safe")
    sim = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    with exclusive_run_lock(sim.database.with_suffix(".runlock")):
        with pytest.raises(RuntimeError, match="Another simulator"):
            sim.reconcile()
    assert not (home / "A101.dwg").exists()
    assert sim.reconcile()["copied"] == [("laptop_to_home", "A101.dwg")]
