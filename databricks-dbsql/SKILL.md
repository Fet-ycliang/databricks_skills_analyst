---
name: databricks-dbsql
description: >-
  Databricks SQL (DBSQL) 進階功能和 SQL 倉儲能力。
  當使用者提到以下內容時，必須呼叫此技能：「DBSQL」、「Databricks SQL」、
  「SQL 倉儲」、「SQL 腳本」、「預存程序」、「CALL 程序」、
  「具體化檢視」、「CREATE MATERIALIZED VIEW」、「管道語法」、「|>」、
  「地理空間」、「H3」、「ST_」、「空間 SQL」、「定序」、「COLLATE」、
  「ai_query」、「ai_classify」、「ai_extract」、「ai_gen」、「AI 函數」、
  「http_request」、「remote_query」、「read_files」、「Lakehouse Federation」、
  「遞迴 CTE」、「WITH RECURSIVE」、「多陳述式交易」、
  「暫存資料表」、「暫時檢視」、「管道運算子」。
  當使用者詢問 SQL 最佳實踐、資料建模模式或 Databricks 上的進階 SQL 功能時，也應該呼叫。
---

# Databricks SQL (DBSQL) - 進階功能

## 快速參考

| 功能 | 關鍵語法 | 版本 | 參考 |
|---------|-----------|-------|-----------|
| SQL 腳本 | `BEGIN...END`、`DECLARE`、`IF/WHILE/FOR` | DBR 16.3+ | [sql-scripting.md](sql-scripting.md) |
| 預存程序 | `CREATE PROCEDURE`、`CALL` | DBR 17.0+ | [sql-scripting.md](sql-scripting.md) |
| 遞迴 CTE | `WITH RECURSIVE` | DBR 17.0+ | [sql-scripting.md](sql-scripting.md) |
| 交易 | `BEGIN ATOMIC...END` | 預覽版 | [sql-scripting.md](sql-scripting.md) |
| 具體化檢視 | `CREATE MATERIALIZED VIEW` | Pro/無伺服器 | [materialized-views-pipes.md](materialized-views-pipes.md) |
| 暫存資料表 | `CREATE TEMPORARY TABLE` | 全部 | [materialized-views-pipes.md](materialized-views-pipes.md) |
| 管道語法 | `\|>` 運算子 | DBR 16.1+ | [materialized-views-pipes.md](materialized-views-pipes.md) |
| 地理空間（H3） | `h3_longlatash3()`、`h3_polyfillash3()` | DBR 11.2+ | [geospatial-collations.md](geospatial-collations.md) |
| 地理空間（ST） | `ST_Point()`、`ST_Contains()`、80+ 函數 | DBR 16.0+ | [geospatial-collations.md](geospatial-collations.md) |
| 定序 | `COLLATE`、`UTF8_LCASE`、區域感知 | DBR 16.1+ | [geospatial-collations.md](geospatial-collations.md) |
| AI 函數 | `ai_query()`、`ai_classify()`、11+ 函數 | DBR 15.1+ | [ai-functions.md](ai-functions.md) |
| http_request | `http_request(conn, ...)` | Pro/無伺服器 | [ai-functions.md](ai-functions.md) |
| remote_query | `SELECT * FROM remote_query(...)` | Pro/無伺服器 | [ai-functions.md](ai-functions.md) |
| read_files | `SELECT * FROM read_files(...)` | 全部 | [ai-functions.md](ai-functions.md) |
| 資料建模 | 星型結構描述、Liquid Clustering | 全部 | [best-practices.md](best-practices.md) |

---

## 常見模式

### SQL 腳本 - 程序式 ETL

```sql
BEGIN
  DECLARE v_count INT;
  DECLARE v_status STRING DEFAULT 'pending';

  SET v_count = (SELECT COUNT(*) FROM catalog.schema.raw_orders WHERE status = 'new');

  IF v_count > 0 THEN
    INSERT INTO catalog.schema.processed_orders
    SELECT *, current_timestamp() AS processed_at
    FROM catalog.schema.raw_orders
    WHERE status = 'new';

    SET v_status = 'completed';
  ELSE
    SET v_status = 'skipped';
  END IF;

  SELECT v_status AS result, v_count AS rows_processed;
END
```

### 帶有錯誤處理的預存程序

```sql
CREATE OR REPLACE PROCEDURE catalog.schema.upsert_customers(
  IN p_source STRING,
  OUT p_rows_affected INT
)
LANGUAGE SQL
SQL SECURITY INVOKER
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    SET p_rows_affected = -1;
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = concat('Upsert failed for source: ', p_source);
  END;

  MERGE INTO catalog.schema.dim_customer AS t
  USING (SELECT * FROM identifier(p_source)) AS s
  ON t.customer_id = s.customer_id
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *;

  SET p_rows_affected = (SELECT COUNT(*) FROM identifier(p_source));
END;

-- 呼叫：
CALL catalog.schema.upsert_customers('catalog.schema.staging_customers', ?);
```

### 帶有排程重新整理的具體化檢視

```sql
CREATE OR REPLACE MATERIALIZED VIEW catalog.schema.daily_revenue
  CLUSTER BY (order_date)
  SCHEDULE EVERY 1 HOUR
  COMMENT '每小時重新整理的按地區每日收入'
AS SELECT
    order_date,
    region,
    SUM(amount) AS total_revenue,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM catalog.schema.fact_orders
JOIN catalog.schema.dim_store USING (store_id)
GROUP BY order_date, region;
```

### 管道語法 - 可讀的轉換

```sql
-- 使用管道語法重寫的傳統 SQL
FROM catalog.schema.fact_orders
  |> WHERE order_date >= current_date() - INTERVAL 30 DAYS
  |> AGGREGATE SUM(amount) AS total, COUNT(*) AS cnt GROUP BY region, product_category
  |> WHERE total > 10000
  |> ORDER BY total DESC
  |> LIMIT 20;
```

### AI 函數 - 使用 LLM 豐富資料

```sql
-- 分類支援工單
SELECT
  ticket_id,
  description,
  ai_classify(description, ARRAY('billing', 'technical', 'account', 'feature_request')) AS category,
  ai_analyze_sentiment(description) AS sentiment
FROM catalog.schema.support_tickets
LIMIT 100;

-- 從文字中提取實體
SELECT
  doc_id,
  ai_extract(content, ARRAY('person_name', 'company', 'dollar_amount')) AS entities
FROM catalog.schema.contracts;

-- 帶有結構化輸出的通用 AI 查詢
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  concat('以 JSON 格式總結此客戶回饋，包含鍵值：topic、sentiment、action_items。回饋：', feedback),
  returnType => 'STRUCT<topic STRING, sentiment STRING, action_items ARRAY<STRING>>'
) AS analysis
FROM catalog.schema.customer_feedback
LIMIT 50;
```

### 地理空間 - 使用 H3 的鄰近搜尋

```sql
-- 使用 H3 索引尋找每個客戶 5 公里內的商店
WITH customer_h3 AS (
  SELECT *, h3_longlatash3(longitude, latitude, 7) AS h3_cell
  FROM catalog.schema.customers
),
store_h3 AS (
  SELECT *, h3_longlatash3(longitude, latitude, 7) AS h3_cell
  FROM catalog.schema.stores
)
SELECT
  c.customer_id,
  s.store_id,
  ST_Distance(
    ST_Point(c.longitude, c.latitude),
    ST_Point(s.longitude, s.latitude)
  ) AS distance_m
FROM customer_h3 c
JOIN store_h3 s ON h3_ischildof(c.h3_cell, h3_toparent(s.h3_cell, 5))
WHERE ST_Distance(
  ST_Point(c.longitude, c.latitude),
  ST_Point(s.longitude, s.latitude)
) < 5000;
```

### 定序 - 不區分大小寫的搜尋

```sql
-- 使用不區分大小寫的定序建立資料表
CREATE TABLE catalog.schema.products (
  product_id BIGINT GENERATED ALWAYS AS IDENTITY,
  name STRING COLLATE UTF8_LCASE,
  category STRING COLLATE UTF8_LCASE,
  price DECIMAL(10, 2)
);

-- 查詢自動不區分大小寫（不需要 LOWER()）
SELECT * FROM catalog.schema.products
WHERE name = 'MacBook Pro';  -- 匹配 'macbook pro'、'MACBOOK PRO' 等
```

### http_request - 呼叫外部 API

```sql
-- 首先設定連接（一次性）
CREATE CONNECTION my_api_conn
  TYPE HTTP
  OPTIONS (host 'https://api.example.com', bearer_token secret('scope', 'token'));

-- 從 SQL 呼叫 API
SELECT
  order_id,
  http_request(
    conn => 'my_api_conn',
    method => 'POST',
    path => '/v1/validate',
    json => to_json(named_struct('order_id', order_id, 'amount', amount))
  ).text AS api_response
FROM catalog.schema.orders
WHERE needs_validation = true;
```

### read_files - 擷取原始檔案

```sql
-- 從磁碟區讀取帶有結構描述提示的 JSON 檔案
SELECT *
FROM read_files(
  '/Volumes/catalog/schema/raw/events/',
  format => 'json',
  schemaHints => 'event_id STRING, timestamp TIMESTAMP, payload MAP<STRING, STRING>',
  pathGlobFilter => '*.json',
  recursiveFileLookup => true
);

-- 使用選項讀取 CSV
SELECT *
FROM read_files(
  '/Volumes/catalog/schema/raw/sales/',
  format => 'csv',
  header => true,
  delimiter => '|',
  dateFormat => 'yyyy-MM-dd',
  schema => 'sale_id INT, sale_date DATE, amount DECIMAL(10,2), store STRING'
);
```

### 遞迴 CTE - 階層遍歷

```sql
WITH RECURSIVE org_chart AS (
  -- 錨點：頂層管理者
  SELECT employee_id, name, manager_id, 0 AS depth, ARRAY(name) AS path
  FROM catalog.schema.employees
  WHERE manager_id IS NULL

  UNION ALL

  -- 遞迴：直接下屬
  SELECT e.employee_id, e.name, e.manager_id, o.depth + 1, array_append(o.path, e.name)
  FROM catalog.schema.employees e
  JOIN org_chart o ON e.manager_id = o.employee_id
  WHERE o.depth < 10  -- 安全限制
)
SELECT * FROM org_chart ORDER BY depth, name;
```

### remote_query - 聯邦查詢

```sql
-- 透過 Lakehouse Federation 查詢 PostgreSQL
SELECT *
FROM remote_query(
  'my_postgres_connection',
  database => 'my_database',
  query    => 'SELECT customer_id, email, created_at FROM customers WHERE active = true'
);
```

---

## 參考文件

載入這些文件以取得詳細語法、完整參數列表和進階模式：

| 檔案 | 內容 | 何時閱讀 |
|------|----------|--------------|
| [sql-scripting.md](sql-scripting.md) | SQL 腳本、預存程序、遞迴 CTE、交易 | 使用者需要程序式 SQL、錯誤處理、迴圈、動態 SQL |
| [materialized-views-pipes.md](materialized-views-pipes.md) | 具體化檢視、暫存資料表/檢視、管道語法 | 使用者需要 MV、重新整理排程、暫存物件、管道運算子 |
| [geospatial-collations.md](geospatial-collations.md) | 39 個 H3 函數、80+ 個 ST 函數、定序類型和階層 | 使用者需要空間分析、H3 索引、大小寫/重音處理 |
| [ai-functions.md](ai-functions.md) | 13 個 AI 函數、http_request、remote_query、read_files（所有選項） | 使用者需要 AI 豐富、API 呼叫、聯邦、檔案擷取 |
| [best-practices.md](best-practices.md) | 資料建模、效能、Liquid Clustering、反模式 | 使用者需要架構指導、優化或建模建議 |

---

## 關鍵指南

- **始終使用無伺服器 SQL 倉儲**用於 AI 函數、MV 和 http_request
- **在開發期間使用 `LIMIT`**搭配 AI 函數以控制成本
- **對新資料表優先使用 Liquid Clustering 而非分割**（最多 1-4 個鍵）
- **當不確定叢集鍵時使用 `CLUSTER BY AUTO`**
- **Gold 層使用星型結構描述**用於 BI；Silver 層可接受 OBT
- **在維度模型上定義 PK/FK 約束**以進行查詢優化
- **對需要不區分大小寫搜尋的面向使用者的字串欄位使用 `COLLATE UTF8_LCASE`**
- **使用 MCP 工具**（`execute_sql`、`execute_sql_multi`）在部署前測試和驗證所有 SQL
