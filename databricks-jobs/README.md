# Databricks Lakeflow Jobs

在 Databricks 上使用多任務 DAG、靈活的觸發器和全面的監控來編排資料工作流程。

## 概述

此技能涵蓋使用 Python SDK、CLI 或 Asset Bundles 建立、配置、執行和監控 Databricks Jobs。當使用者需要建立作業、設定排程或事件驅動觸發器、配置通知或管理作業執行時，此技能會啟動。該技能提供所有任務類型（notebook、Python、SQL、dbt、管線等）、觸發機制（cron、週期性、檔案到達、資料表更新、持續）和監控功能（電子郵件/webhook 通知、健康規則、重試、逾時）的完整參考資料。

## 包含內容

```
databricks-jobs/
├── SKILL.md
├── task-types.md
├── triggers-schedules.md
├── notifications-monitoring.md
└── examples.md
```

## 關鍵主題

- 帶有 `depends_on` 和條件式 `run_if` 邏輯的多任務 DAG 工作流程
- 任務類型：notebook、Spark Python、Python wheel、SQL、dbt、管線、Spark JAR、run-job、for-each
- 觸發器類型：cron 排程、週期性間隔、檔案到達、資料表更新、持續
- 運算配置：作業叢集、自動擴展、現有叢集、無伺服器
- 作業參數和在 notebook 中使用 `dbutils.widgets.get()` 存取
- 作業生命週期事件的電子郵件和 webhook 通知
- 健康規則、逾時配置和重試政策
- 執行佇列設定
- 權限模型（CAN_VIEW、CAN_MANAGE_RUN、CAN_MANAGE）
- Python SDK、CLI 和 Asset Bundle (DABs) 工作流程
- 完整範例：ETL 管線、排程重新整理、事件驅動管線、ML 訓練、多環境部署、串流作業、跨作業編排

## 何時使用

- 建立新的 Databricks 作業或工作流程
- 設定基於 cron 或事件驅動的作業排程
- 配置檔案到達或資料表更新觸發器
- 建立帶有任務相依性的多任務 DAG 管線
- 新增電子郵件或 webhook 通知和健康監控
- 透過 Python SDK 或 CLI 執行或管理作業
- 透過 Databricks Asset Bundles 部署作業
- 疑難排解作業失敗、排程問題或權限錯誤

## 相關技能

- [Asset Bundles](../asset-bundles/) -- 透過 Databricks Asset Bundles 部署作業
- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 配置由作業觸發的管線
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 追蹤作業執行歷史記錄的系統資料表

## 資源

- [Jobs API 參考](https://docs.databricks.com/api/workspace/jobs)
- [Jobs 文件](https://docs.databricks.com/en/jobs/index.html)
- [DABs 作業任務類型](https://docs.databricks.com/en/dev-tools/bundles/job-task-types.html)
- [Bundle 範例儲存庫](https://github.com/databricks/bundle-examples)
