# Metric View 模式與範例 (Metric View Patterns & Examples)

建立和查詢 Metric View 的常見模式。

## 模式 1：來自單一資料表的簡單指標

最基本的模式，具有直接的欄位維度和標準聚合。

### 建立

```sql
CREATE OR REPLACE VIEW catalog.schema.product_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Product sales metrics"
  source: catalog.schema.sales
  dimensions:
    - name: Product Name
      expr: product_name
    - name: Sale Date
      expr: sale_date
  measures:
    - name: Units Sold
      expr: COUNT(1)
    - name: Total Revenue
      expr: SUM(price * quantity)
    - name: Average Price
      expr: AVG(price)
$$
```

### 查詢

```sql
-- 依產品的收入
SELECT
  `Product Name`,
  MEASURE(`Total Revenue`) AS revenue,
  MEASURE(`Units Sold`) AS units
FROM catalog.schema.product_metrics
GROUP BY ALL
ORDER BY revenue DESC
LIMIT 10

-- 每月趨勢
SELECT
  DATE_TRUNC('MONTH', `Sale Date`) AS month,
  MEASURE(`Total Revenue`) AS revenue
FROM catalog.schema.product_metrics
GROUP BY ALL
ORDER BY month
```

## 模式 2：使用 CASE 的衍生維度

將原始值轉換為商業友好的類別。

```sql
CREATE OR REPLACE VIEW catalog.schema.order_kpis
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: catalog.schema.orders
  dimensions:
    - name: Order Month
      expr: DATE_TRUNC('MONTH', order_date)
    - name: Priority Level
      expr: CASE
        WHEN priority <= 2 THEN 'High'
        WHEN priority <= 4 THEN 'Medium'
        ELSE 'Low'
        END
      comment: "Bucketed priority: High (1-2), Medium (3-4), Low (5)"
    - name: Size Category
      expr: CASE
        WHEN total_amount > 10000 THEN 'Large'
        WHEN total_amount > 1000 THEN 'Medium'
        ELSE 'Small'
        END
  measures:
    - name: Order Count
      expr: COUNT(1)
    - name: Total Amount
      expr: SUM(total_amount)
$$
```

## 模式 3：比率度量

能夠安全處理重新聚合的比率和每單位指標。

```sql
CREATE OR REPLACE VIEW catalog.schema.efficiency_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Efficiency and per-unit metrics"
  source: catalog.schema.transactions
  dimensions:
    - name: Department
      expr: department_name
    - name: Quarter
      expr: DATE_TRUNC('QUARTER', transaction_date)
  measures:
    - name: Total Revenue
      expr: SUM(revenue)
    - name: Total Cost
      expr: SUM(cost)
    - name: Profit Margin
      expr: (SUM(revenue) - SUM(cost)) / SUM(revenue)
      comment: "Profit as percentage of revenue"
    - name: Revenue per Employee
      expr: SUM(revenue) / COUNT(DISTINCT employee_id)
    - name: Average Transaction Size
      expr: SUM(revenue) / COUNT(1)
$$
```

## 模式 4：過濾後的度量 (FILTER 子句)

建立僅計算部分資料列的度量。

```sql
CREATE OR REPLACE VIEW catalog.schema.order_status_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: catalog.schema.orders
  dimensions:
    - name: Order Month
      expr: DATE_TRUNC('MONTH', order_date)
    - name: Region
      expr: region
  measures:
    - name: Total Orders
      expr: COUNT(1)
    - name: Open Orders
      expr: COUNT(1) FILTER (WHERE status = 'OPEN')
    - name: Fulfilled Orders
      expr: COUNT(1) FILTER (WHERE status = 'FULFILLED')
    - name: Open Revenue
      expr: SUM(amount) FILTER (WHERE status = 'OPEN')
      comment: "Revenue at risk from unfulfilled orders"
    - name: Fulfillment Rate
      expr: COUNT(1) FILTER (WHERE status = 'FULFILLED') * 1.0 / COUNT(1)
      comment: "Percentage of orders fulfilled"
$$
```

### 查詢過濾後的度量

```sql
SELECT
  `Order Month`,
  MEASURE(`Total Orders`) AS total,
  MEASURE(`Open Orders`) AS open_orders,
  MEASURE(`Fulfillment Rate`) AS fulfillment_rate
FROM catalog.schema.order_status_metrics
WHERE `Region` = 'EMEA'
GROUP BY ALL
ORDER BY ALL
```

## 模式 5：帶有聯結的星狀架構

將事實資料表聯結到維度資料表。

```sql
CREATE OR REPLACE VIEW catalog.schema.sales_analytics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Sales analytics with customer and product dimensions"
  source: catalog.schema.fact_sales

  joins:
    - name: customer
      source: catalog.schema.dim_customer
      on: source.customer_id = customer.customer_id
    - name: product
      source: catalog.schema.dim_product
      on: source.product_id = product.product_id
    - name: store
      source: catalog.schema.dim_store
      on: source.store_id = store.store_id

  dimensions:
    - name: Customer Segment
      expr: customer.segment
    - name: Product Category
      expr: product.category
    - name: Store City
      expr: store.city
    - name: Sale Month
      expr: DATE_TRUNC('MONTH', source.sale_date)

  measures:
    - name: Total Revenue
      expr: SUM(source.amount)
    - name: Unique Customers
      expr: COUNT(DISTINCT source.customer_id)
    - name: Average Basket Size
      expr: SUM(source.amount) / COUNT(DISTINCT source.transaction_id)
$$
```

## 模式 6：雪花架構 (巢狀聯結)

多層級維度階層。需要 DBR 17.1+。

```sql
CREATE OR REPLACE VIEW catalog.schema.geo_sales
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: catalog.schema.orders

  joins:
    - name: customer
      source: catalog.schema.customer
      on: source.customer_key = customer.customer_key
      joins:
        - name: nation
          source: catalog.schema.nation
          on: customer.nation_key = nation.nation_key
          joins:
            - name: region
              source: catalog.schema.region
              on: nation.region_key = region.region_key

  dimensions:
    - name: Customer Name
      expr: customer.name
    - name: Nation
      expr: nation.name
    - name: Region
      expr: region.name
    - name: Order Year
      expr: EXTRACT(YEAR FROM source.order_date)

  measures:
    - name: Total Revenue
      expr: SUM(source.total_price)
    - name: Order Count
      expr: COUNT(1)
$$
```

### 查詢跨階層級別

```sql
-- 依地區收入 (跨國家和客戶匯總)
SELECT
  `Region`,
  MEASURE(`Total Revenue`) AS revenue
FROM catalog.schema.geo_sales
GROUP BY ALL

-- 特定地區內的國家收入
SELECT
  `Nation`,
  MEASURE(`Total Revenue`) AS revenue,
  MEASURE(`Order Count`) AS orders
FROM catalog.schema.geo_sales
WHERE `Region` = 'EUROPE'
GROUP BY ALL
ORDER BY revenue DESC
```

## 模式 7：具體化 Metric View

預先計算常見聚合以加快查詢速度。

```sql
CREATE OR REPLACE VIEW catalog.schema.ecommerce_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: catalog.schema.transactions

  dimensions:
    - name: Category
      expr: product_category
    - name: Day
      expr: DATE_TRUNC('DAY', transaction_date)
    - name: Channel
      expr: sales_channel

  measures:
    - name: Revenue
      expr: SUM(amount)
    - name: Transactions
      expr: COUNT(1)
    - name: Unique Buyers
      expr: COUNT(DISTINCT customer_id)

  materialization:
    schedule: every 1 hour
    mode: relaxed
    materialized_views:
      - name: daily_category
        type: aggregated
        dimensions:
          - Category
          - Day
        measures:
          - Revenue
          - Transactions
      - name: full_model
        type: unaggregated
$$
```

## 模式 8：使用 samples.tpch 進行快速示範

TPC-H 範例資料集可在所有 Databricks 工作區中使用。

```sql
CREATE OR REPLACE VIEW catalog.schema.tpch_orders_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "TPC-H Orders KPIs - demo metric view"
  source: samples.tpch.orders
  filter: o_orderdate > '1990-01-01'

  dimensions:
    - name: Order Month
      expr: DATE_TRUNC('MONTH', o_orderdate)
      comment: "Month of order"
    - name: Order Status
      expr: CASE
        WHEN o_orderstatus = 'O' THEN 'Open'
        WHEN o_orderstatus = 'P' THEN 'Processing'
        WHEN o_orderstatus = 'F' THEN 'Fulfilled'
        END
      comment: "Status: Open, Processing, or Fulfilled"
    - name: Order Priority
      expr: SPLIT(o_orderpriority, '-')[1]
      comment: "Numeric priority 1-5; 1 is highest"

  measures:
    - name: Order Count
      expr: COUNT(1)
    - name: Total Revenue
      expr: SUM(o_totalprice)
      comment: "Sum of total price"
    - name: Revenue per Customer
      expr: SUM(o_totalprice) / COUNT(DISTINCT o_custkey)
      comment: "Average revenue per distinct customer"
    - name: Open Order Revenue
      expr: SUM(o_totalprice) FILTER (WHERE o_orderstatus = 'O')
      comment: "Potential revenue from open orders"
$$
```

### 示範查詢

```sql
-- 每月收入趨勢
SELECT
  `Order Month`,
  MEASURE(`Total Revenue`)::BIGINT AS revenue,
  MEASURE(`Order Count`) AS orders
FROM catalog.schema.tpch_orders_metrics
WHERE extract(year FROM `Order Month`) = 1995
GROUP BY ALL
ORDER BY ALL

-- 依狀態收入
SELECT
  `Order Status`,
  MEASURE(`Total Revenue`)::BIGINT AS revenue,
  MEASURE(`Revenue per Customer`)::BIGINT AS rev_per_customer
FROM catalog.schema.tpch_orders_metrics
GROUP BY ALL

-- 開放訂單風險評估
SELECT
  `Order Month`,
  MEASURE(`Open Order Revenue`)::BIGINT AS at_risk_revenue,
  MEASURE(`Total Revenue`)::BIGINT AS total_revenue
FROM catalog.schema.tpch_orders_metrics
WHERE extract(year FROM `Order Month`) >= 1995
GROUP BY ALL
ORDER BY ALL
```

## 模式 9：視窗度量 (實驗性)

視窗度量啟用移動平均、累計總和、期間比較和半可加 (semiadditive) 度量。將 `window`區塊新增至任何度量定義。請參閱 [Window Measures Documentation](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures)。

### 視窗範圍值

| 範圍 (Range) | 描述 |
|-------|-------------|
| `current` | 僅視窗排序值等於當前列的資料列 |
| `cumulative` | 直至並包含當前列的所有資料列 |
| `trailing <N> <unit>` | 當前列之前的 N 個單位 (**不包含** 當前列) |
| `leading <N> <unit>` | 當前列之後的 N 個單位 |
| `all` | 無論排序為何的所有資料列 |

### 移動視窗：7 日不重複客戶

```sql
CREATE OR REPLACE VIEW catalog.schema.customer_activity
WITH METRICS
LANGUAGE YAML
AS $$
  version: 0.1
  source: catalog.schema.orders
  filter: order_date > DATE'2024-01-01'

  dimensions:
    - name: date
      expr: order_date

  measures:
    - name: t7d_customers
      expr: COUNT(DISTINCT customer_id)
      window:
        - order: date
          range: trailing 7 day
          semiadditive: last
$$
```

**關鍵：** `trailing 7 day` 包含每個日期之前的 7 天，**不包含** 當前日期。`semiadditive: last` 當 `date` 維度不在 GROUP BY 中時返回最後一個值。

### 累計總和 (Cumulative)

```sql
CREATE OR REPLACE VIEW catalog.schema.cumulative_sales
WITH METRICS
LANGUAGE YAML
AS $$
  version: 0.1
  source: catalog.schema.orders
  filter: order_date > DATE'2024-01-01'

  dimensions:
    - name: date
      expr: order_date

  measures:
    - name: running_total_sales
      expr: SUM(total_price)
      window:
        - order: date
          range: cumulative
          semiadditive: last
$$
```

### 期間比較：日增長率 (Day-Over-Day Growth)

在衍生度量中使用 `MEASURE()` 引用來組合視窗度量。

```sql
CREATE OR REPLACE VIEW catalog.schema.daily_growth
WITH METRICS
LANGUAGE YAML
AS $$
  version: 0.1
  source: catalog.schema.orders
  filter: order_date > DATE'2024-01-01'

  dimensions:
    - name: date
      expr: order_date

  measures:
    - name: previous_day_sales
      expr: SUM(total_price)
      window:
        - order: date
          range: trailing 1 day
          semiadditive: last

    - name: current_day_sales
      expr: SUM(total_price)
      window:
        - order: date
          range: current
          semiadditive: last

    - name: day_over_day_growth
      expr: (MEASURE(current_day_sales) - MEASURE(previous_day_sales)) / MEASURE(previous_day_sales) * 100
$$
```

**關鍵：** 衍生的 `day_over_day_growth` 度量使用 `MEASURE()` 引用其他視窗度量。它不需要自己的 `window` 區塊。

### 年初至今 (組合多個視窗)

單一度量可以有多個視窗規範，以建立期間至今 (period-to-date) 的計算。

```sql
CREATE OR REPLACE VIEW catalog.schema.ytd_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 0.1
  source: catalog.schema.orders
  filter: order_date > DATE'2023-01-01'

  dimensions:
    - name: date
      expr: order_date
    - name: year
      expr: DATE_TRUNC('year', order_date)

  measures:
    - name: ytd_sales
      expr: SUM(total_price)
      window:
        - order: date
          range: cumulative
          semiadditive: last
        - order: year
          range: current
          semiadditive: last
$$
```

**關鍵：** 第一個視窗對 `date` 進行累計總和。第二個視窗將範圍限制為 `current` 年。它們一起產生年初至今的結果。

### 半可加度量：銀行餘額

對於像餘額這樣不應跨時間加總的度量。

```sql
CREATE OR REPLACE VIEW catalog.schema.account_balances
WITH METRICS
LANGUAGE YAML
AS $$
  version: 0.1
  source: catalog.schema.daily_balances

  dimensions:
    - name: date
      expr: date
    - name: customer
      expr: customer_id

  measures:
    - name: balance
      expr: SUM(balance)
      window:
        - order: date
          range: current
          semiadditive: last
$$
```

**關鍵：** `semiadditive: last` 防止跨日期加總 (而是返回最後日期的值)，但度量 **仍然跨其他維度聚合**，如 `customer`。當按日期分組時，您會得到當天所有客戶的總餘額。當不按日期分組時，您會得到最近日期的餘額。

### 查詢視窗度量

視窗度量使用相同的 `MEASURE()` 語法進行查詢：

```sql
SELECT
  date,
  MEASURE(t7d_customers) AS trailing_7d_customers,
  MEASURE(running_total_sales) AS running_total
FROM catalog.schema.customer_activity
WHERE date >= DATE'2024-06-01'
GROUP BY ALL
ORDER BY ALL
```

## MCP 工具範例

### 建立 (包含聯結)

```python
manage_metric_views(
    action="create",
    full_name="catalog.schema.sales_metrics",
    source="catalog.schema.fact_sales",
    or_replace=True,
    joins=[
        {
            "name": "customer",
            "source": "catalog.schema.dim_customer",
            "on": "source.customer_id = customer.id"
        },
        {
            "name": "product",
            "source": "catalog.schema.dim_product",
            "on": "source.product_id = product.id"
        }
    ],
    dimensions=[
        {"name": "Customer Segment", "expr": "customer.segment"},
        {"name": "Product Category", "expr": "product.category"},
        {"name": "Sale Month", "expr": "DATE_TRUNC('MONTH', source.sale_date)"},
    ],
    measures=[
        {"name": "Total Revenue", "expr": "SUM(source.amount)"},
        {"name": "Order Count", "expr": "COUNT(1)"},
        {"name": "Unique Customers", "expr": "COUNT(DISTINCT source.customer_id)"},
    ],
)
```

### 修改 (Alter) 以新增度量

```python
manage_metric_views(
    action="alter",
    full_name="catalog.schema.sales_metrics",
    source="catalog.schema.fact_sales",
    joins=[
        {"name": "customer", "source": "catalog.schema.dim_customer", "on": "source.customer_id = customer.id"},
    ],
    dimensions=[
        {"name": "Customer Segment", "expr": "customer.segment"},
        {"name": "Sale Month", "expr": "DATE_TRUNC('MONTH', source.sale_date)"},
    ],
    measures=[
        {"name": "Total Revenue", "expr": "SUM(source.amount)"},
        {"name": "Order Count", "expr": "COUNT(1)"},
        {"name": "Average Order Value", "expr": "AVG(source.amount)"},  # New measure
    ],
)
```

### 帶有過濾器的查詢

```python
manage_metric_views(
    action="query",
    full_name="catalog.schema.sales_metrics",
    query_measures=["Total Revenue", "Order Count"],
    query_dimensions=["Customer Segment", "Sale Month"],
    where="`Customer Segment` = 'Enterprise'",
    order_by="ALL",
    limit=50,
)
```
