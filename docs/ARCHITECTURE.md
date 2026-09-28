\# AI\_SYNC Enterprise V2 Architecture



\## Vision



AI\_SYNC Enterprise V2 is an enterprise-grade file synchronization and audit platform.



\---



\# Core Modules



\## 1. Config Module



\- config\_loader.py

\- Read JSON configuration

\- Validate settings



\---



\## 2. Logger Module



\- logger.py



Log Types



\- transfer.log

\- system.log

\- error.log

\- audit.log



\---



\## 3. Sync Module



Components



\- event\_handler.py

\- queue\_manager.py

\- file\_copier.py

\- sync\_engine.py



Responsibilities



\- Watchdog monitoring

\- Queue events

\- Remove duplicate events

\- Copy files



\---



\## 4. Version Module



\- version\_engine.py



Responsibilities



\- Version backup

\- Timestamp naming

\- History retention



\---



\## 5. Audit Module



\- audit\_engine.py



Responsibilities



\- SQLite database

\- Operation history

\- User information

\- Machine information



\---



\## 6. Hash Module



\- hash\_engine.py



Responsibilities



\- SHA256 verification

\- Integrity checking



\---



\# Future Modules



\- AutoCAD Engine

\- Excel Engine

\- RC Quantity Engine

\- AI Bridge Interface



\---



\# System Flow



Config

&#x20;   ↓

Logger

&#x20;   ↓

Sync Engine

&#x20;   ↓

Queue Manager

&#x20;   ↓

File Copier

&#x20;   ↓

Version Engine

&#x20;   ↓

Audit Engine

&#x20;   ↓

SQLite

