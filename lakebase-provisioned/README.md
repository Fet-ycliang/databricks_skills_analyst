# Lakebase Provisioned

使用 Lakebase Provisioned（Databricks 託管 PostgreSQL）處理 OLTP 工作負載的模式和最佳實踐。

## 概述

此技能涵蓋 Lakebase Provisioned，這是 Databricks 的託管 PostgreSQL 資料庫服務，專為線上交易處理（OLTP）工作負載而設計。當建立需要關聯式資料庫以保存持久狀態的應用程式、從 Delta Lake 實作反向 ETL，或將 PostgreSQL 與 Databricks Apps 和 LangChain 代理整合時，此技能會啟動。該技能提供從簡單腳本到具有自動 OAuth 權杖重新整理的生產級設定的連接模式。

## 包含內容

```
lakebase-provisioned/
├── SKILL.md                 # 主要技能：快速入門、常見模式、CLI 參考、疑難排解
├── connection-patterns.md   # 詳細連接方法（psycopg、SQLAlchemy、連接池、DNS 解決方法）
└── reverse-etl.md           # 從 Delta Lake 資料表同步資料到 Lakebase PostgreSQL
```

## 關鍵主題

- 建立和管理 Lakebase Provisioned 實例
- OAuth 權杖生成和自動重新整理（1 小時到期）
- 用於腳本和 notebook 的直接 psycopg3 連接
- 帶有連接池和權杖注入的 SQLAlchemy 非同步引擎
- macOS 的 DNS 解析解決方法
- 使用環境變數的 Databricks Apps 整合
- 用於治理的 Unity Catalog 註冊
- MLflow 模型資源宣告
- 反向 ETL：具有 FULL 和 INCREMENTAL 模式的同步資料表
- 透過 Databricks Jobs 排程同步
- 用於實例生命週期管理的 CLI 命令

## 何時使用

- 建立需要 PostgreSQL 資料庫處理交易工作負載的應用程式
- 為 Databricks Apps 新增持久狀態
- 從 Delta Lake 到營運資料庫實作反向 ETL
- 為 LangChain 應用程式儲存聊天或代理記憶
- 為生產應用程式設定帶有 OAuth 權杖重新整理的連接池

## 相關技能

- [Databricks Apps (APX)](../databricks-app-apx/) -- 可以使用 Lakebase 進行持久化的全端應用程式
- [Databricks Apps (Python)](../databricks-app-python/) -- 帶有 Lakebase 後端的 Python 應用程式
- [Databricks Python SDK](../databricks-python-sdk/) -- 用於實例管理和權杖生成的 SDK
- [Asset Bundles](../asset-bundles/) -- 部署帶有 Lakebase 資源的應用程式
- [Databricks Jobs](../databricks-jobs/) -- 排程反向 ETL 同步作業

## 資源

- [Lakebase 文件](https://docs.databricks.com/aws/en/database)
- [Databricks Python SDK - Database API](https://databricks-sdk-py.readthedocs.io/en/latest/)
- [psycopg 3 文件](https://www.psycopg.org/psycopg3/docs/)
- [SQLAlchemy 非同步引擎](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
