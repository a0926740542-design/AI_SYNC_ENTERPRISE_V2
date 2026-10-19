# AI_SYNC Enterprise V3.005-A — Release 4.1 test

This branch is based on `release/v3.005-a-r4-test`. Release 4 is unchanged.

## Changes
- Instance-level OS lock keyed by resolved source, backup and version folders; a second launch exits with code 2 and logs an error.
- Per-destination inter-process lock around comparison, VERSION snapshot and atomic replacement.
- Start/stop system log includes the Python PID.
- Added multiprocessing and lock regression tests.

Lock files live under the operating system temporary directory in `ai_sync_locks`. They are **not deleted** on release, since deleting an active lock file would defeat cross-process exclusion. Operating system locks release when a process exits, including a crash.

## Windows validation (PowerShell)
Stop previous AI_SYNC processes first. In the extracted `release4` folder:

```powershell
python -m pytest -q
python -m app.main
```

In a second PowerShell window, from the same folder, run `python -m app.main`. It should print `AI_SYNC already running` and exit. Stop the first window with Ctrl+C and verify that starting again succeeds.

Test with isolated `C:\AI_SYNC_TEST` folders before production use.

**Status:** Code published for testing; not certified or production-released. GitHub publication is not proof that Windows integration tests passed.
