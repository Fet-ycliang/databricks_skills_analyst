---
name: check-tag-coverage
description: 檢查資源標籤覆蓋率，確保成本分配和治理的準確性
tags: [data-quality, tags, governance, compliance]
---

# 檢查標籤覆蓋率

## 描述
檢查關鍵標籤（Purpose、envType、擁有者）的覆蓋率，識別未標記或標記不完整的資源。標籤覆蓋率是成本分配和治理的基礎。

## 使用時機
* 每週資料品質檢查
* 成本分配準備
* 治理合規審查
* 新資源上線驗證

## 查詢

```sql
-- 標籤覆蓋率分析（最近 30 天）
WITH tag_analysis AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    COUNT(DISTINCT ResourceName) AS total_resources,
    COUNT(DISTINCT CASE WHEN Tags['Purpose'] IS NOT NULL THEN ResourceName END) AS tagged_cost_center,
    COUNT(DISTINCT CASE WHEN Tags['envType'] IS NOT NULL THEN ResourceName END) AS tagged_environment,
    COUNT(DISTINCT CASE WHEN tag_owner IS NOT NULL THEN ResourceName END) AS tagged_owner,
    COUNT(DISTINCT CASE WHEN Tags['Project'] IS NOT NULL THEN ResourceName END) AS tagged_project,
    COUNT(DISTINCT CASE 
      WHEN Tags['Purpose'] IS NOT NULL 
       AND Tags['envType'] IS NOT NULL 
       AND tag_owner IS NOT NULL 
      THEN ResourceName 
    END) AS fully_tagged,
    SUM(CostInBillingCurrency) AS total_cost,
    SUM(CASE WHEN Tags['Purpose'] IS NULL THEN CostInBillingCurrency ELSE 0 END) AS unallocated_cost,
    SUM(CASE WHEN Tags['envType'] IS NULL THEN CostInBillingCurrency ELSE 0 END) AS no_env_cost,
    SUM(CASE WHEN tag_owner IS NULL THEN CostInBillingCurrency ELSE 0 END) AS no_owner_cost
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  GROUP BY month
)
SELECT 
  month,
  total_resources,
  tagged_cost_center,
  tagged_environment,
  tagged_owner,
  tagged_project,
  fully_tagged,
  ROUND(tagged_cost_center / NULLIF(total_resources, 0) * 100, 2) AS cost_center_coverage_pct,
  ROUND(tagged_environment / NULLIF(total_resources, 0) * 100, 2) AS environment_coverage_pct,
  ROUND(tagged_owner / NULLIF(total_resources, 0) * 100, 2) AS owner_coverage_pct,
  ROUND(tagged_project / NULLIF(total_resources, 0) * 100, 2) AS project_coverage_pct,
  ROUND(fully_tagged / NULLIF(total_resources, 0) * 100, 2) AS full_tag_coverage_pct,
  ROUND(total_cost, 2) AS total_cost,
  ROUND(unallocated_cost, 2) AS unallocated_cost,
  ROUND(no_env_cost, 2) AS no_env_cost,
  ROUND(no_owner_cost, 2) AS no_owner_cost,
  ROUND(unallocated_cost / NULLIF(total_cost, 0) * 100, 2) AS unallocated_cost_pct,
  CASE 
    WHEN fully_tagged / NULLIF(total_resources, 0) >= 0.9 THEN '✅ 優秀 (>90%)'
    WHEN fully_tagged / NULLIF(total_resources, 0) >= 0.8 THEN '🟢 良好 (80-90%)'
    WHEN fully_tagged / NULLIF(total_resources, 0) >= 0.7 THEN '🟡 尚可 (70-80%)'
    WHEN fully_tagged / NULLIF(total_resources, 0) >= 0.5 THEN '🟠 需改善 (50-70%)'
    ELSE '🔴 不佳 (<50%)'
  END AS tag_quality_status
FROM tag_analysis
ORDER BY month DESC
```

## 輸出欄位

* `month` - 月份
* `total_resources` - 總資源數
* `tagged_cost_center` - 有 Purpose 標籤的資源數
* `tagged_environment` - 有 envType 標籤的資源數
* `tagged_owner` - 有擁有者標籤的資源數
* `tagged_project` - 有專案標籤的資源數
* `fully_tagged` - 完整標記的資源數（三個必要標籤都有）
* `cost_center_coverage_pct` - Purpose 覆蓋率
* `environment_coverage_pct` - envType 覆蓋率
* `owner_coverage_pct` - 擁有者覆蓋率
* `project_coverage_pct` - 專案覆蓋率
* `full_tag_coverage_pct` - 完整標籤覆蓋率
* `total_cost` - 總成本
* `unallocated_cost` - 未分配成本（無 Purpose 標籤）
* `no_env_cost` - 無 envType 標籤的成本
* `no_owner_cost` - 無擁有者標籤的成本
* `unallocated_cost_pct` - 未分配成本百分比
* `tag_quality_status` - 標籤品質狀態

## 標籤覆蓋率目標

### ✅ 優秀（> 90%）
* **狀態**：符合最佳實踐
* **行動**：維持現狀，持續監控
* **成本分配**：可進行精確的成本回收

### 🟢 良好（80-90%）
* **狀態**：接近目標
* **行動**：識別並標記剩餘 10-20% 資源
* **成本分配**：可進行成本回收，少量未分配

### 🟡 尚可（70-80%）
* **狀態**：需要改善
* **行動**：啟動標籤改善計畫
* **成本分配**：可進行成本展示，不建議成本回收

### 🟠 需改善（50-70%）
* **狀態**：不符合標準
* **行動**：優先處理高成本未標記資源
* **成本分配**：僅能進行部分成本展示

### 🔴 不佳（< 50%）
* **狀態**：嚴重問題
* **行動**：立即啟動標籤治理專案
* **成本分配**：無法進行有效的成本分配

## 使用範例

### 範例 1：查看未標記的高成本資源
```sql
-- 識別需要優先標記的資源
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  ROUND(SUM(CostInBillingCurrency), 2) AS cost_30d,
  CASE 
    WHEN Tags['Purpose'] IS NULL THEN '❌ 缺少 Purpose'
    ELSE '✅ 有 Purpose'
  END AS purpose_status,
  CASE 
    WHEN Tags['envType'] IS NULL THEN '❌ 缺少 envType'
    ELSE '✅ 有 envType'
  END AS environment_status,
  CASE 
    WHEN tag_owner IS NULL THEN '❌ 缺少擁有者'
    ELSE '✅ 有擁有者'
  END AS owner_status
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND (Tags['Purpose'] IS NULL OR Tags['envType'] IS NULL OR tag_owner IS NULL)
GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category, 
         Tags['Purpose'], Tags['envType'], tag_owner
HAVING SUM(CostInBillingCurrency) > 100
ORDER BY cost_30d DESC
LIMIT 50
```

### 範例 2：按資源群組的標籤覆蓋率
```sql
-- 查看各資源群組的標籤品質
SELECT 
  ResourceGroup,
  COUNT(DISTINCT ResourceName) AS total_resources,
  COUNT(DISTINCT CASE WHEN Tags['Purpose'] IS NOT NULL THEN ResourceName END) AS tagged_resources,
  ROUND(COUNT(DISTINCT CASE WHEN Tags['Purpose'] IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS coverage_pct,
  ROUND(SUM(CostInBillingCurrency), 2) AS total_cost
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY ResourceGroup
ORDER BY coverage_pct ASC, total_cost DESC
```

### 範例 3：按服務類型的標籤覆蓋率
```sql
-- 查看哪些服務類型標籤覆蓋率較低
SELECT 
  ConsumedService,
  COUNT(DISTINCT ResourceName) AS total_resources,
  ROUND(COUNT(DISTINCT CASE WHEN Tags['Purpose'] IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 2) AS coverage_pct
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY ConsumedService
HAVING COUNT(DISTINCT ResourceName) >= 10
ORDER BY coverage_pct ASC
```

## 改善標籤覆蓋率的步驟

### 1. 識別階段（1 週）
* 執行標籤覆蓋率查詢
* 識別高成本未標記資源
* 按資源群組和服務分類

### 2. 規劃階段（1-2 週）
* 定義標籤標準和命名規範
* 確定責任歸屬
* 建立標籤政策文件

### 3. 執行階段（2-4 週）
* 聯絡資源擁有者
* 批次標記資源
* 使用 Azure Policy 強制新資源標記

### 4. 維護階段（持續）
* 每週監控標籤覆蓋率
* 自動警報未標記的新資源
* 定期審查和更新標籤

## 標籤標準建議

### 必要標籤（Required）
* **Purpose**：資源用途或成本中心代碼（例如：IT-001, Production-DB）
* **envType**：環境類型（dev/test/staging/prod）
* **Owner**：技術擁有者電子郵件

### 建議標籤（Recommended）
* **Project**：專案或應用程式名稱
* **BusinessUnit**：業務單位
* **Criticality**：重要性（critical/high/medium/low）
* **DataClassification**：資料分類（public/internal/confidential）

### 選用標籤（Optional）
* **CreatedBy**：建立者
* **CreatedDate**：建立日期
* **ExpiryDate**：到期日期（用於臨時資源）

## 相關 Commands

* `show-cost-by-cost-center` - 查看成本分配（需要標籤）
* `find-idle-resources` - 尋找閒置資源（標籤有助於聯絡擁有者）
* `show-finops-kpis` - 標籤覆蓋率是 KPI 之一
* `detect-cost-anomalies` - 標籤有助於異常調查

## 資料來源

* **主要表格**：`develop_catalog.system_report.infra_azure_cost_silver`
* **資料層級**：Silver 層（包含標籤資訊）
* **更新頻率**：每日
* **歷史資料**：最近 30 天
* **標籤來源**：從 `Tags` MAP 欄位提取 `Purpose` 和 `envType`

## 注意事項

1. **標籤來源**：標籤從 Azure 資源標籤提取，儲存在 `Tags` MAP 欄位中
2. **標籤名稱**：使用 `Tags['Purpose']` 取代傳統的 cost_center，`Tags['envType']` 取代 environment
3. **大小寫**：標籤名稱區分大小寫，請確保使用正確的大小寫（Purpose, envType）
4. **標籤限制**：Azure 每個資源最多 50 個標籤
5. **繼承**：資源群組標籤不會自動繼承到資源
6. **成本影響**：未標記資源無法進行準確的成本分配
7. **效能**：使用 Silver 層表格，查詢時間約 5-10 秒
