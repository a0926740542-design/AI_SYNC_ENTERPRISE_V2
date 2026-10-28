"""R5.3-C6 phase 4 batch 6: strictly gated simulation recovery closure.

Never copies, restores, deletes, or modifies DWG/backup files.
This is NOT a production-safe atomic filesystem/database transaction.
"""
import hashlib
import json
import os

from app.bidirectional_simulator import digest
from app.recovery_inspector_r53c6 import inspect_recovery
from app.recovery_review_r53c6 import _canonical
from app.sync_safety_r53c3 import exclusive_run_lock
from app.recovery_windows_guard_r53c6 import hold_read_only_no_writers


def close_verified_replacement(sim, relative_path, fingerprint, operator, reason):
    """Close an already-complete replacement only with verified displaced backup.

    Requires two equal endpoint hashes matching pending+intent, one displaced
    backup matching the old baseline, and explicit current evidence consent.
    """
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("Operator is required")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Reason is required")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("Evidence fingerprint required")
    with exclusive_run_lock(sim.database.with_suffix(".runlock")):
        report = inspect_recovery(sim)
        rows = [row for row in report["records"] if row["relative_path"] == relative_path]
        if len(rows) != 1:
            raise RuntimeError("No unique pending replacement")
        row = rows[0]
        actual = hashlib.sha256(_canonical(row).encode("utf-8")).hexdigest()
        if actual != fingerprint:
            raise RuntimeError("Recovery evidence changed: re-inspect required")
        expected = row["pending_sha256"]
        baseline = row["baseline_sha256"]
        if (row["direction"] not in ("laptop_to_home", "home_to_laptop")
                or not expected or not baseline or expected == baseline
                or row["replacement_intent_sha256"] != expected
                or row["laptop_sha256"] != expected
                or row["home_sha256"] != expected
                or row["issues"]):
            raise RuntimeError("Unsafe recovery: endpoint or intent verification failed")
        # Reject missing/extra/ambiguous backups, including one on the wrong root.
        backups = row["backups"]
        if len(backups) != 1 or backups[0]["sha256"] != baseline:
            raise RuntimeError("Unsafe recovery: displaced backup verification failed")
        expected_root = sim.home if row["direction"] == "laptop_to_home" else sim.laptop
        backup_path = backups[0]["path"]
        from pathlib import Path
        if Path(backup_path).parent != (expected_root / relative_path).parent:
            raise RuntimeError("Unsafe recovery: backup located on wrong endpoint")
        # Rehash immediately before acknowledging; concurrent external writers
        # can still race these checks. Use only on isolated offline test roots.
        laptop = sim.laptop / relative_path
        home = sim.home / relative_path
        if (digest(laptop) != expected or digest(home) != expected
                or digest(Path(backup_path)) != baseline):
            raise RuntimeError("Recovery evidence changed during verification")
        # Hold Windows read-sharing handles through audit and SQLite commit.
        # No write access is shared; normal AutoCAD writer opens fail closed.
        with hold_read_only_no_writers((laptop, home, Path(backup_path))):
            audit_path = sim.database.parent / (sim.database.stem + "_recovery_audit.jsonl")
            entry = {
                "relative_path": relative_path,
                "evidence_sha256": actual,
                "operator": operator.strip(),
                "decision": "CLOSE_VERIFIED",
                "reason": reason.strip(),
                "status": "CLOSURE_REQUESTED",
            }
            fd = os.open(audit_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "ab") as stream:
                stream.write((_canonical(entry) + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            # Revalidate AFTER the durable audit write as well. A third-party
            # writer may modify a DWG while the audit record is being flushed.
            # This narrows but DOES NOT eliminate the final check-to-commit race.
            if (digest(laptop) != expected or digest(home) != expected
                    or digest(Path(backup_path)) != baseline):
                raise RuntimeError("Recovery evidence changed after audit write")
            sim.state.finish_transfer(relative_path, expected)
            return {**entry, "status": "CLOSED", "note": "Audit records request before database commit"}
