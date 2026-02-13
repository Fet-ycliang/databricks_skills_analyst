---
name: databricks-genie
description: "建立和查詢 Databricks Genie Spaces，用於自然語言 SQL 探索。在建立 Genie Spaces 或透過 Genie Conversation API 提問時使用。"
---

# Databricks Genie

建立和查詢 Databricks Genie Spaces - 用於基於 SQL 的資料探索的自然語言介面。

## 概述

Genie Spaces 允許使用者對 Unity Catalog 中的結構化資料提出自然語言問題。系統將問題轉換為 SQL 查詢，在 SQL 倉儲上執行，並以對話方式呈現結果。

## 何時使用此技能

在以下情況使用此技能：
- 建立新的 Genie Space 用於資料探索
- 新增範例問題以引導使用者
- 將 Unity Catalog 資料表連接到對話介面
- 以程式方式向 Genie Space 提問（Conversation API）

## MCP 工具

### Space 管理

| 工具 | 用途 |
|------|---------|
| `list_genie` | 列出您可存取的所有 Genie Spaces |
| `create_or_update_genie` | 建立或更新 Genie Space |
| `get_genie` | 取得 Genie Space 詳細資訊 |
| `delete_genie` | 刪除 Genie Space |

### Conversation API

| 工具 | 用途 |
|------|---------|
| `ask_genie` | 向 Genie Space 提問，取得 SQL + 結果 |
| `ask_genie_followup` | 在現有對話中提出後續問題 |

### 支援工具

| 工具 | 用途 |
|------|---------|
| `get_table_details` | 在建立 space 前檢查資料表結構描述 |
| `execute_sql` | 直接測試 SQL 查詢 |

## 快速入門

### 1. 檢查您的資料表

在建立 Genie Space 之前，先了解您的資料：

```python
get_table_details(
    catalog="my_catalog",
    schema="sales",
    table_stat_level="SIMPLE"
)
```

### 2. 建立 Genie Space

```python
create_or_update_genie(
    display_name="銷售分析",
    table_identifiers=[
        "my_catalog.sales.customers",
        "my_catalog.sales.orders"
    ],
    description="使用自然語言探索銷售資料",
    sample_questions=[
        "上個月的總銷售額是多少？",
        "誰是我們的前 10 名客戶？"
    ]
)
```

### 3. 提問（Conversation API）

```python
ask_genie(
    space_id="your_space_id",
    question="上個月的總銷售額是多少？"
)
# 返回：SQL、欄位、資料、row_count
```

## 工作流程

```
1. 檢查資料表    → get_table_details
2. 建立 space    → create_or_update_genie
3. 查詢 space    → ask_genie（或在 Databricks UI 中測試）
4. 精選（選用）  → 使用 Databricks UI 新增指示
```

## 參考文件

- [spaces.md](spaces.md) - 建立和管理 Genie Spaces
- [conversation.md](conversation.md) - 透過 Conversation API 提問

## 先決條件

在建立 Genie Space 之前：

1. **Unity Catalog 中的資料表** - 包含資料的 Bronze/Silver/Gold 資料表
2. **SQL 倉儲** - 用於執行查詢的倉儲（如果未指定則自動偵測）

### 建立資料表

按順序使用這些技能：
1. `synthetic-data-generation` - 生成原始 parquet 檔案
2. `spark-declarative-pipelines` - 建立 bronze/silver/gold 資料表

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **沒有可用的倉儲** | 建立 SQL 倉儲或明確提供 `warehouse_id` |
| **查詢生成不佳** | 新增引用實際欄位名稱的指示和範例問題 |
| **查詢緩慢** | 確保倉儲正在執行；對資料表使用 OPTIMIZE |
