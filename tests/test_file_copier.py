from pathlib import Path

from app.file_copier import FileCopier


def main():

    source = Path(r"C:\WORK\FILECOPIER_TEST.txt")

    source.write_text(
        "AI_SYNC Enterprise Test",
        encoding="utf-8"
    )

    copier = FileCopier(r"C:\BACKUP")

    ok = copier.copy(source)

    print("Copy Result :", ok)

    backup = Path(r"C:\BACKUP\FILECOPIER_TEST.txt")

    print("Backup Exists :", backup.exists())


if __name__ == "__main__":
    main()