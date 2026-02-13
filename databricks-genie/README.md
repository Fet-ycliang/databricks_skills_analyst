# Databricks Genie

建立和查詢 Databricks Genie Spaces，用於自然語言 SQL 探索。

## 概述

此技能教導如何建立 Genie Spaces，讓使用者能夠對 Unity Catalog 中的結構化資料提出自然語言問題，並接收 SQL 生成的答案。當建立新的 Genie Spaces、新增範例問題或透過 Conversation API 以程式方式查詢 space 時，此技能會啟動。Genie Spaces 在商業使用者和複雜 SQL 之間架起橋樑，透過對話實現自助式分析。

## 包含內容

```
databricks-genie/
├── SKILL.md          # 主要技能參考：工具、快速入門和常見問題
├── conversation.md   # Genie Conversation API：ask_genie、後續問題、回應處理
└── spaces.md         # 建立和管理 Genie Spaces：資料表檢查、精選、最佳實踐
```

## 關鍵主題

- 使用 `create_or_update_genie` 建立 Genie Spaces
- 建立 space 前的資料表結構描述檢查工作流程
- 引用實際欄位名稱的範例問題設計
- 用於程式化查詢的 Conversation API（`ask_genie`、`ask_genie_followup`）
- 帶有對話上下文的後續問題
- SQL 倉儲的自動偵測和選擇
- 資料表選擇指南（建議使用 silver/gold 層）
- 使用指示和認證查詢進行 Space 精選
- 在 `ask_genie` 和直接 SQL（`execute_sql`）之間選擇

## 何時使用

- 您正在建立新的 Genie Space 用於資料探索
- 您需要將 Unity Catalog 資料表連接到對話介面
- 您想要以程式方式向現有的 Genie Space 提問
- 您正在使用範例查詢測試新建立的 Genie Space
- 您需要新增或改進範例問題以提升查詢生成品質
- 使用者明確說「詢問 Genie」或「使用我的 Genie Space」

## 相關技能

- [Agent Bricks](../agent-bricks/) -- 在多代理監督器中將 Genie Spaces 用作代理
- [Synthetic Data Generation](../synthetic-data-generation/) -- 生成原始 parquet 資料以填充 Genie 的資料表
- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 建立 Genie Spaces 使用的 bronze/silver/gold 資料表
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 管理 Genie 查詢的目錄、結構描述和資料表

## 資源

- [Databricks Genie 文件](https://docs.databricks.com/genie/)
- [Genie Conversation API](https://docs.databricks.com/api/workspace/genie)
