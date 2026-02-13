---
name: Azure FinOps Skills
description: 基於 FinOps v1.2 框架的 Azure 成本管理與優化技能集，提供成本可視化、優化、分攤、異常檢測、KPI 追蹤和自動儀表板建立等完整功能。支援透過自然語言建立 FinOps 儀表板。
---

# Azure FinOps Skills - FinOps v1.2 框架

## 📋 概述

本技能提供基於 **FinOps v1.2 框架**的完整 Azure 成本管理與優化能力。它採用獎章架構（Bronze-Silver-Gold）來實現快速、高效的成本分析和報告。

這是**主技能**文件，提供資料架構概覽，並連結到針對特定 FinOps 使用案例的專門子技能。

---

## 🎯 目的

透過以下方式實現資料驅動的雲端財務管理：
* **成本可視化**：了解資金的使用去向
* **成本優化**：識別節省機會
* **成本分攤**：準確的成本回收與展示
* **異常檢測**：識別異常的支出模式
* **FinOps KPI**：追蹤關鍵財務營運指標
* **資料品質**：確保成本資料的準確性和可靠性

---

## 📊 資料架構

### Bronze 層（原始資料）
* **資料表**：`develop_catalog.system_report.infra_azure_cost_usage_actual`
* **用途**：原始 Azure 成本匯出資料（符合 FinOps v1.2 規範）
* **保留期限**：13-24 個月的歷史資料
* **更新頻率**：每日從 Azure Cost Export 更新

### Silver 層（清理與豐富化）
* **資料表**：`develop_catalog.system_report.infra_azure_cost_silver`
* **用途**：標準化、豐富化的成本資料，包含：
  * 資料品質驗證
  * 成本分類（運算、儲存、網路、資料庫、其他）
  * 區域分組（亞洲、美國、歐洲、其他）
  * 標籤提取（用途、環境、成本中心、擁有者）
  * 保留實例識別
* **分區**：依 `year_month` 分區
* **叢集**：依 `ConsumedService`、`ResourceGroup` 叢集
* **使用案例**：詳細的資源層級分析、自訂聚合

### Gold 層（業務就緒的聚合）

#### 1. 每日成本摘要
* **資料表**：`develop_catalog.system_report.finops_daily_cost_summary`
* **用途**：依服務、類別和區域的每日聚合成本
* **關鍵指標**： 
  * 總成本、數量、資源數量
  * 多維度成本拆分：保留實例、Spot 實例、節省方案、隨選成本
  * 平均有效價格與 Pay-as-you-go 價格比較
* **效能**：針對快速儀表板查詢優化（次秒級）
* **完整欄位清單**：
  * `date_key`, `year_month` (分區欄位)
  * `ConsumedService`, `cost_category`, `region_group`
  * `resource_count`, `total_quantity`
  * `avg_payGPrice`, `avg_effective_price`
  * `total_cost`, `reservation_cost`, `spot_cost`, `savingplan_cost`, `on_demand_cost`

#### 2. 資源群組月度
* **資料表**：`develop_catalog.system_report.finops_resource_group_monthly`
* **用途**：依資源群組的月度成本分配
* **使用案例**：成本回收、預算追蹤、團隊責任歸屬
* **關鍵維度**：資源群組、標籤、環境、成本中心

#### 3. 服務月度趨勢
* **資料表**：`develop_catalog.system_report.finops_service_monthly_trend`
* **用途**：服務層級成本趨勢，包含月對月和年對年比較
* **關鍵指標**：成本成長、資源擴展、趨勢分析
* **包含**：歷史比較（上個月、去年同期）

---

## 🎓 專門子技能

本主技能組織為 **6 個專門子技能**，每個專注於 FinOps 的特定面向：

### 1. 💰 [成本優化模式](skills/finops_skills/cost-optimization-patterns/SKILL.md)
**焦點**：識別並實施成本節省機會

**涵蓋主題**：
* 調整過大的運算資源規模
* 保留實例與節省方案分析
* 閒置資源消除
* 儲存優化策略
* 網路成本降低
* 排程與自動化機會

**使用時機**：當您需要降低雲端支出並提高成本效率時

---

### 2. 🚨 [進階異常檢測](skills/finops_skills/anomaly-detection-advanced/SKILL.md)
**焦點**：檢測異常的支出模式和成本異常

**涵蓋主題**：
* 統計異常檢測（Z-score 方法）
* 時間序列異常檢測
* 資源層級異常檢測
* 服務層級異常檢測
* 閾值型警報
* 模式型檢測

**使用時機**：當您需要識別意外的成本激增或異常支出行為時

---

### 3. 💳 [成本回收與展示指南](skills/finops_skills/chargeback-showback-guide/SKILL.md)
**焦點**：實施成本分配與責任歸屬模型

**涵蓋主題**：
* 成本回收 vs 成本展示模型
* 成本分配方法論
* 基於標籤的分配
* 共享成本分配
* 部門與團隊報告
* 預算追蹤與預測

**使用時機**：當您需要將成本分配給業務單位、團隊或專案時

---

### 4. 📊 [FinOps KPI 指標](skills/finops_skills/finops-kpi-metrics/SKILL.md)
**焦點**：追蹤和衡量 FinOps 成熟度與效能

**涵蓋主題**：
* 成本效率指標
* 成本可視化指標
* 成本優化指標
* 營運指標
* 治理指標
* 業務價值指標

**使用時機**：當您需要衡量 FinOps 計畫成功並向領導層報告時

---

### 5. ✅ [資料品質驗證](skills/finops_skills/data-quality-validation/SKILL.md)
**焦點**：確保成本資料的準確性和可靠性

**涵蓋主題**：
* 完整性檢查
* 準確性驗證
* 跨層一致性驗證
* 時效性監控
* 有效性檢查（業務規則）
* 重複檢測

**使用時機**：當您需要驗證資料品質或排除資料問題時

---

### 6. 📈 [儀表板查詢](skills/finops_skills/dashboard-queries/SKILL.md)
**焦點**：用於建構 FinOps 儀表板的即用查詢

**涵蓋主題**：
* 高階主管儀表板（高層概覽）
* FinOps 團隊儀表板（營運監控）
* 成本中心儀表板（部門視圖）
* 優化儀表板（節省機會）
* 資源儀表板（詳細資源視圖）
* 趨勢分析儀表板（歷史模式）

**使用時機**：當您需要建構或增強 FinOps 儀表板和報告時

---

### 7. 📊 自動建立 FinOps 儀表板 🤖

**焦點**：透過自然語言自動建立完整的 FinOps 儀表板

**功能**：
* 自動建立綜合型 FinOps 儀表板
* 包含所有關鍵 KPI 和視覺化
* 支援自訂時間範圍和參數
* 自動發布和分享

**使用方式**：
直接對 Assistant 說：
* "建立一個 FinOps 儀表板"
* "幫我建立綜合型 FinOps dashboard"
* "我要一個顯示最近 6 個月成本的儀表板"

**技術實作**：
使用 [aibi-dashboards](../aibi-dashboards/SKILL.md) 技能的 `scripts/dashboard_create.py` 模組

**儀表板內容**：
* **KPI 卡片**：總成本、保留實例使用率
* **趨勢圖**：月度成本趨勢（總成本 vs 保留實例成本）
* **分解圖**：Top 10 服務成本、Top 10 資源群組成本
* **分類圖**：成本分類分布（運算、儲存、網路等）

**使用時機**：當您需要快速建立 FinOps 儀表板進行成本分析和報告時

---

## 🚀 快速入門指南

### 新使用者
1. **從這裡開始**：檢閱本概述以了解資料架構
2. **驗證存取**：執行下方的快速驗證查詢確認資料可用性
3. **建立儀表板**：對 Assistant 說「建立一個 FinOps 儀表板」快速建立視覺化報告
4. **探索資料**：使用[儀表板查詢](skills/finops_skills/dashboard-queries/SKILL.md)熟悉資料
5. **驗證品質**：執行[資料品質驗證](skills/finops_skills/data-quality-validation/SKILL.md)檢查
6. **設定監控**：實施[異常檢測](skills/finops_skills/anomaly-detection-advanced/SKILL.md)警報

### 成本分析
1. 使用[儀表板查詢](skills/finops_skills/dashboard-queries/SKILL.md)進行標準報告
2. 應用[成本回收與展示](skills/finops_skills/chargeback-showback-guide/SKILL.md)進行成本分配
3. 使用 [FinOps KPI 指標](skills/finops_skills/finops-kpi-metrics/SKILL.md)追蹤進度

### 成本優化
1. 檢閱[成本優化模式](skills/finops_skills/cost-optimization-patterns/SKILL.md)尋找節省機會
2. 使用[異常檢測](skills/finops_skills/anomaly-detection-advanced/SKILL.md)及早發現問題
3. 使用 [FinOps KPI 指標](skills/finops_skills/finops-kpi-metrics/SKILL.md)衡量影響

---

## ⚡ 快速驗證查詢

在開始使用前，執行以下查詢驗證資料可用性和品質：

### 資料新鮮度檢查
```sql
-- 檢查各層資料的最新日期
SELECT 
  'Bronze' AS layer,
  MAX(Date) AS latest_date,
  DATEDIFF(CURRENT_DATE(), MAX(Date)) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), MAX(Date)) <= 2 THEN '✓ PASS'
    ELSE '✗ FAIL' 
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_usage_actual

UNION ALL

SELECT 
  'Silver' AS layer,
  TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd') AS latest_date,
  DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 2 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END AS status
FROM develop_catalog.system_report.infra_azure_cost_silver

UNION ALL

SELECT 
  'Gold' AS layer,
  TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd') AS latest_date,
  DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) AS days_lag,
  CASE 
    WHEN DATEDIFF(CURRENT_DATE(), TO_DATE(CAST(MAX(date_key) AS STRING), 'yyyyMMdd')) <= 2 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END AS status
FROM develop_catalog.system_report.finops_daily_cost_summary

ORDER BY layer;
```

**預期結果**：所有層的 `days_lag` 應 ≤ 2 天，狀態為 `✓ PASS`

### 資料完整性檢查
```sql
-- 檢查最近 7 天的資料記錄數
SELECT 
  date_key,
  TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
  COUNT(*) AS record_count,
  ROUND(SUM(total_cost), 2) AS daily_cost,
  COUNT(DISTINCT ConsumedService) AS service_count
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)
GROUP BY date_key
ORDER BY date_key DESC;
```

**預期結果**：每天應有穩定的記錄數和合理的成本範圍

### 標籤覆蓋率檢查
```sql
-- 檢查關鍵標籤的覆蓋率
SELECT 
  ROUND(COUNT(CASE WHEN tag_environment IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS environment_coverage_pct,
  ROUND(COUNT(CASE WHEN tag_cost_center IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS cost_center_coverage_pct,
  ROUND(COUNT(CASE WHEN tag_owner IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) AS owner_coverage_pct,
  COUNT(*) AS total_records
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM');
```

**預期結果**：標籤覆蓋率應 > 90%

---

## 🎓 最佳實踐

### 查詢效能
* **始終依日期篩選**：使用 `year_month` 或 `Date` 來利用分區修剪
* **使用正確的層級**：
  * Gold 層用於聚合查詢（快 10-100 倍）
  * Silver 層用於詳細的資源層級分析
  * 避免使用 Bronze 層進行分析（僅用於資料血緣）
* **限制結果集**：使用 `LIMIT` 和日期範圍來控制查詢大小
* **善用 CTE**：對於複雜查詢，使用 Common Table Expressions 提高可讀性和效能

### 成本分析方法
* **跨時間比較**：始終包含月對月和年對年比較
* **標準化成本**：使用單位成本指標進行公平比較
* **分段分析**：依標籤、區域、服務和資源群組細分
* **設定閾值**：專注於重要項目（參考下方成本基準表）

### 資料品質
* **監控標籤覆蓋率**：目標 >90% 標籤合規性
* **驗證保留實例**：確保保留實例分配正確
* **檢查孤立資源**：識別缺少適當中繼資料的資源
* **檢閱異常**：每週調查成本激增
* **定期執行健康檢查**：使用上方的快速驗證查詢

### FinOps 成熟度
* **爬行**：從基本的成本可視化和報告開始
* **行走**：實施成本回收/展示和優化
* **奔跑**：自動化異常檢測和優化建議

---

## 💰 成本基準與閾值參考

以下基準值可協助您識別優化機會和設定異常檢測閾值：

| 服務類型 | 每月基準成本 | 異常閾值 | 優化優先級 | 關鍵指標 |
|---------|------------|---------|-----------|---------|
| 虛擬機器 (Virtual Machines) | $5,000 - $15,000 | +30% MoM | 🔴 高 | CPU 使用率 < 20% |
| Azure Kubernetes Service | $3,000 - $10,000 | +40% MoM | 🔴 高 | 節點使用率 < 50% |
| 儲存 (Storage) | $2,000 - $8,000 | +50% MoM | 🟠 中 | 未存取 > 90 天 |
| SQL Database | $2,000 - $6,000 | +35% MoM | 🟠 中 | DTU 使用率 < 30% |
| 網路 (Networking) | $1,000 - $4,000 | +100% MoM | 🟡 低 | 跨區域流量 |
| Azure Monitor | $500 - $2,000 | +60% MoM | 🟡 低 | 日誌保留期 |

**使用說明**：
* **基準成本**：典型企業環境的月度成本範圍
* **異常閾值**：月對月 (MoM) 成長超過此百分比應調查
* **優化優先級**：建議的優化檢視順序
* **關鍵指標**：識別優化機會的主要指標

---

## 📚 常見查詢模式

### 基本成本摘要（最近 30 天）- 優化版
```sql
-- 使用 year_month 分區過濾提升效能
WITH recent_months AS (
  SELECT DISTINCT year_month 
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyy-MM')
)
SELECT 
  ConsumedService,
  cost_category,
  SUM(total_cost) AS total_cost,
  COUNT(DISTINCT date_key) AS days_active,
  ROUND(SUM(total_cost) / COUNT(DISTINCT date_key), 2) AS avg_daily_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month IN (SELECT year_month FROM recent_months)
  AND date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
GROUP BY ConsumedService, cost_category
ORDER BY total_cost DESC
LIMIT 10;
```

### 月度趨勢（最近 6 個月）- 含成長率
```sql
WITH monthly_costs AS (
  SELECT 
    year_month,
    SUM(total_cost) AS monthly_cost,
    SUM(reservation_cost) AS reserved_cost,
    SUM(on_demand_cost) AS on_demand_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
  GROUP BY year_month
)
SELECT 
  year_month,
  monthly_cost,
  reserved_cost,
  on_demand_cost,
  ROUND((reserved_cost / NULLIF(monthly_cost, 0)) * 100, 2) AS reserved_pct,
  ROUND(monthly_cost - LAG(monthly_cost) OVER (ORDER BY year_month), 2) AS mom_change,
  ROUND(((monthly_cost - LAG(monthly_cost) OVER (ORDER BY year_month)) / 
         NULLIF(LAG(monthly_cost) OVER (ORDER BY year_month), 0)) * 100, 2) AS mom_change_pct
FROM monthly_costs
ORDER BY year_month DESC;
```

### 資源群組分配（當月）- 含排名
```sql
WITH rg_costs AS (
  SELECT 
    ResourceGroup,
    tag_environment,
    SUM(total_cost) AS monthly_cost
  FROM develop_catalog.system_report.finops_resource_group_monthly
  WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
  GROUP BY ResourceGroup, tag_environment
)
SELECT 
  ROW_NUMBER() OVER (ORDER BY monthly_cost DESC) AS rank,
  ResourceGroup,
  tag_environment,
  ROUND(monthly_cost, 2) AS monthly_cost,
  ROUND(monthly_cost / SUM(monthly_cost) OVER () * 100, 2) AS cost_share_pct,
  ROUND(SUM(monthly_cost) OVER (ORDER BY monthly_cost DESC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / 
        SUM(monthly_cost) OVER () * 100, 2) AS cumulative_pct
FROM rg_costs
ORDER BY monthly_cost DESC
LIMIT 20;
```

### Top 成本異常檢測（簡易版）
```sql
WITH daily_avg AS (
  SELECT 
    ConsumedService,
    AVG(total_cost) AS avg_cost,
    STDDEV(total_cost) AS stddev_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
  GROUP BY ConsumedService
),
recent_costs AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ConsumedService,
    SUM(total_cost) AS daily_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 7), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ConsumedService
)
SELECT 
  r.date,
  r.ConsumedService,
  ROUND(r.daily_cost, 2) AS daily_cost,
  ROUND(a.avg_cost, 2) AS avg_cost,
  ROUND((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0), 2) AS z_score,
  CASE 
    WHEN ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) > 3 THEN '🔴 嚴重異常'
    WHEN ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) > 2 THEN '🟠 中度異常'
    ELSE '✓ 正常'
  END AS anomaly_status
FROM recent_costs r
JOIN daily_avg a ON r.ConsumedService = a.ConsumedService
WHERE ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) > 2
ORDER BY ABS((r.daily_cost - a.avg_cost) / NULLIF(a.stddev_cost, 0)) DESC
LIMIT 10;
```

**更詳細的查詢**，請參閱上述列出的專門子技能。

---

## 🔐 權限與存取控制

### 建議的權限模型

| 角色 | Bronze 層 | Silver 層 | Gold 層 | 用途 |
|-----|----------|----------|---------|------|
| FinOps 管理員 | SELECT, MODIFY | SELECT, MODIFY | SELECT, MODIFY | 完整資料管理 |
| FinOps 分析師 | SELECT | SELECT | SELECT | 成本分析與報告 |
| 部門主管 | - | SELECT (限定 RG) | SELECT (限定 RG) | 部門成本檢視 |
| 開發團隊 | - | - | SELECT (限定 RG) | 團隊成本檢視 |
| 儀表板服務帳號 | - | - | SELECT | 自動化報告 |

### Unity Catalog 權限設定範例

```sql
-- 授予 FinOps 分析師讀取權限
GRANT SELECT ON TABLE develop_catalog.system_report.infra_azure_cost_silver 
TO `finops-analysts@company.com`;

GRANT SELECT ON TABLE develop_catalog.system_report.finops_daily_cost_summary 
TO `finops-analysts@company.com`;

-- 授予部門主管限定資源群組的權限（需搭配 Row-Level Security）
CREATE OR REPLACE VIEW develop_catalog.system_report.dept_cost_view AS
SELECT * 
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE ResourceGroup IN (SELECT rg FROM dept_resource_groups WHERE dept = current_user());

GRANT SELECT ON VIEW develop_catalog.system_report.dept_cost_view 
TO `dept-managers@company.com`;
```

### 資料敏感性分類

* **Bronze 層**：🔴 高敏感 - 包含原始成本資料和完整資源詳情
* **Silver 層**：🟠 中敏感 - 包含豐富化的成本資料和標籤資訊
* **Gold 層**：🟡 低敏感 - 聚合資料，適合廣泛分享

---

## 🔗 相關資源

### FinOps 框架
* [FinOps Foundation](https://www.finops.org/)
* [FinOps v1.2 規範 (FOCUS)](https://focus.finops.org/)
* [FinOps 成熟度模型](https://www.finops.org/framework/maturity-model/)

### Azure 成本管理
* [Azure 成本管理最佳實踐](https://learn.microsoft.com/azure/cost-management-billing/)
* [Azure 定價計算機](https://azure.microsoft.com/pricing/calculator/)
* [Azure 成本匯出](https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-export-acm-data)

### Databricks 資源
* [Databricks SQL 效能調校](https://docs.databricks.com/sql/admin/query-tuning.html)
* [Delta Lake 最佳實踐](https://docs.databricks.com/delta/best-practices.html)
* [Unity Catalog 權限管理](https://docs.databricks.com/data-governance/unity-catalog/manage-privileges/index.html)

---

## 📝 關鍵資料表參考

| 層級 | 資料表名稱 | 用途 | 更新頻率 | 分區欄位 |
|-------|-----------|---------|------------------|---------|
| Bronze | `infra_azure_cost_usage_actual` | 原始 Azure 成本匯出 | 每日 | `Date` |
| Silver | `infra_azure_cost_silver` | 清理與豐富化的成本資料 | 每日 | `year_month` |
| Gold | `finops_daily_cost_summary` | 每日聚合成本 | 每日 | `year_month` |
| Gold | `finops_resource_group_monthly` | 月度資源群組成本 | 每月 | `year_month` |
| Gold | `finops_service_monthly_trend` | 月度服務趨勢 | 每月 | `year_month` |

**目錄**：`develop_catalog`  
**結構描述**：`system_report`

**效能提示**：
* 查詢時始終包含分區欄位過濾條件
* Gold 層表已針對常見聚合查詢優化
* 使用 `year_month` 過濾比 `Date` 過濾更高效（分區修剪）

---

## 🆘 支援與疑難排解

### 常見問題

**問：查詢很慢**
* 答：確保您依 `year_month` 或 `Date` 篩選以進行分區修剪
* 答：使用 Gold 層資料表進行聚合查詢，而非 Silver 層
* 答：檢查查詢計畫，確認有使用分區修剪（partition pruning）
* 答：避免在 WHERE 子句中對分區欄位使用函數

**問：最近日期的資料遺失**
* 答：執行上方的「資料新鮮度檢查」查詢驗證
* 答：檢查資料表中的 `MAX(Date)` 以驗證資料新鮮度
* 答：Azure 成本匯出可能有 1-2 天的延遲
* 答：確認 Azure Cost Export 排程是否正常運作

**問：標籤值為 NULL**
* 答：資源可能未在 Azure 中標記
* 答：執行上方的「標籤覆蓋率檢查」查詢
* 答：參閱[資料品質驗證](skills/finops_skills/data-quality-validation/SKILL.md)的標籤覆蓋率報告
* 答：與資源擁有者協調改善標籤合規性

**問：成本數字與 Azure 入口網站不符**
* 答：檢查日期範圍和貨幣設定
* 答：驗證您使用相同的成本類型（實際 vs 攤銷）
* 答：確認時區設定一致（UTC vs 本地時間）
* 答：檢查是否包含稅金和折扣

**問：權限錯誤 - 無法存取資料表**
* 答：確認您的帳號已被授予適當的 Unity Catalog 權限
* 答：聯絡 FinOps 管理員申請存取權限
* 答：檢查是否使用正確的目錄和結構描述名稱

### 取得協助
1. 檢閱相關的子技能文件
2. 執行快速驗證查詢檢查資料可用性
3. 檢查[資料品質驗證](skills/finops_skills/data-quality-validation/SKILL.md)的資料問題
4. 驗證資料表存取權限
5. 聯絡 FinOps 團隊尋求支援

---

## 📅 維護與更新

* **資料更新**：每日 UTC 時間 2:00 AM
* **歷史資料**：保留 13-24 個月
* **結構描述變更**：透過 FinOps 團隊溝通
* **技能更新**：檢查下方版本歷史

---

## 📝 變更日誌

### v2.1.1 (2026-02-13)
* 📝 更新 Gold 層 `finops_daily_cost_summary` 資料表文件
* ✨ 補充 `spot_cost` 和 `savingplan_cost` 欄位說明
* 📊 完善成本拆分維度文件（保留實例、Spot、節省方案、隨選）
* 🔍 新增完整欄位清單以提高文件準確性
* 🔧 修正 Silver 層標籤欄位說明，補充 `tag_purpose` 欄位
* 🐛 修正所有驗證查詢和常見查詢模式，將 `Date` 欄位改為 `date_key`
* ⚡ 優化日期篩選邏輯，使用 `date_key` (INT) 格式提升查詢效能

### v2.1 (2026-02-13)
* ✨ 新增快速驗證查詢區塊（資料新鮮度、完整性、標籤覆蓋率）
* ✨ 新增成本基準與閾值參考表
* ✨ 新增權限與存取控制指引
* 🔧 修正所有子技能路徑（加入 `finops_skills/` 前綴）
* 🚀 優化 SQL 查詢範例（加入分區過濾、CTE、視窗函數）
* 📊 新增成本異常檢測查詢範例
* 📚 擴充疑難排解區塊，新增更多常見問題
* 📝 新增資料表參考中的分區欄位資訊

### v2.0 (2026-02-13)
* 🎉 重構為模組化架構（6 個子技能）
* ✨ 新增 Gold 層聚合表
* 🚀 改進查詢效能（10-100x）
* 📊 新增月度趨勢分析表
* 🏷️ 改進標籤提取和分類邏輯

### v1.0 (2025-XX-XX)
* 🎉 初始版本（單體式架構）
* 📊 建立 Bronze 和 Silver 層
* 📈 基本成本報告功能

---

**最後更新**：2026-02-13  
**版本**：2.1.1（Schema 與查詢修正版）  
**維護者**：FinOps 團隊  
**授權**：內部使用
