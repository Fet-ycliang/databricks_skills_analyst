---
name: trigger-and-cost-optimization
description: 選擇並調校 Spark Structured Streaming 的觸發器以平衡延遲與成本。適用於在 processingTime、availableNow 與即時模式 (RTM) 之間做選擇、計算最佳觸發間隔、透過叢集規模最適化、排程串流、多串流叢集來優化成本，或管理延遲與成本的權衡。
---

# 觸發器與成本優化 (Trigger and Cost Optimization)

選擇並調校觸發器以平衡延遲需求與成本。透過觸發器調校、叢集規模最適化、多串流叢集、儲存優化與排程執行模式來優化串流作業成本。

## 快速入門 (Quick Start)

```python
# 成本優化: 排程串流而非持續執行
df.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/stream") \
    .trigger(availableNow=True) \  # 處理所有資料後停止
    .start("/delta/target")

# 透過 Databricks Jobs 排程: 每 15 分鐘
# 成本: 100 個資料表在 8 核心叢集上約 ~$20/天
```

## 觸發器類型 (Trigger Types)

### ProcessingTime 觸發器

以固定間隔處理：

```python
# 每 30 秒處理一次
.trigger(processingTime="30 seconds")

# 每 5 分鐘處理一次
.trigger(processingTime="5 minutes")

# 延遲: 觸發間隔 + 處理時間
# 成本: 持續執行的叢集
```

### AvailableNow 觸發器

處理所有可用資料後停止：

```python
# 處理所有可用資料後停止
.trigger(availableNow=True)

# 透過 Databricks Jobs 排程:
# - 每 15 分鐘: 近即時
# - 每 4 小時: 類批次

# 延遲: 排程間隔 + 處理時間
# 成本: 叢集僅在處理期間執行
```

### 即時模式 (Real-Time Mode / RTM)

搭配 Photon 實現亞秒級延遲：

```python
# 即時模式 (Databricks 13.3+)
.trigger(realTime=True)

# 需求:
# - 啟用 Photon
# - 固定大小叢集 (無自動縮放)
# - 延遲: < 800ms

# 成本: 搭配 Photon 的持續執行叢集
```

## 觸發器選擇指南

| 延遲需求 | 觸發器 | 成本 | 使用案例 |
|---------------------|---------|------|----------|
| < 800ms | RTM | $$$ | 即時分析, 警報 |
| 1-30 秒 | processingTime | $$ | 近即時儀表板 |
| 15-60 分鐘 | availableNow (排程) | $ | 類批次 SLA |
| > 1 小時 | availableNow (排程) | $ | ETL 管線 |

## 觸發間隔計算

### 經驗法則: SLA / 3

```python
# 從 SLA 計算觸發間隔
business_sla_minutes = 60  # 1 小時 SLA
trigger_interval_minutes = business_sla_minutes / 3  # 20 分鐘

.trigger(processingTime=f"{trigger_interval_minutes} minutes")

# 為何除以 3?
# - 處理時間緩衝
# - 復原時間緩衝
# - 安全邊際
```

### 計算範例

```python
# 範例 1: 1 小時 SLA
sla = 60  # 分鐘
trigger = sla / 3  # 20 分鐘
.trigger(processingTime="20 minutes")

# 範例 2: 15 分鐘 SLA
sla = 15  # 分鐘
trigger = sla / 3  # 5 分鐘
.trigger(processingTime="5 minutes")

# 範例 3: 即時需求
.trigger(realTime=True)  # < 800ms
```

## 成本優化策略

### 策略 1: 觸發間隔調校

平衡延遲與成本：

```python
# 較短間隔 = 較高成本
.trigger(processingTime="5 seconds")   # 昂貴 - 持續處理

# 較長間隔 = 較低成本
.trigger(processingTime="5 minutes")   # 較便宜 - 處理頻率較低

# 使用 availableNow 進行類批次 (最便宜)
.trigger(availableNow=True)            # 處理積壓後停止

# 經驗法則: SLA / 3
# 範例: 1 小時 SLA → 20 分鐘觸發
```

### 策略 2: 排程 vs 持續

根據 SLA 選擇執行模式：

| 模式 | 成本 | 延遲 | 使用案例 |
|---------|------|---------|----------|
| 持續 | $$$ | < 1 分鐘 | 即時需求 |
| 15 分鐘排程 | $$ | 15-30 分鐘 | 近即時 |
| 4 小時排程 | $ | 4-5 小時 | 類批次 SLA |

```python
# 持續 (昂貴)
.trigger(processingTime="30 seconds")

# 排程 (具成本效益)
.trigger(availableNow=True)  # 透過 Jobs 排程: 每 15 分鐘

# 類批次 (最便宜)
.trigger(availableNow=True)  # 透過 Jobs 排程: 每 4 小時
```

### 策略 3: 叢集規模最適化 (Cluster Right-Sizing)

根據工作負載調整叢集大小：

```python
# 不要過度配置:
# - 監控 CPU 使用率 (目標 60-80%)
# - 檢查閒置時間
# - 使用固定大小叢集 (串流不使用自動縮放)

# 擴展測試方法:
# 1. 從小規模開始
# 2. 監控 Lag (max offsets behind latest)
# 3. 若落後則擴展 (Scale up)
# 4. 根據穩定狀態進行最適化 (Right-size)
```

### 策略 4: 多串流叢集 (Multi-Stream Clusters)

在一個叢集上執行多個串流：

```python
# 在一個叢集上執行多個串流
# 已測試: 8 核心單節點叢集上執行 100 個串流
# 成本: 100 個資料表約 ~$20/天

# 範例: 同一叢集上的多個串流
stream1.writeStream.option("checkpointLocation", "/checkpoints/stream1").start()
stream2.writeStream.option("checkpointLocation", "/checkpoints/stream2").start()
stream3.writeStream.option("checkpointLocation", "/checkpoints/stream3").start()
# ... 超過 100+ 個串流

# 監控: 每個串流的 CPU/記憶體
# 若總使用率 > 80% 則擴展叢集
```

### 策略 5: 儲存優化

降低儲存成本：

```sql
# VACUUM 舊檔案
VACUUM table RETAIN 24 HOURS;

# 啟用自動優化以減少小檔案
ALTER TABLE table SET TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = true,
    'delta.autoOptimize.autoCompact' = true
);

# 封存舊資料至較便宜的儲存體
# 使用資料保留策略
```

## 成本公式

```
每日成本 = 
    (Cluster DBU/小時 × 執行時數) +
    (儲存 GB × 儲存費率) +
    (網路流量 若適用)

優化槓桿:
- 減少執行時數 (排程觸發)
- 縮小叢集規模 (Right-sizing)
- 減少儲存 (VACUUM, 壓縮)
- 減少網路流量 (同地部署運算與儲存)
```

## 常見模式 (Common Patterns)

### 模式 1: 成本優化的排程串流

將持續執行轉換為排程執行：

```python
# 之前: 持續 (昂貴)
df.writeStream \
    .trigger(processingTime="30 seconds") \
    .start()

# 之後: 排程 (具成本效益)
df.writeStream \
    .trigger(availableNow=True) \  # 處理所有資料後停止
    .start()

# 透過 Databricks Jobs 排程:
# - 每 15 分鐘: 近即時
# - 每 4 小時: 類批次
# 相同程式碼，不同排程
```

### 模式 2: 多串流叢集

優化叢集利用率：

```python
# 在一個叢集上執行多個串流
def start_all_streams():
    streams = []
    
    # 啟動多個串流
    for i in range(100):
        stream = (spark
            .readStream
            .table(f"source_{i}")
            .writeStream
            .format("delta")
            .option("checkpointLocation", f"/checkpoints/stream_{i}")
            .trigger(availableNow=True)
            .start(f"/delta/target_{i}")
        )
        streams.append(stream)
    
    return streams

# 監控總 CPU/記憶體
# 若需要則擴展叢集
```

### 模式 3: 適用於亞秒級延遲的 RTM

針對即時需求使用 RTM：

```python
# 適用於亞秒級延遲的即時模式
df.writeStream \
    .format("kafka") \
    .option("topic", "output") \
    .trigger(realTime=True) \
    .start()

# 必要設定:
spark.conf.set("spark.databricks.photon.enabled", "true")
spark.conf.set("spark.sql.streaming.stateStore.providerClass", 
               "com.databricks.sql.streaming.state.RocksDBStateProvider")

# 延遲: < 800ms
# 成本: 搭配 Photon 的持續執行叢集
```

## 即時模式 (RTM) 設定

### 啟用 RTM

```python
# 啟用即時模式
.trigger(realTime=True)

# 必要設定:
spark.conf.set("spark.databricks.photon.enabled", "true")
spark.conf.set("spark.sql.streaming.stateStore.providerClass", 
               "com.databricks.sql.streaming.state.RocksDBStateProvider")

# 叢集需求:
# - 固定大小叢集 (無自動縮放)
# - 啟用 Photon
# - Driver: 至少 4 核心
```

### RTM 使用案例

```python
# 適合 RTM:
# - 亞秒級延遲需求
# - 簡單轉換
# - 無狀態操作
# - Kafka-to-Kafka 管線

# 不建議 RTM:
# - 有狀態操作 (聚合, Joins)
# - 複雜轉換
# - 大批次大小
```

## 效能考量

### 批次期間 vs 觸發間隔

```python
# 批次期間應 < 觸發間隔
# 範例:
trigger_interval = 30  # 秒
batch_duration = 10  # 秒

# 健康: batch_duration < trigger_interval
# 不健康: batch_duration >= trigger_interval

# 在 Spark UI 中監控:
# - Batch duration
# - Trigger interval
# - 若 batch duration >= trigger interval 則發出警報
```

### 觸發間隔調校

```python
# 從保守值開始，根據監控優化
# 步驟 1: 從 SLA / 3 開始
trigger_interval = business_sla / 3

# 步驟 2: 監控 batch duration
# 若 batch duration < trigger_interval / 2: 可增加觸發頻率 (縮短間隔)
# 若 batch duration >= trigger_interval: 降低觸發頻率 (增長間隔)

# 步驟 3: 優化成本 vs 延遲
# 增加觸發間隔以降低成本
# 減少觸發間隔以降低延遲
```

## 成本監控

### 追蹤個別串流成本

```python
# 為 Jobs 加上串流名稱標籤
job_tags = {
    "stream_name": "orders_stream",
    "environment": "prod",
    "cost_center": "analytics"
}

# 使用 DBU 消耗指標
# 依 Workspace/Cluster 監控
# 隨時間追蹤每個串流的成本
```

### 監控叢集利用率

```python
# 檢查 CPU 使用率
# 目標: 60-80% 利用率
# 低於 60%: 考慮縮減規模 (Downsizing)
# 高於 80%: 考慮擴大規模 (Upsizing)

# 檢查記憶體利用率
# 監控 OOM 錯誤
# 相應調整叢集大小
```

## 延遲 vs 成本權衡

### 持續處理

```python
# 高成本, 低延遲
.trigger(processingTime="30 seconds")

# 成本: 持續執行的叢集
# 延遲: 30 秒 + 處理時間
# 使用時機: 即時需求
```

### 排程處理

```python
# 較低成本, 較高延遲
.trigger(availableNow=True)  # 排程: 每 15 分鐘

# 成本: 叢集僅在處理期間執行
# 延遲: 排程間隔 + 處理時間
# 使用時機: 可接受類批次 SLA
```

### 即時模式

```python
# 最高成本, 最低延遲
.trigger(realTime=True)

# 成本: 搭配 Photon 的持續執行叢集
# 延遲: < 800ms
# 使用時機: 需要亞秒級延遲
```

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **高延遲** | 觸發間隔太長 | 減少觸發間隔或使用 RTM |
| **高成本** | 持續處理 | 使用排程 (availableNow) |
| **批次期間 > 觸發** | 處理太慢 | 優化處理或增加觸發間隔 |
| **RTM 未運作** | 未啟用 Photon | 啟用 Photon 並設定叢集 |

## 快速致勝 (Quick Wins)

1.  **從持續改為 15 分鐘排程** -顯著降低成本
2.  **每個叢集執行多個串流** - 較佳的叢集利用率
3.  **啟用自動優化** - 降低儲存成本
4.  **使用 Spot 執行個體** - 用於非關鍵串流 (謹慎使用)
5.  **封存舊資料** - 移至較便宜的儲存層級

## 權衡 (Trade-offs)

| 成本降低 | 影響 | 緩解措施 |
|----------------|--------|------------|
| 較長觸發 | 較高延遲 | 若 SLA 允許則可接受 |
| 較小叢集 | 可能落後 | 監控 Lag; 若需要則擴展 |
| 積極 VACUUM | 較少 Time Travel | 平衡保留期 vs 成本 |
| Spot 執行個體 | 可能中斷 | 用於非關鍵串流 |
| 排程 vs 持續 | 較高延遲 | 配合業務 SLA |

## 生產最佳實踐 (Production Best Practices)

### 配合 SLA 設定觸發器

```python
# 從業務 SLA 計算觸發器
def calculate_trigger_interval(sla_minutes):
    """計算最佳觸發間隔"""
    return max(30, sla_minutes / 3)  # 最小 30 秒

trigger_interval = calculate_trigger_interval(business_sla_minutes)
.trigger(processingTime=f"{trigger_interval} seconds")
```

### 叢集設定

```python
# 固定大小叢集 (串流不使用自動縮放)
cluster_config = {
    "num_workers": 4,
    "node_type_id": "i3.xlarge",
    "autotermination_minutes": 60,  # 若閒置則終止
    "enable_elastic_disk": True  # 降低儲存成本
}
```

### 儲存管理

```sql
# 啟用自動優化
ALTER TABLE table SET TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = true,
    'delta.autoOptimize.autoCompact' = true
);

# 定期 VACUUM
VACUUM table RETAIN 7 DAYS;  # 平衡保留期 vs 成本

# 封存舊分區
# 移至較便宜的儲存層級
```

## 生產檢核清單 (Production Checklist)

- [ ] 根據延遲需求選擇觸發器類型
- [ ] 從 SLA 計算觸發間隔 (SLA / 3)
- [ ] 監控批次期間 (< 觸發間隔)
- [ ] 叢集規模最適化 (60-80% 利用率)
- [ ] 每個叢集多個串流 (若適用)
- [ ] 排程執行 (若 SLA 允許)
- [ ] 若需亞秒級延遲則設定 RTM
- [ ] 啟用自動優化
- [ ] 監控儲存成本
- [ ] 追蹤每個串流的成本

## 相關技能 (Related Skills)

- `kafka-streaming` - Kafka 管線的 RTM 設定
- `checkpoint-best-practices` - 檢查點管理
