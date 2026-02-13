# 觸發器和排程參考

## 目錄
- [Cron 排程](#cron-排程)
- [週期性觸發器](#週期性觸發器)
- [檔案到達觸發器](#檔案到達觸發器)
- [資料表更新觸發器](#資料表更新觸發器)
- [持續作業](#持續作業)
- [手動執行](#手動執行)

---

## Cron 排程

基於 cron 的排程執行作業。

### DABs YAML

```yaml
resources:
  jobs:
    daily_etl:
      name: "每日 ETL"
      schedule:
        quartz_cron_expression: "0 0 8 * * ?"  # 每日上午 8 點
        timezone_id: "America/New_York"
        pause_status: UNPAUSED
      tasks:
        - task_key: etl
          notebook_task:
            notebook_path: ../src/etl.py
```

### Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import CronSchedule, PauseStatus

w = WorkspaceClient()

job = w.jobs.create(
    name="每日 ETL",
    schedule=CronSchedule(
        quartz_cron_expression="0 0 8 * * ?",
        timezone_id="America/New_York",
        pause_status=PauseStatus.UNPAUSED
    ),
    tasks=[...]
)
```

### CLI JSON

```json
{
  "name": "每日 ETL",
  "schedule": {
    "quartz_cron_expression": "0 0 8 * * ?",
    "timezone_id": "America/New_York",
    "pause_status": "UNPAUSED"
  },
  "tasks": [...]
}
```

### Cron 表達式參考

格式：`秒 分 時 日 月 星期`

| 表達式 | 說明 |
|------------|-------------|
| `0 0 8 * * ?` | 每日上午 8:00 |
| `0 0 8 * * MON-FRI` | 工作日上午 8:00 |
| `0 0 */2 * * ?` | 每 2 小時 |
| `0 30 9 * * ?` | 每日上午 9:30 |
| `0 0 0 1 * ?` | 每月第一天午夜 |
| `0 0 6 ? * MON` | 每週一上午 6:00 |
| `0 0 8 15 * ?` | 每月 15 日上午 8:00 |
| `0 0 8 L * ?` | 每月最後一天上午 8:00 |

### 常見時區

| 時區 ID | 說明 |
|-------------|-------------|
| `UTC` | 協調世界時 |
| `America/New_York` | 美國東部時間 |
| `America/Chicago` | 美國中部時間 |
| `America/Denver` | 美國山區時間 |
| `America/Los_Angeles` | 美國太平洋時間 |
| `Europe/London` | 英國時間 |
| `Europe/Paris` | 中歐時間 |
| `Asia/Tokyo` | 日本標準時間 |
| `Asia/Taipei` | 台北時間 |

---

## 週期性觸發器

以固定間隔執行作業（比 cron 更簡單）。

### DABs YAML

```yaml
resources:
  jobs:
    hourly_sync:
      name: "每小時同步"
      trigger:
        pause_status: UNPAUSED
        periodic:
          interval: 1
          unit: HOURS
      tasks:
        - task_key: sync
          notebook_task:
            notebook_path: ../src/sync.py
```

### Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import TriggerSettings, Periodic, PeriodicTriggerConfigurationTimeUnit, PauseStatus

w = WorkspaceClient()

job = w.jobs.create(
    name="每小時同步",
    trigger=TriggerSettings(
        pause_status=PauseStatus.UNPAUSED,
        periodic=Periodic(
            interval=1,
            unit=PeriodicTriggerConfigurationTimeUnit.HOURS
        )
    ),
    tasks=[...]
)
```

### 間隔單位

| 單位 | 說明 |
|------|-------------|
| `HOURS` | 每 N 小時執行 |
| `DAYS` | 每 N 天執行 |
| `WEEKS` | 每 N 週執行 |

### 範例

```yaml
# 每 30 分鐘（不支援 - 使用 cron）
# 最小週期性間隔為 1 小時

# 每 4 小時
trigger:
  periodic:
    interval: 4
    unit: HOURS

# 每 2 天
trigger:
  periodic:
    interval: 2
    unit: DAYS

# 每週
trigger:
  periodic:
    interval: 1
    unit: WEEKS
```

---

## 檔案到達觸發器

當新檔案到達雲端儲存時執行作業。

### DABs YAML

```yaml
resources:
  jobs:
    process_uploads:
      name: "處理上傳"
      trigger:
        pause_status: UNPAUSED
        file_arrival:
          url: "abfss://container@account.dfs.core.windows.net/uploads/"
          min_time_between_triggers_seconds: 60
          wait_after_last_change_seconds: 30
      tasks:
        - task_key: process
          notebook_task:
            notebook_path: ../src/process_files.py
```

### Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import TriggerSettings, FileArrivalTriggerConfiguration, PauseStatus

w = WorkspaceClient()

job = w.jobs.create(
    name="處理上傳",
    trigger=TriggerSettings(
        pause_status=PauseStatus.UNPAUSED,
        file_arrival=FileArrivalTriggerConfiguration(
            url="abfss://container@account.dfs.core.windows.net/uploads/",
            min_time_between_triggers_seconds=60,
            wait_after_last_change_seconds=30
        )
    ),
    tasks=[...]
)
```

### 參數

| 參數 | 必要 | 說明 |
|-----------|----------|-------------|
| `url` | 是 | 要監控的雲端儲存 URL |
| `min_time_between_triggers_seconds` | 否 | 觸發器之間的最小等待時間（預設：0） |
| `wait_after_last_change_seconds` | 否 | 最後一次檔案變更後的等待時間（預設：0） |

### 支援的 URL 格式

| 雲端 | 格式 | 範例 |
|-------|--------|---------|
| AWS S3 | `s3://bucket/path/` | `s3://my-bucket/data/uploads/` |
| Azure ADLS | `abfss://container@account.dfs.core.windows.net/path/` | `abfss://data@myaccount.dfs.core.windows.net/uploads/` |
| GCS | `gs://bucket/path/` | `gs://my-bucket/uploads/` |
| Unity Catalog 磁碟區 | `/Volumes/catalog/schema/volume/path/` | `/Volumes/main/data/uploads/` |

### 在 Notebook 中存取檔案資訊

```python
# 觸發器透過任務上下文提供檔案資訊
import json

# 從作業上下文取得觸發器資訊
trigger_info = dbutils.jobs.taskValues.get(
    taskKey="__trigger_info__",
    key="file_arrival",
    debugValue={}
)

# 包含：url、files（新檔案列表）
print(f"新檔案：{trigger_info.get('files', [])}")
```

---

## 資料表更新觸發器

當 Unity Catalog 資料表更新時執行作業。

### DABs YAML

```yaml
resources:
  jobs:
    process_updates:
      name: "處理資料表更新"
      trigger:
        pause_status: UNPAUSED
        table_update:
          table_names:
            - "catalog.schema.source_table"
            - "catalog.schema.other_table"
          condition: ANY_UPDATED
          min_time_between_triggers_seconds: 300
          wait_after_last_change_seconds: 60
      tasks:
        - task_key: process
          notebook_task:
            notebook_path: ../src/process_changes.py
```

### Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import (
    TriggerSettings,
    TableUpdateTriggerConfiguration,
    Condition,
    PauseStatus
)

w = WorkspaceClient()

job = w.jobs.create(
    name="處理資料表更新",
    trigger=TriggerSettings(
        pause_status=PauseStatus.UNPAUSED,
        table_update=TableUpdateTriggerConfiguration(
            table_names=["catalog.schema.source_table"],
            condition=Condition.ANY_UPDATED,
            min_time_between_triggers_seconds=300,
            wait_after_last_change_seconds=60
        )
    ),
    tasks=[...]
)
```

### 參數

| 參數 | 必要 | 說明 |
|-----------|----------|-------------|
| `table_names` | 是 | 要監控的 Unity Catalog 資料表列表 |
| `condition` | 否 | `ANY_UPDATED`（預設）- 當任何資料表更新時觸發 |
| `min_time_between_triggers_seconds` | 否 | 觸發器之間的最小等待時間 |
| `wait_after_last_change_seconds` | 否 | 最後一次變更後的等待時間 |

### 需求

- 資料表必須在 Unity Catalog 中
- 作業身分需要對監控的資料表具有 `SELECT` 權限
- 適用於 Delta 資料表（託管和外部）

---

## 持續作業

始終執行並自動重新啟動的作業。

### DABs YAML

```yaml
resources:
  jobs:
    streaming_job:
      name: "串流處理器"
      continuous:
        pause_status: UNPAUSED
      tasks:
        - task_key: stream
          notebook_task:
            notebook_path: ../src/streaming_processor.py
```

### Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Continuous, PauseStatus

w = WorkspaceClient()

job = w.jobs.create(
    name="串流處理器",
    continuous=Continuous(
        pause_status=PauseStatus.UNPAUSED
    ),
    tasks=[...]
)
```

### 持續作業行為

- 作業在建立/取消暫停時立即執行
- 完成或失敗後自動重新啟動
- 一次維持一個活躍執行
- 使用 `pause_status: PAUSED` 停止

### 控制持續作業

```python
# 暫停持續作業
w.jobs.update(
    job_id=12345,
    new_settings=JobSettings(
        continuous=Continuous(pause_status=PauseStatus.PAUSED)
    )
)

# 恢復持續作業
w.jobs.update(
    job_id=12345,
    new_settings=JobSettings(
        continuous=Continuous(pause_status=PauseStatus.UNPAUSED)
    )
)
```

---

## 手動執行

按需執行作業，無需自動觸發器。

### 無觸發器配置

只需省略 `schedule`、`trigger` 和 `continuous`：

```yaml
resources:
  jobs:
    manual_job:
      name: "手動作業"
      # 無 schedule/trigger = 僅手動
      tasks:
        - task_key: run
          notebook_task:
            notebook_path: ../src/manual_task.py
```

### 觸發手動執行

**Python SDK：**
```python
# 使用預設參數執行
run = w.jobs.run_now(job_id=12345)

# 使用自訂參數執行
run = w.jobs.run_now(
    job_id=12345,
    job_parameters={"env": "prod", "date": "2024-01-15"}
)

# 等待完成
run_result = w.jobs.run_now_and_wait(job_id=12345)
```

**CLI：**
```bash
# 執行作業
databricks jobs run-now 12345

# 使用參數執行
databricks jobs run-now 12345 --job-params '{"env": "prod"}'
```

**DABs：**
```bash
databricks bundle run my_job_resource_key
```

---

## 組合觸發器

一個作業可以有多種觸發器類型（獨立評估）：

```yaml
resources:
  jobs:
    multi_trigger:
      name: "多觸發器作業"
      # Cron 排程
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"
        timezone_id: "UTC"
        pause_status: UNPAUSED
      # 也在檔案到達時觸發
      trigger:
        pause_status: UNPAUSED
        file_arrival:
          url: "abfss://container@account.dfs.core.windows.net/urgent/"
      tasks:
        - task_key: process
          notebook_task:
            notebook_path: ../src/process.py
```

### 觸發器優先順序

當多個觸發器同時觸發時：
- 如果 `max_concurrent_runs > 1`，作業會將執行排入佇列
- 否則，當有執行處於活躍狀態時，後續觸發器會被跳過

```yaml
max_concurrent_runs: 1  # 一次只執行一個（預設）
```

---

## 暫停和恢復

### 暫停排程作業

```yaml
schedule:
  quartz_cron_expression: "0 0 8 * * ?"
  timezone_id: "UTC"
  pause_status: PAUSED  # 作業不會按排程執行
```

### 透過 SDK 暫停

```python
from databricks.sdk.service.jobs import JobSettings, CronSchedule, PauseStatus

w.jobs.update(
    job_id=12345,
    new_settings=JobSettings(
        schedule=CronSchedule(
            quartz_cron_expression="0 0 8 * * ?",
            timezone_id="UTC",
            pause_status=PauseStatus.PAUSED
        )
    )
)
```

### 透過 CLI 暫停

```bash
databricks jobs update 12345 --json '{
  "new_settings": {
    "schedule": {
      "pause_status": "PAUSED"
    }
  }
}'
```
