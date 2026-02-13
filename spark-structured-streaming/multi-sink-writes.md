---
name: multi-sink-writes
description: 使用 ForEachBatch 將單一 Spark 串流寫入至多個 Delta 資料表或 Kafka 主題。適用於將串流資料扇出 (Fan-out) 至多個目標、實作獎章架構 (Bronze/Silver/Gold)、條件式路由、CDC 模式，或從單一串流建立物化視圖。
---

# 多重目標寫入 (Multi-Sink Writes)

使用 ForEachBatch 有效率地將單一串流來源寫入至多個 Delta 資料表或 Kafka 主題。讀取一次，寫入多次 (Read once, write many) - 避免重複處理來源資料。

## 快速入門 (Quick Start)

```python
from pyspark.sql.functions import col, current_timestamp

def write_multiple_tables(batch_df, batch_id):
    """將批次寫入至多個目標 (Sinks)"""
    # Bronze - 原始資料
    batch_df.write \
        .format("delta") \
        .mode("append") \
        .option("txnVersion", batch_id) \
        .option("txnAppId", "multi_sink_job") \
        .save("/delta/bronze_events")
    
    # Silver - 已清理
    cleansed = batch_df.dropDuplicates(["event_id"])
    cleansed.write \
        .format("delta") \
        .mode("append") \
        .option("txnVersion", batch_id) \
        .option("txnAppId", "multi_sink_job_silver") \
        .save("/delta/silver_events")
    
    # Gold - 已聚合
    aggregated = batch_df.groupBy("category").count()
    aggregated.write \
        .format("delta") \
        .mode("append") \
        .option("txnVersion", batch_id) \
        .option("txnAppId", "multi_sink_job_gold") \
        .save("/delta/category_counts")

stream.writeStream \
    .foreachBatch(write_multiple_tables) \
    .option("checkpointLocation", "/checkpoints/multi_sink") \
    .start()
```

## 核心概念 (Core Concepts)

### 單一來源，單一檢查點

整個多重目標串流使用單一檢查點：

```python
# 正確: 所有目標共用一個檢查點
stream.writeStream \
    .foreachBatch(multi_sink_function) \
    .option("checkpointLocation", "/checkpoints/single_source_multi_sink") \
    .start()

# 錯誤: 不要建立個別的串流
#這會導致每個串流獨立重複處理來源
```

### 交易保證 (Transactional Guarantees)

每次 ForEachBatch 呼叫代表一個 Epoch。批次內的所有寫入：
- 看到相同的輸入資料
- 共用相同的 batch_id
- 若使用 txnVersion 則具備冪等性 (Idempotent)

## 常見模式 (Common Patterns)

### 模式 1: Bronze-Silver-Gold 獎章架構

單一串流供應所有三個獎章層級：

```python
from pyspark.sql.functions import window, count, sum, current_timestamp

def medallion_architecture(batch_df, batch_id):
    """單一串流供應所有三個獎章層級"""
    
    # Bronze: 原始攝取
    (batch_df.write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "medallion_bronze")
        .saveAsTable("bronze.events")
    )
    
    # Silver: 清理與驗證
    silver_df = (batch_df
        .dropDuplicates(["event_id"])
        .filter(col("status").isin(["active", "pending"]))
        .withColumn("processed_at", current_timestamp())
    )
    
    (silver_df.write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "medallion_silver")
        .saveAsTable("silver.events")
    )
    
    # Gold: 業務聚合
    gold_df = (silver_df
        .groupBy(window(col("timestamp"), "5 minutes"), "category")
        .agg(
            count("*").alias("event_count"),
            sum("amount").alias("total_amount")
        )
    )
    
    (gold_df.write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "medallion_gold")
        .saveAsTable("gold.category_metrics")
    )

stream.writeStream \
    .foreachBatch(medallion_architecture) \
    .trigger(processingTime="30 seconds") \
    .option("checkpointLocation", "/checkpoints/medallion") \
    .start()
```

### 模式 2: 條件式路由 (Conditional Routing)

根據條件將事件路由至不同資料表：

```python
def route_by_type(batch_df, batch_id):
    """根據類型將事件路由至不同資料表"""
    
    # 依事件類型拆分
    orders = batch_df.filter(col("event_type") == "order")
    refunds = batch_df.filter(col("event_type") == "refund")
    reviews = batch_df.filter(col("event_type") == "review")
    
    # 寫入至個別資料表
    if orders.count() > 0:
        (orders.write
            .format("delta")
            .mode("append")
            .option("txnVersion", batch_id)
            .option("txnAppId", "router_orders")
            .saveAsTable("orders")
        )
    
    if refunds.count() > 0:
        (refunds.write
            .format("delta")
            .mode("append")
            .option("txnVersion", batch_id)
            .option("txnAppId", "router_refunds")
            .saveAsTable("refunds")
        )
    
    if reviews.count() > 0:
        (reviews.write
            .format("delta")
            .mode("append")
            .option("txnVersion", batch_id)
            .option("txnAppId", "router_reviews")
            .saveAsTable("reviews")
        )
```

### 模式 3: 平行扇出 (Parallel Fan-Out)

平行寫入至多個獨立資料表：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_write(batch_df, batch_id):
    """平行寫入至多個目標"""
    
    # Cache 以避免重複計算
    batch_df.cache()
    
    def write_table(table_name, filter_expr=None):
        """寫入過濾後的資料至資料表"""
        df = batch_df.filter(filter_expr) if filter_expr else batch_df
        (df.write
            .format("delta")
            .mode("append")
            .option("txnVersion", batch_id)
            .option("txnAppId", f"parallel_{table_name}")
            .saveAsTable(table_name)
        )
        return f"Wrote {table_name}"
    
    # 定義資料表與過濾器
    tables = [
        ("bronze.all_events", None),
        ("silver.errors", col("level") == "ERROR"),
        ("silver.warnings", col("level") == "WARN"),
        ("gold.metrics", col("type") == "metric")
    ]
    
    # 平行寫入
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(write_table, table_name, filter_expr): table_name 
            for table_name, filter_expr in tables
        }
        
        errors = []
        for future in as_completed(futures):
            table_name = futures[future]
            try:
                future.result()
            except Exception as e:
                errors.append((table_name, str(e)))
    
    batch_df.unpersist()
    
    if errors:
        raise Exception(f"Write failures: {errors}")
```

### 模式 4: 物化視圖 (Materialized Views)

從同一串流建立多個衍生視圖：

```python
from pyspark.sql.functions import window, count, sum

def create_materialized_views(batch_df, batch_id):
    """從同一串流建立多個衍生視圖"""
    
    # 基底: 所有事件
    (batch_df.write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "views_raw")
        .save("/delta/views/raw")
    )
    
    # 視圖 1: 每小時聚合
    hourly = (batch_df
        .withWatermark("event_time", "1 hour")
        .groupBy(window(col("event_time"), "1 hour"), col("category"))
        .agg(
            count("*").alias("event_count"),
            sum("value").alias("total_value")
        )
    )
    
    (hourly.write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "views_hourly")
        .save("/delta/views/hourly")
    )
    
    # 視圖 2: 使用者工作階段 (15 分鐘視窗)
    sessions = (batch_df
        .withWatermark("event_time", "15 minutes")
        .groupBy(window(col("event_time"), "15 minutes"), col("user_id"))
        .agg(count("*").alias("actions"))
    )
    
    (sessions.write
        .format("delta")
        .mode("append")
        .option("txnVersion", batch_id)
        .option("txnAppId", "views_sessions")
        .save("/delta/views/sessions")
    )
```

### 模式 5: 搭配死信佇列的錯誤處理

將無效記錄路由至 DLQ：

```python
from pyspark.sql.functions import when, lit

def write_with_dlq(batch_df, batch_id):
    """寫入有效記錄至目標，無效記錄至死信佇列"""
    
    # 驗證
    valid = batch_df.filter(
        col("required_field").isNotNull() & 
        col("timestamp").isNotNull()
    )
    invalid = batch_df.filter(
        col("required_field").isNull() | 
        col("timestamp").isNull()
    )
    
    # 寫入有效資料
    if valid.count() > 0:
        (valid.write
            .format("delta")
            .mode("append")
            .option("txnVersion", batch_id)
            .option("txnAppId", "multi_sink_valid")
            .saveAsTable("silver.valid_events")
        )
    
    # 寫入無效資料至 DLQ 並附帶中繼資料
    if invalid.count() > 0:
        dlq_df = (invalid
            .withColumn("_error_reason", 
                when(col("required_field").isNull(), "missing_required_field")
                .otherwise("missing_timestamp"))
            .withColumn("_batch_id", lit(batch_id))
            .withColumn("_processed_at", current_timestamp())
        )
        
        (dlq_df.write
            .format("delta")
            .mode("append")
            .saveAsTable("errors.dead_letter_queue")
        )
```

## 效能優化 (Performance Optimization)

### 最小化重複計算

快取批次 DataFrame 以避免重複計算：

```python
def optimized_multi_sink(batch_df, batch_id):
    """快取以避免重複計算"""
    
    # 快取批次
    batch_df.cache()
    
    # 從快取資料進行多次寫入
    batch_df.write...  # Sink 1
    batch_df.filter(...).write...  # Sink 2
    batch_df.filter(...).write...  # Sink 3
    
    # 完成後 Unpersist
    batch_df.unpersist()
```

### 平行寫入

使用 ThreadPoolExecutor 進行獨立寫入：

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_write(batch_df, batch_id):
    """平行寫入至獨立資料表"""
    
    batch_df.cache()
    
    def write_table(table_name, df):
        df.write.format("delta").mode("append").saveAsTable(table_name)
    
    # 平行寫入
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.submit(write_table, "table1", batch_df)
        executor.submit(write_table, "table2", batch_df.filter(...))
        executor.submit(write_table, "table3", batch_df.filter(...))
    
    batch_df.unpersist()
```

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **寫入緩慢** | 循序處理 | 使用 ThreadPoolExecutor 平行處理 |
| **重複計算** | 對同一 DataFrame 執行多次 Action | 快取批次 DataFrame |
| **部分失敗** | 單一目標失敗 | 使用冪等寫入; Spark 會重試整個批次 |
| **Schema 衝突** | 資料表有不同 Schema | 寫入前進行轉換 |
| **資源競爭** | 並發寫入過多 | 限制平行度; 分批寫入 |

## 生產最佳實踐 (Production Best Practices)

### 冪等寫入 (Idempotent Writes)

始終搭配 batch_id 使用 txnVersion：

```python
.write
    .format("delta")
    .option("txnVersion", batch_id)
    .option("txnAppId", "unique_app_id_per_table")
    .mode("append")
```

### 保持批次處理快速

```python
# GOOD: 簡單的過濾與寫入
def efficient_write(df, batch_id):
    df.filter(...).write.save("/delta/table1")
    df.filter(...).write.save("/delta/table2")

# BAD: 昂貴的聚合 (移至串流定義中!)
def inefficient_write(df, batch_id):
    df.groupBy(...).agg(...).write.save("/delta/table3")  # 移至串流!
```

## 生產檢核清單 (Production Checklist)

- [ ] 每個多重目標串流使用單一檢查點
- [ ] 設定冪等寫入 (txnVersion/txnAppId)
- [ ] 使用 Cache 避免重複計算
- [ ] 對獨立資料表使用平行寫入
- [ ] 設定錯誤處理與 DLQ
- [ ] 處理 Schema 演變
- [ ] 每個目標的效能監控

## 相關技能 (Related Skills)

- `merge-operations` - 平行 MERGE 操作
- `kafka-streaming` - Kafka 攝取模式
- `stream-static-joins` - 多重目標寫入前的豐富化
- `checkpoint-best-practices` - 檢查點設定
