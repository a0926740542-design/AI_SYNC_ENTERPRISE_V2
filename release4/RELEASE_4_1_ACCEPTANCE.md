# AI_SYNC Enterprise V3.005-A — Release 4.1 封版驗收紀錄

- 版本：v3.005-a-r4.1
- 驗收日期：2026-10-19
- 驗收平台：Windows / Python 3.14
- 原始分支：release/v3.005-a-r4-test
- 驗收分支：release/v3.005-a-r4.1-test
- 範圍：release4/
- 狀態：使用者回報功能驗收通過；Git Tag 與 GitHub Release 須另外發布

## 變更項目

1. 增加相同 SOURCE、BACKUP、VERSION 設定的單一執行個體鎖。
2. 增加目的檔案的跨程序互斥，涵蓋比較、VERSION 備份與原子替換。
3. 重複啟動回傳 exit code 2，並寫入 error.log。
4. 啟動與停止日誌加入 PID。
5. 新增跨程序版本保存及執行個體鎖測試。

## Windows 實機驗收（使用者提供的終端輸出）

| 驗收項目 | 結果 |
| --- | --- |
| pytest | 10 passed in 2.27s |
| 第二次啟動 | AI_SYNC already running |
| 重複啟動退出碼 | 2 |
| error.log | 已記錄重複啟動 |
| 全部停止後重新啟動 | 成功 |
| 連續寫入 10 次後 SOURCE | AI_SYNC R4.1 FINAL TEST 10 |
| 連續寫入 10 次後 BACKUP | AI_SYNC R4.1 FINAL TEST 10 |
| VERSION 數量 | 1 |
| VERSION 內容 | R41_BASE |

## 已知限制及部署前注意事項

- 單一執行個體鎖只約束採用相同鎖定機制的版本；**舊版 R4 不會自動受到保護**。部署前須停止舊版監控程序。
- 此次驗收未涵蓋斷電、網路磁碟中斷、大型 DWG 正在寫入等情況。
- `config/config.json` 的 `project_name` 仍顯示 `R4 TEST`，不影響程式鎖定，但正式部署前可更新。
- 建議先在 `C:\AI_SYNC_TEST` 測試環境使用，正式工程檔案部署需另行驗收。
- 此紀錄是封版依據；Git Tag 和 GitHub Release 只有在 GitHub 確認建立後才算正式發布。

## GitHub Release 說明（建議內容）

**AI_SYNC Enterprise V3.005-A Release 4.1**

This release adds single-instance protection and per-destination inter-process locking to prevent duplicate VERSION snapshots. Windows acceptance: 10/10 pytest tests, second instance rejected with exit code 2, restart succeeds, and a ten-write stress test ends with matching SOURCE/BACKUP and one prior VERSION snapshot.

Known limitation: older R4 processes are not blocked by the new lock. Stop them before deployment. Network interruptions, power loss and large DWG write-in-progress scenarios require additional validation.
