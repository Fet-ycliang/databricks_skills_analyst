---
name: 資料品質驗證
description: 提供完整的資料品質檢查與驗證查詢，確保 Azure 成本資料在 Bronze-Silver-Gold 架構中的準確性和可靠性
---

# FinOps 資料品質驗證

## 📋 概述

本文件提供完整的資料品質檢查與驗證查詢，以確保 Azure 成本資料在 Bronze-Silver-Gold 架構中的準確性和可靠性。

---

## 🎯 資料品質維度

### 1. 完整性 - 所有預期資料是否存在？
### 2. 準確性 - 資料是否正確？
### 3. 一致性 - 資料在各層之間是否一致？
### 4. 時效性 - 資料是否新鮮且最新？
### 5. 有效性 - 資料是否符合業務規則？
### 6. 唯一性 - 是否有重複記錄？

---

## 1️⃣ 完整性檢查

### 檢查 1.1：每日資料可用性

**目標**：確保所有預期日期都已載入成本資料

```sql
-- 檢查最近 90 天是否有遺失的日期
WITH expected_dates AS (
  SELECT EXPLODE(SEQUENCE(
    DATE_SUB(CURRENT_DATE(), 90),
    DATE_SUB(CURRENT_DATE(), 1),
    INTERVAL 1 DAY
  )) AS expected_date
),
actual_dates AS (
  SELECT DISTINCT TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS actual_date
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
)
SELECT 
  ed.expected_date,
  CASE WHEN ad.actual_date IS NULL THEN 'MISSING' ELSE 'Present' END AS status
FROM expected_dates ed
LEFT JOIN actual_dates ad ON ed.expected_date = ad.actual_date
WHERE ad.actual_date IS NULL
ORDER BY ed.expected_date DESC
```

**預期結果**：無遺失日期（空結果集）

**警報閾值**：最近 7 天內任何遺失日期 = 嚴重

---

### 檢查 1.2：資料量一致性

**目標**：檢測每日記錄數的異常下降或激增

```sql
-- 使用異常檢測監控每日記錄數
WITH daily_counts AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    COUNT(*) AS record_count,
    COUNT(DISTINCT ResourceName) AS unique_resources,
    SUM(CostInBillingCurrency) AS total_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyyMMdd') AS INT)
  GROUP BY date_key
),
stats AS (
  SELECT 
    AVG(record_count) AS avg_records,
    STDDEV(record_count) AS stddev_records,
    AVG(unique_resources) AS avg_resources,
    AVG(total_cost) AS avg_cost
  FROM daily_counts
)
SELECT 
  dc.date,
  dc.record_count,
  dc.unique_resources,
  ROUND(dc.total_cost, 2) AS total_cost,
  ROUND(s.avg_records, 0) AS avg_records,
  ROUND((dc.record_count - s.avg_records) / NULLIF(s.stddev_records, 0), 2) AS z_score,
  CASE 
    WHEN ABS((dc.record_count - s.avg_records) / NULLIF(s.stddev_records, 0)) > 3 THEN '🔴 CRITICAL'
    WHEN ABS((dc.record_count - s.avg_records) / NULLIF(s.stddev_records, 0)) > 2 THEN '🟡 WARNING'
    ELSE '🟢 OK'
  END AS status
FROM daily_counts dc
CROSS JOIN stats s
WHERE dc.date >= DATE_SUB(CURRENT_DATE(), 30)
ORDER BY dc.date DESC
```

**警報閾值**：
* Z-score > 3：嚴重異常
* Z-score > 2：警告
* 記錄數 = 0：嚴重

---

### 檢查 1.3：服務覆蓋率

**目標**：確保所有主要 Azure 服務都有呈現

```sql
-- 檢查最近資料中的預期服務
WITH recent_services AS (
  SELECT DISTINCT ConsumedService
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 7)
),
expected_services AS (
  SELECT service FROM (VALUES
    ('Microsoft.Compute'),
    ('Microsoft.Storage'),
    ('Microsoft.Network'),
    ('Microsoft.Databricks'),
    ('Microsoft.Sql')
  ) AS t(service)
)
SELECT 
  es.service AS expected_service,
  CASE WHEN rs.ConsumedService IS NULL THEN '❌ MISSING' ELSE '✅ Present' END AS status
FROM expected_services es
LEFT JOIN recent_services rs ON es.service = rs.ConsumedService
WHERE rs.ConsumedService IS NULL
```

**預期結果**：所有預期服務都存在

---

## 2️⃣ 準確性檢查

### 檢查 2.1：成本計算驗證

**目標**：驗證成本 = 數量 × 價格

```sql
-- 驗證成本計算準確性
SELECT 
  Date,
  ResourceGroup,
  ResourceName,
  ConsumedService,
  Quantity,
  EffectivePrice,
  CostInBillingCurrency AS recorded_cost,
  ROUND(Quantity * EffectivePrice, 6) AS calculated_cost,
  ROUND(ABS(CostInBillingCurrency - (Quantity * EffectivePrice)), 6) AS difference,
  CASE 
    WHEN ABS(CostInBillingCurrency - (Quantity * EffectivePrice)) > 0.01 THEN '⚠️ MISMATCH'
    ELSE '✅ OK'
  END AS validation_status
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 7)
  AND CostInBillingCurrency > 0
  AND ABS(CostInBillingCurrency - (Quantity * EffectivePrice)) > 0.01
ORDER BY difference DESC
LIMIT 100
```

**警報閾值**：每天 > 100 個不匹配 = 需要調查

---

### 檢查 2.2：負值或零成本驗證

**目標**：識別無效的成本值

```sql
-- 尋找負成本或可疑的零成本記錄
SELECT 
  Date,
  ResourceGroup,
  ResourceName,
  ConsumedService,
  ProductName,
  Quantity,
  CostInBillingCurrency,
  CASE 
    WHEN CostInBillingCurrency < 0 THEN '🔴 NEGATIVE COST'
    WHEN CostInBillingCurrency = 0 AND Quantity > 0 THEN '🟡 ZERO COST WITH USAGE'
    ELSE '✅ OK'
  END AS issue_type
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND (
    CostInBillingCurrency < 0 
    OR (CostInBillingCurrency = 0 AND Quantity > 0)
  )
ORDER BY Date DESC, CostInBillingCurrency
LIMIT 100
```

**預期結果**：
* 負成本：應該很少見（僅限抵免/退款）
* 有使用量但零成本：可能表示免費層或定價錯誤

---

### 檢查 2.3：價格異常值檢測

**目標**：識別異常的單位價格

```sql
-- 檢測每個計量器的異常定價
WITH price_stats AS (
  SELECT 
    ConsumedService,
    MeterCategory,
    MeterId,
    MeterName,
    AVG(EffectivePrice) AS avg_price,
    STDDEV(EffectivePrice) AS stddev_price,
    MIN(EffectivePrice) AS min_price,
    MAX(EffectivePrice) AS max_price,
    COUNT(*) AS sample_size
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
    AND EffectivePrice > 0
  GROUP BY ConsumedService, MeterCategory, MeterId, MeterName
  HAVING COUNT(*) >= 10
)
SELECT 
  s.Date,
  s.ConsumedService,
  s.MeterName,
  s.ResourceName,
  ROUND(s.EffectivePrice, 6) AS current_price,
  ROUND(ps.avg_price, 6) AS avg_price,
  ROUND(ps.min_price, 6) AS min_price,
  ROUND(ps.max_price, 6) AS max_price,
  ROUND((s.EffectivePrice - ps.avg_price) / NULLIF(ps.stddev_price, 0), 2) AS z_score,
  CASE 
    WHEN ABS((s.EffectivePrice - ps.avg_price) / NULLIF(ps.stddev_price, 0)) > 3 THEN '🔴 OUTLIER'
    WHEN ABS((s.EffectivePrice - ps.avg_price) / NULLIF(ps.stddev_price, 0)) > 2 THEN '🟡 UNUSUAL'
    ELSE '✅ OK'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver s
JOIN price_stats ps ON s.MeterId = ps.MeterId
WHERE s.Date >= DATE_SUB(CURRENT_DATE(), 7)
  AND ABS((s.EffectivePrice - ps.avg_price) / NULLIF(ps.stddev_price, 0)) > 2
ORDER BY z_score DESC
LIMIT 50
```

---

## 3️⃣ 一致性檢查

### 檢查 3.1：Bronze 到 Silver 層對帳

**目標**：確保 Silver 層與 Bronze 層總計相符

```sql
-- 比較 Bronze 和 Silver 層之間的總成本
WITH bronze_totals AS (
  SELECT 
    CAST(Date AS DATE) AS date,
    COUNT(*) AS record_count,
    SUM(CostInBillingCurrency) AS total_cost,
    COUNT(DISTINCT ResourceName) AS unique_resources
  FROM develop_catalog.system_report.infra_azure_cost_usage_actual
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  GROUP BY date
),
silver_totals AS (
  SELECT 
    CAST(Date AS DATE) AS date,
    COUNT(*) AS record_count,
    SUM(CostInBillingCurrency) AS total_cost,
    COUNT(DISTINCT ResourceName) AS unique_resources
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  GROUP BY date
)
SELECT 
  b.date,
  b.record_count AS bronze_records,
  s.record_count AS silver_records,
  b.record_count - s.record_count AS record_diff,
  ROUND(b.total_cost, 2) AS bronze_cost,
  ROUND(s.total_cost, 2) AS silver_cost,
  ROUND(b.total_cost - s.total_cost, 2) AS cost_diff,
  ROUND(ABS(b.total_cost - s.total_cost) / NULLIF(b.total_cost, 0) * 100, 4) AS cost_diff_pct,
  CASE 
    WHEN ABS(b.total_cost - s.total_cost) / NULLIF(b.total_cost, 0) > 0.01 THEN '🔴 MISMATCH'
    WHEN b.record_count != s.record_count THEN '🟡 RECORD COUNT DIFF'
    ELSE '✅ OK'
  END AS status
FROM bronze_totals b
FULL OUTER JOIN silver_totals s ON b.date = s.date
WHERE ABS(b.total_cost - s.total_cost) / NULLIF(b.total_cost, 0) > 0.001
   OR b.record_count != s.record_count
ORDER BY b.date DESC
```

**警報閾值**：成本差異 > 0.1% = 需要調查

---

### 檢查 3.2：Silver 到 Gold 層對帳

**目標**：確保 Gold 聚合與 Silver 總計相符

```sql
-- 驗證 Gold 層每日摘要與 Silver 層的對應
WITH silver_daily AS (
  SELECT 
    CAST(Date AS DATE) AS date,
    ConsumedService,
    cost_category,
    region_group,
    COUNT(DISTINCT ResourceName) AS resource_count,
    SUM(Quantity) AS total_quantity,
    SUM(CostInBillingCurrency) AS total_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  GROUP BY date, ConsumedService, cost_category, region_group
),
gold_daily AS (
  SELECT 
    CAST(Date AS DATE) AS date,
    ConsumedService,
    cost_category,
    region_group,
    resource_count,
    total_quantity,
    total_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
)
SELECT 
  s.date,
  s.ConsumedService,
  s.cost_category,
  ROUND(s.total_cost, 2) AS silver_cost,
  ROUND(g.total_cost, 2) AS gold_cost,
  ROUND(s.total_cost - g.total_cost, 2) AS cost_diff,
  ROUND(ABS(s.total_cost - g.total_cost) / NULLIF(s.total_cost, 0) * 100, 4) AS diff_pct,
  CASE 
    WHEN g.total_cost IS NULL THEN '🔴 MISSING IN GOLD'
    WHEN ABS(s.total_cost - g.total_cost) / NULLIF(s.total_cost, 0) > 0.01 THEN '🔴 MISMATCH'
    ELSE '✅ OK'
  END AS status
FROM silver_daily s
LEFT JOIN gold_daily g 
  ON s.date = g.date 
  AND s.ConsumedService = g.ConsumedService 
  AND s.cost_category = g.cost_category
  AND s.region_group = g.region_group
WHERE g.total_cost IS NULL 
   OR ABS(s.total_cost - g.total_cost) / NULLIF(s.total_cost, 0) > 0.001
ORDER BY s.date DESC, cost_diff DESC
LIMIT 100
```

---

## 4️⃣ 時效性檢查

### 檢查 4.1：資料新鮮度

**目標**：確保資料在 SLA 內載入

```sql
-- 檢查資料新鮮度和載入延遲
WITH latest_data AS (
  SELECT 
    MAX(Date) AS latest_date,
    MAX(processed_at) AS latest_processed_at,
    COUNT(DISTINCT CAST(Date AS DATE)) AS days_loaded
  FROM develop_catalog.system_report.infra_azure_cost_silver
),
freshness_check AS (
  SELECT 
    latest_date,
    latest_processed_at,
    CURRENT_TIMESTAMP() AS check_time,
    DATEDIFF(CURRENT_DATE(), CAST(latest_date AS DATE)) AS days_behind,
    ROUND(UNIX_TIMESTAMP(CURRENT_TIMESTAMP()) - UNIX_TIMESTAMP(latest_processed_at)) / 3600, 2) AS hours_since_load,
    days_loaded
  FROM latest_data
)
SELECT 
  *,
  CASE 
    WHEN days_behind > 2 THEN '🔴 CRITICAL - Data > 2 days old'
    WHEN days_behind > 1 THEN '🟡 WARNING - Data > 1 day old'
    WHEN hours_since_load > 24 THEN '🟡 WARNING - No load in 24h'
    ELSE '✅ OK - Data is fresh'
  END AS freshness_status
FROM freshness_check
```

**SLA 目標**：
* 資料應落後 < 1 天
* 載入應至少每天進行

---

### 檢查 4.2：各層處理延遲

**目標**：監控各層之間的處理時間

```sql
-- 檢查各層的處理時間戳記
SELECT 
  'Bronze Layer' AS layer,
  MAX(Date) AS latest_date,
  COUNT(DISTINCT CAST(Date AS DATE)) AS days_available,
  DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS days_behind
FROM develop_catalog.system_report.infra_azure_cost_usage_actual

UNION ALL

SELECT 
  'Silver Layer' AS layer,
  MAX(Date) AS latest_date,
  COUNT(DISTINCT CAST(Date AS DATE)) AS days_available,
  DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS days_behind
FROM develop_catalog.system_report.infra_azure_cost_silver

UNION ALL

SELECT 
  'Gold - Daily Summary' AS layer,
  MAX(Date) AS latest_date,
  COUNT(DISTINCT CAST(Date AS DATE)) AS days_available,
  DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS days_behind
FROM develop_catalog.system_report.finops_daily_cost_summary

ORDER BY days_behind DESC
```

---

## 5️⃣ 有效性檢查

### 檢查 5.1：標籤完整性

**目標**：監控成本分配的標籤覆蓋率

```sql
-- 標籤覆蓋率和品質指標
WITH tag_analysis AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    COUNT(DISTINCT ResourceName) AS total_resources,
    COUNT(DISTINCT CASE WHEN tag_environment IS NOT NULL THEN ResourceName END) AS tagged_environment,
    COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) AS tagged_cost_center,
    COUNT(DISTINCT CASE WHEN tag_owner IS NOT NULL THEN ResourceName END) AS tagged_owner,
    COUNT(DISTINCT CASE 
      WHEN tag_environment IS NOT NULL 
       AND tag_cost_center IS NOT NULL 
       AND tag_owner IS NOT NULL 
      THEN ResourceName 
    END) AS fully_tagged,
    SUM(CostInBillingCurrency) AS total_cost,
    SUM(CASE WHEN tag_cost_center IS NULL THEN CostInBillingCurrency ELSE 0 END) AS unallocated_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
  GROUP BY month
)
SELECT 
  month,
  total_resources,
  ROUND(tagged_environment / NULLIF(total_resources, 0) * 100, 2) AS environment_coverage_pct,
  ROUND(tagged_cost_center / NULLIF(total_resources, 0) * 100, 2) AS cost_center_coverage_pct,
  ROUND(tagged_owner / NULLIF(total_resources, 0) * 100, 2) AS owner_coverage_pct,
  ROUND(fully_tagged / NULLIF(total_resources, 0) * 100, 2) AS fully_tagged_pct,
  ROUND(total_cost, 2) AS total_cost,
  ROUND(unallocated_cost, 2) AS unallocated_cost,
  ROUND(unallocated_cost / NULLIF(total_cost, 0) * 100, 2) AS unallocated_cost_pct,
  CASE 
    WHEN fully_tagged / NULLIF(total_resources, 0) < 0.5 THEN '🔴 POOR (<50%)'
    WHEN fully_tagged / NULLIF(total_resources, 0) < 0.8 THEN '🟡 FAIR (50-80%)'
    ELSE '✅ GOOD (>80%)'
  END AS tag_quality_status
FROM tag_analysis
ORDER BY month DESC
```

**目標**：成本分配的標籤覆蓋率 > 80%

---

### 檢查 5.2：資源命名慣例

**目標**：驗證資源命名標準

```sql
-- 檢查不符合命名慣例的資源
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  SUM(CostInBillingCurrency) AS cost_30d,
  CASE 
    WHEN ResourceName IS NULL THEN '🔴 NULL NAME'
    WHEN LENGTH(ResourceName) < 3 THEN '🔴 TOO SHORT'
    WHEN ResourceName LIKE '%test%' OR ResourceName LIKE '%temp%' THEN '🟡 TEMPORARY NAME'
    WHEN ResourceName RLIKE '[^a-zA-Z0-9-_]' THEN '🟡 INVALID CHARACTERS'
    ELSE '✅ OK'
  END AS naming_status
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category
HAVING SUM(CostInBillingCurrency) > 10
  AND (
    ResourceName IS NULL 
    OR LENGTH(ResourceName) < 3
    OR ResourceName LIKE '%test%' 
    OR ResourceName LIKE '%temp%'
  )
ORDER BY cost_30d DESC
LIMIT 100
```

---

## 6️⃣ 唯一性檢查

### 檢查 6.1：重複記錄檢測

**目標**：識別重複的成本記錄

```sql
-- 在 Silver 層尋找潛在的重複記錄
WITH record_counts AS (
  SELECT 
    Date,
    ResourceGroup,
    ResourceName,
    ConsumedService,
    MeterId,
    Quantity,
    CostInBillingCurrency,
    COUNT(*) AS duplicate_count
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  GROUP BY Date, ResourceGroup, ResourceName, ConsumedService, MeterId, Quantity, CostInBillingCurrency
  HAVING COUNT(*) > 1
)
SELECT 
  Date,
  ResourceGroup,
  ResourceName,
  ConsumedService,
  duplicate_count,
  ROUND(CostInBillingCurrency, 2) AS cost_per_record,
  ROUND(CostInBillingCurrency * duplicate_count, 2) AS total_duplicated_cost
FROM record_counts
ORDER BY total_duplicated_cost DESC
LIMIT 100
```

**預期結果**：無重複（空結果集）

---

## 📊 每日資料品質儀表板查詢

**綜合每日品質檢查**

```sql
-- 每日資料品質計分卡
WITH quality_checks AS (
  -- 新鮮度
  SELECT 
    'Freshness' AS check_category,
    'Data Lag' AS check_name,
    DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS metric_value,
    1 AS target_value,
    CASE WHEN DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) <= 1 THEN 'PASS' ELSE 'FAIL' END AS status
  FROM develop_catalog.system_report.infra_azure_cost_silver
  
  UNION ALL
  
  -- 完整性
  SELECT 
    'Completeness' AS check_category,
    'Record Count Today' AS check_name,
    COUNT(*) AS metric_value,
    10000 AS target_value,
    CASE WHEN COUNT(*) > 10000 THEN 'PASS' ELSE 'FAIL' END AS status
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= CURRENT_DATE() - INTERVAL 1 DAY
  
  UNION ALL
  
  -- 標籤覆蓋率
  SELECT 
    'Validity' AS check_category,
    'Tag Coverage %' AS check_name,
    ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
          NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS metric_value,
    80 AS target_value,
    CASE WHEN COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
              NULLIF(COUNT(DISTINCT ResourceName), 0) >= 0.8 THEN 'PASS' ELSE 'FAIL' END AS status
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 7)
  
  UNION ALL
  
  -- 準確性
  SELECT 
    'Accuracy' AS check_category,
    'Negative Costs Count' AS check_name,
    COUNT(*) AS metric_value,
    0 AS target_value,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 7)
    AND CostInBillingCurrency < 0
)
SELECT 
  check_category,
  check_name,
  metric_value,
  target_value,
  CASE 
    WHEN status = 'PASS' THEN '✅ PASS'
    ELSE '❌ FAIL'
  END AS status
FROM quality_checks
ORDER BY check_category, check_name
```

---

## 🔔 自動化警報查詢

### 嚴重警報（每小時執行）

```sql
-- 需要立即關注的嚴重資料品質問題
SELECT 
  CURRENT_TIMESTAMP() AS alert_time,
  'CRITICAL' AS severity,
  issue_type,
  issue_description,
  affected_count,
  recommended_action
FROM (
  -- 資料遺失
  SELECT 
    'Missing Data' AS issue_type,
    CONCAT('No data for ', DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))), ' days') AS issue_description,
    DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS affected_count,
    'Check data pipeline immediately' AS recommended_action
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) > 2
  
  UNION ALL
  
  -- 大量成本差異
  SELECT 
    'Cost Reconciliation' AS issue_type,
    'Bronze-Silver cost mismatch detected' AS issue_description,
    COUNT(*) AS affected_count,
    'Investigate data transformation logic' AS recommended_action
  FROM (
    SELECT b.Date, ABS(b.total - s.total) / NULLIF(b.total, 0) AS diff_pct
    FROM (
      SELECT CAST(Date AS DATE) AS Date, SUM(CostInBillingCurrency) AS total
      FROM develop_catalog.system_report.infra_azure_cost_usage_actual
      WHERE Date >= DATE_SUB(CURRENT_DATE(), 7)
      GROUP BY Date
    ) b
    JOIN (
      SELECT CAST(Date AS DATE) AS Date, SUM(CostInBillingCurrency) AS total
      FROM develop_catalog.system_report.infra_azure_cost_silver
      WHERE Date >= DATE_SUB(CURRENT_DATE(), 7)
      GROUP BY Date
    ) s ON b.Date = s.Date
    WHERE ABS(b.total - s.total) / NULLIF(b.total, 0) > 0.01
  )
) alerts
WHERE affected_count > 0
```

---

## 📈 資料品質趨勢報告

```sql
-- 每週資料品質趨勢
WITH weekly_metrics AS (
  SELECT 
    DATE_TRUNC('week', Date) AS week,
    COUNT(*) AS total_records,
    COUNT(DISTINCT ResourceName) AS unique_resources,
    SUM(CostInBillingCurrency) AS total_cost,
    COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
      NULLIF(COUNT(DISTINCT ResourceName), 0) AS tag_coverage_rate,
    COUNT(CASE WHEN CostInBillingCurrency < 0 THEN 1 END) AS negative_cost_count
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
  GROUP BY week
)
SELECT 
  week,
  total_records,
  unique_resources,
  ROUND(total_cost, 2) AS total_cost,
  ROUND(tag_coverage_rate * 100, 2) AS tag_coverage_pct,
  negative_cost_count,
  ROUND((total_records - LAG(total_records) OVER (ORDER BY week)) / 
        NULLIF(LAG(total_records) OVER (ORDER BY week), 0) * 100, 2) AS record_growth_pct
FROM weekly_metrics
ORDER BY week DESC
```

---

## 🎯 資料品質 KPI

| KPI | 目標 | 嚴重閾值 |
|-----|--------|-------------------|
| 資料新鮮度 | < 1 天 | > 2 天 |
| 標籤覆蓋率 | > 80% | < 50% |
| Bronze-Silver 對帳 | 100% 匹配 | > 0.1% 差異 |
| Silver-Gold 對帳 | 100% 匹配 | > 0.1% 差異 |
| 負成本記錄 | 0 | 每天 > 10 筆 |
| 重複記錄 | 0 | > 0 |
| 遺失日期 | 0 | 最近 7 天 > 0 |

---

## 🔄 建議的監控排程

* **每小時**：資料新鮮度、嚴重警報
* **每日**：完整性檢查、對帳
* **每週**：標籤覆蓋率、品質趨勢
* **每月**：綜合品質報告

---

**最後更新**：2026-02-13  
**版本**：1.0  
**維護者**：FinOps 資料品質團隊
