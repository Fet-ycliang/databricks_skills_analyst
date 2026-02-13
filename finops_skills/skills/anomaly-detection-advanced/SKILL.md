---
name: 進階異常檢測
description: 提供進階統計方法和模式，用於檢測 Azure 支出中的成本異常，實現主動成本管理和早期問題識別
---

# FinOps 進階異常檢測

## 📋 概述

本文件提供進階統計方法和模式，用於檢測 Azure 支出中的成本異常，實現主動成本管理和早期問題識別。

---

## 🎯 異常檢測方法

### 1. 統計異常檢測（Z-Score）
### 2. 時間序列異常檢測
### 3. 資源層級異常檢測
### 4. 服務層級異常檢測
### 5. 閾值型警報
### 6. 模式型檢測

---

## 1️⃣ 統計異常檢測

### 方法 1.1：基於 Z-Score 的檢測

**目標**：識別與歷史模式顯著偏離的成本

```sql
-- 使用 Z-score 方法檢測每日成本異常
WITH daily_costs AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ConsumedService,
    cost_category,
    SUM(total_cost) AS daily_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ConsumedService, cost_category
),
stats AS (
  SELECT 
    ConsumedService,
    cost_category,
    AVG(daily_cost) AS avg_cost,
    STDDEV(daily_cost) AS stddev_cost,
    MIN(daily_cost) AS min_cost,
    MAX(daily_cost) AS max_cost,
    COUNT(*) AS sample_size
  FROM daily_costs
  GROUP BY ConsumedService, cost_category
  HAVING COUNT(*) >= 30  -- 統計顯著性的最小樣本數
)
SELECT 
  dc.date,
  dc.ConsumedService,
  dc.cost_category,
  ROUND(dc.daily_cost, 2) AS daily_cost,
  ROUND(s.avg_cost, 2) AS avg_cost,
  ROUND(s.stddev_cost, 2) AS stddev_cost,
  ROUND((dc.daily_cost - s.avg_cost) / NULLIF(s.stddev_cost, 0), 2) AS z_score,
  ROUND(ABS(dc.daily_cost - s.avg_cost), 2) AS deviation,
  ROUND(ABS(dc.daily_cost - s.avg_cost) / NULLIF(s.avg_cost, 0) * 100, 2) AS deviation_pct,
  CASE 
    WHEN ABS((dc.daily_cost - s.avg_cost) / NULLIF(s.stddev_cost, 0)) > 3 THEN '🔴 嚴重異常'
    WHEN ABS((dc.daily_cost - s.avg_cost) / NULLIF(s.stddev_cost, 0)) > 2 THEN '🟡 警告'
    ELSE '🟢 正常'
  END AS anomaly_status
FROM daily_costs dc
JOIN stats s ON dc.ConsumedService = s.ConsumedService AND dc.cost_category = s.cost_category
WHERE dc.date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND ABS((dc.daily_cost - s.avg_cost) / NULLIF(s.stddev_cost, 0)) > 2
ORDER BY z_score DESC
```

**警報閾值**：
* Z-score > 3：嚴重異常（需立即調查）
* Z-score > 2：警告（需監控）
* 偏差 > 50%：顯著變化

---

### 方法 1.2：百分位數異常檢測

**目標**：使用百分位數識別異常值（對離群值更穩健）

```sql
-- 使用百分位數方法檢測異常
WITH daily_costs AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ResourceGroup,
    SUM(CostInBillingCurrency) AS daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ResourceGroup
),
percentiles AS (
  SELECT 
    ResourceGroup,
    PERCENTILE(daily_cost, 0.25) AS p25,
    PERCENTILE(daily_cost, 0.50) AS p50_median,
    PERCENTILE(daily_cost, 0.75) AS p75,
    PERCENTILE(daily_cost, 0.95) AS p95,
    (PERCENTILE(daily_cost, 0.75) - PERCENTILE(daily_cost, 0.25)) AS iqr
  FROM daily_costs
  GROUP BY ResourceGroup
)
SELECT 
  dc.date,
  dc.ResourceGroup,
  ROUND(dc.daily_cost, 2) AS daily_cost,
  ROUND(p.p50_median, 2) AS median_cost,
  ROUND(p.p95, 2) AS p95_threshold,
  ROUND(p.p75 + 1.5 * p.iqr, 2) AS upper_fence,
  CASE 
    WHEN dc.daily_cost > p.p75 + 3 * p.iqr THEN '🔴 極端異常'
    WHEN dc.daily_cost > p.p75 + 1.5 * p.iqr THEN '🟡 溫和異常'
    WHEN dc.daily_cost > p.p95 THEN '🟡 高於 P95'
    ELSE '🟢 正常'
  END AS anomaly_status
FROM daily_costs dc
JOIN percentiles p ON dc.ResourceGroup = p.ResourceGroup
WHERE dc.date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND dc.daily_cost > p.p75 + 1.5 * p.iqr
ORDER BY dc.daily_cost DESC
```

---

## 2️⃣ 時間序列異常檢測

### 方法 2.1：移動平均異常檢測

**目標**：使用移動平均檢測趨勢偏差

```sql
-- 使用 7 天移動平均檢測異常
WITH daily_costs AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    SUM(CostInBillingCurrency) AS daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY date_key
),
moving_avg AS (
  SELECT 
    date,
    daily_cost,
    AVG(daily_cost) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7day,
    STDDEV(daily_cost) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS stddev_7day
  FROM daily_costs
)
SELECT 
  date,
  ROUND(daily_cost, 2) AS daily_cost,
  ROUND(ma_7day, 2) AS ma_7day,
  ROUND(stddev_7day, 2) AS stddev_7day,
  ROUND(daily_cost - ma_7day, 2) AS deviation,
  ROUND((daily_cost - ma_7day) / NULLIF(ma_7day, 0) * 100, 2) AS deviation_pct,
  CASE 
    WHEN ABS(daily_cost - ma_7day) > 2 * stddev_7day THEN '🔴 異常'
    WHEN ABS(daily_cost - ma_7day) > stddev_7day THEN '🟡 警告'
    ELSE '🟢 正常'
  END AS status
FROM moving_avg
WHERE date >= DATE_SUB(CURRENT_DATE(), 30)
  AND ABS(daily_cost - ma_7day) > stddev_7day
ORDER BY date DESC
```

---

### 方法 2.2：週對週變化檢測

**目標**：檢測週對週的異常變化

```sql
-- 週對週成本變化分析
WITH weekly_costs AS (
  SELECT 
    DATE_TRUNC('week', TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS week,
    ConsumedService,
    SUM(CostInBillingCurrency) AS weekly_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY week, ConsumedService
),
wow_change AS (
  SELECT 
    week,
    ConsumedService,
    weekly_cost,
    LAG(weekly_cost) OVER (PARTITION BY ConsumedService ORDER BY week) AS prev_week_cost,
    weekly_cost - LAG(weekly_cost) OVER (PARTITION BY ConsumedService ORDER BY week) AS wow_change,
    (weekly_cost - LAG(weekly_cost) OVER (PARTITION BY ConsumedService ORDER BY week)) / 
      NULLIF(LAG(weekly_cost) OVER (PARTITION BY ConsumedService ORDER BY week), 0) * 100 AS wow_change_pct
  FROM weekly_costs
)
SELECT 
  week,
  ConsumedService,
  ROUND(weekly_cost, 2) AS weekly_cost,
  ROUND(prev_week_cost, 2) AS prev_week_cost,
  ROUND(wow_change, 2) AS wow_change,
  ROUND(wow_change_pct, 2) AS wow_change_pct,
  CASE 
    WHEN wow_change_pct > 50 THEN '🔴 大幅增加'
    WHEN wow_change_pct > 25 THEN '🟡 顯著增加'
    WHEN wow_change_pct < -50 THEN '🔴 大幅減少'
    WHEN wow_change_pct < -25 THEN '🟡 顯著減少'
    ELSE '🟢 正常'
  END AS status
FROM wow_change
WHERE week >= DATE_SUB(CURRENT_DATE(), 30)
  AND ABS(wow_change_pct) > 25
ORDER BY ABS(wow_change_pct) DESC
```

---

## 3️⃣ 資源層級異常檢測

### 方法 3.1：資源成本激增檢測

**目標**：識別個別資源的異常成本激增

```sql
-- 檢測資源層級的成本激增
WITH resource_daily AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ResourceGroup,
    ResourceName,
    ConsumedService,
    SUM(CostInBillingCurrency) AS daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ResourceGroup, ResourceName, ConsumedService
),
resource_stats AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    AVG(daily_cost) AS avg_daily_cost,
    STDDEV(daily_cost) AS stddev_cost,
    MAX(daily_cost) AS max_cost
  FROM resource_daily
  WHERE date < DATE_SUB(CURRENT_DATE(), 7)  -- 基準期：7 天前
  GROUP BY ResourceGroup, ResourceName, ConsumedService
  HAVING AVG(daily_cost) > 10  -- 僅關注有意義的成本
)
SELECT 
  rd.date,
  rd.ResourceGroup,
  rd.ResourceName,
  rd.ConsumedService,
  ROUND(rd.daily_cost, 2) AS current_cost,
  ROUND(rs.avg_daily_cost, 2) AS baseline_avg,
  ROUND(rd.daily_cost - rs.avg_daily_cost, 2) AS cost_increase,
  ROUND((rd.daily_cost - rs.avg_daily_cost) / NULLIF(rs.avg_daily_cost, 0) * 100, 2) AS increase_pct,
  CASE 
    WHEN rd.daily_cost > rs.avg_daily_cost + 3 * rs.stddev_cost THEN '🔴 嚴重激增'
    WHEN rd.daily_cost > rs.avg_daily_cost + 2 * rs.stddev_cost THEN '🟡 顯著激增'
    ELSE '🟢 正常'
  END AS status
FROM resource_daily rd
JOIN resource_stats rs 
  ON rd.ResourceGroup = rs.ResourceGroup 
  AND rd.ResourceName = rs.ResourceName
  AND rd.ConsumedService = rs.ConsumedService
WHERE rd.date >= DATE_SUB(CURRENT_DATE(), 7)
  AND rd.daily_cost > rs.avg_daily_cost + 2 * rs.stddev_cost
ORDER BY increase_pct DESC
LIMIT 50
```

---

## 4️⃣ 服務層級異常檢測

### 方法 4.1：服務成本異常

**目標**：檢測特定 Azure 服務的異常支出

```sql
-- 服務層級異常檢測
WITH service_daily AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ConsumedService,
    cost_category,
    SUM(total_cost) AS daily_cost,
    COUNT(DISTINCT ResourceName) AS resource_count
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ConsumedService, cost_category
),
service_baseline AS (
  SELECT 
    ConsumedService,
    cost_category,
    AVG(daily_cost) AS avg_cost,
    STDDEV(daily_cost) AS stddev_cost,
    PERCENTILE(daily_cost, 0.95) AS p95_cost
  FROM service_daily
  WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), 60) AND DATE_SUB(CURRENT_DATE(), 8)
  GROUP BY ConsumedService, cost_category
)
SELECT 
  sd.date,
  sd.ConsumedService,
  sd.cost_category,
  ROUND(sd.daily_cost, 2) AS daily_cost,
  sd.resource_count,
  ROUND(sb.avg_cost, 2) AS baseline_avg,
  ROUND(sb.p95_cost, 2) AS p95_threshold,
  ROUND((sd.daily_cost - sb.avg_cost) / NULLIF(sb.stddev_cost, 0), 2) AS z_score,
  CASE 
    WHEN sd.daily_cost > sb.p95_cost * 1.5 THEN '🔴 極端異常'
    WHEN sd.daily_cost > sb.p95_cost THEN '🟡 超過 P95'
    WHEN ABS((sd.daily_cost - sb.avg_cost) / NULLIF(sb.stddev_cost, 0)) > 2 THEN '🟡 統計異常'
    ELSE '🟢 正常'
  END AS status
FROM service_daily sd
JOIN service_baseline sb 
  ON sd.ConsumedService = sb.ConsumedService 
  AND sd.cost_category = sb.cost_category
WHERE sd.date >= DATE_SUB(CURRENT_DATE(), 7)
  AND (sd.daily_cost > sb.p95_cost OR ABS((sd.daily_cost - sb.avg_cost) / NULLIF(sb.stddev_cost, 0)) > 2)
ORDER BY z_score DESC
```

---

## 5️⃣ 閾值型警報

### 方法 5.1：絕對成本閾值

**目標**：當成本超過預定義閾值時發出警報

```sql
-- 基於閾值的警報
WITH daily_totals AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ResourceGroup,
    SUM(CostInBillingCurrency) AS daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ResourceGroup
),
thresholds AS (
  SELECT 
    ResourceGroup,
    AVG(daily_cost) * 1.5 AS warning_threshold,
    AVG(daily_cost) * 2.0 AS critical_threshold
  FROM daily_totals
  WHERE date < DATE_SUB(CURRENT_DATE(), 7)
  GROUP BY ResourceGroup
)
SELECT 
  dt.date,
  dt.ResourceGroup,
  ROUND(dt.daily_cost, 2) AS daily_cost,
  ROUND(t.warning_threshold, 2) AS warning_threshold,
  ROUND(t.critical_threshold, 2) AS critical_threshold,
  CASE 
    WHEN dt.daily_cost > t.critical_threshold THEN '🔴 嚴重：超過 2x 基準'
    WHEN dt.daily_cost > t.warning_threshold THEN '🟡 警告：超過 1.5x 基準'
    ELSE '🟢 正常'
  END AS alert_level
FROM daily_totals dt
JOIN thresholds t ON dt.ResourceGroup = t.ResourceGroup
WHERE dt.date >= DATE_SUB(CURRENT_DATE(), 7)
  AND dt.daily_cost > t.warning_threshold
ORDER BY dt.daily_cost DESC
```

---

## 6️⃣ 模式型檢測

### 方法 6.1：新資源檢測

**目標**：識別新建立的高成本資源

```sql
-- 檢測新的高成本資源
WITH resource_first_seen AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    MIN(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS first_seen_date,
    SUM(CostInBillingCurrency) AS total_cost_since_creation
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  GROUP BY ResourceGroup, ResourceName, ConsumedService
)
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  first_seen_date,
  DATEDIFF(CURRENT_DATE(), first_seen_date) AS days_old,
  ROUND(total_cost_since_creation, 2) AS total_cost,
  ROUND(total_cost_since_creation / NULLIF(DATEDIFF(CURRENT_DATE(), first_seen_date), 0), 2) AS avg_daily_cost,
  CASE 
    WHEN total_cost_since_creation > 1000 AND DATEDIFF(CURRENT_DATE(), first_seen_date) <= 7 
      THEN '🔴 新的高成本資源'
    WHEN total_cost_since_creation > 500 AND DATEDIFF(CURRENT_DATE(), first_seen_date) <= 7 
      THEN '🟡 新的中等成本資源'
    ELSE '🟢 正常'
  END AS status
FROM resource_first_seen
WHERE first_seen_date >= DATE_SUB(CURRENT_DATE(), 14)
  AND total_cost_since_creation > 100
ORDER BY total_cost_since_creation DESC
```

---

## 📊 綜合異常儀表板

```sql
-- 每日異常摘要
SELECT 
  CURRENT_DATE() AS report_date,
  COUNT(DISTINCT CASE WHEN z_score > 3 THEN ResourceName END) AS critical_anomalies,
  COUNT(DISTINCT CASE WHEN z_score > 2 THEN ResourceName END) AS warning_anomalies,
  ROUND(SUM(CASE WHEN z_score > 2 THEN daily_cost ELSE 0 END), 2) AS anomalous_cost,
  ROUND(SUM(daily_cost), 2) AS total_cost,
  ROUND(SUM(CASE WHEN z_score > 2 THEN daily_cost ELSE 0 END) / NULLIF(SUM(daily_cost), 0) * 100, 2) AS anomalous_cost_pct
FROM (
  SELECT 
    ResourceName,
    SUM(CostInBillingCurrency) AS daily_cost,
    (SUM(CostInBillingCurrency) - AVG(SUM(CostInBillingCurrency)) OVER ()) / 
      NULLIF(STDDEV(SUM(CostInBillingCurrency)) OVER (), 0) AS z_score
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key = CAST(DATE_FORMAT(CURRENT_DATE() - INTERVAL 1 DAY, 'yyyyMMdd') AS INT)
  GROUP BY ResourceName
)
```

---

## 🔔 建議的警報設定

| 異常類型 | 檢測頻率 | 警報閾值 | 優先級 |
|---------|---------|---------|--------|
| Z-score > 3 | 每日 | 立即 | 🔴 高 |
| 週對週 > 50% | 每週 | 24 小時內 | 🔴 高 |
| 新高成本資源 | 每日 | 24 小時內 | 🟡 中 |
| 超過 P95 | 每日 | 48 小時內 | 🟡 中 |
| 移動平均偏差 | 每日 | 監控 | 🟢 低 |

---

## 📅 監控排程

* **即時**：嚴重異常（Z-score > 3）
* **每日**：所有異常檢測方法
* **每週**：趨勢分析和模式檢測
* **每月**：閾值調整和模型優化

---

**最後更新**：2026-02-13  
**版本**：1.0  
**維護者**：FinOps 異常檢測團隊
