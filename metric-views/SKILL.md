---
name: metric-views
description: "Unity Catalog Metric Views: 使用 YAML 定義、建立、查詢和管理受治理的業務指標。用於建構標準化 KPI、收入指標、訂單分析，或任何需要在團隊和工具之間保持一致定義的可重複使用業務指標。"
---

# Unity Catalog Metric Views

使用 YAML 定義可重複使用、受治理的業務指標，將度量定義與維度分組分離，以實現靈活的查詢。

## 何時使用

當您需要以下功能時，請使用此技能：
- 定義 **標準化業務指標** (收入、訂單計數、轉換率)
- 建構跨儀表板、Genie 和 SQL 查詢共用的 **KPI 層**
- 建立具有 **複雜聚合** (比率、不重複計數、過濾後的度量) 的指標
- 定義 **視窗度量** (移動平均、累計總和、期間比較、年初至今)
- 模型化 **星狀或雪花架構**，並在指標定義中包含聯結
- 啟用 **具體化 (Materialization)** 以預先計算指標聚合

## 先決條件

- **Databricks Runtime 17.2+** (適用於 YAML 1.1 版本)
- 具有 `CAN USE` 權限的 SQL Warehouse
- 來源資料表的 `SELECT` 權限，以及目標結構描述中的 `CREATE TABLE` + `USE SCHEMA` 權限

## 快速開始

### 建立 Metric View

```sql
CREATE OR REPLACE VIEW catalog.schema.orders_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Orders KPIs for sales analysis"
  source: catalog.schema.orders
  filter: order_date > '2020-01-01'
  dimensions:
    - name: Order Month
      expr: DATE_TRUNC('MONTH', order_date)
      comment: "Month of order"
    - name: Order Status
      expr: CASE
        WHEN status = 'O' THEN 'Open'
        WHEN status = 'P' THEN 'Processing'
        WHEN status = 'F' THEN 'Fulfilled'
        END
      comment: "Human-readable order status"
  measures:
    - name: Order Count
      expr: COUNT(1)
    - name: Total Revenue
      expr: SUM(total_price)
      comment: "Sum of total price"
    - name: Revenue per Customer
      expr: SUM(total_price) / COUNT(DISTINCT customer_id)
      comment: "Average revenue per unique customer"
$$
```

### 查詢 Metric View

所有度量必須使用 `MEASURE()` 函數。不支援 `SELECT *`。

```sql
SELECT
  `Order Month`,
  `Order Status`,
  MEASURE(`Total Revenue`) AS total_revenue,
  MEASURE(`Order Count`) AS order_count
FROM catalog.schema.orders_metrics
WHERE extract(year FROM `Order Month`) = 2024
GROUP BY ALL
ORDER BY ALL
```

## 參考檔案

| 主題 | 檔案 | 描述 |
|-------|------|-------------|
| YAML 語法 | [yaml-reference.md](yaml-reference.md) | 完整的 YAML 規範：維度、度量、聯結、具體化 |
| 模式與範例 | [patterns.md](patterns.md) | 常見模式：星狀架構、雪花架構、過濾後的度量、視窗度量、比率 |

## MCP 工具

使用 `manage_metric_views` 工具進行所有 Metric View 操作：

| 動作 | 描述 |
|--------|-------------|
| `create` | 建立包含維度和度量的 Metric View |
| `alter` | 更新 Metric View 的 YAML 定義 |
| `describe` | 獲取完整的定義和詮釋資料 |
| `query` | 查詢依維度分組的度量 |
| `drop` | 刪除 Metric View |
| `grant` | 授予使用者/群組 SELECT 權限 |

### 透過 MCP 建立

```python
manage_metric_views(
    action="create",
    full_name="catalog.schema.orders_metrics",
    source="catalog.schema.orders",
    or_replace=True,
    comment="Orders KPIs for sales analysis",
    filter_expr="order_date > '2020-01-01'",
    dimensions=[
        {"name": "Order Month", "expr": "DATE_TRUNC('MONTH', order_date)", "comment": "Month of order"},
        {"name": "Order Status", "expr": "status"},
    ],
    measures=[
        {"name": "Order Count", "expr": "COUNT(1)"},
        {"name": "Total Revenue", "expr": "SUM(total_price)", "comment": "Sum of total price"},
    ],
)
```

### 透過 MCP 查詢

```python
manage_metric_views(
    action="query",
    full_name="catalog.schema.orders_metrics",
    query_measures=["Total Revenue", "Order Count"],
    query_dimensions=["Order Month"],
    where="extract(year FROM `Order Month`) = 2024",
    order_by="ALL",
    limit=100,
)
```

### 透過 MCP 描述

```python
manage_metric_views(
    action="describe",
    full_name="catalog.schema.orders_metrics",
)
```

### 授予權限

```python
manage_metric_views(
    action="grant",
    full_name="catalog.schema.orders_metrics",
    principal="data-consumers",
    privileges=["SELECT"],
)
```

## YAML 規範快速參考

```yaml
version: 1.1                    # 必要: DBR 17.2+ 使用 "1.1"
comment: "Description"          # 選用: Metric View 描述
source: catalog.schema.table    # 必要: 來源資料表/視圖
filter: column > value          # 選用: 全域 WHERE 過濾器

dimensions:                     # 必要: 至少一個
  - name: Display Name          # 在查詢中使用反引號引用
    expr: sql_expression        # 欄位參考或 SQL 轉換
    comment: "Description"      # 選用 (v1.1+)

measures:                       # 必要: 至少一個
  - name: Display Name          # 透過 MEASURE(`name`) 查詢
    expr: AGG_FUNC(column)      # 必須是聚合表達式
    comment: "Description"      # 選用 (v1.1+)

joins:                          # 選用: 星狀/雪花架構
  - name: dim_table
    source: catalog.schema.dim_table
    on: source.fk = dim_table.pk

materialization:                # 選用 (實驗性)
  schedule: every 6 hours
  mode: relaxed
```

## 關鍵概念

### 維度與度量

| | 維度 (Dimensions) | 度量 (Measures) |
|---|---|---|
| **目的** | 對資料進行分類和分組 | 聚合數值 |
| **範例** | 地區、日期、狀態 | SUM(revenue), COUNT(orders) |
| **在查詢中** | 用於 SELECT 和 GROUP BY | 包裝在 `MEASURE()` 中 |
| **SQL 表達式** | 任何 SQL 表達式 | 必須使用聚合函數 |

### 為何使用 Metric Views 與標準 Views？

| 功能 | 標準 Views | Metric Views |
|---------|---------------|--------------|
| 建立時鎖定聚合 | 是 | 否 - 查詢時靈活聚合 |
| 比率的安全重新聚合 | 否 | 是 |
| 星狀/雪花架構聯結 | 手動 | 在 YAML 中宣告 |
| 具體化 | 需要單獨的 MV | 內建 |
| AI/BI Genie 整合 | 有限 | 原生支援 |

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **不支援 SELECT *** | 必須明確列出維度並對度量使用 MEASURE() |
| **"Cannot resolve column"** | 包含空格的維度/度量名稱需要反引號引用 |
| **查詢時 JOIN 失敗** | 聯結必須在 YAML 定義中，而不是在 SELECT 查詢中 |
| **需要 MEASURE()** | 所有度量參考必須被包裝：`MEASURE(\`name\`)` |
| **DBR 版本錯誤** | YAML v1.1 需要 Runtime 17.2+，v0.1 需要 16.4+ |
| **具體化無法運作** | 需要啟用 Serverless Compute；目前為實驗性功能 |

## 整合

Metric Views 原生支援下列工具：
- **AI/BI Dashboards** - 作為視覺化的資料集
- **AI/BI Genie** - 指標的自然語言查詢
- **Alerts** - 對度量設定基於閾值的警報
- **SQL Editor** - 使用 MEASURE() 直接進行 SQL 查詢
- **Catalog Explorer UI** - 視覺化建立和瀏覽

## 資源

- [Metric Views Documentation](https://docs.databricks.com/en/metric-views/)
- [YAML Syntax Reference](https://docs.databricks.com/en/metric-views/data-modeling/syntax)
- [Joins](https://docs.databricks.com/en/metric-views/data-modeling/joins)
- [Window Measures](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures) (Experimental)
- [Materialization](https://docs.databricks.com/en/metric-views/materialization)
- [MEASURE() Function](https://docs.databricks.com/en/sql/language-manual/functions/measure)
