# 快速驗證查詢

在開始使用前，執行以下查詢驗證資料可用性和品質。

## 📅 資料新鮮度檢查

```sql
-- 檢查各層資料的最新日期
SELECT 
  'Bronze' AS layer,
  MAX(Date) AS latest_date,
  DATEDIFF(CURRENT_DATE(), MAX(Date)) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), MAX(Date)) <= 2 THEN '✓ PASS'
    ELSE '✗ FAIL' 
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_usage_actual

UNION ALL

SELECT 
  'Silver' AS layer,
  TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd') AS latest_date,
  DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 2 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver

UNION ALL

SELECT 
  'Gold' AS layer,
  TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd') AS latest_date,
  DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 2 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END AS status
FROM develop_catalog.system_report.finops_daily_cost_summary

ORDER BY layer;
```

**預期結果**：所有層的 `days_lag` 應 ≤ 2 天，狀態為 `✓ PASS`

## ✅ 資料完整性檢查

```sql
-- 檢查最近 7 天的資料記錄數
SELECT 
  date_key,
  TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
  COUNT(*) AS record_count,
  ROUND(SUM(total_cost), 2) AS daily_cost,
  COUNT(DISTINCT ConsumedService) AS service_count
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)
GROUP BY date_key
ORDER BY date_key DESC;
```

**預期結果**：每天應有穩定的記錄數和合理的成本範圍

## 🏷️ 標籤覆蓋率檢查

```sql
-- 檢查關鍵標籤的覆蓋率
SELECT 
  ROUND(COUNT(CASE WHEN tag_environment IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS environment_coverage_pct,
  ROUND(COUNT(CASE WHEN tag_cost_center IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS cost_center_coverage_pct,
  ROUND(COUNT(CASE WHEN tag_owner IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS owner_coverage_pct,
  COUNT(*) AS total_records
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM');
```

**預期結果**：標籤覆蓋率應 > 90%
