---
name: show-cost-by-cost-center
description: 按成本中心顯示成本分配，包含月對月變化和成本佔比
tags: [cost-allocation, chargeback, cost-center, monthly]
---

# 按成本中心顯示成本

## 描述
按成本中心顯示月度成本分配，包含資源數量、環境細分、月對月變化和成本佔比。用於成本回收和部門預算追蹤。

## 使用時機
* 月度成本回收報告
* 部門預算審查
* 成本責任歸屬
* 跨部門成本比較

## 查詢

```sql
-- 按成本中心的月度成本分配
SELECT 
  DATE_FORMAT(Date, 'yyyy-MM') AS billing_month,
  COALESCE(tag_cost_center, 'Unallocated') AS cost_center,
  COALESCE(tag_environment, 'Unknown') AS environment,
  cost_category,
  COUNT(DISTINCT ResourceGroup) AS resource_groups,
  COUNT(DISTINCT ResourceName) AS resources,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  ROUND(SUM(CASE WHEN is_reservation THEN total_cost ELSE 0 END), 2) AS reserved_cost,
  ROUND(SUM(CASE WHEN is_reservation THEN 0 ELSE total_cost END), 2) AS on_demand_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER (PARTITION BY DATE_FORMAT(Date, 'yyyy-MM')) * 100, 2) AS cost_share_pct,
  ROUND(LAG(SUM(total_cost)) OVER (PARTITION BY tag_cost_center, tag_environment, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM')), 2) AS previous_month_cost,
  ROUND((SUM(total_cost) - LAG(SUM(total_cost)) OVER (PARTITION BY tag_cost_center, tag_environment, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM'))) / 
        NULLIF(LAG(SUM(total_cost)) OVER (PARTITION BY tag_cost_center, tag_environment, cost_category ORDER BY DATE_FORMAT(Date, 'yyyy-MM')), 0) * 100, 2) AS mom_change_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
GROUP BY billing_month, cost_center, environment, cost_category
ORDER BY billing_month DESC, monthly_cost DESC
```

## 輸出欄位

* `billing_month` - 帳單月份（yyyy-MM 格式）
* `cost_center` - 成本中心（來自標籤，未標記顯示為 'Unallocated'）
* `environment` - 環境（dev/test/prod 等）
* `cost_category` - 成本類別（Compute/Storage/Network 等）
* `resource_groups` - 資源群組數量
* `resources` - 資源數量
* `monthly_cost` - 月度總成本
* `reserved_cost` - 保留實例成本
* `on_demand_cost` - 隨選成本
* `cost_share_pct` - 成本佔比（佔當月總成本的百分比）
* `previous_month_cost` - 上月成本
* `mom_change_pct` - 月對月變化百分比

## 使用範例

### 範例 1：查看特定成本中心的成本
```sql
-- 在 WHERE 子句中加入篩選條件
WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
  AND tag_cost_center = 'IT-Operations'
```

### 範例 2：只看生產環境成本
```sql
-- 篩選特定環境
WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
  AND tag_environment = 'prod'
```

### 範例 3：識別成本成長最快的成本中心
```sql
-- 在最後加入 HAVING 子句
HAVING mom_change_pct > 20
ORDER BY mom_change_pct DESC
```

## 解讀結果

### 正常情況
* 所有成本中心都有標記（Unallocated < 10%）
* 月對月變化在 ±20% 以內
* 成本分佈符合預期的部門規模

### 需要關注
* 🔴 Unallocated > 20%：標籤覆蓋率不足
* 🟡 月對月變化 > 50%：異常成本激增
* 🟡 單一成本中心 > 50% 總成本：成本集中度過高

## 相關 Commands

* `show-unallocated-costs` - 查看未分配成本詳情
* `check-tag-coverage` - 檢查標籤覆蓋率
* `show-cost-by-project` - 按專案顯示成本
* `generate-chargeback-report` - 產生完整成本回收報告

## 資料來源

* **主要表格**：`develop_catalog.system_report.finops_daily_cost_summary`
* **資料層級**：Gold 層（已聚合）
* **更新頻率**：每日
* **歷史資料**：最近 180 天（6 個月）

## 注意事項

1. **標籤依賴**：此查詢依賴 `tag_cost_center` 標籤，確保資源已正確標記
2. **未分配成本**：未標記的資源會顯示為 'Unallocated'，需要定期檢查
3. **環境細分**：結果會按環境細分，同一成本中心可能有多筆記錄
4. **效能**：使用 Gold 層表格，查詢效能良好（< 5 秒）
