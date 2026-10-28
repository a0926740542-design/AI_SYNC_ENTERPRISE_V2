import threading
import time
from pathlib import Path

from app.file_copier import FileCopier


def test_source_changed_during_settle_retries_to_final_version(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    version = tmp_path / "version"
    source.mkdir()
    target = source / "drawing.dwg"
    target.write_bytes(b"ORIGINAL")
    copier = FileCopier(backup, source, version_folder=version, settle_seconds=0)
    assert copier.copy(target)
    target.write_bytes(b"IN_PROGRESS")

    def writer():
        time.sleep(0.05)
        target.write_bytes(b"IN_PROGRESS_AND_CHANGED")

    thread = threading.Thread(target=writer)
    thread.start()
    guarded = FileCopier(backup, source, version_folder=version, settle_seconds=0.2)
    try:
        assert guarded.copy(target)
    finally:
        thread.join()
    assert (backup / "drawing.dwg").read_bytes() == b"IN_PROGRESS_AND_CHANGED"
    versions = list(version.rglob("*drawing.dwg"))
    assert len(versions) == 1
    assert versions[0].read_bytes() == b"ORIGINAL"


def test_stable_source_copies_and_versions(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    version = tmp_path / "version"
    source.mkdir()
    target = source / "drawing.dwg"
    target.write_bytes(b"OLD")
    copier = FileCopier(backup, source, version_folder=version, settle_seconds=0.01)
    assert copier.copy(target)
    target.write_bytes(b"NEW")
    assert copier.copy(target)
    assert (backup / "drawing.dwg").read_bytes() == b"NEW"
    versions = list(version.rglob("*drawing.dwg"))
    assert len(versions) == 1
    assert versions[0].read_bytes() == b"OLD"
