# Databricks 向量搜尋

Databricks 向量搜尋模式：建立端點和索引、使用篩選器查詢、管理嵌入。

## 概述

此技能涵蓋在 Databricks 上為 RAG 和語義搜尋應用程式建立、管理和查詢向量搜尋索引。當建立檢索增強生成管線、實作相似度匹配或在端點和索引類型之間選擇時，此技能會啟動。該技能詳細說明標準和儲存優化端點、所有三種索引類型（Delta 同步託管、Delta 同步自管理、直接存取），以及篩選、混合搜尋和 CLI 操作。

## 包含內容

```
vector-search/
├── SKILL.md          # 主要技能參考：端點、索引、查詢、篩選和 CLI
└── index-types.md    # 索引類型的詳細比較，包含建立模式和決策樹
```

## 關鍵主題

- 標準 vs. 儲存優化端點（延遲、容量、成本權衡）
- 使用託管嵌入的 Delta 同步索引（最簡單的設定）
- 使用自管理（預先計算）嵌入的 Delta 同步索引
- 用於即時 CRUD 操作的直接存取索引
- 使用 `query_text`、`query_vector` 和混合搜尋進行查詢
- 篩選：字典樣式（`filters_json`）和類 SQL（`filter_string`）
- 內建的 Databricks 嵌入模型（`databricks-gte-large-en`、`databricks-bge-large-en`）
- 觸發式 vs. 持續管線同步
- 索引掃描和手動同步操作
- 用於端點和索引管理的 Databricks CLI 快速參考

## 何時使用

- 您正在建立 RAG 應用程式並需要向量索引
- 您需要在標準和儲存優化端點之間選擇
- 您正在從 Delta 資料表建立 Delta 同步或直接存取索引
- 您需要使用文字、向量或混合搜尋查詢向量索引
- 您想要套用中繼資料篩選器以縮小搜尋結果範圍
- 您正在將向量搜尋整合為代理中的檢索器工具

## 相關技能

- [Model Serving](../model-serving/) -- 部署使用 VectorSearchRetrieverTool 的代理
- [Agent Bricks](../agent-bricks/) -- 知識助理使用 RAG 處理索引文件
- [Unstructured PDF Generation](../unstructured-pdf-generation/) -- 生成要在向量搜尋中索引的文件
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 管理支援 Delta 同步索引的目錄和資料表
- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 建立用作向量搜尋來源的 Delta 資料表

## 資源

- [Databricks 向量搜尋文件](https://docs.databricks.com/generative-ai/vector-search.html)
- [向量搜尋 Python SDK 參考](https://docs.databricks.com/dev-tools/sdk-python/vector-search.html)
