---
name: find-idle-resources
description: 尋找產生成本但無使用量的閒置資源，識別立即節省機會
tags: [cost-optimization, idle, waste, savings]
---

# 尋找閒置資源

## 描述
識別產生成本但無使用量（Quantity = 0）的閒置資源。這些是最容易實現的節省機會，通常可節省 90-100% 的資源成本。

## 使用時機
* 每週成本優化審查
* 識別快速節省機會
* 清理未使用的資源
* 降低浪費支出

## 查詢

```sql
-- 閒置資源（最近 30 天）
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
  ROUND(SUM(CostInBillingCurrency), 2) AS cost_30d,
  SUM(Quantity) AS total_quantity,
  COUNT(DISTINCT date_key) AS days_with_cost,
  MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS last_seen,
  ROUND(AVG(CostInBillingCurrency), 2) AS avg_daily_cost,
  CASE 
    WHEN SUM(Quantity) = 0 AND SUM(CostInBillingCurrency) > 100 THEN '🔴 高優先級'
    WHEN SUM(Quantity) = 0 AND SUM(CostInBillingCurrency) > 50 THEN '🟡 中優先級'
    WHEN SUM(Quantity) = 0 THEN '🟢 低優先級'
    ELSE '正常'
  END AS priority,
  CASE 
    WHEN ConsumedService = 'Microsoft.Compute' THEN '停止或刪除 VM'
    WHEN ConsumedService = 'Microsoft.Storage' THEN '刪除未使用的儲存帳戶'
    WHEN ConsumedService = 'Microsoft.Network' THEN '刪除未連接的網路資源'
    WHEN ConsumedService = 'Microsoft.Sql' THEN '刪除或暫停資料庫'
    ELSE '檢閱並考慮刪除'
  END AS recommendation,
  ROUND(SUM(CostInBillingCurrency) * 0.95, 2) AS potential_monthly_savings
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  AND Quantity = 0
  AND CostInBillingCurrency > 0
GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category, ProductName, 
         ResourceLocation, tag_cost_center, tag_environment, tag_owner
HAVING SUM(CostInBillingCurrency) > 10
ORDER BY potential_monthly_savings DESC
LIMIT 100
```

## 輸出欄位

* `ResourceGroup` - 資源群組名稱
* `ResourceName` - 資源名稱
* `ConsumedService` - Azure 服務類型
* `cost_category` - 成本類別
* `ProductName` - 產品名稱
* `ResourceLocation` - 資源位置
* `tag_cost_center` - 成本中心標籤
* `tag_environment` - 環境標籤
* `tag_owner` - 擁有者標籤
* `cost_30d` - 最近 30 天成本
* `total_quantity` - 總使用量（應為 0）
* `days_with_cost` - 產生成本的天數
* `last_seen` - 最後出現日期
* `avg_daily_cost` - 每日平均成本
* `priority` - 優先級（高/中/低）
* `recommendation` - 建議行動
* `potential_monthly_savings` - 潛在月度節省（95%）

## 使用範例

### 範例 1：只看高優先級閒置資源
```sql
-- 在 HAVING 子句中加入篩選
HAVING SUM(CostInBillingCurrency) > 100
ORDER BY potential_monthly_savings DESC
```

### 範例 2：按成本中心分組
```sql
-- 查看各成本中心的閒置資源總成本
SELECT 
  COALESCE(tag_cost_center, 'Unallocated') AS cost_center,
  COUNT(DISTINCT ResourceName) AS idle_resource_count,
  ROUND(SUM(cost_30d), 2) AS total_idle_cost,
  ROUND(SUM(potential_monthly_savings), 2) AS total_potential_savings
FROM (
  -- 原查詢
)
GROUP BY cost_center
ORDER BY total_potential_savings DESC
```

### 範例 3：只看特定服務類型
```sql
-- 只看閒置的運算資源
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND Quantity = 0
  AND CostInBillingCurrency > 0
  AND ConsumedService = 'Microsoft.Compute'
```

## 解讀結果

### 常見閒置資源類型

**1. 已停止但未解除配置的 VM**
* 仍產生磁碟和 IP 成本
* 建議：完全刪除或解除配置

**2. 未連接的磁碟**
* 從 VM 分離但未刪除
* 建議：刪除或建立快照後刪除

**3. 未使用的儲存帳戶**
* 空的或很少使用的儲存
* 建議：刪除或移至 Archive 層級

**4. 孤立的網路資源**
* 未連接的 Load Balancer、Public IP
* 建議：刪除未使用的資源

**5. 暫停的資料庫**
* 仍產生儲存成本
* 建議：刪除或匯出後刪除

### 需要關注
* 🔴 單一閒置資源 > $500/月：立即處理
* 🟡 閒置資源總成本 > 總成本 10%：系統性問題
* 🔴 無擁有者標籤的閒置資源：治理問題

## 行動步驟

### 1. 驗證階段（1-2 天）
* 聯絡資源擁有者確認是否仍需要
* 檢查是否有相依性
* 確認刪除不會影響業務

### 2. 測試階段（3-7 天）
* 先停止資源觀察影響
* 監控是否有錯誤或投訴
* 確認無影響後再刪除

### 3. 執行階段
* 建立快照或備份（如需要）
* 刪除資源
* 記錄節省金額

### 4. 預防措施
* 實施自動標記政策
* 設定資源生命週期規則
* 定期審查（每週或每月）

## 預期節省

* **立即節省**：90-100% 的閒置資源成本
* **典型範圍**：總成本的 5-15%
* **實施時間**：1-2 週
* **風險**：低（經過驗證後）

## 相關 Commands

* `find-rightsizing-opportunities` - 尋找過大的資源
* `show-top-cost-drivers` - 識別高成本服務
* `check-tag-coverage` - 檢查擁有者標籤
* `show-cost-by-cost-center` - 按部門追蹤節省

## 資料來源

* **主要表格**：`develop_catalog.system_report.infra_azure_cost_silver`
* **資料層級**：Silver 層（詳細資料）
* **更新頻率**：每日
* **歷史資料**：最近 30 天

## 注意事項

1. **使用量為零**：Quantity = 0 表示無使用量，但仍產生成本（如儲存、保留費用）
2. **驗證重要性**：刪除前務必確認資源不再需要
3. **備份建議**：重要資源刪除前建立快照或備份
4. **定期執行**：建議每週執行此查詢，及早發現閒置資源
5. **效能**：使用 Silver 層表格，查詢時間約 5-10 秒
