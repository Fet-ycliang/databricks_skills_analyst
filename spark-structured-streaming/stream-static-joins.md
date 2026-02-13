---
name: stream-static-joins
description: 以即時方式使用 Delta 維度資料表豐富串流資料。適用於將快速變動的串流事件與緩慢變更的參考資料 (裝置維度、使用者設定檔、產品目錄) 進行關聯、實作即時資料豐富化，或在無狀態管理開銷的情況下為串流事件添加上下文。
---

# 串流靜態關聯 (Stream-Static Joins)

使用儲存在 Delta 資料表中的緩慢變更參考資料來豐富串流資料。串流靜態關聯是無狀態的，並且會在每個微批次中自動重新整理維度資料。

## 快速入門 (Quick Start)

```python
from pyspark.sql.functions import col, from_json

# 串流來源 (來自 Kafka 的 IoT 事件)
iot_stream = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "iot-events")
    .load()
    .select(from_json(col("value").cast("string"), event_schema).alias("data"))
    .select("data.*")
)

# 靜態 Delta 維度資料表 (每個微批次重新整理)
device_dim = spark.table("device_dimensions")

# 使用 Left Join 豐富串流資料 (推薦)
enriched = iot_stream.join(
    device_dim,
    "device_id",
    "left"  # 保留所有串流事件
).select(
    iot_stream["*"],
    device_dim["device_type"],
    device_dim["location"],
    device_dim["manufacturer"],
    device_dim["updated_at"].alias("dim_updated_at")
)

# 寫入豐富化後的資料
query = (enriched
    .writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/enriched_events")
    .trigger(processingTime="30 seconds")
    .start("/delta/enriched_iot_events")
)
```

## 核心概念 (Core Concepts)

### 為何 Delta 資料表很重要

Delta 資料表能在每個微批次自動檢查版本：

```python
# Delta table: 每個微批次檢查版本
device_dim = spark.table("device_dimensions")  # 自動讀取最新版本

# Non-Delta format: 啟動時讀取一次 (真正的靜態)
device_dim = spark.read.parquet("/path/to/devices")  # 不會重新整理
```

**關鍵見解**: Delta 的版本控制確保每個微批次都能取得最新的維度資料，無需手動重新整理。

### 關聯類型與生產用途

| 關聯類型 | 行為 | 生產用途 |
|-----------|----------|----------------|
| **Left** | 保留所有串流事件 | ✅ 推薦 - 防止資料遺失 |
| **Inner** | 丟棄未匹配事件 | ⚠️ 資料遺失風險 - 生產環境應避免 |
| **Right** | 保留所有維度資料列 | 很少使用 |
| **Full** | 保留雙方資料 | 很少使用 |

**生產規則**: 始終使用 Left Join 以防止丟棄有效的串流事件。

## 常見模式 (Common Patterns)

### 模式 1: 基本裝置豐富化

使用裝置中繼資料豐富 IoT 事件：

```python
# 串流 IoT 事件
iot_stream = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "iot-events")
    .load()
    .select(from_json(col("value").cast("string"), event_schema).alias("data"))
    .select("data.*")
)

# 裝置維度資料表
device_dim = spark.table("device_dimensions")

# Left join 以保留所有事件
enriched = iot_stream.join(
    device_dim,
    "device_id",
    "left"
).select(
    iot_stream["*"],
    device_dim["device_type"],
    device_dim["location"],
    device_dim["status"]
)

enriched.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/enriched") \
    .start("/delta/enriched_events")
```

### 模式 2: 多資料表豐富化

串連多個維度關聯：

```python
# 多個維度資料表
devices = spark.table("device_dimensions")
locations = spark.table("location_dimensions")
categories = spark.table("category_dimensions")

# 串連 joins (每個都是無狀態的)
enriched = (iot_stream
    .join(devices, "device_id", "left")
    .join(locations, "location_id", "left")
    .join(categories, "category_id", "left")
    .select(
        iot_stream["*"],
        devices["device_type"],
        devices["manufacturer"],
        locations["region"],
        locations["country"],
        categories["category_name"]
    )
)

# 每個 join 在每個微批次都會獨立重新整理
```

### 模式 3: 廣播雜湊關聯 (Broadcast Hash Join) 優化

透過確保 Broadcast 來優化關聯：

```python
from pyspark.sql.functions import broadcast

# 選項 1: 僅選取所需欄位
small_dim = device_dim.select("device_id", "device_type", "location")

# 選項 2: 過濾至有效記錄
active_dim = device_dim.filter(col("status") == "active")

# 選項 3: 強制 Broadcast Hint
enriched = iot_stream.join(
    broadcast(active_dim),
    "device_id",
    "left"
)

# 在 Spark UI 驗證: 在查詢計畫中尋找 "BroadcastHashJoin"
```

### 模式 4: 稽核維度新鮮度

追蹤維度資料的新鮮程度：

```python
from pyspark.sql.functions import unix_timestamp, current_timestamp

enriched = (iot_stream
    .join(device_dim, "device_id", "left")
    .withColumn(
        "dim_lag_seconds",
        unix_timestamp(current_timestamp()) - 
        unix_timestamp(col("dim_updated_at"))
    )
    .withColumn(
        "dim_fresh",
        col("dim_lag_seconds") < 3600  # 小於 1 小時
    )
)

# 監控: 若 dim_lag_seconds > 閾值則發出警報
# 用於資料品質檢查
```

### 模式 5: 時間旅行維度查找 (Time-Travel Dimension Lookup)

以事件發生的時間點與維度進行關聯：

```python
from delta import DeltaTable

def enrich_with_time_travel(batch_df, batch_id):
    """使用事件發生當下的維度版本進行豐富化"""
    from pyspark.sql.functions import max as spark_max
    
    # 取得最新維度版本
    latest_version = DeltaTable.forName(spark, "device_dimensions") \
        .history() \
        .select(spark_max("version").alias("max_version")) \
        .first()[0]
    
    # 讀取特定版本的維度
    dim_at_version = (spark
        .read
        .format("delta")
        .option("versionAsOf", latest_version)
        .table("device_dimensions")
    )
    
    # 與批次進行 Join
    enriched = batch_df.join(dim_at_version, "device_id", "left")
    
    # 寫入
    (enriched
        .write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "enrichment_job")
        .saveAsTable("enriched_events")
    )

iot_stream.writeStream \
    .foreachBatch(enrich_with_time_travel) \
    .option("checkpointLocation", "/checkpoints/enriched") \
    .start()
```

### 模式 6: 回填缺失維度

每日排程作業修復 Left Join 產生的 Null 維度：

```python
# 每日批次作業回填缺失維度
spark.sql("""
    MERGE INTO enriched_events target
    USING device_dimensions source
    ON target.device_id = source.device_id
      AND target.device_type IS NULL
    WHEN MATCHED THEN 
        UPDATE SET 
            device_type = source.device_type,
            location = source.location,
            manufacturer = source.manufacturer,
            dim_updated_at = source.updated_at
""")

# 在維度表更新後執行
# 修復在維度可用前就到達的事件
```

### 模式 7: 維度變更偵測

對維度變更做出反應的串流：

```python
def update_reference_cache(batch_df, batch_id):
    """當維度變更時更新記憶體快取"""
    # 維度表已變更
    # 更新應用程式快取或通知下游系統
    pass

# 串流維度表的變更
dim_changes = (spark
    .readStream
    .format("delta")
    .table("device_dimensions")
    .writeStream
    .foreachBatch(update_reference_cache)
    .option("checkpointLocation", "/checkpoints/dim_changes")
    .start()
)
```

## 效能優化 (Performance Optimization)

### 檢核清單

- [ ] 維度表 < 100MB 適合 Broadcast (或提高閾值)
- [ ] Join 前僅選取所需欄位
- [ ] 僅過濾維度至有效記錄
- [ ] 驗證查詢計畫中的 "BroadcastHashJoin"
- [ ] 分區大小在記憶體中約 100-200MB
- [ ] 運算與儲存使用相同區域

### 設定 (Configuration)

```python
# 若維度較大，提高 Broadcast 閾值
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "1g")

# 控制分區大小
spark.conf.set("spark.sql.shuffle.partitions", "200")

# 優化維度表讀取
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
```

### 減少維度大小

```python
# Join 前: 僅選取所需欄位
small_dim = device_dim.select(
    "device_id",
    "device_type",
    "location",
    "status"
)

# 過濾至有效記錄
active_dim = small_dim.filter(col("status") == "active")

# 使用較小的維度進行 Join
enriched = iot_stream.join(active_dim, "device_id", "left")
```

## 監控 (Monitoring)

### 關鍵指標 (Key Metrics)

```python
# 空值率 (Left Join 品質)
spark.sql("""
    SELECT 
        date_trunc('hour', timestamp) as hour,
        count(*) as total_events,
        count(device_type) as matched_events,
        count(*) - count(device_type) as unmatched_events,
        (count(*) - count(device_type)) * 100.0 / count(*) as null_rate_pct
    FROM enriched_events
    GROUP BY 1
    ORDER BY 1 DESC
""")

# 維度新鮮度
spark.sql("""
    SELECT 
        date_trunc('hour', timestamp) as hour,
        avg(dim_lag_seconds) as avg_lag_seconds,
        max(dim_lag_seconds) as max_lag_seconds,
        count(*) as events_with_dim
    FROM enriched_events
    WHERE dim_updated_at IS NOT NULL
    GROUP BY 1
    ORDER BY 1 DESC
""")
```

### 程式化監控

```python
# 監控串流健康狀態
for stream in spark.streams.active:
    status = stream.status
    progress = stream.lastProgress
    
    if progress:
        print(f"Stream: {stream.name}")
        print(f"Input rate: {progress.get('inputRowsPerSecond', 0)} rows/sec")
        print(f"Processing rate: {progress.get('processedRowsPerSecond', 0)} rows/sec")
        print(f"Batch duration: {progress.get('durationMs', {}).get('triggerExecution', 0)} ms")
```

### Spark UI 檢查

- **Streaming Tab**: Input rate vs processing rate (Processing 必須超過 Input)
- **SQL Tab**: 尋找 "BroadcastHashJoin" (而非 "SortMergeJoin")
- **Jobs Tab**: 檢查 Shuffle 操作 (應極少)
- **Stages Tab**: 驗證分區大小 (目標 100-200MB)

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **資料遺失** | Inner Join 丟棄未匹配事件 | 切換至 Left Join |
| **Join 緩慢** | 使用 Shuffle Join 而非 Broadcast | 減少維度大小; 強制 Broadcast |
| **資料過舊** | 非 Delta 格式 | 將維度表轉換為 Delta |
| **記憶體問題** | 維度表過大 | Join 前過濾; 提高 Broadcast 閾值 |
| **Join 傾斜** | 維度中有熱點鍵值 | 關聯鍵加鹽 (Salt) 或對維度表分區 |
| **高空值率** | 維度更新延遲 | 監控維度新鮮度; 回填作業 |

## 生產最佳實踐 (Production Best Practices)

### 始終使用 Left Join

```python
# 錯誤: Inner Join 會遺失資料
enriched = iot_stream.join(device_dim, "device_id", "inner")

# 正確: Left Join 保留所有事件
enriched = iot_stream.join(device_dim, "device_id", "left")

# 原因? 新裝置可能在維度表更新前就傳送資料
# Left Join 保留事件; 稍後再回填維度
```

### 處理 Null 維度

```python
# 在轉換中處理 Null
enriched = (iot_stream
    .join(device_dim, "device_id", "left")
    .withColumn(
        "device_type",
        coalesce(col("device_type"), lit("UNKNOWN"))
    )
    .withColumn(
        "location",
        coalesce(col("location"), lit("UNKNOWN"))
    )
)

# 或標記以供人工審閱
enriched = enriched.withColumn(
    "needs_review",
    col("device_type").isNull()
)
```

### 冪等寫入 (Idempotent Writes)

```python
def idempotent_write(batch_df, batch_id):
    """具備交易版本的冪等寫入"""
    (batch_df
        .write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "enrichment_job")
        .saveAsTable("enriched_events")
    )

enriched.writeStream \
    .foreachBatch(idempotent_write) \
    .option("checkpointLocation", "/checkpoints/enriched") \
    .start()
```

## 生產檢核清單 (Production Checklist)

- [ ] 使用 Left Join (非 Inner Join)
- [ ] 維度表為 Delta 格式
- [ ] 驗證查詢計畫中的 Broadcast Hash Join
- [ ] 維度大小優化 (< 100MB 或提高閾值)
- [ ] 監控空值率並設定警報
- [ ] 追蹤維度新鮮度
- [ ] 排程回填作業以處理缺失維度
- [ ] 每個查詢使用唯一檢查點位置
- [ ] 設定冪等寫入 (txnVersion/txnAppId)
- [ ] 追蹤效能指標 (Input rate, Batch duration)

## 專家提示 (Expert Tips)

### Delta 版本檢查

Delta 資料表透過檢查最新版本，自動在每個微批次重新整理：

```python
# 每個微批次:
# 1. Spark 檢查 Delta 資料表版本
# 2. 若有變更則讀取最新版本
# 3. 若無變更則使用快取版本
# 4. 無需手動重新整理

# 這就是為何 Delta 資料表比 Parquet 更適合做維度表
# Parquet: 啟動時讀取一次 (真正的靜態)
# Delta: 每個微批次檢查版本 (半靜態)
```

### 驗證 Broadcast Join

始終在生產環境驗證 Broadcast Joins：

```python
# 檢查查詢計畫
enriched.explain(extended=True)

# 尋找:
# - BroadcastHashJoin ✅ (快, 無 shuffle)
# - SortMergeJoin ⚠️ (慢, 需要 shuffle)

# 若看到 SortMergeJoin:
# 1. 減少維度大小 (選取欄位, 過濾資料列)
# 2. 提高 Broadcast 閾值
# 3. 強制 Broadcast Hint
```

### 維度資料表優化

優化維度資料表以利串流關聯：

```python
# 1. 對 Join Key 使用 Z-order 或 Liquid Clustering
spark.sql("""
    OPTIMIZE device_dimensions
    ZORDER BY (device_id)
""")

# 2. 保持維度表小巧 (理想 < 100MB)
# 3. 使用 Delta 以獲得自動版本檢查
# 4. 依常過濾的欄位進行分區
```

## 相關技能 (Related Skills)

- `stream-stream-joins` - 關聯兩個具備狀態管理的串流來源
- `kafka-to-delta` - Kafka 攝取模式
- `write-multiple-tables` - 多重目標的扇出模式
- `checkpoint-best-practices` - 檢查點設定與管理
