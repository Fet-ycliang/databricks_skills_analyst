---
name: show-top-cost-drivers
description: 顯示前 10 大成本驅動因素，識別最高成本的服務和資源
tags: [cost-analysis, top-drivers, services, optimization]
---

# 前 10 大成本驅動因素

## 描述
識別並顯示當月成本最高的前 10 個 Azure 服務，包含成本佔比、資源數量和每日平均成本。這是成本優化的起點。

## 使用時機
* 識別主要成本來源
* 優化工作優先順序排定
* 成本審查會議
* 向管理層解釋成本結構

## 查詢

```sql
-- 前 10 大成本驅動服務（當月）
SELECT 
  ConsumedService,
  cost_category,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  COUNT(DISTINCT date_key) AS days_active,
  COUNT(DISTINCT ResourceName) AS resource_count,
  ROUND(AVG(total_cost), 2) AS avg_daily_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 2) AS cost_share_pct,
  ROUND(SUM(reservation_cost), 2) AS reserved_cost,
  ROUND(SUM(on_demand_cost), 2) AS on_demand_cost,
  ROUND(SUM(reservation_cost) / NULLIF(SUM(total_cost), 0) * 100, 2) AS reservation_coverage_pct,
  ROUND(LAG(SUM(total_cost)) OVER (PARTITION BY ConsumedService ORDER BY year_month), 2) AS last_month_cost,
  ROUND((SUM(total_cost) - LAG(SUM(total_cost)) OVER (PARTITION BY ConsumedService ORDER BY year_month)) / 
        NULLIF(LAG(SUM(total_cost)) OVER (PARTITION BY ConsumedService ORDER BY year_month), 0) * 100, 2) AS mom_change_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY ConsumedService, cost_category, year_month
ORDER BY monthly_cost DESC
LIMIT 10
```

## 輸出欄位

* `ConsumedService` - Azure 服務名稱（例如：Microsoft.Compute）
* `cost_category` - 成本類別（Compute/Storage/Network 等）
* `monthly_cost` - 當月總成本
* `days_active` - 活躍天數
* `resource_count` - 資源數量
* `avg_daily_cost` - 每日平均成本
* `cost_share_pct` - 成本佔比（佔總成本的百分比）
* `reserved_cost` - 保留實例成本
* `on_demand_cost` - 隨選成本
* `reservation_coverage_pct` - 保留實例覆蓋率
* `last_month_cost` - 上月成本
* `mom_change_pct` - 月對月變化百分比

## 使用範例

### 範例 1：查看前 20 大成本驅動因素
```sql
-- 修改 LIMIT 為 20
ORDER BY monthly_cost DESC
LIMIT 20
```

### 範例 2：只看運算類別的前 10 大
```sql
-- 在 WHERE 子句中加入篩選
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  AND cost_category = 'Compute'
```

### 範例 3：識別成長最快的服務
```sql
-- 按月對月變化排序
ORDER BY mom_change_pct DESC
LIMIT 10
```

## 解讀結果

### 正常情況
* 前 3 大服務佔總成本 50-70%
* 成本分佈相對穩定
* 月對月變化在 ±20% 以內

### 需要關注
* 🔴 單一服務 > 50% 總成本：成本集中度過高，風險大
* 🟡 新服務突然進入前 10：需檢查是否為預期的新專案
* 🔴 月對月變化 > 100%：異常成本激增
* 🟡 保留實例覆蓋率 < 30%：優化機會

## 優化建議

### 高成本服務優化優先順序
1. **Microsoft.Compute**（運算）
   * 檢查閒置 VM
   * 調整 VM 規模
   * 購買保留實例

2. **Microsoft.Databricks**（資料處理）
   * 啟用自動縮放
   * 設定自動終止
   * 檢閱叢集大小

3. **Microsoft.Storage**（儲存）
   * 移至較便宜的儲存層級
   * 刪除舊快照
   * 實施生命週期管理

4. **Microsoft.Network**（網路）
   * 減少跨區域傳輸
   * 使用 CDN
   * 優化資料傳輸模式

## 相關 Commands

* `show-monthly-cost-summary` - 查看總體成本摘要
* `show-cost-by-category` - 按類別細分
* `find-idle-resources` - 尋找閒置資源
* `find-rightsizing-opportunities` - 尋找調整規模機會

## 資料來源

* **主要表格**：`develop_catalog.system_report.finops_daily_cost_summary`
* **資料層級**：Gold 層（已聚合）
* **更新頻率**：每日
* **歷史資料**：當月 + 上月（用於比較）

## 注意事項

1. **服務名稱**：Azure 服務名稱格式為 `Microsoft.ServiceName`
2. **成本佔比**：前 10 大通常佔總成本 80-90%（帕累托法則）
3. **優化焦點**：優先優化前 3-5 大成本驅動因素，效益最大
4. **效能**：使用 Gold 層表格，查詢效能良好（< 3 秒）
