# 常見查詢模式

以下是一些用於 FinOps 分析的常用 SQL 查詢模式。

## 📊 基本成本摘要（最近 30 天）- 優化版

```sql
-- 使用 year_month 分區過濾提升效能
WITH recent_months AS (
  SELECT DISTINCT year_month 
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
)
SELECT 
  ConsumedService,
  cost_category,
  SUM(total_cost) AS total_cost,
  COUNT(DISTINCT date_key) AS days_active,
  ROUND(SUM(total_cost) / COUNT(DISTINCT date_key), 2) AS avg_daily_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month IN (SELECT year_month FROM recent_months)
  AND date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
GROUP BY ConsumedService, cost_category
ORDER BY total_cost DESC
LIMIT 10;
```

## 📈 月度趨勢（最近 6 個月）- 含成長率

```sql
WITH monthly_costs AS (
  SELECT 
    year_month,
    SUM(total_cost) AS monthly_cost,
    SUM(reservation_cost) AS reserved_cost,
    SUM(spot_cost) AS spot_cost,
    SUM(savingplan_cost) AS saving_plan_cost,
    SUM(on_demand_cost) AS on_demand_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
  GROUP BY year_month
)
SELECT 
  year_month,
  monthly_cost,
  reserved_cost,
  spot_cost,
  saving_plan_cost,
  on_demand_cost,
  ROUND(((reserved_cost + saving_plan_cost) / NULLIF(monthly_cost, 0)) * 100, 2) AS commitment_coverage_pct,
  ROUND(monthly_cost - LAG(monthly_cost) OVER (ORDER BY year_month), 2) AS mom_change,
  ROUND(((monthly_cost - LAG(monthly_cost) OVER (ORDER BY year_month)) / 
         NULLIF(LAG(monthly_cost) OVER (ORDER BY year_month), 0)) * 100, 2) AS mom_change_pct
FROM monthly_costs
ORDER BY year_month DESC;
```

## 🏢 資源群組分配（當月）- 含排名

```sql
WITH rg_costs AS (
  SELECT 
    ResourceGroup,
    tag_environment,
    SUM(total_cost) AS monthly_cost
  FROM develop_catalog.system_report.finops_resource_group_monthly
  WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  GROUP BY ResourceGroup, tag_environment
)
SELECT 
  ROW_NUMBER() OVER (ORDER BY monthly_cost DESC) AS rank,
  ResourceGroup,
  tag_environment,
  ROUND(monthly_cost, 2) AS monthly_cost,
  ROUND(monthly_cost / SUM(monthly_cost) OVER () * 100, 2) AS cost_share_pct,
  ROUND(SUM(monthly_cost) OVER (ORDER BY monthly_cost DESC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / 
        SUM(monthly_cost) OVER () * 100, 2) AS cumulative_pct
FROM rg_costs
ORDER BY monthly_cost DESC
LIMIT 20;
```

## 🔮 智能預測：下個月成本預估 (Linear Regression)

利用線性回歸模型，基於過去 60 天的數據預測未來 30 天的成本趨勢。

```sql
WITH daily_trend AS (
  SELECT 
    -- 轉換日期為數值 (X 軸)
    DATEDIFF(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd'), DATE_SUB(CURRENT_DATE(), 60)) AS x,
    SUM(total_cost) AS y
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyyMMdd') AS INT)
  GROUP BY date_key
),
regression_stats AS (
  SELECT
    REGR_SLOPE(y, x) AS slope,
    REGR_INTERCEPT(y, x) AS intercept
  FROM daily_trend
)
SELECT
  'Next 30 Days Forecast' AS period,
  ROUND(slope * (60 + 30) + intercept, 2) AS forecast_daily_cost_end, -- 30 天後的預測日成本
  ROUND((slope * (60 + 15) + intercept) * 30, 2) AS forecast_monthly_total -- 預估下個月總成本 (以平均值推算)
FROM regression_stats;
```

## ⚡ 效能優化：大規模計數 (HyperLogLog)

當資料量達到億級時，使用 `APPROX_COUNT_DISTINCT` 替代 `COUNT(DISTINCT)` 可顯著提升查詢速度，誤差率通常低於 5%。

```sql
SELECT 
  year_month,
  APPROX_COUNT_DISTINCT(ResourceName) AS approx_resource_count,
  SUM(total_cost) AS total_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
GROUP BY year_month
ORDER BY year_month DESC;
```

## 🚨 Top 成本異常檢測（簡易版）

```sql
WITH daily_avg AS (
  SELECT 
    ConsumedService,
    AVG(total_cost) AS avg_cost,
    STDDEV(total_cost) AS stddev_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  GROUP BY ConsumedService
),
recent_costs AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ConsumedService,
    SUM(total_cost) AS daily_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ConsumedService
)
SELECT 
  r.date,
  r.ConsumedService,
  ROUND(r.daily_cost, 2) AS daily_cost,
  ROUND(a.avg_cost, 2) AS avg_cost,
  ROUND((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0), 2) AS z_score,
  CASE 
    WHEN ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) > 3 THEN '🔴 嚴重異常'
    WHEN ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) > 2 THEN '🟠 中度異常'
    ELSE '✓ 正常'
  END AS anomaly_status
FROM recent_costs r
JOIN daily_avg a ON r.ConsumedService = a.ConsumedService
WHERE ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) > 2
ORDER BY ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) DESC
LIMIT 10;
```
