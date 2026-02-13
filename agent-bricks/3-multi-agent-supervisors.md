# 多代理監督器（MAS）

多代理監督器編排多個專業代理，根據查詢內容將使用者查詢路由到最合適的代理。

## 什麼是多代理監督器？

MAS 充當多個 AI 代理的流量控制器。當使用者提出問題時：

1. **分析**查詢以理解意圖
2. **路由**到最合適的專業代理
3. **返回**代理的回應給使用者

這允許您將多個專業代理組合成單一統一介面。

## 何時使用

在以下情況使用多代理監督器：
- 您有多個專業代理（帳務、技術支援、人力資源等）
- 使用者不應該需要知道要詢問哪個代理
- 您想要提供統一的對話體驗

## 先決條件

在建立 MAS 之前，您需要以下一種或兩種類型的代理：

**模型服務端點**（`endpoint_name`）：
- 知識助理（KA）端點（例如，`ka-abc123-endpoint`）
- 使用 LangChain、LlamaIndex 等建立的自訂代理
- 微調模型
- RAG 應用程式

**Genie Spaces**（`genie_space_id`）：
- 用於基於 SQL 的資料探索的現有 Genie spaces
- 非常適合分析、指標和資料驅動的問題
- 不需要單獨的端點部署 - 直接引用 space
- 要依名稱尋找 Genie space，請使用 `find_genie_by_name(display_name="My Genie")`
- **注意**：Genie spaces 沒有系統資料表 - 不要嘗試查詢 `system.ai.genie_spaces`

## 建立多代理監督器

使用 `create_or_update_mas` 工具：

- `name`："客戶支援 MAS"
- `agents`：
  ```json
  [
    {
      "name": "policy_agent",
      "ka_tile_id": "f32c5f73-466b-4798-b3a0-5396b5ece2a5",
      "description": "從索引文件中回答有關公司政策和程序的問題"
    },
    {
      "name": "usage_analytics",
      "genie_space_id": "01abc123-def4-5678-90ab-cdef12345678",
      "description": "回答有關使用量指標、趨勢和統計資料的資料問題"
    },
    {
      "name": "custom_agent",
      "endpoint_name": "my-custom-endpoint",
      "description": "透過自訂模型端點處理專業查詢"
    }
  ]
  ```
- `description`："將客戶查詢路由到專業支援代理"
- `instructions`："分析使用者的問題並路由到最合適的代理。如果不清楚，請要求澄清。"

此範例展示了混合使用知識助理（policy_agent）、Genie spaces（usage_analytics）和自訂端點（custom_agent）。

## 代理配置

`agents` 列表中的每個代理需要：

| 欄位 | 必要 | 說明 |
|-------|----------|-------------|
| `name` | 是 | 代理的內部識別碼 |
| `description` | 是 | 此代理處理什麼（對路由至關重要） |
| `ka_tile_id` | 三選一 | 知識助理 tile ID（用於文件問答代理） |
| `genie_space_id` | 三選一 | Genie space ID（用於基於 SQL 的資料代理） |
| `endpoint_name` | 三選一 | 模型服務端點名稱（用於自訂代理） |

**注意**：必須提供以下其中一個：`ka_tile_id`、`genie_space_id` 或 `endpoint_name`。

要尋找 KA tile_id，請使用 `find_ka_by_name(name="Your KA Name")`。
要尋找 Genie space_id，請使用 `find_genie_by_name(display_name="Your Genie Name")`。

### 撰寫好的描述

`description` 欄位對路由至關重要。使其具體：

**好的描述：**
- "處理帳務問題，包括發票、付款、退款和訂閱變更"
- "回答有關 API 錯誤、整合問題和產品錯誤的技術問題"
- "提供有關人力資源政策、休假、福利和員工手冊的資訊"

**不好的描述：**
- "帳務代理"（太模糊）
- "處理事情"（沒有幫助）
- "技術"（不具體）

## 佈建時間表

建立後，MAS 端點需要佈建：

| 狀態 | 意義 | 持續時間 |
|--------|---------|----------|
| `PROVISIONING` | 正在建立監督器 | 2-5 分鐘 |
| `ONLINE` | 準備路由查詢 | - |
| `OFFLINE` | 目前未執行 | - |

使用 `get_mas` 檢查狀態。

## 新增範例問題

範例問題有助於評估並可以引導路由優化：

```json
{
  "examples": [
    {
      "question": "我還沒有收到本月的發票",
      "guideline": "應該路由到 billing_agent"
    },
    {
      "question": "API 返回 500 錯誤",
      "guideline": "應該路由到 technical_agent"
    },
    {
      "question": "我有多少天假期？",
      "guideline": "應該路由到 hr_agent"
    }
  ]
}
```

如果 MAS 尚未 `ONLINE`，範例會排入佇列並在準備就緒時自動新增。

## 最佳實踐

### 代理設計

1. **專業代理**：每個代理應該有清晰、明確的目的
2. **非重疊領域**：避免具有相似描述的代理
3. **清晰的界限**：定義每個代理處理和不處理的內容

### 指示

提供路由指示：

```
您是客戶支援監督器。您的工作是將使用者查詢路由到正確的專家：

1. 對於帳務、付款或訂閱問題 → billing_agent
2. 對於技術問題、錯誤或 API 問題 → technical_agent
3. 對於人力資源、福利或政策問題 → hr_agent

如果查詢不清楚或跨越多個領域，請要求使用者澄清。
```

### 備用處理

考慮為不適合其他地方的查詢新增通用代理：

```json
{
  "name": "general_agent",
  "endpoint_name": "general-support-endpoint",
  "description": "處理不適合其他類別的一般查詢，提供導覽幫助"
}
```

## 範例工作流程

1. **部署專業代理**作為模型服務端點：
   - `billing-assistant-endpoint`
   - `tech-support-endpoint`
   - `hr-assistant-endpoint`

2. **建立 MAS**：
   - 使用清晰的描述配置代理
   - 新增路由指示

3. **等待 ONLINE 狀態**（2-5 分鐘）

4. **新增範例問題**用於評估

5. **使用各種查詢類型測試路由**

## 更新多代理監督器

要更新現有的 MAS：

1. **新增/移除代理**：使用更新的 `agents` 列表呼叫 `create_or_update_mas`
2. **更新描述**：變更代理描述以改進路由
3. **修改指示**：更新路由規則

該工具會依名稱尋找現有的 MAS 並更新它。

## 疑難排解

### 查詢路由到錯誤的代理

- 檢閱並改進代理描述
- 使描述更具體和明確
- 新增展示正確路由的範例

### 端點無回應

- 驗證每個底層模型服務端點是否正在執行
- 檢查端點日誌以尋找錯誤
- 確保端點接受預期的輸入格式

### 回應緩慢

- 檢查底層端點的延遲
- 考慮端點擴展設定
- 監控冷啟動問題

## 進階：階層式路由

對於複雜情境，您可以建立多層級的 MAS：

```
頂層 MAS
├── 客戶支援 MAS
│   ├── billing_agent
│   ├── technical_agent
│   └── general_agent
├── 銷售 MAS
│   ├── pricing_agent
│   ├── demo_agent
│   └── contract_agent
└── 內部 MAS
    ├── hr_agent
    └── it_helpdesk_agent
```

每個子 MAS 都部署為端點，並在頂層 MAS 中配置為代理。
