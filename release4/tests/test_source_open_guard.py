import os
import subprocess
import sys

import pytest

from app.source_open_guard import SourceBusyError, assert_exclusively_openable


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_exclusive_guard_rejects_open_writer(tmp_path):
    target = tmp_path / "drawing.dwg"
    target.write_bytes(b"PARTIAL")
    child_code = (
        "import pathlib,sys,time\n"
        "p=pathlib.Path(sys.argv[1])\n"
        "with p.open('ab') as f:\n"
        " print('READY',flush=True)\n"
        " time.sleep(5)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", child_code, str(target)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        assert process.stdout.readline().strip() == "READY"
        with pytest.raises(SourceBusyError):
            assert_exclusively_openable(target)
    finally:
        process.terminate()
        process.communicate(timeout=10)
    assert_exclusively_openable(target)
