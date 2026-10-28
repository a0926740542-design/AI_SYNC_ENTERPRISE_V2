"""R5.3-C6 isolated regression tests for atomic new-file installation."""
import pytest
from app.bidirectional_simulator import TwoFolderSimulator


def roots(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


def test_new_destination_installed_without_overwrite(tmp_path):
    sim, laptop, home = roots(tmp_path)
    (laptop / "A101.dwg").write_bytes(b"laptop")
    result = sim.reconcile()
    assert result["copied"] == [("laptop_to_home", "A101.dwg")]
    assert (home / "A101.dwg").read_bytes() == b"laptop"
    assert sim.state.pending_transfers() == []


def test_destination_created_at_install_is_never_overwritten(tmp_path, monkeypatch):
    import app.transfer_guard_r53c6 as guard
    sim, laptop, home = roots(tmp_path)
    (laptop / "A101.dwg").write_bytes(b"laptop")
    target = home / "A101.dwg"
    original_link = guard.os.link

    def race_link(staged, destination, *args, **kwargs):
        if str(destination) == str(target):
            target.write_bytes(b"third-party")
        return original_link(staged, destination, *args, **kwargs)

    monkeypatch.setattr(guard.os, "link", race_link)
    with pytest.raises(RuntimeError, match="Destination appeared"):
        sim.reconcile()
    assert target.read_bytes() == b"third-party"
    assert sim.state.pending_transfers()


def test_staging_debris_is_not_synchronized(tmp_path):
    sim, laptop, home = roots(tmp_path)
    (laptop / ".r53b-interrupted").write_bytes(b"unfinished")
    result = sim.reconcile()
    assert result["copied"] == []
    assert not (home / ".r53b-interrupted").exists()
