import pytest

from app.bidirectional_decisions import Decision, decide
from app.bidirectional_state import SyncState


@pytest.mark.parametrize("base,laptop,home,expected", [
    ("old", "new", "old", Decision.SEND_LAPTOP_TO_HOME),
    ("old", "old", "new", Decision.SEND_HOME_TO_LAPTOP),
    ("old", "left", "right", Decision.CONFLICT),
    ("old", "new", "new", Decision.NO_CHANGE),
    ("old", "old", "old", Decision.NO_CHANGE),
    (None, "left", "right", Decision.CONFLICT),
    (None, "new", None, Decision.SEND_LAPTOP_TO_HOME),
    (None, None, "new", Decision.SEND_HOME_TO_LAPTOP),
    ("old", None, "old", Decision.CONFLICT),
    ("old", "old", None, Decision.CONFLICT),
    ("old", None, None, Decision.CONFLICT),
])
def test_three_way_decision(base, laptop, home, expected):
    assert decide(base, laptop, home).action == expected


def test_state_survives_restart_and_keeps_conflict(tmp_path):
    database = tmp_path / "metadata" / "state.db"
    first = SyncState(database)
    first.acknowledge("CAD/A101.dwg", "old")
    first.record_conflict("CAD/A101.dwg", "old", "laptop", "home")
    second = SyncState(database)
    assert second.baseline("CAD/A101.dwg") == "old"
    assert second.unresolved_conflicts() == [
        ("CAD/A101.dwg", "old", "laptop", "home")
    ]


def test_reject_parent_path(tmp_path):
    state = SyncState(tmp_path / "state.db")
    with pytest.raises(ValueError):
        state.acknowledge("../escape.dwg", "hash")
