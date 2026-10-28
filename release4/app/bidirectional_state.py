"""Persistent R5.3-A baseline and unresolved conflict metadata.

This module stores metadata only. It does not overwrite DWG files.
"""
import sqlite3
from pathlib import Path


class SyncState:
    def __init__(self, database):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS baselines (
                relative_path TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS pending_transfers (\n                relative_path TEXT PRIMARY KEY, direction TEXT NOT NULL,\n                expected_sha256 TEXT NOT NULL\n            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS conflicts (
                relative_path TEXT PRIMARY KEY,
                baseline_sha256 TEXT,
                laptop_sha256 TEXT,
                home_sha256 TEXT,
                status TEXT NOT NULL DEFAULT 'unresolved'
            )""")

    def _connect(self):
        return sqlite3.connect(self.database, timeout=10)

    @staticmethod
    def _path(relative_path):
        path = Path(relative_path)
        if path.is_absolute() or not path.parts or '..' in path.parts or str(path) in ('.', ''):
            raise ValueError("Expected safe relative path")
        return path.as_posix()

    def baseline(self, relative_path):
        with self._connect() as db:
            row = db.execute("SELECT sha256 FROM baselines WHERE relative_path=?",
                             (self._path(relative_path),)).fetchone()
            return row[0] if row else None

    def acknowledge(self, relative_path, sha256):
        if not sha256:
            raise ValueError("An acknowledged file requires a digest")
        with self._connect() as db:
            db.execute("""INSERT INTO baselines(relative_path, sha256) VALUES (?, ?)
                ON CONFLICT(relative_path) DO UPDATE SET sha256=excluded.sha256""",
                (self._path(relative_path), sha256))

    def record_conflict(self, relative_path, baseline, laptop, home):
        with self._connect() as db:
            db.execute("""INSERT INTO conflicts
                (relative_path,baseline_sha256,laptop_sha256,home_sha256,status)
                VALUES (?,?,?,?, 'unresolved')
                ON CONFLICT(relative_path) DO UPDATE SET
                baseline_sha256=excluded.baseline_sha256,
                laptop_sha256=excluded.laptop_sha256,
                home_sha256=excluded.home_sha256,status='unresolved'""",
                (self._path(relative_path), baseline, laptop, home))

    def unresolved_conflicts(self):
        with self._connect() as db:
            return db.execute("""SELECT relative_path,baseline_sha256,
                laptop_sha256,home_sha256 FROM conflicts
                WHERE status='unresolved' ORDER BY relative_path""").fetchall()

    def stage_transfer(self, relative_path, direction, expected_sha256):
        if direction not in ("laptop_to_home", "home_to_laptop") or not expected_sha256:
            raise ValueError("Invalid pending transfer")
        with self._connect() as db:
            db.execute("""INSERT INTO pending_transfers(relative_path,direction,expected_sha256)
                VALUES (?,?,?) ON CONFLICT(relative_path) DO UPDATE SET
                direction=excluded.direction, expected_sha256=excluded.expected_sha256""",
                (self._path(relative_path), direction, expected_sha256))

    def pending_transfers(self):
        with self._connect() as db:
            return db.execute("""SELECT relative_path,direction,expected_sha256
                FROM pending_transfers ORDER BY relative_path""").fetchall()

    def finish_transfer(self, relative_path, expected_sha256):
        """Atomically acknowledge a verified copy and clear its pending intent."""
        path = self._path(relative_path)
        with self._connect() as db:
            row = db.execute("SELECT expected_sha256 FROM pending_transfers WHERE relative_path=?",
                             (path,)).fetchone()
            if row is None or row[0] != expected_sha256:
                raise RuntimeError("Pending transfer changed")
            db.execute("""INSERT INTO baselines(relative_path,sha256) VALUES (?,?)
                ON CONFLICT(relative_path) DO UPDATE SET sha256=excluded.sha256""",
                (path, expected_sha256))
            db.execute("DELETE FROM pending_transfers WHERE relative_path=?", (path,))
