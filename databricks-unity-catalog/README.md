# Databricks Unity Catalog

Unity Catalog 系統資料表和磁碟區 -- 查詢稽核日誌、血緣關係、帳單，以及管理磁碟區檔案操作。

## 概述

此技能提供使用 Unity Catalog 系統資料表和磁碟區的指南。當使用者查詢系統資料表（稽核、血緣關係、帳單、運算、作業、查詢歷史記錄）、執行磁碟區檔案操作（上傳、下載、列出檔案）或需要了解治理和存取控制時，此技能會啟動。該技能涵蓋 `system` 目錄結構描述、SQL 授權模式，以及用於系統資料表查詢和磁碟區管理的 MCP 工具整合。

## 包含內容

```
databricks-unity-catalog/
├── SKILL.md
├── 5-system-tables.md
└── 6-volumes.md
```

## 關鍵主題

- 系統資料表結構描述：`system.access`（稽核、血緣關係）、`system.billing`（使用量、成本）、`system.compute`（叢集、倉儲）、`system.lakeflow`（作業、管線）、`system.query`（查詢歷史記錄）、`system.storage`（儲存指標）
- 啟用系統結構描述並使用 SQL 授予存取權限
- 資料表和欄位層級的血緣關係查詢
- 稽核日誌分析：權限變更、資料存取追蹤
- 按工作區和 SKU 監控帳單和 DBU 消耗
- 磁碟區類型：託管 vs. 外部
- 磁碟區檔案操作：列出、上傳、下載、建立目錄
- 磁碟區路徑格式：`/Volumes/<catalog>/<schema>/<volume>/<path>`
- 最佳實踐：對大型系統資料表進行日期篩選、最小存取授權、排程監控報告

## 何時使用

- 查詢系統資料表以取得稽核、血緣關係、帳單或運算指標
- 在 Unity Catalog 磁碟區中上傳、下載或列出檔案
- 分析誰存取了特定資料表或變更了權限
- 監控跨工作區的 DBU 消耗和成本
- 追蹤資料表相依性和欄位層級血緣關係
- 檢閱作業執行歷史記錄和查詢效能
- 為系統資料設定治理和存取控制

## 相關技能

- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 用於寫入 Unity Catalog 資料表的管線
- [Databricks Jobs](../databricks-jobs/) -- 用於系統資料表中可見的作業執行資料
- [Synthetic Data Generation](../synthetic-data-generation/) -- 用於生成儲存在 Unity Catalog 磁碟區中的資料
- [AI/BI Dashboards](../aibi-dashboards/) -- 用於在 Unity Catalog 資料之上建立儀表板

## 資源

- [Unity Catalog 系統資料表](https://docs.databricks.com/administration-guide/system-tables/)
- [稽核日誌參考](https://docs.databricks.com/administration-guide/account-settings/audit-logs.html)
- [Unity Catalog 磁碟區](https://docs.databricks.com/en/connect/unity-catalog/volumes.html)
