# Python API: 現代化 vs 舊版 (Modern vs Legacy)

**最後更新**: 2026 年 1 月
**狀態**: 對於所有新專案，推薦使用現代化 API (`pyspark.pipelines`)

---

## 概述

Databricks 為 Spark Declarative Pipelines 提供兩種 Python API：

1.  **現代化 API (Modern API)** (`pyspark.pipelines` as `dp`) - **推薦 (2025)**
2.  **舊版 API (Legacy API)** (`dlt`) - 舊的 Delta Live Tables API，仍受支援

**關鍵建議**: 新專案務必使用 **現代化 API**。僅在維護現有 DLT 程式碼時使用舊版。

---

## 快速比較

| 面向 | 現代化 (`dp`) | 舊版 (`dlt`) |
|--------|---------------|----------------|
| **匯入** | `from pyspark import pipelines as dp` | `import dlt` |
| **狀態** | ✅ **推薦** | ⚠️ Legacy |
| **資料表裝飾器** | `@dp.table()` | `@dlt.table()` |
| **讀取** | `spark.read.table("table")` | `dlt.read("table")` |
| **CDC/SCD** | `dp.create_auto_cdc_flow()` | `dlt.apply_changes()` |
| **適用於** | 新專案 | 維護現有專案 |

---

## 對照範例

### 基本資料表定義

**現代化 (推薦)**:
```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.table(name="bronze_events", comment="Raw events")
def bronze_events():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .load("/mnt/raw/events")
    )
```

**舊版**:
```python
import dlt
from pyspark.sql import functions as F

@dlt.table(name="bronze_events", comment="Raw events")
def bronze_events():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .load("/mnt/raw/events")
    )
```

### 讀取資料表

**現代化 (推薦)**:
```python
@dp.table(name="silver_events")
def silver_events():
    # 明確的 Unity Catalog 路徑
    return spark.read.table("bronze_events").filter(...)
```

**舊版**:
```python
@dlt.table(name="silver_events")
def silver_events():
    # 隱含 LIVE schema
    return dlt.read("bronze_events").filter(...)
```

**關鍵差異**: 現代化使用明確 UC 路徑，舊版使用隱含 `LIVE.*`。

### 串流讀取

**現代化 (推薦)**:
```python
@dp.table(name="silver_events")
def silver_events():
    # 具備 Context 感知 (無獨立 read_stream)
    return (
        spark.readStream.table("catalog.schema.bronze_events")
        .filter(F.col("event_type").isNotNull())
    )
```

**舊版**:
```python
@dlt.table(name="silver_events")
def silver_events():
    # 明確串流讀取
    return (
        dlt.read_stream("bronze_events")
        .filter(F.col("event_type").isNotNull())
    )
```

### 資料品質預期 (Data Quality Expectations)

**現代化 (推薦)**:
```python
@dp.table(name="silver_validated")
@dp.expect_or_drop("valid_id", "id IS NOT NULL")
@dp.expect_or_drop("valid_amount", "amount > 0")
@dp.expect_or_fail("critical_field", "timestamp IS NOT NULL")
def silver_validated():
    return spark.read.table("catalog.schema.bronze_events")
```

**舊版**:
```python
@dlt.table(name="silver_validated")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_fail("critical_field", "timestamp IS NOT NULL")
def silver_validated():
    return dlt.read("bronze_events")
```

**注意**: 版本間的 Expectations API 相同。

### SCD Type 2 (AUTO CDC)

**現代化 (推薦)**:
```python
from pyspark.sql.functions import col

dp.create_streaming_table("customers_history")

dp.create_auto_cdc_flow(
    target="customers_history",
    source="customers_cdc",
    keys=["customer_id"],
    sequence_by=col("event_timestamp"),
    stored_as_scd_type="2",
    track_history_column_list=["*"]
)
```

**舊版**:
```python
dlt.create_streaming_table("customers_history")

dlt.apply_changes(
    target="customers_history",
    source="customers_cdc",
    keys=["customer_id"],
    sequence_by="event_timestamp",
    stored_as_scd_type="2",
    track_history_column_list=["*"]
)
```

**關鍵差異**: 現代化使用 `create_auto_cdc_flow()`，舊版使用 `apply_changes()`。

### Liquid Clustering

**現代化 (推薦)**:
```python
@dp.table(
    name="bronze_events",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true"
    },
    cluster_by=["event_type", "event_date"]  # Liquid Clustering
)
def bronze_events():
    return spark.readStream.format("cloudFiles").load("/data")
```

**舊版**:
```python
@dlt.table(
    name="bronze_events",
    table_properties={
        "pipelines.autoOptimize.managed": "true",
        "pipelines.autoOptimize.zOrderCols": "event_type"
    },
    partition_cols=["event_date"]  # 舊版分區
)
def bronze_events():
    return spark.readStream.format("cloudFiles").load("/data")
```

**關鍵差異**: 現代化支援 `cluster_by` 進行 Liquid Clustering。

---

## 決策矩陣

### 使用現代化 API (`dp`) 當：
- ✅ **開始新專案** (預設選擇)
- ✅ **學習 SDP/LDP** (學習目前標準)
- ✅ **想要 Liquid Clustering**
- ✅ **偏好明確 Unity Catalog 路徑**
- ✅ **遵循 2025 最佳實踐**

### 使用舊版 API (`dlt`) 當：
- ⚠️ **維護現有 DLT 管線** (不要重寫正常運作的程式碼)
- ⚠️ **團隊受過 DLT 訓練** (與現有一致)
- ⚠️ **較舊的 DBR 版本** (若無法使用現代化 API)

**預設**: 除非有使用舊版的特定理由，否則使用現代化 `dp` API。

---

## 遷移指南: dlt → dp

### 步驟 1: 更新匯入

**原本**:
```python
import dlt
```

**之後**:
```python
from pyspark import pipelines as dp
```

### 步驟 2: 更新裝飾器

**原本**: `@dlt.table(name="my_table")`
**之後**: `@dp.table(name="my_table")`

### 步驟 3: 更新讀取

**原本**:
```python
dlt.read("source_table")
dlt.read_stream("source_table")
```

**之後**:
```python
spark.table("catalog.schema.source_table")
# 串流具備 Context 感知，無獨立 read_stream
```

### 步驟 4: 更新 CDC/SCD 操作

**原本**:
```python
dlt.apply_changes(target="dim_customer", source="cdc_source", ...)
```

**之後**:
```python
from pyspark.sql.functions import col

dp.create_auto_cdc_flow(
    target="dim_customer",
    source="cdc_source",
    keys=["customer_id"],
    sequence_by=col("event_timestamp"),
    stored_as_scd_type="2",
    track_history_column_list=["*"]
)
```

**關鍵變更**: `dlt.apply_changes()` → `dp.create_auto_cdc_flow()`

### 步驟 5: 更新 Clustering

**原本**: `@dlt.table(partition_cols=["date"])`
**之後**: `@dp.table(cluster_by=["date", "other_col"])`

---

## 關鍵模式 (2025)

### 1. 使用 Liquid Clustering

```python
@dp.table(cluster_by=["key_col", "date_col"])
def my_table():
    return ...

# 或自動
@dp.table(cluster_by=["AUTO"])
def my_table():
    return ...
```

### 2. 明確 UC 路徑

```python
# ✅ 現代化: 明確路徑
spark.table("catalog.schema.table")

# ❌ 舊版: 隱含 LIVE
dlt.read("table")
```

### 3. 用於自訂 Sinks 的 forEachBatch

```python
def write_to_custom_sink(batch_df, batch_id):
    batch_df.write.format("custom").save(...)

@dp.table(name="my_table")
def my_table():
    return (
        spark.readStream
        .format("cloudFiles")
        .load("/data")
        .writeStream
        .foreachBatch(write_to_custom_sink)
    )
```

---

## 總結

**對於新專案**: 使用現代化 `pyspark.pipelines` (`dp`)
- ✅ 目前最佳實踐 (2025)
- ✅ 支援 Liquid Clustering
- ✅ 明確 Unity Catalog 路徑

**對於現有專案**: 舊版 `dlt` 受完整支援
- ⚠️ 方便時遷移，不緊急
- ⚠️ 對新檔案考慮使用現代化 API

**重點**: 現代化 API 提供相同功能外加新特性。所有新專案請以 `from pyspark import pipelines as dp` 開始。
