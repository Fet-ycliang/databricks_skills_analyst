# 使用 Lakebase Autoscaling 的反向 ETL (Reverse ETL)

## 概述

反向 ETL 允許您將 Unity Catalog Delta tables 的資料作為 PostgreSQL 資料表同步到 Lakebase Autoscaling 中。這使得能夠對 Lakehouse 中處理的資料進行 OLTP 存取模式。

## 運作方式

同步資料表 (Synced tables) 在 Lakebase 中建立 Unity Catalog 資料的託管副本：

1. 一個新的 Unity Catalog 資料表 (唯讀，由同步管線管理)
2. 一個 Lakebase 中的 Postgres 資料表 (應用程式可查詢)

同步管線使用託管的 Lakeflow Spark Declarative Pipelines 來持續更新這兩個資料表。

### 效能

- **持續寫入：** 每 CU 約 1,200 列/秒
- **大量寫入：** 每 CU 約 15,000 列/秒
- **使用連線：** 每個同步資料表最多 16 個連線

## 同步模式

| 模式 | 描述 | 最適合 | 備註 |
|------|-------------|----------|-------|
| **Snapshot** | 一次性完整複製 | 初始設定、歷史分析 | 如果修改 >10% 資料，效率高 10 倍 |
| **Triggered** | 依需求排程更新 | 每小時/每日更新的儀表板 | 需要在來源資料表上啟用 CDF |
| **Continuous** | 即時串流 (秒級延遲) | 即時應用程式 | 成本最高，最小 15 秒間隔，需要 CDF |

**注意：** Triggered 和 Continuous 模式需要在來源資料表上啟用變更資料摘要 (Change Data Feed, CDF)：

```sql
ALTER TABLE your_catalog.your_schema.your_table
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
```

## 建立同步資料表

### 使用 Python SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import (
    SyncedDatabaseTable,
    SyncedTableSpec,
    NewPipelineSpec,
    SyncedTableSchedulingPolicy,
)

w = WorkspaceClient()

# 建立同步資料表
synced_table = w.database.create_synced_database_table(
    SyncedDatabaseTable(
        name="lakebase_catalog.schema.synced_table",
        spec=SyncedTableSpec(
            source_table_full_name="analytics.gold.user_profiles",
            primary_key_columns=["user_id"],
            scheduling_policy=SyncedTableSchedulingPolicy.TRIGGERED,
            new_pipeline_spec=NewPipelineSpec(
                storage_catalog="lakebase_catalog",
                storage_schema="staging"
            )
        ),
    )
)
print(f"Created synced table: {synced_table.name}")
```

### 使用 CLI

```bash
databricks database create-synced-database-table \
    --json '{
        "name": "lakebase_catalog.schema.synced_table",
        "spec": {
            "source_table_full_name": "analytics.gold.user_profiles",
            "primary_key_columns": ["user_id"],
            "scheduling_policy": "TRIGGERED",
            "new_pipeline_spec": {
                "storage_catalog": "lakebase_catalog",
                "storage_schema": "staging"
            }
        }
    }'
```

## 檢查同步資料表狀態

```python
status = w.database.get_synced_database_table(name="lakebase_catalog.schema.synced_table")
print(f"State: {status.data_synchronization_status.detailed_state}")
print(f"Message: {status.data_synchronization_status.message}")
```

## 刪除同步資料表

從 Unity Catalog 和 Postgres 同時刪除：

1. **Unity Catalog:** 從 Catalog Explorer 或 SDK 刪除
2. **Postgres:** 刪除資料表以釋放儲存空間

```sql
DROP TABLE your_database.your_schema.your_table;
```

## 資料類型對應

| Unity Catalog 類型 | Postgres 類型 |
|-------------------|---------------|
| BIGINT | BIGINT |
| BINARY | BYTEA |
| BOOLEAN | BOOLEAN |
| DATE | DATE |
| DECIMAL(p,s) | NUMERIC |
| DOUBLE | DOUBLE PRECISION |
| FLOAT | REAL |
| INT | INTEGER |
| INTERVAL | INTERVAL |
| SMALLINT | SMALLINT |
| STRING | TEXT |
| TIMESTAMP | TIMESTAMP WITH TIME ZONE |
| TIMESTAMP_NTZ | TIMESTAMP WITHOUT TIME ZONE |
| TINYINT | SMALLINT |
| ARRAY | JSONB |
| MAP | JSONB |
| STRUCT | JSONB |

**不支援的類型：** GEOGRAPHY, GEOMETRY, VARIANT, OBJECT

## 容量規劃

- **連線使用量：** 每個同步資料表使用最多 16 個連線
- **大小限制：** 所有同步資料表總共 2 TB；建議每個資料表 < 1 TB
- **命名：** 資料庫、結構描述和資料表名稱僅允許 `[A-Za-z0-9_]+`
- **架構演進：** 對於 Triggered/Continuous 模式僅支援添加式變更 (例如，新增欄位)

## 使用案例

### Web 應用程式的產品目錄

```python
w.database.create_synced_database_table(
    SyncedDatabaseTable(
        name="ecommerce_catalog.public.products",
        spec=SyncedTableSpec(
            source_table_full_name="gold.products.catalog",
            primary_key_columns=["product_id"],
            scheduling_policy=SyncedTableSchedulingPolicy.TRIGGERED,
        ),
    )
)
```

### 即時特徵服務 (Real-time Feature Serving)

```python
w.database.create_synced_database_table(
    SyncedDatabaseTable(
        name="ml_catalog.public.user_features",
        spec=SyncedTableSpec(
            source_table_full_name="ml.features.user_features",
            primary_key_columns=["user_id"],
            scheduling_policy=SyncedTableSchedulingPolicy.CONTINUOUS,
        ),
    )
)
```

## 最佳實踐

1. **啟用 CDF**: 在建立 Triggered 或 Continuous 同步資料表之前，在來源資料表上啟用 CDF
2. **選擇適當的同步模式**: 小資料表使用 Snapshot，每小時/每日使用 Triggered，即時使用 Continuous
3. **監控同步狀態**: 透過 Catalog Explorer 檢查失敗和延遲
4. **索引目標資料表**: 為您的查詢模式在 Postgres 中建立適當的索引
5. **處理架構變更**: 串流模式僅支援添加式變更
6. **考慮連線限制**: 每個同步資料表使用最多 16 個連線
