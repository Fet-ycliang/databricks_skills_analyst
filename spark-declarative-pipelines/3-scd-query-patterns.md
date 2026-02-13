# SCD 查詢模式 (SCD Query Patterns)

如何有效地查詢 SCD Type 2 歷史資料表，包括當前狀態查詢、時間點分析與變更追蹤。

---

## 了解 SCD Type 2 結構

當您建立 SCD Type 2 流程時，系統會自動加入時間欄位：

```sql
CREATE FLOW customers_scd2_flow AS
AUTO CDC INTO customers_history
FROM stream(customers_cdc_clean)
KEYS (customer_id)
SEQUENCE BY event_timestamp
STORED AS SCD TYPE 2
TRACK HISTORY ON *;
```

**產生的資料表結構** (Lakeflow 使用雙底線時間欄位)：
```
customers_history
├── customer_id        -- 業務鍵
├── customer_name
├── email
├── phone
├── __START_AT         -- 此版本生效時間 (自動產生)
├── __END_AT           -- 此版本過期時間 (目前版本為 NULL)
└── ...other columns
```

**重要：** 查詢時請使用 `__START_AT` 與 `__END_AT` (雙底線)，而非 `START_AT`/`END_AT`。

---

## 當前狀態查詢 (Current State Queries)

### 所有當前記錄

```sql
-- __END_AT IS NULL 表示有效記錄 (Lakeflow 使用雙底線)
CREATE OR REPLACE MATERIALIZED VIEW dim_customers_current AS
SELECT
  customer_id, customer_name, email, phone, address,
  __START_AT AS valid_from
FROM customers_history
WHERE __END_AT IS NULL;
```

### 特定客戶

```sql
SELECT *
FROM customers_history
WHERE customer_id = '12345'
  AND __END_AT IS NULL;
```

---

## 時間點查詢 (Point-in-Time Queries)

### 特定日期查詢 (As-Of Date Query)

獲取記錄在特定日期的狀態：

```sql
-- 截至 2024 年 1 月 1 日的產品 (使用 __START_AT / __END_AT)
CREATE OR REPLACE MATERIALIZED VIEW products_as_of_2024_01_01 AS
SELECT
  product_id, product_name, price, category,
  __START_AT, __END_AT
FROM products_history
WHERE __START_AT <= '2024-01-01'
  AND (__END_AT > '2024-01-01' OR __END_AT IS NULL);
```

---

## 變更分析 (Change Analysis)

### 追蹤實體的所有變更

```sql
-- 客戶的完整歷史 (使用 __START_AT / __END_AT)
SELECT
  customer_id, customer_name, email, phone,
  __START_AT, __END_AT,
  COALESCE(
    DATEDIFF(DAY, __START_AT, __END_AT),
    DATEDIFF(DAY, __START_AT, CURRENT_TIMESTAMP())
  ) AS days_active
FROM customers_history
WHERE customer_id = '12345'
ORDER BY __START_AT DESC;
```

### 時間區段內的變更

```sql
-- 在 2024 Q1 期間變更的客戶 (使用 __START_AT)
SELECT
  customer_id, customer_name,
  __START_AT AS change_timestamp,
  'UPDATE' AS change_type
FROM customers_history
WHERE __START_AT BETWEEN '2024-01-01' AND '2024-03-31'
  AND __START_AT != (
    SELECT MIN(__START_AT)
    FROM customers_history ch2
    WHERE ch2.customer_id = customers_history.customer_id
  )
ORDER BY __START_AT;
```

---

## 將 Fact 與歷史 Dimensions 關聯

### 在交易時間豐富 Facts

```sql
-- 將銷售與銷售時間的產品價格關聯
CREATE OR REPLACE MATERIALIZED VIEW sales_with_historical_prices AS
SELECT
  s.sale_id, s.product_id, s.sale_date, s.quantity,
  p.product_name, p.price AS unit_price_at_sale_time,
  s.quantity * p.price AS calculated_amount,
  p.category
FROM sales_fact s
INNER JOIN products_history p
  ON s.product_id = p.product_id
  AND s.sale_date >= p.__START_AT
  AND (s.sale_date < p.__END_AT OR p.__END_AT IS NULL);
```

### 與當前 Dimension 關聯

```sql
-- 將銷售與當前產品資訊關聯
CREATE OR REPLACE MATERIALIZED VIEW sales_with_current_prices AS
SELECT
  s.sale_id, s.product_id, s.sale_date, s.quantity,
  s.amount AS amount_at_sale,
  p.product_name AS current_product_name,
  p.price AS current_price,
  p.category AS current_category
FROM sales_fact s
INNER JOIN products_history p
  ON s.product_id = p.product_id
  AND p.__END_AT IS NULL;  -- 僅限目前版本
```

---

## 選擇性歷史追蹤

當使用 `TRACK HISTORY ON specific_columns` 時：

```sql
-- 僅價格變更觸發新版本
CREATE FLOW products_scd2_flow AS
AUTO CDC INTO products_history
FROM stream(products_cdc_clean)
KEYS (product_id)
SEQUENCE BY event_timestamp
STORED AS SCD TYPE 2
TRACK HISTORY ON price, cost;  -- 僅這些欄位
```

---

## 優化模式

### 預過濾物化視圖 (Pre-Filter Materialized Views)

```sql
-- 當前狀態視圖 (最常見模式)
CREATE OR REPLACE MATERIALIZED VIEW dim_products_current AS
SELECT * FROM products_history WHERE __END_AT IS NULL;

-- 僅最近變更
CREATE OR REPLACE MATERIALIZED VIEW dim_recent_changes AS
SELECT * FROM products_history
WHERE __START_AT >= CURRENT_DATE() - INTERVAL 90 DAYS;

-- 變更頻率統計
CREATE OR REPLACE MATERIALIZED VIEW product_change_stats AS
SELECT
  product_id,
  COUNT(*) AS version_count,
  MIN(__START_AT) AS first_seen,
  MAX(__START_AT) AS last_updated
FROM products_history
GROUP BY product_id;
```

---

## 最佳實踐

### 1. 始終依 `__END_AT` 過濾當前記錄 (Lakeflow 使用雙底線)

```sql
-- ✅ 高效
WHERE __END_AT IS NULL

-- ❌ 較低效
WHERE __START_AT = (SELECT MAX(__START_AT) FROM table WHERE ...)
```

### 2. 使用含下界、不含上界 (Inclusive Lower, Exclusive Upper)

```sql
-- ✅ 標準模式
WHERE __START_AT <= '2024-01-01'
  AND (__END_AT > '2024-01-01' OR __END_AT IS NULL)
```

### 3. 為常見模式建立 MV

```sql
-- 當前狀態
CREATE OR REPLACE MATERIALIZED VIEW dim_current AS
SELECT * FROM history WHERE __END_AT IS NULL;

-- 最近變更
CREATE OR REPLACE MATERIALIZED VIEW dim_recent_changes AS
SELECT * FROM history
WHERE __START_AT >= CURRENT_DATE() - INTERVAL 90 DAYS;
```

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| 相同 Key 有多個資料列 | 缺少 `__END_AT IS NULL` 過濾條件以取得當前狀態 |
| 時間點查詢無結果 | 使用 `__START_AT <= date AND (__END_AT > date OR __END_AT IS NULL)` |
| 時序 Join 緩慢 | 為特定時間區段建立物化視圖 |
| 意外的重複資料 | 同一天多次變更 - 使用高精度的 SEQUENCE BY |
