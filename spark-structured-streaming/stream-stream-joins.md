---
name: stream-stream-joins
description: 使用事件時間語義、浮水印 (Watermarks) 與狀態管理，即時關聯兩個串流來源。適用於關聯來自不同串流的事件 (訂單與付款、點擊與轉換、感測器讀數)、處理遲到資料，或實作跨多串流的視窗聚合。
---

# 雙串流關聯 (Stream-Stream Joins)

即時關聯兩個串流來源，以連結在不同時間與速度到達的事件。雙串流關聯需要浮水印來管理狀態並處理遲到資料。

## 快速入門 (Quick Start)

```python
from pyspark.sql.functions import expr, from_json, col
from pyspark.sql.types import StructType

# 讀取兩個串流來源
orders = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "orders")
    .load()
    .select(from_json(col("value").cast("string"), order_schema).alias("data"))
    .select("data.*")
    .withWatermark("order_time", "10 minutes")
)

payments = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "payments")
    .load()
    .select(from_json(col("value").cast("string"), payment_schema).alias("data"))
    .select("data.*")
    .withWatermark("payment_time", "10 minutes")
)

# 具備時間邊界的關聯
matched = (orders
    .join(
        payments,
        expr("""
            orders.order_id = payments.order_id AND
            payments.payment_time >= orders.order_time - interval 5 minutes AND
            payments.payment_time <= orders.order_time + interval 10 minutes
        """),
        "inner"
    )
)

# 寫入結果
query = (matched
    .writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/orders_payments")
    .trigger(processingTime="30 seconds")
    .start("/delta/order_payments")
)
```

## 核心概念 (Core Concepts)

### 為何雙串流關聯需要浮水印

雙串流關聯是有狀態的：雙方都必須緩衝事件直到找到匹配或狀態過期。浮水印定義了何時可以安全清理狀態。

```python
# Watermark = latest_event_time - delay_threshold
.withWatermark("event_time", "10 minutes")

# 時間戳記 < 浮水印的事件被視為「過遲」
# 遲到事件的狀態會被自動清理
```

### 關聯類型與行為

| 關聯類型 | 匹配方式 | 遲到事件 | 使用案例 |
|-----------|---------|-------------|----------|
| **Inner** | 雙方 | 若另一方尚未過期仍可能匹配 | 關聯性分析 |
| **Left Outer** | 所有左側 + 匹配的右側 | 浮水印過後從左側丟棄 | 具備可選資料的豐富化 |
| **Right Outer** | 所有右側 + 匹配的左側 | 浮水印過後從右側丟棄 | 很少使用 |
| **Full Outer** | 來自雙方的所有事件 | 浮水印過後丟棄 | 完整全貌 |

## 常見模式 (Common Patterns)

### 模式 1: 訂單-付款匹配

在時間視窗內匹配訂單與付款：

```python
orders = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "orders")
    .load()
    .select(from_json(col("value").cast("string"), order_schema).alias("data"))
    .select("data.*")
    .withWatermark("order_time", "10 minutes")
)

payments = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "payments")
    .load()
    .select(from_json(col("value").cast("string"), payment_schema).alias("data"))
    .select("data.*")
    .withWatermark("payment_time", "10 minutes")
)

# 匹配訂單前後 10 分鐘內的付款
matched = (orders
    .join(
        payments,
        expr("""
            orders.order_id = payments.order_id AND
            payments.payment_time >= orders.order_time - interval 5 minutes AND
            payments.payment_time <= orders.order_time + interval 10 minutes
        """),
        "leftOuter"  # 包含無付款的訂單
    )
    .withColumn("matched", col("payment_id").isNotNull())
)

matched.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/orders_payments") \
    .start("/delta/order_payments")
```

### 模式 2: 點擊-轉換歸因 (Click-Conversion Attribution)

將轉換歸因於時間視窗內的點擊：

```python
impressions = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "impressions")
    .load()
    .select(from_json(col("value").cast("string"), impression_schema).alias("data"))
    .select("data.*")
    .withWatermark("impression_time", "1 hour")
)

conversions = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "conversions")
    .load()
    .select(from_json(col("value").cast("string"), conversion_schema).alias("data"))
    .select("data.*")
    .withWatermark("conversion_time", "1 hour")
)

# 將轉換歸因於 24 小時內的最後一次曝光
attributed = (impressions
    .join(
        conversions,
        expr("""
            impressions.user_id = conversions.user_id AND
            impressions.ad_id = conversions.ad_id AND
            conversions.conversion_time >= impressions.impression_time AND
            conversions.conversion_time <= impressions.impression_time + interval 24 hours
        """),
        "inner"
    )
    .withColumn("attribution_window_hours", 
                (col("conversion_time").cast("long") - col("impression_time").cast("long")) / 3600)
)

attributed.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/attribution") \
    .start("/delta/attributed_conversions")
```

### 模式 3: 跨串流工作階段化 (Sessionization)

將來自多個串流的事件分組為工作階段：

```python
from pyspark.sql.functions import session_window

pageviews = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "pageviews")
    .load()
    .select(from_json(col("value").cast("string"), pageview_schema).alias("data"))
    .select("data.*")
    .withWatermark("event_time", "30 minutes")
)

clicks = (spark
    .readStream
    .format("kafka")
    .option("subscribe", "clicks")
    .load()
    .select(from_json(col("value").cast("string"), click_schema).alias("data"))
    .select("data.*")
    .withWatermark("event_time", "30 minutes")
)

# 為每個串流建立工作階段視窗
pageview_sessions = (pageviews
    .groupBy(
        col("user_id"),
        session_window(col("event_time"), "10 minutes")
    )
    .agg(
        count("*").alias("pageview_count"),
        min("event_time").alias("session_start"),
        max("event_time").alias("session_end")
    )
)

click_sessions = (clicks
    .groupBy(
        col("user_id"),
        session_window(col("event_time"), "10 minutes")
    )
    .agg(
        count("*").alias("click_count"),
        min("event_time").alias("session_start"),
        max("event_time").alias("session_end")
    )
)

# 關聯工作階段
joined_sessions = (pageview_sessions
    .join(
        click_sessions,
        ["user_id", "session_window"],
        "outer"
    )
    .withColumn("total_events", 
                coalesce(col("pageview_count"), lit(0)) + 
                coalesce(col("click_count"), lit(0)))
)

joined_sessions.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/sessions") \
    .start("/delta/user_sessions")
```

### 模式 4: 搭配死信佇列處理遲到資料

將遲到事件路由至獨立資料表：

```python
def write_with_late_data_handling(batch_df, batch_id):
    """分離準時與遲到資料"""
    from pyspark.sql.functions import current_timestamp, unix_timestamp
    
    # 計算延遲
    processed = batch_df.withColumn(
        "processing_delay_seconds",
        unix_timestamp(current_timestamp()) - unix_timestamp(col("event_time"))
    )
    
    # 準時資料 (浮水印內)
    on_time = processed.filter(col("processing_delay_seconds") < 600)  # 10 分鐘
    
    # 遲到資料
    late = processed.filter(col("processing_delay_seconds") >= 600)
    
    # 寫入準時資料
    (on_time
        .drop("processing_delay_seconds")
        .write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "stream_join_job")
        .saveAsTable("matched_events")
    )
    
    # 寫入遲到資料至 DLQ
    if late.count() > 0:
        (late
            .withColumn("dlq_reason", lit("LATE_ARRIVAL"))
            .withColumn("dlq_timestamp", current_timestamp())
            .write
            .format("delta")
            .mode("append")
            .saveAsTable("late_data_dlq")
        )

matched.writeStream \
    .foreachBatch(write_with_late_data_handling) \
    .option("checkpointLocation", "/checkpoints/orders_payments") \
    .start()
```

## 狀態管理 (State Management)

### 為大型狀態設定 RocksDB

對於超過記憶體容量的狀態儲存，使用 RocksDB：

```python
# 啟用 RocksDB 狀態儲存提供者
spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateProvider"
)

# 狀態儲存在磁碟上，減少記憶體壓力
# 推薦用於: 高基數鍵值、長浮水印期間
```

### 監控狀態大小

```python
# 直接讀取狀態儲存
state_df = (spark
    .read
    .format("statestore")
    .load("/checkpoints/orders_payments/state")
)

# 檢查分區平衡
state_df.groupBy("partitionId").count().orderBy(desc("count")).show()

# 檢查狀態大小
state_metadata = (spark
    .read
    .format("state-metadata")
    .load("/checkpoints/orders_payments")
)
state_metadata.show()

# 程式化監控
for stream in spark.streams.active:
    progress = stream.lastProgress
    if progress and "stateOperators" in progress:
        for op in progress["stateOperators"]:
            print(f"State rows: {op.get('numRowsTotal', 0)}")
            print(f"State memory: {op.get('memoryUsedBytes', 0)}")
```

### 控制狀態增長

```python
# 1. 使用浮水印 (自動清理)
.withWatermark("event_time", "10 minutes")  # 狀態在浮水印後過期

# 2. 降低鍵值基數
# 差: user_id (數百萬個相異值)
# 好: session_id (自然過期)

# 3. 設定合理的時間邊界
# 差: 無界限時間範圍
expr("s2.ts >= s1.ts")  # 狀態永遠增長!

# 好: 有界限時間範圍
expr("s2.ts BETWEEN s1.ts AND s1.ts + interval 1 hour")
```

## 浮水印設定 (Watermark Configuration)

### 選擇浮水印期間

在延遲與完整性之間取得平衡：

```python
# 經驗法則: 預期延遲的 2-3 倍
# 若 99th 百分位延遲為 5 分鐘 → 使用 10-15 分鐘浮水印

# 高容忍度 (更多匹配, 較大狀態)
.withWatermark("event_time", "2 hours")

# 低容忍度 (較快結果, 較小狀態)
.withWatermark("event_time", "10 minutes")
```

### 多重浮水印

當關聯不同延遲的串流時：

```python
# 串流 1: 快速, 低延遲
stream1 = stream1.withWatermark("ts", "5 minutes")

# 串流 2: 慢速, 高延遲
stream2 = stream2.withWatermark("ts", "15 minutes")

# 有效浮水印 = max(5, 15) = 15 分鐘
joined = stream1.join(stream2, join_condition, "inner")
```

## 生產最佳實踐 (Production Best Practices)

### 冪等寫入 (Idempotent Writes)

確保 Exactly-once 語義：

```python
def idempotent_write(batch_df, batch_id):
    """具備交易版本的冪等寫入"""
    (batch_df
        .write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "stream_join_job")
        .saveAsTable("matched_events")
    )

matched.writeStream \
    .foreachBatch(idempotent_write) \
    .option("checkpointLocation", "/checkpoints/orders_payments") \
    .start()
```

### 多串流關聯 (3+ 串流)

謹慎串連 Joins - 每個都會增加狀態開銷：

```python
# 步驟 1: Join 串流 A 與 B
ab = (stream_a
    .withWatermark("ts", "10 minutes")
    .join(
        stream_b.withWatermark("ts", "10 minutes"),
        expr("a.key = b.key AND b.ts BETWEEN a.ts - interval 5 min AND a.ts + interval 5 min"),
        "inner"
    )
)

# 步驟 2: 將結果與串流 C 進行 Join
abc = ab.join(
    stream_c.withWatermark("ts", "10 minutes"),
    expr("ab.key = c.key AND c.ts BETWEEN ab.ts - interval 5 min AND ab.ts + interval 5 min"),
    "inner"
)

# 註: 結果浮水印來自左側 (ab)
```

### 效能調校

```python
# 狀態儲存批次保留
spark.conf.set("spark.sql.streaming.stateStore.minBatchesToRetain", "2")

# 狀態維護間隔
spark.conf.set("spark.sql.streaming.stateStore.maintenanceInterval", "5m")

# Shuffle 分區 (配合 Worker 核心數)
spark.conf.set("spark.sql.shuffle.partitions", "200")
```

## 監控 (Monitoring)

### 關鍵指標 (Key Metrics)

```python
# 程式化監控
for stream in spark.streams.active:
    status = stream.status
    progress = stream.lastProgress
    
    if progress:
        print(f"Stream: {stream.name}")
        print(f"Input rate: {progress.get('inputRowsPerSecond', 0)} rows/sec")
        print(f"Processing rate: {progress.get('processedRowsPerSecond', 0)} rows/sec")
        
        # 狀態指標
        if "stateOperators" in progress:
            for op in progress["stateOperators"]:
                print(f"State rows: {op.get('numRowsTotal', 0)}")
                print(f"State memory: {op.get('memoryUsedBytes', 0)}")
        
        # 浮水印
        if "eventTime" in progress:
            print(f"Watermark: {progress['eventTime'].get('watermark', 'N/A')}")
```

### Spark UI 檢查

- **Streaming Tab**: Input rate vs processing rate (Processing 必須超過 Input)
- **State Operators**: 狀態大小與記憶體使用量
- **Watermark**: 目前浮水印時間戳記
- **Batch Duration**: 應 < trigger interval

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **狀態過大** | 高基數鍵值或長浮水印 | 減少鍵值空間; 縮短浮水印期間 |
| **遲到事件被丟棄** | 浮水印太激進 | 增加浮水印延遲 |
| **無匹配** | 時間條件錯誤 | 檢查時間邊界與單位 (分 vs 時) |
| **OOM 錯誤** | 狀態爆炸 | 使用 RocksDB; 增加記憶體; 減少浮水印 |
| **缺少浮水印** | 狀態永遠增長 | 始終在雙方定義浮水印 |
| **無界限狀態** | 開放式時間範圍 | 在 Join 條件中使用有界限的時間範圍 |

## 生產檢核清單 (Production Checklist)

- [ ] 雙方串流來源均設定浮水印
- [ ] Join 條件包含明確的時間邊界
- [ ] 設定狀態儲存提供者 (大型狀態使用 RocksDB)
- [ ] 監控狀態大小並設定警報
- [ ] 定義遲到資料處理策略 (DLQ 或容忍)
- [ ] Output mode 為 "append" (串流 Join 必要)
- [ ] 每個查詢使用唯一檢查點位置
- [ ] 設定冪等寫入 (txnVersion/txnAppId)
- [ ] 跨串流標準化時區
- [ ] 追蹤效能指標 (Input rate, State size, Watermark lag)

## 專家提示 (Expert Tips)

### 事件時間 vs 處理時間

雙串流關聯始終使用事件時間：

```python
# ✅ 正確: 事件時間 (確定性)
.withWatermark("event_time", "10 minutes")

# ❌ 錯誤: 處理時間 (非確定性)
# 處理時間隨系統負載變化
# 結果無法重現
```

### 浮水印語義深入探討

理解浮水印行為：

```python
# Watermark = max_event_time - delay_threshold
# 範例: max_event_time = 10:15, delay = 10 min
# Watermark = 10:05

# 時間戳記 < 10:05 的事件為「過遲」
# - Inner join: 若另一方尚未過期仍可能匹配
# - Outer join: 浮水印通過後從 Outer 側丟棄

# 有效浮水印 = max(left_watermark, right_watermark)
```

### 狀態儲存後端選擇

選擇正確的狀態儲存後端：

```python
# 預設: 記憶體內 (快但有限)
# 用於: 小狀態 (< 10GB), 低基數鍵值

# RocksDB: 磁碟支援 (較慢但可擴展)
spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateProvider"
)
# 用於: 大狀態 (> 10GB), 高基數鍵值

# 監控狀態大小以決定何時切換
```

### Join 條件最佳實踐

始終包含明確的時間邊界：

```python
# ❌ 差: 無界限 (狀態永遠增長)
expr("s1.key = s2.key AND s2.ts >= s1.ts")

# ✅ 好: 有界限 (狀態受浮水印限制)
expr("""
    s1.key = s2.key AND
    s2.ts >= s1.ts - interval 5 minutes AND
    s2.ts <= s1.ts + interval 10 minutes
""")

# 原因? 有界限範圍允許狀態清理
# 無界限範圍導致狀態無限增長
```

## 相關技能 (Related Skills)

- `stream-static-joins` - 使用 Delta 維度表豐富串流
- `kafka-to-delta` - Kafka 攝取模式
- `watermark-configuration` - 浮水印語義深入探討
- `state-store-management` - 狀態儲存優化與監控
