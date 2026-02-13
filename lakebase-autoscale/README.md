# Lakebase Autoscaling

使用 Lakebase Autoscaling (下一代託管 PostgreSQL) 的模式和最佳實踐，包含自動擴展、分支、縮減至零和即時還原。

## 概述

此技能涵蓋 Lakebase Autoscaling，這是 Databricks 的下一代託管 PostgreSQL 資料庫服務，具有自動擴展計算、類似 Git 的分支、縮減至零和即時時間點還原功能。當建構需要具有動態擴展的操作資料庫的應用程式、為開發/測試工作流程使用資料庫分支、實作從 Delta Lake 的反向 ETL，或透過 SDK、CLI 或 MCP 工具管理 Lakebase Autoscaling 專案、分支和計算時，此技能會啟動。

## 包含內容

```
lakebase-autoscale/
├── SKILL.md                 # 主要技能：快速開始、常見模式、CLI 參考、疑難排解
├── projects.md              # 專案管理模式和設定
├── branches.md              # 分支工作流程、保護和到期
├── computes.md              # 計算調整、自動擴展和縮減至零
├── connection-patterns.md   # 連線方法 (psycopg, SQLAlchemy, pooling, DNS workaround)
└── reverse-etl.md           # 將資料從 Delta Lake tables 同步到 Lakebase PostgreSQL
```

## 關鍵主題

- 建立和管理 Lakebase Autoscaling 專案 (頂層容器)
- 分支管理：建立、保護、到期、從父分支重設
- 從 0.5 到 112 CU 的計算調整，具有自動擴展範圍
- 用於成本優化的縮減至零配置
- OAuth 權杖產生和自動重新整理 (1 小時到期)
- 用於腳本和筆記本的直接 psycopg3 連線
- 具有連線池和權杖注入的 SQLAlchemy 非同步引擎
- 適用於 macOS 的 DNS 解析解決方案
- 反向 ETL：具有 Snapshot、Triggered 和 Continuous 模式的同步資料表
- 用於專案/分支/計算生命週期管理的 CLI 命令
- 與 Lakebase Provisioned 的主要差異

## 何時使用

- 建構需要具有自動擴展計算能力的 PostgreSQL 資料庫的應用程式
- 為開發/測試/預備工作流程使用資料庫分支
- 為應用程式新增持久狀態，並透過縮減至零節省成本
- 透過同步資料表 (synced tables) 實作從 Delta Lake 到操作資料庫的反向 ETL
- 管理 Lakebase Autoscaling 專案、分支、計算或認證

## 相關技能

- [Lakebase Provisioned](../lakebase-provisioned/) -- 固定容量託管 PostgreSQL (前身)
- [Databricks Apps (APX)](../databricks-app-apx/) -- 可以使用 Lakebase 進行持久化的全端應用程式
- [Databricks Apps (Python)](../databricks-app-python/) -- 具有 Lakebase 後端的 Python 應用程式
- [Databricks Python SDK](../databricks-python-sdk/) -- 用於專案管理和權杖產生的 SDK
- [Asset Bundles](../asset-bundles/) -- 部署具有 Lakebase 資源的應用程式
- [Databricks Jobs](../databricks-jobs/) -- 排程反向 ETL 同步作業

## 資源

- [Lakebase Autoscaling Documentation](https://docs.databricks.com/aws/en/oltp/projects/)
- [Lakebase Autoscaling API Guide](https://docs.databricks.com/aws/en/oltp/projects/api-usage)
- [Databricks Python SDK - Postgres API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/postgres/postgres.html)
- [psycopg 3 Documentation](https://www.psycopg.org/psycopg3/docs/)
- [SQLAlchemy Async Engine](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
