---
name: finops_genie
description: 查詢 Databricks Genie spaces 以回答 Azure 成本與 FinOps 相關問題。當使用者詢問關於成本優化、閒置資源、預算追蹤或 FinOps KPI 時使用此技能。此技能管理與 Genie 的對話，包括啟動、追問和清理。
---

# FinOps Genie Skill

使用自然語言查詢 Databricks Genie spaces，以獲取 Azure 成本分析與優化建議。

## 可用的 Genie Spaces

> **Space ID 設定**：實際的 Space ID 定義在 [config.md](config.md) 中

| Space 名稱 | Space ID | 領域 | 用途 |
| :--- | :--- | :--- | :--- |
| **Azure Cost Optimization** | `${GENIE_FINOPS_SPACE_ID}` | 成本優化與分析 | 成本分析、優化建議、閒置資源、保留實例覆蓋率 |

## Space 選擇

根據問題類型路由到適當的 space：

| 問題主題 | Space 名稱 |
| :--- | :--- |
| 閒置資源、調整規模建議 | Azure Cost Optimization |
| 孤兒資源清理 (Snapshot) | Azure Cost Optimization |
| 儲存冗餘檢查 (GRS/LRS) | Azure Cost Optimization |
| 成本總覽與趨勢分析 | Azure Cost Optimization |

## 實作選項

### Python 腳本

執行 [scripts/genie_query.py](scripts/genie_query.py) 中的函式。

| 函式 | 用途 |
| :--- | :--- |
| `start_conversation(space_id, question)` | 啟動新的 Genie 對話 |
| `ask_followup(space_id, conversation_id, question)` | 詢問追問問題 |
| `delete_conversation(space_id, conversation_id)` | 完成後清理 |

## 工作流程說明

### 步驟 1：選擇正確的 Space

根據使用者的問題，從上表選擇適當的 `space_id`。

### 步驟 2：啟動對話

```python
from scripts.genie_query import start_conversation

response = start_conversation(
    space_id="${GENIE_FINOPS_SPACE_ID}",
    question="我們有多少閒置的 VM？"
)
# 回應中已包含：查詢答案、SQL 查詢、建議的後續問題
```

### 步驟 3：處理追問問題

使用 `response` 中的 `conversation_id` 進行追問：

```python
from scripts.genie_query import ask_followup

response = ask_followup(
    space_id="${GENIE_FINOPS_SPACE_ID}",
    conversation_id=previous_conversation_id,
    question="這些 VM 的總成本是多少？"
)
```

### 步驟 4：結束對話

完成對話或切換主題時，請務必清理：

```python
from scripts.genie_query import delete_conversation

delete_conversation(
    space_id="${GENIE_FINOPS_SPACE_ID}",
    conversation_id=previous_conversation_id
)
```

## 範例問答 (映射至 Genie 功能)

此技能將使用者的自然語言映射至 Genie Space 的能力。Genie Space 內部已配置了處理這些請求所需的 SQL 檢視表與邏輯。

| 使用者意圖 | 範例提問 | Genie 處理方式 (後端) |
| :--- | :--- | :--- |
| **閒置資源** | "找出所有閒置資源" | 查詢 `v_idle_resources` 檢視表 |
| **調整規模** | "哪些機器規格開太大了？" | 查詢 `v_right_sizing_recommendations` 檢視表 |
| **孤兒資源** | "清理沒用的快照" | 查詢 `v_orphaned_snapshots` 檢視表 |
| **儲存優化** | "Dev 環境有沒有人用 GRS？" | 查詢 `v_storage_redundancy_check` 檢視表 |

## 注意事項

1. **Space ID**: 確保環境變數 `${GENIE_FINOPS_SPACE_ID}` 已正確設定。
2. **對話管理**: 獲得滿意的答案或主題切換後，請呼叫 `delete_conversation` 清理對話。
