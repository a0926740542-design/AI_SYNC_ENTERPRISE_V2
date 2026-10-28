"""R5.3-C6 phase 4 batch 5: human review evidence and append-only audit.

This module NEVER clears pending records, changes baselines, writes DWGs,
restores backups or unlocks synchronization. Reviews are evidence only.
"""
import hashlib
import json
import os
from pathlib import Path

from app.recovery_inspector_r53c6 import inspect_recovery
from app.sync_safety_r53c3 import exclusive_run_lock


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def prepare_review(sim, relative_path):
    """Produce a snapshot and fingerprint to be explicitly confirmed."""
    with exclusive_run_lock(sim.database.with_suffix(".runlock")):
        report = inspect_recovery(sim)
        rows = [r for r in report["records"] if r["relative_path"] == relative_path]
        if len(rows) != 1:
            raise ValueError("No unique unresolved recovery record")
        row = rows[0]
        return {
            "record": row,
            "fingerprint": hashlib.sha256(_canonical(row).encode("utf-8")).hexdigest(),
            "mode": "REVIEW_ONLY",
        }


def record_review(sim, relative_path, fingerprint, operator, decision, note):
    """Recheck evidence, then durably record an operator review; never unlock."""
    if decision not in ("HOLD", "ESCALATE"):
        raise ValueError("Only HOLD or ESCALATE are permitted")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("Operator is required")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Review note is required")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise ValueError("Full evidence fingerprint is required")
    with exclusive_run_lock(sim.database.with_suffix(".runlock")):
        report = inspect_recovery(sim)
        rows = [r for r in report["records"] if r["relative_path"] == relative_path]
        if len(rows) != 1:
            raise RuntimeError("Recovery evidence changed: record missing")
        current = rows[0]
        current_fingerprint = hashlib.sha256(_canonical(current).encode("utf-8")).hexdigest()
        if current_fingerprint != fingerprint:
            raise RuntimeError("Recovery evidence changed: re-inspect required")
        audit_path = sim.database.parent / (sim.database.stem + "_recovery_audit.jsonl")
        entry = {
            "relative_path": relative_path,
            "evidence_sha256": current_fingerprint,
            "operator": operator.strip(),
            "decision": decision,
            "note": note.strip(),
            "status": "BLOCKED_UNCHANGED",
        }
        # Exclusive create/appending protects prior entries from truncation.
        # This is not tamper-proof and does not substitute for external audit storage.
        fd = os.open(audit_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            with os.fdopen(fd, "ab") as output:
                output.write((_canonical(entry) + "\n").encode("utf-8"))
                output.flush()
                os.fsync(output.fileno())
        finally:
            pass
        return entry
