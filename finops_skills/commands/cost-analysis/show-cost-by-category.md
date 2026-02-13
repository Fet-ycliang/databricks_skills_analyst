---
name: show-cost-by-category
description: 按成本類別顯示成本分佈，包含運算、儲存、網路、資料庫等
tags: [cost-analysis, category, distribution, breakdown]
---

# 按成本類別顯示成本

## 描述
按成本類別（運算、儲存、網路、資料庫、其他）顯示當月成本分佈，包含資源數量、月對月變化和成本佔比。用於理解成本結構。

## 使用時機
* 理解成本結構
* 識別成本類別趨勢
* 類別層級的預算追蹤
* 向管理層解釋成本組成

## 查詢

```sql
-- 按成本類別的成本分佈
WITH current_month AS (
  SELECT 
    cost_category,
    ROUND(SUM(total_cost), 2) AS monthly_cost,
    COUNT(DISTINCT ConsumedService) AS service_count,
    COUNT(DISTINCT ResourceName) AS resource_count,
    ROUND(AVG(total_cost), 2) AS avg_daily_cost,
    ROUND(SUM(reservation_cost), 2) AS reserved_cost,
    ROUND(SUM(on_demand_cost), 2) AS on_demand_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  GROUP BY cost_category
),
previous_month AS (
  SELECT 
    cost_category,
    ROUND(SUM(total_cost), 2) AS last_month_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM')
  GROUP BY cost_category
)
SELECT 
  cm.cost_category,
  cm.monthly_cost,
  cm.service_count,
  cm.resource_count,
  cm.avg_daily_cost,
  cm.reserved_cost,
  cm.on_demand_cost,
  ROUND(cm.reserved_cost / NULLIF(cm.monthly_cost, 0) * 100, 2) AS reservation_coverage_pct,
  ROUND(cm.monthly_cost / SUM(cm.monthly_cost) OVER () * 100, 2) AS cost_share_pct,
  COALESCE(pm.last_month_cost, 0) AS last_month_cost,
  ROUND(cm.monthly_cost - COALESCE(pm.last_month_cost, 0), 2) AS mom_change,
  ROUND((cm.monthly_cost - COALESCE(pm.last_month_cost, 0)) / NULLIF(pm.last_month_cost, 0) * 100, 2) AS mom_change_pct
FROM current_month cm
LEFT JOIN previous_month pm ON cm.cost_category = pm.cost_category
ORDER BY cm.monthly_cost DESC
```

## 輸出欄位

* `cost_category` - 成本類別（Compute/Storage/Network/Database/Other）
* `monthly_cost` - 當月總成本
* `service_count` - 服務數量
* `resource_count` - 資源數量
* `avg_daily_cost` - 每日平均成本
* `reserved_cost` - 保留實例成本
* `on_demand_cost` - 隨選成本
* `reservation_coverage_pct` - 保留實例覆蓋率
* `cost_share_pct` - 成本佔比
* `last_month_cost` - 上月成本
* `mom_change` - 月對月變化金額
* `mom_change_pct` - 月對月變化百分比

## 成本類別說明

### Compute（運算）
* 虛擬機器（VMs）
* Databricks 叢集
* App Service
* Container Instances
* **典型佔比**：40-60%

### Storage（儲存）
* Blob Storage
* File Storage
* Disk Storage
* **典型佔比**：15-25%

### Network（網路）
* 資料傳輸
* Load Balancer
* VPN Gateway
* **典型佔比**：5-15%

### Database（資料庫）
* SQL Database
* Cosmos DB
* MySQL/PostgreSQL
* **典型佔比**：10-20%

### Other（其他）
* 監控和管理
* 安全服務
* 其他雜項服務
* **典型佔比**：5-10%

## 使用範例

### 範例 1：查看最近 6 個月的類別趨勢
```sql
-- 修改為按月分組
SELECT 
  DATE_FORMAT(Date, 'yyyy-MM') AS month,
  cost_category,
  ROUND(SUM(total_cost), 2) AS monthly_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
GROUP BY month, cost_category
ORDER BY month DESC, monthly_cost DESC
```

### 範例 2：只看運算和儲存類別
```sql
-- 在 WHERE 子句中加入篩選
WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  AND cost_category IN ('Compute', 'Storage')
```

## 解讀結果

### 正常情況
* 運算類別通常最高（40-60%）
* 類別分佈相對穩定
* 月對月變化在 ±15% 以內

### 需要關注
* 🔴 運算 > 70%：可能有閒置或過大的資源
* 🟡 網路 > 20%：可能有跨區域傳輸問題
* 🔴 月對月變化 > 50%：異常變化，需調查
* 🟡 儲存持續成長：需檢查資料保留政策

## 優化建議

### 按類別的優化策略

**Compute（運算）**
* 尋找閒置資源
* 調整 VM 規模
* 購買保留實例
* 實施排程（非生產環境）

**Storage（儲存）**
* 移至較便宜的儲存層級
* 刪除舊快照和備份
* 實施生命週期管理
* 啟用壓縮

**Network（網路）**
* 減少跨區域傳輸
* 使用 CDN
* 優化資料傳輸模式
* 資源共置

**Database（資料庫）**
* 調整資料庫規模
* 購買保留容量
* 優化查詢效能
* 考慮 Serverless 選項

## 相關 Commands

* `show-monthly-cost-summary` - 查看總體成本
* `show-top-cost-drivers` - 查看服務層級詳情
* `find-idle-resources` - 尋找閒置資源（運算類別）
* `show-cost-by-cost-center` - 按成本中心細分

## 資料來源

* **主要表格**：`develop_catalog.system_report.finops_daily_cost_summary`
* **資料層級**：Gold 層（已聚合）
* **更新頻率**：每日
* **歷史資料**：當月 + 上月

## 注意事項

1. **類別定義**：成本類別在 Silver 層根據服務類型自動分類
2. **視覺化**：此查詢結果適合用圓餅圖或堆疊長條圖呈現
3. **趨勢分析**：建議每月追蹤類別佔比變化
4. **效能**：使用 Gold 層表格，查詢效能良好（< 2 秒）
