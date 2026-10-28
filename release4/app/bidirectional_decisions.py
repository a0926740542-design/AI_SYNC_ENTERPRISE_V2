"""R5.3-A three-way sync decisions. No file writes or network operations.

The baseline is the last acknowledged common state, not a timestamp.
Each side is a SHA-256 digest or None for an absent file.
"""
from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    NO_CHANGE = "no_change"
    SEND_LAPTOP_TO_HOME = "send_laptop_to_home"
    SEND_HOME_TO_LAPTOP = "send_home_to_laptop"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class SyncDecision:
    action: Decision
    reason: str


def decide(baseline: str | None, laptop: str | None, home: str | None) -> SyncDecision:
    """Compare against last mutually acknowledged state.

    No automatic deletion: absence on one side is a conflict when a baseline
    existed. Both changed to identical content is safe to acknowledge.
    """
    if baseline is not None and (laptop is None or home is None):
        return SyncDecision(Decision.CONFLICT, "deletion requires manual review")
    if laptop == home:
        return SyncDecision(Decision.NO_CHANGE, "both sides already identical")
    laptop_changed = laptop != baseline
    home_changed = home != baseline
    if laptop_changed and home_changed:
        return SyncDecision(Decision.CONFLICT, "both sides diverged from baseline")
    if laptop_changed:
        return SyncDecision(Decision.SEND_LAPTOP_TO_HOME, "only laptop changed")
    if home_changed:
        return SyncDecision(Decision.SEND_HOME_TO_LAPTOP, "only home changed")
    return SyncDecision(Decision.NO_CHANGE, "unchanged")
