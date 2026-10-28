import pytest

from app.bidirectional_simulator import TwoFolderSimulator, digest


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


def test_failed_copy_preserves_destination_and_pending_intent(tmp_path, monkeypatch):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"first")
    sim.reconcile()
    a.write_bytes(b"second")
    original = sim._copy_verified

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(sim, "_copy_verified", fail)
    with pytest.raises(OSError, match="simulated disk failure"):
        sim.reconcile()
    assert b.read_bytes() == b"first"
    assert sim.state.pending_transfers() == [
        ("A101.dwg", "laptop_to_home", digest(a))
    ]
    monkeypatch.setattr(sim, "_copy_verified", original)
    restarted = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    assert restarted.reconcile()["copied"] == [("laptop_to_home", "A101.dwg")]
    assert restarted.state.pending_transfers() == []
    assert b.read_bytes() == b"second"


def test_crash_after_copy_before_acknowledge_is_recovered(tmp_path):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    new_hash = digest(a)
    sim.state.stage_transfer("A101.dwg", "laptop_to_home", new_hash)
    sim._copy_verified(a, b, new_hash, digest(b))
    restarted = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    assert restarted.reconcile()["copied"] == []
    assert restarted.state.pending_transfers() == []
    assert restarted.state.baseline("A101.dwg") == new_hash


def test_destination_change_during_copy_is_rejected(tmp_path, monkeypatch):
    sim, laptop, home = roots(tmp_path)
    a, b = laptop / "A101.dwg", home / "A101.dwg"
    a.write_bytes(b"old")
    sim.reconcile()
    a.write_bytes(b"new")
    original_digest = __import__("app.bidirectional_simulator", fromlist=["digest"])
    original = original_digest.digest
    triggered = {"value": False}

    def inject(path):
        if str(path) == str(b) and not triggered["value"]:
            triggered["value"] = True
            b.write_bytes(b"concurrent-home-change")
        return original(path)

    monkeypatch.setattr(original_digest, "digest", inject)
    with pytest.raises(RuntimeError, match="Destination changed"):
        sim.reconcile()
    assert b.read_bytes() == b"concurrent-home-change"
    assert sim.state.pending_transfers()
