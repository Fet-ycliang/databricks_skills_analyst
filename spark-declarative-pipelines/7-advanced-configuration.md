# 進階管線設定 (`extra_settings`)

預設情況下，管線會使用 **Serverless Compute 與 Unity Catalog** 建立。僅在進階使用案例時使用 `extra_settings` 參數。

**重要：除非使用者明確要求，否則請勿使用 `extra_settings` 將 `serverless` 設為 `false`：**
- R 語言支援
- Spark RDD APIs
- JAR 函式庫或 Maven 座標

## 何時使用 `extra_settings`

- **開發模式**: 透過寬鬆的驗證加速迭代
- **連續管線 (Continuous)**: 即時串流而非觸發執行
- **事件日誌**: 自訂事件日誌資料表位置
- **管線 Metadata**: Tags, 設定變數
- **Python 依賴**: 為 Serverless 管線安裝 pip 套件
- **Classic Clusters** (罕見): 僅當使用者明確需要 R, RDD APIs 或 JARs 時

## `extra_settings` 參數參考

### 頂層欄位

| 欄位 | 類型 | 預設值 | 描述 |
|-------|------|---------|-------------|
| `serverless` | bool | `true` | 使用 Serverless Compute。設為 `false` 則使用專用叢集。 |
| `continuous` | bool | `false` | `true` = 永遠執行 (即時), `false` = 觸發執行 |
| `development` | bool | `false` | 開發模式：加速啟動，寬鬆驗證，無重試 |
| `photon` | bool | `false` | 啟用 Photon 向量化查詢引擎 |
| `edition` | str | `"CORE"` | `"CORE"`, `"PRO"`, 或 `"ADVANCED"`. CDC 需要 Advanced。 |
| `channel` | str | `"CURRENT"` | `"CURRENT"` (穩定) 或 `"PREVIEW"` (最新功能) |
| `clusters` | list | `[]` | 叢集設定 (若 `serverless=false` 則為必填) |
| `configuration` | dict | `{}` | Spark 設定鍵值對 (所有值必須是字串) |
| `tags` | dict | `{}` | 管線 Metadata Tags (最多 25 個) |
| `event_log` | dict | auto | 自訂事件日誌資料表位置 |
| `notifications` | list | `[]` | 管線事件的 Email/Webhook 警報 |
| `id` | str | - | 強制更新特定 Pipeline ID |
| `allow_duplicate_names` | bool | `false` | 允許相同名稱的多個管線 |
| `budget_policy_id` | str | - | 用於成本追蹤的預算策略 ID |
| `storage` | str | - | Checkpoints/Tables 的 DBFS 根目錄 (舊版，請改用 Unity Catalog) |
| `target` | str | - | **已棄用**: 請改用 `schema` 參數 |
| `dry_run` | bool | `false` | 驗證管線而不建立 (僅建立) |
| `run_as` | dict | - | 以特定使用者/Service Principal 身份執行管線 |
| `restart_window` | dict | - | 連續管線重啟的維護視窗 |
| `filters` | dict | - | 包含/排除管線中的特定路徑 |
| `trigger` | dict | - | **已棄用**: 請改用 `continuous` |
| `deployment` | dict | - | 部署方法 (BUNDLE 或 DEFAULT) |
| `environment` | dict | - | Serverless 的 Python pip 依賴 |
| `gateway_definition` | dict | - | CDC Gateway 管線設定 |
| `ingestion_definition` | dict | - | 託管攝取設定 (Salesforce, Workday 等) |
| `usage_policy_id` | str | - | 使用策略 ID |

### `clusters` 陣列 - 叢集設定

每個叢集物件支援這些欄位：

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `label` | str | **必填**。主要叢集為 `"default"`，維護任務為 `"maintenance"` |
| `num_workers` | int | 固定 Worker 數量 (使用此項或 autoscale，不可兩者皆用) |
| `autoscale` | dict | `{"min_workers": 1, "max_workers": 4, "mode": "ENHANCED"}` |
| `node_type_id` | str | 實例類型，例如 `"i3.xlarge"`, `"Standard_DS3_v2"` |
| `driver_node_type_id` | str | Driver 實例類型 (預設為 node_type_id) |
| `instance_pool_id` | str | 使用此 Pool 的實例 (加速啟動) |
| `driver_instance_pool_id` | str | Driver 節點的 Pool |
| `spark_conf` | dict | 此叢集的 Spark 設定 |
| `spark_env_vars` | dict | 環境變數 |
| `custom_tags` | dict | 應用於雲端資源的 Tags |
| `init_scripts` | list | Init Script 位置 |
| `aws_attributes` | dict | AWS 專屬: `{"availability": "SPOT", "zone_id": "us-west-2a"}` |
| `azure_attributes` | dict | Azure 專屬: `{"availability": "SPOT_AZURE"}` |
| `gcp_attributes` | dict | GCP 專屬設定 |

**Autoscale 模式**: `"LEGACY"` 或 `"ENHANCED"` (推薦，針對 DLT 工作負載優化)

### `event_log` 物件 - 自訂事件日誌位置

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `catalog` | str | 事件日誌資料表的 Unity Catalog 名稱 |
| `schema` | str | 事件日誌資料表的 Schema 名稱 |
| `name` | str | 事件日誌的資料表名稱 |

### `notifications` 陣列 - 警報設定

每個通知物件：

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `email_recipients` | list | Email 地址列表 |
| `alerts` | list | 觸發警報的事件: `"on-update-success"`, `"on-update-failure"`, `"on-update-fatal-failure"`, `"on-flow-failure"` |

### `configuration` Dict - Spark/Pipeline 設定

常見設定鍵 (所有值必須是字串)：

| 鍵 | 描述 |
|-----|-------------|
| `spark.sql.shuffle.partitions` | Shuffle 分區數量 (`"auto"` 推薦) |
| `pipelines.numRetries` | 瞬時失敗的重試次數 |
| `pipelines.trigger.interval` | 連續管線的觸發間隔，例如 `"1 hour"` |
| `spark.databricks.delta.preview.enabled` | 啟用 Delta 預覽功能 (`"true"`) |

### `run_as` 物件 - 管線執行身分

指定執行管線的使用者或 Service Principal：

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `user_name` | str | Workspace 使用者的 Email (僅能設為自己的 Email) |
| `service_principal_name` | str | Service Principal 的 Application ID (需要 servicePrincipal/user 角色) |

**注意**: 只能設定 `user_name` 或 `service_principal_name` 其中之一。

### `restart_window` 物件 - 連續管線重啟排程

對於連續管線，定義何時可以發生重啟：

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `start_hour` | int | **必填**。5 小時重啟視窗開始的小時 (0-23) |
| `days_of_week` | list | 允許的天數: `"MONDAY"`, `"TUESDAY"` 等 (預設: 每天) |
| `time_zone_id` | str | 時區，例如 `"America/Los_Angeles"` (預設: UTC) |

### `filters` 物件 - 路徑過濾

包含或排除管線中的特定路徑：

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `include` | list | 包含的路徑列表 |
| `exclude` | list | 排除的路徑列表 |

### `environment` 物件 - Python 依賴 (Serverless)

為 Serverless 管線安裝 pip 依賴：

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `dependencies` | list | pip requirements 列表 (例如 `["pandas==2.0.0", "requests"]`) |

### `deployment` 物件 - 部署方法

| 欄位 | 類型 | 描述 |
|-------|------|-------------|
| `kind` | str | `"BUNDLE"` (Databricks Asset Bundles) 或 `"DEFAULT"` |
| `metadata_file_path` | str | 部署 Metadata 檔案的路徑 |

### 版本比較 (Edition Comparison)

| 功能 | CORE | PRO | ADVANCED |
|---------|------|-----|----------|
| 串流資料表 | Yes | Yes | Yes |
| 物化視圖 | Yes | Yes | Yes |
| Expectations (資料品質) | Yes | Yes | Yes |
| Change Data Capture (CDC) | No | No | Yes |
| SCD Type 1/2 | No | No | Yes |

## 設定範例

### 開發模式管線

使用 `create_or_update_pipeline` 工具搭配：
- `name`: "my_dev_pipeline"
- `root_path`: "/Workspace/Users/user@example.com/my_pipeline"
- `catalog`: "dev_catalog"
- `schema`: "dev_schema"
- `workspace_file_paths`: [...]
- `start_run`: true
- `extra_settings`:
```json
{
    "development": true,
    "tags": {"environment": "development", "owner": "data-team"}
}
```

### 非 Serverless 搭配專用叢集

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "serverless": false,
    "clusters": [{
        "label": "default",
        "num_workers": 4,
        "node_type_id": "i3.xlarge",
        "custom_tags": {"cost_center": "analytics"}
    }],
    "photon": true,
    "edition": "ADVANCED"
}
```

### 連續串流管線

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "continuous": true,
    "configuration": {
        "spark.sql.shuffle.partitions": "auto"
    }
}
```

### 使用 Instance Pool

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "serverless": false,
    "clusters": [{
        "label": "default",
        "instance_pool_id": "0727-104344-hauls13-pool-xyz",
        "num_workers": 2,
        "custom_tags": {"project": "analytics"}
    }]
}
```

### 自訂事件日誌位置

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "event_log": {
        "catalog": "audit_catalog",
        "schema": "pipeline_logs",
        "name": "my_pipeline_events"
    }
}
```

### 具備 Email 通知的管線

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "notifications": [{
        "email_recipients": ["team@example.com", "oncall@example.com"],
        "alerts": ["on-update-failure", "on-update-fatal-failure", "on-flow-failure"]
    }]
}
```

### 具備 Autoscaling 的生產管線

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "serverless": false,
    "development": false,
    "photon": true,
    "edition": "ADVANCED",
    "clusters": [{
        "label": "default",
        "autoscale": {
            "min_workers": 2,
            "max_workers": 8,
            "mode": "ENHANCED"
        },
        "node_type_id": "i3.xlarge",
        "spark_conf": {
            "spark.sql.adaptive.enabled": "true"
        },
        "custom_tags": {"environment": "production"}
    }],
    "notifications": [{
        "email_recipients": ["data-team@example.com"],
        "alerts": ["on-update-failure"]
    }]
}
```

### 以 Service Principal 執行

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "run_as": {
        "service_principal_name": "00000000-0000-0000-0000-000000000000"
    }
}
```

### 具備重啟視窗的連續管線

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "continuous": true,
    "restart_window": {
        "start_hour": 2,
        "days_of_week": ["SATURDAY", "SUNDAY"],
        "time_zone_id": "America/Los_Angeles"
    }
}
```

### Serverless 搭配 Python 依賴

使用 `create_or_update_pipeline` 工具搭配 `extra_settings`:
```json
{
    "serverless": true,
    "environment": {
        "dependencies": [
            "scikit-learn==1.3.0",
            "pandas>=2.0.0",
            "requests"
        ]
    }
}
```

### 依 ID 更新現有管線

若您有來自 Databricks UI 的管線 ID，可在 `extra_settings` 中包含 `id` 強制更新：
```json
{
    "id": "554f4497-4807-4182-bff0-ffac4bb4f0ce"
}
```

### 從 Databricks UI 匯出完整 JSON

您可以從 Databricks UI (Pipeline Settings > JSON)複製管線設定，並直接作為 `extra_settings` 傳遞。無效欄位如 `pipeline_type` 會自動過濾：

```json
{
    "id": "554f4497-4807-4182-bff0-ffac4bb4f0ce",
    "pipeline_type": "WORKSPACE",
    "continuous": false,
    "development": true,
    "photon": false,
    "edition": "ADVANCED",
    "channel": "CURRENT",
    "clusters": [{
        "label": "default",
        "num_workers": 1,
        "instance_pool_id": "0727-104344-pool-xyz"
    }],
    "configuration": {
        "catalog": "main",
        "schema": "my_schema"
    }
}
```

**注意**: 明確的工具參數 (`name`, `root_path`, `catalog`, `schema`, `workspace_file_paths`) 優先順序恆大於 `extra_settings` 中的值。
