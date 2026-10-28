"""R5.3-C6 phase 4 batch 4: read-only recovery inventory.

No DWG writes, database writes, backup deletion, or automatic unlock.
The caller must use isolated test roots for the offline simulator.
"""
from pathlib import Path

from app.bidirectional_simulator import digest
from app.replacement_backup_r53c6 import BACKUP_PREFIX


def inspect_recovery(sim):
    """Return an evidence-only inventory of unresolved transfer state."""
    pending = {row[0]: (row[1], row[2]) for row in sim.state.pending_transfers()}
    intents = sim.state.replacement_intents()
    names = sorted(set(pending) | set(intents))
    records = []
    for relative in names:
        # Database keys are validated when written; refuse unsafe legacy rows.
        safe = sim.state._path(relative)
        laptop = sim.laptop / safe
        home = sim.home / safe
        backups = []
        for endpoint in (laptop, home):
            if endpoint.parent.is_dir():
                for path in sorted(endpoint.parent.glob(BACKUP_PREFIX + "*" + endpoint.name)):
                    if path.is_file() and not path.is_symlink():
                        backups.append({
                            "path": str(path),
                            "sha256": digest(path),
                        })
        pending_entry = pending.get(relative)
        expected = pending_entry[1] if pending_entry else None
        intent = intents.get(relative)
        issues = []
        if pending_entry is None:
            issues.append("orphan_replacement_intent")
        if intent is not None and intent != expected:
            issues.append("intent_digest_mismatch")
        if intent is not None and not backups:
            issues.append("replacement_backup_missing_or_not_visible")
        laptop_hash = digest(laptop)
        home_hash = digest(home)
        if expected is not None and laptop_hash != expected and home_hash != expected:
            issues.append("expected_content_absent")
        records.append({
            "relative_path": relative,
            "direction": pending_entry[0] if pending_entry else None,
            "pending_sha256": expected,
            "replacement_intent_sha256": intent,
            "baseline_sha256": sim.state.baseline(relative),
            "laptop_sha256": laptop_hash,
            "home_sha256": home_hash,
            "backups": backups,
            "issues": issues,
            "status": "MANUAL_REVIEW_REQUIRED",
        })
    return {"mode": "READ_ONLY", "record_count": len(records), "records": records}
