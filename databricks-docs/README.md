# Databricks 文件參考

Databricks 文件參考。作為查詢資源與其他技能和 MCP 工具一起使用，以獲得全面的指導。

## 概述

此技能透過 `llms.txt` 端點提供對完整 Databricks 文件索引的存取。當您需要查詢未被更具體技能涵蓋的 Databricks 概念、API 或功能時，此技能會啟動。它本身不執行操作，而是作為參考層，指導您如何使用 MCP 工具和其他面向操作的技能。

## 包含內容

```
databricks-docs/
  SKILL.md
  README.md
```

## 關鍵主題

- 獲取和導覽 Databricks `llms.txt` 文件索引
- 查詢有關 Databricks API 和概念的權威指導
- 使用參考文件補充操作技能
- 文件類別：資料工程、SQL 與分析、AI/ML、治理和開發者工具

## 何時使用

- 您需要有關未被其他技能涵蓋的 Databricks 功能的參考資訊
- 您想在使用 MCP 工具之前確認 API 詳細資訊或行為
- 使用者詢問不熟悉的 Databricks 概念或能力
- 您需要使用更深入的文件來補充工作流程技能（例如，`spark-declarative-pipelines`、`databricks-python-sdk`）

## 相關技能

- [Databricks Python SDK](../databricks-python-sdk/) -- 用於程式化 Databricks 存取的 SDK 模式
- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- DLT / Lakeflow 管線工作流程
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 治理和目錄管理
- [Model Serving](../model-serving/) -- 服務端點和模型部署
- [MLflow Evaluation](../mlflow-evaluation/) -- MLflow 3 GenAI 評估工作流程

## 資源

- [Databricks LLMs.txt 文件索引](https://docs.databricks.com/llms.txt)
- [Databricks 文件首頁](https://docs.databricks.com/)
