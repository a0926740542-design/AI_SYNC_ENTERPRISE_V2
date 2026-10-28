from app.core.sync_engine import SyncEngine


def test_startup_reconcile_copies_missed_nested_file(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    version = tmp_path / "version"
    nested = source / "CAD"
    nested.mkdir(parents=True)
    (nested / "offline.dwg").write_bytes(b"OFFLINE_CHANGE")
    (nested / "ignored.bak").write_bytes(b"IGNORE")
    engine = SyncEngine(source, backup, version_folder=version)
    engine.file_copier.settle_seconds = 0.01
    try:
        engine.start()
    finally:
        engine.stop()
    assert (backup / "CAD" / "offline.dwg").read_bytes() == b"OFFLINE_CHANGE"
    assert not (backup / "CAD" / "ignored.bak").exists()


def test_startup_reconcile_unchanged_file_creates_no_extra_version(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    version = tmp_path / "version"
    source.mkdir()
    (source / "drawing.dwg").write_bytes(b"ALREADY_SYNCED")
    for _ in range(2):
        engine = SyncEngine(source, backup, version_folder=version)
        engine.file_copier.settle_seconds = 0.01
        try:
            engine.start()
        finally:
            engine.stop()
    assert (backup / "drawing.dwg").read_bytes() == b"ALREADY_SYNCED"
    assert list(version.rglob("*drawing.dwg")) == []
