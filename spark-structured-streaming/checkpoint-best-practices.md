---
name: checkpoint-best-practices
description: 設定與管理 Spark Structured Streaming 的檢查點位置以確保可靠性。適用於設定新的串流作業、排除檢查點問題、遷移檢查點，或透過適當的檢查點儲存與組織確保 Exactly-once 語義。
---

# 檢查點最佳實踐 (Checkpoint Best Practices)

設定檢查點位置以確保具有 Exactly-once (精確一次) 語義的可靠串流。檢查點用於追蹤進度並實現容錯能力。

## 快速入門 (Quick Start)

```python
def get_checkpoint_location(table_name):
    """綁定至目標資料表的檢查點"""
    return f"/Volumes/catalog/checkpoints/{table_name}"

# 範例:
# Table: prod.analytics.orders
# Checkpoint: /Volumes/prod/checkpoints/orders

query = (df
    .writeStream
    .format("delta")
    .option("checkpointLocation", get_checkpoint_location("orders"))
    .start("/delta/orders")
)
```

## 檢查點儲存 (Checkpoint Storage)

### 使用持久化儲存 (Use Persistent Storage)

```python
# DO: 使用 Unity Catalog 磁碟區 (S3/ADLS-backed)
checkpoint_path = "/Volumes/catalog/checkpoints/stream_name"

# DON'T: 使用 DBFS (暫時性, workspace-local)
checkpoint_path = "/dbfs/checkpoints/stream_name"  # 避免使用
```

### 綁定目標的組織方式 (Target-Tied Organization)

```python
def get_checkpoint_location(table_name):
    """檢查點應綁定至TARGET(目標)，而非來源"""
    return f"/Volumes/catalog/checkpoints/{table_name}"

# 為何綁定目標？
# - 檢查點已包含來源資訊
# - 系統化的組織
# - 易於備份與還原
# - 此明確的所有權
```

### 每個串流使用唯一檢查點 (Unique Checkpoint Per Stream)

```python
# 正確: 每個串流擁有自己的檢查點
stream1.writeStream \
    .option("checkpointLocation", "/checkpoints/stream1") \
    .start()

stream2.writeStream \
    .option("checkpointLocation", "/checkpoints/stream2") \
    .start()

# 錯誤: 絕不在串流間共用檢查點
# 這會導致資料遺失與損毀
```

## 檢查點結構 (Checkpoint Structure)

### 資料夾內容

```
checkpoint_location/
├── metadata/      # 查詢 ID (Query ID)
├── offsets/       # 要處理的內容 (意圖 intent)
├── commits/       # 完成的內容 (確認 confirmation)
├── sources/       # 來源中繼資料
└── state/         # 有狀態操作 (若有)
```

### 無狀態 vs 有狀態 (Stateless vs Stateful)

```python
# 無狀態 (從 Kafka 讀取, 寫入 Delta)
# Checkpoint: metadata, offsets, commits, sources
# 無 state 資料夾

df = (spark.readStream
    .format("kafka")
    .option("subscribe", "topic")
    .load())

# 有狀態 (含浮水印與去重)
# Checkpoint: + state 資料夾
df_stateful = (df
    .withWatermark("timestamp", "10 minutes")
    .dropDuplicates(["partition", "offset"])
)
```

## 讀取檢查點內容 (Reading Checkpoint Contents)

### 讀取偏移量檔案 (Read Offset Files)

```python
import json

# 讀取偏移量檔案
offset_file = "/checkpoints/stream/offsets/223"
content = dbutils.fs.head(offset_file)
offset_data = json.loads(content)

# 美化列印
print(json.dumps(offset_data, indent=2))

# 關鍵欄位:
# - batchWatermarkMs: 浮水印時間戳記
# - batchTimestampMs: 批次開始時間
# - source[0].startOffset: 批次起點 (包含)
# - source[0].endOffset: 批次終點 (排除)
# - source[0].latestOffset: 來源目前位置
```

### 讀取狀態儲存 (Read State Store)

```python
# 直接查詢狀態儲存
state_df = (spark
    .read
    .format("statestore")
    .load("/checkpoints/stream/state")
)

state_df.show()
# 顯示: key, value, partitionId, expiration timestamp

# 讀取狀態中繼資料
state_metadata = (spark
    .read
    .format("state-metadata")
    .load("/checkpoints/stream")
)
state_metadata.show()
# 顯示: operatorName, numPartitions, minBatchId, maxBatchId
```

## 復原情境 (Recovery Scenarios)

### 遺失檢查點 (Lost Checkpoint)

```python
# 復原步驟:
# 1. 刪除檢查點資料夾
dbutils.fs.rm("/checkpoints/stream", recurse=True)

# 2. 以 startingOffsets=earliest 重啟串流
df.writeStream \
    .format("delta") \
    .option("checkpointLocation", "/checkpoints/stream") \
    .option("startingOffsets", "earliest") \
    .start()

# 3. 串流從頭重新處理
# 4. Delta sink 處理去重 (若已設定冪等寫入)
```

### 檢查點損毀 (Corrupted Checkpoint)

```python
# 同遺失檢查點:
# 1. 刪除檢查點資料夾
# 2. 以 startingOffsets=earliest 重啟
# 3. 或從備份還原 (若有)

# 在重大變更前備份檢查點
dbutils.fs.cp(
    "/checkpoints/stream",
    "/checkpoints/stream_backup_20240101",
    recurse=True
)
```

### 批次期間崩潰 (Crash During Batch)

```python
# 情境: 批次處理期間崩潰
# - 最新 offset = 223 (開始時寫入)
# - Commit 223 遺失 (完成前崩潰)
# - 重啟時: Spark 重新處理 offset 223
# - Delta 去重防止重複資料 (若已設定 txnVersion)
```

## 監控 (Monitoring)

### 檢查點大小 (Checkpoint Size)

```python
# 追蹤檢查點資料夾大小
checkpoint_size = dbutils.fs.ls("/checkpoints/stream")
total_size = sum([f.size for f in checkpoint_size if f.isFile()])
print(f"Checkpoint size: {total_size / (1024*1024):.2f} MB")

# 針對檢查點存取失敗發出警報
try:
    dbutils.fs.ls("/checkpoints/stream")
except Exception as e:
    print(f"Checkpoint access failed: {e}")
    # 發送警報
```

### 狀態儲存增長 (State Store Growth)

```python
# 監控狀態儲存大小 (有狀態作業)
state_df = spark.read.format("statestore").load("/checkpoints/stream/state")

# 檢查分區平衡
state_df.groupBy("partitionId").count().orderBy(desc("count")).show()

# 尋找傾斜 (Skew) - 若一分區為其他 10 倍 = 有問題
# State size = f(watermark duration, key cardinality)
```

### Offset vs Commit 同步

```python
# 檢查 offset 是否有對應的 commit
import json

# 讀取最新 offset
latest_offset_file = sorted(dbutils.fs.ls("/checkpoints/stream/offsets"))[-1].path
offset_data = json.loads(dbutils.fs.head(latest_offset_file))
batch_id = latest_offset_file.split("/")[-1]

# 檢查 commit 是否存在
commit_file = f"/checkpoints/stream/commits/{batch_id}"
if dbutils.fs.exists(commit_file):
    print(f"Batch {batch_id}: Committed")
else:
    print(f"Batch {batch_id}: Not committed (will reprocess)")
```

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **狀態增長過大** | 浮水印期間過長或高基數鍵值 (High Cardinality Keys) | 縮短浮水印期間; 降低鍵值基數 |
| **檢查點損毀** | 檔案系統問題或手動刪除 | 刪除檢查點並重啟; 從備份還原 |
| **狀態操作緩慢** | 分區不平衡 | 檢查分區平衡; 確保鍵值均勻分佈 |
| **找不到 commit 檔案** | 若作業崩潰屬正常現象 | Spark 會在重啟時重新處理 |
| **Offsets 不同步** | Offsets 無對應 commits | 表示未處理的批次; 將重新處理 |

## 生產最佳實踐 (Production Best Practices)

### 檢查點位置模式

```python
def get_checkpoint_path(table_name, environment="prod"):
    """
    檢查點應:
    1. 綁定至 TARGET 資料表 (非來源)
    2. 位於持久化儲存 (UC Volume, S3, ADLS)
    3. 系統化組織
    """
    return f"/Volumes/{environment}/checkpoints/{table_name}"

# 使用方式
checkpoint = get_checkpoint_path("orders", "prod")
```

### 備份策略

```python
# 在重大變更前備份檢查點
def backup_checkpoint(checkpoint_path, backup_suffix):
    backup_path = f"{checkpoint_path}_backup_{backup_suffix}"
    dbutils.fs.cp(checkpoint_path, backup_path, recurse=True)
    return backup_path

# 在程式碼變更或遷移前
backup_checkpoint("/checkpoints/stream", "20240101")
```

### 遷移 (Migration)

```python
# 遷移檢查點至新位置
def migrate_checkpoint(old_path, new_path):
    # 複製檢查點資料夾
    dbutils.fs.cp(old_path, new_path, recurse=True)
    
    # 更新程式碼以使用新路徑
    # 舊檢查點保留以便 rollback
    
    # 使用新檢查點位置重啟串流
```

## 生產檢核清單 (Production Checklist)

- [ ] 檢查點位置為持久化儲存 (S3/ADLS, 非 DBFS)
- [ ] 每個串流使用唯一檢查點
- [ ] 綁定目標的檢查點組織
- [ ] 定義備份策略
- [ ] 設定監控 (檢查點大小, 存取失敗)
- [ ] 監控狀態儲存增長 (若為有狀態)
- [ ] 記錄復原程序
- [ ] 記錄遷移程序

## 相關技能 (Related Skills)

- `kafka-to-delta` - 包含檢查點管理的 Kafka 攝取
- `stream-stream-joins` - 有狀態操作與狀態儲存
- `state-store-management` - 狀態儲存優化深入探討
