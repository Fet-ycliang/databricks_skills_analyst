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

### 路由範例

| 問題                             | Space 名稱 |
| -------------------------------- | ---------- |
| "閒置資源、調整規模建議"       | Azure CostUsage Optimization |
| "成本總覽與趨勢分析？"         | Azure CostUsage Optimization |

## 實作選項

### Python 腳本

執行 [scripts/genie_query.py](scripts/genie_query.py) 中的函式。

| 函式 | 用途 |
| :--- | :--- |
| `start_conversation(space_id, question)` | 啟動新的 Genie 對話 |
| `ask_followup(space_id, conversation_id, question)` | 詢問追問問題 |
| `get_query_result(space_id, conversation_id, message_id)` | 取得查詢結果 |
| `send_message_feedback(space_id, conversation_id, message_id, rating)` | 發送消息反饋 |
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
# 重要：儲存這些資訊以供後續使用
conversation_id = response.conversation_id
message_id = response.message_id  # 用於取得查詢結果
```

### 步驟 3：取得查詢結果（自動執行，四部分內容）

查詢結果會在 `start_conversation()` 完成後**自動提取和合併**到回應中：

**第一部分：查詢答案**
- 從 `attachments[].text.content` 提取自然語言答案
- 包含：對問題的直接回答和分析結論

**第二部分：查詢元數據**
- 呼叫 `get_message_query_result()` 取得欄位定義和 statement_id
- 包含：欄位名稱、資料類型、查詢狀態

**第三部分：SQL 查詢**
- 從 `attachments[].query.query` 提取生成的 SQL
- 包含：完整的 SQL 查詢語句

**第四部分：建議的後續問題**
- 從 `attachments[].suggested_questions` 提取
- 包含：引導進一步分析的後續問題列表

```python
from scripts.genie_query import start_conversation

response = start_conversation(
    space_id="${GENIE_COST_SPACE_ID}",
    question="<使用者問題>"
)
# 回應中已包含（按順序）：
# 1. 查詢答案（自然語言分析結論）
# 2. 查詢描述（Genie 如何理解問題）
# 3. SQL 查詢（生成的 SQL 語句）
# 4. 查詢結果行數（資料筆數）
# 5. 建議的後續問題（可進一步探索的方向）
```

**如果需要單獨取得查詢結果**（例如非 start_conversation 的情況），可使用：

```python
from scripts.genie_query import get_query_result

query_result = get_query_result(
    space_id="${GENIE_COST_SPACE_ID}",
    conversation_id=conversation_id,
    message_id=message_id
)
```

### 步驟 4：處理追問問題

使用 `response` 中的 `conversation_id` 進行追問：

```python
from scripts.genie_query import ask_followup

response = ask_followup(
    space_id="${GENIE_FINOPS_SPACE_ID}",
    conversation_id=previous_conversation_id,
    question="這些 VM 的總成本是多少？"
)
```

### 步驟 5：結束對話

完成對話或切換主題時，請務必清理：

```python
from scripts.genie_query import delete_conversation

delete_conversation(
    space_id="${GENIE_FINOPS_SPACE_ID}",
    conversation_id=previous_conversation_id
)
```

### 步驟 6：重新整理 / 啟動新對話

如果使用者想要重新開始或重置：

1. 刪除當前對話：

   ```python
   delete_conversation(space_id, conversation_id)
   ```

2. 詢問使用者：「您想了解什麼？」

3. 使用 `start_conversation()` 啟動新對話

**觸發重新整理的關鍵字：**「重新開始」、「新問題」、「重置」

### 在 Spaces 之間切換

如果追問問題屬於不同的 space：

1. 刪除當前對話
2. 在適當的 space 中啟動新對話
3. 告知使用者您正在查詢不同的資料來源

## 範例會話

```python
from scripts.genie_query import start_conversation, ask_followup, delete_conversation

# 使用者：「上個月 Databricks 的費用是多少？」
# → 自動取得查詢結果（不需手動呼叫 get_query_result）
response = start_conversation(
    space_id="${GENIE_COST_SPACE_ID}", 
    question="上個月 Databricks 的費用是多少？"
)
# → 回應已包含：SQL 查詢、查詢結果、建議的後續問題

# 儲存對話 ID 以供追問使用
conversation_id = response.conversation_id

# 使用者：「請按計費模型分類」
response = ask_followup(
    space_id="${GENIE_COST_SPACE_ID}",
    conversation_id=conversation_id,
    question="請按計費模型分類"
)

# 繼續提問...
response = ask_followup(
    space_id="${GENIE_COST_SPACE_ID}",
    conversation_id=conversation_id,
    question="最貴的資源群組是什麼?"
)

# 完成對話清理
delete_conversation(
    space_id="${GENIE_COST_SPACE_ID}",
    conversation_id=conversation_id
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

## 回應內容的重點提取

Genie API 回應包含以下重點資訊，系統會自動提取並記錄：

### 1. 查詢答案
* **包含在**: `response.attachments[].text.content`
* **記錄位置**: 日誌中輸出「找到查詢答案」
* **用途**: 直接回答使用者問題，包含分析結論

### 2. 查詢描述
* **包含在**: `response.attachments[].query.description`
* **記錄位置**: 日誌中輸出「查詢描述」
* **用途**: 瞭解 Genie 如何理解和重新表述問題

### 3. SQL 查詢
* **包含在**: `response.attachments[].query.query`
* **記錄位置**: 日誌中輸出完整 SQL
* **用途**: 瞭解 Genie 如何轉換自然語言為 SQL

### 4. 查詢結果行數
* **包含在**: `response.attachments[].query.query_result_metadata.row_count`
* **記錄位置**: 日誌中輸出「查詢結果行數」
* **用途**: 瞭解查詢返回多少行資料

### 5. 建議的後續問題
* **包含在**: `response.attachments[].suggested_questions.questions[]`
* **記錄位置**: 日誌中輸出每個建議問題
* **用途**: 引導使用者進行進一步的查詢

## 對話狀態

**在對話期間追蹤這些值：**

* `space_id` - 當前的 Genie space ID
* `conversation_id` - 從 `start_conversation()` 返回，用於追問

## 實作細節

### API 非同步處理機制

Genie API 採用非同步處理模式，需要輪詢等待結果：

#### start_conversation 處理流程
1. **立即回應**：API 返回 `GenieMessage` 對象，初始狀態為 `PENDING_WAREHOUSE`
2. **自動等待**：使用 `start_conversation_and_wait()` SDK 方法，內部自動處理輪詢
3. **完成狀態**：SDK 會等到 `status == COMPLETED` 才返回完整結果

#### ask_followup 處理流程
1. **建立訊息**：使用 `create_message()` 發送追問，立即返回
2. **手動輪詢**：每 **3 秒**查詢一次對話狀態
3. **狀態檢查**：檢查最新訊息的 `status` 是否為 `COMPLETED`
4. **完成回應**：當狀態為 `COMPLETED` 且有內容時返回結果
5. **取得結果**：同樣執行兩階段查詢結果取得（元數據 + 實際資料）

**訊息狀態流程：**
```
PENDING_WAREHOUSE → EXECUTING_QUERY → COMPLETED
```

### 日誌追蹤

實作中包含詳細的日誌輸出，便於追蹤與除錯：
* **狀態追蹤**：記錄每次輪詢的訊息狀態
* **效能監控**：記錄總耗時和輪詢次數
* **內容驗證**：DEBUG 模式下輸出完整回應內容

## 函式參數說明

### start_conversation

* `space_id` (str): 要查詢的 Genie space ID
* `question` (str): 自然語言問題
* `timeout_minutes` (int, 可選): 最大等待時間，預設 20

### ask_followup

* `space_id` (str): Genie space ID
* `conversation_id` (str): 來自 start_conversation 回應
* `question` (str): 追問問題
* `timeout_minutes` (int, 可選): 最大等待時間，預設 20

### get_query_result

* `space_id` (str): Genie space ID
* `conversation_id` (str): 對話 ID
* `message_id` (str): 訊息 ID（來自 start_conversation 或 ask_followup 回應）

### send_message_feedback

* `space_id` (str): Genie space ID
* `conversation_id` (str): 對話 ID
* `message_id` (str): 訊息 ID
* `rating` (str): 評分（例如：'positive' 或 'negative'）

### delete_conversation

* `space_id` (str): Genie space ID
* `conversation_id` (str): 要刪除的對話 ID

## 注意事項

1. **環境變數設定**: 確保已設定 `GENIE_COST_SPACE_ID`、`GENIE_STORAGE_SPACE_ID`、`GENIE_WORKFLOW_SPACE_ID` 環境變數
2. **逾時控制**: 複雜查詢可能需要調整 `timeout_minutes` 參數
3. **對話清理**: 記得在結束時呼叫 `delete_conversation()` 以釋放資源
4. **錯誤處理**: 檢查回應內容確認查詢是否成功
5. **Space 選擇**: 根據問題類型選擇正確的 Space，避免查詢錯誤的資料來源

## 文件與交付規範

所有專案相關文件與交付物 (Artifacts) 必須使用**繁體中文**撰寫，包括但不限於：

* **Implementation Plan (實作計畫)**: 規劃變更時使用。
* **Walkthrough (演練)**: 驗證與交付時使用。
* **Task List (任務列表)**: 追蹤進度時使用。
* **Project Guidelines**: 專案指引相關文件。

這有助於保持溝通的一致性與清晰度。

