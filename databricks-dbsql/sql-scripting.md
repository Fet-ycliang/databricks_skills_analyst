# SQL 腳本、預存程序、遞迴 CTE 和交易

> 基於 SQL/PSM 標準的 Databricks SQL 程序式擴充功能。涵蓋 SQL 腳本（複合陳述式、控制流程、例外處理）、預存程序、遞迴 CTE 和多陳述式交易。

---

## 目錄

- [SQL 腳本](#sql-腳本)
  - [複合陳述式（BEGIN...END）](#複合陳述式beginend)
  - [變數宣告（DECLARE）](#變數宣告declare)
  - [變數賦值（SET）](#變數賦值set)
  - [控制流程](#控制流程)
    - [IF / ELSEIF / ELSE](#if--elseif--else)
    - [CASE 陳述式](#case-陳述式)
    - [WHILE 迴圈](#while-迴圈)
    - [FOR 迴圈](#for-迴圈)
    - [LOOP 陳述式](#loop-陳述式)
    - [REPEAT 陳述式](#repeat-陳述式)
    - [LEAVE 和 ITERATE](#leave-和-iterate)
  - [例外處理](#例外處理)
    - [條件宣告](#條件宣告)
    - [處理器宣告](#處理器宣告)
    - [SIGNAL 和 RESIGNAL](#signal-和-resignal)
  - [EXECUTE IMMEDIATE（動態 SQL）](#execute-immediate動態-sql)
- [預存程序](#預存程序)
  - [CREATE PROCEDURE](#create-procedure)
  - [CALL（呼叫程序）](#call呼叫程序)
  - [DROP PROCEDURE](#drop-procedure)
  - [DESCRIBE PROCEDURE](#describe-procedure)
  - [SHOW PROCEDURES](#show-procedures)
- [遞迴 CTE](#遞迴-cte)
  - [WITH RECURSIVE 語法](#with-recursive-語法)
  - [錨點和遞迴成員](#錨點和遞迴成員)
  - [MAX RECURSION LEVEL](#max-recursion-level)
  - [使用案例和範例](#使用案例和範例)
  - [限制](#限制)
- [多陳述式交易](#多陳述式交易)
  - [概述和目前狀態](#概述和目前狀態)
  - [SQL 腳本原子區塊](#sql-腳本原子區塊)
  - [Python 連接器交易 API](#python-連接器交易-api)
  - [隔離層級](#隔離層級)
  - [寫入衝突和並行性](#寫入衝突和並行性)
  - [最佳實踐](#最佳實踐)

---

## SQL 腳本

**可用性**：Databricks Runtime 16.3+ 和 Databricks SQL

SQL 腳本使用 SQL/PSM 標準啟用程序式邏輯。每個 SQL 腳本都以複合陳述式區塊（`BEGIN...END`）開始。

### 複合陳述式（BEGIN...END）

複合陳述式是包含變數宣告、條件/處理器宣告和可執行陳述式的基本建構區塊。

**語法**：

```sql
[ label : ] BEGIN
  [ { declare_variable | declare_condition } ; [...] ]
  [ declare_handler ; [...] ]
  [ SQL_statement ; [...] ]
END [ label ]
```

**關鍵規則**：

- 宣告必須出現在可執行陳述式之前
- 變數宣告在條件宣告之前，條件宣告在處理器宣告之前
- 頂層複合陳述式不能指定標籤
- `NOT ATOMIC` 是預設且唯一的行為（失敗時不會自動回滾）
- 在 notebook 中，複合陳述式必須是儲存格中的唯一陳述式

**主體中支援的陳述式類型**：

| 類別 | 陳述式 |
|----------|-----------|
| DDL | ALTER、CREATE、DROP |
| DCL | GRANT、REVOKE |
| DML | INSERT、UPDATE、DELETE、MERGE |
| 查詢 | SELECT |
| 賦值 | SET |
| 動態 SQL | EXECUTE IMMEDIATE |
| 控制流程 | IF、CASE、WHILE、FOR、LOOP、REPEAT、LEAVE、ITERATE |
| 巢狀 | 巢狀 BEGIN...END 區塊 |

**最小範例**：

```sql
BEGIN
  SELECT 'Hello, SQL Scripting!';
END;
```

### 變數宣告（DECLARE）

**語法**：

```sql
DECLARE variable_name [, ...] data_type [ DEFAULT default_expr ];
```

- 如果未指定 `DEFAULT`，變數會初始化為 `NULL`
- 當提供 `DEFAULT` 時可以省略資料類型（從表達式推斷類型）
- Runtime 17.2+ 支援在單一 `DECLARE` 中使用多個變數名稱
- 變數的範圍限定在其封閉的複合陳述式中
- 變數名稱從最內層範圍向外解析；使用標籤來消除歧義

**範例**：

```sql
BEGIN
  DECLARE counter INT DEFAULT 0;
  DECLARE name STRING DEFAULT 'unknown';
  DECLARE x, y, z DOUBLE DEFAULT 0.0;        -- Runtime 17.2+
  DECLARE inferred DEFAULT current_date();    -- 類型推斷為 DATE

  SET counter = counter + 1;
  VALUES (counter, name);
END;
```

### 變數賦值（SET）

**語法**：

```sql
SET variable_name = expression;
SET VAR variable_name = expression;          -- 明確的本地變數
SET (var1, var2, ...) = (expr1, expr2, ...); -- 多重賦值
```

當存在同名的工作階段變數時，使用 `SET VAR` 明確指定本地變數。

**範例**：

```sql
BEGIN
  DECLARE total INT DEFAULT 0;
  DECLARE label STRING;
  SET total = 100;
  SET label = 'final';
  VALUES (total, label);
END;
```

### 控制流程

#### IF / ELSEIF / ELSE

根據第一個評估為 `TRUE` 的條件執行陳述式。

**語法**：

```sql
IF condition THEN
  { stmt ; } [...]
[ ELSEIF condition THEN
  { stmt ; } [...] ] [...]
[ ELSE
  { stmt ; } [...] ]
END IF;
```

**範例**：

```sql
BEGIN
  DECLARE score INT DEFAULT 85;
  DECLARE grade STRING;

  IF score >= 90 THEN
    SET grade = 'A';
  ELSEIF score >= 80 THEN
    SET grade = 'B';
  ELSEIF score >= 70 THEN
    SET grade = 'C';
  ELSE
    SET grade = 'F';
  END IF;

  VALUES (grade);  -- 返回 'B'
END;
```

#### CASE 陳述式

兩種形式：**簡單 CASE**（比較表達式）和**搜尋 CASE**（評估布林條件）。

**簡單 CASE 語法**：

```sql
CASE expr
  WHEN opt1 THEN { stmt ; } [...]
  WHEN opt2 THEN { stmt ; } [...]
  [ ELSE { stmt ; } [...] ]
END CASE;
```

**搜尋 CASE 語法**：

```sql
CASE
  WHEN cond1 THEN { stmt ; } [...]
  WHEN cond2 THEN { stmt ; } [...]
  [ ELSE { stmt ; } [...] ]
END CASE;
```

只有第一個匹配的分支會執行。

**範例**：

```sql
BEGIN
  DECLARE status STRING DEFAULT 'active';

  CASE status
    WHEN 'active'   THEN VALUES ('處理中');
    WHEN 'paused'   THEN VALUES ('暫停中');
    WHEN 'archived' THEN VALUES ('唯讀');
    ELSE VALUES ('未知狀態');
  END CASE;
END;
```

#### WHILE 迴圈

當條件為 `TRUE` 時重複執行。

**語法**：

```sql
[ label : ] WHILE condition DO
  { stmt ; } [...]
END WHILE [ label ];
```

**範例** -- 計算 1 到 10 的奇數總和：

```sql
BEGIN
  DECLARE total INT DEFAULT 0;
  DECLARE i INT DEFAULT 0;

  sum_odds: WHILE i < 10 DO
    SET i = i + 1;
    IF i % 2 = 0 THEN
      ITERATE sum_odds;   -- 跳過偶數
    END IF;
    SET total = total + i;
  END WHILE sum_odds;

  VALUES (total);  -- 返回 25
END;
```

#### FOR 迴圈

迭代查詢結果列。

**語法**：

```sql
[ label : ] FOR [ variable_name AS ] query DO
  { stmt ; } [...]
END FOR [ label ];
```

- 使用 `variable_name`（不是標籤）來限定來自游標的欄位引用
- 對於 Delta 資料表，在迭代期間修改來源不會影響游標結果
- 如果被 `LEAVE` 或錯誤提前終止，迴圈可能不會完全執行查詢

**範例** -- 處理查詢中的每一列：

```sql
BEGIN
  DECLARE total_revenue DOUBLE DEFAULT 0.0;

  process_orders: FOR row AS
    SELECT order_id, amount FROM orders WHERE status = 'completed'
  DO
    SET total_revenue = total_revenue + row.amount;
    IF total_revenue > 1000000 THEN
      LEAVE process_orders;
    END IF;
  END FOR process_orders;

  VALUES (total_revenue);
END;
```

#### LOOP 陳述式

無條件迴圈；必須使用 `LEAVE` 退出。

**語法**：

```sql
[ label : ] LOOP
  { stmt ; } [...]
END LOOP [ label ];
```

**範例**：

```sql
BEGIN
  DECLARE counter INT DEFAULT 0;

  count_up: LOOP
    SET counter = counter + 1;
    IF counter >= 5 THEN
      LEAVE count_up;
    END IF;
  END LOOP count_up;

  VALUES (counter);  -- 返回 5
END;
```

#### REPEAT 陳述式

至少執行一次，然後重複直到條件為 `TRUE`。

**語法**：

```sql
[ label : ] REPEAT
  { stmt ; } [...]
  UNTIL condition
END REPEAT [ label ];
```

**範例**：

```sql
BEGIN
  DECLARE total INT DEFAULT 0;
  DECLARE i INT DEFAULT 0;

  sum_loop: REPEAT
    SET i = i + 1;
    IF i % 2 != 0 THEN
      SET total = total + i;
    END IF;
    UNTIL i >= 10
  END REPEAT sum_loop;

  VALUES (total);  -- 返回 25
END;
```

#### LEAVE 和 ITERATE

| 陳述式 | 用途 | 等效 |
|-----------|---------|-----------|
| `LEAVE label` | 退出標記的迴圈或複合區塊 | 其他語言中的 `BREAK` |
| `ITERATE label` | 跳到標記迴圈的下一次迭代 | 其他語言中的 `CONTINUE` |

兩者都需要標記的迴圈作為目標。

### 例外處理

#### 條件宣告

為特定 SQLSTATE 代碼定義命名條件。

**語法**：

```sql
DECLARE condition_name CONDITION [ FOR SQLSTATE [ VALUE ] sqlstate ];
```

- `sqlstate` 是 5 個字元的字母數字字串（A-Z、0-9，不區分大小寫）
- 不能以 `'00'`、`'01'` 或 `'XX'` 開頭
- 如果未指定，預設為 `'45000'`

**範例**：

```sql
BEGIN
  DECLARE divide_by_zero CONDITION FOR SQLSTATE '22012';
  -- 在下面的處理器宣告中使用
END;
```

#### 處理器宣告

在複合陳述式中捕獲和處理例外。

**語法**：

```sql
DECLARE handler_type HANDLER FOR condition_value [, ...] handler_action;
```

| 參數 | 選項 | 說明 |
|-----------|---------|-------------|
| `handler_type` | `EXIT` | 處理後退出封閉的複合陳述式 |
| `condition_value` | `SQLSTATE 'xxxxx'`、`condition_name`、`SQLEXCEPTION`、`NOT FOUND` | 要捕獲的內容 |
| `handler_action` | 單一陳述式或巢狀 `BEGIN...END` | 要執行的內容 |

- `SQLEXCEPTION` 捕獲所有錯誤狀態（SQLSTATE 類別不是 `'00'` 或 `'01'`）
- `NOT FOUND` 捕獲 `'02xxx'` 狀態（找不到資料）
- 處理器不能應用於其自身主體中的陳述式

**範例** -- 捕獲除以零：

```sql
BEGIN
  DECLARE result DOUBLE;
  DECLARE EXIT HANDLER FOR SQLSTATE '22012'
    BEGIN
      SET result = -1;
    END;

  SET result = 10 / 0;  -- 觸發處理器
  VALUES (result);       -- 返回 -1
END;
```

**範例** -- 通用例外處理器：

```sql
BEGIN
  DECLARE error_msg STRING DEFAULT 'none';

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
      SET error_msg = '發生錯誤';
      INSERT INTO error_log (message, ts) VALUES (error_msg, current_timestamp());
    END;

  -- 可能失敗的陳述式
  INSERT INTO target_table SELECT * FROM source_table;
END;
```

#### SIGNAL 和 RESIGNAL

引發或重新引發例外。

**SIGNAL 語法**：

```sql
SIGNAL condition_name
  [ SET { MESSAGE_ARGUMENTS = argument_map | MESSAGE_TEXT = message_str } ];

SIGNAL SQLSTATE [ VALUE ] sqlstate
  [ SET MESSAGE_TEXT = message_str ];
```

**RESIGNAL 語法**（在處理器中使用以保留診斷堆疊）：

```sql
RESIGNAL [ condition_name | SQLSTATE [ VALUE ] sqlstate ]
  [ SET { MESSAGE_ARGUMENTS = argument_map | MESSAGE_TEXT = message_str } ];
```

- 在處理器內優先使用 `RESIGNAL` 而非 `SIGNAL` -- `RESIGNAL` 保留診斷堆疊，而 `SIGNAL` 會清除它
- `MESSAGE_ARGUMENTS` 接受 `MAP<STRING, STRING>` 字面值

**範例** -- 驗證輸入並引發自訂錯誤：

```sql
BEGIN
  DECLARE input_value INT DEFAULT 150;

  IF input_value > 100 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = '輸入值必須 <= 100';
  END IF;

  VALUES (input_value);
END;
```

**範例** -- 使用帶有 MESSAGE_ARGUMENTS 的命名條件：

```sql
BEGIN
  DECLARE input INT DEFAULT 5;
  DECLARE arg_map MAP<STRING, STRING>;

  IF input > 4 THEN
    SET arg_map = map('errorMessage', '輸入必須 <= 4。');
    SIGNAL USER_RAISED_EXCEPTION
      SET MESSAGE_ARGUMENTS = arg_map;
  END IF;
END;
```

### EXECUTE IMMEDIATE（動態 SQL）

在執行時執行建構為字串的 SQL 陳述式。

**可用性**：Runtime 14.3+；從 Runtime 17.3+ 開始支援基於表達式的 `sql_string` 和巢狀執行。

**語法**：

```sql
EXECUTE IMMEDIATE sql_string
  [ INTO var_name [, ...] ]
  [ USING { arg_expr [ AS ] [ alias ] } [, ...] ];
```

- `sql_string`：產生格式良好的 SQL 陳述式的常數表達式
- `INTO`：將單列結果捕獲到變數中（零列返回 `NULL`；多列會出錯）
- `USING`：將值綁定到位置（`?`）或命名（`:param`）參數標記（不能混合樣式）

**範例**：

```sql
-- 位置參數
EXECUTE IMMEDIATE 'SELECT SUM(c1) FROM VALUES(?), (?) AS t(c1)' USING 5, 6;

-- 帶有 INTO 的命名參數
BEGIN
  DECLARE total INT;
  EXECUTE IMMEDIATE 'SELECT SUM(c1) FROM VALUES(:a), (:b) AS t(c1)'
    INTO total USING (5 AS a, 6 AS b);
  VALUES (total);  -- 返回 11
END;

-- 動態資料表操作
BEGIN
  DECLARE table_name STRING DEFAULT 'my_catalog.my_schema.staging';
  EXECUTE IMMEDIATE 'TRUNCATE TABLE ' || table_name;
  EXECUTE IMMEDIATE 'INSERT INTO ' || table_name || ' SELECT * FROM source';
END;
```

---

## 預存程序

**可用性**：公開預覽版 -- Databricks Runtime 17.0+

預存程序將 SQL 腳本持久化在 Unity Catalog 中，並使用 `CALL` 呼叫。

### CREATE PROCEDURE

**語法**：

```sql
CREATE [ OR REPLACE ] PROCEDURE [ IF NOT EXISTS ]
    procedure_name ( [ parameter [, ...] ] )
    characteristic [...]
    AS compound_statement
```

**參數定義**：

```sql
[ IN | OUT | INOUT ] parameter_name data_type
  [ DEFAULT default_expression ]
  [ COMMENT parameter_comment ]
```

| 參數模式 | 行為 |
|---------------|----------|
| `IN`（預設） | 僅輸入；值傳遞到程序中 |
| `OUT` | 僅輸出；初始化為 `NULL`；成功時返回最終值 |
| `INOUT` | 輸入和輸出；接受值並在成功時返回修改後的值 |

**必要特性**：

| 特性 | 說明 |
|---------------|-------------|
| `LANGUAGE SQL` | 指定實作語言 |
| `SQL SECURITY INVOKER` | 在呼叫者的權限下執行 |

**選用特性**：

| 特性 | 說明 |
|---------------|-------------|
| `NOT DETERMINISTIC` | 程序可能對相同輸入返回不同結果 |
| `MODIFIES SQL DATA` | 程序修改 SQL 資料 |
| `COMMENT 'description'` | 人類可讀的說明 |
| `DEFAULT COLLATION UTF8_BINARY` | 當結構描述使用非 UTF8_BINARY 定序時必要（Runtime 17.1+） |

**規則**：

- `OR REPLACE` 和 `IF NOT EXISTS` 不能組合
- 程序內的參數名稱必須唯一
- `OUT` 參數不支援 `DEFAULT`
- 一旦參數有 `DEFAULT`，所有後續參數也必須有預設值
- 預設表達式不能引用其他參數或包含子查詢
- 主體在建立時進行語法驗證，但僅在呼叫時進行語義驗證

**範例** -- 帶有輸出參數的 ETL 程序：

```sql
CREATE OR REPLACE PROCEDURE run_daily_etl(
    IN source_schema STRING,
    IN target_schema STRING,
    OUT rows_processed INT,
    OUT status STRING DEFAULT 'pending'
)
LANGUAGE SQL
SQL SECURITY INVOKER
COMMENT '訂單處理的每日 ETL 管線'
AS BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
      SET status = 'failed';
      SET rows_processed = 0;
    END;

  -- 截斷並重新載入
  EXECUTE IMMEDIATE 'TRUNCATE TABLE ' || target_schema || '.orders_daily';

  EXECUTE IMMEDIATE
    'INSERT INTO ' || target_schema || '.orders_daily '
    || 'SELECT * FROM ' || source_schema || '.orders '
    || 'WHERE order_date = current_date()';

  EXECUTE IMMEDIATE
    'SELECT COUNT(*) FROM ' || target_schema || '.orders_daily'
    INTO rows_processed;

  SET status = 'success';
END;
```

### CALL（呼叫程序）

**語法**：

```sql
CALL procedure_name( [ argument [, ...] ] );
CALL procedure_name( [ named_param => argument ] [, ...] );
```

**規則**：

- 支援最多 64 層巢狀
- 對於 `IN` 參數：任何可轉換為參數類型的表達式，或 `DEFAULT`
- 對於 `OUT`/`INOUT` 參數：必須是工作階段變數或本地變數
- 引數必須匹配參數的資料類型（使用類型化字面值，例如 `DATE'2025-01-01'`）
- 如果剩餘參數有 `DEFAULT` 值，則允許較少的引數
- 不支援透過 ODBC

**範例**：

```sql
-- 位置呼叫
DECLARE rows_out INT;
DECLARE status_out STRING;
CALL run_daily_etl('raw', 'silver', rows_out, status_out);
SELECT rows_out, status_out;

-- 命名參數呼叫
CALL run_daily_etl(
  target_schema => 'silver',
  source_schema => 'raw',
  rows_processed => rows_out,
  status => status_out
);
```

### DROP PROCEDURE

**語法**：

```sql
DROP PROCEDURE [ IF EXISTS ] procedure_name;
```

- 沒有 `IF EXISTS` 時，刪除不存在的程序會引發 `ROUTINE_NOT_FOUND`
- 需要 `MANAGE` 權限、程序的所有權，或包含的結構描述/目錄/metastore 的所有權

**範例**：

```sql
DROP PROCEDURE IF EXISTS run_daily_etl;
```

### DESCRIBE PROCEDURE

**語法**：

```sql
{ DESC | DESCRIBE } PROCEDURE [ EXTENDED ] procedure_name;
```

- 基本：返回程序名稱和參數列表
- `EXTENDED`：另外返回擁有者、建立時間、主體、語言、安全類型、確定性、資料存取和配置

**範例**：

```sql
DESCRIBE PROCEDURE EXTENDED run_daily_etl;
```

### SHOW PROCEDURES

**語法**：

```sql
SHOW PROCEDURES [ { FROM | IN } schema_name ];
```

返回欄位：`catalog`、`namespace`、`schema`、`procedure_name`。

**範例**：

```sql
SHOW PROCEDURES IN my_catalog.my_schema;
```

---

## 遞迴 CTE

**可用性**：Databricks Runtime 17.0+ 和 DBSQL 2025.20+

遞迴 CTE 啟用自我引用查詢，用於階層資料、圖形遍歷和序列生成。

### WITH RECURSIVE 語法

```sql
WITH RECURSIVE cte_name [ ( column_name [, ...] ) ]
  [ MAX RECURSION LEVEL max_level ] AS (
    base_case_query
    UNION ALL
    recursive_query
  )
SELECT ... FROM cte_name;
```

### 錨點和遞迴成員

| 元件 | 說明 |
|-----------|-------------|
| **錨點（基本案例）** | 提供種子列的初始查詢；不得引用 CTE 名稱 |
| **遞迴成員** | 引用 CTE 名稱；處理前一次迭代的列 |
| **UNION ALL** | 組合錨點和遞迴結果（必要） |

遞迴成員讀取前一次迭代產生的列並生成新列。當遞迴成員產生零列時，遞迴終止。

### MAX RECURSION LEVEL

```sql
WITH RECURSIVE cte_name MAX RECURSION LEVEL 200 AS (...)
```

| 設定 | 預設值 | 說明 |
|---------|---------|-------------|
| 最大遞迴深度 | 100 | 超過會引發 `RECURSION_LEVEL_LIMIT_EXCEEDED` |
| 最大結果列數 | 1,000,000 | 超過會引發錯誤 |
| `LIMIT ALL` | N/A | 暫停列限制（Runtime 17.2+） |

### 使用案例和範例

**生成數字序列**：

```sql
WITH RECURSIVE numbers(n) AS (
  VALUES (1)
  UNION ALL
  SELECT n + 1 FROM numbers WHERE n < 100
)
SELECT * FROM numbers;
```

**組織階層遍歷**：

```sql
WITH RECURSIVE org_tree AS (
  -- 錨點：從 CEO 開始
  SELECT employee_id, name, manager_id, name AS root_name, 0 AS depth
  FROM employees
  WHERE manager_id IS NULL

  UNION ALL

  -- 遞迴：尋找直接下屬
  SELECT e.employee_id, e.name, e.manager_id, t.root_name, t.depth + 1
  FROM employees e
  JOIN org_tree t ON e.manager_id = t.employee_id
)
SELECT * FROM org_tree ORDER BY depth, name;
```

**帶有循環偵測的圖形遍歷**：

```sql
WITH RECURSIVE search_graph(f, t, label, path, cycle) AS (
  -- 錨點：所有邊作為起始路徑
  SELECT *, array(struct(g.f, g.t)), false
  FROM graph g

  UNION ALL

  -- 遞迴：擴展路徑，偵測循環
  SELECT g.f, g.t, g.label,
         sg.path || array(struct(g.f, g.t)),
         array_contains(sg.path, struct(g.f, g.t))
  FROM graph g
  JOIN search_graph sg ON g.f = sg.t
  WHERE NOT sg.cycle
)
SELECT * FROM search_graph WHERE NOT cycle;
```

**字串累積**：

```sql
WITH RECURSIVE r(col) AS (
  SELECT 'a'
  UNION ALL
  SELECT col || char(ascii(substr(col, -1)) + 1)
  FROM r
  WHERE length(col) < 10
)
SELECT * FROM r;
-- a, ab, abc, abcd, ..., abcdefghij
```

**物料清單（BOM）展開**：

```sql
WITH RECURSIVE bom AS (
  -- 錨點：頂層產品
  SELECT part_id, component_id, quantity, 1 AS level
  FROM bill_of_materials
  WHERE part_id = 'PROD-001'

  UNION ALL

  -- 遞迴：子元件
  SELECT b.part_id, b.component_id, b.quantity * bom.quantity, bom.level + 1
  FROM bill_of_materials b
  JOIN bom ON b.part_id = bom.component_id
)
SELECT component_id, SUM(quantity) AS total_quantity, MAX(level) AS max_depth
FROM bom
GROUP BY component_id
ORDER BY total_quantity DESC;
```

### 限制

- 不支援在 UPDATE、DELETE 或 MERGE 陳述式中使用
- 步驟（遞迴）查詢不能包含對 CTE 名稱的相關欄位引用
- 隨機數生成器可能在迭代中產生相同的值
- 預設列限制為 1,000,000 列（在 Runtime 17.2+ 中使用 `LIMIT ALL` 覆寫）
- 預設遞迴深度為 100（使用 `MAX RECURSION LEVEL` 覆寫）

---

## 多陳述式交易

### 概述和目前狀態

多陳述式交易（MST）允許將多個 SQL 陳述式分組為原子單位，這些單位要麼完全成功，要麼完全失敗。

| 功能 | 狀態 | 備註 |
|---------|--------|-------|
| 單資料表交易 | GA | Delta Lake 預設；每個 DML 陳述式都是原子的 |
| 多陳述式交易（SQL 腳本） | 預覽版 | `BEGIN ATOMIC...END` 區塊 |
| 多陳述式交易（Python 連接器） | 預覽版 | `connection.autocommit = False` 模式 |
| 跨資料表交易 | 預覽版 | 跨多個 Delta 資料表的原子更新 |

### SQL 腳本原子區塊

使用 `BEGIN ATOMIC...END` 將多個陳述式作為單一原子單位執行：

```sql
BEGIN ATOMIC
  INSERT INTO customers (id, name) VALUES (1, 'Alice');
  INSERT INTO orders (id, customer_id, amount) VALUES (1, 1, 250.00);
  INSERT INTO audit_log (action, ts) VALUES ('new_customer_order', current_timestamp());
END;
```

如果任何陳述式失敗，所有變更都會回滾。

> **注意：**在 `BEGIN ATOMIC` 區塊中使用的資料表必須啟用 `catalogManaged` 資料表功能。使用 `TBLPROPERTIES ('delta.feature.catalogManaged' = 'supported')` 建立資料表。現有資料表無法就地升級 — 必須使用此屬性重新建立。

### Python 連接器交易 API

Databricks SQL Connector for Python 提供明確的交易控制：

```python
from databricks import sql

connection = sql.connect(
    server_hostname="...",
    http_path="...",
    access_token="..."
)

# 停用自動提交以開始明確交易
connection.autocommit = False
cursor = connection.cursor()

try:
    cursor.execute("INSERT INTO customers VALUES (1, 'Alice')")
    cursor.execute("INSERT INTO orders VALUES (1, 1, 100.00)")
    cursor.execute("INSERT INTO shipments VALUES (1, 1, 'pending')")
    connection.commit()    # 三個陳述式原子性成功
except Exception:
    connection.rollback()  # 三個陳述式都被丟棄
finally:
    connection.autocommit = True
```

**關鍵 API 方法**：

| 方法 | 說明 |
|--------|-------------|
| `connection.autocommit = False` | 開始明確交易模式 |
| `connection.commit()` | 提交目前交易 |
| `connection.rollback()` | 丟棄目前交易中的所有變更 |
| `connection.get_transaction_isolation()` | 返回目前隔離層級 |
| `connection.set_transaction_isolation(level)` | 設定隔離層級 |

**錯誤處理**：

- 在沒有活躍交易時提交會引發 `sql.TransactionError`
- 當交易處於活躍狀態時無法變更 `autocommit`
- 當沒有活躍交易時，`rollback()` 是安全的無操作

### 隔離層級

Databricks 使用**快照隔離**（在標準 SQL 術語中對應到 `REPEATABLE_READ`）。

| 層級 | 說明 | 預設 |
|-------|-------------|---------|
| `WriteSerializable` | 只有寫入是可序列化的；並行寫入可能重新排序 | 是（資料表預設） |
| `Serializable` | 讀取和寫入都是可序列化的；最嚴格的隔離 | 否 |
| `REPEATABLE_READ` | 連接器層級交易的快照隔離 | 連接器預設 |

**在資料表層級設定隔離**：

```sql
ALTER TABLE my_table
SET TBLPROPERTIES ('delta.isolationLevel' = 'Serializable');
```

**在 Python 連接器中設定隔離**：

```python
from databricks.sql import TRANSACTION_ISOLATION_LEVEL_REPEATABLE_READ

connection.set_transaction_isolation(TRANSACTION_ISOLATION_LEVEL_REPEATABLE_READ)
# 僅支援 REPEATABLE_READ；其他會引發 NotSupportedError
```

**快照隔離行為**：

- **可重複讀取**：交易內讀取的資料保持一致
- **原子提交**：變更在提交前對其他連接不可見
- **寫入衝突**：對同一資料表的並行寫入會導致衝突
- **跨資料表寫入**：對不同資料表的並行寫入可以成功

### 寫入衝突和並行性

**列層級並行性**（Runtime 14.2+）減少具有刪除向量或 liquid clustering 的資料表的衝突：

| 操作 | WriteSerializable | Serializable |
|-----------|------------------|--------------|
| INSERT vs INSERT | 無衝突 | 無衝突 |
| UPDATE/DELETE/MERGE vs 相同 | 無衝突（不同列） | 可能衝突 |
| OPTIMIZE vs 並行 DML | 僅與 ZORDER BY 衝突 | 可能衝突 |

**常見衝突例外**：

| 例外 | 原因 |
|-----------|-------|
| `ConcurrentAppendException` | 並行附加到同一分割區 |
| `ConcurrentDeleteReadException` | 並行刪除正在讀取的檔案 |
| `MetadataChangedException` | 並行 ALTER TABLE 或結構描述變更 |
| `ProtocolChangedException` | 寫入期間的協定版本升級 |

### 最佳實踐

1. **保持交易簡短**以最小化衝突視窗
2. **始終使用 try/except/finally 包裝**，錯誤時回滾
3. **在 `finally` 區塊中恢復自動提交**
4. **在 MERGE 條件中使用分割區修剪**以減少衝突範圍
5. **啟用列層級並行性**（刪除向量 + liquid clustering）用於高並行工作負載
6. **在更新單一資料表時優先使用單陳述式 MERGE** 而非多陳述式交易
7. **提交並重新啟動**交易以查看其他連接所做的變更

---

## Runtime 版本參考

| 功能 | 最低 Runtime | 狀態 |
|---------|----------------|--------|
| SQL 腳本（複合陳述式、控制流程） | 16.3 | GA |
| 預存程序（CREATE/CALL/DROP PROCEDURE） | 17.0 | 公開預覽版 |
| 遞迴 CTE（WITH RECURSIVE） | 17.0 / DBSQL 2025.20 | GA |
| 多變數 DECLARE | 17.2 | GA |
| EXECUTE IMMEDIATE（基本） | 14.3 | GA |
| EXECUTE IMMEDIATE（表達式、巢狀） | 17.3 | GA |
| 遞迴 CTE LIMIT ALL | 17.2 | GA |
| 多陳述式交易 | 不同 | 預覽版 |
| 列層級並行性 | 14.2 | GA |

---

## 快速參考卡

### SQL 腳本骨架

```sql
BEGIN
  -- 1. 宣告
  DECLARE var1 INT DEFAULT 0;
  DECLARE var2 STRING;
  DECLARE my_error CONDITION FOR SQLSTATE '45000';
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
      -- 錯誤處理邏輯
    END;

  -- 2. 邏輯
  IF var1 > 0 THEN
    SET var2 = 'positive';
  ELSE
    SET var2 = 'non-positive';
  END IF;

  -- 3. 輸出
  VALUES (var1, var2);
END;
```

### 預存程序骨架

```sql
CREATE OR REPLACE PROCEDURE my_schema.my_proc(
    IN  input_param STRING,
    OUT output_param INT
)
LANGUAGE SQL
SQL SECURITY INVOKER
COMMENT '此程序功能的說明'
AS BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
    SET output_param = -1;

  -- 程序主體
  SET output_param = (SELECT COUNT(*) FROM my_table WHERE col = input_param);
END;

-- 呼叫
DECLARE result INT;
CALL my_schema.my_proc('value', result);
SELECT result;
```

### 遞迴 CTE 骨架

```sql
WITH RECURSIVE cte_name (col1, col2) MAX RECURSION LEVEL 50 AS (
  -- 錨點
  SELECT seed_col1, seed_col2
  FROM base_table
  WHERE condition

  UNION ALL

  -- 遞迴步驟
  SELECT derived_col1, derived_col2
  FROM source_table s
  JOIN cte_name c ON s.parent = c.col1
)
SELECT * FROM cte_name;
```
