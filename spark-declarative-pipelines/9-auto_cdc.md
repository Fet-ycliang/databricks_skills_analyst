# 用於變更資料擷取的 AUTO CDC 模式 (AUTO CDC Patterns)

**關鍵字**: Slow Changing Dimension, SCD, SCD Type 1, SCD Type 2, AUTO CDC, change data capture, dp.create_auto_cdc_flow, deduplication

---

## 概述

AUTO CDC 自動處理變更資料擷取 (CDC)，使用緩慢變化維度 (SCD) 追蹤資料變更。它提供自動去重、變更追蹤，並正確處理晚到資料。

**何處應用 AUTO CDC:**
- **Silver 層**: 當業務使用者需要去重或歷史資料進行分析/ML 時
- **Gold 層**: 實作維度模型 (星狀綱要) 搭配 dim/fact tables 時
- **選擇取決於**: 下游消費模式與查詢需求

---

## SCD Type 1 vs Type 2

### SCD Type 1 (就地更新 In-place updates)
- **覆寫** 用新值覆蓋舊值
- **不保留歷史** - 僅維護當前狀態
- **用於**: 不需要歷史的維度屬性
  - 修正資料錯誤 (錯字)
  - 更新歷史不重要的屬性
  - 每個鍵值維持單一當前記錄
- **語法**: `stored_as_scd_type="1"` (字串)

### SCD Type 2 (歷史追蹤 History tracking)
- 每次變更 **建立新資料列**
- 使用 `__START_AT` 與 `__END_AT` 時間戳記 **保留完整歷史**
- **用於**: 追蹤隨時間變化的資料
  - 客戶地址變更
  - 產品價格歷史
  - 員工職位變更
  - 任何需要時序分析的維度
- **語法**: `stored_as_scd_type=2` (整數)

---

## 模式：清理 + AUTO CDC

### 步驟 1: 清理與驗證資料

建立具備適當型別與品質檢查的清理後串流資料表：

```python
# 清理後資料準備 (可為 Silver 或中介層)
from pyspark import pipelines as dp
from pyspark.sql import functions as F

schema = spark.conf.get("schema")

@dp.table(
    name=f"{schema}.users_clean",
    comment="Cleaned and validated user data with proper typing and quality checks",
    cluster_by=["user_id"]
)
def users_clean():
    """
    準備清理後的資料：
    - 適當的時間戳記型別
    - 資料品質驗證
    - 移除無效 email 或 null user_id 的記錄
    """
    return (
        spark.readStream.table("bronze_users")
        .filter(F.col("user_id").isNotNull())
        .filter(F.col("email").isNotNull())
        .filter(F.col("email").rlike(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"))
        .withColumn("created_timestamp", F.to_timestamp("created_timestamp"))
        .withColumn("updated_timestamp", F.to_timestamp("updated_timestamp"))
        .drop("_rescued_data")
        .select(
            "user_id",
            "email",
            "name",
            "subscription_tier",
            "country",
            "created_timestamp",
            "updated_timestamp",
            "_ingested_at",
            "_source_file"
        )
    )
```

### 步驟 2: 應用 AUTO CDC (SCD Type 2)

建立具備完整變更歷史的歷史追蹤維度表：

```python
# AUTO CDC 搭配 SCD Type 2 (history tracking)
from pyspark import pipelines as dp

target_schema = spark.conf.get("target_schema")
source_schema = spark.conf.get("source_schema")

# 建立 AUTO CDC 的目標資料表
dp.create_streaming_table(f"{target_schema}.dim_users")

# 應用 AUTO CDC (SCD Type 2)
dp.create_auto_cdc_flow(
    target=f"{target_schema}.dim_users",
    source=f"{source_schema}.users_clean",
    keys=["user_id"],
    sequence_by="updated_timestamp",
    stored_as_scd_type=2  # 整數代表 Type 2
)
```

**結果資料表將包含**:
- 來源的所有原始欄位
- `__START_AT` - 此版本生效時間
- `__END_AT` - 此版本過期時間 (目前版本為 NULL)

### 步驟 3: 應用 AUTO CDC (SCD Type 1)

建立具備就地更新的去重資料表 (無歷史)：

```python
# AUTO CDC 搭配 SCD Type 1 (in-place updates)
from pyspark import pipelines as dp

target_schema = spark.conf.get("target_schema")
source_schema = spark.conf.get("source_schema")

# 建立 AUTO CDC 的目標資料表
dp.create_streaming_table(f"{target_schema}.orders_current")

# 應用 AUTO CDC (SCD Type 1)
dp.create_auto_cdc_flow(
    target=f"{target_schema}.orders_current",
    source=f"{source_schema}.orders_clean",
    keys=["order_id"],
    sequence_by="updated_timestamp",
    stored_as_scd_type="1"  # 字串代表 Type 1
)
```

---

## 主要優點

- 基於 Keys 的 **自動去重** - 無需手動 MERGE 邏輯
- 透過時間 Metadata (`__START_AT`, `__END_AT`) 進行 **自動變更追蹤**
- 使用 `sequence_by` 時間戳記正確 **處理晚到資料**
- **簡化管線程式碼** - 無需複雜的 merge/upsert 邏輯
- **內建冪等性 (Idempotency)** - 可安全地重新處理資料

---

## 常見模式

### 模式 1: Gold 維度模型

在 Gold 層為星狀綱要維度使用 AUTO CDC：

```python
# Silver: 清理後的串流資料表
@dp.table(name="silver.customers_clean")
def customers_clean():
    return spark.readStream.table("bronze.customers").filter(...)

# Gold: SCD Type 2 維度
dp.create_streaming_table("gold.dim_customers")
dp.create_auto_cdc_flow(
    target="gold.dim_customers",
    source="silver.customers_clean",
    keys=["customer_id"],
    sequence_by="updated_at",
    stored_as_scd_type=2
)

# Gold: Fact 資料表 (無 AUTO CDC)
@dp.table(name="gold.fact_orders")
def fact_orders():
    return spark.read.table("silver.orders_clean")
```

### 模式 2: 用於 Joins 的 Silver 去重

在 Silver 層 Join 多個資料表時使用 AUTO CDC：

```python
# Silver: 用於去重的 AUTO CDC
dp.create_streaming_table("silver.products_dedupe")
dp.create_auto_cdc_flow(
    target="silver.products_dedupe",
    source="bronze.products",
    keys=["product_id"],
    sequence_by="modified_at",
    stored_as_scd_type="1"  # Type 1: 僅去重，無歷史
)

# Silver: 與去重後的資料 Join
@dp.table(name="silver.orders_enriched")
def orders_enriched():
    orders = spark.readStream.table("bronze.orders")
    products = spark.read.table("silver.products_dedupe")
    return orders.join(products, "product_id")
```

### 模式 3: 混合 SCD 類型

不同資料表根據需求使用不同 SCD 類型：

```python
# SCD Type 2: 需要歷史
dp.create_auto_cdc_flow(
    target="gold.dim_customers",
    source="silver.customers",
    keys=["customer_id"],
    sequence_by="updated_at",
    stored_as_scd_type=2  # 追蹤地址隨時間的變更
)

# SCD Type 1: 僅修正
dp.create_auto_cdc_flow(
    target="gold.dim_products",
    source="silver.products",
    keys=["product_id"],
    sequence_by="modified_at",
    stored_as_scd_type="1"  # 僅當前產品資訊
)
```

---

## 選擇性歷史追蹤

僅追蹤特定欄位的歷史 (SCD Type 2)：

```python
dp.create_auto_cdc_flow(
    target="gold.dim_products",
    source="silver.products_clean",
    keys=["product_id"],
    sequence_by="modified_at",
    stored_as_scd_type=2,
    track_history_column_list=["price", "cost"]  # 僅追蹤這些欄位
)
```

當 `price` 或 `cost` 變更時，會建立新版本。其他欄位變更會更新當前記錄而不建立新版本。

---

## 搭配 AUTO CDC 使用暫存視圖 (Temporary Views)

**`@dp.temporary_view()`** 建立管線內的暫存視圖，僅在管線執行期間存在。這對於 AUTO CDC 之前的中介轉換很有用。

**關鍵限制:**
- 無法指定 `catalog` 或 `schema` (暫存視圖僅限管線範疇)
- 無法使用 `cluster_by` (不持久化)
- 僅在管線執行期間存在

**使用案例:**
- AUTO CDC 之前的複雜轉換
- 被多次引用的中介邏輯
- 避免冗餘的轉換

**範例: AUTO CDC 之前的準備**

```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F

# 步驟 1: 用於複雜業務邏輯的暫存視圖
@dp.temporary_view()
def orders_with_calculated_fields():
    """
    用於複雜計算的暫存視圖。
    無需 catalog/schema - 僅存在於管線中。
    """
    return (
        spark.readStream.table("bronze.orders")
        .withColumn("order_total", F.col("quantity") * F.col("unit_price"))
        .withColumn("discount_amount", F.col("order_total") * F.col("discount_rate"))
        .withColumn("final_amount", F.col("order_total") - F.col("discount_amount"))
        .withColumn("order_category",
            F.when(F.col("final_amount") > 1000, "large")
             .when(F.col("final_amount") > 100, "medium")
             .otherwise("small")
        )
        .filter(F.col("order_id").isNotNull())
        .filter(F.col("final_amount") > 0)
        .filter(F.col("order_date").isNotNull())
    )

# 步驟 2: 使用暫存視圖作為來源應用 AUTO CDC
target_schema = spark.conf.get("target_schema")

dp.create_streaming_table(f"{target_schema}.orders_current")
dp.create_auto_cdc_flow(
    target=f"{target_schema}.orders_current",
    source="orders_with_calculated_fields",  # 依名稱引用暫存視圖
    keys=["order_id"],
    sequence_by="order_date",
    stored_as_scd_type="1"
)
```

**好處:**
- 避免建立不必要的持久化資料表
- 降低儲存成本 (不寫入磁碟)
- 簡化複雜的多步驟轉換
- 在同一管線的多個資料表中重用程式碼

---

## 相關文件

- **[3-scd-query-patterns.md](3-scd-query-patterns.md)** - 查詢 SCD Type 2 歷史資料表、時間點分析、時序 Join
- **[1-ingestion-patterns.md](1-ingestion-patterns.md)** - CDC 資料來源 (Kafka, Event Hubs, Kinesis)
- **[2-streaming-patterns.md](2-streaming-patterns.md)** - 不使用 AUTO CDC 的去重模式

---

## 最佳實踐

1. **選擇正確的 SCD 類型**:
   - 需要查詢歷史狀態時使用 Type 2
   - 僅需要當前狀態或去重時使用 Type 1

2. **使用有意義的 sequence_by 欄位**:
   - 應反映變更的真實時間順序
   - 通常為 `updated_timestamp`, `modified_at`, 或 `event_timestamp`

3. **在 AUTO CDC 之前清理資料**:
   - 先應用型別轉換、驗證與過濾
   - AUTO CDC 在清理過、型別良好的資料上運作最佳

4. **考慮查詢模式**:
   - 若分析師查詢歷史 → 使用 Type 2
   - 若分析師僅需當前資料 → 使用 Type 1
   - 若頻繁 Join → 考慮 Silver 去重

5. **對大資料表使用選擇性追蹤**:
   - 僅追蹤有意義變更的欄位歷史
   - 減少儲存空間並改善查詢效能

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **副本仍然出現** | 檢查 `keys` 包含所有業務鍵欄位；驗證 `sequence_by` 有正確的排序 |
| **缺少 `__START_AT`/`__END_AT` 欄位** | 這些僅出現在 SCD Type 2 (整數)，而非 Type 1 (字串) |
| **未處理晚到資料** | 確保已設定 `sequence_by` 欄位並反映真實事件時間 |
| **Type 語法錯誤** | Type 2 使用整數 `2`，Type 1 使用字串 `"1"` |
| **效能問題** | 使用 `track_history_column_list` 限制觸發新版本的欄位 |
