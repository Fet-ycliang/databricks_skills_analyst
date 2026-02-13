# Agent Bricks

建立和管理 Databricks Agent Bricks：用於文件問答的知識助理（KA）、用於 SQL 探索的 Genie Spaces，以及用於多代理編排的多代理監督器（MAS）。

## 概述

此技能涵蓋使用三種預建 Agent Brick 類型在 Databricks 上建立對話式 AI 應用程式。當您需要建立基於文件的問答系統、自然語言 SQL 介面，或將多個專業代理編排成統一體驗時，此技能會啟動。Agent Bricks 大幅減少了從原始資料到生產就緒的對話式 AI 所需的工作量。

## 包含內容

```
agent-bricks/
├── SKILL.md                        # 主要技能參考：工具、工作流程和最佳實踐
├── 1-knowledge-assistants.md       # KA 建立、佈建和範例的深入探討
└── 3-multi-agent-supervisors.md    # MAS 路由、代理配置和階層式模式的深入探討
```

## 關鍵主題

- 用於基於 RAG 的文件問答的知識助理（KA），資料來源為 Unity Catalog 磁碟區
- 用於自然語言轉 SQL 探索的 Genie Spaces（委託給 `databricks-genie` 技能）
- 用於跨多個專業代理路由查詢的多代理監督器（MAS）
- 用於建立、更新、尋找和刪除每種磚塊類型的 MCP 工具
- 佈建生命週期和端點狀態監控
- 從配套 JSON 檔案自動擷取範例
- 用於準確 MAS 查詢路由的代理描述最佳實踐
- 階層式多層級 MAS 架構

## 何時使用

- 您需要從儲存在磁碟區中的 PDF 或文字檔案建立文件問答聊天機器人
- 您想要在 Unity Catalog 資料表中的結構化資料上建立自然語言介面
- 您正在將多個專業代理（帳務、人力資源、技術支援）組合在單一對話端點後面
- 您需要依名稱尋找現有的 KA 或 MAS 以檢索其 tile ID 或端點名稱
- 您正在將 KA 端點、Genie Spaces 和自訂模型服務端點一起編排在一個 MAS 中

## 相關技能

- [Databricks Genie](../databricks-genie/) -- 全面的 Genie Space 建立、精選和 Conversation API 指導
- [Unstructured PDF Generation](../unstructured-pdf-generation/) -- 生成合成 PDF 以提供給知識助理
- [Synthetic Data Generation](../synthetic-data-generation/) -- 為 Genie Space 資料表建立原始資料
- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 建立 Genie Spaces 使用的 bronze/silver/gold 資料表
- [Model Serving](../model-serving/) -- 部署用作 MAS 代理的自訂代理端點
- [Vector Search](../vector-search/) -- 為與 KA 配對的 RAG 應用程式建立向量索引

## 資源

- [Databricks Agent Framework 文件](https://docs.databricks.com/generative-ai/agent-framework/)
- [Databricks Model Serving 文件](https://docs.databricks.com/machine-learning/model-serving/)
