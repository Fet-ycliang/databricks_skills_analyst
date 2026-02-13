# 建立 Genie Spaces

本指南涵蓋建立和管理 Genie Spaces 以進行基於 SQL 的資料探索。

## 什麼是 Genie Space？

Genie Space 連接到 Unity Catalog 資料表，並將自然語言問題轉換為 SQL 查詢。系統會：

1. **理解**資料表結構描述和關聯性
2. **生成**來自自然語言的 SQL 查詢
3. **執行**在 SQL 倉儲上的查詢
4. **呈現**以對話格式顯示的結果

## 建立工作流程

### 步驟 1：檢查資料表結構描述（必要）

**在建立 Genie Space 之前，您必須檢查資料表結構描述**以了解可用的資料：

```python
get_table_details(
    catalog="my_catalog",
    schema="sales",
    table_stat_level="SIMPLE"
)
```

這會返回：
- 資料表名稱和列數
- 欄位名稱和資料類型
- 範例值和基數
- 空值計數和統計資訊

### 步驟 2：分析和規劃

根據結構描述資訊：

1. **選擇相關資料表** - 選擇支援使用者使用案例的資料表
2. **識別關鍵欄位** - 注意日期欄位、指標、維度和外鍵
3. **理解關聯性** - 資料表如何連接在一起？
4. **規劃範例問題** - 這些資料可以回答什麼問題？

### 步驟 3：建立 Genie Space

使用針對實際資料量身定制的內容建立 space：

```python
create_or_update_genie(
    display_name="銷售分析",
    table_identifiers=[
        "my_catalog.sales.customers",
        "my_catalog.sales.orders",
        "my_catalog.sales.products"
    ],
    description="""使用三個相關資料表探索零售銷售資料：
- customers：客戶人口統計資料，包括地區、區隔和註冊日期
- orders：交易歷史記錄，包含 order_date、total_amount 和 status
- products：產品目錄，包含 category、price 和 inventory

資料表透過 customer_id 和 product_id 連接。""",
    sample_questions=[
        "上個月的總銷售額是多少？",
        "按 total_amount 統計，誰是我們的前 10 名客戶？",
        "第四季按地區統計下了多少訂單？",
        "按客戶區隔統計的平均訂單價值是多少？",
        "哪些產品類別的收入最高？",
        "顯示 90 天內沒有下訂單的客戶"
    ]
)
```

## 為什麼這個工作流程很重要

**引用實際欄位名稱的範例問題**可幫助 Genie：
- 學習您資料的詞彙
- 生成更準確的 SQL 查詢
- 提供更好的自動完成建議

**解釋資料表關聯性的說明**可幫助 Genie：
- 理解如何正確連接資料表
- 知道哪個資料表包含哪些資訊
- 提供更相關的答案

## 倉儲的自動偵測

當未指定 `warehouse_id` 時，工具會：

1. 列出工作區中的所有 SQL 倉儲
2. 按以下順序優先排序：
   - **執行中**的倉儲優先（已經可用）
   - **啟動中**的倉儲其次
   - **較小的大小**優先（具成本效益）
3. 如果不存在倉儲則返回錯誤

要使用特定倉儲，請明確提供 `warehouse_id`。

## 資料表選擇

仔細選擇資料表以獲得最佳結果：

| 層級 | 建議 | 原因 |
|-------|-------------|-----|
| Bronze | 否 | 原始資料，可能有品質問題 |
| Silver | 是 | 已清理和驗證 |
| Gold | 是 | 已聚合，針對分析優化 |

### 資料表選擇提示

- **包含相關資料表**：如果使用者詢問客戶和訂單，請同時包含兩者
- **使用描述性欄位名稱**：`customer_name` 優於 `cust_nm`
- **新增資料表註解**：Genie 使用中繼資料來理解資料

## 範例問題

範例問題幫助使用者理解他們可以提出什麼問題：

**好的範例問題：**
- "上個月的總銷售額是多少？"
- "按收入統計，誰是我們的前 10 名客戶？"
- "第四季下了多少訂單？"
- "按地區統計的平均訂單價值是多少？"

這些會出現在 Genie UI 中以引導使用者。

## 最佳實踐

### 為 Genie 設計資料表

1. **描述性名稱**：使用 `customer_lifetime_value` 而不是 `clv`
2. **新增註解**：`COMMENT ON TABLE sales.customers IS '客戶主資料'`
3. **主鍵**：清楚定義關聯性
4. **日期欄位**：包含適當的日期/時間戳記欄位以進行基於時間的查詢

### 說明和上下文

在說明中提供上下文：

```
探索來自我們電子商務平台的零售銷售資料。包括：
- Customers：人口統計資料、區隔和帳戶狀態
- Orders：包含金額和日期的交易歷史記錄
- Products：包含類別和定價的目錄

時間範圍：最近 6 個月的資料
```

### 範例問題

撰寫範例問題時應：
- 涵蓋常見使用案例
- 展示資料的功能
- 使用自然語言（不是 SQL 術語）

## 更新 Genie Space

要更新現有的 space：

1. **新增/移除資料表**：使用更新的 `table_identifiers` 呼叫 `create_or_update_genie`
2. **更新問題**：包含新的 `sample_questions`
3. **變更倉儲**：提供不同的 `warehouse_id`

工具會按名稱尋找現有的 space 並更新它。

## 端到端工作流程範例

1. **生成合成資料**，使用 `synthetic-data-generation` 技能：
   - 在 `/Volumes/catalog/schema/raw_data/` 中建立 parquet 檔案

2. **建立資料表**，使用 `spark-declarative-pipelines` 技能：
   - 建立 `catalog.schema.bronze_*` → `catalog.schema.silver_*` → `catalog.schema.gold_*`

3. **檢查資料表**：
   ```python
   get_table_details(catalog="catalog", schema="schema")
   ```

4. **建立 Genie Space**：
   - `display_name`："我的資料探索器"
   - `table_identifiers`：`["catalog.schema.silver_customers", "catalog.schema.silver_orders"]`

5. **新增範例問題**，基於實際欄位名稱

6. **在 Databricks UI 中測試**

## 疑難排解

### 沒有可用的倉儲

- 在 Databricks 工作區中建立 SQL 倉儲
- 或提供特定的 `warehouse_id`

### 查詢緩慢

- 確保倉儲正在執行（未停止）
- 考慮使用較大的倉儲大小
- 檢查資料表是否已優化（OPTIMIZE、Z-ORDER）

### 查詢生成不佳

- 使用描述性欄位名稱
- 新增資料表和欄位註解
- 包含展示詞彙的範例問題
- 透過 Databricks Genie UI 新增指示
