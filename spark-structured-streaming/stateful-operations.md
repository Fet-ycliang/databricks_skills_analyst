---
name: stateful-operations
description: 設定 Spark Structured Streaming 有狀態操作的浮水印 (Watermarks) 並管理狀態儲存 (State Stores)。適用於設定有狀態操作、調校浮水印期間、處理遲到資料、為大型狀態設定 RocksDB、監控狀態儲存大小或優化狀態效能。
---

# 有狀態操作：浮水印與狀態儲存 (Stateful Operations: Watermarks and State Stores)

設定浮水印以處理遲到資料並管理有狀態串流操作的狀態儲存。浮水印控制狀態的清理，而狀態儲存則負責有狀態資料的儲存與檢索。

## 快速入門 (Quick Start)

```python
# 為大型狀態儲存啟用 RocksDB
spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateProvider"
)

# 具備浮水印的有狀態操作
df = (spark.readStream
    .format("kafka")
    .option("subscribe", "events")
    .load()
    .select(from_json(col("value").cast("string"), schema).alias("data"))
    .select("data.*")
    .withWatermark("event_time", "10 minutes")  # 遲到資料閾值 + 狀態清理
    .dropDuplicates(["event_id"])  # 有狀態操作
)

# Watermark = 最新事件時間 - 10 分鐘
# 狀態在浮水印期間後自動過期
```

## 浮水印設定 (Watermark Configuration)

### 浮水印如何運作

```python
# Watermark = latest_event_time - delay_threshold
.withWatermark("event_time", "10 minutes")

# 時間戳記 < 浮水印的事件被視為「過遲 (Too Late)」
# 遲到事件的狀態會被自動清理
# 遲到事件可能會被丟棄 (Outer Joins) 或處理 (Inner Joins)
```

### 選擇浮水印期間

| 浮水印設定 | 效果 | 使用案例 |
|-------------------|--------|----------|
| `"10 minutes"` | 中等延遲 | 一般串流 |
| `"1 hour"` | 高完整性 | 金融交易 |
| `"5 minutes"` | 低延遲 | 即時分析 |
| `"24 hours"` | 類批次 | 回填情境 (Backfill) |

**經驗法則**: 從 p95 延遲的 2-3 倍開始。監控遲到資料比率並調整。

### 浮水印與狀態大小

```python
# 浮水印直接影響狀態儲存大小
# 狀態保留時間 = 浮水印期間 + 處理時間

# 計算範例:
# - 10 分鐘浮水印
# - 100 萬事件/分
# - 狀態大小 = ~1000 萬個鍵值 × 鍵值大小

# 縮短浮水印以減少狀態大小
.withWatermark("event_time", "5 minutes")  # 較小的狀態

# 狀態在浮水印期間後自動過期
# 無需手動清理
```

## 狀態儲存設定 (State Store Configuration)

### 啟用 RocksDB

當狀態儲存超過記憶體容量時使用 RocksDB：

```python
# 啟用 RocksDB 狀態儲存提供者
spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateProvider"
)

# 優點:
# - 狀態儲存在磁碟上，減少記憶體壓力
# - 推薦用於: 高基數鍵值 (High Cardinality Keys)、長浮水印期間
# - 對於大型狀態儲存有較佳效能
```

### 狀態儲存設定

```python
# 狀態儲存批次保留
spark.conf.set("spark.sql.streaming.stateStore.minBatchesToRetain", "2")

# 狀態維護間隔
spark.conf.set("spark.sql.streaming.stateStore.maintenanceInterval", "5m")

# 狀態儲存位置 (預設: checkpoint/state)
# 由 Spark 自動管理
```

## 常見模式 (Common Patterns)

### 模式 1: 具備浮水印的基本有狀態操作

```python
# 用於去重 (Deduplication) 的浮水印
df = (spark.readStream
    .format("kafka")
    .option("subscribe", "events")
    .load()
    .select(from_json(col("value").cast("string"), schema).alias("data"))
    .select("data.*")
    .withWatermark("event_time", "10 minutes")
    .dropDuplicates(["event_id"])
)

# 狀態在浮水印期間後過期
# 防止狀態無限增長
```

### 模式 2: 針對 Join 的浮水印調校

為不同延遲的串流設定不同的浮水印：

```python
# 快速來源: 5 分鐘浮水印
impressions = (spark.readStream
    .format("kafka")
    .option("subscribe", "impressions")
    .load()
    .select(from_json(col("value").cast("string"), impression_schema).alias("data"))
    .select("data.*")
    .withWatermark("impression_time", "5 minutes")
)

# 較慢來源: 15 分鐘浮水印
clicks = (spark.readStream
    .format("kafka")
    .option("subscribe", "clicks")
    .load()
    .select(from_json(col("value").cast("string"), click_schema).alias("data"))
    .select("data.*")
    .withWatermark("click_time", "15 minutes")
)

# 有效浮水印 = max(5, 15) = 15 分鐘
joined = impressions.join(
    clicks,
    expr("""
        impressions.ad_id = clicks.ad_id AND
        clicks.click_time BETWEEN impressions.impression_time AND
                                impressions.impression_time + interval 1 hour
    """),
    "inner"
)
```

### 模式 3: 具備浮水印的視窗聚合 (Windowed Aggregations)

```python
from pyspark.sql.functions import window, count, sum, max, current_timestamp

windowed = (df
    .withWatermark("event_time", "10 minutes")
    .groupBy(
        window(col("event_time"), "5 minutes"),
        col("user_id")
    )
    .agg(
        count("*").alias("event_count"),
        sum("value").alias("total_value"),
        max("event_time").alias("latest_event")
    )
    .withColumn("processing_time", current_timestamp())
)

# 使用 Update 模式以在遲到資料到達時更正結果
windowed.writeStream \
    .outputMode("update") \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/windowed") \
    .start("/delta/windowed_metrics")
```

### 模式 4: 監控狀態分區平衡

檢查狀態儲存傾斜 (Skew)：

```python
def check_state_balance(checkpoint_path):
    """檢查狀態儲存分區平衡"""
    state_df = spark.read.format("statestore").load(f"{checkpoint_path}/state")
    
    partition_counts = state_df.groupBy("partitionId").count().orderBy(desc("count"))
    partition_counts.show()
    
    # 計算傾斜
    counts = [row['count'] for row in partition_counts.collect()]
    if counts:
        max_count = max(counts)
        min_count = min(counts)
        skew_ratio = max_count / min_count if min_count > 0 else float('inf')
        
        print(f"State skew ratio: {skew_ratio:.2f}")
        if skew_ratio > 10:
            print("WARNING: High state skew detected")
            return False
    return True
```

### 模式 5: 監控狀態增長

```python
def monitor_state_growth(checkpoint_path):
    """追蹤狀態儲存增長"""
    state_df = spark.read.format("statestore").load(f"{checkpoint_path}/state")
    
    # 目前狀態大小
    total_rows = state_df.count()
    
    print(f"State rows: {total_rows}")
    
    # 檢查過期
    from pyspark.sql.functions import current_timestamp, col
    expired = state_df.filter(col("expirationMs") < current_timestamp().cast("long") * 1000)
    expired_count = expired.count()
    
    print(f"Expired state rows: {expired_count}")
    print(f"Active state rows: {total_rows - expired_count}")
```

## 狀態大小控制 (State Size Control)

### 使用浮水印 (Use Watermarks)

浮水印自動清理過期狀態：

```python
# 狀態在浮水印期間後過期
.withWatermark("event_time", "10 minutes")

# 狀態大小 = f(浮水印期間, 鍵值基數)
# 10 分浮水印 × 100 萬事件/分 = 可管理
# 72 小時浮水印 × 100 萬事件/分 = 非常大
```

### 降低鍵值基數 (Reduce Key Cardinality)

```python
# 差: 高基數鍵值
.dropDuplicates(["user_id"])  # 數百萬個相異值

# 好: 較低基數或會過期的鍵值
.dropDuplicates(["session_id"])  # Session 自然過期
.dropDuplicates(["event_id", "date"])  # 依日期分區可降低基數
```

## 監控 (Monitoring)

### 程式化狀態監控

```python
# 程式化監控狀態大小
for stream in spark.streams.active:
    progress = stream.lastProgress
    
    if progress and "stateOperators" in progress:
        for op in progress["stateOperators"]:
            print(f"Operator: {op.get('operatorName', 'unknown')}")
            print(f"State rows: {op.get('numRowsTotal', 0)}")
            print(f"State memory: {op.get('memoryUsedBytes', 0)}")
            print(f"State on disk: {op.get('diskBytesUsed', 0)}")
```

### 追蹤遲到資料比率

```python
# 監控遲到資料影響
late_data_stats = spark.sql("""
    SELECT 
        date_trunc('hour', event_time) as hour,
        COUNT(*) as total_events,
        SUM(CASE 
            WHEN unix_timestamp(processing_time) - unix_timestamp(event_time) > 600 
            THEN 1 ELSE 0 
        END) as late_events,
        AVG(unix_timestamp(processing_time) - unix_timestamp(event_time)) as avg_delay_seconds,
        MAX(unix_timestamp(processing_time) - unix_timestamp(event_time)) as max_delay_seconds
    FROM events
    WHERE processing_time >= current_timestamp() - interval 24 hours
    GROUP BY 1
    ORDER BY 1 DESC
""")
```

## 遲到資料分類

| 延遲 | 類別 | 處理方式 |
|-------|----------|----------|
| < 浮水印 | 準時 | 正常處理 |
| 浮水印 < 延遲 < 2×浮水印 | 遲到 | Inner Join 仍可能處理 |
| > 2×浮水印 | 嚴重遲到 | DLQ 手動處理 |

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **狀態儲存爆炸** | 浮水印太長 | 縮短浮水印; 封存舊狀態 |
| **遲到資料被丟棄** | 浮水印太短 | 增加浮水印; 分析延遲模式 |
| **狀態過大** | 高基數鍵值或長浮水印 | 降低鍵值基數; 減少浮水印期間 |
| **狀態分區傾斜** | 鍵值分佈不均 | 確保鍵值均勻分佈; 考慮 Salting |
| **OOM 錯誤** | 狀態超過記憶體 | 啟用 RocksDB; 增加記憶體; 減少浮水印 |
| **狀態未過期** | 未設定浮水印 | 為有狀態操作加入浮水印 |

## 狀態儲存復原 (State Store Recovery)

```python
# 情境 1: 狀態儲存損毀
# 解法: 刪除 state 資料夾，重啟串流
# 狀態將依據浮水印重建

dbutils.fs.rm("/checkpoints/stream/state", recurse=True)

# 重啟串流 - 狀態自動重建
# 註: 可能會重新處理浮水印視窗內的部分資料

# 情境 2: 狀態儲存過大
# 解法: 縮短浮水印期間
.withWatermark("event_time", "5 minutes")  # 從 10 分鐘減少

# 情境 3: 狀態分區不平衡
# 解法: 確保鍵值均勻分佈
# 若需要可考慮 Salting 鍵值
```

## 生產最佳實踐 (Production Best Practices)

### 始終為有狀態操作使用浮水印

```python
# 必要: 有狀態操作需浮水印
df.withWatermark("event_time", "10 minutes").dropDuplicates(["id"])

# 必要: 聚合操作需浮水印
df.withWatermark("event_time", "10 minutes").groupBy(...).agg(...)

# 必要: Stream-Stream Join 需浮水印
stream1.withWatermark("ts", "10 min").join(stream2.withWatermark("ts", "10 min"))
```

### 浮水印選擇

```python
# 經驗法則: 2-3× p95 延遲
# 範例: p95 延遲 = 5 分鐘 → 浮水印 = 10-15 分鐘

# 從保守值開始，根據監控調整
.withWatermark("event_time", "10 minutes")  # 從這裡開始
# 監控遲到資料比率
# 如遲到事件過多，增加
# 如狀態過大，減少
```

### 為大型狀態使用 RocksDB

```python
# 若狀態 > 記憶體容量，啟用 RocksDB
# 典型閾值: > 1 億個鍵值 或 > 10GB 狀態

spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateProvider"
)
```

## 生產檢核清單 (Production Checklist)

- [ ] 為所有有狀態操作設定浮水印
- [ ] 浮水印期間符合延遲需求 (2-3× p95)
- [ ] 為大型狀態儲存啟用 RocksDB
- [ ] 監控狀態大小並設定警報
- [ ] 定期檢查狀態分區平衡
- [ ] 追蹤狀態隨時間的增長
- [ ] 設定遲到資料監控
- [ ] 記錄復原程序

## 相關技能 (Related Skills)

- `stream-stream-joins` - 關聯中的遲到資料
- `checkpoint-best-practices` - 檢查點與狀態復原
