# Metric View YAML 參考 (Metric View YAML Reference)

Unity Catalog Metric Views 使用的 YAML 規範完整參考。

## 頂層欄位

| 欄位 | 必要 | 類型 | 描述 |
|-------|----------|------|-------------|
| `version` | 否 | string | YAML 規範版本。DBR 17.2+ 為 `"1.1"`，DBR 16.4-17.1 為 `"0.1"`。預設為 `1.1`。|
| `source` | 是 | string | 三層命名空間格式的來源資料表、視圖或 SQL 查詢。 |
| `comment` | 否 | string | Metric View 的描述 (v1.1+)。 |
| `filter` | 否 | string | 作為全域 WHERE 子句應用的 SQL 布林表達式。 |
| `dimensions` | 是 | list | 維度定義陣列 (至少一個)。 |
| `measures` | 是 | list | 度量定義陣列 (至少一個)。 |
| `joins` | 否 | list | 星狀/雪花架構聯結定義。 |
| `materialization` | 否 | object | 預先計算配置 (實驗性)。 |

## 維度 (Dimensions)

維度定義用於分組和過濾資料的分類屬性。

```yaml
dimensions:
  - name: Region               # 顯示名稱，查詢中使用反引號引用
    expr: region_name           # 直接欄位參考
    comment: "Sales region"     # 選用描述 (v1.1+)

  - name: Order Month
    expr: DATE_TRUNC('MONTH', order_date)  # SQL 轉換

  - name: Order Year
    expr: EXTRACT(YEAR FROM `Order Month`)  # 可以參考其他維度

  - name: Customer Type
    expr: CASE
      WHEN customer_tier = 'A' THEN 'Enterprise'
      WHEN customer_tier = 'B' THEN 'Mid-Market'
      ELSE 'SMB'
      END                      # 支援多行 CASE 表達式

  - name: Nation
    expr: customer.c_name      # 參考聯結資料表的欄位
```

### 維度規則

- `name` 是必要的，並成為查詢中的欄位名稱 (若包含空格需用反引號引用)
- `expr` 是必要的，且必須是有效的 SQL 表達式
- 可以參考來源欄位、SQL 函數、CASE 表達式和其他維度
- 可以使用 `join_name.column_name` 參考聯結資料表中的欄位
- 不能使用聚合函數 (那些屬於度量)

## 度量 (Measures)

度量定義在查詢時計算的聚合值。

```yaml
measures:
  - name: Total Revenue
    expr: SUM(total_price)
    comment: "Sum of all order prices"

  - name: Order Count
    expr: COUNT(1)

  - name: Average Order Value
    expr: AVG(total_price)

  - name: Unique Customers
    expr: COUNT(DISTINCT customer_id)

  - name: Revenue per Customer           # 比率度量
    expr: SUM(total_price) / COUNT(DISTINCT customer_id)

  - name: Open Order Revenue             # 過濾後的度量
    expr: SUM(total_price) FILTER (WHERE status = 'O')
    comment: "Revenue from open orders only"

  - name: Open Revenue per Customer      # 過濾後的比率
    expr: SUM(total_price) FILTER (WHERE status = 'O') / COUNT(DISTINCT customer_id) FILTER (WHERE status = 'O')
```

### 視窗度量 (實驗性)

在度量中新增 `window` 區塊以進行視窗化、累計或半可加聚合。請參閱 [Window Measures Documentation](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures)。

```yaml
measures:
  - name: Running Total
    expr: SUM(total_price)
    window:
      - order: date              # 決定視窗排序的維度
        range: cumulative        # 視窗範圍 (見下方範圍值)
        semiadditive: last       # 當排序維度不在 GROUP BY 中時如何匯總

  - name: 7-Day Customers
    expr: COUNT(DISTINCT customer_id)
    window:
      - order: date
        range: trailing 7 day    # 當前日之前的 7 天，不包含當日
        semiadditive: last
```

**視窗範圍值：**

| 範圍 (Range) | 描述 |
|-------|-------------|
| `current` | 僅匹配當前排序值的資料列 |
| `cumulative` | 直至並包含當前列的所有資料列 |
| `trailing <N> <unit>` | 當前列之前的 N 個單位 (不包含當前列) |
| `leading <N> <unit>` | 當前列之後的 N 個單位 |
| `all` | 所有資料列 |

**視窗規範欄位：**

| 欄位 | 必要 | 描述 |
|-------|----------|-------------|
| `order` | 是 | 決定視窗排序的維度名稱 |
| `range` | 是 | 視窗範圍 (見上表) |
| `semiadditive` | 是 | `first` 或 `last` - 當排序維度不在 GROUP BY 中時使用的值 |

**多個視窗** 可以組合在單一度量上 (例如，用於年初至今)：

```yaml
  - name: ytd_sales
    expr: SUM(total_price)
    window:
      - order: date
        range: cumulative
        semiadditive: last
      - order: year
        range: current
        semiadditive: last
```

**衍生度量** 可以使用 `MEASURE()` 參考視窗度量：

```yaml
  - name: day_over_day_growth
    expr: (MEASURE(current_day_sales) - MEASURE(previous_day_sales)) / MEASURE(previous_day_sales) * 100
```

### 度量規則

- `name` 是必要的，並透過 `MEASURE(\`name\`)` 查詢
- `expr` 必須包含聚合函數 (SUM, COUNT, AVG, MIN, MAX 等)
- 支援 `FILTER (WHERE ...)` 進行條件聚合
- 支援聚合的比率
- 衍生度量可以透過 `MEASURE()` 參考其他度量 (與視窗度量一起使用)
- 視窗度量使用 `version: 0.1` (實驗性功能)
- 不支援 `SELECT *`；必須明確使用 `MEASURE()`

## 聯結 (Joins)

### 星狀架構 (單層)

```yaml
source: catalog.schema.fact_orders
joins:
  - name: customer
    source: catalog.schema.dim_customer
    on: source.customer_id = customer.id

  - name: product
    source: catalog.schema.dim_product
    on: source.product_id = product.id
```

### 使用 USING 的星狀架構

```yaml
joins:
  - name: customer
    source: catalog.schema.dim_customer
    using:
      - customer_id
      - region_id
```

### 雪花架構 (巢狀聯結, DBR 17.1+)

```yaml
source: catalog.schema.orders
joins:
  - name: customer
    source: catalog.schema.customer
    on: source.customer_id = customer.id
    joins:
      - name: nation
        source: catalog.schema.nation
        on: customer.nation_id = nation.id
        joins:
          - name: region
            source: catalog.schema.region
            on: nation.region_id = region.id
```

### 聯結規則

- `name` 是必要的，用於參考聯結欄位：`name.column`
- `source` 是全限定的資料表/視圖名稱
- 使用 `on` (表達式) 或 `using` (欄位列表)，兩者擇一
- 在 `on` 中，將事實資料表參照為 `source`，並依其 `name` 參照聯結資料表
- 巢狀 `joins` 建立雪花架構 (需要 DBR 17.1+)
- 聯結的資料表不能包含 MAP 類型的欄位

## 過濾器 (Filter)

作為 WHERE 子句應用於所有查詢的全域過濾器。

```yaml
filter: order_date > '2020-01-01'

# 多個條件
filter: order_date > '2020-01-01' AND status != 'CANCELLED'

# 使用聯結欄位
filter: customer.active = true
```

## 具體化 (Materialization) (實驗性)

預先計算聚合以加快查詢效能。底層使用 Lakeflow Spark Declarative Pipelines。

```yaml
materialization:
  schedule: every 6 hours           # 與 MV schedule 子句語法相同
  mode: relaxed                     # 目前僅支援 "relaxed"

  materialized_views:
    - name: baseline
      type: unaggregated            # 完整的未聚合資料模型
    
    - name: revenue_breakdown
      type: aggregated              # 預先計算的聚合
      dimensions:
        - category
        - region
      measures:
        - total_revenue
        - order_count

    - name: daily_summary
      type: aggregated
      dimensions:
        - order_date
      measures:
        - total_revenue
```

### 具體化類型

| 類型 | 描述 | 何時使用 |
|------|-------------|-------------|
| `unaggregated` | 具體化完整的資料模型 (來源 + 聯結 + 過濾器) | 昂貴的來源視圖或多個聯結 |
| `aggregated` | 預先計算特定的維度/度量組合 | 經常查詢的組合 |

### 具體化需求

- 必須啟用 Serverless Compute
- Databricks Runtime 17.2+
- 不支援 `TRIGGER ON UPDATE` 子句
- 排程使用與 Materialized View 排程相同的語法

### 重新整理具體化

```python
# 尋找並重新整理管線
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
pipeline_id = "your-pipeline-id"
w.pipelines.start_update(pipeline_id)
```

## 完整範例

```sql
CREATE OR REPLACE VIEW catalog.schema.sales_metrics
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: "Comprehensive sales metrics with customer and product dimensions"
  source: catalog.schema.fact_sales
  filter: sale_date >= '2023-01-01'

  joins:
    - name: customer
      source: catalog.schema.dim_customer
      on: source.customer_id = customer.id
      joins:
        - name: region
          source: catalog.schema.dim_region
          on: customer.region_id = region.id
    - name: product
      source: catalog.schema.dim_product
      on: source.product_id = product.id

  dimensions:
    - name: Sale Month
      expr: DATE_TRUNC('MONTH', sale_date)
      comment: "Month of sale"
    - name: Customer Name
      expr: customer.name
    - name: Region
      expr: region.name
      comment: "Geographic region"
    - name: Product Category
      expr: product.category

  measures:
    - name: Total Revenue
      expr: SUM(amount)
      comment: "Sum of sale amounts"
    - name: Transaction Count
      expr: COUNT(1)
    - name: Unique Customers
      expr: COUNT(DISTINCT customer_id)
    - name: Average Transaction
      expr: AVG(amount)
    - name: Revenue per Customer
      expr: SUM(amount) / COUNT(DISTINCT customer_id)
      comment: "Average revenue per unique customer"

  materialization:
    schedule: every 1 hour
    mode: relaxed
    materialized_views:
      - name: hourly_region
        type: aggregated
        dimensions:
          - Sale Month
          - Region
        measures:
          - Total Revenue
          - Transaction Count
$$
```
