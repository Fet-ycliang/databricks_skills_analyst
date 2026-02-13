---
name: lakebase-autoscale
description: "使用 Lakebase Autoscaling (下一代託管 PostgreSQL) 的模式和最佳實踐，包含自動擴展、分支、縮減至零和即時還原。"
---

# Lakebase Autoscaling

使用 Lakebase Autoscaling 的模式和最佳實踐，這是 Databricks 上的下一代託管 PostgreSQL，具有自動擴展計算、分支、縮減至零 (scale-to-zero) 和即時還原功能。

## 何時使用

當您需要以下功能時，請使用此技能：
- 建構需要具有自動擴展計算能力的 PostgreSQL 資料庫的應用程式
- 為開發/測試/預備工作流程使用資料庫分支
- 為應用程式新增持久狀態，並透過縮減至零節省成本
- 透過同步資料表 (synced tables) 實作從 Delta Lake 到操作資料庫的反向 ETL
- 管理 Lakebase Autoscaling 專案、分支、計算或認證

## 概述

Lakebase Autoscaling 是 Databricks 用於 OLTP 工作負載的下一代託管 PostgreSQL 服務。它提供自動擴展計算、類似 Git 的分支、縮減至零和即時時間點還原。

| 功能 | 描述 |
|---------|-------------|
| **自動擴展計算** | 每 CU 0.5-112 CU，配備 2 GB RAM；根據負載動態擴展 |
| **縮減至零** | 在配置閒置逾時後暫停計算 |
| **分支** | 為開發/測試建立隔離的資料庫環境 (類似 Git 分支) |
| **即時還原** | 從配置視窗內的任何時刻即時還原 (最多 35 天) |
| **OAuth 驗證** | 透過 Databricks SDK 進行基於權杖的驗證 (1 小時到期) |
| **反向 ETL** | 透過同步資料表將資料從 Delta tables 同步到 PostgreSQL |

**可用區域 (AWS):** us-east-1, us-east-2, eu-central-1, eu-west-1, eu-west-2, ap-south-1, ap-southeast-1, ap-southeast-2

**可用區域 (Azure Beta):** eastus2, westeurope, westus

## 專案階層

了解階層對於使用 Lakebase Autoscaling 至關重要：

```
Project (頂層容器)
  └── Branch(es) (隔離的資料庫環境)
        ├── Compute (主要讀/寫端點)
        ├── Read Replica(s) (選用，唯讀)
        ├── Role(s) (Postgres 角色)
        └── Database(s) (Postgres 資料庫)
              └── Schema(s)
```

| 物件 | 描述 |
|--------|-------------|
| **Project** | 頂層容器。透過 `w.postgres.create_project()` 建立。 |
| **Branch** | 具有寫入時複製 (copy-on-write) 儲存的隔離資料庫環境。預設分支為 `production`。 |
| **Compute** | 驅動分支的 Postgres 伺服器。可配置 CU 大小和自動擴展。 |
| **Database** | 分支內的標準 Postgres 資料庫。預設為 `databricks_postgres`。 |

## 快速開始

建立專案並連線：

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Project, ProjectSpec

w = WorkspaceClient()

# 建立專案 (長時間執行操作)
operation = w.postgres.create_project(
    project=Project(
        spec=ProjectSpec(
            display_name="My Application",
            pg_version="17"
        )
    ),
    project_id="my-app"
)
result = operation.wait()
print(f"Created project: {result.name}")
```

## 常見模式

### 產生 OAuth 權杖

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 產生用於連線的資料庫認證 (可選範圍至端點)
cred = w.postgres.generate_database_credential(
    endpoint="projects/my-app/branches/production/endpoints/ep-primary"
)
token = cred.token  # 在連線字串中作為密碼使用
# 權杖在 1 小時後過期
```

### 從筆記本連線

```python
import psycopg
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 取得端點詳細資訊
endpoint = w.postgres.get_endpoint(
    name="projects/my-app/branches/production/endpoints/ep-primary"
)
host = endpoint.status.hosts.host

# 產生權杖 (範圍至端點)
cred = w.postgres.generate_database_credential(
    endpoint="projects/my-app/branches/production/endpoints/ep-primary"
)

# 使用 psycopg3 連線
conn_string = (
    f"host={host} "
    f"dbname=databricks_postgres "
    f"user={w.current_user.me().user_name} "
    f"password={cred.token} "
    f"sslmode=require"
)
with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        print(cur.fetchone())
```

### 為開發建立分支

```python
from databricks.sdk.service.postgres import Branch, BranchSpec, Duration

# 建立具有 7 天到期時間的開發分支
branch = w.postgres.create_branch(
    parent="projects/my-app",
    branch=Branch(
        spec=BranchSpec(
            source_branch="projects/my-app/branches/production",
            ttl=Duration(seconds=604800)  # 7 days
        )
    ),
    branch_id="development"
).wait()
print(f"Branch created: {branch.name}")
```

### 調整計算大小 (自動擴展)

```python
from databricks.sdk.service.postgres import Endpoint, EndpointSpec, FieldMask

# 更新計算以在 2-8 CU 之間自動擴展
w.postgres.update_endpoint(
    name="projects/my-app/branches/production/endpoints/ep-primary",
    endpoint=Endpoint(
        name="projects/my-app/branches/production/endpoints/ep-primary",
        spec=EndpointSpec(
            autoscaling_limit_min_cu=2.0,
            autoscaling_limit_max_cu=8.0
        )
    ),
    update_mask=FieldMask(field_mask=[
        "spec.autoscaling_limit_min_cu",
        "spec.autoscaling_limit_max_cu"
    ])
).wait()
```

## MCP 工具

以下 MCP 工具可用於管理 Lakebase Autoscaling 基礎設施。

### 專案管理

| 工具 | 描述 |
|------|-------------|
| `create_lakebase_autoscale_project` | 使用 Postgres 版本和顯示名稱建立新專案 |
| `get_lakebase_autoscale_project` | 取得專案詳細資訊 (狀態、顯示名稱、pg_version) |
| `list_lakebase_autoscale_projects` | 列出工作區中的所有專案 |
| `update_lakebase_autoscale_project` | 更新專案顯示名稱 |
| `delete_lakebase_autoscale_project` | 刪除專案及其所有資源 |

### 分支管理

| 工具 | 描述 |
|------|-------------|
| `create_lakebase_autoscale_branch` | 從父分支建立分支 (可選 TTL) |
| `get_lakebase_autoscale_branch` | 取得分支詳細資訊 (狀態、保護、到期) |
| `list_lakebase_autoscale_branches` | 列出專案中的所有分支 |
| `update_lakebase_autoscale_branch` | 更新分支 (保護、設定到期) |
| `delete_lakebase_autoscale_branch` | 刪除分支及其資源 |

### 計算 (端點) 管理

| 工具 | 描述 |
|------|-------------|
| `create_lakebase_autoscale_endpoint` | 在分支上建立計算端點 |
| `get_lakebase_autoscale_endpoint` | 取得端點詳細資訊 (主機、CU 範圍、狀態) |
| `list_lakebase_autoscale_endpoints` | 列出分支上的所有端點 |
| `update_lakebase_autoscale_endpoint` | 調整計算大小或設定縮減至零 |
| `delete_lakebase_autoscale_endpoint` | 刪除計算端點 |

### 認證

| 工具 | 描述 |
|------|-------------|
| `generate_lakebase_autoscale_credential` | 產生用於 PostgreSQL 連線的 OAuth 權杖 (1 小時到期，可選範圍至端點) |

## 參考檔案

- [projects.md](projects.md) - 專案管理模式和設定
- [branches.md](branches.md) - 分支工作流程、保護和到期
- [computes.md](computes.md) - 計算調整、自動擴展和縮減至零
- [connection-patterns.md](connection-patterns.md) - 不同使用案例的連線模式
- [reverse-etl.md](reverse-etl.md) - 從 Delta Lake 到 Lakebase 的同步資料表

## CLI 快速參考

```bash
# 建立專案
databricks postgres create-project \
    --project-id my-app \
    --json '{"spec": {"display_name": "My App", "pg_version": "17"}}'

# 列出專案
databricks postgres list-projects

# 取得專案詳細資訊
databricks postgres get-project projects/my-app

# 建立分支
databricks postgres create-branch projects/my-app development \
    --json '{"spec": {"source_branch": "projects/my-app/branches/production", "no_expiry": true}}'

# 列出分支
databricks postgres list-branches projects/my-app

# 取得端點詳細資訊
databricks postgres get-endpoint projects/my-app/branches/production/endpoints/ep-primary

# 刪除專案
databricks postgres delete-project projects/my-app
```

## 與 Lakebase Provisioned 的主要差異

| 面向 | Provisioned | Autoscaling |
|--------|-------------|-------------|
| SDK 模組 | `w.database` | `w.postgres` |
| 頂層資源 | Instance | Project |
| 容量 | CU_1, CU_2, CU_4, CU_8 (16 GB/CU) | 0.5-112 CU (2 GB/CU) |
| 分支 | 不支援 | 完整分支支援 |
| 縮減至零 | 不支援 | 可配置逾時 |
| 操作 | 同步 | 長時間執行操作 (LRO) |
| 讀取副本 | 可讀次要節點 | 專用唯讀端點 |

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **長時間查詢期間權杖過期** | 實作權杖重新整理迴圈；權杖在 1 小時後過期 |
| **縮減至零後連線被拒絕** | 計算在連線時自動喚醒；重新啟動需要幾百毫秒；實作重試邏輯 |
| **macOS 上的 DNS 解析失敗** | 使用 `dig` 命令解析主機名稱，將 `hostaddr` 傳遞給 psycopg |
| **刪除分支被阻擋** | 先刪除子分支；無法刪除有子分支的分支 |
| **自動擴展範圍太寬** | Max - min 不能超過 8 CU (例如，8-16 CU 有效，0.5-32 CU 無效) |
| **SSL required 錯誤** | 在連線字串中始終使用 `sslmode=require` |
| **需要 Update mask** | 所有更新操作都需要指定要修改欄位的 `update_mask` |
| **閒置 24 小時後連線關閉** | 所有連線都有 24 小時閒置逾時和 3 天最大生命週期；實作重試邏輯 |

## 目前限制

Lakebase Autoscaling 尚未支援這些功能：
- 具有可讀次要節點的高可用性 (使用讀取副本代替)
- Databricks Apps UI 整合 (Apps 可以透過認證手動連線)
- Feature Store 整合
- 有狀態 AI 代理 (LangChain記憶體)
- Postgres 到 Delta 同步 (僅支援 Delta 到 Postgres 的反向 ETL)
- 自訂計費標籤和 Serverless 預算策略
- 從 Lakebase Provisioned 直接遷移 (使用 pg_dump/pg_restore 或反向 ETL)

## SDK 版本需求

- **Databricks SDK for Python**: >= 0.81.0 (用於 `w.postgres` 模組)
- **psycopg**: 3.x (支援 `hostaddr` 參數用於 DNS 解決方案)
- **SQLAlchemy**: 2.x 搭配 `postgresql+psycopg` 驅動程式

```python
%pip install -U "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0" sqlalchemy
```

## 備註

- Autoscaling 中的 **Compute Units** 提供 ~2 GB RAM (相較於 Provisioned 中的 16 GB)。
- **資源命名** 遵循階層路徑：`projects/{id}/branches/{id}/endpoints/{id}`。
- 所有建立/更新/刪除操作都是 **長時間執行** -- 在 SDK 中使用 `.wait()`。
- 權杖生命週期短 (1 小時) -- 生產應用程式 **必須** 實作權杖重新整理。
- 支援 **Postgres 版本** 16 和 17。
