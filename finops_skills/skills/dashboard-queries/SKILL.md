---
name: 儀表板查詢
description: 提供用於在 Databricks 中建構完整 FinOps 儀表板的即用 SQL 查詢，涵蓋高階主管摘要、營運監控和優化追蹤
---

# FinOps 儀表板查詢

## 📋 概述

本文件提供用於在 Databricks 中建構完整 FinOps 儀表板的即用 SQL 查詢，涵蓋高階主管摘要、營運監控和優化追蹤。

---

## 🎯 儀表板類型

### 1. 高階主管儀表板 - 高層成本概覽
### 2. FinOps 團隊儀表板 - 每日營運監控
### 3. 成本中心儀表板 - 部門/團隊視圖
### 4. 優化儀表板 - 節省機會
### 5. 資源儀表板 - 資源層級詳情
### 6. 趨勢分析儀表板 - 歷史模式

---

## 1️⃣ 高階主管儀表板

### 查詢 1.1：月度成本摘要卡片

**用途**：顯示當月總成本、月對月變化和年初至今總計

```sql
-- 月度成本摘要
WITH current_month AS (
  SELECT 
    SUM(total_cost) AS mtd_cost,
    COUNT(DISTINCT date_key) AS days_in_month
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
    SUM(total_cost) AS ytd_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_TRUNC('year', CURRENT_DATE()), 'yyyy-MM')
)
SELECT 
  ROUND(cm.mtd_cost, 2) AS month_to_date_cost,
  ROUND(pm.last_month_cost, 2) AS previous_month_cost,
  ROUND(cm.mtd_cost - pm.last_month_cost, 2) AS mom_change,
  ROUND((cm.mtd_cost - pm.last_month_cost) / NULLIF(pm.last_month_cost, 0) * 100, 2) AS mom_change_pct,
  ROUND(ytd.ytd_cost, 2) AS year_to_date_cost,
  cm.days_in_month AS days_reported
FROM current_month cm
CROSS JOIN previous_month pm
CROSS JOIN ytd
```

---

### 查詢 1.2：成本類別分佈（圓餅圖）

**用途**：按成本類別顯示當月支出分佈

```sql
-- 依類別的成本分佈
SELECT 
  cost_category,
  ROUND(SUM(total_cost), 2) AS category_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 2) AS percentage
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY cost_category
ORDER BY category_cost DESC
```

---

### 查詢 1.3：前 10 大成本驅動因素

**用途**：識別最高成本的服務

```sql
-- 前 10 大服務（當月）
SELECT 
  ConsumedService,
  cost_category,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  COUNT(DISTINCT date_key) AS days_active,
  ROUND(AVG(total_cost), 2) AS avg_daily_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 2) AS cost_share_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY ConsumedService, cost_category
ORDER BY monthly_cost DESC
LIMIT 10
```

---

### 查詢 1.4：每日成本趨勢（折線圖）

**用途**：顯示最近 90 天的每日成本趨勢

```sql
-- 每日成本趨勢（最近 90 天）
SELECT 
  TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
  ROUND(SUM(total_cost), 2) AS daily_cost,
  ROUND(AVG(SUM(total_cost)) OVER (ORDER BY date_key ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS ma_7day,
  ROUND(AVG(SUM(total_cost)) OVER (ORDER BY date_key ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS ma_30day
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
GROUP BY date_key
ORDER BY date_key
```

---

### 查詢 1.5：區域成本分佈（地圖視覺化）

**用途**：按 Azure 區域顯示成本分佈

```sql
-- 依區域的成本分佈
SELECT 
  region_group,
  ROUND(SUM(total_cost), 2) AS region_cost,
  COUNT(DISTINCT ConsumedService) AS services_count,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 2) AS cost_percentage
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY region_group
ORDER BY region_cost DESC
```

---

## 2️⃣ FinOps 團隊儀表板

### 查詢 2.1：每日成本異常警報

**用途**：識別今日的成本異常

```sql
-- 今日成本異常
WITH daily_stats AS (
  SELECT 
    ConsumedService,
    cost_category,
    AVG(total_cost) AS avg_cost,
    STDDEV(total_cost) AS stddev_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key BETWEEN CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT) 
    AND CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 1), 'yyyyMMdd') AS INT)
  GROUP BY ConsumedService, cost_category
  HAVING COUNT(*) >= 20
),
today_costs AS (
  SELECT 
    ConsumedService,
    cost_category,
    SUM(total_cost) AS today_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key = CAST(DATE_FORMAT(CURRENT_DATE() - INTERVAL 1 DAY, 'yyyyMMdd') AS INT)
  GROUP BY ConsumedService, cost_category
)
SELECT 
  tc.ConsumedService,
  tc.cost_category,
  ROUND(tc.today_cost, 2) AS today_cost,
  ROUND(ds.avg_cost, 2) AS baseline_avg,
  ROUND((tc.today_cost - ds.avg_cost) / NULLIF(ds.stddev_cost, 0), 2) AS z_score,
  ROUND(tc.today_cost - ds.avg_cost, 2) AS deviation,
  CASE 
    WHEN ABS((tc.today_cost - ds.avg_cost) / NULLIF(ds.stddev_cost, 0)) > 3 THEN '🔴 嚴重'
    WHEN ABS((tc.today_cost - ds.avg_cost) / NULLIF(ds.stddev_cost, 0)) > 2 THEN '🟡 警告'
    ELSE '🟢 正常'
  END AS status
FROM today_costs tc
JOIN daily_stats ds ON tc.ConsumedService = ds.ConsumedService AND tc.cost_category = ds.cost_category
WHERE ABS((tc.today_cost - ds.avg_cost) / NULLIF(ds.stddev_cost, 0)) > 2
ORDER BY z_score DESC
```

---

### 查詢 2.2：標籤覆蓋率儀表板

**用途**：監控標籤合規性

```sql
-- 標籤覆蓋率摘要
SELECT 
  'Cost Center' AS tag_type,
  COUNT(DISTINCT ResourceName) AS total_resources,
  COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) AS tagged_resources,
  ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS coverage_pct,
  ROUND(SUM(CASE WHEN tag_cost_center IS NULL THEN CostInBillingCurrency ELSE 0 END), 2) AS untagged_cost
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)

UNION ALL

SELECT 
  'Environment' AS tag_type,
  COUNT(DISTINCT ResourceName) AS total_resources,
  COUNT(DISTINCT CASE WHEN tag_environment IS NOT NULL THEN ResourceName END) AS tagged_resources,
  ROUND(COUNT(DISTINCT CASE WHEN tag_environment IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS coverage_pct,
  ROUND(SUM(CASE WHEN tag_environment IS NULL THEN CostInBillingCurrency ELSE 0 END), 2) AS untagged_cost
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)

UNION ALL

SELECT 
  'Owner' AS tag_type,
  COUNT(DISTINCT ResourceName) AS total_resources,
  COUNT(DISTINCT CASE WHEN tag_owner IS NOT NULL THEN ResourceName END) AS tagged_resources,
  ROUND(COUNT(DISTINCT CASE WHEN tag_owner IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS coverage_pct,
  ROUND(SUM(CASE WHEN tag_owner IS NULL THEN CostInBillingCurrency ELSE 0 END), 2) AS untagged_cost
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)
```

---

### 查詢 2.3：新資源監控

**用途**：追蹤最近建立的資源

```sql
-- 最近 7 天建立的新資源
WITH resource_first_seen AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    cost_category,
    MIN(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS first_seen_date,
    SUM(CostInBillingCurrency) AS total_cost_since_creation,
    COUNT(DISTINCT date_key) AS days_active
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category
)
SELECT 
  first_seen_date,
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  days_active,
  ROUND(total_cost_since_creation, 2) AS total_cost,
  ROUND(total_cost_since_creation / NULLIF(days_active, 0), 2) AS avg_daily_cost,
  CASE 
    WHEN total_cost_since_creation > 1000 THEN '🔴 高成本'
    WHEN total_cost_since_creation > 100 THEN '🟡 中等成本'
    ELSE '🟢 低成本'
  END AS cost_level
FROM resource_first_seen
WHERE first_seen_date >= DATE_SUB(CURRENT_DATE(), 7)
ORDER BY total_cost_since_creation DESC
LIMIT 50
```

---

## 3️⃣ 成本中心儀表板

### 查詢 3.1：成本中心月度摘要

**用途**：按成本中心的月度成本細分

```sql
-- 成本中心月度摘要
SELECT 
  year_month AS month,
  COALESCE(tag_cost_center, 'Unallocated') AS cost_center,
  COALESCE(tag_environment, 'Unknown') AS environment,
  COUNT(DISTINCT ResourceGroup) AS resource_groups,
  COUNT(DISTINCT ResourceName) AS resources,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER (PARTITION BY year_month) * 100, 2) AS cost_share_pct,
  ROUND(LAG(SUM(total_cost)) OVER (PARTITION BY tag_cost_center, tag_environment ORDER BY year_month), 2) AS previous_month_cost,
  ROUND((SUM(total_cost) - LAG(SUM(total_cost)) OVER (PARTITION BY tag_cost_center, tag_environment ORDER BY year_month)) / 
        NULLIF(LAG(SUM(total_cost)) OVER (PARTITION BY tag_cost_center, tag_environment ORDER BY year_month), 0) * 100, 2) AS mom_change_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
GROUP BY month, cost_center, environment
ORDER BY month DESC, monthly_cost DESC
```

---

### 查詢 3.2：成本中心服務細分

**用途**：顯示每個成本中心使用的服務

```sql
-- 依成本中心的服務細分
SELECT 
  tag_cost_center AS cost_center,
  ConsumedService,
  cost_category,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  COUNT(DISTINCT ResourceName) AS resource_count,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER (PARTITION BY tag_cost_center) * 100, 2) AS service_share_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  AND tag_cost_center IS NOT NULL
GROUP BY cost_center, ConsumedService, cost_category
ORDER BY cost_center, monthly_cost DESC
```

---

## 4️⃣ 優化儀表板

### 查詢 4.1：閒置資源

**用途**：識別產生成本但無使用量的資源

```sql
-- 閒置資源（最近 30 天）
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  tag_cost_center,
  tag_environment,
  ROUND(SUM(CostInBillingCurrency), 2) AS cost_30d,
  SUM(Quantity) AS total_quantity,
  MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS last_seen,
  '刪除或停止' AS recommendation,
  ROUND(SUM(CostInBillingCurrency) * 0.95, 2) AS potential_monthly_savings
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND Quantity = 0
  AND CostInBillingCurrency > 0
GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category, tag_cost_center, tag_environment
HAVING SUM(CostInBillingCurrency) > 10
ORDER BY potential_monthly_savings DESC
LIMIT 50
```

---

### 查詢 4.2：保留實例機會

**用途**：識別適合購買保留實例的工作負載

```sql
-- 保留實例購買機會
WITH on_demand_usage AS (
  SELECT 
    ConsumedService,
    ProductName,
    ResourceLocation,
    year_month AS month,
    SUM(CASE WHEN is_reservation THEN 0 ELSE CostInBillingCurrency END) AS on_demand_cost,
    COUNT(DISTINCT ResourceName) AS resource_count
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
    AND cost_category IN ('Compute', 'Database')
  GROUP BY ConsumedService, ProductName, ResourceLocation, month
)
SELECT 
  ConsumedService,
  ProductName,
  ResourceLocation,
  ROUND(AVG(on_demand_cost), 2) AS avg_monthly_on_demand,
  ROUND(AVG(resource_count), 0) AS avg_resource_count,
  ROUND(AVG(on_demand_cost) * 0.35, 2) AS potential_monthly_savings_35pct,
  ROUND(AVG(on_demand_cost) * 0.35 * 12, 2) AS potential_annual_savings,
  CASE 
    WHEN AVG(on_demand_cost) > 1000 THEN '🔴 高優先級'
    WHEN AVG(on_demand_cost) > 500 THEN '🟡 中優先級'
    ELSE '🟢 低優先級'
  END AS priority
FROM on_demand_usage
GROUP BY ConsumedService, ProductName, ResourceLocation
HAVING AVG(on_demand_cost) > 100
ORDER BY potential_annual_savings DESC
LIMIT 20
```

---

### 查詢 4.3：調整規模機會

**用途**：識別利用率低的運算資源

```sql
-- 調整規模機會
WITH compute_usage AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ProductName,
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    AVG(Quantity) AS avg_daily_hours,
    COUNT(DISTINCT date_key) AS days_active
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyy-MM')
    AND cost_category = 'Compute'
    AND ConsumedService = 'Microsoft.Compute'
  GROUP BY ResourceGroup, ResourceName, ProductName, month
)
SELECT 
  ResourceGroup,
  ResourceName,
  ProductName,
  ROUND(AVG(monthly_cost), 2) AS avg_monthly_cost,
  ROUND(AVG(avg_daily_hours), 2) AS avg_daily_hours,
  ROUND(AVG(avg_daily_hours) / 24 * 100, 2) AS utilization_pct,
  CASE 
    WHEN AVG(avg_daily_hours) < 8 THEN '考慮較小的 SKU 或排程'
    WHEN AVG(avg_daily_hours) < 16 THEN '檢閱使用模式'
    ELSE '使用情況正常'
  END AS recommendation,
  ROUND(AVG(monthly_cost) * 0.30, 2) AS potential_monthly_savings_30pct
FROM compute_usage
GROUP BY ResourceGroup, ResourceName, ProductName
HAVING AVG(monthly_cost) > 50 AND AVG(avg_daily_hours) < 16
ORDER BY potential_monthly_savings_30pct DESC
LIMIT 50
```

---

## 5️⃣ 資源儀表板

### 查詢 5.1：資源詳細清單

**用途**：所有資源的詳細視圖及其成本

```sql
-- 資源詳細清單（最近 30 天）
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  ProductName,
  ResourceLocation,
  tag_cost_center,
  tag_environment,
  tag_owner,
  COUNT(DISTINCT date_key) AS days_active,
  ROUND(SUM(CostInBillingCurrency), 2) AS cost_30d,
  ROUND(AVG(CostInBillingCurrency), 2) AS avg_daily_cost,
  ROUND(SUM(Quantity), 2) AS total_quantity,
  MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS last_seen
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category, ProductName, ResourceLocation, 
         tag_cost_center, tag_environment, tag_owner
HAVING SUM(CostInBillingCurrency) > 1
ORDER BY cost_30d DESC
```

---

### 查詢 5.2：資源群組摘要

**用途**：按資源群組的成本聚合

```sql
-- 資源群組摘要
SELECT 
  ResourceGroup,
  tag_cost_center,
  tag_environment,
  COUNT(DISTINCT ResourceName) AS resource_count,
  COUNT(DISTINCT ConsumedService) AS service_count,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  ROUND(AVG(total_cost), 2) AS avg_daily_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 2) AS cost_share_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY ResourceGroup, tag_cost_center, tag_environment
ORDER BY monthly_cost DESC
```

---

## 6️⃣ 趨勢分析儀表板

### 查詢 6.1：月對月成本趨勢

**用途**：顯示最近 12 個月的成本趨勢

```sql
-- 月對月成本趨勢（最近 12 個月）
WITH monthly_costs AS (
  SELECT 
    year_month AS month,
    cost_category,
    SUM(total_cost) AS monthly_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
  GROUP BY month, cost_category
)
SELECT 
  month,
  cost_category,
  ROUND(monthly_cost, 2) AS monthly_cost,
  ROUND(LAG(monthly_cost) OVER (PARTITION BY cost_category ORDER BY month), 2) AS previous_month,
  ROUND(monthly_cost - LAG(monthly_cost) OVER (PARTITION BY cost_category ORDER BY month), 2) AS mom_change,
  ROUND((monthly_cost - LAG(monthly_cost) OVER (PARTITION BY cost_category ORDER BY month)) / 
        NULLIF(LAG(monthly_cost) OVER (PARTITION BY cost_category ORDER BY month), 0) * 100, 2) AS mom_change_pct,
  ROUND(AVG(monthly_cost) OVER (PARTITION BY cost_category ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS ma_3month
FROM monthly_costs
ORDER BY month DESC, cost_category
```

---

### 查詢 6.2：服務成長趨勢

**用途**：識別成長最快的服務

```sql
-- 服務成長趨勢（最近 6 個月）
WITH service_monthly AS (
  SELECT 
    year_month AS month,
    ConsumedService,
    SUM(total_cost) AS monthly_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
  GROUP BY month, ConsumedService
),
growth_calc AS (
  SELECT 
    ConsumedService,
    MAX(CASE WHEN month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM') THEN monthly_cost END) AS current_month,
    MAX(CASE WHEN month = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM') THEN monthly_cost END) AS last_month,
    MAX(CASE WHEN month = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM') THEN monthly_cost END) AS six_months_ago
  FROM service_monthly
  GROUP BY ConsumedService
)
SELECT 
  ConsumedService,
  ROUND(current_month, 2) AS current_month_cost,
  ROUND(last_month, 2) AS last_month_cost,
  ROUND(six_months_ago, 2) AS six_months_ago_cost,
  ROUND((current_month - last_month) / NULLIF(last_month, 0) * 100, 2) AS mom_growth_pct,
  ROUND((current_month - six_months_ago) / NULLIF(six_months_ago, 0) * 100, 2) AS six_month_growth_pct,
  CASE 
    WHEN (current_month - last_month) / NULLIF(last_month, 0) > 0.5 THEN '🔴 快速成長'
    WHEN (current_month - last_month) / NULLIF(last_month, 0) > 0.2 THEN '🟡 穩定成長'
    WHEN (current_month - last_month) / NULLIF(last_month, 0) < -0.2 THEN '🟢 下降'
    ELSE '➡️ 穩定'
  END AS trend
FROM growth_calc
WHERE current_month IS NOT NULL AND last_month IS NOT NULL
ORDER BY mom_growth_pct DESC
LIMIT 20
```

---

## 📊 儀表板最佳實踐

### 效能優化
* 使用 Gold 層表格進行聚合查詢
* 始終依 `year_month` 或 `date_key` 篩選以利用分區修剪
* 使用 `LIMIT` 限制大型結果集
* 考慮為頻繁查詢建立物化視圖

### 視覺化建議
* **卡片**：KPI 摘要、月對月變化
* **折線圖**：時間趨勢、移動平均
* **長條圖**：服務比較、成本中心排名
* **圓餅圖**：類別分佈、區域分佈
* **表格**：詳細清單、資源詳情

### 更新頻率
* **即時儀表板**：每 5-15 分鐘
* **每日儀表板**：每小時
* **月度報告**：每日
* **趨勢分析**：每週

---

## 🔄 建議的儀表板結構

### 第 1 頁：高階主管概覽
* 月度成本卡片
* 每日趨勢圖
* 前 10 大成本驅動因素
* 類別分佈圓餅圖

### 第 2 頁：營運監控
* 異常警報表
* 新資源追蹤
* 標籤覆蓋率儀表
* 資料品質指標

### 第 3 頁：優化機會
* 閒置資源清單
* 保留實例機會
* 調整規模建議
* 潛在節省摘要

### 第 4 頁：成本分配
* 成本中心細分
* 專案/應用程式成本
* 環境比較
* 未分配成本

---

**最後更新**：2026-02-13  
**版本**：1.0  
**維護者**：FinOps 儀表板團隊
