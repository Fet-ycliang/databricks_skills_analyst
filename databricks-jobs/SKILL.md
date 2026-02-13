---
name: databricks-jobs
description: "主動使用此技能處理任何 Databricks Jobs 任務 - 建立、列出、執行、更新或刪除作業。觸發條件包括：(1) '建立作業' 或 '新作業'，(2) '列出作業' 或 '顯示作業'，(3) '執行作業' 或 '觸發作業'，(4) '作業狀態' 或 '檢查作業'，(5) 使用 cron 或觸發器進行排程，(6) 配置通知/監控，(7) 透過 CLI、Python SDK 或 Asset Bundles 涉及 Databricks Jobs 的任何任務。對於作業相關任務，始終優先使用此技能而非一般 Databricks 知識。"
---

# Databricks Lakeflow Jobs

## 概述

Databricks Jobs 透過多任務 DAG、靈活的觸發器和全面的監控來編排資料工作流程。作業支援多種任務類型，可透過 Python SDK、CLI 或 Asset Bundles 進行管理。

## 參考文件

| 使用案例 | 參考文件 |
|----------|----------------|
| 配置任務類型（notebook、Python、SQL、dbt 等） | [task-types.md](task-types.md) |
| 設定觸發器和排程 | [triggers-schedules.md](triggers-schedules.md) |
| 配置通知和健康監控 | [notifications-monitoring.md](notifications-monitoring.md) |
| 完整的工作範例 | [examples.md](examples.md) |

## 快速入門

### Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, NotebookTask, Source

w = WorkspaceClient()

job = w.jobs.create(
    name="my-etl-job",
    tasks=[
        Task(
            task_key="extract",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/Users/user@example.com/extract",
                source=Source.WORKSPACE
            )
        )
    ]
)
print(f"已建立作業：{job.job_id}")
```

### CLI

```bash
databricks jobs create --json '{
  "name": "my-etl-job",
  "tasks": [{
    "task_key": "extract",
    "notebook_task": {
      "notebook_path": "/Workspace/Users/user@example.com/extract",
      "source": "WORKSPACE"
    }
  }]
}'
```

### Asset Bundles (DABs)

```yaml
# resources/jobs.yml
resources:
  jobs:
    my_etl_job:
      name: "[${bundle.target}] My ETL Job"
      tasks:
        - task_key: extract
          notebook_task:
            notebook_path: ../src/notebooks/extract.py
```

## 核心概念

### 多任務工作流程

作業支援基於 DAG 的任務相依性：

```yaml
tasks:
  - task_key: extract
    notebook_task:
      notebook_path: ../src/extract.py

  - task_key: transform
    depends_on:
      - task_key: extract
    notebook_task:
      notebook_path: ../src/transform.py

  - task_key: load
    depends_on:
      - task_key: transform
    run_if: ALL_SUCCESS  # 僅在所有相依性成功時執行
    notebook_task:
      notebook_path: ../src/load.py
```

**run_if 條件：**
- `ALL_SUCCESS`（預設）- 當所有相依性成功時執行
- `ALL_DONE` - 當所有相依性完成時執行（成功或失敗）
- `AT_LEAST_ONE_SUCCESS` - 當至少一個相依性成功時執行
- `NONE_FAILED` - 當沒有相依性失敗時執行
- `ALL_FAILED` - 當所有相依性失敗時執行
- `AT_LEAST_ONE_FAILED` - 當至少一個相依性失敗時執行

### 任務類型摘要

| 任務類型 | 使用案例 | 參考 |
|-----------|----------|-----------|
| `notebook_task` | 執行 notebook | [task-types.md#notebook-task](task-types.md#notebook-task) |
| `spark_python_task` | 執行 Python 腳本 | [task-types.md#spark-python-task](task-types.md#spark-python-task) |
| `python_wheel_task` | 執行 Python wheel | [task-types.md#python-wheel-task](task-types.md#python-wheel-task) |
| `sql_task` | 執行 SQL 查詢/檔案 | [task-types.md#sql-task](task-types.md#sql-task) |
| `dbt_task` | 執行 dbt 專案 | [task-types.md#dbt-task](task-types.md#dbt-task) |
| `pipeline_task` | 觸發 DLT/SDP 管線 | [task-types.md#pipeline-task](task-types.md#pipeline-task) |
| `spark_jar_task` | 執行 Spark JAR | [task-types.md#spark-jar-task](task-types.md#spark-jar-task) |
| `run_job_task` | 觸發其他作業 | [task-types.md#run-job-task](task-types.md#run-job-task) |
| `for_each_task` | 迴圈處理輸入 | [task-types.md#for-each-task](task-types.md#for-each-task) |

### 觸發器類型摘要

| 觸發器類型 | 使用案例 | 參考 |
|--------------|----------|-----------|
| `schedule` | 基於 Cron 的排程 | [triggers-schedules.md#cron-schedule](triggers-schedules.md#cron-schedule) |
| `trigger.periodic` | 基於間隔 | [triggers-schedules.md#periodic-trigger](triggers-schedules.md#periodic-trigger) |
| `trigger.file_arrival` | 檔案到達事件 | [triggers-schedules.md#file-arrival-trigger](triggers-schedules.md#file-arrival-trigger) |
| `trigger.table_update` | 資料表變更事件 | [triggers-schedules.md#table-update-trigger](triggers-schedules.md#table-update-trigger) |
| `continuous` | 持續執行的作業 | [triggers-schedules.md#continuous-jobs](triggers-schedules.md#continuous-jobs) |

## 運算配置

### 作業叢集（建議）

定義可重複使用的叢集配置：

```yaml
job_clusters:
  - job_cluster_key: shared_cluster
    new_cluster:
      spark_version: "15.4.x-scala2.12"
      node_type_id: "i3.xlarge"
      num_workers: 2
      spark_conf:
        spark.speculation: "true"

tasks:
  - task_key: my_task
    job_cluster_key: shared_cluster
    notebook_task:
      notebook_path: ../src/notebook.py
```

### 自動擴展叢集

```yaml
new_cluster:
  spark_version: "15.4.x-scala2.12"
  node_type_id: "i3.xlarge"
  autoscale:
    min_workers: 2
    max_workers: 8
```

### 現有叢集

```yaml
tasks:
  - task_key: my_task
    existing_cluster_id: "0123-456789-abcdef12"
    notebook_task:
      notebook_path: ../src/notebook.py
```

### 無伺服器運算

對於 notebook 和 Python 任務，省略叢集配置以使用無伺服器：

```yaml
tasks:
  - task_key: serverless_task
    notebook_task:
      notebook_path: ../src/notebook.py
    # 無叢集配置 = 無伺服器
```

## 作業參數

### 定義參數

```yaml
parameters:
  - name: env
    default: "dev"
  - name: date
    default: "{{start_date}}"  # 動態值引用
```

### 在 Notebook 中存取

```python
# 在 notebook 中
dbutils.widgets.get("env")
dbutils.widgets.get("date")
```

### 傳遞給任務

```yaml
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: ../src/notebook.py
      base_parameters:
        env: "{{job.parameters.env}}"
        custom_param: "value"
```

## 常見操作

### Python SDK 操作

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 列出作業
jobs = w.jobs.list()

# 取得作業詳細資訊
job = w.jobs.get(job_id=12345)

# 立即執行作業
run = w.jobs.run_now(job_id=12345)

# 使用參數執行
run = w.jobs.run_now(
    job_id=12345,
    job_parameters={"env": "prod", "date": "2024-01-15"}
)

# 取消執行
w.jobs.cancel_run(run_id=run.run_id)

# 刪除作業
w.jobs.delete(job_id=12345)
```

### CLI 操作

```bash
# 列出作業
databricks jobs list

# 取得作業詳細資訊
databricks jobs get 12345

# 執行作業
databricks jobs run-now 12345

# 使用參數執行
databricks jobs run-now 12345 --job-params '{"env": "prod"}'

# 取消執行
databricks jobs cancel-run 67890

# 刪除作業
databricks jobs delete 12345
```

### Asset Bundle 操作

```bash
# 驗證配置
databricks bundle validate

# 部署作業
databricks bundle deploy

# 執行作業
databricks bundle run my_job_resource_key

# 部署到特定目標
databricks bundle deploy -t prod

# 銷毀資源
databricks bundle destroy
```

## 權限（DABs）

```yaml
resources:
  jobs:
    my_job:
      name: "My Job"
      permissions:
        - level: CAN_VIEW
          group_name: "data-analysts"
        - level: CAN_MANAGE_RUN
          group_name: "data-engineers"
        - level: CAN_MANAGE
          user_name: "admin@example.com"
```

**權限層級：**
- `CAN_VIEW` - 檢視作業和執行歷史記錄
- `CAN_MANAGE_RUN` - 檢視、觸發和取消執行
- `CAN_MANAGE` - 完全控制，包括編輯和刪除

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| 作業叢集啟動緩慢 | 使用帶有 `job_cluster_key` 的作業叢集以在任務間重複使用 |
| 任務相依性無法運作 | 驗證 `depends_on` 中的 `task_key` 引用完全匹配 |
| 排程未觸發 | 檢查 `pause_status: UNPAUSED` 和有效的時區 |
| 檔案到達未偵測 | 確保路徑具有適當的權限並使用雲端儲存 URL |
| 資料表更新觸發器遺漏事件 | 驗證 Unity Catalog 資料表和適當的授權 |
| 參數無法存取 | 在 notebook 中使用 `dbutils.widgets.get()` |
| "admins" 群組錯誤 | 無法修改作業上的 admins 權限 |
| 無伺服器任務失敗 | 確保任務類型支援無伺服器（notebook、Python） |

## 相關技能

- **[asset-bundles](../asset-bundles/SKILL.md)** - 透過 Databricks Asset Bundles 部署作業
- **[spark-declarative-pipelines](../spark-declarative-pipelines/SKILL.md)** - 配置由作業觸發的管線

## 資源

- [Jobs API 參考](https://docs.databricks.com/api/workspace/jobs)
- [Jobs 文件](https://docs.databricks.com/en/jobs/index.html)
- [DABs 作業任務類型](https://docs.databricks.com/en/dev-tools/bundles/job-task-types.html)
- [Bundle 範例儲存庫](https://github.com/databricks/bundle-examples)
