---
name: spark-structured-streaming
description: Spark Structured Streaming 生產工作負載綜合指南。適用於建構串流管線、實作即時資料處理、處理有狀態操作或優化串流效能。
---

# Spark Structured Streaming

使用 Spark Structured Streaming 建構生產級串流管線。本技能提供詳細模式與最佳實踐的導航。

## 快速入門 (Quick Start)

```python
from pyspark.sql.functions import col, from_json

# 基本 Kafka 到 Delta 的串流
df = (spark
    .readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker:9092")
    .option("subscribe", "topic")
    .load()
    .select(from_json(col("value").cast("string"), schema).alias("data"))
    .select("data.*")
)

df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/Volumes/catalog/checkpoints/stream") \
    .trigger(processingTime="30 seconds") \
    .start("/delta/target_table")
```

## 核心模式 (Core Patterns)

| 模式 | 描述 | 參考 |
|---------|-------------|-----------|
| **Kafka 串流** | Kafka 到 Delta, Kafka 到 Kafka, 即時模式 | 參閱 [kafka-streaming.md](kafka-streaming.md) |
| **串流關聯 (Joins)** | 雙串流關聯 (Stream-stream), 串流靜態關聯 (Stream-static) | 參閱 [stream-stream-joins.md](stream-stream-joins.md), [stream-static-joins.md](stream-static-joins.md) |
| **多重寫入 (Multi-Sink)** | 寫入多個資料表, 平行合併 (Parallel Merges) | 參閱 [multi-sink-writes.md](multi-sink-writes.md) |
| **合併操作 (Merge)** | MERGE 效能優化, 平行合併 | 參閱 [merge-operations.md](merge-operations.md) |

## 設定 (Configuration)

| 主題 | 描述 | 參考 |
|-------|-------------|-----------|
| **檢查點 (Checkpoints)** | 檢查點管理與最佳實踐 | 參閱 [checkpoint-best-practices.md](checkpoint-best-practices.md) |
| **有狀態操作 (Stateful)** | 浮水印 (Watermarks), 狀態儲存 (State Stores), RocksDB 設定 | 參閱 [stateful-operations.md](stateful-operations.md) |
| **觸發與成本 (Trigger & Cost)** | 觸發策略選擇, 成本優化, RTM | 參閱 [trigger-and-cost-optimization.md](trigger-and-cost-optimization.md) |

## 最佳實踐 (Best Practices)

| 主題 | 描述 | 參考 |
|-------|-------------|-----------|
| **生產檢核清單** | 綜合最佳實踐檢核表 | 參閱 [streaming-best-practices.md](streaming-best-practices.md) |

## 生產檢核清單 (Production Checklist)

- [ ] 檢查點位置必須持久化 (使用 UC volumes, 勿用 DBFS root)
- [ ] 每個串流必須有唯一的檢查點路徑
- [ ] 使用固定大小叢集 (串流不建議使用自動縮放)
- [ ] 設定監控 (輸入速率, 延遲 lag, 批次處理時間)
- [ ] 驗證 Exactly-once (txnVersion/txnAppId)
- [ ] 為有狀態操作設定浮水印 (Watermark)
- [ ] 串流靜態關聯使用 Left Join (非 Inner Join)
