---
name: "streaming-best-practices"
description: "Spark Streaming 經生產驗證的最佳實踐：觸發間隔、分區、檢查點管理，以及可靠管線的叢集設定。"
tags: ["spark-streaming", "best-practices", "production", "performance", "expert"]
---

# 串流最佳實踐專家套件 (Streaming Best Practices Expert Pack)

## 概述

從生產經驗中提煉出的綜合檢核清單。這些實踐在幾乎所有情境下都適用。

**來源**: Canadian Data Guy — "Spark Streaming Best Practices"

## 初學者檢核清單 (Beginner Checklist)

### 1. 始終設定觸發間隔 (Trigger Interval)

```python
# ✅ 好: 控制 API 成本與列表操作
stream.writeStream \
    .trigger(processingTime='5 seconds') \
    .start()

# ❌ 壞: 無觸發器表示連續微批次
# 可能導致過多的 S3/ADLS 列表成本
```

**原因**: 快速處理 (<1 秒) 會重複列表操作，導致意外成本。

### 2. 使用 Auto Loader 通知模式

```python
# 從檔案列表切換至事件基礎模式
spark.readStream \
    .format("cloudFiles") \
    .option("cloudFiles.useNotifications", "true") \
    .load("/path/to/data")
```

[Auto Loader 檔案通知模式](https://docs.databricks.com/ingestion/auto-loader/file-notification-mode.html)

### 3. 先用 S3 版本控制

```python
# ❌ 不要在有 Delta 的 S3 儲存體上啟用版本控制
# ✅ Delta 具備 Time Travel — 無需 S3 版本控制
# 版本控制會在規模擴大時顯著增加延遲
```

### 4. 同地部署運算與儲存 (Co-Locate Compute and Storage)

```python
# ✅ 保持運算與儲存在同一區域
# 跨區域 = 延遲 + 流量成本
```

### 5. 在 Azure 上使用 ADLS Gen2

```python
# ✅ ADLS Gen2 專為大數據分析優化
# ❌ 一般 Blob Storage = 效能較慢
```

### 6. 分區策略 (Partition Strategy)

```python
# ✅ 依低基數欄位分區: date, region, country
# ❌ 避免高基數: user_id, transaction_id

# 經驗法則: < 100,000 分區
# 範例: 10 年 × 365 天 × 20 國家 = 73,000 分區 ✅
```

### 7. 命名您的串流查詢

```python
# ✅ 在 Spark UI 中易於識別
stream.writeStream \
    .option("queryName", "IngestFromKafka") \
    .start()

# 在 Streaming 頁籤中顯示為 "IngestFromKafka"
```

### 8. 每個串流一個檢查點

```python
# ✅ 每個串流擁有自己的檢查點
# ❌ 絕不在串流間共用檢查點

# 範例: 兩個來源 → 一個目標
# Source 1 → checkpoint_1 → target
# Source 2 → checkpoint_2 → target
```

### 9. 不要多工串流 (Multiplex Streams)

```python
# ❌ 不要在同一個 Driver 上執行多個串流
# 可能導致穩定性問題

# ✅ 使用個別 Job 或徹底進行基準測試
```

### 10. 最佳分區大小

```python
# 目標: 記憶體中每個分區 100-200MB

# 透過以下選項調校:
.option("maxFilesPerTrigger", "100")
.option("maxBytesPerTrigger", "100MB")

# 在 Spark UI 監控 → Stages → Partition size
```

### 11. 偏好廣播雜湊關聯 (Broadcast Hash Join)

```python
# ✅ BroadcastHashJoin 比 SortMergeJoin 快
# Spark 自動廣播 < 100MB 的資料表

# 若需要可增加閾值:
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "1g")
```

## 進階檢核清單 (Advanced Checklist)

### 12. 檢查點命名慣例

```python
# 結構: {table_location}/_checkpoints/_{target_table_name}_starting_{identifier}

# 範例:
# 1. 依時間戳記: /delta/events/_checkpoints/_events_starting_2024_01_15
# 2. 依版本: /delta/events/_checkpoints/_events_startingVersion_12345

# 原因: 資料表生命週期中可能有多個檢查點 (升級、邏輯變更)
```

### 13. 最小化 Shuffle 溢寫 (Spill)

```python
# ✅ 目標: Shuffle 溢寫 (磁碟) = 0
# ✅ 應僅存在 Shuffle 讀取

# 檢查: Spark UI → SQL → Exchange operators
# 若 spill > 0: 增加記憶體或減少分區大小
```

### 14. 為有狀態操作使用 RocksDB

```python
# 對於大型狀態儲存，使用 RocksDB 後端
spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateProvider"
)
```

### 15. 透過 Kafka Connector 連接 Event Hubs

```python
# ✅ 對 Azure Event Hubs 使用 Kafka 協定
# 更靈活的分區處理

# 註: 使用 EventHubs Kafka connector
# 核心數可不同於分區數
# (相較於原生 EventHubs: 核心數 == 分區數)
```

### 16. 用於狀態清理的浮水印

```python
# ✅ 有狀態操作始終使用浮水印
# 防止狀態無限增長

stream.withWatermark("timestamp", "10 minutes") \
    .groupBy("user_id") \
    .agg(sum("amount"))

# 例外: 若需要無限狀態，儲存至 Delta + ZORDER
```

### 17. 大規模去重 (Deduplication)

```python
# 在兆級記錄規模下:
# ✅ 使用 Delta Merge 替代 dropDuplicates

# dropDuplicates: 狀態儲存增長巨大
# Delta merge: 使用資料表進行查找

# 範例:
spark.sql("""
    MERGE INTO target t
    USING source s ON t.event_id = s.event_id
    WHEN NOT MATCHED THEN INSERT *
""")
```

### 18. Azure 執行個體系列選擇

| 工作負載 | 執行個體系列 |
|----------|----------------|
| Map 密集型 (解析, JSON) | F-series |
| 同一來源多個串流 | Fsv2-series |
| Joins/聚合/Optimize | DS_v2-series |
| Delta 快取 | L-series (SSD) |

### 19. Shuffle 分區

```python
# 設定為等於總 Worker 核心數
spark.conf.set("spark.sql.shuffle.partitions", "200")

# ❌ 不要設定太高
# 若變更: 清除檢查點 (儲存了舊值)
```

## 快速參考 (Quick Reference)

### 觸發器選擇

| 延遲需求 | 觸發器 |
|---------------------|---------|
| < 1 秒 | 即時模式 (RTM) |
| 1-10 秒 | processingTime('5 seconds') |
| 1-60 分鐘 | 基於 SLA/3 的 processingTime |
| 類批次 | availableNow=True |

### 叢集規模調整

```python
# 串流建議使用固定大小叢集
# ❌ 串流工作負載不使用自動縮放

# 原因: 預先配置資源 = 可預測的延遲
```

## 監控檢核清單 (Monitoring Checklist)

- [ ] Input rate vs processing rate (Processing > Input)
- [ ] Max offsets behind latest (應隨時間減少)
- [ ] Batch duration vs trigger interval (保留餘裕)
- [ ] 狀態儲存大小 (若使用有狀態操作)
- [ ] Shuffle spill = 0
- [ ] Left joins 中的空值率 (資料品質)

## 常見錯誤 (Common Mistakes)

| 錯誤 | 影響 | 修正 |
|---------|--------|-----|
| 共用檢查點 | 資料遺失/損毀 | 分離檢查點 |
| 無浮水印 | 狀態爆炸 | 加入浮水印 |
| S3 版本控制 | 延遲 | 停用版本控制 |
| 自動縮放叢集 | 不可預測的延遲 | 固定大小叢集 |
| 高基數分區 | 小檔案 | 依日期分區 |

## 相關技能 (Related Skills)

- `spark-streaming-master-class-kafka-to-delta` — 端對端模式
- `mastering-checkpoints-in-spark-streaming` — 檢查點深入探討
- `scaling-spark-streaming-jobs` — 效能調校
