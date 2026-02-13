# SDP 的串流模式 (Streaming Patterns)

特定於串流的模式，包括去重 (Deduplication)、視窗聚合 (Windowed Aggregations)、晚到資料處理 (Late-arriving Data) 以及有狀態操作 (Stateful Operations)。

---

## 去重模式 (Deduplication Patterns)

### 依鍵 (By Key)

```sql
-- Bronze: 攝取所有 (可能包含重複)
CREATE OR REPLACE STREAMING TABLE bronze_events AS
SELECT *, current_timestamp() AS _ingested_at
FROM read_stream(...);

-- Silver: 依 event_id 去重
CREATE OR REPLACE STREAMING TABLE silver_events_dedup AS
SELECT
  event_id, user_id, event_type, event_timestamp, _ingested_at
FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_timestamp) AS rn
  FROM STREAM bronze_events
)
WHERE rn = 1;
```

### 搭配時間視窗

在時間視窗內去重以處理晚到資料：

```sql
CREATE OR REPLACE STREAMING TABLE silver_events_dedup AS
SELECT
  event_id, user_id, event_type, event_timestamp,
  MIN(_ingested_at) AS first_seen_at
FROM STREAM bronze_events
GROUP BY
  event_id, user_id, event_type, event_timestamp,
  window(event_timestamp, '1 hour')  -- 在 1 小時視窗內去重
HAVING COUNT(*) >= 1;
```

### 複合鍵 (Composite Key)

```sql
CREATE OR REPLACE STREAMING TABLE silver_transactions_dedup AS
SELECT
  transaction_id, customer_id, amount, transaction_timestamp,
  MIN(_ingested_at) AS _ingested_at
FROM STREAM bronze_transactions
GROUP BY transaction_id, customer_id, amount, transaction_timestamp;
```

---

## 視窗聚合 (Windowed Aggregations)

### 滾動視窗 (Tumbling Windows)

```sql
-- 5 分鐘不重疊視窗
CREATE OR REPLACE STREAMING TABLE silver_sensor_5min AS
SELECT
  sensor_id,
  window(event_timestamp, '5 minutes') AS time_window,
  AVG(temperature) AS avg_temperature,
  MIN(temperature) AS min_temperature,
  MAX(temperature) AS max_temperature,
  COUNT(*) AS event_count
FROM STREAM bronze_sensor_events
GROUP BY sensor_id, window(event_timestamp, '5 minutes');
```

### 多種視窗大小

```sql
-- 1 分鐘用於即時監控
CREATE OR REPLACE STREAMING TABLE gold_sensor_1min AS
SELECT
  sensor_id,
  window(event_timestamp, '1 minute').start AS window_start,
  window(event_timestamp, '1 minute').end AS window_end,
  AVG(value) AS avg_value,
  COUNT(*) AS event_count
FROM STREAM silver_sensor_data
GROUP BY sensor_id, window(event_timestamp, '1 minute');

-- 1 小時用於趨勢分析
CREATE OR REPLACE STREAMING TABLE gold_sensor_1hour AS
SELECT
  sensor_id,
  window(event_timestamp, '1 hour').start AS window_start,
  AVG(value) AS avg_value,
  STDDEV(value) AS stddev_value
FROM STREAM silver_sensor_data
GROUP BY sensor_id, window(event_timestamp, '1 hour');
```

---

## 晚到資料 (Late-Arriving Data)

### 事件時間 vs 處理時間

業務邏輯務必使用事件時間戳記，而非攝取時間戳記：

```sql
-- ✅ 使用事件時間
CREATE OR REPLACE STREAMING TABLE silver_orders AS
SELECT
  order_id, order_timestamp,  -- 來自來源的事件時間
  customer_id, amount,
  _ingested_at                -- 處理時間 (僅供除錯)
FROM STREAM bronze_orders;

-- 依事件時間分組
CREATE OR REPLACE STREAMING TABLE gold_daily_orders AS
SELECT
  CAST(order_timestamp AS DATE) AS order_date,  -- 事件時間
  COUNT(*) AS order_count,
  SUM(amount) AS total_amount
FROM STREAM silver_orders
GROUP BY CAST(order_timestamp AS DATE);
```

### 使用 SCD2 處理亂序資料

使用 `SEQUENCE BY` 搭配事件時間戳記。**子句順序很重要**: 將 `APPLY AS DELETE WHEN` 放在 `SEQUENCE BY` 之前。在 `COLUMNS * EXCEPT (...)` 中僅列出來源中實際存在的欄位 (除非 Bronze 資料表使用 Rescue Data，否則省略 `_rescued_data`)。若 `TRACK HISTORY ON *` 導致解析錯誤則省略；預設即為相同效果。

```sql
CREATE OR REFRESH STREAMING TABLE silver_customers_history;

CREATE FLOW customers_scd2_flow AS
AUTO CDC INTO silver_customers_history
FROM stream(bronze_customer_cdc)
KEYS (customer_id)
APPLY AS DELETE WHEN operation = "DELETE"
SEQUENCE BY event_timestamp  -- 處理亂序
COLUMNS * EXCEPT (operation, _ingested_at, _source_file)
STORED AS SCD TYPE 2;
```

---

## 有狀態操作 (Stateful Operations)

### 串流對串流 Joins

```sql
-- Join 兩個串流來源
CREATE OR REPLACE STREAMING TABLE silver_orders_with_payments AS
SELECT
  o.order_id, o.customer_id, o.order_timestamp, o.amount AS order_amount,
  p.payment_id, p.payment_timestamp, p.payment_method, p.amount AS payment_amount
FROM STREAM bronze_orders o
INNER JOIN STREAM bronze_payments p
  ON o.order_id = p.order_id
  AND p.payment_timestamp BETWEEN o.order_timestamp AND o.order_timestamp + INTERVAL 1 HOUR;
```

### 串流對靜態 Joins

使用維度資料表豐富串流資料：

```sql
-- 靜態維度 (變更頻率低)
CREATE OR REPLACE TABLE dim_products AS
SELECT * FROM catalog.schema.products;

-- 串流對靜態 Join
CREATE OR REPLACE STREAMING TABLE silver_sales_enriched AS
SELECT
  s.sale_id, s.product_id, s.quantity, s.sale_timestamp,
  p.product_name, p.category, p.price,
  s.quantity * p.price AS total_amount
FROM STREAM bronze_sales s
LEFT JOIN dim_products p ON s.product_id = p.product_id;
```

### 增量聚合

```sql
-- 依客戶的累計總額 (有狀態)
CREATE OR REPLACE STREAMING TABLE silver_customer_running_totals AS
SELECT
  customer_id,
  SUM(amount) AS total_spent,
  COUNT(*) AS transaction_count,
  MAX(transaction_timestamp) AS last_transaction_at
FROM STREAM bronze_transactions
GROUP BY customer_id;
```

---

## 工作階段視窗 (Session Windows)

根據閒置間隔將事件分組為工作階段 (Sessions)：

```sql
-- 30 分鐘閒置逾時
CREATE OR REPLACE STREAMING TABLE silver_user_sessions AS
SELECT
  user_id,
  session_window(event_timestamp, '30 minutes') AS session,
  MIN(event_timestamp) AS session_start,
  MAX(event_timestamp) AS session_end,
  COUNT(*) AS event_count,
  COLLECT_LIST(event_type) AS event_sequence
FROM STREAM bronze_user_events
GROUP BY user_id, session_window(event_timestamp, '30 minutes');
```

---

## 異常偵測 (Anomaly Detection)

### 即時離群值偵測

```sql
CREATE OR REPLACE STREAMING TABLE silver_sensor_with_anomalies AS
SELECT
  sensor_id, event_timestamp, temperature,
  AVG(temperature) OVER (
    PARTITION BY sensor_id ORDER BY event_timestamp
    ROWS BETWEEN 100 PRECEDING AND CURRENT ROW
  ) AS rolling_avg_100,
  STDDEV(temperature) OVER (
    PARTITION BY sensor_id ORDER BY event_timestamp
    ROWS BETWEEN 100 PRECEDING AND CURRENT ROW
  ) AS rolling_stddev_100,
  CASE
    WHEN temperature > rolling_avg_100 + (3 * rolling_stddev_100) THEN 'HIGH_OUTLIER'
    WHEN temperature < rolling_avg_100 - (3 * rolling_stddev_100) THEN 'LOW_OUTLIER'
    ELSE 'NORMAL'
  END AS anomaly_flag
FROM STREAM bronze_sensor_events;

-- 路由異常以進行警報
CREATE OR REPLACE STREAMING TABLE silver_sensor_anomalies AS
SELECT *
FROM STREAM silver_sensor_with_anomalies
WHERE anomaly_flag IN ('HIGH_OUTLIER', 'LOW_OUTLIER');
```

### 基於閾值的過濾

```sql
CREATE OR REPLACE STREAMING TABLE silver_high_value_transactions AS
SELECT transaction_id, customer_id, amount, transaction_timestamp
FROM STREAM bronze_transactions
WHERE amount > 10000;
```

---

## 執行模式 (Execution Modes)

在管線層級設定 (非 SQL)：

**Continuous** (即時，亞秒級延遲):
```yaml
execution_mode: continuous
serverless: true
```

**Triggered** (排程，成本優化):
```yaml
execution_mode: triggered
schedule: "0 * * * *"  # 每小時
```

**何時使用**:
- **Continuous**: 即時儀表板、警報、亞分鐘 SLA
- **Triggered**: 每日/每小時報表、批次處理

---

## 關鍵模式

### 1. 使用事件時間戳記

```sql
-- ✅ 邏輯使用事件時間
GROUP BY date_trunc('hour', event_timestamp)

-- ❌ 處理時間戳記
GROUP BY date_trunc('hour', _ingested_at)
```

### 2. 視窗大小選擇

- **1-5 分鐘**: 即時監控
- **15-60 分鐘**: 營運儀表板
- **1-24 小時**: 分析報表

### 3. 狀態管理

較高基數 (Cardinality) = 更多狀態：

```sql
-- 高狀態: 1M 使用者 × 10K 產品 × 100M 工作階段
GROUP BY user_id, product_id, session_id

-- 較低狀態: 1M 使用者 × 100 類別 × 天
GROUP BY user_id, product_category, DATE(event_time)
```

使用時間視窗來限制狀態保留。

### 4. 及早去重

在 Bronze → Silver 轉換時應用：

```sql
-- Bronze: 接受重複
CREATE OR REPLACE STREAMING TABLE bronze_events AS
SELECT * FROM read_stream(...);

-- Silver: 立即去重
CREATE OR REPLACE STREAMING TABLE silver_events AS
SELECT DISTINCT event_id, event_type, event_timestamp, user_id
FROM STREAM bronze_events;

-- Gold: 使用乾淨資料
CREATE OR REPLACE STREAMING TABLE gold_metrics AS
SELECT ... FROM STREAM silver_events;
```

### 5. 監控 Lag

```sql
CREATE OR REPLACE STREAMING TABLE monitoring_lag AS
SELECT
  'kafka_events' AS source,
  MAX(kafka_timestamp) AS max_event_timestamp,
  current_timestamp() AS processing_timestamp,
  (unix_timestamp(current_timestamp()) - unix_timestamp(MAX(kafka_timestamp))) AS lag_seconds
FROM STREAM bronze_kafka_events
GROUP BY window(kafka_timestamp, '1 minute');
```

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| 視窗導致高記憶體使用 | 使用較大視窗，減少 Group-by 基數 |
| 輸出資料表中有重複事件 | 依唯一鍵加入明確去重 |
| 遺失晚到事件 | 增加視窗大小或使用較長的保留期 |
| 串流對串流 Join 為空 | 驗證 Join 條件與時間邊界 |
| 狀態隨時間增長 | 加入時間視窗，減少基數，物化中介結果 |
