---
name: Azure FinOps Skills
description: 基於 FinOps 1.2 框架與 Azure 成本管理最佳實踐，提供全面的成本分析、優化、異常檢測與分攤功能。支援透過自然語言建立 FinOps 儀表板，協助 FinOps 工程師、財務分析師與 IT 主管進行雲端財務管理。
---

# Azure FinOps Skills - FinOps v1.2 框架

## 📋 概述

本技能提供基於 **FinOps v1.2 框架** (FOCUS) 的完整 Azure 成本管理與優化能力。它整合了 Azure 成本管理的最佳實踐，採用獎章架構（Bronze-Silver-Gold）來實現快速、高效的成本分析和報告。

### 🎯 適用場景
* **成本可視化**：分析 Azure 雲端成本流向，識別高成本服務。
* **成本優化**：識別閒置資源、調整規模機會與保留實例優化。
* **成本分攤**：將成本精確分配給業務單位、團隊或專案。
* **異常檢測**：即時發現異常支出模式與預算超支。
* **FinOps KPI**：追蹤關鍵財務營運指標與成熟度。

---

## 📊 資料架構

本技能採用三層資料架構設計，詳細規格請參閱 [資料架構參考](references/data-architecture.md)。

* **Bronze 層**：原始 Azure 成本匯出資料。
* **Silver 層**：清理與豐富化的資料，包含標籤與成本分類。
* **Gold 層**：針對高效能查詢優化的每日聚合與月度趨勢資料。

---

## 🎓 專門子技能

本技能包含 6 個專門子技能，每個專注於 FinOps 的特定面向：

| 子技能 | 焦點 | 連結 |
| :--- | :--- | :--- |
| **💰 成本優化模式** | 識別並實施成本節省機會 | [SKILL.md](cost-optimization-patterns/SKILL.md) |
| **🚨 進階異常檢測** | 檢測異常的支出模式和成本異常 | [SKILL.md](anomaly-detection-advanced/SKILL.md) |
| **💳 成本回收與展示** | 實施成本分配與責任歸屬模型 | [SKILL.md](chargeback-showback-guide/SKILL.md) |
| **📊 FinOps KPI 指標** | 追蹤和衡量 FinOps 成熟度與效能 | [SKILL.md](finops-kpi-metrics/SKILL.md) |
| **✅ 資料品質驗證** | 確保成本資料的準確性和可靠性 | [SKILL.md](data-quality-validation/SKILL.md) |
| **📈 儀表板查詢** | 用於建構 FinOps 儀表板的即用查詢 | [SKILL.md](dashboard-queries/SKILL.md) |

---

## 🤖 聊天機器人互動指南 (Chatbot Guide)

本節提供 Assistant 如何利用這些技能來回應使用者的自然語言提問。

### 🗣️ 自然語言觸發範例 (Intents)

| 使用者意圖 | 範例提問 | 推薦技能 |
| :--- | :--- | :--- |
| **成本總覽** | "上個月的總花費是多少？", "為什麼成本增加了？" | `references/common-queries.md` (基本摘要, 月度趨勢) |
| **成本優化** | "我有浪費的資源嗎？", "如何降低 VM 成本？" | `cost-optimization-patterns/SKILL.md` (閒置資源, RI, Spot) |
| **KPI 追蹤** | "我們的 RI 覆蓋率達標了嗎？", "單位成本是多少？" | `finops-kpi-metrics/SKILL.md` (KPI 1.2, 3.1) |
| **異常檢測** | "昨天有異常的高額支出嗎？" | `anomaly-detection-advanced/SKILL.md` |
| **名詞解釋** | "什麼是 Spot 實例？", "Chargeback 是什麼意思？" | `references/glossary.md` |

### 🔄 對話流程建議 (Conversation Flow)

1.  **高層次概覽 (High-Level)**：
    *   先使用 `common-queries.md` 中的「基本成本摘要」回答總數。
    *   *範例回應*："上個月總成本為 $50,000，較前月增長 5%。"

2.  **鑽取分析 (Drill-Down)**：
    *   若用戶詢問原因，檢查 `finops_daily_cost_summary` (Gold 層) 的 `cost_category` 或 `ConsumedService` 分佈。
    *   *範例回應*："增長主要來自 Compute 服務，佔了新增成本的 80%。"

3.  **提供建議 (Actionable Advice)**：
    *   主動查詢 `cost-optimization-patterns` 尋找節省機會。
    *   *範例回應*："我發現有 5 個閒置的 VM，如果關閉它們，每月可節省 $500。"

4.  **教育用戶 (Education)**：
    *   當涉及專有名詞時，參考 `references/glossary.md` 進行簡短解釋。

### 📚 知識庫
*   **FinOps 詞彙表**：[references/glossary.md](references/glossary.md) - 定義關鍵術語。

### 🤖 自動建立儀表板
直接對 Assistant 說：「建立一個 FinOps 儀表板」或「幫我建立綜合型 FinOps dashboard」，即可自動生成包含關鍵 KPI 與趨勢圖的報告。

---

## 🚀 快速入門

### 1. 驗證環境
在開始之前，請務必執行 [快速驗證查詢](references/validation-queries.md) 來檢查資料的新鮮度與完整性。

### 2. 資料探索
使用 [常見查詢模式](references/common-queries.md) 來熟悉核心數據表與分析方法。
- **基本成本摘要**：查看最近 30 天的成本分布。
- **月度趨勢**：分析近半年的成本成長與保留實例覆蓋率。
- **異常檢測**：快速掃描潛在的成本激增。

---

## 🎓 最佳實踐

### 查詢效能
* **分區過濾**：始終依 `year_month` 或 `date_key` (INT) 進行篩選以利用分區修剪。
* **層級選擇**：
  * **Gold 層**：用於大多數的聚合查詢與儀表板（快 10-100 倍）。
  * **Silver 層**：僅用於需要鑽取到特定資源 ID 的詳細分析。
* **結果限制**：使用 `LIMIT` 防止返回過多資料。

### FinOps 成熟度路徑
* **爬行 (Crawl)**：使用儀表板查詢進行基本的可視化與報告。
* **行走 (Walk)**：實施成本回收/展示，並應用成本優化模式。
* **奔跑 (Run)**：自動化異常檢測，並建立 KPI 驅動的優化流程。

---

## 💰 成本基準參考

| 服務類型 | 每月基準參考 | 異常閾值 (MoM) | 優化優先級 |
| :--- | :--- | :--- | :--- |
| **Virtual Machines** | $5k - $15k | +30% | 🔴 高 |
| **AKS** | $3k - $10k | +40% | 🔴 高 |
| **Storage** | $2k - $8k | +50% | 🟠 中 |
| **SQL Database** | $2k - $6k | +35% | 🟠 中 |

---

## 🔗 相關資源

* [FinOps Foundation](https://www.finops.org/)
* [Azure 成本管理文件](https://learn.microsoft.com/azure/cost-management-billing/)
* [Databricks SQL 效能調校](https://docs.databricks.com/sql/admin/query-tuning.html)

---

**最後更新**：2026-02-14
**版本**：2.2 (Refactored for Agent Skills)
**維護者**：FinOps 團隊
