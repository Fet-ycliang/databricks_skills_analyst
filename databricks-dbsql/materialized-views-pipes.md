# 具體化檢視、暫存資料表/檢視和管道語法

## 1. Databricks SQL 中的具體化檢視

### 概述

具體化檢視（MV）是 Unity Catalog 管理的資料表，實際儲存預先計算的查詢結果。與每次查詢都重新計算的標準檢視不同，MV 會快取結果並自動更新 -- 可以按排程、當上游資料變更時，或按需更新。

關鍵特性：
- **預先計算的儲存**：結果實際儲存為 Delta 資料表，減少查詢延遲
- **自動更新**：變更透過增量或完全重新整理從來源資料表傳播
- **無伺服器管線**：每個 MV 自動建立無伺服器管線以進行建立和重新整理
- **增量重新整理**：在某些條件下可以僅計算來源資料表的變更資料

### 需求

- **運算**：啟用 Unity Catalog 的**無伺服器** SQL 倉儲
- **區域**：您的區域必須支援無伺服器 SQL 倉儲
- **權限**：
  - 建立者需要：基礎資料表上的 `SELECT`、`USE CATALOG`、`USE SCHEMA`、`CREATE TABLE`、`CREATE MATERIALIZED VIEW`
  - 重新整理需要：所有權或 `REFRESH` 權限；MV 擁有者必須保留基礎資料表上的 `SELECT`
  - 查詢需要：MV 上的 `SELECT`、`USE CATALOG`、`USE SCHEMA`

### CREATE MATERIALIZED VIEW 語法

```sql
{ CREATE OR REPLACE MATERIALIZED VIEW | CREATE MATERIALIZED VIEW [ IF NOT EXISTS ] }
  view_name
  [ column_list ]
  [ view_clauses ]
  AS query
```

**欄位列表**（選用）：
```sql
CREATE MATERIALIZED VIEW mv_name (
  col1 INT NOT NULL,
  col2 STRING,
  col3 DOUBLE,
  CONSTRAINT pk PRIMARY KEY (col1)
)
AS SELECT ...
```

**檢視子句**（選用）：
- `PARTITIONED BY (col1, col2)` -- 按欄位分割
- `CLUSTER BY (col1, col2)` 或 `CLUSTER BY AUTO` -- liquid clustering（不能與 PARTITIONED BY 組合）
- `COMMENT 'description'` -- 檢視說明
- `TBLPROPERTIES ('key' = 'value')` -- 使用者定義的屬性
- `WITH ROW FILTER func ON (col1, col2)` -- 列層級安全性
- `MASK func` 在欄位上 -- 欄位層級遮罩
- `SCHEDULE` 子句 -- 自動重新整理排程
- `TRIGGER ON UPDATE` 子句 -- 事件驅動重新整理

### 基本範例

```sql
-- 簡單的具體化檢視
CREATE MATERIALIZED VIEW catalog.schema.daily_sales
  COMMENT '每日銷售聚合'
AS SELECT
    date,
    region,
    SUM(sales) AS total_sales,
    COUNT(*) AS num_transactions
FROM catalog.schema.raw_sales
GROUP BY date, region;

-- 帶有明確欄位、約束和叢集的 MV
CREATE MATERIALIZED VIEW catalog.schema.customer_orders (
  customer_id INT NOT NULL,
  full_name STRING,
  order_count BIGINT,
  CONSTRAINT customer_pk PRIMARY KEY (customer_id)
)
CLUSTER BY AUTO
COMMENT '客戶訂單計數'
AS SELECT
    c.customer_id,
    c.full_name,
    COUNT(o.order_id) AS order_count
FROM catalog.schema.customers c
INNER JOIN catalog.schema.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.full_name;
```

### 重新整理選項

MV 支援四種重新整理策略：

#### 1. 手動重新整理

```sql
-- 同步（阻塞直到完成）
REFRESH MATERIALIZED VIEW catalog.schema.daily_sales;

-- 非同步（立即返回）
REFRESH MATERIALIZED VIEW catalog.schema.daily_sales ASYNC;
```

#### 2. 排程重新整理（SCHEDULE）

```sql
-- 每 N 小時/天/週
CREATE OR REPLACE MATERIALIZED VIEW catalog.schema.hourly_metrics
  SCHEDULE EVERY 1 HOUR
AS SELECT date_trunc('hour', event_time) AS hour, COUNT(*) AS events
FROM catalog.schema.raw_events
GROUP BY 1;

-- 基於 Cron 的排程
CREATE OR REPLACE MATERIALIZED VIEW catalog.schema.nightly_report
  SCHEDULE CRON '0 0 2 * * ?' AT TIME ZONE 'America/New_York'
AS SELECT * FROM catalog.schema.daily_aggregates;
```

有效間隔：1-72 小時、1-31 天、1-8 週。會自動為排程重新整理建立 Databricks Job。

#### 3. 事件驅動重新整理（TRIGGER ON UPDATE）

當上游資料變更時自動重新整理：

```sql
CREATE OR REPLACE MATERIALIZED VIEW catalog.schema.customer_orders
  TRIGGER ON UPDATE
AS SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_count
FROM catalog.schema.customers c
JOIN catalog.schema.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name;

-- 帶有節流以避免過度重新整理
CREATE OR REPLACE MATERIALIZED VIEW catalog.schema.customer_orders
  TRIGGER ON UPDATE AT MOST EVERY INTERVAL 5 MINUTES
AS SELECT c.customer_id, c.name, COUNT(o.order_id) AS order_count
FROM catalog.schema.customers c
JOIN catalog.schema.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name;
```

觸發器限制：
- 最多 **10 個上游來源資料表**和 **30 個上游檢視**
- 最小 **1 分鐘**間隔（預設）
- 每個工作區最多 **1,000** 個基於觸發器的 MV
- 支援 Delta 資料表、託管檢視和串流資料表作為來源
- **不**支援 Delta Sharing 共享資料表

#### 4. 基於作業的編排

使用 SQL 任務類型將重新整理整合到現有的 Databricks Jobs 中：

```sql
-- 在 Databricks Job SQL 任務中
REFRESH MATERIALIZED VIEW catalog.schema.daily_sales_summary;
```

### 建立後管理排程

```sql
-- 為現有 MV 新增排程
ALTER MATERIALIZED VIEW catalog.schema.my_mv ADD SCHEDULE EVERY 4 HOURS;

-- 新增基於觸發器的重新整理
ALTER MATERIALIZED VIEW catalog.schema.my_mv ADD TRIGGER ON UPDATE;

-- 變更現有排程
ALTER MATERIALIZED VIEW catalog.schema.my_mv ALTER SCHEDULE EVERY 2 HOURS;

-- 移除排程
ALTER MATERIALIZED VIEW catalog.schema.my_mv DROP SCHEDULE;
```

### 增量 vs 完全重新整理

| 方面 | 增量重新整理 | 完全重新整理 |
|--------|-------------------|--------------|
| 功能 | 評估自上次重新整理以來的變更，僅合併新的/修改的記錄 | 重新執行整個定義查詢 |
| 使用時機 | 當來源資料表支援變更追蹤且查詢結構允許時 | 當增量不可能或不具成本效益時 |
| 需求 | 啟用列追蹤和 CDF 的 Delta 來源資料表 | 無特殊需求 |
| 成本 | 較低（僅處理增量） | 較高（重新計算所有內容） |

在來源資料表上啟用列追蹤以進行增量重新整理：

```sql
ALTER TABLE catalog.schema.source_table
SET TBLPROPERTIES (delta.enableRowTracking = true);
```

預設情況下，Databricks 使用成本模型在增量和完全重新整理之間選擇。使用 `EXPLAIN CREATE MATERIALIZED VIEW` 驗證選擇的重新整理類型。

### 逾時配置

```sql
-- 在建立或重新整理前設定逾時
SET STATEMENT_TIMEOUT = '6h';
CREATE OR REFRESH MATERIALIZED VIEW catalog.schema.my_mv
  SCHEDULE EVERY 12 HOURS
AS SELECT * FROM catalog.schema.large_source_table;
```

如果未配置倉儲逾時，預設逾時為 **2 天**。變更倉儲逾時後，重新執行 `CREATE OR REFRESH` 以應用新設定。

### 監控

- **Catalog Explorer**：在 MV 條目下檢視重新整理狀態、結構描述、權限、血緣
- **DESCRIBE EXTENDED**：取得排程和配置詳細資訊
- **Jobs & Pipelines UI**：監控自動建立的管線
- **Pipelines API**：`GET /api/2.0/pipelines/{pipeline_id}` 用於程式化存取
- **DESCRIBE EXTENDED AS JSON**：取得重新整理資訊，包括上次重新整理時間、類型、狀態和排程（2025 年 10 月新增）

### 關鍵限制

- 不支援識別欄位或代理鍵
- 無法從具體化檢視讀取變更資料摘要（CDF）
- 不支援時間旅行查詢
- 不支援 `OPTIMIZE` 和 `VACUUM` 命令（自動管理）
- **Null 處理邊緣案例**：當所有非 null 值被移除時，可空欄位上的 `SUM()` 返回 **0** 而非 `NULL`
- 定義查詢中的非欄位表達式需要明確別名
- 底層儲存可能包含 MV 定義中不可見的上游資料（增量重新整理所需）
- 無法透過 ALTER 重新命名 MV 或變更其擁有者（必須刪除並重新建立）
- 不支援資料品質期望
- AWS PrivateLink 需要聯絡 Databricks 支援

### DBSQL 具體化檢視 vs 管線（SDP/DLT）具體化檢視

| 方面 | DBSQL 具體化檢視 | 管線（SDP/DLT）具體化檢視 |
|--------|-------------------------|--------------------------------------|
| **建立** | 在 SQL 倉儲中使用 `CREATE MATERIALIZED VIEW` | 在管線來源程式碼中定義（SQL 或 Python） |
| **管線類型** | `MV/ST`（自動建立的無伺服器管線） | `ETL`（明確定義的管線） |
| **管線管理** | 自動建立和管理 | 使用者定義，完全的管線生命週期控制 |
| **語法** | 標準 `CREATE MATERIALIZED VIEW` | 帶有 `PRIVATE` 選項的 `CREATE OR REFRESH MATERIALIZED VIEW` |
| **私有 MV** | 不支援 | `PRIVATE` 關鍵字用於管線範圍的檢視 |
| **重新整理觸發器** | 排程、觸發更新、手動或基於作業 | 管線更新（手動或排程） |
| **運算** | 無伺服器 SQL 倉儲（建立）；無伺服器管線（重新整理） | 管線運算（無伺服器或傳統） |
| **資料品質** | 不支援 | 支援期望 |
| **最適合** | 獨立 MV、BI 儀表板加速、簡單 ETL | 複雜的多資料表管線、編排的轉換 |

兩種方法最終都使用類似的底層機制（無伺服器管線）並支援增量重新整理。關鍵差異在於管理：DBSQL MV 是自包含的，具有自動管理的管線，而管線 MV 是更廣泛編排資料流的一部分。

### 最佳實踐

1. **選擇正確的重新整理策略**：`TRIGGER ON UPDATE` 用於近即時 SLA；`SCHEDULE` 用於可預測的節奏；手動或基於作業用於複雜編排
2. **在 Delta 來源資料表上啟用列追蹤**以實現具成本效益的增量重新整理
3. **使用非同步重新整理**當重新整理持續時間較長且下游查詢可以容忍輕微的過時性時
4. **設定明確的逾時**當重新整理持續時間可預測時，以避免失控的成本
5. **使用 `CLUSTER BY AUTO`** 以進行自動 liquid clustering 優化
6. **在 MV 建立時應用列篩選器和欄位遮罩**以確保安全性
7. **使用 `EXPLAIN CREATE MATERIALIZED VIEW` 監控重新整理類型**以驗證增量行為

---

## 2. 暫存資料表和暫存檢視

### 暫存資料表

暫存資料表是工作階段範圍的實體 Delta 資料表，用於中間資料儲存。它們僅存在於建立它們的工作階段中。

#### 關鍵特性

- **工作階段範圍**：僅對建立工作階段可見；與其他使用者隔離
- **實體儲存**：儲存為與工作區綁定的內部 Unity Catalog 位置中的 Delta 資料表
- **最長生命週期**：從工作階段建立起 7 天，或直到工作階段結束（以先到者為準）
- **不需要目錄權限**：任何使用者都可以建立暫存資料表，無需 `CREATE TABLE` 權限
- **自動清理**：Databricks 自動回收儲存，即使在意外斷開連接後
- **共享命名空間**：暫存資料表與暫存檢視共享命名空間；您不能建立兩者具有相同名稱

#### 語法

```sql
-- 使用結構描述建立
CREATE TEMPORARY TABLE temp_results (
  id INT,
  name STRING,
  score DOUBLE
);

-- 從查詢建立（CTAS）
CREATE TEMP TABLE temp_active_users
AS SELECT user_id, username, last_login
FROM catalog.schema.users
WHERE last_login > current_date() - INTERVAL 30 DAYS;
```

注意：**尚不支援** `CREATE OR REPLACE TEMP TABLE`。要替換，請先刪除。

#### 支援的操作

```sql
-- INSERT
INSERT INTO temp_results VALUES (1, 'Alice', 95.5);
INSERT INTO temp_results SELECT * FROM catalog.schema.source WHERE score > 90;

-- UPDATE
UPDATE temp_results SET score = 100.0 WHERE name = 'Alice';

-- MERGE
MERGE INTO temp_results t
USING catalog.schema.new_scores s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET score = s.score
WHEN NOT MATCHED THEN INSERT *;
```

#### 不支援的操作

- `DELETE FROM`（不支援）
- `ALTER TABLE`（改為刪除並重新建立）
- 淺層或深層複製
- 時間旅行
- 串流（foreachBatch）
- DataFrame API 存取（僅限 SQL）

#### 使用案例

1. **探索性分析**：在迭代查詢時儲存中間結果
2. **多步驟轉換**：將複雜轉換分解為可讀的步驟
3. **查詢結果重複使用**：計算一次，在工作階段中多次引用
4. **沙箱測試**：測試轉換而不影響生產資料表

#### 名稱解析

當引用單部分資料表名稱時，Databricks 按順序解析：
1. 目前工作階段中的暫存資料表
2. 目前結構描述中的永久資料表

與永久資料表同名的暫存資料表在該工作階段中**優先**。

### 暫存檢視

暫存檢視是工作階段範圍的邏輯檢視，儲存查詢定義（而非資料）。它們在每次存取時重新計算。

#### 語法

```sql
-- 建立暫存檢視
CREATE TEMPORARY VIEW active_customers
AS SELECT customer_id, name, email
FROM catalog.schema.customers
WHERE status = 'active';

-- 替換現有的暫存檢視
CREATE OR REPLACE TEMPORARY VIEW active_customers
AS SELECT customer_id, name, email, phone
FROM catalog.schema.customers
WHERE status = 'active' AND last_order > current_date() - INTERVAL 90 DAYS;
```

#### 關鍵規則

- 暫存檢視名稱**不得限定**（無目錄或結構描述前綴）
- 建立不需要特殊權限
- 工作階段結束時自動刪除
- 不能使用 `schema_binding` 子句
- 支援 `COMMENT` 和欄位註解

#### 全域暫存檢視（僅限 Databricks Runtime）

```sql
-- 僅在 Databricks Runtime 中可用，在 Databricks SQL 中不可用
CREATE GLOBAL TEMPORARY VIEW global_summary
AS SELECT region, SUM(revenue) AS total_revenue
FROM catalog.schema.sales
GROUP BY region;

-- 必須透過 global_temp 結構描述引用
SELECT * FROM global_temp.global_summary;
```

全域暫存檢視儲存在系統 `global_temp` 結構描述中，並且是工作階段範圍的。它們**在 Databricks SQL 中不可用**（僅限 Databricks Runtime）。

### 暫存資料表 vs 暫存檢視

| 方面 | 暫存資料表 | 暫存檢視 |
|--------|-----------------|-----------------|
| **儲存** | 實體 Delta 資料表（儲存資料） | 邏輯（僅儲存查詢定義） |
| **存取時計算** | 否（資料已具體化） | 是（每次重新執行查詢） |
| **DML 支援** | INSERT、UPDATE、MERGE | 無（唯讀定義） |
| **最長生命週期** | 7 天或工作階段結束 | 工作階段結束 |
| **CREATE OR REPLACE** | 不支援 | 支援 |
| **效能** | 重複讀取更快（資料已快取） | 重複讀取較慢（重新計算） |
| **儲存成本** | 使用雲端儲存（自動清理） | 無儲存成本 |
| **共享命名空間** | 是（與暫存檢視衝突） | 是（與暫存資料表衝突） |
| **使用時機** | 大型中間結果、重複存取、需要 DML | 簡單查詢別名、輕量級轉換 |

### 暫存指標檢視（2025 年 9 月新增）

```sql
-- 暫存指標檢視：工作階段範圍，工作階段結束時刪除
CREATE TEMPORARY METRIC VIEW session_metrics
AS SELECT ...;
```

在 Databricks Runtime 17.2+ 和 Databricks SQL 中可用。

---

## 3. SQL 管道語法

### 概述

管道語法（2025 年 2 月引入）允許使用 `|>` 運算子將 SQL 查詢組合為由上而下、由左至右的操作鏈。它消除了深度巢狀的子查詢，並使 SQL 讀起來像 DataFrame 管線。

**需求**：Databricks SQL 或 Databricks Runtime **16.2+**

### 基本語法

```sql
FROM table_name
|> pipe_operation_1
|> pipe_operation_2
|> pipe_operation_3;
```

任何查詢都可以啟動管線。最常見的模式是 `FROM table_name`，但任何 SELECT 或子查詢也可以：

```sql
-- 從資料表開始
FROM catalog.schema.sales |> WHERE region = 'US' |> SELECT product, amount;

-- 從子查詢開始
(SELECT * FROM catalog.schema.sales WHERE year = 2025)
|> AGGREGATE SUM(amount) AS total GROUP BY product
|> ORDER BY total DESC;
```

### 所有可用的管道運算子

#### SELECT -- 投影欄位

```sql
FROM catalog.schema.employees
|> SELECT employee_id, name, department, salary;
```

注意：管道語法中的 `SELECT` **不得包含聚合函數**。改用 `AGGREGATE`。

#### EXTEND -- 新增新欄位

將新欄位附加到現有結果集（類似 PySpark 的 `withColumn`）：

```sql
FROM catalog.schema.orders
|> EXTEND quantity * unit_price AS line_total
|> EXTEND line_total * 0.1 AS tax;
```

表達式可以引用同一 EXTEND 中前面表達式建立的欄位。

#### SET -- 修改現有欄位

覆寫現有欄位值（類似 PySpark 在現有欄位上的 `withColumn`）：

```sql
FROM catalog.schema.products
|> SET price = price * 1.1
|> SET name = UPPER(name);
```

如果欄位不存在則引發 `UNRESOLVED_COLUMN`。

#### DROP -- 移除欄位

移除欄位（`SELECT * EXCEPT` 的簡寫）：

```sql
FROM catalog.schema.users
|> DROP password_hash, internal_id, debug_flag;
```

#### WHERE -- 篩選列

```sql
FROM catalog.schema.transactions
|> WHERE amount > 1000
|> WHERE transaction_date >= '2025-01-01';
```

#### AGGREGATE -- 帶有選用 GROUP BY 的聚合

```sql
-- 全資料表聚合
FROM catalog.schema.orders
|> AGGREGATE
     COUNT(*) AS total_orders,
     SUM(amount) AS total_revenue,
     AVG(amount) AS avg_order_value;

-- 分組聚合
FROM catalog.schema.orders
|> AGGREGATE
     SUM(amount) AS total_revenue,
     COUNT(*) AS order_count
   GROUP BY region, product_category;
```

在管道語法中，`AGGREGATE` 取代 `SELECT ... GROUP BY`。GROUP BY 中的數值引用輸入欄位，而非生成的結果。

#### JOIN -- 組合關聯

```sql
FROM catalog.schema.orders
|> AS o
|> LEFT JOIN catalog.schema.customers c ON o.customer_id = c.customer_id
|> SELECT o.order_id, c.name, o.amount;
```

支援所有 JOIN 類型：`INNER JOIN`、`LEFT OUTER JOIN`、`RIGHT OUTER JOIN`、`FULL OUTER JOIN`、`CROSS JOIN`、`SEMI JOIN`、`ANTI JOIN`。

#### ORDER BY -- 排序結果

```sql
FROM catalog.schema.products
|> ORDER BY price DESC, name ASC;
```

#### LIMIT 和 OFFSET -- 分頁

```sql
FROM catalog.schema.products
|> ORDER BY price DESC
|> LIMIT 10
|> OFFSET 20;
```

#### AS -- 指定資料表別名

為中間結果命名，以便在後續 JOIN 或自我引用中使用：

```sql
FROM catalog.schema.sales
|> AS current_sales
|> JOIN catalog.schema.targets t ON current_sales.region = t.region
|> SELECT current_sales.region, current_sales.revenue, t.target;
```

#### 集合運算子 -- UNION、EXCEPT、INTERSECT

```sql
FROM catalog.schema.us_customers
|> UNION ALL (SELECT * FROM catalog.schema.eu_customers)
|> ORDER BY name;
```

#### TABLESAMPLE -- 取樣列

```sql
-- 按列數取樣
FROM catalog.schema.large_table
|> TABLESAMPLE (1000 ROWS);

-- 按百分比取樣
FROM catalog.schema.large_table
|> TABLESAMPLE (10 PERCENT);
```

#### PIVOT -- 列轉欄位

```sql
FROM catalog.schema.quarterly_sales
|> PIVOT (
     SUM(revenue)
     FOR quarter IN ('Q1', 'Q2', 'Q3', 'Q4')
   );
```

#### UNPIVOT -- 欄位轉列

```sql
FROM catalog.schema.wide_metrics
|> UNPIVOT (
     metric_value FOR metric_name IN (cpu_usage, memory_usage, disk_usage)
   );
```

### 實用範例

#### 範例 1：多步驟聚合（取代巢狀子查詢）

傳統 SQL：
```sql
SELECT c_count, COUNT(*) AS custdist
FROM (
  SELECT c_custkey, COUNT(o_orderkey) AS c_count
  FROM customer
  LEFT OUTER JOIN orders ON c_custkey = o_custkey
    AND o_comment NOT LIKE '%unusual%packages%'
  GROUP BY c_custkey
) AS c_orders
GROUP BY c_count
ORDER BY custdist DESC, c_count DESC;
```

管道語法：
```sql
FROM customer
|> LEFT OUTER JOIN orders ON c_custkey = o_custkey
   AND o_comment NOT LIKE '%unusual%packages%'
|> AGGREGATE COUNT(o_orderkey) AS c_count GROUP BY c_custkey
|> AGGREGATE COUNT(*) AS custdist GROUP BY c_count
|> ORDER BY custdist DESC, c_count DESC;
```

#### 範例 2：資料探索和分析

```sql
FROM catalog.schema.raw_events
|> WHERE event_date >= '2025-01-01'
|> EXTEND YEAR(event_date) AS event_year, MONTH(event_date) AS event_month
|> AGGREGATE
     COUNT(*) AS event_count,
     COUNT(DISTINCT user_id) AS unique_users,
     AVG(duration_seconds) AS avg_duration
   GROUP BY event_year, event_month
|> ORDER BY event_year, event_month;
```

#### 範例 3：逐步建立報告

```sql
FROM catalog.schema.orders
|> AS o
|> JOIN catalog.schema.products p ON o.product_id = p.product_id
|> JOIN catalog.schema.customers c ON o.customer_id = c.customer_id
|> WHERE o.order_date >= '2025-01-01'
|> EXTEND o.quantity * p.unit_price AS line_total
|> AGGREGATE
     SUM(line_total) AS total_revenue,
     COUNT(DISTINCT o.order_id) AS order_count
   GROUP BY c.region, p.category
|> ORDER BY total_revenue DESC
|> LIMIT 20;
```

#### 範例 4：透過註解尾部操作進行除錯

```sql
FROM catalog.schema.sales
|> WHERE region = 'US'
|> EXTEND amount * tax_rate AS tax_amount
-- |> AGGREGATE SUM(tax_amount) AS total_tax GROUP BY state
-- |> ORDER BY total_tax DESC
;
-- 註解掉最後的操作以檢查中間結果
```

### 管道語法 vs 傳統 SQL

| 方面 | 傳統 SQL | 管道 SQL |
|--------|----------------|----------|
| **閱讀順序** | 由內而外（子查詢優先） | 由上而下、由左至右 |
| **子句順序** | 固定：SELECT...FROM...WHERE...GROUP BY...ORDER BY | 任何順序，任意次數 |
| **子查詢巢狀** | 多步驟聚合需要 | 透過鏈接消除 |
| **新增欄位** | SELECT *, expr AS new_col | `EXTEND expr AS new_col` |
| **移除欄位** | 使用明確欄位列表或 EXCEPT 的 SELECT | `DROP col1, col2` |
| **修改欄位** | 使用替換欄位的表達式的 SELECT | `SET col = new_expr` |
| **聚合** | SELECT agg() ... GROUP BY | `AGGREGATE agg() GROUP BY` |
| **可組合性** | 有限；需要 CTE 或子查詢 | 原生鏈接 |
| **互通性** | 標準 | 與傳統 SQL 完全互通 |

### 何時使用管道語法

**使用管道語法的時機：**
- 多步驟聚合需要巢狀子查詢
- 您想要 SQL 中類似 DataFrame 的可讀性
- 建立探索性或迭代查詢（易於新增/移除步驟）
- 具有許多連接、篩選器和投影的複雜轉換

**使用傳統 SQL 的時機：**
- 已經可讀的簡單查詢
- 團隊更熟悉標準 SQL
- 查詢將與可能不支援管道語法的工具共享

### 效能考量

- 管道語法是**語法糖** -- 它編譯為與傳統 SQL 相同的執行計劃
- 對於等效查詢，管道和傳統語法之間沒有效能差異
- 最佳實踐：將減少資料的操作（`WHERE`、`DROP`、`SELECT`）放在管線的早期，以最小化流經後續操作的資料
- 在開發期間使用 `TABLESAMPLE` 以處理較小的資料集
