# DLT 到 SDP 遷移指南 (DLT to SDP Migration Guide)

將 Delta Live Tables (DLT) Python 管線遷移至 Spark Declarative Pipelines (SDP) SQL 的指南。

⚠️ **對於新的 Python SDP 管線**: 請使用現代化 `pyspark.pipelines` API。參見 [5-python-api.md](5-python-api.md)。

---

## 遷移決策矩陣

| 特性/模式 | DLT Python | SDP SQL | 建議 |
|-----------------|------------|---------|----------------|
| 簡單轉換 | ✓ | ✓ | **遷移至 SQL** |
| 聚合 (Aggregations) | ✓ | ✓ | **遷移至 SQL** |
| 過濾, WHERE 子句 | ✓ | ✓ | **遷移至 SQL** |
| CASE 表達式 | ✓ | ✓ | **遷移至 SQL** |
| SCD Type 1/2 | ✓ | ✓ | **遷移至 SQL** (AUTO CDC) |
| 簡單 Joins | ✓ | ✓ | **遷移至 SQL** |
| Auto Loader | ✓ | ✓ | **遷移至 SQL** (read_files) |
| 串流來源 (Kafka) | ✓ | ✓ | **遷移至 SQL** (read_stream) |
| 複雜 Python UDFs | ✓ | ❌ | **保留在 Python** |
| 外部 API 呼叫 | ✓ | ❌ | **保留在 Python** |
| 自訂函式庫 | ✓ | ❌ | **保留在 Python** |
| 複雜 Apply 函數 | ✓ | ❌ | **保留在 Python** 或簡化 |
| ML 模型推論 | ✓ | ❌ | **保留在 Python** |

**規則**: 若 80% 以上可用 SQL 表達，則遷移至 SDP SQL。若有大量 Python 邏輯，則保留 DLT Python 或使用混合模式。

---

## 對照：關鍵模式

### 基本串流資料表

**DLT Python**:
```python
@dlt.table(name="bronze_sales", comment="Raw sales")
def bronze_sales():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .load("/mnt/raw/sales")
        .withColumn("_ingested_at", F.current_timestamp())
    )
```

**SDP SQL**:
```sql
CREATE OR REPLACE STREAMING TABLE bronze_sales
COMMENT 'Raw sales'
AS
SELECT *, current_timestamp() AS _ingested_at
FROM read_files('/mnt/raw/sales', format => 'json');
```

### 過濾與轉換

**DLT Python**:
```python
@dlt.table(name="silver_sales")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_drop("valid_sale_id", "sale_id IS NOT NULL")
def silver_sales():
    return (
        dlt.read_stream("bronze_sales")
        .withColumn("sale_date", F.to_date("sale_date"))
        .withColumn("amount", F.col("amount").cast("decimal(10,2)"))
        .select("sale_id", "customer_id", "amount", "sale_date")
    )
```

**SDP SQL**:
```sql
CREATE OR REPLACE STREAMING TABLE silver_sales AS
SELECT
  sale_id, customer_id,
  CAST(amount AS DECIMAL(10,2)) AS amount,
  CAST(sale_date AS DATE) AS sale_date
FROM STREAM bronze_sales
WHERE amount > 0 AND sale_id IS NOT NULL;
```

### SCD Type 2

**DLT Python**:
```python
dlt.create_streaming_table("customers_history")

dlt.apply_changes(
    target="customers_history",
    source="customers_cdc_clean",
    keys=["customer_id"],
    sequence_by="event_timestamp",
    stored_as_scd_type="2",
    track_history_column_list=["*"]
)
```

**SDP SQL** (子句順序：APPLY AS DELETE WHEN 在 SEQUENCE BY 之前；僅列出 EXCEPT 中來源存在的欄位；若 TRACK HISTORY ON * 導致解析錯誤則省略):
```sql
CREATE OR REFRESH STREAMING TABLE customers_history;

CREATE FLOW customers_scd2_flow AS
AUTO CDC INTO customers_history
FROM stream(customers_cdc_clean)
KEYS (customer_id)
APPLY AS DELETE WHEN operation = "DELETE"
SEQUENCE BY event_timestamp
COLUMNS * EXCEPT (operation, _ingested_at, _source_file)
STORED AS SCD TYPE 2;
```

### Joins

**DLT Python**:
```python
@dlt.table(name="silver_sales_enriched")
def silver_sales_enriched():
    sales = dlt.read_stream("silver_sales")
    products = dlt.read("dim_products")

    return (
        sales.join(products, "product_id", "left")
        .select(sales["*"], products["product_name"], products["category"])
    )
```

**SDP SQL**:
```sql
CREATE OR REPLACE STREAMING TABLE silver_sales_enriched AS
SELECT
  s.*,
  p.product_name,
  p.category
FROM STREAM silver_sales s
LEFT JOIN dim_products p ON s.product_id = p.product_id;
```

---

## 處理 Expectations

**DLT Python**:
```python
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_fail("critical_id", "id IS NOT NULL")
```

**SDP SQL - 基本**:
```sql
-- 使用 WHERE (等同於 expect_or_drop)
WHERE amount > 0 AND id IS NOT NULL
```

**SDP SQL - 隔離區模式 (Quarantine Pattern)** (用於稽核):
```sql
-- 標記無效記錄
CREATE OR REPLACE STREAMING TABLE bronze_data_flagged AS
SELECT
  *,
  CASE
    WHEN amount <= 0 THEN TRUE
    WHEN id IS NULL THEN TRUE
    ELSE FALSE
  END AS is_invalid
FROM STREAM bronze_data;

-- 清理供下游使用
CREATE OR REPLACE STREAMING TABLE silver_data_clean AS
SELECT * FROM STREAM bronze_data_flagged WHERE NOT is_invalid;

-- 隔離以供調查
CREATE OR REPLACE STREAMING TABLE silver_data_quarantine AS
SELECT * FROM STREAM bronze_data_flagged WHERE is_invalid;
```

**遷移**: `@dlt.expect_or_drop` → WHERE 子句或隔離區模式。

---

## 處理 UDFs

### 簡單 UDFs (遷移至 SQL)

**DLT Python**:
```python
@F.udf(returnType=StringType())
def categorize_amount(amount):
    if amount > 1000:
        return "High"
    elif amount > 100:
        return "Medium"
    else:
        return "Low"

@dlt.table(name="sales_categorized")
def sales_categorized():
    return (
        dlt.read("sales")
        .withColumn("category", categorize_amount(F.col("amount")))
    )
```

**SDP SQL** (CASE 表達式):
```sql
CREATE OR REPLACE MATERIALIZED VIEW sales_categorized AS
SELECT
  *,
  CASE
    WHEN amount > 1000 THEN 'High'
    WHEN amount > 100 THEN 'Medium'
    ELSE 'Low'
  END AS category
FROM sales;
```

### 複雜 UDFs (保留在 Python)

**保留在 Python 的情況**:
- 複雜條件邏輯
- 外部 API 呼叫
- 自訂演算法
- ML 推論

**選項**:
1. 轉換保留在 Python DLT
2. 建立混合模式 (SQL + 針對特定 UDFs 的 Python)
3. 若可能，重構為 SQL 內建函數

---

## 遷移流程

### 步驟 1: 清查 (Inventory)

記錄：
- 資料表/視圖數量
- Python UDFs (簡單 vs 複雜)
- 外部依賴
- Expectations 與品質規則

### 步驟 2: 分類 (Categorize)

**易於遷移**: Filters, aggregations, 簡單 CASE
**中等**: 可重寫為 SQL 的 UDFs
**困難**: 複雜 Python, 外部呼叫, ML

### 步驟 3: 依層級遷移 (Migrate by Layer)

1. **Bronze** (攝取): 將 Auto Loader 轉為 read_files()
2. **Silver** (清理): 將 expectations 轉為 WHERE/隔離區
3. **Gold** (聚合): 通常很直觀
4. **SCD/CDC**: 使用 AUTO CDC

### 步驟 4: 測試 (Test)

- 平行執行兩個管線
- 比較輸出的正確性
- 驗證效能
- 檢查品質指標

---

## 何時 **不** 遷移

**若符合以下情況，請保留 DLT Python**:
1. 大量使用 Python UDF (>30% 邏輯)
2. 需要外部 API 呼叫
3. 自訂 ML 模型推論
4. SQL 中沒有的複雜有狀態操作
5. 現有管線運作良好，團隊偏好 Python
6. SQL 專業知識有限

**考慮混合模式**: 大部分使用 SQL，複雜邏輯使用 Python。

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| UDF 無法轉換 | 保留在 Python 或使用 SQL 內建函數重構 |
| Expectations 不同 | 使用隔離區模式稽核被丟棄的記錄 |
| 效能下降 | 使用 CLUSTER BY 進行 Liquid Clustering，檢視 Joins |
| Schema 演變不同 | 在 read_files() 中使用 `mode => 'PERMISSIVE'` |

---

## 總結

**遷移路徑**:
1. 使用決策矩陣 (80%+ 可用 SQL 表達 → 遷移)
2. 依層級遷移 (bronze → silver → gold)
3. 使用 WHERE/隔離區處理 expectations
4. 將簡單 UDFs 轉換為 CASE 表達式
5. 將複雜 Python 邏輯保留在 Python

**關鍵**: DLT Python 與 SDP SQL 均受完整支援。為了簡化而遷移，而非必要性。
