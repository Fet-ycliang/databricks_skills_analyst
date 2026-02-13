---
name: kafka-streaming
description: 綜合 Kafka 串流模式，包含 Kafka-to-Delta 攝取、Kafka-to-Kafka 管線，以及適用於亞秒級延遲的即時模式 (Real-Time Mode)。適用於建構 Kafka 攝取管線、實作事件豐富化、格式轉換或低延遲串流工作負載。
---

# Kafka 串流模式 (Kafka Streaming Patterns)

Spark Structured Streaming 的 Kafka 串流綜合指南：從攝取至 Delta、Kafka-to-Kafka 管線，以及適用於亞秒級延遲的即時模式。

## 快速入門 (Quick Start)

### Kafka 到 Delta (Kafka to Delta)

```python
from pyspark.sql.functions import col, from_json

# 從 Kafka 讀取
df = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker1:9092,broker2:9092")
    .option("subscribe", "topic_name")
    .option("startingOffsets", "earliest")
    .option("minPartitions", "6")  # 配合 Kafka 分區數
    .load()
)

# 解析 JSON value
df_parsed = df.select(
    col("key").cast("string"),
    from_json(col("value").cast("string"), event_schema).alias("data"),
    col("topic"), col("partition"), col("offset"),
    col("timestamp").alias("kafka_timestamp")
).select("key", "data.*", "topic", "partition", "offset", "kafka_timestamp")

# 寫入至 Delta
df_parsed.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/kafka_stream") \
    .trigger(processingTime="30 seconds") \
    .start("/delta/bronze_events")
```

### Kafka 到 Kafka (Kafka to Kafka)

```python
from pyspark.sql.functions import col, from_json, to_json, struct, current_timestamp

# 從來源 Kafka 讀取
source_df = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker1:9092")
    .option("subscribe", "input-events")
    .option("startingOffsets", "latest")
    .load()
)

# 解析與轉換
parsed_df = source_df.select(
    col("key").cast("string"),
    from_json(col("value").cast("string"), event_schema).alias("data"),
    col("topic").alias("source_topic")
).select("key", "data.*", "source_topic")

# 轉換事件
enriched_df = parsed_df.withColumn(
    "processed_at", current_timestamp()
).withColumn(
    "value", to_json(struct("event_id", "user_id", "event_type", "processed_at"))
)

# 寫入至輸出 Kafka 主題
enriched_df.select("key", "value").writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "broker1:9092") \
    .option("topic", "output-events") \
    .option("checkpointLocation", "/checkpoints/kafka-to-kafka") \
    .trigger(processingTime="30 seconds") \
    .start()
```

## 常見模式 (Common Patterns)

### 模式 1: Bronze 層攝取 (Kafka 到 Delta)

最小化轉換，保留原始欄位：

```python
# 最佳實踐: 最小化轉換，保留原始欄位
# 原因: Kafka 保留成本高 (預設 7 天)
# Delta 提供具備完整歷史的永久儲存

df_bronze = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", servers)
    .option("subscribe", topic)
    .option("startingOffsets", "earliest")
    .option("maxOffsetsPerTrigger", 10000)  # 控制批次大小
    .load()
    .select(
        col("key").cast("string"),
        col("value").cast("string"),
        col("topic"), col("partition"), col("offset"),
        col("timestamp").alias("kafka_timestamp"),
        current_timestamp().alias("ingestion_timestamp")
    )
)

df_bronze.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/bronze_events") \
    .trigger(processingTime="30 seconds") \
    .start("/delta/bronze_events")
```

### 模式 2: 排程串流 (成本優化)

定期執行而非持續執行：

```python
# 每 4 小時執行一次，而非持續執行
# 程式碼相同，僅需在工作排程器中變更 trigger

df_bronze.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/bronze_events") \
    .trigger(availableNow=True) \  # 處理所有可用資料後停止
    .start("/delta/bronze_events")

# 在 Databricks Jobs 中:
# - 排程: 每 4 小時
# - 叢集: 固定大小 (串流不使用自動縮放)
# - 相同的串流程式碼，採批次式執行
```

### 模式 3: 即時模式 (亞秒級延遲)

當延遲需求 < 800ms 時使用 RTM：

```python
# 即時觸發 (Databricks 13.3+)
query = (enriched_df
    .select(col("key"), col("value"))
    .writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", brokers)
    .option("topic", "output-events")
    .trigger(realTime=True)  # 啟用 RTM
    .option("checkpointLocation", checkpoint_path)
    .start()
)

# RTM 叢集需求
spark.conf.set("spark.databricks.photon.enabled", "true")
spark.conf.set("spark.sql.streaming.stateStore.providerClass", 
               "com.databricks.sql.streaming.state.RocksDBStateProvider")

# 何時使用 RTM:
# - 延遲需求 < 800ms
# - 啟用 Photon
# - 固定大小叢集 (無自動縮放)
```

### 模式 4: 事件豐富化 (Kafka 到 Kafka 搭配 Delta)

使用維度資料豐富事件：

```python
# 讀取參考資料 (Delta table - 每個微批次自動重新整理)
user_dim = spark.table("users.dimension")

# 串流靜態關連 (Stream-static join) 進行豐富化
enriched = (parsed_df
    .join(user_dim, "user_id", "left")
    .withColumn("enriched_value", to_json(struct(
        col("event_id"),
        col("user_id"),
        col("user_name"),  # 來自維度表
        col("user_segment"),  # 來自維度表
        col("event_type"),
        col("timestamp")
    )))
)

# 寫入豐富化事件至 Kafka
enriched.select(col("key"), col("enriched_value").alias("value")).writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", brokers) \
    .option("topic", "enriched-events") \
    .trigger(realTime=True) \
    .option("checkpointLocation", "/checkpoints/enrichment") \
    .start()
```

### 模式 5: 多主題路由 (Multi-Topic Routing)

將事件路由至不同的 Kafka 主題：

```python
def route_events(batch_df, batch_id):
    """將事件路由至不同 Kafka 主題"""
    
    # 高優先級 → 緊急主題
    high_priority = batch_df.filter(col("priority") == "high")
    if high_priority.count() > 0:
        high_priority.select("key", "value").write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", brokers) \
            .option("topic", "urgent-events") \
            .save()
    
    # 錯誤 → DLQ 主題
    errors = batch_df.filter(col("event_type") == "error")
    if errors.count() > 0:
        errors.select("key", "value").write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", brokers) \
            .option("topic", "error-events-dlq") \
            .save()
    
    # 所有事件 → 標準主題
    batch_df.select("key", "value").write \
        .format("kafka") \
        .option("kafka.bootstrap.servers", brokers) \
        .option("topic", "standard-events") \
        .save()

parsed_df.writeStream \
    .foreachBatch(route_events) \
    .trigger(realTime=True) \
    .option("checkpointLocation", "/checkpoints/routing") \
    .start()
```

### 模式 6: 結構描述驗證與 DLQ

驗證結構描述並路由無效記錄：

```python
from pyspark.sql.functions import from_json, col, lit, to_json, struct, current_timestamp

def validate_and_route(batch_df, batch_id):
    """驗證結構描述，將不良記錄路由至 DLQ"""
    
    # 嘗試使用嚴格結構描述進行解析
    parsed = batch_df.withColumn(
        "parsed",
        from_json(col("value").cast("string"), validated_schema)
    )
    
    # 有效記錄
    valid = parsed.filter(col("parsed").isNotNull()).select("key", "value")
    
    # 無效記錄 → DLQ
    invalid = parsed.filter(col("parsed").isNull()).select(
        col("key"),
        to_json(struct(
            col("value"),
            lit("SCHEMA_VALIDATION_FAILED").alias("dlq_reason"),
            current_timestamp().alias("dlq_timestamp")
        )).alias("value")
    )
    
    # 寫入有效記錄至主主題
    if valid.count() > 0:
        valid.write.format("kafka") \
            .option("kafka.bootstrap.servers", brokers) \
            .option("topic", "valid-events") \
            .save()
    
    # 寫入無效記錄至 DLQ
    if invalid.count() > 0:
        invalid.write.format("kafka") \
            .option("kafka.bootstrap.servers", brokers) \
            .option("topic", "dlq-events") \
            .save()

source_df.writeStream \
    .foreachBatch(validate_and_route) \
    .trigger(realTime=True) \
    .option("checkpointLocation", "/checkpoints/validation") \
    .start()
```

## 設定 (Configuration)

### 消費者選項 (從 Kafka 讀取)

```python
(spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "host1:9092,host2:9092")
    .option("subscribe", "source-topic")
    .option("startingOffsets", "latest")  # latest, earliest, 或特定 JSON
    .option("maxOffsetsPerTrigger", "10000")  # 控制批次大小
    .option("minPartitions", "6")  # 配合 Kafka 分區數
    .option("kafka.auto.offset.reset", "latest")
    .option("kafka.enable.auto.commit", "false")  # Spark 管理 offsets
    .load()
)
```

### 生產者選項 (寫入至 Kafka)

```python
(df
    .select("key", "value")
    .writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "host1:9092,host2:9092")
    .option("topic", "target-topic")
    .option("kafka.acks", "all")  # 持久性: all, 1, 0
    .option("kafka.retries", "3")
    .option("kafka.batch.size", "16384")
    .option("kafka.linger.ms", "5")
    .option("kafka.compression.type", "lz4")  # lz4, snappy, gzip
    .option("checkpointLocation", checkpoint_path)
    .start()
)
```

### 安全性 (SASL/SSL)

```python
# 使用 Databricks secrets
kafka_username = dbutils.secrets.get("kafka-scope", "username")
kafka_password = dbutils.secrets.get("kafka-scope", "password")

# SASL/PLAIN 驗證
df.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", brokers) \
    .option("topic", target_topic) \
    .option("kafka.security.protocol", "SASL_SSL") \
    .option("kafka.sasl.mechanism", "PLAIN") \
    .option("kafka.sasl.jaas.config", 
            f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{kafka_username}" password="{kafka_password}";') \
    .option("checkpointLocation", checkpoint_path) \
    .start()
```

## 效能調校 (Performance Tuning)

| 參數 | 建議 | 原因 |
|-----------|---------------|-----|
| minPartitions | 配合 Kafka 分區數 | 最佳化平行度 |
| maxOffsetsPerTrigger | 10,000-100,000 | 平衡延遲與吞吐量 |
| trigger interval | 業務 SLA / 3 | 復原緩衝時間 |
| RTM | 僅在需求 < 800ms 時使用 | 微批次更具成本效益 |

## 監控 (Monitoring)

### 關鍵指標 (Key Metrics)

```python
# 程式化監控
for stream in spark.streams.active:
    progress = stream.lastProgress
    if progress:
        print(f"Input rate: {progress.get('inputRowsPerSecond', 0)} rows/sec")
        print(f"Processing rate: {progress.get('processedRowsPerSecond', 0)} rows/sec")
        
        # Kafka 特定指標
        sources = progress.get("sources", [])
        for source in sources:
            end_offset = source.get("endOffset", {})
            latest_offset = source.get("latestOffset", {})
            
            # 計算每個分區的 Lag
            for topic, partitions in end_offset.items():
                for partition, end in partitions.items():
                    latest = latest_offset.get(topic, {}).get(partition, end)
                    lag = int(latest) - int(end)
                    print(f"Topic {topic}, Partition {partition}: Lag = {lag}")
```

### Spark UI 檢查

- **Input Rate vs Processing Rate**: Processing 必須 > Input
- **Max Offsets Behind Latest**: 應保持一致或下降
- **Batch Duration**: 應 < trigger interval

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **未讀取到資料** | `startingOffsets` 預設為 "latest" | 針對現有資料使用 "earliest" |
| **高延遲** | 微批次額外開銷 | 使用 RTM (trigger(realTime=True)) |
| **Consumer lag** | Processing < Input rate | 擴展叢集; 降低 maxOffsetsPerTrigger |
| **重複訊息** | 未設定 Exactly-once | 啟用冪等生產者 (acks=all) |
| **進度落後** | Processing < Input rate | 增加叢集大小 |
| **無法使用自動縮放** | 串流需求 | 使用固定大小叢集 |

## 生產檢核清單 (Production Checklist)

- [ ] 檢查點位置為持久化儲存 (UC volumes, 非 DBFS)
- [ ] 每個管線使用唯一檢查點
- [ ] 固定大小叢集 (串流/RTM 不使用自動縮放)
- [ ] 僅在延遲需求 < 800ms 時啟用 RTM
- [ ] 監控 Consumer lag 並設定警報
- [ ] Producer 設定 acks=all 以確保持久性
- [ ] 設定結構描述驗證與 DLQ
- [ ] 為生產環境設定安全性 (SASL/SSL)
- [ ] 驗證 Exactly-once 語義

## 相關技能 (Related Skills)

- `stream-static-joins` - Delta 資料表的豐富化模式
- `stream-stream-joins` - 跨 Kafka 主題的事件關聯
- `checkpoint-best-practices` - 檢查點設定
- `trigger-tuning` - 觸發器設定與 RTM 設置
