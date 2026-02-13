# 合成資料生成

使用 Faker 和 Spark 生成逼真的合成資料，具有非線性分佈、完整性約束，並儲存到 Databricks。

## 概述

此技能指導使用 Python 搭配 Faker、NumPy 和 Spark 為 Databricks 生成逼真的、故事驅動的合成資料。當使用者需要測試資料、示範資料集，或具有可信分佈和參照完整性的合成資料表時，此技能會啟動。生成的資料會以原始 Parquet 檔案的形式儲存到 Unity Catalog 磁碟區，準備透過 Spark 宣告式管線（bronze/silver/gold 層）進行下游處理。

## 包含內容

```
synthetic-data-generation/
└── SKILL.md
```

## 關鍵主題

- 工作流程：在本地撰寫 Python 腳本，透過 MCP 工具在 Databricks 上執行，在失敗時迭代
- 用於更快執行的上下文重複使用模式（`cluster_id` 和 `context_id` 持久性）
- 儲存目的地：Unity Catalog 磁碟區，預設使用 `ai_dev_kit` 目錄
- 僅原始交易資料（無預先聚合欄位）以提供給下游 SDP 管線
- 參照完整性：先生成主資料表，然後使用有效外鍵生成子資料表
- 非線性分佈：價格使用對數常態分佈，持續時間使用指數分佈，加權分類
- 基於時間的模式：工作日/週末效應、假日日曆、季節性、事件高峰
- 列連貫性：相關屬性（層級影響優先順序，優先順序影響解決時間，解決影響 CSAT）
- 資料量指南：最少 10K-50K 列，以便模式在 GROUP BY 聚合後仍然存在
- 動態日期範圍：從目前日期起過去 6 個月
- 腳本結構，頂部有配置變數，底部有驗證
- Pandas 用於生成，Spark 用於儲存到磁碟區

## 何時使用

- 為 Databricks 建立測試或示範資料集
- 生成具有逼真分佈的合成資料
- 建立跨多個資料表保持參照完整性的資料
- 為獎章架構管線準備原始資料
- 需要具有可配置種子和數量的可重現資料集
- 使用可信資料原型設計儀表板或分析

## 相關技能

- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 用於在生成的資料之上建立 bronze/silver/gold 管線
- [AI/BI Dashboards](../aibi-dashboards/) -- 用於在儀表板中視覺化生成的資料
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 用於管理儲存資料的目錄、結構描述和磁碟區

## 資源

- [Unity Catalog 磁碟區](https://docs.databricks.com/en/connect/unity-catalog/volumes.html)
- [Faker 函式庫文件](https://faker.readthedocs.io/)
- [Databricks 執行上下文 API](https://docs.databricks.com/api/workspace/commandexecution)
