---
name: FinOps KPI 指標
description: 定義用於衡量 FinOps 成熟度和效能的關鍵績效指標（KPI），並提供 SQL 查詢來追蹤每個指標的時間趨勢
---

# FinOps KPI 指標

## 📋 概述

本文件定義用於衡量 FinOps 成熟度和效能的關鍵績效指標（KPI），並提供 SQL 查詢來追蹤每個指標的時間趨勢。

## 🤖 聊天機器人問答映射 (Chatbot QA Mapping)

下表協助 Assistant 將使用者的自然語言提問映射至特定的 KPI 查詢：

| 使用者提問 (User Question) | 相關 KPI | 查詢代碼 |
| :--- | :--- | :--- |
| "我們的成本效率如何？", "每個用戶的成本是多少？" | **單位成本 (Unit Economics)** | `KPI 1.1` |
| "我們的 RI 買得夠多嗎？", "承諾覆蓋率是多少？" | **承諾覆蓋率 (Commitment Coverage)** | `KPI 1.2` |
| "我們省了多少錢？", "優化有效果嗎？" | **成本效率比率** | `KPI 1.3` |
| "所有資源都有標籤嗎？", "哪些資源沒貼標籤？" | **標籤覆蓋率** | `KPI 2.1` |
| "成本資料是最新的嗎？", "資料延遲多久？" | **成本可見性時效性** | `KPI 2.2` |
| "我們還有多少節省空間？", "有哪些優化機會？" | **已識別的節省機會** | `KPI 3.1` |
| "這個月的預算爆了嗎？", "預算偏差是多少？" | **預算準確度** | `KPI 4.2` |
| "雲端成本佔營收多少？" | **雲端成本佔收入比** | `KPI 6.1` |
| "我們的 FinOps 成熟度幾分？" | **FinOps 成熟度計分卡** | `Scorecard` |

---

## 🎯 KPI 類別

### 1. 成本效率指標
### 2. 成本可視化指標
### 3. 成本優化指標
### 4. 營運指標
### 5. 治理指標
### 6. 業務價值指標

---

## 1️⃣ 成本效率指標

### KPI 1.1：單位成本（Unit Economics）

**定義**：每個業務單位的雲端成本

**計算公式**：總雲端成本 / 業務指標（例如：使用者數、交易數）

```sql
-- 每月單位成本趨勢
WITH monthly_costs AS (
  SELECT 
    year_month AS month,
    SUM(CostInBillingCurrency) AS total_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
  GROUP BY month
),
business_metrics AS (
  -- 替換為您的實際業務指標
  SELECT 
    month,
    active_users,
    transactions
  FROM your_business_metrics_table
)
SELECT 
  mc.month,
  ROUND(mc.total_cost, 2) AS total_cost,
  bm.active_users,
  bm.transactions,
  ROUND(mc.total_cost / NULLIF(bm.active_users, 0), 2) AS cost_per_user,
  ROUND(mc.total_cost / NULLIF(bm.transactions, 0), 4) AS cost_per_transaction
FROM monthly_costs mc
LEFT JOIN business_metrics bm ON mc.month = bm.month
ORDER BY mc.month DESC
```

**目標**：單位成本逐月下降或保持穩定

---

### KPI 1.2：保留實例覆蓋率

**定義**：保留實例成本佔總運算成本的百分比

**計算公式**：保留實例成本 / 總運算成本 × 100%

```sql
-- 承諾覆蓋率趨勢 (Reserved + Savings Plan)
SELECT 
  year_month AS month,
  cost_category,
  ROUND(SUM(reservation_cost + savingplan_cost), 2) AS commitment_cost,
  ROUND(SUM(total_cost), 2) AS total_cost,
  ROUND(SUM(reservation_cost + savingplan_cost) / 
        NULLIF(SUM(total_cost), 0) * 100, 2) AS commitment_coverage_pct,
  ROUND((SUM(reservation_cost + savingplan_cost) / 
         NULLIF(SUM(total_cost), 0) * 100) - 
        LAG(SUM(reservation_cost + savingplan_cost) / 
            NULLIF(SUM(total_cost), 0) * 100) OVER (PARTITION BY cost_category ORDER BY year_month), 2) AS mom_change
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
  AND cost_category IN ('Compute', 'Database')
GROUP BY month, cost_category
ORDER BY month DESC, cost_category
```

**目標**：運算工作負載 > 70%，資料庫工作負載 > 80%

---

### KPI 1.3：成本效率比率

**定義**：優化後的成本節省與總成本的比率

```sql
-- 成本效率改善追蹤
WITH baseline_cost AS (
  SELECT 
    SUM(CostInBillingCurrency) AS baseline
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key BETWEEN CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 395), 'yyyyMMdd') AS INT) AND CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyyMMdd') AS INT)
),
current_cost AS (
  SELECT 
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
  GROUP BY month
)
SELECT 
  cc.month,
  ROUND(cc.monthly_cost, 2) AS current_cost,
  ROUND(bc.baseline / 12, 2) AS baseline_monthly,
  ROUND(bc.baseline / 12 - cc.monthly_cost, 2) AS savings,
  ROUND((bc.baseline / 12 - cc.monthly_cost) / NULLIF(bc.baseline / 12, 0) * 100, 2) AS efficiency_improvement_pct
FROM current_cost cc
CROSS JOIN baseline_cost bc
ORDER BY cc.month DESC
```

**目標**：年度效率改善 > 10%

---

## 2️⃣ 成本可視化指標

### KPI 2.1：標籤覆蓋率

**定義**：具有必要標籤的資源百分比

```sql
-- 標籤覆蓋率 KPI
SELECT 
  year_month AS month,
  COUNT(DISTINCT ResourceName) AS total_resources,
  COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) AS tagged_cost_center,
  COUNT(DISTINCT CASE WHEN tag_environment IS NOT NULL THEN ResourceName END) AS tagged_environment,
  COUNT(DISTINCT CASE WHEN tag_owner IS NOT NULL THEN ResourceName END) AS tagged_owner,
  COUNT(DISTINCT CASE 
    WHEN tag_cost_center IS NOT NULL 
     AND tag_environment IS NOT NULL 
     AND tag_owner IS NOT NULL 
    THEN ResourceName 
  END) AS fully_tagged,
  ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS cost_center_coverage_pct,
  ROUND(COUNT(DISTINCT CASE 
    WHEN tag_cost_center IS NOT NULL 
     AND tag_environment IS NOT NULL 
     AND tag_owner IS NOT NULL 
    THEN ResourceName 
  END) / NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS full_tag_coverage_pct
  END) / NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS full_tag_coverage_pct
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
GROUP BY month
ORDER BY month DESC
```

**目標**：完整標籤覆蓋率 > 90%

---

### KPI 2.2：成本可見性時效性

**定義**：成本資料的新鮮度（資料延遲天數）

```sql
-- 資料新鮮度 KPI
SELECT 
  'Bronze Layer' AS layer,
  MAX(CAST(Date AS DATE)) AS latest_date,
  DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) <= 1 THEN '✅ 符合 SLA'
    WHEN DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) <= 2 THEN '🟡 接近 SLA'
    ELSE '🔴 違反 SLA'
  END AS sla_status
FROM develop_catalog.system_report.infra_azure_cost_usage_actual

UNION ALL

SELECT 
  'Silver Layer' AS layer,
  TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd') AS latest_date,
  DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 1 THEN '✅ 符合 SLA'
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 2 THEN '🟡 接近 SLA'
    ELSE '🔴 違反 SLA'
  END AS sla_status
FROM develop_catalog.system_report.infra_azure_cost_silver

UNION ALL

SELECT 
  'Gold Layer' AS layer,
  TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd') AS latest_date,
  DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 1 THEN '✅ 符合 SLA'
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 2 THEN '🟡 接近 SLA'
    ELSE '🔴 違反 SLA'
  END AS sla_status
FROM develop_catalog.system_report.finops_daily_cost_summary
```

**目標**：資料延遲 < 1 天

---

## 3️⃣ 成本優化指標

### KPI 3.1：已識別的節省機會

**定義**：透過優化分析識別的潛在節省金額

```sql
-- 優化機會追蹤
WITH idle_resources AS (
  SELECT 
    'Idle Resources' AS opportunity_type,
    COUNT(DISTINCT ResourceName) AS resource_count,
    SUM(CostInBillingCurrency) * 0.90 AS potential_savings
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
    AND Quantity = 0 AND CostInBillingCurrency > 0
),
rightsizing AS (
  SELECT 
    'Right-Sizing' AS opportunity_type,
    COUNT(DISTINCT ResourceName) AS resource_count,
    SUM(CostInBillingCurrency) * 0.30 AS potential_savings
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
    AND cost_category = 'Compute'
    AND Quantity / 24 < 0.5
),
reservation_opportunities AS (
  SELECT 
    'Reservation Purchase' AS opportunity_type,
    COUNT(DISTINCT ResourceName) AS resource_count,
    SUM(CostInBillingCurrency) * 0.40 AS potential_savings
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
    AND cost_category IN ('Compute', 'Database')
    AND is_reservation = FALSE
)
SELECT 
  opportunity_type,
  resource_count,
  ROUND(potential_savings, 2) AS monthly_potential_savings,
  ROUND(potential_savings * 12, 2) AS annual_potential_savings
FROM (
  SELECT * FROM idle_resources
  UNION ALL
  SELECT * FROM rightsizing
  UNION ALL
  SELECT * FROM reservation_opportunities
)
ORDER BY monthly_potential_savings DESC
```

**目標**：每月識別 > 總成本的 10% 節省機會

---

### KPI 3.2：已實現的節省

**定義**：透過優化行動實際節省的金額

```sql
-- 已實現節省追蹤（需要優化行動追蹤表）
WITH monthly_baseline AS (
  SELECT 
    AVG(daily_cost) * 30 AS baseline_monthly_cost
  FROM (
    SELECT 
      TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    SUM(CostInBillingCurrency) AS daily_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key BETWEEN CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT) AND CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyyMMdd') AS INT)
  GROUP BY date
  )
),
current_monthly AS (
  SELECT 
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyy-MM')
  GROUP BY month
)
SELECT 
  cm.month,
  ROUND(mb.baseline_monthly_cost, 2) AS baseline_cost,
  ROUND(cm.monthly_cost, 2) AS actual_cost,
  ROUND(mb.baseline_monthly_cost - cm.monthly_cost, 2) AS realized_savings,
  ROUND((mb.baseline_monthly_cost - cm.monthly_cost) / NULLIF(mb.baseline_monthly_cost, 0) * 100, 2) AS savings_pct
FROM current_monthly cm
CROSS JOIN monthly_baseline mb
ORDER BY cm.month DESC
```

**目標**：實現 > 50% 的已識別節省機會

---

## 4️⃣ 營運指標

### KPI 4.1：異常檢測回應時間

**定義**：從異常檢測到解決的平均時間

```sql
-- 異常回應時間（需要異常追蹤表）
-- 這是一個範例結構
SELECT 
  DATE_FORMAT(detected_date, 'yyyy-MM') AS month,
  COUNT(*) AS total_anomalies,
  COUNT(CASE WHEN resolved_date IS NOT NULL THEN 1 END) AS resolved_anomalies,
  ROUND(AVG(DATEDIFF(resolved_date, detected_date)), 1) AS avg_resolution_days,
  ROUND(COUNT(CASE WHEN resolved_date IS NOT NULL THEN 1 END) / NULLIF(COUNT(*), 0) * 100, 2) AS resolution_rate_pct
FROM your_anomaly_tracking_table
WHERE detected_date >= DATE_SUB(CURRENT_DATE(), 180)
GROUP BY month
ORDER BY month DESC
```

**目標**：平均解決時間 < 3 天，解決率 > 95%

---

### KPI 4.2：預算準確度

**定義**：實際成本與預算的偏差百分比

```sql
-- 預算 vs 實際（需要預算表）
WITH monthly_actual AS (
  SELECT 
    year_month AS month,
    tag_cost_center,
    SUM(CostInBillingCurrency) AS actual_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
  GROUP BY month, tag_cost_center
),
monthly_budget AS (
  SELECT 
    month,
    cost_center,
    budget_amount
  FROM your_budget_table
  WHERE month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
)
SELECT 
  ma.month,
  ma.tag_cost_center AS cost_center,
  ROUND(mb.budget_amount, 2) AS budget,
  ROUND(ma.actual_cost, 2) AS actual,
  ROUND(ma.actual_cost - mb.budget_amount, 2) AS variance,
  ROUND((ma.actual_cost - mb.budget_amount) / NULLIF(mb.budget_amount, 0) * 100, 2) AS variance_pct,
  CASE 
    WHEN ABS((ma.actual_cost - mb.budget_amount) / NULLIF(mb.budget_amount, 0)) <= 0.05 THEN '✅ 在範圍內'
    WHEN ABS((ma.actual_cost - mb.budget_amount) / NULLIF(mb.budget_amount, 0)) <= 0.10 THEN '🟡 接近限制'
    ELSE '🔴 超出範圍'
  END AS status
FROM monthly_actual ma
LEFT JOIN monthly_budget mb ON ma.month = mb.month AND ma.tag_cost_center = mb.cost_center
ORDER BY ma.month DESC, variance_pct DESC
```

**目標**：預算偏差 < ±5%

---

## 5️⃣ 治理指標

### KPI 5.1：政策合規率

**定義**：符合 FinOps 政策的資源百分比

```sql
-- 政策合規檢查
WITH compliance_checks AS (
  SELECT 
    year_month AS month,
    COUNT(DISTINCT ResourceName) AS total_resources,
    -- 標籤合規
    COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) AS tagged_resources,
    -- 命名慣例合規
    COUNT(DISTINCT CASE WHEN ResourceName RLIKE '^[a-z0-9-]+$' THEN ResourceName END) AS naming_compliant,
    -- 非生產環境應有適當標籤
    COUNT(DISTINCT CASE 
      WHEN tag_environment IN ('dev', 'test', 'qa') 
       AND ResourceGroup LIKE '%nonprod%' 
      THEN ResourceName 
    END) AS env_compliant
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
  GROUP BY month
)
SELECT 
  month,
  total_resources,
  ROUND(tagged_resources / NULLIF(total_resources, 0) * 100, 2) AS tag_compliance_pct,
  ROUND(naming_compliant / NULLIF(total_resources, 0) * 100, 2) AS naming_compliance_pct,
  ROUND((tagged_resources + naming_compliant) / NULLIF(total_resources * 2, 0) * 100, 2) AS overall_compliance_pct
FROM compliance_checks
ORDER BY month DESC
```

**目標**：整體合規率 > 90%

---

## 6️⃣ 業務價值指標

### KPI 6.1：雲端成本佔收入比

**定義**：雲端成本佔總收入的百分比

```sql
-- 雲端成本佔收入比（需要收入資料）
WITH monthly_costs AS (
  SELECT 
    year_month AS month,
    ROUND(SUM(total_cost), 2) AS total_cost,
  ROUND(SUM(reservation_cost), 2) AS reserved_cost,
  ROUND(SUM(spot_cost), 2) AS spot_cost,
  ROUND(SUM(savingplan_cost), 2) AS saving_plan_cost,
  ROUND(SUM(on_demand_cost), 2) AS on_demand_cost,
  ROUND((SUM(reservation_cost) + SUM(savingplan_cost)) / SUM(total_cost) * 100, 2) AS commitment_coverage_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
GROUP BY month
),
monthly_revenue AS (
  SELECT 
    month,
    revenue
  FROM your_revenue_table
  WHERE month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
)
SELECT 
  mc.month,
  ROUND(mc.total_cost, 2) AS cloud_cost,
  ROUND(mr.revenue, 2) AS revenue,
  ROUND(mc.total_cost / NULLIF(mr.revenue, 0) * 100, 4) AS cost_of_revenue_pct,
  ROUND((mc.total_cost / NULLIF(mr.revenue, 0) * 100) - 
        LAG(mc.total_cost / NULLIF(mr.revenue, 0) * 100) OVER (ORDER BY mc.month), 4) AS mom_change
FROM monthly_costs mc
LEFT JOIN monthly_revenue mr ON mc.month = mr.month
ORDER BY mc.month DESC
```

**目標**：趨勢穩定或下降

---

## 📊 FinOps 成熟度計分卡

```sql
-- 綜合 FinOps 成熟度評分
WITH kpi_scores AS (
  SELECT 
    'Tag Coverage' AS kpi_name,
    ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
          NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 0) AS score,
    90 AS target,
    CASE 
      WHEN COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
           NULLIF(COUNT(DISTINCT ResourceName), 0) >= 0.90 THEN '✅'
      WHEN COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
           NULLIF(COUNT(DISTINCT ResourceName), 0) >= 0.70 THEN '🟡'
      ELSE '🔴'
    END AS status
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  
  UNION ALL
  
  SELECT 
    'Commitment Coverage' AS kpi_name,
    ROUND(SUM(reservation_cost + savingplan_cost) / 
          NULLIF(SUM(total_cost), 0) * 100, 0) AS score,
    70 AS target,
    CASE 
      WHEN SUM(reservation_cost + savingplan_cost) / 
           NULLIF(SUM(total_cost), 0) >= 0.70 THEN '✅'
      WHEN SUM(reservation_cost + savingplan_cost) / 
           NULLIF(SUM(total_cost), 0) >= 0.50 THEN '🟡'
      ELSE '🔴'
    END AS status
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
    AND cost_category IN ('Compute', 'Database')
)
SELECT 
  kpi_name,
  score,
  target,
  status,
  CASE 
    WHEN score >= target THEN '達標'
    WHEN score >= target * 0.8 THEN '接近目標'
    ELSE '需改善'
  END AS performance
FROM kpi_scores
```

---

## 🎯 FinOps 成熟度等級

| 等級 | 描述 | 關鍵指標 |
|------|------|---------|
| **爬行** | 基本可視化 | 標籤覆蓋率 > 50%，資料延遲 < 3 天 |
| **行走** | 主動優化 | 標籤覆蓋率 > 80%，保留實例覆蓋率 > 50%，已識別節省 > 5% |
| **奔跑** | 持續優化 | 標籤覆蓋率 > 90%，保留實例覆蓋率 > 70%，已實現節省 > 10%，預算偏差 < 5% |

---

## 📅 KPI 報告排程

* **每日**：資料新鮮度、異常檢測
* **每週**：成本趨勢、優化機會
* **每月**：完整 KPI 儀表板、成熟度評分
* **每季**：業務審查、策略調整

---

**最後更新**：2026-02-13  
**版本**：1.0  
**維護者**：FinOps KPI 團隊
