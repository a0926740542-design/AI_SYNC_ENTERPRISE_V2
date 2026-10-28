"""R5.3-B offline two-folder simulator; no network or production integration.

Only transfers non-conflicting files after stable SHA-256 reads.
A conflicting file is never overwritten. Missing files are not propagated
as deletions. Both folders must be dedicated test roots.
"""
import hashlib
import os
from pathlib import Path
import tempfile

from app.bidirectional_decisions import Decision, decide
from app.bidirectional_state import SyncState
from app.conflict_vault import ConflictVault
from app.sync_safety_r53c3 import exclusive_run_lock, stable_file
from app.destination_safety_r53c5 import destination_preflight


def digest(path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class TwoFolderSimulator:
    def __init__(self, laptop_root, home_root, database):
        self.laptop = Path(laptop_root).resolve()
        self.home = Path(home_root).resolve()
        self.database = Path(database).resolve()
        if self.laptop == self.home or self.laptop in self.home.parents or self.home in self.laptop.parents:
            raise ValueError("Simulation roots must be disjoint")
        if self.database == self.laptop or self.database == self.home or self.laptop in self.database.parents or self.home in self.database.parents:
            raise ValueError("State database must be outside simulation roots")
        self.state = SyncState(self.database)
        self.vault = ConflictVault(self.database.parent / (self.database.stem + '_conflicts'))

    def _files(self, root):
        if not root.is_dir():
            raise FileNotFoundError(root)
        result = set()
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError("Symlinks are not supported in simulation")
            if path.is_file():
                result.add(path.relative_to(root).as_posix())
        return result

    @staticmethod
    def _copy_verified(source, target, expected_hash, expected_target_hash=None):
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".r53b-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
                for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if digest(source) != expected_hash or digest(Path(name)) != expected_hash:
                raise RuntimeError("Source changed during transfer")
            with destination_preflight(target):
                if digest(target) != expected_target_hash:
                    raise RuntimeError("Destination changed during transfer")
            # Windows replace requires releasing the no-sharing handle first.
            # A narrow external-writer race remains; never use on production DWGs.
            if digest(target) != expected_target_hash:
                raise RuntimeError("Destination changed during transfer")
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def reconcile(self, online=True):
        if not online:
            return {"status": "offline", "copied": [], "conflicts": []}
        with exclusive_run_lock(self.database.with_suffix('.runlock')):
            return self._reconcile_locked()

    def _reconcile_locked(self):
        names = sorted(self._files(self.laptop) | self._files(self.home))
        copied, conflicts = [], []
        pending = {row[0]: (row[1], row[2]) for row in self.state.pending_transfers()}
        for relative in names:
            laptop_path, home_path = self.laptop / relative, self.home / relative
            laptop_hash, home_hash = digest(laptop_path), digest(home_path)
            baseline = self.state.baseline(relative)
            outcome = decide(baseline, laptop_hash, home_hash)
            if outcome.action == Decision.CONFLICT:
                self.vault.preserve(relative, laptop_path, home_path, baseline, laptop_hash, home_hash)
                self.state.record_conflict(relative, baseline, laptop_hash, home_hash)
                conflicts.append(relative)
                continue
            if outcome.action in (Decision.SEND_LAPTOP_TO_HOME, Decision.SEND_HOME_TO_LAPTOP):
                if outcome.action == Decision.SEND_LAPTOP_TO_HOME:
                    direction = "laptop_to_home"
                    source, target = laptop_path, home_path
                    source_hash, target_hash = laptop_hash, home_hash
                else:
                    direction = "home_to_laptop"
                    source, target = home_path, laptop_path
                    source_hash, target_hash = home_hash, laptop_hash
                stable_file(source)
                self.state.stage_transfer(relative, direction, source_hash)
                self._copy_verified(source, target, source_hash, target_hash)
                if digest(source) != source_hash or digest(target) != source_hash:
                    raise RuntimeError(f"Post-copy mismatch: {relative}")
                self.state.finish_transfer(relative, source_hash)
                copied.append((direction, relative))
                continue
            final_laptop, final_home = digest(laptop_path), digest(home_path)
            if final_laptop != final_home:
                raise RuntimeError(f"Post-copy mismatch: {relative}")
            if final_laptop is not None:
                if relative in pending and pending[relative][1] == final_laptop:
                    self.state.finish_transfer(relative, final_laptop)
                else:
                    self.state.acknowledge(relative, final_laptop)
                    if relative in pending:
                        self.state.discard_pending(relative, pending[relative][1])
        return {"status": "online", "copied": copied, "conflicts": conflicts}
