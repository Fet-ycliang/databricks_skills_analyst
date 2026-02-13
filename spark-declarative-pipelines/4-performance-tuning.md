# SDP 的效能調校 (Performance Tuning)

效能優化策略，包括 **Liquid Clustering** (現代化方法)、物化視圖重新整理、狀態管理與運算設定。

---

## Liquid Clustering (推薦)

**Liquid Clustering** 是資料佈局優化的推薦方法。它取代了手動的 `PARTITION BY` 與 `Z-ORDER`。

### 什麼是 Liquid Clustering?

- **自適應 (Adaptive)**: 適應資料分佈的變化
- **多維度 (Multi-dimensional)**: 同時在多個欄位上進行叢集
- **自動檔案大小調整**: 維持最佳檔案大小
- **自我優化**: 減少手動 OPTIMIZE 指令

### 基本語法

**SQL**:
```sql
CREATE OR REPLACE STREAMING TABLE bronze_events
CLUSTER BY (event_type, event_date)
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  CAST(current_date() AS DATE) AS event_date
FROM read_files('/mnt/raw/events/', format => 'json');
```

**Python**:
```python
from pyspark import pipelines as dp

@dp.table(cluster_by=["event_type", "event_date"])
def bronze_events():
    return spark.readStream.format("cloudFiles").load("/data")
```

### 自動叢集鍵選擇

```sql
-- 讓 Databricks 根據查詢模式選擇
CREATE OR REPLACE STREAMING TABLE bronze_events
CLUSTER BY (AUTO)
AS SELECT ...;
```

**何時使用 AUTO**: 學習階段、未知的存取模式、原型製作
**何時手動定義**: 熟知的查詢模式、生產工作負載

---

## 依層級選擇叢集鍵 (Cluster Key Selection)

### Bronze 層

依事件類型 + 日期叢集：

```sql
CREATE OR REPLACE STREAMING TABLE bronze_events
CLUSTER BY (event_type, ingestion_date)
TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  CAST(current_date() AS DATE) AS ingestion_date
FROM read_files('/mnt/raw/events/', format => 'json');
```

**原因**: Bronze 通常依事件類型過濾以進行處理，並依日期進行增量載入。

### Silver 層

依主鍵 + 業務維度叢集：

```sql
CREATE OR REPLACE STREAMING TABLE silver_orders
CLUSTER BY (customer_id, order_date)
AS
SELECT
  order_id, customer_id, product_id, amount,
  CAST(order_timestamp AS DATE) AS order_date,
  order_timestamp
FROM STREAM bronze_orders;
```

**原因**: 實體查找 (依 ID) 與時間範圍查詢 (依日期)。

### Gold 層

依聚合維度叢集：

```sql
CREATE OR REPLACE MATERIALIZED VIEW gold_sales_summary
CLUSTER BY (product_category, year_month)
AS
SELECT
  product_category,
  DATE_FORMAT(order_date, 'yyyy-MM') AS year_month,
  SUM(amount) AS total_sales,
  COUNT(*) AS transaction_count,
  AVG(amount) AS avg_order_value
FROM silver_orders
GROUP BY product_category, DATE_FORMAT(order_date, 'yyyy-MM');
```

**原因**: 儀表板過濾器 (類別、區域、時間區段)。

### 選擇指南

| 層級 | 好的鍵值 | 理由 |
|-------|-----------|-----------|
| **Bronze** | event_type, ingestion_date | 依類型過濾；日期用於增量 |
| **Silver** | primary_key, business_date | 實體查找 + 時間範圍 |
| **Gold** | aggregation_dimensions | 儀表板過濾器 |

**最佳實踐**:
- 第一個鍵: 最具選擇性的過濾器 (例如 customer_id)
- 第二個鍵: 次要常見過濾器 (例如 date)
- 順序很重要: 最具選擇性的在先
- 限制為 4 個鍵: 超過 4 個邊際效益遞減
- **若不確定則使用 AUTO**

---

## 從舊版 PARTITION BY 遷移

### 之前 (舊版 Legacy)

```sql
CREATE OR REPLACE STREAMING TABLE events
PARTITIONED BY (date DATE)
TBLPROPERTIES ('pipelines.autoOptimize.zOrderCols' = 'user_id,event_type')
AS SELECT ...;
```

**問題**: 固定鍵值、小檔案問題、分佈傾斜、需要手動 OPTIMIZE。

### 之後 (現代化搭配 Liquid Clustering)

```sql
CREATE OR REPLACE STREAMING TABLE events
CLUSTER BY (date, user_id, event_type)
AS SELECT ...;
```

**好處**: 自適應、無小檔案、自動優化、20-50% 效能提升。

### 何時仍使用 PARTITION BY

**僅用於**:
1. **法規** 需求 (實體分離)
2. **資料生命週期**: 需要 `DROP` 分區以進行保留
3. **相容性**: 較舊的 Delta Lake 版本 (< DBR 13.3)
4. **現有大資料表**: 遷移成本大於效益

**否則，優先使用 Liquid Clustering。**

---

## 資料表屬性 (Table Properties)

### 自動優化 (Auto-Optimize)

```sql
CREATE OR REPLACE STREAMING TABLE bronze_events
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
AS SELECT * FROM read_files(...);
```

**好處**: 減少小檔案、改善讀取、自動壓實。

### Change Data Feed

```sql
CREATE OR REPLACE STREAMING TABLE silver_customers
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
AS SELECT * FROM STREAM bronze_customers;
```

**使用時機**: 下游系統需要高效的變更追蹤。

### 保留期間 (Retention Periods)

```sql
CREATE OR REPLACE STREAMING TABLE bronze_high_volume
TBLPROPERTIES (
  'delta.logRetentionDuration' = '7 days',
  'delta.deletedFileRetentionDuration' = '7 days'
)
AS SELECT * FROM read_files(...);
```

**適用於**: 高容量資料表以降低儲存成本。

---

## 物化視圖重新整理 (Materialized View Refresh)

### 重新整理頻率

```sql
-- 近即時 (頻繁)
CREATE OR REPLACE MATERIALIZED VIEW gold_live_metrics
REFRESH EVERY 5 MINUTES
AS
SELECT
  metric_name,
  AVG(metric_value) AS avg_value,
  MAX(last_updated) AS freshness
FROM silver_metrics
GROUP BY metric_name;

-- 每日報表 (排程)
CREATE OR REPLACE MATERIALIZED VIEW gold_daily_summary
REFRESH EVERY 1 DAY
AS
SELECT report_date, SUM(amount) AS total_amount
FROM silver_sales
GROUP BY report_date;
```

### 增量重新整理 (自動)

物化視圖在可能時會自動使用增量重新整理：

```sql
-- 若來源有 Row Tracking 則增量重新整理
CREATE OR REPLACE MATERIALIZED VIEW gold_aggregates AS
SELECT
  product_id,
  SUM(quantity) AS total_quantity,
  SUM(amount) AS total_amount
FROM silver_sales
GROUP BY product_id;
```

**需求**: 來源有 Delta Row Tracking、無資料列過濾、支援的聚合函數。

### 預聚合 (Pre-Aggregation)

```sql
-- 取代重複查詢大資料表
CREATE OR REPLACE MATERIALIZED VIEW orders_monthly AS
SELECT
  customer_id,
  YEAR(order_date) AS year,
  MONTH(order_date) AS month,
  SUM(amount) AS total
FROM large_orders_table
GROUP BY customer_id, YEAR(order_date), MONTH(order_date);

-- 查詢 MV (快速)
SELECT * FROM orders_monthly WHERE year = 2024;
```

---

## 串流的狀態管理

### 了解狀態增長

```sql
-- 高狀態: 每個唯一組合都會建立狀態
SELECT
  user_id,       -- 1M users
  product_id,    -- 10K products
  session_id,    -- 100M sessions
  COUNT(*) AS events
FROM STREAM bronze_events
GROUP BY user_id, product_id, session_id;  -- 巨大狀態!
```

### 減少狀態大小

**策略 1: 降低基數 (Cardinality)**

```sql
-- 在較高層級聚合
SELECT
  user_id,
  product_category,  -- 100 categories (非 10K products)
  DATE(event_time) AS event_date,
  COUNT(*) AS events
FROM STREAM bronze_events
GROUP BY user_id, product_category, DATE(event_time);
```

**策略 2: 使用時間視窗**

```sql
-- 透過視窗限制狀態
SELECT
  user_id,
  window(event_time, '1 hour') AS time_window,
  COUNT(*) AS events
FROM STREAM bronze_events
GROUP BY user_id, window(event_time, '1 hour');
```

**策略 3: 物化中介結果**

```sql
-- 串流聚合 (維護狀態)
CREATE OR REPLACE STREAMING TABLE user_daily_stats AS
SELECT
  user_id,
  DATE(event_time) AS event_date,
  COUNT(*) AS event_count
FROM STREAM bronze_events
GROUP BY user_id, DATE(event_time);

-- 批次聚合 (無串流狀態)
CREATE OR REPLACE MATERIALIZED VIEW user_monthly_stats AS
SELECT
  user_id,
  DATE_TRUNC('month', event_date) AS month,
  SUM(event_count) AS total_events
FROM user_daily_stats
GROUP BY user_id, DATE_TRUNC('month', event_date);
```

---

## Join 優化

### 串流對靜態 (高效)

```sql
-- 小靜態維度，大串流 Fact
CREATE OR REPLACE STREAMING TABLE sales_enriched AS
SELECT
  s.sale_id, s.product_id, s.amount,
  p.product_name, p.category  -- 來自小靜態資料表
FROM STREAM bronze_sales s
LEFT JOIN dim_products p ON s.product_id = p.product_id;
```

**最佳實踐**: 保持靜態維度小 (<10K rows) 以進行廣播。

### 串流對串流 (有狀態)

```sql
-- 時間邊界限制狀態保留
CREATE OR REPLACE STREAMING TABLE orders_with_payments AS
SELECT
  o.order_id, o.amount AS order_amount,
  p.payment_id, p.amount AS payment_amount
FROM STREAM bronze_orders o
INNER JOIN STREAM bronze_payments p
  ON o.order_id = p.order_id
  AND p.payment_time BETWEEN o.order_time AND o.order_time + INTERVAL 1 HOUR;
```

**優化**: 在 Join 條件中使用時間邊界。

---

## 運算設定

### Serverless vs Classic

| 面向 | Serverless | Classic |
|--------|-----------|---------|
| 啟動 | 快速 (秒級) | 較慢 (分鐘級) |
| 擴展 | 自動，即時 | 手動/自動縮放 |
| 成本 | 依使用量付費 | 依叢集時間付費 |
| 最適合 | 變動工作負載，Dev/Test | 穩定工作負載 |

### Serverless (推薦)

在管線層級啟用：

```yaml
execution_mode: continuous  # 或 triggered
serverless: true
```

**優點**: 無需叢集管理，即時擴展，突發工作負載成本較低。

---

## 查詢優化

### 提早過濾

```sql
-- ✅ 在來源過濾
CREATE OR REPLACE STREAMING TABLE silver_recent AS
SELECT *
FROM STREAM bronze_events
WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS;

-- ❌ 延遲過濾
CREATE OR REPLACE STREAMING TABLE silver_all AS
SELECT * FROM STREAM bronze_events;

CREATE OR REPLACE MATERIALIZED VIEW gold_recent AS
SELECT * FROM silver_all
WHERE event_date >= CURRENT_DATE() - INTERVAL 7 DAYS;
```

### 選擇特定欄位

```sql
-- ❌ 讀取所有欄位
SELECT * FROM large_table;

-- ✅ 僅所需欄位
SELECT customer_id, order_date, amount FROM large_table;
```

### 使用 GROUP BY 取代 DISTINCT

```sql
-- ❌ 在高基數上昂貴
SELECT DISTINCT transaction_id FROM huge_table;

-- ✅ 較佳
SELECT transaction_id, COUNT(*) FROM huge_table GROUP BY transaction_id;
```

---

## 監控

追蹤關鍵指標：

```sql
-- 資料新鮮度
SELECT
  table_name,
  MAX(event_timestamp) AS latest_event,
  CURRENT_TIMESTAMP() AS now,
  TIMESTAMPDIFF(MINUTE, MAX(event_timestamp), CURRENT_TIMESTAMP()) AS lag_minutes
FROM pipeline_monitoring.table_metrics
GROUP BY table_name;
```

**檢查**:
1. 緩慢的串流資料表 (高處理延遲 / Processing Lag)
2. 大型狀態操作 (高記憶體)
3. 昂貴的 Joins (長處理時間)
4. 小檔案 (Delta 中有許多小檔案)

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| 管線執行緩慢 | 檢查分區、狀態大小、Join 模式 |
| 高記憶體使用量 | 無限狀態 - 加入時間視窗，降低基數 |
| 許多小檔案 | 啟用自動優化，執行 OPTIMIZE 指令 |
| 大資料表上的昂貴查詢 | 加入 Clustering，建立過濾後的 MV |
| MV 重新整理緩慢 | 在來源啟用 Row Tracking，驗證增量重新整理 |
