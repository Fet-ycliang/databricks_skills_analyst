---
name: show-executive-dashboard
description: 顯示高階主管儀表板，提供成本概覽、趨勢和關鍵指標的綜合視圖
tags: [dashboards, executive, summary, overview]
---

# 高階主管儀表板

## 描述
提供高階主管層級的成本概覽，包含當月成本摘要、前 10 大成本驅動因素、成本類別分佈、趨勢分析和關鍵 KPI。適合每月審查會議和管理層報告。

## 使用時機
* 每月高階主管審查會議
* 董事會或管理層報告
* 預算審查和規劃
* 季度業務審查

## 儀表板組成

此儀表板包含 6 個關鍵視圖，建議使用以下查詢建構完整儀表板：

---

## 視圖 1：成本摘要卡片

**用途**：顯示當月關鍵成本指標

```sql
-- 月度成本摘要卡片
WITH current_month AS (
  SELECT 
    SUM(total_cost) AS mtd_cost,
    SUM(reservation_cost) AS reserved_cost,
    SUM(on_demand_cost) AS on_demand_cost,
    COUNT(DISTINCT Date) AS days_in_month
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
),
previous_month AS (
  SELECT SUM(total_cost) AS last_month_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -1), 'yyyy-MM')
),
ytd AS (
  SELECT SUM(total_cost) AS ytd_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE YEAR(Date) = YEAR(CURRENT_DATE())
)
SELECT 
  '當月至今成本' AS metric,
  CONCAT('$', FORMAT_NUMBER(ROUND(cm.mtd_cost, 0), 0)) AS value,
  CONCAT(
    CASE 
      WHEN cm.mtd_cost > pm.last_month_cost THEN '↑ '
      WHEN cm.mtd_cost < pm.last_month_cost THEN '↓ '
      ELSE '→ '
    END,
    ABS(ROUND((cm.mtd_cost - pm.last_month_cost) / NULLIF(pm.last_month_cost, 0) * 100, 1)),
    '% vs 上月'
  ) AS trend
FROM current_month cm, previous_month pm

UNION ALL

SELECT 
  '保留實例覆蓋率' AS metric,
  CONCAT(ROUND(cm.reserved_cost / NULLIF(cm.mtd_cost, 0) * 100, 1), '%') AS value,
  CASE 
    WHEN cm.reserved_cost / NULLIF(cm.mtd_cost, 0) >= 0.7 THEN '✅ 達標'
    WHEN cm.reserved_cost / NULLIF(cm.mtd_cost, 0) >= 0.5 THEN '🟡 可改善'
    ELSE '🔴 需優化'
  END AS trend
FROM current_month cm

UNION ALL

SELECT 
  '年初至今成本' AS metric,
  CONCAT('$', FORMAT_NUMBER(ROUND(ytd.ytd_cost, 0), 0)) AS value,
  CONCAT(ROUND(ytd.ytd_cost / NULLIF(cm.mtd_cost, 0), 1), 'x 當月') AS trend
FROM current_month cm, ytd

UNION ALL

SELECT 
  '預計月底成本' AS metric,
  CONCAT('$', FORMAT_NUMBER(
    ROUND(cm.mtd_cost / cm.days_in_month * DAY(LAST_DAY(CURRENT_DATE())), 0), 0
  )) AS value,
  CONCAT('基於 ', cm.days_in_month, ' 天資料') AS trend
FROM current_month cm
```

**視覺化建議**：使用 4 個大型數字卡片，並排顯示

---

## 視圖 2：前 10 大成本驅動因素

**用途**：識別主要成本來源

```sql
-- 前 10 大成本驅動服務
SELECT 
  ConsumedService AS service,
  cost_category AS category,
  ROUND(SUM(total_cost), 0) AS monthly_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 1) AS cost_share_pct,
  ROUND((SUM(total_cost) - LAG(SUM(total_cost)) OVER (PARTITION BY ConsumedService ORDER BY DATE_FORMAT(Date, 'yyyy-MM'))) / 
        NULLIF(LAG(SUM(total_cost)) OVER (PARTITION BY ConsumedService ORDER BY DATE_FORMAT(Date, 'yyyy-MM')), 0) * 100, 1) AS mom_change_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY ConsumedService, cost_category, DATE_FORMAT(Date, 'yyyy-MM')
ORDER BY monthly_cost DESC
LIMIT 10
```

**視覺化建議**：水平長條圖，顯示成本和佔比

---

## 視圖 3：成本類別分佈

**用途**：理解成本結構

```sql
-- 成本類別分佈（圓餅圖）
SELECT 
  cost_category,
  ROUND(SUM(total_cost), 0) AS category_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 1) AS percentage,
  COUNT(DISTINCT ConsumedService) AS service_count
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE DATE_FORMAT(Date, 'yyyy-MM') = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY cost_category
ORDER BY category_cost DESC
```

**視覺化建議**：圓餅圖或環形圖

---

## 視圖 4：每日成本趨勢

**用途**：顯示成本趨勢和波動

```sql
-- 每日成本趨勢（最近 90 天）
SELECT 
  CAST(Date AS DATE) AS date,
  ROUND(SUM(total_cost), 0) AS daily_cost,
  ROUND(AVG(SUM(total_cost)) OVER (ORDER BY Date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0) AS ma_7day,
  ROUND(AVG(SUM(total_cost)) OVER (ORDER BY Date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 0) AS ma_30day
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE Date >= DATE_SUB(CURRENT_DATE(), 90)
GROUP BY date
ORDER BY date
```

**視覺化建議**：折線圖，包含每日成本和移動平均線

---

## 視圖 5：月度成本趨勢

**用途**：顯示長期成本趨勢

```sql
-- 月度成本趨勢（最近 12 個月）
WITH monthly_costs AS (
  SELECT 
    DATE_FORMAT(Date, 'yyyy-MM') AS month,
    SUM(total_cost) AS monthly_cost,
    SUM(reservation_cost) AS reserved_cost,
    SUM(on_demand_cost) AS on_demand_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE Date >= DATE_SUB(CURRENT_DATE(), 365)
  GROUP BY month
)
SELECT 
  month,
  ROUND(monthly_cost, 0) AS total_cost,
  ROUND(reserved_cost, 0) AS reserved_cost,
  ROUND(on_demand_cost, 0) AS on_demand_cost,
  ROUND(reserved_cost / NULLIF(monthly_cost, 0) * 100, 1) AS reservation_pct,
  ROUND((monthly_cost - LAG(monthly_cost) OVER (ORDER BY month)) / 
        NULLIF(LAG(monthly_cost) OVER (ORDER BY month), 0) * 100, 1) AS mom_growth_pct
FROM monthly_costs
ORDER BY month DESC
```

**視覺化建議**：堆疊長條圖或折線圖

---

## 視圖 6：關鍵 KPI 計分卡

**用途**：追蹤 FinOps 健康度

```sql
-- 關鍵 KPI 摘要
SELECT 
  'Tag Coverage' AS kpi,
  CONCAT(
    ROUND(COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
          NULLIF(COUNT(DISTINCT ResourceName), 0) * 100, 0), '%'
  ) AS current_value,
  '90%' AS target,
  CASE 
    WHEN COUNT(DISTINCT CASE WHEN tag_cost_center IS NOT NULL THEN ResourceName END) / 
         NULLIF(COUNT(DISTINCT ResourceName), 0) >= 0.9 THEN '✅'
    ELSE '🔴'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)

UNION ALL

SELECT 
  'Reservation Coverage' AS kpi,
  CONCAT(
    ROUND(SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END) / 
          NULLIF(SUM(CostInBillingCurrency), 0) * 100, 0), '%'
  ) AS current_value,
  '70%' AS target,
  CASE 
    WHEN SUM(CASE WHEN is_reservation THEN CostInBillingCurrency ELSE 0 END) / 
         NULLIF(SUM(CostInBillingCurrency), 0) >= 0.7 THEN '✅'
    ELSE '🔴'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
  AND cost_category IN ('Compute', 'Database')

UNION ALL

SELECT 
  'Idle Resources' AS kpi,
  CONCAT(
    ROUND(SUM(CASE WHEN Quantity = 0 AND CostInBillingCurrency > 0 THEN CostInBillingCurrency ELSE 0 END) / 
          NULLIF(SUM(CostInBillingCurrency), 0) * 100, 1), '%'
  ) AS current_value,
  '<5%' AS target,
  CASE 
    WHEN SUM(CASE WHEN Quantity = 0 AND CostInBillingCurrency > 0 THEN CostInBillingCurrency ELSE 0 END) / 
         NULLIF(SUM(CostInBillingCurrency), 0) <= 0.05 THEN '✅'
    ELSE '🔴'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)

UNION ALL

SELECT 
  'Data Freshness' AS kpi,
  CONCAT(DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))), ' days') AS current_value,
  '≤1 day' AS target,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), MAX(CAST(Date AS DATE))) <= 1 THEN '✅'
    ELSE '🔴'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver
```

**視覺化建議**：表格或卡片式佈局

---

## 儀表板佈局建議

```
┌─────────────────────────────────────────────────────────────┐
│  高階主管成本儀表板 - 2024年1月                              │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ 當月至今成本  │ 保留實例覆蓋率 │ 年初至今成本  │ 預計月底成本    │
│  $125,000   │    68%      │  $125,000   │   $155,000     │
│  ↑ 5.2%     │  🟡 可改善   │  1.0x 當月  │  基於 25 天    │
└─────────────┴─────────────┴─────────────┴─────────────────┘

┌──────────────────────────┬──────────────────────────────────┐
│  前 10 大成本驅動因素      │  成本類別分佈                     │
│  (水平長條圖)             │  (圓餅圖)                        │
│                          │                                  │
│  Microsoft.Compute 45%   │  Compute    45%                  │
│  Microsoft.Storage 20%   │  Storage    25%                  │
│  ...                     │  Network    15%                  │
└──────────────────────────┴──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  每日成本趨勢（最近 90 天）                                   │
│  (折線圖 - 每日成本 + 7天移動平均 + 30天移動平均)             │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────┬──────────────────────────────────┐
│  月度成本趨勢（12個月）    │  關鍵 KPI 計分卡                  │
│  (堆疊長條圖)             │  (表格)                          │
│                          │                                  │
│  保留 vs 隨選成本         │  Tag Coverage      85%  ✅       │
│                          │  Reservation       68%  🔴       │
│                          │  Idle Resources    3%   ✅       │
│                          │  Data Freshness    1d   ✅       │
└──────────────────────────┴──────────────────────────────────┘
```

## 使用範例

### 範例 1：匯出為 PDF 報告
建議使用 Databricks SQL 的「排程」功能，每月自動產生並發送 PDF 報告給管理層。

### 範例 2：嵌入到內部入口網站
使用 Databricks SQL 的嵌入功能，將儀表板嵌入到公司內部入口網站。

### 範例 3：自訂時間範圍
在每個查詢中調整日期篩選條件，例如查看特定季度或年度資料。

## 關鍵洞察

### 成本趨勢
* **正常**：月對月變化 ±10% 以內
* **注意**：月對月變化 10-20%
* **警報**：月對月變化 > 20%

### 成本結構
* **健康**：運算 40-50%、儲存 20-30%、其他 20-30%
* **不平衡**：單一類別 > 60%

### 優化機會
* 保留實例覆蓋率 < 70%：購買保留實例
* 閒置資源 > 5%：清理未使用資源
* 標籤覆蓋率 < 90%：改善標籤治理

## 報告建議

### 每月高階主管報告應包含
1. **執行摘要**（1 頁）
   * 當月成本總覽
   * 主要變化和原因
   * 關鍵行動項目

2. **成本分析**（2-3 頁）
   * 成本趨勢分析
   * 前 10 大成本驅動因素
   * 類別和區域分佈

3. **優化進度**（1-2 頁）
   * 已實現的節省
   * 進行中的優化專案
   * 未來機會

4. **KPI 追蹤**（1 頁）
   * 關鍵 KPI 達標情況
   * 與目標的差距
   * 改善計畫

## 相關 Commands

* `show-monthly-cost-summary` - 詳細月度摘要
* `show-top-cost-drivers` - 成本驅動因素分析
* `show-finops-kpis` - 完整 KPI 儀表板
* `detect-cost-anomalies` - 異常檢測

## 資料來源

* **主要表格**：
  * `develop_catalog.system_report.finops_daily_cost_summary`（Gold 層）
  * `develop_catalog.system_report.infra_azure_cost_silver`（Silver 層）
* **更新頻率**：每日
* **歷史資料**：12 個月

## 注意事項

1. **資料新鮮度**：確認資料是最新的（< 2 天延遲）
2. **貨幣單位**：確認使用正確的貨幣單位
3. **預測準確性**：月初預測可能不準確，建議月中後使用
4. **視覺化**：使用清晰的圖表和顏色編碼
5. **互動性**：在 Databricks SQL 中啟用篩選器和下鑽功能
6. **效能**：整個儀表板載入時間應 < 10 秒
