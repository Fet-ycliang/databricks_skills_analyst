---
name: find-rightsizing-opportunities
description: 識別利用率低的運算資源，建議調整為較小的 SKU 以節省成本
tags: [cost-optimization, rightsizing, compute, vm-optimization]
---

# 尋找調整規模機會

## 描述
識別利用率低（每日使用時數 < 16 小時）的運算資源，建議調整為較小的 VM SKU 或實施排程。典型可節省 20-50% 的運算成本。

## 使用時機
* 每月成本優化審查
* VM 規模調整計畫
* 運算成本降低專案
* 容量規劃

## 查詢

```sql
-- 調整規模機會（最近 60 天）
WITH compute_usage AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ConsumedService,
    ProductName,
    MeterName,
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    SUM(Quantity) AS total_hours,
    AVG(Quantity) AS avg_daily_hours,
    COUNT(DISTINCT CAST(Date AS DATE)) AS days_active
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 60)
    AND cost_category = 'Compute'
    AND ConsumedService IN ('Microsoft.Compute', 'Microsoft.Databricks')
  GROUP BY ResourceGroup, ResourceName, ConsumedService, ProductName, MeterName, month
)
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  ProductName,
  ROUND(AVG(monthly_cost), 2) AS avg_monthly_cost,
  ROUND(AVG(avg_daily_hours), 2) AS avg_daily_hours,
  ROUND(AVG(days_active), 0) AS avg_days_per_month,
  ROUND(AVG(avg_daily_hours) / 24 * 100, 2) AS utilization_pct,
  CASE 
    WHEN AVG(avg_daily_hours) < 4 THEN '🔴 極低利用率'
    WHEN AVG(avg_daily_hours) < 8 THEN '🔴 低利用率'
    WHEN AVG(avg_daily_hours) < 12 THEN '🟡 中等利用率'
    WHEN AVG(avg_daily_hours) < 16 THEN '🟡 可接受利用率'
    ELSE '🟢 高利用率'
  END AS utilization_status,
  CASE 
    WHEN AVG(avg_daily_hours) < 4 THEN '考慮刪除或大幅縮小 SKU'
    WHEN AVG(avg_daily_hours) < 8 THEN '降低 1-2 個 SKU 層級或實施排程'
    WHEN AVG(avg_daily_hours) < 12 THEN '降低 1 個 SKU 層級'
    WHEN AVG(avg_daily_hours) < 16 THEN '檢閱使用模式，考慮排程'
    ELSE '使用情況正常'
  END AS recommendation,
  CASE 
    WHEN AVG(avg_daily_hours) < 4 THEN ROUND(AVG(monthly_cost) * 0.50, 2)
    WHEN AVG(avg_daily_hours) < 8 THEN ROUND(AVG(monthly_cost) * 0.40, 2)
    WHEN AVG(avg_daily_hours) < 12 THEN ROUND(AVG(monthly_cost) * 0.30, 2)
    WHEN AVG(avg_daily_hours) < 16 THEN ROUND(AVG(monthly_cost) * 0.20, 2)
    ELSE 0
  END AS potential_monthly_savings,
  CASE 
    WHEN AVG(monthly_cost) > 1000 THEN '🔴 高優先級'
    WHEN AVG(monthly_cost) > 500 THEN '🟡 中優先級'
    ELSE '🟢 低優先級'
  END AS priority
FROM compute_usage
WHERE monthly_cost > 50
GROUP BY ResourceGroup, ResourceName, ConsumedService, ProductName
HAVING AVG(avg_daily_hours) < 16
ORDER BY potential_monthly_savings DESC
LIMIT 100
```

## 輸出欄位

* `ResourceGroup` - 資源群組名稱
* `ResourceName` - 資源名稱
* `ConsumedService` - 服務類型（Compute/Databricks）
* `ProductName` - 產品/SKU 名稱
* `avg_monthly_cost` - 平均月度成本
* `avg_daily_hours` - 平均每日使用時數
* `avg_days_per_month` - 平均每月活躍天數
* `utilization_pct` - 利用率百分比（基於 24 小時）
* `utilization_status` - 利用率狀態
* `recommendation` - 建議行動
* `potential_monthly_savings` - 潛在月度節省
* `priority` - 優先級（高/中/低）

## 利用率分級

### 🔴 極低利用率（< 4 小時/天，< 17%）
* **問題**：資源幾乎未使用
* **建議**：考慮刪除或大幅縮小
* **潛在節省**：50%

### 🔴 低利用率（4-8 小時/天，17-33%）
* **問題**：資源使用不足
* **建議**：降低 1-2 個 SKU 層級或實施排程
* **潛在節省**：40%

### 🟡 中等利用率（8-12 小時/天，33-50%）
* **問題**：有優化空間
* **建議**：降低 1 個 SKU 層級
* **潛在節省**：30%

### 🟡 可接受利用率（12-16 小時/天，50-67%）
* **問題**：輕微優化機會
* **建議**：檢閱使用模式，考慮排程
* **潛在節省**：20%

### 🟢 高利用率（> 16 小時/天，> 67%）
* **狀態**：使用情況正常
* **建議**：維持現狀
* **潛在節省**：0%

## 使用範例

### 範例 1：只看高優先級機會
```sql
-- 在最後加入篩選
HAVING AVG(avg_daily_hours) < 16 AND AVG(monthly_cost) > 1000
ORDER BY potential_monthly_savings DESC
```

### 範例 2：按資源群組彙總
```sql
-- 查看各資源群組的優化機會
SELECT 
  ResourceGroup,
  COUNT(DISTINCT ResourceName) AS resources_to_optimize,
  ROUND(SUM(avg_monthly_cost), 2) AS total_current_cost,
  ROUND(SUM(potential_monthly_savings), 2) AS total_potential_savings,
  ROUND(SUM(potential_monthly_savings) / NULLIF(SUM(avg_monthly_cost), 0) * 100, 2) AS savings_pct
FROM (
  -- 原查詢
)
GROUP BY ResourceGroup
ORDER BY total_potential_savings DESC
```

### 範例 3：只看 Databricks 叢集
```sql
-- 篩選 Databricks 資源
WHERE Date >= DATE_SUB(CURRENT_DATE(), 60)
  AND cost_category = 'Compute'
  AND ConsumedService = 'Microsoft.Databricks'
```

## 調整規模指南

### VM SKU 調整建議

**Standard_D 系列（通用）**
* D4s_v3 → D2s_v3（降低 50% 成本）
* D8s_v3 → D4s_v3（降低 50% 成本）
* D16s_v3 → D8s_v3（降低 50% 成本）

**Standard_E 系列（記憶體優化）**
* E8s_v3 → E4s_v3（降低 50% 成本）
* E16s_v3 → E8s_v3（降低 50% 成本）

**Standard_F 系列（運算優化）**
* F8s_v2 → F4s_v2（降低 50% 成本）
* F16s_v2 → F8s_v2（降低 50% 成本）

### Databricks 叢集調整
* 減少 worker 節點數量
* 降低 driver 和 worker 的 VM 類型
* 啟用自動縮放
* 設定自動終止（閒置 15-30 分鐘）

## 實施步驟

### 1. 評估階段（1-2 週）
* 分析使用模式和尖峰時段
* 確認效能需求
* 評估業務影響

### 2. 測試階段（1-2 週）
* 在非生產環境測試較小 SKU
* 監控效能指標
* 收集使用者回饋

### 3. 執行階段（2-4 週）
* 逐步調整生產環境
* 持續監控效能
* 記錄節省金額

### 4. 優化階段（持續）
* 定期檢閱利用率
* 根據需求調整
* 實施自動化排程

## 預期節省

* **立即節省**：20-50% 的運算成本
* **典型範圍**：總成本的 5-10%
* **實施時間**：2-6 週
* **風險**：中（需效能測試）

## 相關 Commands

* `find-idle-resources` - 尋找完全閒置的資源
* `show-top-cost-drivers` - 識別高成本運算資源
* `detect-cost-anomalies` - 監控調整後的成本變化
* `show-finops-kpis` - 追蹤優化效益

## 資料來源

* **主要表格**：`develop_catalog.system_report.infra_azure_cost_silver`
* **資料層級**：Silver 層（詳細資料）
* **更新頻率**：每日
* **歷史資料**：最近 60 天（2 個月）

## 注意事項

1. **使用時數**：Quantity 欄位代表使用時數，24 小時 = 100% 利用率
2. **效能風險**：調整前務必測試，確保不影響效能
3. **尖峰需求**：考慮尖峰時段的效能需求
4. **保留實例**：已購買保留實例的資源調整規模較複雜
5. **自動縮放**：考慮使用自動縮放而非固定降低規模
6. **效能**：使用 Silver 層表格，查詢時間約 5-10 秒
