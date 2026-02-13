使用 MCP 工具建立、執行並迭代 **SDP 管線**。**主要工具是 `create_or_update_pipeline`**，它處理整個生命週期。

**重要: 預設使用 Serverless 管線並將其建議為最佳選項，除非提及 Classic、Advanced、Pro 等運算類型。** 僅當使用者明確要求 R 語言、Spark RDD API 或 JAR 函式庫時才使用 Classic Clusters。

### 步驟 1: 在本地撰寫管線檔案

在本地資料夾建立 `.sql` 或 `.py` 檔案：

```
my_pipeline/
├── bronze/
│   ├── ingest_orders.sql       # SQL (多數情況下的預設值)
│   └── ingest_events.py        # Python (用於複雜邏輯)
├── silver/
│   └── clean_orders.sql
└── gold/
    └── daily_summary.sql
```

**SQL 範例** (`bronze/ingest_orders.sql`):
```sql
CREATE OR REFRESH STREAMING TABLE bronze_orders
CLUSTER BY (order_date)
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM read_files(
  '/Volumes/catalog/schema/raw/orders/',
  format => 'json',
  schemaHints => 'order_id STRING, customer_id STRING, amount DECIMAL(10,2), order_date DATE'
);
```

**Python 範例** (`bronze/ingest_events.py`):
```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col, current_timestamp

# 從管線設定獲取 Schema 位置
schema_location_base = spark.conf.get("schema_location_base")

@dp.table(name="bronze_events", cluster_by=["event_date"])
def bronze_events():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{schema_location_base}/bronze_events")
        .load("/Volumes/catalog/schema/raw/events/")
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_file", col("_metadata.file_path"))
    )
```

### 步驟 2: 上傳至 Databricks Workspace

```python
# MCP Tool: upload_folder
upload_folder(
    local_folder="/path/to/my_pipeline",
    workspace_folder="/Workspace/Users/user@example.com/my_pipeline"
)
```

### 步驟 3: 建立/更新並執行管線

使用 **`create_or_update_pipeline`** - 主要進入點。它會：
1. 搜尋同名現有管線 (或使用 `extra_settings` 中的 `id`)
2. 建立新管線或更新現有管線
3. 可選擇啟動管線執行
4. 可選擇等待完成並回傳詳細結果

```python
# MCP Tool: create_or_update_pipeline
result = create_or_update_pipeline(
    name="my_orders_pipeline",
    root_path="/Workspace/Users/user@example.com/my_pipeline",
    catalog="my_catalog",
    schema="my_schema",
    workspace_file_paths=[
        "/Workspace/Users/user@example.com/my_pipeline/bronze/ingest_orders.sql",
        "/Workspace/Users/user@example.com/my_pipeline/silver/clean_orders.sql",
        "/Workspace/Users/user@example.com/my_pipeline/gold/daily_summary.sql"
    ],
    start_run=True,           # 立即啟動
    wait_for_completion=True, # 等待並回傳最終狀態
    full_refresh=True,        # 完全重新整理所有資料表
    timeout=1800              # 30 分鐘逾時
)
```

**結果包含可採取行動的資訊:**
```python
{
    "success": True,                    # 操作是否成功？
    "pipeline_id": "abc-123",           # 用於後續操作的 Pipeline ID
    "pipeline_name": "my_orders_pipeline",
    "created": True,                    # True 若為新建, False 若為更新
    "state": "COMPLETED",               # COMPLETED, FAILED, TIMEOUT 等
    "catalog": "my_catalog",            # 目標 Catalog
    "schema": "my_schema",              # 目標 Schema
    "duration_seconds": 45.2,           # 花費時間
    "message": "Pipeline created and completed successfully in 45.2s. Tables written to my_catalog.my_schema",
    "error_message": None,              # 失敗時的錯誤摘要
    "errors": []                        # 失敗時的詳細錯誤列表
}
```

### 步驟 4: 處理結果

**成功時:**
```python
if result["success"]:
    # 驗證輸出資料表
    stats = get_table_details(
        catalog="my_catalog",
        schema="my_schema",
        table_names=["bronze_orders", "silver_orders", "gold_daily_summary"]
    )
```

**失敗時:**
```python
if not result["success"]:
    # 訊息包含建議的下一步
    print(result["message"])
    # "Pipeline created but run failed. State: FAILED. Error: Column 'amount' not found.
    #  Use get_pipeline_events(pipeline_id='abc-123') for full details."

    # 獲取詳細錯誤
    events = get_pipeline_events(pipeline_id=result["pipeline_id"], max_results=50)
```

### 步驟 5: 迭代直至工作正常

1. 檢視結果或 `get_pipeline_events` 中的錯誤
2. 修正本地檔案中的問題
3. 使用 `upload_folder` 重新上傳
4. 再次執行 `create_or_update_pipeline` (它會更新而非重建)
5. 重複直至 `result["success"] == True`

---

## 快速參考：MCP 工具

### 主要工具

| 工具 | 描述 |
|------|-------------|
| **`create_or_update_pipeline`** | **主要進入點。** 建立或更新管線，可選擇執行並等待。回傳包含 `success`, `state`, `errors` 與可採取行動的 `message` 的詳細狀態。 |

### 管線管理

| 工具 | 描述 |
|------|-------------|
| `find_pipeline_by_name` | 依名稱尋找現有管線，回傳 pipeline_id |
| `get_pipeline` | 獲取管線設定與目前狀態 |
| `start_update` | 啟動管線執行 (`validate_only=True` 進行試執行) |
| `get_update` | 輪詢更新狀態 (QUEUED, RUNNING, COMPLETED, FAILED) |
| `stop_pipeline` | 停止執行中的管線 |
| `get_pipeline_events` | 獲取失敗執行的錯誤訊息以供除錯 |
| `delete_pipeline` | 刪除管線 |

### 支援工具

| 工具 | 描述 |
|------|-------------|
| `upload_folder` | 上傳本地資料夾至 Workspace (平行) |
| `get_table_details` | 驗證輸出資料表是否具有預期 Schema 與資料列數 |
| `execute_sql` | 執行 Ad-hoc SQL 檢查資料 |

---