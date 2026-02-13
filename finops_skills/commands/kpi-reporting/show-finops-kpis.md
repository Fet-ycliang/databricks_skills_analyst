---
name: show-finops-kpis
description: 顯示 FinOps 關鍵績效指標儀表板，追蹤成本效率和優化進度
tags: [kpi-reporting, metrics, dashboard, maturity]
---

# FinOps KPI 儀表板

## 描述
顯示綜合的 FinOps 關鍵績效指標（KPI），包含成本效率、標籤覆蓋率、保留實例覆蓋率、資料品質等核心指標。用於追蹤 FinOps 成熟度和優化進度。

## 使用時機
* 每月 FinOps 審查會議
* 向管理層報告進度
* 追蹤優化計畫效益
* 評估 FinOps 成熟度

## 查詢

```sql
-- FinOps KPI 綜合儀表板
WITH kpi_metrics AS (
  -- KPI 1: 標籤覆蓋率
  SELECT 
    'Tag Coverage' AS kpi_name,
    '資料品質' AS kpi_category,
    ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
          NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 1) AS current_value,
    90.0 AS target_value,
    '%' AS unit,
    CASE 
      WHEN COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
           NULLIF(COUNT(DISTINCT ResourceName), 0) >= 0.90 THEN '✅ 達標'
      WHEN COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
           NULLIF(COUNT(DISTINCT ResourceName), 0) >= 0.80 THEN '🟡 接近'
      ELSE '🔴 未達標'
    END AS status,
    1 AS display_order
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  
  UNION ALL
  
  -- KPI 2: 保留實例覆蓋率
  SELECT 
    'Reservation Coverage' AS kpi_name,
    '成本效率' AS kpi_category,
    ROUND(SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END) / 
          NULLIF(SUM(CostInBillingCurrency), 0) * 100, 1) AS current_value,
    70.0 AS target_value,
    '%' AS unit,
    CASE 
      WHEN SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END) / 
           NULLIF(SUM(CostInBillingCurrency), 0) >= 0.70 THEN '✅ 達標'
      WHEN SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END) / 
           NULLIF(SUM(CostInBillingCurrency), 0) >= 0.50 THEN '🟡 接近'
      ELSE '🔴 未達標'
    END AS status,
    2 AS display_order
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
    AND cost_category IN ('Compute', 'Database')
  
  UNION ALL
  
  -- KPI 3: 資料新鮮度
  SELECT 
    'Data Freshness' AS kpi_name,
    '資料品質' AS kpi_category,
    DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) AS current_value,
    1.0 AS target_value,
    'days' AS unit,
    CASE 
      WHEN DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) <= 1 THEN '✅ 達標'
      WHEN DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) <= 2 THEN '🟡 接近'
      ELSE '🔴 未達標'
    END AS status,
    3 AS display_order
  FROM develop_catalog.system_report.infra_azure_cost_silver
  
  UNION ALL
  
  -- KPI 4: 月對月成本變化
  SELECT 
    'MoM Cost Change' AS kpi_name,
    '成本趨勢' AS kpi_category,
    ROUND((cm.mtd_cost - pm.last_month_cost) / NULLIF(pm.last_month_cost, 0) * 100, 1) AS current_value,
    10.0 AS target_value,
    '%' AS unit,
    CASE 
      WHEN ABS((cm.mtd_cost - pm.last_month_cost) / NULLIF(pm.last_month_cost, 0)) <= 0.10 THEN '✅ 正常'
      WHEN ABS((cm.mtd_cost - pm.last_month_cost) / NULLIF(pm.last_month_cost, 0)) <= 0.20 THEN '🟡 注意'
      ELSE '🔴 異常'
    END AS status,
    4 AS display_order
  FROM (
    SELECT SUM(total_cost) AS mtd_cost
    FROM develop_catalog.system_report.finops_daily_cost_summary
    WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  ) cm
  CROSS JOIN (
    SELECT SUM(total_cost) AS last_month_cost
    FROM develop_catalog.system_report.finops_daily_cost_summary
    WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM')
  ) pm
  
  UNION ALL
  
  -- KPI 5: 閒置資源成本佔比
  SELECT 
    'Idle Resource Cost %' AS kpi_name,
    '成本優化' AS kpi_category,
    ROUND(SUM(CASE WHEN Quantity = 0 AND CostInBillingCurrency > 0 THEN CostInBillingCurrency ELSE 0 END) / 
          NULLIF(SUM(CostInBillingCurrency), 0) * 100, 1) AS current_value,
    5.0 AS target_value,
    '%' AS unit,
    CASE 
      WHEN SUM(CASE WHEN Quantity = 0 AND CostInBillingCurrency > 0 THEN CostInBillingCurrency ELSE 0 END) / 
           NULLIF(SUM(CostInBillingCurrency), 0) <= 0.05 THEN '✅ 達標'
      WHEN SUM(CASE WHEN Quantity = 0 AND CostInBillingCurrency > 0 THEN CostInBillingCurrency ELSE 0 END) / 
           NULLIF(SUM(CostInBillingCurrency), 0) <= 0.10 THEN '🟡 可改善'
      ELSE '🔴 需優化'
    END AS status,
    5 AS display_order
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  
  UNION ALL
  
  -- KPI 6: 未分配成本佔比
  SELECT 
    'Unallocated Cost %' AS kpi_name,
    '成本分配' AS kpi_category,
    ROUND(SUM(CASE WHEN tag_cost_center IS NULL THEN CostInBillingCurrency ELSE 0 END) / 
          NULLIF(SUM(CostInBillingCurrency), 0) * 100, 1) AS current_value,
    10.0 AS target_value,
    '%' AS unit,
    CASE 
      WHEN SUM(CASE WHEN tag_cost_center IS NULL THEN CostInBillingCurrency ELSE 0 END) / 
           NULLIF(SUM(CostInBillingCurrency), 0) <= 0.10 THEN '✅ 達標'
      WHEN SUM(CASE WHEN tag_cost_center IS NULL THEN CostInBillingCurrency ELSE 0 END) / 
           NULLIF(SUM(CostInBillingCurrency), 0) <= 0.20 THEN '🟡 可改善'
      ELSE '🔴 需改善'
    END AS status,
    6 AS display_order
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
)
SELECT 
  kpi_name,
  kpi_category,
  current_value,
  target_value,
  unit,
  status,
  CASE 
    WHEN current_value >= target_value AND unit = '%' AND kpi_name NOT IN ('MoM Cost Change', 'Idle Resource Cost %', 'Unallocated Cost %') THEN '達標'
    WHEN current_value <= target_value AND kpi_name IN ('Data Freshness', 'MoM Cost Change', 'Idle Resource Cost %', 'Unallocated Cost %') THEN '達標'
    WHEN ABS(current_value - target_value) / target_value <= 0.2 THEN '接近目標'
    ELSE '需改善'
  END AS performance,
  ROUND((current_value - target_value) / NULLIF(target_value, 0) * 100, 1) AS variance_pct
FROM kpi_metrics
ORDER BY display_order
```

## 輸出欄位

* `kpi_name` - KPI 名稱
* `kpi_category` - KPI 類別
* `current_value` - 當前值
* `target_value` - 目標值
* `unit` - 單位（%、days 等）
* `status` - 狀態（達標/接近/未達標）
* `performance` - 績效評估
* `variance_pct` - 與目標的偏差百分比

## KPI 說明

### 1. 標籤覆蓋率（Tag Coverage）
* **類別**：資料品質
* **定義**：有成本中心標籤的資源百分比
* **目標**：≥ 90%
* **重要性**：成本分配的基礎

### 2. 保留實例覆蓋率（Reservation Coverage）
* **類別**：成本效率
* **定義**：保留實例成本佔運算和資料庫成本的百分比
* **目標**：≥ 70%
* **重要性**：直接影響成本節省

### 3. 資料新鮮度（Data Freshness）
* **類別**：資料品質
* **定義**：最新資料距今的天數
* **目標**：≤ 1 天
* **重要性**：及時的成本可視化

### 4. 月對月成本變化（MoM Cost Change）
* **類別**：成本趨勢
* **定義**：當月與上月成本的變化百分比
* **目標**：≤ ±10%
* **重要性**：成本穩定性指標

### 5. 閒置資源成本佔比（Idle Resource Cost %）
* **類別**：成本優化
* **定義**：閒置資源成本佔總成本的百分比
* **目標**：≤ 5%
* **重要性**：浪費程度指標

### 6. 未分配成本佔比（Unallocated Cost %）
* **類別**：成本分配
* **定義**：無成本中心標籤的成本佔比
* **目標**：≤ 10%
* **重要性**：成本分配準確性

## FinOps 成熟度評分

```sql
-- 計算整體 FinOps 成熟度評分
WITH kpi_scores AS (
  -- 使用上面的 KPI 查詢
  SELECT 
    kpi_name,
    CASE 
      WHEN status = '✅ 達標' THEN 100
      WHEN status = '🟡 接近' OR status = '🟡 注意' OR status = '🟡 可改善' THEN 70
      ELSE 40
    END AS score
  FROM (
    -- 原 KPI 查詢
  )
)
SELECT 
  ROUND(AVG(score), 0) AS overall_finops_score,
  COUNT(*) AS total_kpis,
  SUM(CASE WHEN score = 100 THEN 1 ELSE 0 END) AS kpis_met,
  SUM(CASE WHEN score = 70 THEN 1 ELSE 0 END) AS kpis_close,
  SUM(CASE WHEN score = 40 THEN 1 ELSE 0 END) AS kpis_need_improvement,
  CASE 
    WHEN AVG(score) >= 90 THEN '🏆 優秀 - 奔跑階段'
    WHEN AVG(score) >= 75 THEN '🟢 良好 - 行走階段'
    WHEN AVG(score) >= 60 THEN '🟡 尚可 - 爬行階段'
    ELSE '🔴 需改善 - 起步階段'
  END AS maturity_level
FROM kpi_scores
```

## 成熟度等級

### 🏆 優秀（90-100 分）- 奔跑階段
* 所有 KPI 達標或接近目標
* 自動化程度高
* 持續優化文化
* **特徵**：主動優化、預測性分析、自動化警報

### 🟢 良好（75-89 分）- 行走階段
* 大部分 KPI 達標
* 定期優化審查
* 成本意識普及
* **特徵**：定期報告、優化計畫、標籤治理

### 🟡 尚可（60-74 分）- 爬行階段
* 部分 KPI 達標
* 基本可視化建立
* 開始成本分配
* **特徵**：基本報告、手動分析、初步標籤

### 🔴 需改善（< 60 分）- 起步階段
* 多數 KPI 未達標
* 缺乏可視化
* 成本分配困難
* **特徵**：反應式管理、資料品質問題、缺乏治理

## 使用範例

### 範例 1：追蹤 KPI 趨勢（最近 6 個月）
```sql
-- 修改查詢以按月分組
SELECT 
  DATE_FORMAT(Date, 'yyyy-MM') AS month,
  'Tag Coverage' AS kpi_name,
  ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
        NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 1) AS value
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 180)
GROUP BY month
ORDER BY month DESC
```

### 範例 2：按類別的 KPI 摘要
```sql
-- 查看各類別的 KPI 達標情況
SELECT 
  kpi_category,
  COUNT(*) AS total_kpis,
  SUM(CASE WHEN status LIKE '%達標%' THEN 1 ELSE 0 END) AS kpis_met,
  ROUND(SUM(CASE WHEN status LIKE '%達標%' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100, 1) AS achievement_rate
FROM (
  -- 原 KPI 查詢
)
GROUP BY kpi_category
ORDER BY achievement_rate DESC
```

## 改善建議

### 標籤覆蓋率 < 90%
* 執行 `check-tag-coverage` 識別未標記資源
* 實施 Azure Policy 強制標記
* 定期審查和清理

### 保留實例覆蓋率 < 70%
* 分析穩定工作負載
* 購買 1 年或 3 年保留實例
* 考慮 Azure Hybrid Benefit

### 閒置資源 > 5%
* 執行 `find-idle-resources` 每週
* 實施自動關閉政策
* 建立資源生命週期管理

### 未分配成本 > 10%
* 提高標籤覆蓋率
* 建立標籤標準
* 培訓團隊成員

## 相關 Commands

* `show-monthly-cost-summary` - 查看成本趨勢
* `check-tag-coverage` - 改善標籤覆蓋率
* `find-idle-resources` - 減少閒置資源
* `detect-cost-anomalies` - 監控成本變化

## 資料來源

* **主要表格**：
  * `develop_catalog.system_report.finops_daily_cost_summary`（Gold 層）
  * `develop_catalog.system_report.infra_azure_cost_silver`（Silver 層）
* **更新頻率**：每日
* **歷史資料**：最近 30 天

## 注意事項

1. **KPI 定義**：根據組織需求調整 KPI 和目標值
2. **報告頻率**：建議每月審查，每週監控關鍵 KPI
3. **趨勢分析**：追蹤 KPI 趨勢比單點值更重要
4. **行動導向**：每個未達標 KPI 應有改善計畫
5. **效能**：查詢時間約 5-10 秒
