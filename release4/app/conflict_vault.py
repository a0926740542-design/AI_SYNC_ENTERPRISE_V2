"""Immutable conflict evidence snapshots for the R5.3 simulator.

Snapshots live outside both sync roots and are never used as live DWG files.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ConflictVault:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _snapshot(self, source, expected_hash, relative, side):
        if expected_hash is None:
            return None
        # Hash-addressed, immutable: later conflict iterations retain older evidence.
        key = hashlib.sha256(relative.encode("utf-8")).hexdigest()
        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (side + "-" + expected_hash + ".snapshot")
        if target.exists():
            if _sha256(target) != expected_hash:
                raise RuntimeError("Existing conflict evidence corrupted")
            return str(target)
        fd, temp = tempfile.mkstemp(prefix=".evidence-", dir=folder)
        try:
            with os.fdopen(fd, "wb") as output, Path(source).open("rb") as input_file:
                for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if _sha256(source) != expected_hash or _sha256(temp) != expected_hash:
                raise RuntimeError("Conflict source changed during snapshot")
            # Exclusive create prevents overwriting existing immutable evidence.
            try:
                os.link(temp, target)
            except FileExistsError:
                if _sha256(target) != expected_hash:
                    raise RuntimeError("Existing conflict evidence corrupted")
            return str(target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def preserve(self, relative, laptop_path, home_path, baseline, laptop_hash, home_hash):
        laptop_snapshot = self._snapshot(laptop_path, laptop_hash, relative, "laptop")
        home_snapshot = self._snapshot(home_path, home_hash, relative, "home")
        return {"relative_path": relative, "baseline_sha256": baseline,
                "laptop_sha256": laptop_hash, "home_sha256": home_hash,
                "laptop_snapshot": laptop_snapshot, "home_snapshot": home_snapshot}
