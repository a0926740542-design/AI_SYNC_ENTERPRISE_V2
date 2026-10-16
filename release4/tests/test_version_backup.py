from app.file_copier import FileCopier
def test_version_history(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    file = src / "test.txt"
    backup = tmp_path / "backup"
    history = tmp_path / "history"
    copier = FileCopier(backup, src, version_folder=history)
    file.write_text("first")
    assert copier.copy(file)
    file.write_text("second")
    assert copier.copy(file)
    assert (backup / "test.txt").read_text() == "second"
    saved = list(history.glob("*test.txt"))
    assert len(saved) == 1
    assert saved[0].read_text() == "first"
    assert copier.copy(file)
    assert len(list(history.glob("*test.txt"))) == 1
def test_overlapping_version_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        FileCopier(tmp_path / "backup", tmp_path / "source", version_folder=tmp_path / "backup" / "history")
