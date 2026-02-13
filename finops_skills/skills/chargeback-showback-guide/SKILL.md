---
name: 成本回收與展示指南
description: 提供實施 Azure 雲端成本回收和展示模型的完整指南，實現跨團隊和部門的準確成本分配和責任歸屬
---

# 成本回收與展示指南

## 📋 概述

本文件提供實施 Azure 雲端成本回收和展示模型的完整指南，實現跨團隊和部門的準確成本分配和責任歸屬。

---

## 🎯 關鍵概念

### **成本回收（Chargeback）**
* 實際向業務單位收取雲端成本
* 成本從中央 IT 預算轉移到消費團隊
* 需要正式批准和預算分配
* 建立財務責任歸屬

### **成本展示（Showback）**
* 雲端成本的資訊性報告
* 不實際轉移預算
* 提高意識並鼓勵優化
* 通常作為成本回收的前導

---

## 📊 成本分配模型

### 1. 直接分配 - 基於標籤
### 2. 比例分配 - 基於使用量
### 3. 混合分配 - 混合模型
### 4. 共享服務分配

---

## 1️⃣ 直接分配（基於標籤）

### 模型 1.1：成本中心分配

**原則**：根據成本中心標籤直接分配成本

```sql
-- 依成本中心的月度成本分配
SELECT 
  year_month AS billing_month,
  COALESCE(tag_cost_center, 'Unallocated') AS cost_center,
  COALESCE(tag_environment, 'Unknown') AS environment,
  cost_category,
  COUNT(DISTINCT ResourceGroup) AS resource_groups,
  COUNT(DISTINCT ResourceName) AS resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS total_cost,
  ROUND(SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END), 2) AS reserved_cost,
  ROUND(SUM(CASE WHEN is_reservation THEN 0 ELSE CostInBillingCurrency END), 2) AS on_demand_cost,
  ROUND(SUM(CostInBillingCurrency) / SUM(SUM(CostInBillingCurrency)) OVER (PARTITION BY year_month) * 100, 2) AS cost_share_pct
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
GROUP BY billing_month, cost_center, environment, cost_category
ORDER BY billing_month DESC, total_cost DESC
```

**使用時機**：
* 資源有明確的擁有者標籤
* 標籤覆蓋率 > 80%
* 需要精確的成本歸屬

---

### 模型 1.2：專案/應用程式分配

**原則**：依專案或應用程式標籤分配成本

```sql
-- 依專案的成本分配
WITH project_costs AS (
  SELECT 
    year_month AS month,
    COALESCE(tag_project, tag_application, 'Unallocated') AS project,
    tag_cost_center,
    tag_environment,
    SUM(CostInBillingCurrency) AS monthly_cost,
    COUNT(DISTINCT ResourceName) AS resource_count
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
  GROUP BY month, project, tag_cost_center, tag_environment
)
SELECT 
  month,
  project,
  tag_cost_center AS cost_center,
  tag_environment AS environment,
  resource_count,
  ROUND(monthly_cost, 2) AS monthly_cost,
  ROUND(monthly_cost / SUM(monthly_cost) OVER (PARTITION BY month) * 100, 2) AS cost_share_pct,
  ROUND(AVG(monthly_cost) OVER (PARTITION BY project ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS ma_3month
FROM project_costs
ORDER BY month DESC, monthly_cost DESC
```

---

## 2️⃣ 比例分配（基於使用量）

### 模型 2.1：資源群組比例分配

**原則**：依資源群組的使用比例分配共享成本

```sql
-- 依資源群組的比例成本分配
WITH rg_usage AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    ResourceGroup,
    tag_cost_center,
    SUM(Quantity) AS total_usage,
    SUM(CostInBillingCurrency) AS direct_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
    AND cost_category = 'Compute'
  GROUP BY month, ResourceGroup, tag_cost_center
),
shared_costs AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    SUM(CostInBillingCurrency) AS shared_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
    AND (tag_cost_center IS NULL OR tag_cost_center = 'Shared')
  GROUP BY month
)
SELECT 
  rg.month,
  rg.ResourceGroup,
  rg.tag_cost_center,
  ROUND(rg.direct_cost, 2) AS direct_cost,
  ROUND(rg.total_usage / SUM(rg.total_usage) OVER (PARTITION BY rg.month) * sc.shared_cost, 2) AS allocated_shared_cost,
  ROUND(rg.direct_cost + (rg.total_usage / SUM(rg.total_usage) OVER (PARTITION BY rg.month) * sc.shared_cost), 2) AS total_allocated_cost
FROM rg_usage rg
JOIN shared_costs sc ON rg.month = sc.month
ORDER BY rg.month DESC, total_allocated_cost DESC
```

---

## 3️⃣ 混合分配（混合模型）

### 模型 3.1：分層分配方法

**原則**：結合直接和比例分配

```sql
-- 分層成本分配
WITH tier1_direct AS (
  -- 第 1 層：直接標記的成本
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    tag_cost_center AS cost_center,
    'Direct' AS allocation_method,
    SUM(CostInBillingCurrency) AS allocated_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
    AND tag_cost_center IS NOT NULL
  GROUP BY month, cost_center
),
tier2_rg_based AS (
  -- 第 2 層：基於資源群組的分配
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    SUBSTRING_INDEX(ResourceGroup, '-', 1) AS cost_center,
    'ResourceGroup' AS allocation_method,
    SUM(CostInBillingCurrency) AS allocated_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
    AND tag_cost_center IS NULL
    AND ResourceGroup IS NOT NULL
  GROUP BY month, cost_center
),
tier3_proportional AS (
  -- 第 3 層：比例分配剩餘成本
  SELECT 
    t1.month,
    t1.cost_center,
    'Proportional' AS allocation_method,
    t1.allocated_cost / SUM(t1.allocated_cost) OVER (PARTITION BY t1.month) * 
      (SELECT SUM(CostInBillingCurrency) 
       FROM develop_catalog.system_report.infra_azure_cost_silver 
       WHERE DATE_FORMAT(Date, 'yyyy-MM') = t1.month 
         AND tag_cost_center IS NULL 
         AND ResourceGroup IS NULL) AS allocated_cost
  FROM tier1_direct t1
)
SELECT 
  month,
  cost_center,
  allocation_method,
  ROUND(allocated_cost, 2) AS allocated_cost
FROM (
  SELECT * FROM tier1_direct
  UNION ALL
  SELECT * FROM tier2_rg_based
  UNION ALL
  SELECT * FROM tier3_proportional
)
ORDER BY month DESC, allocated_cost DESC
```

---

## 4️⃣ 共享服務分配

### 模型 4.1：共享基礎設施成本分配

**原則**：依消費比例分配共享服務成本

```sql
-- 共享服務成本分配
WITH shared_services AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    ConsumedService,
    SUM(CostInBillingCurrency) AS shared_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
    AND (ResourceGroup LIKE '%shared%' OR tag_cost_center = 'Infrastructure')
  GROUP BY month, ConsumedService
),
consumer_usage AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    tag_cost_center AS cost_center,
    SUM(Quantity) AS usage_quantity,
    SUM(CostInBillingCurrency) AS direct_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
    AND tag_cost_center IS NOT NULL
    AND tag_cost_center != 'Infrastructure'
  GROUP BY month, cost_center
)
SELECT 
  cu.month,
  cu.cost_center,
  ROUND(cu.direct_cost, 2) AS direct_cost,
  ROUND(SUM(ss.shared_cost) * (cu.usage_quantity / SUM(cu.usage_quantity) OVER (PARTITION BY cu.month)), 2) AS allocated_shared_cost,
  ROUND(cu.direct_cost + SUM(ss.shared_cost) * (cu.usage_quantity / SUM(cu.usage_quantity) OVER (PARTITION BY cu.month)), 2) AS total_cost
FROM consumer_usage cu
CROSS JOIN shared_services ss
WHERE cu.month = ss.month
GROUP BY cu.month, cu.cost_center, cu.direct_cost, cu.usage_quantity
ORDER BY cu.month DESC, total_cost DESC
```

---

## 📊 成本回收報告範本

### 報告 1：月度成本中心對帳單

```sql
-- 成本中心月度對帳單
SELECT 
  DATE_FORMAT(Date, 'yyyy-MM') AS billing_period,
  tag_cost_center AS cost_center,
  cost_category,
  COUNT(DISTINCT ResourceGroup) AS resource_groups,
  COUNT(DISTINCT ResourceName) AS resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_month_cost,
  ROUND(LAG(SUM(CostInBillingCurrency)) OVER (PARTITION BY tag_cost_center, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM')), 2) AS previous_month_cost,
  ROUND(SUM(CostInBillingCurrency) - LAG(SUM(CostInBillingCurrency)) OVER (PARTITION BY tag_cost_center, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM')), 2) AS mom_change,
  ROUND((SUM(CostInBillingCurrency) - LAG(SUM(CostInBillingCurrency)) OVER (PARTITION BY tag_cost_center, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM'))) / 
        NULLIF(LAG(SUM(CostInBillingCurrency)) OVER (PARTITION BY tag_cost_center, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM')), 0) * 100, 2) AS mom_change_pct
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
  AND tag_cost_center IS NOT NULL
GROUP BY billing_period, tag_cost_center, cost_category
ORDER BY billing_period DESC, current_month_cost DESC
```

---

### 報告 2：未分配成本報告

```sql
-- 未分配成本分析
SELECT 
  DATE_FORMAT(Date, 'yyyy-MM') AS month,
  ResourceGroup,
  ConsumedService,
  cost_category,
  COUNT(DISTINCT ResourceName) AS untagged_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS unallocated_cost,
  ROUND(SUM(CostInBillingCurrency) / SUM(SUM(CostInBillingCurrency)) OVER (PARTITION BY DATE_FORMAT(Date, 'yyyy-MM')) * 100, 2) AS pct_of_total,
  CASE 
    WHEN tag_cost_center IS NULL AND tag_project IS NULL THEN '完全未標記'
    WHEN tag_cost_center IS NULL THEN '缺少成本中心'
    ELSE '其他'
  END AS issue_type
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
  AND tag_cost_center IS NULL
GROUP BY month, ResourceGroup, ConsumedService, cost_category, issue_type
HAVING SUM(CostInBillingCurrency) > 50
ORDER BY month DESC, unallocated_cost DESC
```

---

## 🎯 實施最佳實踐

### 階段 1：展示（Showback）
* **目標**：提高成本意識
* **期間**：3-6 個月
* **行動**：
  * 建立月度成本報告
  * 識別主要成本驅動因素
  * 提高標籤覆蓋率至 > 80%

### 階段 2：軟性回收（Soft Chargeback）
* **目標**：建立責任歸屬
* **期間**：6-12 個月
* **行動**：
  * 設定成本中心預算
  * 追蹤預算與實際差異
  * 實施成本優化計畫

### 階段 3：完全回收（Full Chargeback）
* **目標**：完全財務責任
* **期間**：持續
* **行動**：
  * 實際預算轉移
  * 正式發票流程
  * 持續優化和治理

---

## 📋 標籤策略

### 必要標籤
* `CostCenter`：成本中心代碼
* `Environment`：dev/test/prod
* `Owner`：技術擁有者電子郵件
* `Project`：專案或應用程式名稱

### 選用標籤
* `BusinessUnit`：業務單位
* `Application`：應用程式名稱
* `Criticality`：critical/high/medium/low

---

## 🔄 建議的報告週期

* **每日**：異常成本警報
* **每週**：成本趨勢摘要
* **每月**：正式成本回收報告
* **每季**：預算審查和調整

---

**最後更新**：2026-02-13  
**版本**：1.0  
**維護者**：FinOps 成本分配團隊
