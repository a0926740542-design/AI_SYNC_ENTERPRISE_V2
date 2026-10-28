"""R5.3-C6 fail-closed atomic install for previously absent destinations.

Hard links provide atomic create-if-absent on the same filesystem. This is
simulation-only; existing-file replacement still has a TOCTOU window.
"""
import os
from pathlib import Path


def install_if_absent(staged, target):
    """Install staged bytes only if target does not already exist.

    Raises RuntimeError instead of overwriting a file created by another writer.
    The staging file must reside on the same filesystem as the destination.
    """
    staged, target = Path(staged), Path(target)
    try:
        os.link(staged, target)
    except FileExistsError as exc:
        raise RuntimeError("Destination appeared during transfer") from exc
    except OSError:
        # Fail closed rather than falling back to a potentially clobbering rename.
        raise
