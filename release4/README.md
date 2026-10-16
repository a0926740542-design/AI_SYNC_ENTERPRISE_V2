# AI_SYNC Enterprise V3.005-A Release 4 TEST
This is a test candidate, not a production release.
Run from the release4 directory:
```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m app.main
```
Config uses C:\AI_SYNC_TEST isolated folders.
Stop Release 3 before starting Release 4.
The previous backup is preserved in VERSION when changed content replaces it.
