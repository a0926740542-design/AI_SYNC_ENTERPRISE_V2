"""C6 phase 4 batch 7: read-only reconciliation of closure audit vs SQLite.

Audit requests are not proof of completion. No files or DB are modified.
"""
import json

from app.recovery_inspector_r53c6 import inspect_recovery


def inspect_closure_requests(sim):
    path = sim.database.parent / (sim.database.stem + "_recovery_audit.jsonl")
    if not path.exists():
        return []
    entries = []
    # Never infer success from audit alone, even if pending was cleared.
    pending = {r[0] for r in sim.state.pending_transfers()}
    intents = set(sim.state.replacement_intents())
    unresolved = {r["relative_path"] for r in inspect_recovery(sim)["records"]}
    with path.open("r", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                entries.append({"line": number, "status": "MALFORMED_AUDIT_MANUAL_REVIEW"})
                continue
            if not isinstance(row, dict):
                entries.append({"line": number, "status": "MALFORMED_AUDIT_MANUAL_REVIEW"})
                continue
            if row.get("decision") != "CLOSE_VERIFIED":
                continue
            relative = row.get("relative_path")
            if not isinstance(relative, str) or not relative:
                entries.append({"line": number, "status": "MALFORMED_AUDIT_MANUAL_REVIEW"})
                continue
            status = ("CLOSURE_REQUEST_PENDING_MANUAL_REVIEW"
                      if relative in pending or relative in intents or relative in unresolved
                      else "NO_PENDING_STATE_VERIFY_EXTERNALLY")
            entries.append({"line": number, "relative_path": relative, "status": status})
    return entries
