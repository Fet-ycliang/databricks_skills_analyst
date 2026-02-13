# Azure FinOps Skills - 使用指南

## 🎯 何時使用此技能

使用此技能當您需要：

* **分析 Azure 雲端成本**：了解資金流向、識別高成本服務和資源
* **建立 FinOps 儀表板**：建構高階主管、團隊或部門的成本報告
* **優化雲端支出**：找出節省機會、調整資源規模、優化保留實例
* **實施成本分攤**：將成本分配給業務單位、團隊或專案
* **監控成本異常**：及早發現異常支出、預算超支或成本激增
* **追蹤 FinOps 成熟度**：衡量 FinOps 計畫成效並向領導層報告
* **驗證資料品質**：確保成本資料的準確性和可靠性

---

## 👥 適用角色

| 角色 | 主要使用場景 |
|------|-------------|
| **FinOps 工程師/分析師** | 日常成本分析、優化建議、異常監控 |
| **雲端財務管理團隊** | 預算追蹤、成本預測、財務報告 |
| **Azure 成本管理者** | 資源優化、保留實例管理、成本控制 |
| **財務分析師** | 成本分攤、部門報告、ROI 分析 |
| **雲端架構師** | 架構成本評估、資源規劃、效能與成本平衡 |
| **IT 主管/CTO** | 高階成本概覽、趨勢分析、策略決策 |

---

## 💬 如何使用此技能（Commands）

您可以透過**自然語言指令**直接與 AI 助理互動，無需手動撰寫 SQL 查詢。以下是常見的使用方式：

### 基本查詢指令

* **「顯示最近 30 天的 Top 10 成本服務」**
* **「分析當月各資源群組的成本分配」**
* **「查看最近 6 個月的成本趨勢」**
* **「找出成本超過 $1000 的資源群組」**

### 優化分析指令

* **「幫我找出可以優化的高成本資源」**
* **「分析保留實例的使用率」**
* **「識別閒置或低使用率的資源」**
* **「比較本月與上月的成本差異」**

### 異常檢測指令

* **「檢測最近 7 天的成本異常」**
* **「找出成本激增超過 20% 的服務」**
* **「顯示異常支出的資源群組」**

### 成本分攤指令

* **「按環境標籤分配成本」**
* **「產生各部門的月度成本報告」**
* **「計算各成本中心的費用佔比」**

### 資料品質檢查指令

* **「檢查標籤覆蓋率」**
* **「驗證最近的資料更新時間」**
* **「找出缺少標籤的資源」**

### 儀表板查詢指令

* **「產生高階主管成本儀表板查詢」**
* **「建立 FinOps 團隊的日常監控查詢」**
* **「產生成本優化機會報告」**

### 💡 使用技巧

1. **明確指定時間範圍**：例如「最近 30 天」、「本月」、「2024 年 1 月」
2. **指定分組維度**：例如「依服務」、「依資源群組」、「依標籤」
3. **設定篩選條件**：例如「成本超過 $100」、「環境為 production」
4. **要求特定格式**：例如「產生 SQL 查詢」、「顯示圖表」、「匯出為表格」

### 🎯 範例對話

**使用者**：「幫我分析最近 30 天哪些 Azure 服務花費最多」

**AI 助理**：會自動產生並執行查詢，顯示 Top 10 成本服務及其費用

**使用者**：「找出可以優化的資源，成本超過 $500」

**AI 助理**：會分析高成本資源並提供優化建議（調整規模、保留實例等）

**使用者**：「產生本月各部門的成本分配報告」

**AI 助理**：會依標籤或資源群組產生成本分攤報告

---

## ⚡ 5 分鐘快速入門

### 1️⃣ 查看最近 30 天的 Top 10 成本服務

```sql
SELECT 
  ConsumedService,
  cost_category,
  ROUND(SUM(total_cost), 2) AS total_cost,
  COUNT(DISTINCT Date) AS days_active
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE Date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY ConsumedService, cost_category
ORDER BY total_cost DESC
LIMIT 10
```

**用途**：快速了解哪些 Azure 服務花費最多

---

### 2️⃣ 查看當月各資源群組的成本分配

```sql
SELECT 
  ResourceGroup,
  tag_environment,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  ROUND(SUM(total_cost) / SUM(SUM(total_cost)) OVER () * 100, 2) AS cost_share_pct
FROM develop_catalog.system_report.finops_resource_group_monthly
WHERE year_month = DATE_FORMAT(CURRENT_DATE(), 'yyyy-MM')
GROUP BY ResourceGroup, tag_environment
ORDER BY monthly_cost DESC
LIMIT 20
```

**用途**：了解各團隊或專案的成本佔比

---

### 3️⃣ 查看最近 6 個月的成本趨勢

```sql
SELECT 
  year_month,
  ROUND(SUM(total_cost), 2) AS monthly_cost,
  ROUND(SUM(reservation_cost), 2) AS reserved_cost,
  ROUND(SUM(on_demand_cost), 2) AS on_demand_cost,
  ROUND(SUM(reservation_cost) / NULLIF(SUM(total_cost), 0) * 100, 2) AS reserved_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 180), 'yyyy-MM')
GROUP BY year_month
ORDER BY year_month DESC
```

**用途**：追蹤成本趨勢和保留實例使用率

---

## 🧭 技能導航 - 我該使用哪個子技能？

根據您的需求，選擇適合的子技能：

```
您的需求是什麼？
│
├─ 💰 我想降低雲端成本
│   └─ 使用：[成本優化模式](skills/cost-optimization-patterns/SKILL.md)
│      • 調整過大資源規模
│      • 保留實例分析
│      • 閒置資源消除
│      • 儲存與網路優化
│
├─ 🚨 我想監控異常支出
│   └─ 使用：[進階異常檢測](skills/anomaly-detection-advanced/SKILL.md)
│      • 統計異常檢測
│      • 時間序列分析
│      • 成本激增警報
│
├─ 💳 我想分配成本給各部門/團隊
│   └─ 使用：[成本回收與展示指南](skills/chargeback-showback-guide/SKILL.md)
│      • 成本分配方法論
│      • 基於標籤的分配
│      • 共享成本分攤
│      • 部門報告
│
├─ 📊 我想追蹤 FinOps KPI
│   └─ 使用：[FinOps KPI 指標](skills/finops-kpi-metrics/SKILL.md)
│      • 成本效率指標
│      • 優化指標
│      • 治理指標
│      • 業務價值指標
│
├─ ✅ 我想驗證資料品質
│   └─ 使用：[資料品質驗證](skills/data-quality-validation/SKILL.md)
│      • 完整性檢查
│      • 準確性驗證
│      • 一致性驗證
│      • 標籤覆蓋率
│
└─ 📈 我想建立儀表板
    └─ 使用：[儀表板查詢](skills/dashboard-queries/SKILL.md)
       • 高階主管儀表板
       • FinOps 團隊儀表板
       • 成本中心儀表板
       • 優化儀表板
```

---

## 📋 先決條件

### 資料表存取權限

您需要有以下資料表的 **SELECT** 權限：

| 資料表 | 用途 | 必要性 |
|--------|------|--------|
| `develop_catalog.system_report.infra_azure_cost_usage_actual` | Bronze 層原始資料 | 選用（僅用於資料血緣） |
| `develop_catalog.system_report.infra_azure_cost_silver` | Silver 層清理資料 | 必要（詳細分析） |
| `develop_catalog.system_report.finops_daily_cost_summary` | Gold 層每日摘要 | 必要（日常查詢） |
| `develop_catalog.system_report.finops_resource_group_monthly` | Gold 層月度資源群組 | 必要（成本分配） |
| `develop_catalog.system_report.finops_service_monthly_trend` | Gold 層月度趨勢 | 必要（趨勢分析） |

### 資料新鮮度

* **更新頻率**：每日 UTC 時間 2:00 AM
* **資料延遲**：Azure 成本匯出可能有 1-2 天延遲
* **歷史資料**：保留 13-24 個月
* **驗證方式**：執行 `SELECT MAX(Date) FROM develop_catalog.system_report.finops_daily_cost_summary`

### 建議的 SQL 倉儲規模

* **探索性查詢**：Small (2X-Small 至 Small)
* **儀表板查詢**：Medium (針對 Gold 層優化)
* **大量歷史分析**：Large (處理 12+ 個月資料)

---

## 📚 資料架構概覽

### 三層架構

```
┌─────────────────────────────────────────────────────────────┐
│ Bronze 層 - 原始資料                                          │
│ infra_azure_cost_usage_actual                                │
│ • 原始 Azure 成本匯出（FinOps v1.2 規範）                     │
│ • 每日更新，保留 13-24 個月                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Silver 層 - 清理與豐富化                                      │
│ infra_azure_cost_silver                                      │
│ • 資料品質驗證                                                │
│ • 成本分類（運算、儲存、網路、資料庫、其他）                   │
│ • 區域分組（亞洲、美國、歐洲、其他）                           │
│ • 標籤提取（環境、成本中心、擁有者）                           │
│ • 保留實例識別                                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Gold 層 - 業務就緒的聚合                                      │
│                                                               │
│ finops_daily_cost_summary                                    │
│ • 每日聚合成本（依服務、類別、區域）                          │
│ • 次秒級查詢效能                                              │
│                                                               │
│ finops_resource_group_monthly                                │
│ • 月度資源群組成本分配                                        │
│ • 用於成本回收與預算追蹤                                      │
│                                                               │
│ finops_service_monthly_trend                                 │
│ • 月度服務趨勢與歷史比較                                      │
│ • 包含月對月、年對年成長率                                    │
└─────────────────────────────────────────────────────────────┘
```

### 選擇正確的層級

* **Gold 層**：用於儀表板、報告、日常查詢（推薦）
* **Silver 層**：用於詳細的資源層級分析、自訂聚合
* **Bronze 層**：僅用於資料血緣追蹤（避免直接查詢）

---

## 🚀 典型工作流程

### 工作流程 1：新手入門（第 1 週）

1. **驗證資料存取**
   ```sql
   SELECT MAX(Date) AS latest_date, COUNT(*) AS row_count
   FROM develop_catalog.system_report.finops_daily_cost_summary
   ```

2. **探索資料**：使用上方「5 分鐘快速入門」的 3 個查詢

3. **檢查資料品質**：參考 [資料品質驗證](skills/data-quality-validation/SKILL.md)

4. **建立第一個儀表板**：參考 [儀表板查詢](skills/dashboard-queries/SKILL.md)

---

### 工作流程 2：成本優化專案（持續進行）

1. **識別高成本領域**：使用 [儀表板查詢](skills/dashboard-queries/SKILL.md) 的優化儀表板

2. **分析優化機會**：參考 [成本優化模式](skills/cost-optimization-patterns/SKILL.md)

3. **設定異常監控**：使用 [進階異常檢測](skills/anomaly-detection-advanced/SKILL.md)

4. **追蹤優化成效**：使用 [FinOps KPI 指標](skills/finops-kpi-metrics/SKILL.md)

---

### 工作流程 3：實施成本分攤（1-2 個月）

1. **定義分配策略**：參考 [成本回收與展示指南](skills/chargeback-showback-guide/SKILL.md)

2. **驗證標籤覆蓋率**：使用 [資料品質驗證](skills/data-quality-validation/SKILL.md)

3. **建立分配報告**：使用 `finops_resource_group_monthly` 資料表

4. **設定定期報告**：自動化月度成本分配報告

---

## 💡 最佳實踐

### 查詢效能優化

✅ **DO（建議做法）**
* 始終依 `year_month` 或 `Date` 篩選（利用分區）
* 優先使用 Gold 層資料表（快 10-100 倍）
* 使用 `LIMIT` 限制結果集大小
* 針對大型查詢使用 `WHERE` 子句過濾

❌ **DON'T（避免做法）**
* 不要在沒有日期篩選的情況下掃描全表
* 不要直接查詢 Bronze 層進行分析
* 不要在 Silver 層做可以在 Gold 層完成的聚合

---

### 成本分析方法

* **跨時間比較**：始終包含月對月（MoM）和年對年（YoY）比較
* **標準化成本**：使用單位成本指標（例如：每 GB 成本、每 VM 成本）
* **分段分析**：依標籤、區域、服務和資源群組細分
* **設定閾值**：專注於重要項目（例如：成本 > $100 或佔比 > 1%）
* **趨勢分析**：觀察 3-6 個月的趨勢，而非單一時間點

---

### FinOps 成熟度路徑

| 階段 | 焦點 | 使用的子技能 |
|------|------|-------------|
| **爬行（Crawl）** | 基本可視化與報告 | 儀表板查詢、資料品質驗證 |
| **行走（Walk）** | 成本分配與優化 | 成本回收與展示、成本優化模式 |
| **奔跑（Run）** | 自動化與預測 | 異常檢測、FinOps KPI 指標 |

---

## 🆘 常見問題與疑難排解

### Q1: 查詢很慢，如何優化？

**解決方案**：
1. 確保依 `year_month` 或 `Date` 篩選
2. 使用 Gold 層資料表而非 Silver 層
3. 限制日期範圍（例如：最近 90 天）
4. 使用 `LIMIT` 限制結果數量

---

### Q2: 最近日期的資料遺失

**檢查步驟**：
1. 驗證資料新鮮度：
   ```sql
   SELECT MAX(Date) FROM develop_catalog.system_report.finops_daily_cost_summary
   ```
2. Azure 成本匯出可能有 1-2 天延遲（正常現象）
3. 檢查是否有資料管線失敗

---

### Q3: 標籤值顯示為 NULL

**原因與解決**：
* **原因**：資源在 Azure 中未標記
* **解決**：
  1. 檢查標籤覆蓋率報告（參考 [資料品質驗證](skills/data-quality-validation/SKILL.md)）
  2. 與資源擁有者協調補上標籤
  3. 使用資源群組或訂閱作為替代分組維度

---

### Q4: 成本數字與 Azure 入口網站不符

**檢查清單**：
* ✅ 日期範圍是否一致？
* ✅ 貨幣設定是否相同？
* ✅ 成本類型是否一致（實際 vs 攤銷）？
* ✅ 是否包含稅金和折扣？
* ✅ 資料是否為最新（檢查 `MAX(Date)`）？

---

### Q5: 如何取得資料表存取權限？

**申請步驟**：
1. 聯絡 FinOps 團隊或資料平台團隊
2. 說明使用目的和需要的資料表
3. 等待權限核准（通常 1-2 個工作日）

---

## 📞 取得協助

### 自助資源

1. **檢閱主技能文件**：[SKILL.md](SKILL.md)
2. **瀏覽子技能**：根據上方「技能導航」選擇相關子技能
3. **執行資料品質檢查**：[資料品質驗證](skills/data-quality-validation/SKILL.md)
4. **查看常見查詢範例**：[儀表板查詢](skills/dashboard-queries/SKILL.md)

### 聯絡支援

* **FinOps 團隊**：技能使用、資料問題、功能請求
* **資料平台團隊**：資料表權限、資料管線問題
* **Azure 成本管理團隊**：Azure 計費問題、成本匯出設定

---

## 📅 版本資訊

* **當前版本**：2.0（模組化架構）
* **最後更新**：2026-02-13
* **維護者**：FinOps 團隊
* **變更歷史**：
  * v2.0：重構為模組化架構，新增 6 個專門子技能
  * v1.0：初始版本（單體式）

---

## 🔗 相關資源

### FinOps 框架
* [FinOps Foundation](https://www.finops.org/)
* [FinOps v1.2 規範 (FOCUS)](https://focus.finops.org/)
* [FinOps 成熟度模型](https://www.finops.org/framework/maturity-model/)

### Azure 成本管理
* [Azure 成本管理最佳實踐](https://learn.microsoft.com/azure/cost-management-billing/)
* [Azure 定價計算機](https://azure.microsoft.com/pricing/calculator/)

### Databricks 資源
* [Databricks SQL 效能調校](https://docs.databricks.com/sql/admin/query-tuning.html)
* [Delta Lake 最佳實踐](https://docs.databricks.com/delta/best-practices.html)

---

**🎉 準備好開始了嗎？從上方「5 分鐘快速入門」的查詢開始探索您的 Azure 成本資料！**
