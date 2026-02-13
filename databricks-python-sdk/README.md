# Databricks Python SDK

Databricks 開發指南，包括 Python SDK、Databricks Connect、CLI 和 REST API。

## 概述

此技能提供使用 Databricks Python SDK（`databricks-sdk`）、Databricks Connect、Databricks CLI 和直接 REST API 存取的全面參考資料。當撰寫與 Databricks 服務互動的程式碼時，此技能會啟動，例如叢集、作業、SQL 倉儲、Unity Catalog、模型服務、向量搜尋等。該技能包含完整的 API 文件索引，包含方法簽章和常見操作的註解範例腳本。

## 包含內容

```
databricks-python-sdk/
├── SKILL.md                              # 主要技能：設定、驗證、核心 API 參考、模式
├── doc-index.md                          # 對應到文件 URL 的完整 SDK 方法簽章
└── examples/
    ├── 1-authentication.py               # 驗證模式和憑證設定
    ├── 2-clusters-and-jobs.py            # 叢集管理和作業編排
    ├── 3-sql-and-warehouses.py           # SQL 陳述式執行和倉儲管理
    ├── 4-unity-catalog.py                # 目錄、結構描述、資料表和磁碟區
    └── 5-serving-and-vector-search.py    # 模型服務端點和向量搜尋索引
```

## 關鍵主題

- 驗證（PAT、OAuth、Azure 服務主體、命名設定檔）
- 用於在本地執行 Spark 程式碼的 Databricks Connect
- WorkspaceClient 和 AccountClient 初始化
- 叢集 API（建立、啟動、停止、調整大小、權限）
- 作業 API（建立、執行、監控、修復）
- SQL 陳述式執行和倉儲管理
- Unity Catalog（目錄、結構描述、資料表、磁碟區、檔案）
- 模型服務端點和 OpenAI 相容客戶端
- 向量搜尋索引和查詢
- 管線（Delta Live Tables）管理
- 密鑰管理
- DBUtils 存取
- 透過 `api_client.do()` 進行直接 REST API 呼叫
- 非同步使用模式（FastAPI 的 `asyncio.to_thread`）
- 長時間執行操作的等待模式和分頁
- 使用類型化例外的錯誤處理

## 何時使用

- 撰寫使用 `databricks-sdk` 或 `databricks-connect` 的 Python 程式碼
- 以程式方式管理 Databricks 資源（叢集、作業、倉儲）
- 查詢 Unity Catalog 中繼資料或執行 SQL 陳述式
- 將 Databricks API 整合到應用程式中（FastAPI、腳本、notebook）
- 設定驗證或配置 Databricks CLI
- 查找 SDK 方法簽章或文件 URL

## 相關技能

- [Databricks Config](../databricks-config/) -- 設定檔和驗證設定
- [Asset Bundles](../asset-bundles/) -- 透過 DABs 部署資源
- [Databricks Jobs](../databricks-jobs/) -- 作業編排模式
- [Unity Catalog](../databricks-unity-catalog/) -- 目錄治理
- [Model Serving](../model-serving/) -- 服務端點管理
- [Vector Search](../vector-search/) -- 向量索引操作
- [Lakebase Provisioned](../lakebase-provisioned/) -- 透過 SDK 管理 PostgreSQL

## 資源

- [Databricks Python SDK 文件](https://databricks-sdk-py.readthedocs.io/en/latest/)
- [Databricks SDK GitHub 儲存庫](https://github.com/databricks/databricks-sdk-py)
- [驗證指南](https://databricks-sdk-py.readthedocs.io/en/latest/authentication.html)
- [DBUtils 文件](https://databricks-sdk-py.readthedocs.io/en/latest/dbutils.html)
