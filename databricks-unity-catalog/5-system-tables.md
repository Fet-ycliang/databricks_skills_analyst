# 系統資料表

Unity Catalog 系統資料表的完整參考：血緣關係、稽核、帳單、運算、作業和中繼資料。

## 概述

系統資料表是 `system` 目錄中的唯讀資料表，提供有關您 Databricks 帳戶的營運資料。

| 結構描述 | 用途 |
|--------|---------|
| `system.access` | 稽核日誌、血緣關係追蹤 |
| `system.billing` | 使用量和成本資料 |
| `system.compute` | 叢集、倉儲、節點指標 |
| `system.lakeflow` | 作業和管線 |
| `system.query` | 查詢歷史記錄和效能 |
| `system.storage` | 儲存指標和預測性 IO |
| `system.information_schema` | UC 物件的中繼資料 |

---

## 啟用系統結構描述

查詢前必須先啟用系統結構描述。

**SQL：**
```sql
-- 檢查可用的系統結構描述
SELECT * FROM system.information_schema.schemata
WHERE catalog_name = 'system';
```

**Python SDK：**
```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 列出系統結構描述及其狀態
for schema in w.system_schemas.list(metastore_id="your-metastore-id"):
    print(f"{schema.schema}: {schema.state}")

# 啟用系統結構描述
w.system_schemas.enable(
    metastore_id="your-metastore-id",
    schema_name="access"
)
```

**CLI：**
```bash
# 列出系統結構描述
databricks system-schemas list --metastore-id your-metastore-id

# 啟用系統結構描述
databricks system-schemas enable --metastore-id your-metastore-id \
    --schema-name access
```

---

## Access 結構描述（稽核與血緣關係）

### system.access.audit

所有 Unity Catalog 操作的稽核日誌。

**結構描述：**
| 欄位 | 類型 | 說明 |
|--------|------|-------------|
| `event_date` | DATE | 分割區鍵 - 務必對此進行篩選 |
| `event_time` | TIMESTAMP | 事件發生時間 |
| `workspace_id` | BIGINT | 事件發生的工作區 |
| `user_identity` | STRUCT | 使用者電子郵件、IP、工作階段資訊 |
| `action_name` | STRING | 執行的操作 |
| `request_params` | MAP | 請求參數 |
| `response` | STRUCT | 回應狀態和錯誤 |
| `source_ip_address` | STRING | 用戶端 IP 位址 |

**常見查詢：**

```sql
-- 最近的資料表存取事件
SELECT
    event_time,
    user_identity.email AS user_email,
    action_name,
    request_params.full_name_arg AS table_name,
    response.status_code
FROM system.access.audit
WHERE event_date >= current_date() - 7
  AND action_name IN ('getTable', 'createTable', 'deleteTable')
ORDER BY event_time DESC
LIMIT 100;

-- 過去 30 天的權限變更
SELECT
    event_time,
    user_identity.email AS changed_by,
    action_name,
    request_params.securable_type AS object_type,
    request_params.securable_full_name AS object_name,
    request_params.changes AS permission_changes
FROM system.access.audit
WHERE event_date >= current_date() - 30
  AND action_name IN ('updatePermissions', 'grantPermission', 'revokePermission')
ORDER BY event_time DESC;

-- 失敗的存取嘗試（安全監控）
SELECT
    event_time,
    user_identity.email AS user_email,
    source_ip_address,
    action_name,
    request_params.full_name_arg AS resource,
    response.error_message
FROM system.access.audit
WHERE event_date >= current_date() - 7
  AND response.status_code != '200'
ORDER BY event_time DESC;

-- 按查詢數量統計最活躍的使用者
SELECT
    user_identity.email AS user_email,
    COUNT(*) AS query_count,
    COUNT(DISTINCT DATE(event_time)) AS active_days
FROM system.access.audit
WHERE event_date >= current_date() - 30
  AND action_name = 'commandSubmit'
GROUP BY user_identity.email
ORDER BY query_count DESC
LIMIT 20;

-- 目錄/結構描述建立事件
SELECT
    event_time,
    user_identity.email AS created_by,
    action_name,
    request_params.name AS object_name,
    request_params.catalog_name
FROM system.access.audit
WHERE event_date >= current_date() - 30
  AND action_name IN ('createCatalog', 'createSchema', 'deleteCatalog', 'deleteSchema')
ORDER BY event_time DESC;

-- 誰建立了特定資料表？
SELECT
    event_time,
    user_identity.email AS created_by,
    request_params
FROM system.access.audit
WHERE action_name = 'createTable'
  AND request_params.full_name_arg = 'analytics.gold.customer_360'
ORDER BY event_time DESC
LIMIT 1;

-- 使用者存取了哪些資料表？
SELECT DISTINCT
    request_params.full_name_arg AS table_name,
    MIN(event_time) AS first_access,
    MAX(event_time) AS last_access,
    COUNT(*) AS access_count
FROM system.access.audit
WHERE user_identity.email = 'analyst@company.com'
  AND action_name = 'getTable'
  AND event_date >= current_date() - 30
GROUP BY request_params.full_name_arg
ORDER BY access_count DESC;

-- 追蹤敏感資料表存取
SELECT
    event_time,
    user_identity.email AS user_email,
    source_ip_address,
    action_name
FROM system.access.audit
WHERE event_date >= current_date() - 7
  AND request_params.full_name_arg IN (
      'analytics.gold.customers',
      'analytics.gold.financial_data'
  )
ORDER BY event_time DESC;
```

### system.access.table_lineage

追蹤資料表之間的資料流。

**結構描述：**
| 欄位 | 類型 | 說明 |
|--------|------|-------------|
| `source_table_full_name` | STRING | 來源資料表（catalog.schema.table） |
| `source_type` | STRING | TABLE、VIEW、PATH |
| `target_table_full_name` | STRING | 目標資料表 |
| `target_type` | STRING | TABLE、VIEW |
| `created_by` | STRING | 建立血緣關係的使用者 |
| `event_time` | TIMESTAMP | 擷取血緣關係的時間 |

**常見查詢：**

```sql
-- 尋找上游資料表（什麼資料表提供給此資料表）
SELECT DISTINCT
    source_table_full_name,
    source_type,
    MAX(event_time) AS last_updated
FROM system.access.table_lineage
WHERE target_table_full_name = 'analytics.gold.customer_360'
GROUP BY source_table_full_name, source_type
ORDER BY last_updated DESC;

-- 尋找下游資料表（此資料表提供給什麼資料表）
SELECT DISTINCT
    target_table_full_name,
    target_type,
    MAX(event_time) AS last_updated
FROM system.access.table_lineage
WHERE source_table_full_name = 'analytics.bronze.raw_orders'
GROUP BY target_table_full_name, target_type
ORDER BY last_updated DESC;

-- 完整血緣關係鏈（遞迴）
WITH RECURSIVE lineage AS (
    SELECT
        source_table_full_name,
        target_table_full_name,
        1 AS depth
    FROM system.access.table_lineage
    WHERE target_table_full_name = 'analytics.gold.customer_360'

    UNION ALL

    SELECT
        t.source_table_full_name,
        t.target_table_full_name,
        l.depth + 1
    FROM system.access.table_lineage t
    JOIN lineage l ON t.target_table_full_name = l.source_table_full_name
    WHERE l.depth < 10
)
SELECT DISTINCT * FROM lineage ORDER BY depth;

-- 相依性最多的資料表
SELECT
    target_table_full_name,
    COUNT(DISTINCT source_table_full_name) AS upstream_count
FROM system.access.table_lineage
WHERE event_time >= current_date() - 90
GROUP BY target_table_full_name
ORDER BY upstream_count DESC
LIMIT 20;

-- 帶有實體類型的血緣關係
SELECT
    source_table_full_name,
    source_type,
    target_table_full_name,
    target_type,
    created_by,
    event_time
FROM system.access.table_lineage
WHERE target_table_full_name LIKE 'analytics.gold.%'
  AND event_time >= current_date() - 30;
```

### system.access.column_lineage

欄位層級血緣關係追蹤。

**常見查詢：**

```sql
-- 尋找欄位來源
SELECT
    source_table_full_name,
    source_column_name,
    target_table_full_name,
    target_column_name
FROM system.access.column_lineage
WHERE target_table_full_name = 'analytics.gold.customer_360'
  AND target_column_name = 'total_orders'
ORDER BY event_time DESC;

-- 影響分析：什麼使用了此欄位？
SELECT DISTINCT
    target_table_full_name,
    target_column_name
FROM system.access.column_lineage
WHERE source_table_full_name = 'analytics.bronze.raw_customers'
  AND source_column_name = 'email';

-- PII 欄位追蹤
SELECT
    source_table_full_name,
    source_column_name,
    target_table_full_name,
    target_column_name
FROM system.access.column_lineage
WHERE source_column_name IN ('email', 'ssn', 'phone', 'address')
ORDER BY event_time DESC;

-- 尋找欄位的所有轉換
SELECT
    source_table_full_name,
    source_column_name,
    target_table_full_name,
    target_column_name
FROM system.access.column_lineage
WHERE target_column_name = 'customer_ltv'
ORDER BY event_time DESC;
```

---

## Billing 結構描述

### system.billing.usage

用於成本分析的詳細使用記錄。

**結構描述：**
| 欄位 | 類型 | 說明 |
|--------|------|-------------|
| `usage_date` | DATE | 使用日期 |
| `workspace_id` | BIGINT | 工作區 ID |
| `sku_name` | STRING | 產品 SKU |
| `usage_quantity` | DECIMAL | 消耗量 |
| `usage_unit` | STRING | 測量單位（DBU） |
| `cloud` | STRING | 雲端提供者 |
| `usage_metadata` | MAP | 額外的中繼資料 |

**常見查詢：**

```sql
-- 按 SKU 統計每日 DBU 消耗
SELECT
    usage_date,
    sku_name,
    SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
WHERE usage_date >= current_date() - 30
GROUP BY usage_date, sku_name
ORDER BY usage_date DESC, total_dbus DESC;

-- 運算 vs SQL 倉儲使用量
SELECT
    CASE
        WHEN sku_name LIKE '%ALL_PURPOSE%' THEN '通用運算'
        WHEN sku_name LIKE '%JOBS%' THEN '作業運算'
        WHEN sku_name LIKE '%SQL%' THEN 'SQL 倉儲'
        WHEN sku_name LIKE '%SERVERLESS%' THEN '無伺服器'
        ELSE '其他'
    END AS compute_type,
    SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
WHERE usage_date >= current_date() - 30
GROUP BY 1
ORDER BY total_dbus DESC;

-- 每日趨勢與 7 天移動平均
SELECT
    usage_date,
    SUM(usage_quantity) AS daily_dbus,
    AVG(SUM(usage_quantity)) OVER (
        ORDER BY usage_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7d
FROM system.billing.usage
WHERE usage_date >= current_date() - 60
GROUP BY usage_date
ORDER BY usage_date;

-- 按叢集統計最高成本驅動因素
SELECT
    usage_metadata.cluster_id,
    usage_metadata.cluster_name,
    SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
WHERE usage_date >= current_date() - 30
  AND usage_metadata.cluster_id IS NOT NULL
GROUP BY usage_metadata.cluster_id, usage_metadata.cluster_name
ORDER BY total_dbus DESC
LIMIT 20;

-- 按工作區統計成本與定價
SELECT
    workspace_id,
    u.sku_name,
    SUM(usage_quantity) AS total_dbus,
    SUM(usage_quantity * p.pricing.default) AS estimated_cost
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
    ON u.sku_name = p.sku_name AND u.cloud = p.cloud
WHERE usage_date >= current_date() - 30
  AND p.price_end_time IS NULL
GROUP BY workspace_id, u.sku_name
ORDER BY estimated_cost DESC;
```

### system.billing.list_prices

SKU 的參考價格。

```sql
-- 取得目前定價
SELECT
    sku_name,
    cloud,
    currency_code,
    pricing.default AS price_per_dbu
FROM system.billing.list_prices
WHERE price_end_time IS NULL
ORDER BY sku_name;
```

---

## Compute 結構描述

### system.compute.clusters

叢集配置和中繼資料（歷史定義，非即時狀態）。

```sql
-- 按來源類型統計叢集
SELECT
    cluster_source,
    COUNT(*) AS cluster_count
FROM system.compute.clusters
WHERE delete_time IS NULL
GROUP BY cluster_source;

-- 按 Databricks Runtime 版本統計叢集
SELECT
    dbr_version,
    COUNT(*) AS cluster_count
FROM system.compute.clusters
WHERE delete_time IS NULL
GROUP BY dbr_version
ORDER BY cluster_count DESC;

-- 最近建立的叢集
SELECT
    cluster_id,
    cluster_name,
    owned_by,
    dbr_version,
    cluster_source,
    create_time
FROM system.compute.clusters
WHERE delete_time IS NULL
  AND create_time >= current_date() - 30
ORDER BY create_time DESC
LIMIT 20;

-- 按節點類型統計叢集
SELECT
    worker_node_type,
    COUNT(*) AS cluster_count
FROM system.compute.clusters
WHERE delete_time IS NULL
GROUP BY worker_node_type
ORDER BY cluster_count DESC;
```

### system.compute.warehouse_events

SQL 倉儲擴展和狀態事件。

```sql
-- 倉儲運行時間分析
SELECT
    warehouse_id,
    event_type,
    COUNT(*) AS event_count
FROM system.compute.warehouse_events
WHERE event_time >= current_date() - 7
GROUP BY warehouse_id, event_type
ORDER BY warehouse_id, event_count DESC;

-- 按小時統計倉儲擴展模式
SELECT
    DATE(event_time) AS event_date,
    HOUR(event_time) AS event_hour,
    COUNT(*) AS scale_events
FROM system.compute.warehouse_events
WHERE event_type IN ('SCALED_UP', 'SCALED_DOWN')
  AND event_time >= current_date() - 30
GROUP BY DATE(event_time), HOUR(event_time)
ORDER BY event_date, event_hour;
```

---

## Lakeflow 結構描述（作業與管線）

### system.lakeflow.jobs

作業定義和配置。

```sql
-- 按觸發類型統計作業
SELECT
    CASE
        WHEN trigger.schedule IS NOT NULL THEN '排程'
        WHEN trigger.file_arrival IS NOT NULL THEN '檔案到達'
        WHEN trigger.continuous IS NOT NULL THEN '持續'
        WHEN trigger.table_update IS NOT NULL THEN '資料表更新'
        ELSE '手動/API'
    END AS job_trigger_type,
    COUNT(*) AS job_count
FROM system.lakeflow.jobs
WHERE delete_time IS NULL
GROUP BY 1;

-- 沒有最近執行的作業（可能過時）
SELECT
    j.job_id,
    j.name,
    j.creator_user_name,
    MAX(r.period_start_time) AS last_run
FROM system.lakeflow.jobs j
LEFT JOIN system.lakeflow.job_run_timeline r
    ON j.job_id = r.job_id
WHERE j.delete_time IS NULL
GROUP BY j.job_id, j.name, j.creator_user_name
HAVING MAX(r.period_start_time) < current_date() - 30
    OR MAX(r.period_start_time) IS NULL;
```

### system.lakeflow.job_run_timeline

作業執行歷史記錄和效能。

```sql
-- 作業成功率
SELECT
    job_id,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN result_state = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_runs,
    ROUND(100.0 * SUM(CASE WHEN result_state = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate
FROM system.lakeflow.job_run_timeline
WHERE period_start_time >= current_date() - 30
GROUP BY job_id
HAVING COUNT(*) >= 5
ORDER BY success_rate ASC;

-- 按日統計平均作業持續時間
SELECT
    DATE(period_start_time) AS run_date,
    job_id,
    AVG(run_duration_seconds / 60) AS avg_duration_minutes
FROM system.lakeflow.job_run_timeline
WHERE period_start_time >= current_date() - 30
  AND run_duration_seconds IS NOT NULL
GROUP BY DATE(period_start_time), job_id
ORDER BY run_date DESC;

-- 過去 24 小時失敗的作業
SELECT
    job_id,
    run_id,
    period_start_time,
    result_state,
    termination_code
FROM system.lakeflow.job_run_timeline
WHERE period_start_time >= current_timestamp() - INTERVAL 24 HOURS
  AND result_state IN ('FAILED', 'TIMEDOUT', 'CANCELED')
ORDER BY period_start_time DESC;

-- 作業執行持續時間百分位數
SELECT
    job_id,
    PERCENTILE(run_duration_seconds / 60, 0.5) AS p50_minutes,
    PERCENTILE(run_duration_seconds / 60, 0.9) AS p90_minutes,
    PERCENTILE(run_duration_seconds / 60, 0.99) AS p99_minutes
FROM system.lakeflow.job_run_timeline
WHERE period_start_time >= current_date() - 30
  AND run_duration_seconds IS NOT NULL
GROUP BY job_id;
```

### system.lakeflow.pipeline_events

DLT/SDP 管線執行事件。

```sql
-- 管線成功率
SELECT
    pipeline_id,
    COUNT(*) AS total_updates,
    SUM(CASE WHEN event_type = 'update_success' THEN 1 ELSE 0 END) AS successful,
    ROUND(100.0 * SUM(CASE WHEN event_type = 'update_success' THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_rate
FROM system.lakeflow.pipeline_events
WHERE timestamp >= current_date() - 30
  AND event_type IN ('update_success', 'update_failed')
GROUP BY pipeline_id;

-- 最近的管線失敗
SELECT
    pipeline_id,
    pipeline_name,
    timestamp,
    event_type,
    details
FROM system.lakeflow.pipeline_events
WHERE timestamp >= current_date() - 7
  AND event_type = 'update_failed'
ORDER BY timestamp DESC;
```

---

## Query 結構描述

### system.query.history

查詢執行歷史記錄和效能。

```sql
-- 過去 7 天最慢的查詢
SELECT
    statement_id,
    executed_by,
    compute.warehouse_id AS warehouse_id,
    total_duration_ms / 1000 AS duration_seconds,
    produced_rows,
    LEFT(statement_text, 100) AS query_preview
FROM system.query.history
WHERE start_time >= current_date() - 7
  AND execution_status = 'FINISHED'
ORDER BY total_duration_ms DESC
LIMIT 20;

-- 按小時統計查詢量
SELECT
    DATE(start_time) AS query_date,
    HOUR(start_time) AS query_hour,
    COUNT(*) AS query_count,
    AVG(total_duration_ms / 1000) AS avg_duration_seconds
FROM system.query.history
WHERE start_time >= current_date() - 7
GROUP BY DATE(start_time), HOUR(start_time)
ORDER BY query_date DESC, query_hour;

-- 最活躍的查詢使用者
SELECT
    executed_by,
    COUNT(*) AS query_count,
    SUM(total_duration_ms) / 1000 / 60 AS total_minutes,
    AVG(total_duration_ms) / 1000 AS avg_seconds
FROM system.query.history
WHERE start_time >= current_date() - 30
GROUP BY executed_by
ORDER BY query_count DESC
LIMIT 20;

-- 失敗查詢分析
SELECT
    executed_by,
    error_message,
    COUNT(*) AS failure_count
FROM system.query.history
WHERE start_time >= current_date() - 7
  AND execution_status = 'FAILED'
GROUP BY executed_by, error_message
ORDER BY failure_count DESC
LIMIT 20;

-- 按陳述式類型統計查詢
SELECT
    statement_type,
    COUNT(*) AS query_count,
    AVG(total_duration_ms / 1000) AS avg_duration_seconds,
    SUM(produced_rows) AS total_rows
FROM system.query.history
WHERE start_time >= current_date() - 7
GROUP BY statement_type
ORDER BY query_count DESC;
```

---

## Information Schema

Unity Catalog 物件的中繼資料。

```sql
-- 列出所有目錄
SELECT catalog_name, catalog_owner, comment, created, created_by
FROM system.information_schema.catalogs
ORDER BY catalog_name;

-- 列出目錄中的所有結構描述
SELECT schema_name, schema_owner, comment, created
FROM system.information_schema.schemata
WHERE catalog_name = 'analytics'
ORDER BY schema_name;

-- 列出所有資料表
SELECT
    table_catalog,
    table_schema,
    table_name,
    table_type,
    comment
FROM system.information_schema.tables
WHERE table_catalog = 'analytics'
  AND table_schema = 'gold'
ORDER BY table_name;

-- 資料表的欄位詳細資訊
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default,
    comment
FROM system.information_schema.columns
WHERE table_catalog = 'analytics'
  AND table_schema = 'gold'
  AND table_name = 'customers'
ORDER BY ordinal_position;

-- 按欄位名稱尋找資料表（資料探索）
SELECT DISTINCT
    table_catalog,
    table_schema,
    table_name
FROM system.information_schema.columns
WHERE column_name LIKE '%email%'
   OR column_name LIKE '%customer_id%';

-- 沒有註解的資料表（治理缺口）
SELECT
    table_catalog,
    table_schema,
    table_name
FROM system.information_schema.tables
WHERE comment IS NULL
  AND table_catalog NOT IN ('system', 'hive_metastore')
ORDER BY table_catalog, table_schema, table_name;

-- 權限稽核：誰有權存取什麼
SELECT
    grantee,
    table_catalog,
    table_schema,
    table_name,
    privilege_type
FROM system.information_schema.table_privileges
WHERE table_catalog = 'analytics'
ORDER BY table_schema, table_name, grantee;

-- 結構描述權限
SELECT
    grantee,
    catalog_name,
    schema_name,
    privilege_type
FROM system.information_schema.schema_privileges
WHERE catalog_name = 'analytics'
ORDER BY schema_name, grantee;

-- 尋找所有磁碟區
SELECT
    volume_catalog,
    volume_schema,
    volume_name,
    volume_type,
    storage_location,
    comment
FROM system.information_schema.volumes
WHERE volume_catalog = 'analytics';

-- 尋找所有函數
SELECT
    routine_catalog,
    routine_schema,
    routine_name,
    routine_type,
    data_type AS return_type
FROM system.information_schema.routines
WHERE routine_catalog = 'analytics';

-- 共用詳細資訊
SELECT * FROM system.information_schema.shares;

-- 共用物件
SELECT
    share_name,
    name AS object_name,
    data_object_type,
    shared_as
FROM system.information_schema.shared_data_objects
WHERE share_name = 'customer_insights';

-- 接收者授權
SELECT
    share_name,
    recipient_name,
    privilege
FROM system.information_schema.share_recipients;
```

---

## 外部血緣關係

追蹤到外部系統的血緣關係。

**Python SDK：**
```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import (
    CreateRequestExternalLineage,
    ExternalLineageObject,
    LineageDirection
)

w = WorkspaceClient()

# 建立外部血緣關係
w.external_lineage.create_external_lineage_relationship(
    external_lineage_relationship=CreateRequestExternalLineage(
        target=ExternalLineageObject(
            table_full_name="analytics.bronze.raw_orders"
        ),
        source=ExternalLineageObject(
            external_system="salesforce",
            external_object="Account"
        )
    )
)

# 列出外部血緣關係
lineage = w.external_lineage.list_external_lineage_relationships(
    object_info=ExternalLineageObject(
        table_full_name="analytics.bronze.raw_orders"
    ),
    lineage_direction=LineageDirection.UPSTREAM
)
for rel in lineage:
    print(f"來源：{rel.source}")
```

**CLI：**
```bash
# 建立外部血緣關係
databricks external-lineage create-external-lineage-relationship --json '{
    "source": {
        "external_system": "salesforce",
        "external_object": "Account"
    },
    "target": {
        "table_full_name": "analytics.bronze.raw_orders"
    }
}'

# 列出外部血緣關係
databricks external-lineage list-external-lineage-relationships --json '{
    "object_info": {
        "table_full_name": "analytics.bronze.raw_orders"
    },
    "lineage_direction": "UPSTREAM"
}'
```

---

## 最佳實踐

### 查詢效能

1. **務必按日期分割區篩選** - 系統資料表按日期分割
```sql
WHERE event_date >= current_date() - 30  -- 良好
WHERE event_time >= '2024-01-01'         -- 較慢（掃描所有分割區）
```

2. **探索時使用 LIMIT** - 系統資料表可能非常大
```sql
LIMIT 100  -- 探索性查詢務必加上
```

3. **為常見查詢建立檢視** - 避免重複複雜邏輯
```sql
CREATE VIEW analytics.governance.daily_audit_summary AS
SELECT ...
```

4. **排程聚合作業** - 為儀表板預先聚合
```sql
CREATE TABLE analytics.monitoring.daily_usage_summary AS
SELECT usage_date, sku_name, SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
GROUP BY usage_date, sku_name;
```

### 保留期限

| 系統資料表 | 保留期限 |
|--------------|-----------|
| 稽核日誌 | 365 天 |
| 帳單使用量 | 365 天 |
| 查詢歷史記錄 | 30 天 |
| 血緣關係 | 365 天 |
| 運算事件 | 30 天 |

### 存取控制

```sql
-- 授予監控團隊存取權限
GRANT SELECT ON SCHEMA system.access TO `monitoring_team`;
GRANT SELECT ON SCHEMA system.billing TO `finance_team`;
GRANT SELECT ON SCHEMA system.query TO `platform_team`;
```

### 治理提示

1. 在 UC 設定中**儘早啟用系統資料表**
2. 使用**欄位血緣關係**追蹤敏感資料
3. **註冊外部來源**以獲得完整可見性
4. **保留稽核日誌**以符合合規性（通常 1-7 年）
5. **監控失敗的存取**以防範安全威脅
6. **自動化警報**以監控敏感操作
