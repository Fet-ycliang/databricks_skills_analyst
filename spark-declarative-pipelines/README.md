# Spark Declarative Pipelines

使用 Serverless Compute 建立、設定與更新 Databricks Lakeflow Spark Declarative Pipelines (SDP/LDP)。

## 概述

此技能涵蓋 Spark Declarative Pipelines (前身為 Delta Live Tables) 的端對端生命週期，包括串流資料表 (Streaming Tables)、物化視圖 (Materialized Views)、CDC、SCD Type 2 以及 Auto Loader 攝取模式。當使用者建置資料管線、使用 Delta Live Tables、攝取串流資料、實作變更資料擷取，或提及 SDP、LDP、DLT、Lakeflow、Streaming Tables 或 Bronze/Silver/Gold 獎章架構時，此技能便會啟動。此技能支援 Asset Bundle 初始化 (`databricks pipelines init`) 與使用 SQL 或現代化 `pyspark.pipelines` Python API 的手動 MCP 驅動工作流程。

## 包含內容

```
spark-declarative-pipelines/
├── SKILL.md
├── 1-ingestion-patterns.md
├── 2-streaming-patterns.md
├── 3-scd-patterns.md
├── 4-performance-tuning.md
├── 5-python-api.md
├── 6-dlt-migration.md
├── 7-advanced-configuration.md
└── 8-project-initialization.md
```

## 關鍵主題

- 使用 `read_files()` 的 Auto Loader 攝取，支援來自雲端儲存的 JSON, CSV, Parquet 與 Avro
- 串流來源：Kafka, Event Hub, Kinesis
- 去重、視窗聚合與有狀態串流操作
- 搭配 AUTO CDC 與 SCD Type 1/Type 2 模式的變更資料擷取 (CDC)
- 使用 `__START_AT` / `__END_AT` 時間欄位查詢 SCD Type 2 歷史資料表
- Liquid Clustering (`CLUSTER BY`) 取代舊版 `PARTITION BY` 與 `Z-ORDER`
- 現代化 Python API (`pyspark.pipelines` as `dp`) vs. 舊版 DLT API (`import dlt`)
- DLT 到 SDP 的遷移決策矩陣與逐步指南
- 透過 `extra_settings` 進行進階設定 (開發模式、持續管線、Photon、Python 相依性)
- 使用 `databricks pipelines init` 與 Asset Bundles 初始化專案
- 扁平或子目錄佈局的獎章架構 (Bronze/Silver/Gold)
- Serverless Compute 需求、限制以及何時退回 Classic Clusters

## 何時使用

- 在 Databricks 上建立新的資料管線
- 使用 Auto Loader 從雲端儲存攝取檔案
- 建置串流資料表或物化視圖
- 實作變更資料擷取 (CDC) 或緩慢變更維度 (SCD Type 2)
- 將現有 Delta Live Tables (DLT) 管線遷移至現代化 SDP 框架
- 設定獎章架構 (Bronze/Silver/Gold 層)
- 使用 Liquid Clustering 設定管線效能
- 使用 Asset Bundles 初始化新管線專案
- 偵錯管線錯誤 (空資料表、串流讀取失敗、找不到欄位)

## 相關技能

- [Databricks Jobs](../databricks-jobs/) -- 用於編排與排程管線執行
- [Asset Bundles](../asset-bundles/) -- 用於管線專案的多環境部署
- [Synthetic Data Generation](../synthetic-data-generation/) -- 用於產生測試資料以餵入管線
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 用於 Catalog/Schema/Volume 管理與治理

## 資源

- [Lakeflow Spark Declarative Pipelines 概述](https://docs.databricks.com/aws/en/ldp/)
- [SQL 語言參考](https://docs.databricks.com/aws/en/ldp/developer/sql-dev)
- [Python 語言參考](https://docs.databricks.com/aws/en/ldp/developer/python-ref)
- [載入資料 (Auto Loader, Kafka, Kinesis)](https://docs.databricks.com/aws/en/ldp/load)
- [變更資料擷取 (CDC)](https://docs.databricks.com/aws/en/ldp/cdc)
- [開發管線](https://docs.databricks.com/aws/en/ldp/develop)
- [Liquid Clustering](https://docs.databricks.com/aws/en/delta/clustering)
- [read_files -- 用於串流資料表](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files#usage-in-streaming-tables)
