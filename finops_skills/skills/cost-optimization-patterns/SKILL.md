---
name: 成本優化模式
description: 提供詳細的模式和策略，用於識別和實施基於 FinOps 最佳實踐的 Azure 成本優化機會
---

# 成本優化模式

## 📋 概述

本文件提供詳細的模式和策略，用於識別和實施基於 FinOps 最佳實踐的 Azure 成本優化機會。

---

## 🎯 優化類別

### 1. 調整資源規模機會
### 2. 保留實例與節省方案
### 3. 閒置資源消除
### 4. 儲存優化
### 5. 網路成本降低
### 6. 排程與自動化

---

## 1️⃣ 調整資源規模機會

### 模式 1.1：過大的運算資源

**目標**：識別持續未充分利用的 VM 和運算資源

```sql
-- 尋找成本高但利用率低的運算資源
WITH compute_usage AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    ProductName,
    MeterName,
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    SUM(Quantity) AS total_hours,
    AVG(Quantity) AS avg_daily_hours,
    COUNT(DISTINCT date_key) AS days_active
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyy-MM')
    AND cost_category = 'Compute'
    AND ConsumedService = 'Microsoft.Compute'
  GROUP BY ResourceGroup, ResourceName, ConsumedService, ProductName, MeterName, month
)
SELECT 
  ResourceGroup,
  ResourceName,
  ProductName,
  SUM(monthly_cost) AS total_cost_60d,
  AVG(avg_daily_hours) AS avg_daily_hours,
  AVG(days_active) AS avg_days_per_month,
  ROUND(AVG(avg_daily_hours) / 24 * 100, 2) AS utilization_pct,
  CASE 
    WHEN AVG(avg_daily_hours) < 8 THEN '高優先級：考慮較小的 SKU 或排程'
    WHEN AVG(avg_daily_hours) < 16 THEN '中優先級：檢閱使用模式'
    ELSE '低優先級：使用情況正常'
  END AS recommendation,
  ROUND(SUM(monthly_cost) * 0.30, 2) AS potential_monthly_savings_30pct
FROM compute_usage
WHERE monthly_cost > 50
GROUP BY ResourceGroup, ResourceName, ProductName
HAVING AVG(avg_daily_hours) < 16
ORDER BY potential_monthly_savings_30pct DESC
```

**行動項目**：
* 檢閱每日使用量 < 8 小時的資源
* 考慮將 VM SKU 降低 1-2 級
* 潛在節省：每個資源 20-50%

---

### 模式 1.2：Databricks 叢集優化

**目標**：識別具有優化機會的 Databricks 叢集

```sql
-- 分析 Databricks 運算成本和使用模式
WITH databricks_usage AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ProductName,
    MeterName,
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    SUM(Quantity) AS total_dbu_hours,
    COUNT(DISTINCT date_key) AS days_active,
    AVG(CostInBillingCurrency) AS avg_daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
    AND ConsumedService = 'Microsoft.Databricks'
  GROUP BY ResourceGroup, ResourceName, ProductName, MeterName, month
)
SELECT 
  month,
  ResourceGroup,
  ResourceName,
  ProductName,
  SUM(monthly_cost) AS monthly_cost,
  AVG(total_dbu_hours) AS avg_dbu_hours,
  AVG(days_active) AS days_active,
  CASE 
    WHEN AVG(total_dbu_hours) < 100 THEN '考慮使用 Serverless 或較小叢集'
    WHEN AVG(total_dbu_hours) > 1000 THEN '考慮保留容量或承諾使用折扣'
    ELSE '檢閱自動縮放設定'
  END AS recommendation
FROM databricks_usage
GROUP BY month, ResourceGroup, ResourceName, ProductName
HAVING SUM(monthly_cost) > 100
ORDER BY month DESC, monthly_cost DESC
```

**行動項目**：
* 啟用叢集自動縮放
* 設定自動終止閒置叢集
* 考慮 Databricks 承諾使用折扣
* 潛在節省：30-60%

---

## 2️⃣ 保留實例與節省方案

### 模式 2.1：保留實例覆蓋率分析

**目標**：識別適合購買保留實例的穩定工作負載

```sql
-- 分析保留實例覆蓋率和機會
WITH reservation_analysis AS (
  SELECT 
    ConsumedService,
    ProductName,
    ResourceLocation,
    year_month AS month,
    SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END) AS reserved_cost,
    SUM(CASE WHEN is_reservation THEN 0 ELSE CostInBillingCurrency END) AS on_demand_cost,
    SUM(CostInBillingCurrency) AS total_cost,
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
  AVG(on_demand_cost) AS avg_monthly_on_demand,
  AVG(reserved_cost) AS avg_monthly_reserved,
  AVG(total_cost) AS avg_monthly_total,
  ROUND(AVG(reserved_cost) / NULLIF(AVG(total_cost), 0) * 100, 2) AS current_reservation_pct,
  ROUND(AVG(on_demand_cost) * 0.30, 2) AS potential_monthly_savings_30pct,
  ROUND(AVG(on_demand_cost) * 0.30 * 12, 2) AS potential_annual_savings,
  CASE 
    WHEN AVG(on_demand_cost) > 1000 AND AVG(reserved_cost) / NULLIF(AVG(total_cost), 0) < 0.5 
      THEN '高優先級：大量隨選支出'
    WHEN AVG(on_demand_cost) > 500 
      THEN '中優先級：考慮保留實例'
    ELSE '低優先級：成本較低'
  END AS priority
FROM reservation_analysis
GROUP BY ConsumedService, ProductName, ResourceLocation
HAVING AVG(on_demand_cost) > 100
ORDER BY potential_annual_savings DESC
```

**行動項目**：
* 針對穩定工作負載購買 1 年或 3 年保留實例
* 保留實例通常可節省 30-70%
* 優先處理高成本、穩定的資源

---

## 3️⃣ 閒置資源消除

### 模式 3.1：閒置或未使用的資源

**目標**：識別產生成本但未使用的資源

```sql
-- 尋找閒置或低使用率的資源
WITH resource_usage AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    cost_category,
    COUNT(DISTINCT date_key) AS days_with_cost,
    SUM(CostInBillingCurrency) AS total_cost_30d,
    SUM(Quantity) AS total_quantity,
    AVG(CostInBillingCurrency) AS avg_daily_cost,
    MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS last_seen
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category
)
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  days_with_cost,
  ROUND(total_cost_30d, 2) AS cost_30d,
  ROUND(total_quantity, 2) AS total_quantity,
  last_seen,
  CASE 
    WHEN total_quantity = 0 AND total_cost_30d > 0 THEN '🔴 閒置：有成本但無使用量'
    WHEN total_quantity < 10 AND total_cost_30d > 50 THEN '🟡 低使用率：考慮刪除'
    WHEN days_with_cost < 5 THEN '🟡 很少使用：考慮按需使用'
    ELSE '✅ 正常使用'
  END AS status,
  ROUND(total_cost_30d * 0.90, 2) AS potential_monthly_savings
FROM resource_usage
WHERE (total_quantity = 0 AND total_cost_30d > 0)
   OR (total_quantity < 10 AND total_cost_30d > 50)
   OR days_with_cost < 5
ORDER BY potential_monthly_savings DESC
LIMIT 100
```

**行動項目**：
* 刪除或停止閒置資源
* 檢閱低使用率資源的業務需求
* 潛在節省：90-100% 的閒置資源成本

---

## 4️⃣ 儲存優化

### 模式 4.1：儲存層級優化

**目標**：識別可移至較便宜儲存層級的資料

```sql
-- 分析儲存成本和使用模式
WITH storage_analysis AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ProductName,
    MeterName,
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    SUM(Quantity) AS total_gb_month,
    AVG(CostInBillingCurrency) AS avg_daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
    AND cost_category = 'Storage'
    AND MeterName LIKE '%Storage%'
  GROUP BY ResourceGroup, ResourceName, ProductName, MeterName, month
)
SELECT 
  ResourceGroup,
  ResourceName,
  ProductName,
  AVG(monthly_cost) AS avg_monthly_cost,
  AVG(total_gb_month) AS avg_gb_stored,
  CASE 
    WHEN ProductName LIKE '%Premium%' AND AVG(monthly_cost) > 100 
      THEN '考慮移至標準層級'
    WHEN ProductName LIKE '%Hot%' AND AVG(monthly_cost) > 50 
      THEN '考慮移至 Cool 或 Archive 層級'
    WHEN AVG(total_gb_month) > 1000 
      THEN '檢閱資料保留政策'
    ELSE '目前層級適當'
  END AS recommendation,
  ROUND(AVG(monthly_cost) * 0.40, 2) AS potential_monthly_savings_40pct
FROM storage_analysis
GROUP BY ResourceGroup, ResourceName, ProductName
HAVING AVG(monthly_cost) > 50
ORDER BY potential_monthly_savings_40pct DESC
```

**行動項目**：
* 將不常存取的資料移至 Cool 或 Archive 層級
* 實施生命週期管理政策
* 刪除舊的快照和備份
* 潛在節省：40-80%

---

## 5️⃣ 網路成本降低

### 模式 5.1：跨區域資料傳輸

**目標**：識別昂貴的跨區域資料傳輸

```sql
-- 分析網路和資料傳輸成本
SELECT 
  ResourceGroup,
  ResourceLocation,
  ProductName,
  MeterName,
  year_month AS month,
  SUM(CostInBillingCurrency) AS monthly_cost,
  SUM(Quantity) AS total_gb_transferred,
  ROUND(SUM(CostInBillingCurrency) / NULLIF(SUM(Quantity), 0), 4) AS cost_per_gb,
  CASE 
    WHEN MeterName LIKE '%Outbound%' OR MeterName LIKE '%Egress%' 
      THEN '考慮使用 CDN 或快取'
    WHEN MeterName LIKE '%Inter-Region%' 
      THEN '考慮資源共置'
    ELSE '檢閱網路架構'
  END AS recommendation
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
  AND cost_category = 'Network'
  AND CostInBillingCurrency > 0
GROUP BY ResourceGroup, ResourceLocation, ProductName, MeterName, month
HAVING SUM(CostInBillingCurrency) > 50
ORDER BY monthly_cost DESC
```

**行動項目**：
* 將相關資源共置於同一區域
* 使用 Azure CDN 減少出站流量
* 優化資料傳輸模式
* 潛在節省：30-60%

---

## 6️⃣ 排程與自動化

### 模式 6.1：非生產環境排程

**目標**：識別可在非工作時間關閉的資源

```sql
-- 識別非生產環境的運算資源
WITH non_prod_resources AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    tag_environment,
    ProductName,
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    COUNT(DISTINCT CAST(Date AS DATE)) AS days_active
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 60)
    AND cost_category = 'Compute'
    AND (tag_environment IN ('dev', 'test', 'qa', 'staging')
         OR ResourceGroup LIKE '%dev%'
         OR ResourceGroup LIKE '%test%')
  GROUP BY ResourceGroup, ResourceName, ConsumedService, tag_environment, ProductName, month
)
SELECT 
  ResourceGroup,
  ResourceName,
  tag_environment,
  ProductName,
  AVG(monthly_cost) AS avg_monthly_cost,
  ROUND(AVG(monthly_cost) * 0.65, 2) AS potential_monthly_savings_65pct,
  '實施 12x5 排程（工作日 8AM-8PM）' AS recommendation
FROM non_prod_resources
GROUP BY ResourceGroup, ResourceName, tag_environment, ProductName
HAVING AVG(monthly_cost) > 50
ORDER BY potential_monthly_savings_65pct DESC
```

**行動項目**：
* 在非工作時間關閉開發/測試環境
* 實施自動啟動/停止排程
* 週末完全關閉
* 潛在節省：60-75%

---

## 📊 綜合優化機會摘要

```sql
-- 所有優化類別的摘要
SELECT 
  '調整資源規模' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.30, 2) AS potential_savings,
  '30%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND cost_category = 'Compute'
  AND Quantity / 24 < 0.5  -- 低利用率

UNION ALL

SELECT 
  '保留實例' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.40, 2) AS potential_savings,
  '40%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND cost_category IN ('Compute', 'Database')
  AND is_reservation = FALSE

UNION ALL

SELECT 
  '閒置資源' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.90, 2) AS potential_savings,
  '90%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND Quantity = 0
  AND CostInBillingCurrency > 0

ORDER BY potential_savings DESC
```

---

## 🎯 優化優先級矩陣

| 優化類型 | 實施難度 | 潛在節省 | 優先級 |
|---------|---------|---------|--------|
| 閒置資源消除 | 低 | 90%+ | 🔴 高 |
| 非生產環境排程 | 低 | 60-75% | 🔴 高 |
| 保留實例 | 中 | 30-70% | 🟡 中 |
| 調整資源規模 | 中 | 20-50% | 🟡 中 |
| 儲存層級優化 | 中 | 40-80% | 🟡 中 |
| 網路優化 | 高 | 30-60% | 🟢 低 |

---

## 📅 建議的優化週期

* **每週**：檢閱閒置資源和異常支出
* **每月**：分析調整規模機會和保留實例覆蓋率
* **每季**：全面優化審查和策略調整
* **每年**：保留實例續約和長期承諾評估

---

**最後更新**：2026-02-13  
**版本**：1.0  
**維護者**：FinOps 優化團隊
