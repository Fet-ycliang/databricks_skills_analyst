---
name: 成本優化模式
description: 提供詳細的模式和策略，用於識別和實施基於 FinOps 最佳實踐的 Azure 成本優化機會
---

# 成本優化模式

## 📋 概述

本文件提供詳細的模式和策略，用於識別和實施基於 FinOps 最佳實踐的 Azure 成本優化機會。

## 🤖 聊天機器人問答映射 (Chatbot QA Mapping)

下表協助 Assistant 將使用者的自然語言提問映射至特定的優化模式：

| 使用者提問 (User Question) | 相關模式 | 查詢代碼 |
| :--- | :--- | :--- |
| "我有閒置的資源嗎？", "哪些 VM 沒在用？" | **閒置資源消除** | `Pattern 3.1` |
| "有些快照是不是沒在用了？", "如何清理孤兒資源？" | **孤兒資源 (快照/磁碟)** | `Pattern 3.2` |
| "我的 VM 規格是不是開太大了？", "調整規模能省多少？" | **調整資源規模 (Right-sizing)** | `Pattern 1.1` |
| "Databricks 叢集成本太高怎麼辦？" | **Databricks 叢集優化** | `Pattern 1.2` |
| "我們是否用了舊款 VM？", "升級 VM 能省錢嗎？" | **VM 世代現代化** | `Pattern 1.3` |
| "Databricks 作業要在哪種叢集跑？" | **Databricks 工作負載對齊** | `Pattern 1.4` |
| "應該買 RI 嗎？", "隨選成本太高了" | **保留實例覆蓋率** | `Pattern 2.1` |
| "非生產環境週末可以關機嗎？" | **排程與自動化** | `Pattern 6.1` |
| "儲存成本怎麼降？", "資料可以放 Cold Tier 嗎？" | **儲存優化** | `Pattern 4.1` |
| "非生產環境需要 GRS 嗎？" | **儲存冗餘優化** | `Pattern 4.2` |
| "幫我檢查所有的優化機會" | **綜合優化機會摘要** | `Summary Query` |

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

### 模式 1.3：VM 世代與 DBU 綜合優化 (VM & DBU Optimization)

**目標**：識別舊世代 (Legacy) VM，但需綜合考量 Databricks DBU 費率與 Spot 實例的可用性 (Availability)

```sql
-- 識別舊世代 VM，並區分 Databricks 與一般 IaaS
SELECT 
  ResourceGroup,
  ResourceName,
  MeterName,
  ConsumedService,
  Location,
  SUM(CostInBillingCurrency) AS monthly_vm_cost,
  -- 判斷是否為 Spot 實例
  MAX(CASE WHEN MeterName LIKE '%Spot%' OR CostInBillingCurrency < 0.1 THEN 1 ELSE 0 END) AS is_spot,
  CASE 
    -- Databricks 特殊邏輯：需考慮 DBU 加乘與 Spot 穩定性
    WHEN ConsumedService = 'Microsoft.Databricks' AND MeterName LIKE '%v3%' 
      THEN 'v3 為舊世代，但在 Spot 模式下可能具有較佳的回收率 (Eviction Rate)，請謹慎評估'
    WHEN ConsumedService = 'Microsoft.Databricks' AND MeterName LIKE '%v4%' 
      THEN 'v4 目前為 Databricks 主流，若非效能瓶頸可維持現狀 (v5 DBU 可能較高)'
    
    -- 一般 IaaS VM 邏輯：追求性價比
    WHEN ConsumedService = 'Microsoft.Compute' AND MeterName LIKE '%v3%' 
      THEN '建議升級至 v5 (性價比提升 ~20%)'
    WHEN ConsumedService = 'Microsoft.Compute' AND MeterName LIKE '%v4%' 
      THEN '考慮升級至 v5'
    ELSE '檢閱'
  END AS recommendation
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyy-MM')
  AND (ConsumedService = 'Microsoft.Compute' OR ConsumedService = 'Microsoft.Databricks')
  AND (MeterName LIKE '%v3%' OR MeterName LIKE '%v4%') 
GROUP BY ResourceGroup, ResourceName, MeterName, ConsumedService, Location
HAVING monthly_vm_cost > 50
ORDER BY monthly_vm_cost DESC
```

**行動項目**：
* **Databricks**：升級前務必計算 `(VM 價格 + DBU 價格)` 的總成本，v5 的 DBU 係數可能較高。
* **Spot 策略**：舊世代 VM (如 v3/v4) 在某些區域的 Spot 容量池 (Capacity Pool) 可能較充裕，若工作負載對中斷敏感，可優先保留舊世代 Spot。
* **一般 VM**：若非 Databricks 節點，原則上 v5 比 v4/v3 更便宜且快。

---

### 模式 1.4：Databricks 工作負載對齊

**目標**：識別在昂貴的互動式 (Interactive/All-Purpose) 叢集上運行的自動化作業

```sql
-- 分析 Databricks 叢集類型使用比例
WITH cluster_stats AS (
  SELECT 
    ResourceName, -- Workspace Name
    SUM(CASE WHEN MeterName LIKE '%Interactive%' OR MeterName LIKE '%All-Purpose%' THEN CostInBillingCurrency ELSE 0 END) AS interactive_cost,
    SUM(CASE WHEN MeterName LIKE '%Jobs%' OR MeterName LIKE '%Automated%' THEN CostInBillingCurrency ELSE 0 END) AS jobs_cost,
    SUM(CostInBillingCurrency) AS total_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
    AND ConsumedService = 'Microsoft.Databricks'
  GROUP BY ResourceName
)
SELECT 
  ResourceName,
  ROUND(interactive_cost, 2) AS interactive_cost,
  ROUND(jobs_cost, 2) AS jobs_cost,
  ROUND(interactive_cost / NULLIF(total_cost, 0) * 100, 1) AS interactive_ratio_pct,
  CASE 
    WHEN interactive_cost / NULLIF(total_cost, 0) > 0.70 THEN '🔴 高互動式比例：請確認是否將 Jobs 跑在互動叢集'
    WHEN interactive_cost / NULLIF(total_cost, 0) > 0.50 THEN '🟡 中互動式比例：檢閱開發習慣'
    ELSE '✅ 比例健康'
  END AS recommendation,
  ROUND(interactive_cost * 0.40, 2) AS potential_savings_migration -- 假設遷移 50% 至 Jobs (Jobs 比 Interactive 便宜約 40-50%)
FROM cluster_stats
WHERE total_cost > 500
ORDER BY interactive_ratio_pct DESC
```

**行動項目**：
* 將定期排程的 Notebooks 遷移至 Databricks Jobs Compute
* Jobs Compute 費率通常比 All-Purpose 低 40-50%

---

## 2️⃣ 保留實例與節省方案

### 模式 2.1：保留實例覆蓋率分析

**目標**：識別適合購買保留實例的穩定工作負載

```sql
-- 分析承諾覆蓋率 (Reserved + Savings Plan) 和機會
WITH commitment_analysis AS (
  SELECT 
    ConsumedService,
    cost_category,
    region_group,
    year_month AS month,
    SUM(reservation_cost + savingplan_cost) AS commitment_cost,
    SUM(on_demand_cost) AS on_demand_cost,
    SUM(total_cost) AS total_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
    AND cost_category IN ('Compute', 'Database')
  GROUP BY ConsumedService, cost_category, region_group, month
)
SELECT 
  ConsumedService,
  cost_category,
  region_group,
  AVG(on_demand_cost) AS avg_monthly_on_demand,
  AVG(commitment_cost) AS avg_monthly_commitment,
  AVG(total_cost) AS avg_monthly_total,
  ROUND(AVG(commitment_cost) / NULLIF(AVG(total_cost), 0) * 100, 2) AS current_coverage_pct,
  ROUND(AVG(on_demand_cost) * 0.30, 2) AS potential_monthly_savings_30pct,
  ROUND(AVG(on_demand_cost) * 0.30 * 12, 2) AS potential_annual_savings,
  CASE 
    WHEN AVG(on_demand_cost) > 1000 AND AVG(commitment_cost) / NULLIF(AVG(total_cost), 0) < 0.5 
      THEN '高優先級：大量隨選支出'
    WHEN AVG(on_demand_cost) > 500 
      THEN '中優先級：考慮增加承諾'
    ELSE '低優先級：成本較低'
  END AS priority
FROM commitment_analysis
GROUP BY ConsumedService, cost_category, region_group
HAVING AVG(on_demand_cost) > 100
ORDER BY potential_annual_savings DESC
```

**行動項目**：
* 針對穩定工作負載購買保留實例 (RI) 或節省方案 (Savings Plan)
* 承諾使用通常可節省 30-70%
* 目標覆蓋率：穩定負載應達 80% 以上

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

### 模式 3.2：孤兒資源（長期快照與未連結磁碟）

**目標**：識別長期存在但可能不再需要的快照或未連結磁碟

```sql
-- 尋找超過 90 天的快照
SELECT 
  ResourceGroup,
  ResourceName,
  MeterName,
  SUM(CostInBillingCurrency) AS total_cost_90d,
  ROUND(AVG(CostInBillingCurrency), 2) AS avg_daily_cost,
  COUNT(DISTINCT date_key) AS billing_days
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  AND (ConsumedService = 'Microsoft.Compute' AND MeterName LIKE '%Snapshot%')
GROUP BY ResourceGroup, ResourceName, MeterName
HAVING billing_days >= 85 -- 持續計費接近 3 個月
ORDER BY total_cost_90d DESC
LIMIT 50;
```

**行動項目**：
* 刪除超過 90 天的快照（除非有合規需求）
* 確認磁碟 (Disks) 是否有對應的 VM，若無則刪除
* 潛在節省：100% 的快照儲存成本

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

### 模式 4.2：儲存冗餘優化 (GRS vs LRS)

**目標**：識別非生產環境中不必要的異地備援 (GRS/RA-GRS) 儲存帳戶

```sql
-- 識別非生產環境的 GRS 儲存
SELECT 
  ResourceGroup,
  ResourceName,
  MeterName,
  tag_environment,
  SUM(CostInBillingCurrency) AS monthly_cost,
  '建議降級至 LRS (本地備援)' AS recommendation,
  ROUND(SUM(CostInBillingCurrency) * 0.40, 2) AS potential_savings -- GRS 到 LRS 約省 40-50%
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyy-MM')
  AND ConsumedService = 'Microsoft.Storage'
  AND (MeterName LIKE '%GRS%' OR MeterName LIKE '%Geo-Redundant%')
  AND (tag_environment IN ('dev', 'test', 'qa') OR ResourceGroup LIKE '%dev%' OR ResourceGroup LIKE '%test%')
GROUP BY ResourceGroup, ResourceName, MeterName, tag_environment
HAVING monthly_cost > 20
ORDER BY monthly_cost DESC
```

**行動項目**：
* 將 Dev/Test 環境的儲存帳戶複寫設定由 GRS 改為 LRS
* 潛在節省：40-50% 的儲存成本

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
    ProductName,
    year_month AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    COUNT(DISTINCT date_key) AS days_active
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyy-MM')
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
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
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
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND cost_category IN ('Compute', 'Database')
  AND is_reservation = FALSE

UNION ALL

-- Spot 實例潛在節省 (針對非生產環境)
SELECT 
  'Spot Instances' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.60, 2) AS potential_savings,
  '60%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND cost_category = 'Compute'
  AND (tag_environment IN ('dev', 'test', 'nonprod') OR ResourceGroup LIKE '%dev%')
  AND is_reservation = FALSE -- 針對隨選實例

UNION ALL

SELECT 
  '孤兒資源 (快照)' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency), 2) AS potential_savings,
  '100%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND (ConsumedService = 'Microsoft.Compute' AND MeterName LIKE '%Snapshot%')

UNION ALL

SELECT 
  '閒置資源' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.90, 2) AS potential_savings,
  '90%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND Quantity = 0
  AND CostInBillingCurrency > 0

UNION ALL

SELECT 
  'VM 世代現代化' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.15, 2) AS potential_savings,
  '15%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND ConsumedService = 'Microsoft.Compute'
  AND (MeterName LIKE '%v3%' OR MeterName LIKE '%v4%')

UNION ALL

SELECT 
  '儲存冗餘優化 (GRS->LRS)' AS optimization_category,
  COUNT(DISTINCT ResourceName) AS affected_resources,
  ROUND(SUM(CostInBillingCurrency), 2) AS current_monthly_cost,
  ROUND(SUM(CostInBillingCurrency) * 0.40, 2) AS potential_savings,
  '40%' AS savings_rate
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND ConsumedService = 'Microsoft.Storage'
  AND (MeterName LIKE '%GRS%' OR MeterName LIKE '%Geo-Redundant%')
  AND (tag_environment IN ('dev', 'test', 'qa') OR ResourceGroup LIKE '%dev%')

ORDER BY potential_savings DESC
```

---

## 🎯 優化優先級矩陣

| 優化類型 | 實施難度 | 潛在節省 | 優先級 |
|---------|---------|---------|--------|
| 孤兒資源 (快照/磁碟) | 低 | 100% | 🔴 高 |
| 閒置資源消除 | 低 | 90%+ | 🔴 高 |
| 儲存冗餘優化 (GRS) | 低 | 40-50% | 🔴 高 |
| 非生產環境排程 | 低 | 60-75% | 🔴 高 |
| Databricks 工作負載 | 中 | 40% | 🟡 中 |
| 保留實例 | 中 | 30-70% | 🟡 中 |
| 調整資源規模 | 中 | 20-50% | 🟡 中 |
| VM 世代現代化 | 中 | 15% | 🟡 中 |
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
