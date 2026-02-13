# Asset Bundles

使用最佳實踐建立和配置 Databricks Asset Bundles (DABs)，用於多環境部署。

## 概述

此技能提供建立、配置和部署 Databricks Asset Bundles 的全面指南。當您設定新的 DAB 專案、新增儀表板、管線、作業或警報等資源，或配置多環境部署目標時，此技能會啟動。該技能確保在 dev、staging 和 production 環境中正確的路徑解析、權限設定和變數參數化。

## 包含內容

```
asset-bundles/
├── SKILL.md              # 主要技能：bundle 結構、資源類型、命令和疑難排解
├── SDP_guidance.md       # 用於 DABs 的 Spark 宣告式管線配置模式
└── alerts_guidance.md    # SQL 警報 v2 API 結構描述和配置（重要的 API 差異）
```

## 關鍵主題

- Bundle 專案結構（`databricks.yml`、`resources/*.yml`、`src/`）
- 多環境目標配置（dev/staging/prod）
- 目錄、結構描述和倉儲的變數參數化
- 帶有 `dataset_catalog` 和 `dataset_schema` 參數的儀表板資源
- 管線資源配置（無伺服器、串流、批次）
- SQL 警報 v2 API 結構描述（評估、排程、通知）
- 帶有排程和權限的作業資源
- 帶有授權的磁碟區資源
- 應用程式資源和 `app.yaml` 配置
- 路徑解析規則（`../src/` vs `./src/`）
- Bundle 驗證、部署和監控命令

## 何時使用

- 從頭開始建立新的 Databricks Asset Bundle 專案
- 將儀表板、管線、作業、警報、磁碟區或應用程式資源新增到 bundle
- 使用變數替換配置多環境部署
- 為 bundle 資源設定權限
- 透過 Databricks CLI 部署或執行 bundle 資源
- 除錯路徑解析、權限或結構描述驗證錯誤

## 相關技能

- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- DABs 引用的管線定義
- [Databricks Apps (APX)](../databricks-app-apx/) -- 透過 DABs 部署應用程式
- [Databricks Apps (Python)](../databricks-app-python/) -- 透過 DABs 部署 Python 應用程式
- [Databricks Config](../databricks-config/) -- CLI/SDK 的設定檔和驗證設定
- [Databricks Jobs](../databricks-jobs/) -- 透過 bundles 管理的作業編排

## 資源

- [Databricks Asset Bundles 文件](https://docs.databricks.com/dev-tools/bundles/)
- [Bundle 資源參考](https://docs.databricks.com/dev-tools/bundles/resources)
- [Bundle 配置參考](https://docs.databricks.com/dev-tools/bundles/settings)
- [支援的資源類型](https://docs.databricks.com/aws/en/dev-tools/bundles/resources#resource-types)
- [DAB 範例儲存庫](https://github.com/databricks/bundle-examples)
