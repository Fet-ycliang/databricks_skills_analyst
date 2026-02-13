---
name: merge-operations
description: 串流中 Delta MERGE 操作的綜合指南，包括效能優化、平行合併 (Parallel Merges) 以及 Liquid Clustering 設定。適用於實作 Upserts、優化合併效能、執行多表平行合併，或消除最佳化暫停 (Optimize Pauses)。
---

# 串流中的合併操作 (Merge Operations)

Delta MERGE 操作綜合指南：效能優化、多表平行合併，以及現代 Delta 功能 (Liquid Clustering + Deletion Vectors + Row-Level Concurrency)。

## 快速入門 (Quick Start)

### 具備優化的基本 MERGE

```python
from delta.tables import DeltaTable

# 啟用現代 Delta 功能
spark.sql("""
    ALTER TABLE target_table SET TBLPROPERTIES (
        'delta.enableDeletionVectors' = true,
        'delta.enableRowLevelConcurrency' = true,
        'delta.liquid.clustering' = true
    )
""")

# ForEachBatch 中的 MERGE
def upsert_batch(batch_df, batch_id):
    batch_df.createOrReplaceTempView("updates")
    spark.sql("""
        MERGE INTO target_table t
        USING updates s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    # 無需 optimize - Liquid Clustering 會自動處理

stream.writeStream \
    .foreachBatch(upsert_batch) \
    .option("checkpointLocation", "/checkpoints/merge") \
    .start()
```

### 多資料表平行 MERGE

```python
from delta.tables import DeltaTable
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_merge_multiple_tables(batch_df, batch_id):
    """平行合併至多個資料表"""
    
    batch_df.cache()
    
    def merge_table(table_name, merge_key):
        target = DeltaTable.forName(spark, table_name)
        source = batch_df.alias("source")
        
        (target.alias("target")
            .merge(source, f"target.{merge_key} = source.{merge_key}")
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        return f"Merged {table_name}"
    
    tables = [
        ("silver.customers", "customer_id"),
        ("silver.orders", "order_id"),
        ("silver.products", "product_id")
    ]
    
    # 平行合併
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(merge_table, table_name, merge_key): table_name
            for table_name, merge_key in tables
        }
        
        for future in as_completed(futures):
            future.result()  # 發生錯誤時拋出
    
    batch_df.unpersist()

stream.writeStream \
    .foreachBatch(parallel_merge_multiple_tables) \
    .option("checkpointLocation", "/checkpoints/parallel_merge") \
    .start()
```

## 核心概念 (Core Concepts)

### Liquid Clustering + DV + RLC

啟用現代 Delta 功能以獲得最佳合併效能：

```sql
-- 為目標資料表啟用
ALTER TABLE target_table SET TBLPROPERTIES (
    'delta.enableDeletionVectors' = true,
    'delta.enableRowLevelConcurrency' = true,
    'delta.liquid.clustering' = true
);
```

**效益：**
- **刪除向量 (Deletion Vectors)**：軟刪除 (Soft deletes) 無需重寫檔案
- **資料列層級並行 (Row-Level Concurrency)**：不同資料列的並行更新
- **Liquid Clustering**：無暫停的自動優化
- **結果**：消除最佳化暫停、降低 P99 延遲、程式碼更簡潔

## 常見模式 (Common Patterns)

### 模式 1: 具備優化的基本 MERGE

```python
def optimized_merge(batch_df, batch_id):
    """合併至已優化的資料表"""
    batch_df.createOrReplaceTempView("updates")
    
    spark.sql("""
        MERGE INTO target_table t
        USING updates s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    # 無需 optimize - Liquid Clustering 會處理

stream.writeStream \
    .foreachBatch(optimized_merge) \
    .option("checkpointLocation", "/checkpoints/merge") \
    .start()
```

### 模式 2: 多資料表平行 MERGE

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_merge(batch_df, batch_id):
    """平行合併至多個資料表"""
    
    batch_df.cache()
    
    def merge_one_table(table_name, merge_key):
        target = DeltaTable.forName(spark, table_name)
        source = batch_df.alias("source")
        
        (target.alias("target")
            .merge(source, f"target.{merge_key} = source.{merge_key}")
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        return table_name
    
    tables = [
        ("silver.customers", "customer_id"),
        ("silver.orders", "order_id"),
        ("silver.products", "product_id")
    ]
    
    # 最佳執行緒數: min(資料表數量, 叢集核心數 / 2)
    max_workers = min(len(tables), max(2, total_cores // 2))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(merge_one_table, table_name, merge_key): table_name
            for table_name, merge_key in tables
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
        raise Exception(f"Merge failures: {errors}")
```

### 模式 3: 具備分區修剪 (Partition Pruning) 的 MERGE

```python
def partition_pruned_merge(batch_df, batch_id):
    """條件中包含分區欄位的 MERGE"""
    batch_df.createOrReplaceTempView("updates")
    
    # 在合併條件中包含分區欄位
    spark.sql("""
        MERGE INTO target_table t
        USING updates s 
        ON t.id = s.id AND t.date = s.date  -- 分區欄位
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    # 跳過無關分區以加速執行
```

### 模式 4: CDC 多目標平行 MERGE

```python
def cdc_parallel_merge(batch_df, batch_id):
    """平行套用 CDC 變更至多個資料表"""
    
    batch_df.cache()
    
    # 依操作類型拆分
    deletes = batch_df.filter(col("_op") == "DELETE")
    upserts = batch_df.filter(col("_op").isin(["INSERT", "UPDATE"]))
    
    def merge_cdc_table(table_name, merge_key):
        target = DeltaTable.forName(spark, table_name)
        
        # Upserts
        if upserts.count() > 0:
            (target.alias("target")
                .merge(upserts.alias("source"), f"target.{merge_key} = source.{merge_key}")
                .whenMatchedUpdateAll()
                .whenNotMatchedInsertAll()
                .execute()
            )
        
        # Deletes
        if deletes.count() > 0:
            (target.alias("target")
                .merge(deletes.alias("source"), f"target.{merge_key} = source.{merge_key}")
                .whenMatchedDelete()
                .execute()
            )
    
    tables = [
        ("silver.customers", "customer_id"),
        ("silver.orders", "order_id")
    ]
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(merge_cdc_table, table_name, merge_key): table_name
            for table_name, merge_key in tables
        }
        
        for future in as_completed(futures):
            future.result()
    
    batch_df.unpersist()
```

## 效能優化 (Performance Optimization)

### 啟用 Liquid Clustering + DV + RLC

```sql
-- 建立具備 Liquid Clustering 的資料表
CREATE TABLE target_table (
    id STRING,
    name STRING,
    updated_at TIMESTAMP
) USING DELTA
CLUSTER BY (id)
TBLPROPERTIES (
    'delta.enableDeletionVectors' = true,
    'delta.enableRowLevelConcurrency' = true
);

-- 或修改現有資料表
ALTER TABLE target_table SET TBLPROPERTIES (
    'delta.enableDeletionVectors' = true,
    'delta.enableRowLevelConcurrency' = true,
    'delta.liquid.clustering' = true
);
ALTER TABLE target_table CLUSTER BY (id);
```

### 合併鍵 (Merge Key) 的 Z-Ordering

```sql
-- 對合併鍵進行 Z-Order 以加速查詢
OPTIMIZE target_table ZORDER BY (id);

-- 定期執行或透過 Predictive Optimization 執行
-- 對於特定查詢可快 5-10 倍
```

### 檔案大小調校 (File Size Tuning)

```sql
-- 設定最佳合併的目標檔案大小
ALTER TABLE target_table SET TBLPROPERTIES (
    'delta.targetFileSize' = '128mb'
);
```

### 最佳執行緒數 (Optimal Thread Count)

```python
# 公式: min(資料表數量, 叢集核心數 / 2)
# 範例: 4 tables, 8 cores → 4 workers
# 範例: 2 tables, 4 cores → 2 workers

max_workers = min(len(tables), max(2, total_cores // 2))
```

## 監控 (Monitoring)

### 追蹤合併效能

```python
import time

def monitored_merge(batch_df, batch_id):
    start_time = time.time()
    
    batch_df.createOrReplaceTempView("updates")
    spark.sql("""
        MERGE INTO target_table t
        USING updates s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    
    duration = time.time() - start_time
    print(f"Merge duration: {duration:.2f}s")
    
    # 若執行時間超過閾值則發出警報
    if duration > 30:
        print(f"WARNING: Merge duration {duration:.2f}s exceeds threshold")
```

## 常見問題 (Common Issues)

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **高 P99 延遲** | OPTIMIZE 暫停 | 啟用 Liquid Clustering (無暫停) |
| **合併衝突** | 同時更新相同資料列 | 啟用 Row-Level Concurrency |
| **合併緩慢** | 大檔案、未優化 | 啟用 Liquid Clustering; 對合併鍵進行 Z-Order |
| **執行緒過多** | 資源競爭 | 減少 max_workers; 配合叢集容量 |
| **部分失敗** | 單一合併失敗 | 收集所有錯誤; 若有任何錯誤則整批失敗 |

## 生產檢核清單 (Production Checklist)

- [ ] 所有目標資料表啟用 Liquid Clustering + DV + RLC
- [ ] 合併鍵設定 Z-Ordering
- [ ] 設定最佳執行緒數 (從 2 開始)
- [ ] 實作錯誤處理 (收集所有錯誤)
- [ ] 每個資料表的效能監控
- [ ] 使用 Cache 避免重複計算
- [ ] 寫入後 Unpersist
- [ ] 檔案大小調校 (目標 128MB)

## 相關技能 (Related Skills)

- `multi-sink-writes` - 多重目標寫入模式
- `partitioning-strategy` - 合併的分區優化
- `checkpoint-best-practices` - 檢查點設定
