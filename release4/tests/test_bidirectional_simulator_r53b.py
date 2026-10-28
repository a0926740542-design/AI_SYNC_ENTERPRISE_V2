from app.bidirectional_simulator import TwoFolderSimulator, digest


def setup(tmp_path):
    laptop, home = tmp_path / "laptop", tmp_path / "home"
    laptop.mkdir()
    home.mkdir()
    return TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db"), laptop, home


def test_laptop_to_home_and_home_to_laptop(tmp_path):
    sim, laptop, home = setup(tmp_path)
    (laptop / "CAD").mkdir()
    (laptop / "CAD" / "A101.dwg").write_bytes(b"laptop-original")
    result = sim.reconcile()
    assert result["copied"] == [("laptop_to_home", "CAD/A101.dwg")]
    assert digest(laptop / "CAD" / "A101.dwg") == digest(home / "CAD" / "A101.dwg")
    (home / "CAD" / "A101.dwg").write_bytes(b"home-revision")
    result = sim.reconcile()
    assert result["copied"] == [("home_to_laptop", "CAD/A101.dwg")]
    assert (laptop / "CAD" / "A101.dwg").read_bytes() == b"home-revision"


def test_conflicting_offline_edits_never_overwrite(tmp_path):
    sim, laptop, home = setup(tmp_path)
    (laptop / "A101.dwg").write_bytes(b"shared")
    sim.reconcile()
    assert sim.reconcile(online=False)["status"] == "offline"
    (laptop / "A101.dwg").write_bytes(b"laptop-edit")
    (home / "A101.dwg").write_bytes(b"home-edit")
    result = sim.reconcile()
    assert result["conflicts"] == ["A101.dwg"]
    assert result["copied"] == []
    assert (laptop / "A101.dwg").read_bytes() == b"laptop-edit"
    assert (home / "A101.dwg").read_bytes() == b"home-edit"
    assert len(sim.state.unresolved_conflicts()) == 1


def test_restart_recovers_offline_new_file_without_extra_copy(tmp_path):
    sim, laptop, home = setup(tmp_path)
    (home / "nested").mkdir()
    (home / "nested" / "B201.dwg").write_bytes(b"offline-file")
    sim.reconcile(online=False)
    restarted = TwoFolderSimulator(laptop, home, tmp_path / "state" / "sync.db")
    assert restarted.reconcile()["copied"] == [("home_to_laptop", "nested/B201.dwg")]
    assert restarted.reconcile()["copied"] == []


def test_deletion_is_conflict(tmp_path):
    sim, laptop, home = setup(tmp_path)
    (laptop / "A101.dwg").write_bytes(b"shared")
    sim.reconcile()
    (home / "A101.dwg").unlink()
    result = sim.reconcile()
    assert result["conflicts"] == ["A101.dwg"]
    assert (laptop / "A101.dwg").exists()
    assert not (home / "A101.dwg").exists()
