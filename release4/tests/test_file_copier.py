from app.file_copier import FileCopier
def test_file_copier_preserves_nested_paths(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    nested = source / "TEST"
    nested.mkdir(parents=True)
    file = nested / "A010.txt"
    file.write_text("hello", encoding="utf-8")
    copier = FileCopier(backup, source)
    assert copier.copy(file) is True
    assert (backup / "TEST" / "A010.txt").read_text(encoding="utf-8") == "hello"
def test_missing_file_is_not_copied(tmp_path):
    copier = FileCopier(tmp_path / "backup", tmp_path / "source")
    assert copier.copy(tmp_path / "source" / "missing.txt") is False
