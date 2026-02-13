---
name: databricks-docs
description: "Databricks 文件參考。作為查詢資源與其他技能和 MCP 工具一起使用，以獲得全面的指導。"
---

# Databricks 文件參考

此技能透過 llms.txt 提供對完整 Databricks 文件索引的存取 - 將其作為**參考資源**使用，以補充其他技能並指導您使用 MCP 工具。

## 此技能的角色

這是一個**參考技能**，而非操作技能。使用它來：

- 當其他技能未涵蓋某個主題時查詢文件
- 取得有關 Databricks 概念和 API 的權威指導
- 尋找詳細資訊以指導您如何使用 MCP 工具
- 發現您可能不知道的功能和能力

**始終優先使用 MCP 工具進行操作**（execute_sql、create_or_update_pipeline 等），並**載入特定技能以處理工作流程**（databricks-python-sdk、spark-declarative-pipelines 等）。當您需要參考文件時使用此技能。

## 如何使用

獲取 llms.txt 文件索引：

**URL：** `https://docs.databricks.com/llms.txt`

使用 WebFetch 檢索此索引，然後：

1. 搜尋相關章節/連結
2. 獲取特定文件頁面以取得詳細指導
3. 使用適當的 MCP 工具應用您學到的內容

## 文件結構

llms.txt 檔案按類別組織：

- **概述與入門** - 基本概念和教學
- **資料工程** - Lakeflow、Spark、Delta Lake、管線
- **SQL 與分析** - 倉儲、查詢、儀表板
- **AI/ML** - MLflow、模型服務、GenAI
- **治理** - Unity Catalog、權限、安全性
- **開發者工具** - SDK、CLI、API、Terraform

## 範例：補充其他技能

**情境：**使用者想要建立 Delta Live Tables 管線

1. 載入 `spark-declarative-pipelines` 技能以取得工作流程模式
2. 如果您需要澄清特定 DLT 功能，使用此技能獲取文件
3. 使用 `create_or_update_pipeline` MCP 工具實際建立管線

**情境：**使用者詢問不熟悉的 Databricks 功能

1. 獲取 llms.txt 以尋找相關文件
2. 閱讀特定文件以了解該功能
3. 確定適用哪些技能/工具，然後使用它們
