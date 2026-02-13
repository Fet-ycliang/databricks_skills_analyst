# Genie 對話

使用 Genie Conversation API 向精選的 Genie Space 提出自然語言問題。

## 概述

`ask_genie` 工具允許您以程式方式向 Genie Space 發送問題並接收 SQL 生成的答案。您不需要直接撰寫 SQL，而是將查詢生成委託給 Genie，Genie 已經過商業邏輯、指示和認證查詢的精選。

## 何時使用 `ask_genie`

### 使用 `ask_genie` 的時機：

| 情境 | 原因 |
|----------|-----|
| Genie Space 具有精選的商業邏輯 | Genie 知道規則，例如「活躍客戶 = 90 天內下過訂單」 |
| 使用者明確說「詢問 Genie」或「使用我的 Genie Space」 | 使用者意圖使用其精選的 space |
| 具有特定定義的複雜商業指標 | Genie 具有官方指標的認證查詢 |
| 建立後測試 Genie Space | 驗證 space 是否正常運作 |
| 使用者想要對話式資料探索 | Genie 處理後續問題的上下文 |

### 改用直接 SQL（`execute_sql`）的時機：

| 情境 | 原因 |
|----------|-----|
| 簡單的臨時查詢 | 直接 SQL 更快，不需要精選 |
| 您已經有確切的 SQL | 不需要 Genie 重新生成 |
| 此資料不存在 Genie Space | 沒有 space 就無法使用 Genie |
| 需要精確控制查詢 | 直接 SQL 提供精確控制 |

## MCP 工具

| 工具 | 用途 |
|------|---------|
| `ask_genie` | 提出問題，開始新對話 |
| `ask_genie_followup` | 在現有對話中提出後續問題 |

## 基本用法

### 提出問題

```python
ask_genie(
    space_id="01abc123...",
    question="上個月的總銷售額是多少？"
)
```

**回應：**
```python
{
    "question": "上個月的總銷售額是多少？",
    "conversation_id": "conv_xyz789",
    "message_id": "msg_123",
    "status": "COMPLETED",
    "sql": "SELECT SUM(total_amount) AS total_sales FROM orders WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH) AND order_date < DATE_TRUNC('month', CURRENT_DATE)",
    "columns": ["total_sales"],
    "data": [[125430.50]],
    "row_count": 1
}
```

### 提出後續問題

使用第一個回應中的 `conversation_id` 提出帶有上下文的後續問題：

```python
# 第一個問題
result = ask_genie(
    space_id="01abc123...",
    question="上個月的總銷售額是多少？"
)

# 後續問題（使用第一個問題的上下文）
ask_genie_followup(
    space_id="01abc123...",
    conversation_id=result["conversation_id"],
    question="按地區細分"
)
```

Genie 會記住上下文，因此「那個」指的是「上個月的總銷售額」。

## 回應欄位

| 欄位 | 說明 |
|-------|-------------|
| `question` | 提出的原始問題 |
| `conversation_id` | 用於後續問題的 ID |
| `message_id` | 唯一訊息識別碼 |
| `status` | `COMPLETED`、`FAILED`、`CANCELLED`、`TIMEOUT` |
| `sql` | Genie 生成的 SQL 查詢 |
| `columns` | 結果中的欄位名稱列表 |
| `data` | 查詢結果，以列的列表形式呈現 |
| `row_count` | 返回的列數 |
| `text_response` | 文字說明（如果 Genie 要求澄清） |
| `error` | 錯誤訊息（如果狀態不是 COMPLETED） |

## 處理回應

### 成功回應

```python
result = ask_genie(space_id, "誰是我們的前 10 名客戶？")

if result["status"] == "COMPLETED":
    print(f"SQL: {result['sql']}")
    print(f"列數: {result['row_count']}")
    for row in result["data"]:
        print(row)
```

### 失敗回應

```python
result = ask_genie(space_id, "生命的意義是什麼？")

if result["status"] == "FAILED":
    print(f"錯誤: {result['error']}")
    # Genie 無法回答 - 可能需要重新表述或使用直接 SQL
```

### 逾時

```python
result = ask_genie(space_id, question, timeout_seconds=60)

if result["status"] == "TIMEOUT":
    print("查詢時間過長 - 嘗試更簡單的問題或增加逾時時間")
```

## 範例工作流程

### 工作流程 1：使用者要求使用 Genie

```
使用者：「詢問我的銷售 Genie 流失率是多少」

Claude：
1. 識別使用者想要使用 Genie（明確請求）
2. 呼叫 ask_genie(space_id="sales_genie_id", question="流失率是多少？")
3. 返回：「根據您的銷售 Genie，流失率為 4.2%。
   Genie 使用了這個 SQL：SELECT ...」
```

### 工作流程 2：測試新的 Genie Space

```
使用者：「我剛建立了一個 HR 資料的 Genie Space。你能測試它嗎？」

Claude：
1. 從使用者或最近的 create_or_update_genie 結果取得 space_id
2. 使用測試問題呼叫 ask_genie：
   - 「我們有多少員工？」
   - 「按部門統計的平均薪資是多少？」
3. 報告結果：「您的 HR Genie 正常運作。它正確回答了...」
```

### 工作流程 3：使用後續問題進行資料探索

```
使用者：「使用我的分析 Genie 探索銷售趨勢」

Claude：
1. ask_genie(space_id, "今年每月的總銷售額是多少？")
2. 使用者：「哪個月的成長最高？」
3. ask_genie_followup(space_id, conv_id, "哪個月的成長最高？")
4. 使用者：「哪些產品推動了該成長？」
5. ask_genie_followup(space_id, conv_id, "哪些產品推動了該成長？")
```

## 最佳實踐

### 為新主題開始新對話

不要在不相關的問題之間重複使用對話：

```python
# 良好：為新主題開始新對話
result1 = ask_genie(space_id, "上個月的銷售額是多少？")  # 新對話
result2 = ask_genie(space_id, "我們有多少員工？")  # 新對話

# 良好：相關問題的後續
result1 = ask_genie(space_id, "上個月的銷售額是多少？")
result2 = ask_genie_followup(space_id, result1["conversation_id"],
                              "按產品細分")  # 相關後續
```

### 處理澄清請求

Genie 可能會要求澄清而不是返回結果：

```python
result = ask_genie(space_id, "顯示資料")

if result.get("text_response"):
    # Genie 正在要求澄清
    print(f"Genie 詢問：{result['text_response']}")
    # 使用更多細節重新表述
```

### 設定適當的逾時時間

- 簡單聚合：30-60 秒
- 複雜連接：60-120 秒
- 大型資料掃描：120+ 秒

```python
# 快速問題
ask_genie(space_id, "今天有多少訂單？", timeout_seconds=30)

# 複雜分析
ask_genie(space_id, "計算所有客戶的客戶終身價值",
          timeout_seconds=180)
```

## 疑難排解

### 「找不到 Genie Space」

- 驗證 `space_id` 是否正確
- 檢查您是否有權存取該 space
- 使用 `get_genie(space_id)` 驗證它是否存在

### 「查詢逾時」

- 增加 `timeout_seconds`
- 簡化問題
- 檢查 SQL 倉儲是否正在執行

### 「無法生成 SQL」

- 更清楚地重新表述問題
- 檢查問題是否可以用可用的資料表回答
- 透過 Databricks UI 向 Genie Space 新增更多指示/精選

### 意外結果

- 檢閱回應中生成的 SQL
- 透過 Databricks UI 向 Genie Space 新增 SQL 指示
- 新增展示正確模式的範例問題
