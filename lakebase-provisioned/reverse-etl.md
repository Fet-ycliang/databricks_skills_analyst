# 使用 Lakebase 的反向 ETL

## 概述

反向 ETL 允許您將資料從 Unity Catalog Delta 資料表同步到 Lakebase Provisioned 作為 PostgreSQL 資料表。這使得在 Lakehouse 中處理的資料能夠以 OLTP 存取模式使用。

## 建立同步資料表

### 使用 Python SDK

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 從 Unity Catalog 建立同步資料表
synced_table = w.database.create_synced_table(
    instance_name="my-lakebase-instance",
    source_table_name="catalog.schema.source_table",
    target_table_name="target_table",
    sync_mode="FULL",  # FULL 或 INCREMENTAL
)

print(f"同步資料表已建立：{synced_table.target_table_name}")
```

### 使用 SQL

```sql
-- 透過 SQL 建立同步資料表
CREATE SYNCED TABLE my_lakebase.target_table
FROM catalog.schema.source_table
USING LAKEBASE INSTANCE 'my-lakebase-instance';
```

### 使用 CLI

```bash
databricks database create-synced-table \
    --instance-name my-lakebase-instance \
    --source-table-name catalog.schema.source_table \
    --target-table-name target_table \
    --sync-mode FULL
```

## 同步模式

### 完全同步

每次同步時完全替換目標資料表：

```python
synced_table = w.database.create_synced_table(
    instance_name="my-lakebase-instance",
    source_table_name="catalog.schema.customers",
    target_table_name="customers",
    sync_mode="FULL"
)
```

**使用時機：**
- 來源資料表為小到中型大小
- 需要與來源完全一致
- 增量變更難以追蹤

### 增量同步

僅同步變更的列（需要變更追蹤）：

```python
synced_table = w.database.create_synced_table(
    instance_name="my-lakebase-instance",
    source_table_name="catalog.schema.events",
    target_table_name="events",
    sync_mode="INCREMENTAL",
    incremental_column="updated_at"  # 用於追蹤變更的欄位
)
```

**使用時機：**
- 來源資料表很大
- 有可靠的變更追蹤欄位
- 最小化同步時間和資源使用

## 管理同步資料表

### 列出同步資料表

```python
synced_tables = w.database.list_synced_tables(
    instance_name="my-lakebase-instance"
)
for table in synced_tables:
    print(f"{table.target_table_name}: {table.sync_status}")
```

### 觸發手動同步

```python
w.database.sync_table(
    instance_name="my-lakebase-instance",
    table_name="customers"
)
```

### 刪除同步資料表

```python
w.database.delete_synced_table(
    instance_name="my-lakebase-instance",
    table_name="customers"
)
```

## 排程同步

### 使用 Databricks Jobs

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, NotebookTask, CronSchedule

w = WorkspaceClient()

# 建立作業以按排程同步資料表
job = w.jobs.create(
    name="Lakebase 同步作業",
    tasks=[
        Task(
            task_key="sync_customers",
            notebook_task=NotebookTask(
                notebook_path="/Repos/sync/sync_customers"
            )
        )
    ],
    schedule=CronSchedule(
        quartz_cron_expression="0 0 * * * ?",  # 每小時
        timezone_id="UTC"
    )
)
```

### 同步 Notebook 範例

```python
# Databricks notebook: sync_customers

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 觸發特定資料表的同步
tables_to_sync = ["customers", "orders", "products"]

for table in tables_to_sync:
    try:
        w.database.sync_table(
            instance_name="my-lakebase-instance",
            table_name=table
        )
        print(f"已同步：{table}")
    except Exception as e:
        print(f"同步 {table} 失敗：{e}")
```

## 使用案例

### 1. 網頁應用程式的產品目錄

```python
# 為電子商務應用程式同步產品資料
w.database.create_synced_table(
    instance_name="ecommerce-db",
    source_table_name="gold.products.catalog",
    target_table_name="products",
    sync_mode="FULL"
)

# 應用程式直接查詢 PostgreSQL
# 具有低延遲的點查詢
```

### 2. 驗證服務的使用者設定檔

```python
# 為驗證服務同步使用者設定檔
w.database.create_synced_table(
    instance_name="auth-db",
    source_table_name="gold.users.profiles",
    target_table_name="user_profiles",
    sync_mode="INCREMENTAL",
    incremental_column="last_modified"
)
```

### 3. 即時 ML 的特徵存儲

```python
# 為線上服務同步特徵
w.database.create_synced_table(
    instance_name="feature-store-db",
    source_table_name="ml.features.user_features",
    target_table_name="user_features",
    sync_mode="INCREMENTAL",
    incremental_column="computed_at"
)

# ML 模型以低延遲查詢特徵
```

## 最佳實踐

1. **選擇適當的同步模式**：對小型資料表使用 FULL，對具有變更追蹤的大型資料表使用 INCREMENTAL
2. **在低流量期間排程**：大量同步可能會影響來源和目標
3. **監控同步狀態**：檢查失敗和延遲
4. **索引目標資料表**：在 PostgreSQL 中為查詢模式建立適當的索引
5. **處理結構描述變更**：當來源結構描述變更時，同步資料表需要更新

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **同步時間過長** | 切換到 INCREMENTAL 模式；在來源上新增索引 |
| **結構描述不匹配** | 在來源結構描述變更後刪除並重新建立同步資料表 |
| **同步因逾時而失敗** | 增加同步逾時；減少批次大小 |
| **目標資料表被鎖定** | 在同步操作期間避免對目標進行 DDL |
