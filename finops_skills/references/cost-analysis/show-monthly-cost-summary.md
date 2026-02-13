---
name: show-monthly-cost-summary
description: 顯示當月成本摘要，包含月對月變化和年初至今總計
tags: [cost-analysis, monthly, summary, executive]
---

# 月度成本摘要

## 描述
顯示當月總成本、月對月變化百分比和年初至今總計。這是最常用的高階成本概覽查詢，適合每日監控和高階主管報告。

## 使用時機
* 每日成本監控
* 每月成本審查
* 高階主管報告
* 預算追蹤和預測

## 查詢

```sql
-- 月度成本摘要
WITH current_month AS (
  SELECT 
    SUM(total_cost) AS mtd_cost,
    COUNT(DISTINCT date_key) AS days_in_month,
    SUM(reservation_cost) AS mtd_reserved_cost,
    SUM(on_demand_cost) AS mtd_on_demand_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
),
previous_month AS (
  SELECT 
    SUM(total_cost) AS last_month_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM')
),
ytd AS (
  SELECT 
    SUM(total_cost) AS ytd_cost,
    COUNT(DISTINCT year_month) AS months_in_year
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_TRUNC('year', CURRENT_DATE()), 'yyyy-MM')
),
last_year_same_month AS (
  SELECT 
    SUM(total_cost) AS last_year_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -12), 'yyyy-MM')
)
SELECT 
  DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM') AS current_month,
  ROUND(cm.mtd_cost, 2) AS month_to_date_cost,
  ROUND(cm.mtd_reserved_cost, 2) AS reserved_cost,
  ROUND(cm.mtd_on_demand_cost, 2) AS on_demand_cost,
  ROUND(cm.mtd_reserved_cost / NULLIF(cm.mtd_cost, 0) * 100, 2) AS reservation_coverage_pct,
  cm.days_in_month AS days_reported,
  ROUND(pm.last_month_cost, 2) AS previous_month_cost,
  ROUND(cm.mtd_cost - pm.last_month_cost, 2) AS mom_change,
  ROUND((cm.mtd_cost - pm.last_month_cost) / NULLIF(pm.last_month_cost, 0) * 100, 2) AS mom_change_pct,
  ROUND(ly.last_year_cost, 2) AS last_year_same_month_cost,
  ROUND((cm.mtd_cost - ly.last_year_cost) / NULLIF(ly.last_year_cost, 0) * 100, 2) AS yoy_change_pct,
  ROUND(ytd.ytd_cost, 2) AS year_to_date_cost,
  ytd.months_in_year AS ytd_months,
  ROUND(ytd.ytd_cost / NULLIF(ytd.months_in_year, 0), 2) AS ytd_monthly_average
FROM current_month cm
CROSS JOIN previous_month pm
CROSS JOIN ytd
CROSS JOIN last_year_same_month ly
```

## 輸出欄位

* `current_month` - 當前月份（yyyy-MM 格式）
* `month_to_date_cost` - 當月至今總成本
* `reserved_cost` - 保留實例成本
* `on_demand_cost` - 隨選成本
* `reservation_coverage_pct` - 保留實例覆蓋率百分比
* `days_reported` - 已報告天數
* `previous_month_cost` - 上月總成本
* `mom_change` - 月對月變化金額
* `mom_change_pct` - 月對月變化百分比
* `last_year_same_month_cost` - 去年同月成本
* `yoy_change_pct` - 年對年變化百分比
* `year_to_date_cost` - 年初至今總成本
* `ytd_months` - 年初至今月數
* `ytd_monthly_average` - 年初至今月平均成本

## 使用範例

### 範例 1：預測月底成本
```sql
-- 基於當前日均成本預測月底總成本
SELECT 
  month_to_date_cost,
  days_reported,
  ROUND(month_to_date_cost / days_reported * DAY(LAST_DAY(CURRENT_DATE())), 2) AS projected_month_end_cost
FROM (
  -- 原查詢
)
```

### 範例 2：與預算比較
```sql
-- 假設月度預算為 100,000
SELECT 
  month_to_date_cost,
  100000 AS monthly_budget,
  ROUND((month_to_date_cost / 100000) * 100, 2) AS budget_utilization_pct,
  ROUND(100000 - month_to_date_cost, 2) AS remaining_budget
FROM (
  -- 原查詢
)
```

## 解讀結果

### 正常情況
* 月對月變化在 ±10% 以內
* 保留實例覆蓋率 > 60%
* 年對年成長符合業務成長率

### 需要關注
* 🔴 月對月變化 > 30%：異常成本激增，需立即調查
* 🟡 月對月變化 > 15%：顯著變化，需檢閱原因
* 🟡 保留實例覆蓋率 < 50%：優化機會，考慮購買保留實例
* 🔴 超出預算 > 10%：預算控制問題

## 相關 Commands

* `show-top-cost-drivers` - 識別成本驅動因素
* `show-cost-by-category` - 按類別細分成本
* `detect-cost-anomalies` - 檢測異常成本
* `show-finops-kpis` - 查看完整 KPI 儀表板

## 資料來源

* **主要表格**：`develop_catalog.system_report.finops_daily_cost_summary`
* **資料層級**：Gold 層（已聚合）
* **更新頻率**：每日
* **歷史資料**：當月 + 上月 + 去年同月 + 年初至今

## 注意事項

1. **當月資料**：當月資料為部分月份，需考慮天數進行預測
2. **保留實例**：保留實例成本包含預付和每月攤銷
3. **貨幣**：所有金額以帳單貨幣顯示（通常為 USD 或 TWD）
4. **效能**：使用 Gold 層表格，查詢效能極佳（< 2 秒）
