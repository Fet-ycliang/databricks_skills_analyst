---
name: lakebase-provisioned
description: "使用 Lakebase Provisioned（Databricks 託管 PostgreSQL）處理 OLTP 工作負載的模式和最佳實踐。"
---

# Lakebase Provisioned

使用 Lakebase Provisioned（Databricks 託管 PostgreSQL）處理 OLTP 工作負載的模式和最佳實踐。

## 何時使用

在以下情況使用此技能：
- 建立需要 PostgreSQL 資料庫處理交易工作負載的應用程式
- 為 Databricks Apps 新增持久狀態
- 實作從 Delta Lake 到營運資料庫的反向 ETL
- 為 LangChain 應用程式儲存聊天/代理記憶

## 概述

Lakebase Provisioned 是 Databricks 的託管 PostgreSQL 資料庫服務，用於 OLTP（線上交易處理）工作負載。它提供完全託管的 PostgreSQL 相容資料庫，與 Unity Catalog 整合，並支援基於 OAuth 權杖的驗證。

| 功能 | 說明 |
|---------|-------------|
| **託管 PostgreSQL** | 具有自動佈建的完全託管實例 |
| **OAuth 驗證** | 透過 Databricks SDK 進行基於權杖的驗證（1 小時到期） |
| **Unity Catalog** | 註冊資料庫以進行治理 |
| **反向 ETL** | 從 Delta 資料表同步資料到 PostgreSQL |
| **Apps 整合** | Databricks Apps 中的一流支援 |

**可用區域（AWS）：** us-east-1、us-east-2、us-west-2、eu-central-1、eu-west-1、ap-south-1、ap-southeast-1、ap-southeast-2

## 快速入門

建立並連接到 Lakebase Provisioned 實例：

```python
from databricks.sdk import WorkspaceClient
import uuid

# 初始化客戶端
w = WorkspaceClient()

# 建立資料庫實例
instance = w.database.create_database_instance(
    name="my-lakebase-instance",
    capacity="CU_1",  # CU_1、CU_2、CU_4、CU_8
    stopped=False
)
print(f"實例已建立：{instance.name}")
print(f"DNS 端點：{instance.read_write_dns}")
```

## 常見模式

### 生成 OAuth 權杖

```python
from databricks.sdk import WorkspaceClient
import uuid

w = WorkspaceClient()

# 為資料庫連接生成 OAuth 權杖
cred = w.database.generate_database_credential(
    request_id=str(uuid.uuid4()),
    instance_names=["my-lakebase-instance"]
)
token = cred.token  # 在連接字串中使用此作為密碼
```

### 從 Notebook 連接

```python
import psycopg
from databricks.sdk import WorkspaceClient
import uuid

# 取得實例詳細資訊
w = WorkspaceClient()
instance = w.database.get_database_instance(name="my-lakebase-instance")

# 生成權杖
cred = w.database.generate_database_credential(
    request_id=str(uuid.uuid4()),
    instance_names=["my-lakebase-instance"]
)

# 使用 psycopg3 連接
conn_string = f"host={instance.read_write_dns} dbname=postgres user={w.current_user.me().user_name} password={cred.token} sslmode=require"
with psycopg.connect(conn_string) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        print(cur.fetchone())
```

### 帶有權杖重新整理的 SQLAlchemy（生產環境）

對於長時間執行的應用程式，必須重新整理權杖（1 小時後到期）：

```python
import asyncio
import os
import uuid
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from databricks.sdk import WorkspaceClient

# 權杖重新整理狀態
_current_token = None
_token_refresh_task = None
TOKEN_REFRESH_INTERVAL = 50 * 60  # 50 分鐘（在 1 小時到期之前）

def _generate_token(instance_name: str) -> str:
    """生成新的 OAuth 權杖。"""
    w = WorkspaceClient()
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_name]
    )
    return cred.token

async def _token_refresh_loop(instance_name: str):
    """背景任務，每 50 分鐘重新整理權杖。"""
    global _current_token
    while True:
        await asyncio.sleep(TOKEN_REFRESH_INTERVAL)
        _current_token = await asyncio.to_thread(_generate_token, instance_name)

def init_database(instance_name: str, database_name: str, username: str) -> AsyncEngine:
    """使用 OAuth 權杖注入初始化資料庫。"""
    global _current_token
    
    w = WorkspaceClient()
    instance = w.database.get_database_instance(name=instance_name)
    
    # 生成初始權杖
    _current_token = _generate_token(instance_name)
    
    # 建立 URL（密碼透過 do_connect 注入）
    url = f"postgresql+psycopg://{username}@{instance.read_write_dns}:5432/{database_name}"
    
    engine = create_async_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
        connect_args={"sslmode": "require"}
    )
    
    # 在每個連接上注入權杖
    @event.listens_for(engine.sync_engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        cparams["password"] = _current_token
    
    return engine
```

### Databricks Apps 整合

對於 Databricks Apps，使用環境變數進行配置：

```python
# Databricks Apps 設定的環境變數：
# - LAKEBASE_INSTANCE_NAME：實例名稱
# - LAKEBASE_DATABASE_NAME：資料庫名稱
# - LAKEBASE_USERNAME：使用者名稱（選用，預設為服務主體）

import os

def is_lakebase_configured() -> bool:
    """檢查此應用程式是否已配置 Lakebase。"""
    return bool(
        os.environ.get("LAKEBASE_PG_URL") or
        (os.environ.get("LAKEBASE_INSTANCE_NAME") and 
         os.environ.get("LAKEBASE_DATABASE_NAME"))
    )
```

透過 CLI 將 Lakebase 新增為應用程式資源：

```bash
databricks apps add-resource $APP_NAME \
    --resource-type database \
    --resource-name lakebase \
    --database-instance my-lakebase-instance
```

### 註冊到 Unity Catalog

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 在 Unity Catalog 中註冊資料庫
w.database.register_database_instance(
    name="my-lakebase-instance",
    catalog="my_catalog",
    schema="my_schema"
)
```

### MLflow 模型資源

將 Lakebase 宣告為模型資源以自動提供憑證：

```python
from mlflow.models.resources import DatabricksLakebase

resources = [
    DatabricksLakebase(database_instance_name="my-lakebase-instance"),
]

# 記錄模型時
mlflow.langchain.log_model(
    model,
    artifact_path="model",
    resources=resources,
    pip_requirements=["databricks-langchain[memory]"]
)
```

## MCP 工具

以下 MCP 工具可用於管理 Lakebase Provisioned 基礎設施。

### 實例管理

| 工具 | 說明 |
|------|-------------|
| `create_lakebase_instance` | 建立託管 PostgreSQL 實例（CU_1、CU_2、CU_4、CU_8） |
| `get_lakebase_instance` | 取得實例詳細資訊（狀態、DNS、容量） |
| `list_lakebase_instances` | 列出工作區中的所有實例 |
| `update_lakebase_instance` | 調整大小或啟動/停止實例 |
| `delete_lakebase_instance` | 刪除實例 |
| `generate_lakebase_credential` | 為 PostgreSQL 連接生成 OAuth 權杖（1 小時到期） |

### Unity Catalog 註冊

| 工具 | 說明 |
|------|-------------|
| `create_lakebase_catalog` | 將 Lakebase 實例註冊為 Unity Catalog 目錄。參數：`name`、`instance_name`、`database_name`（預設："databricks_postgres"）、`create_database_if_not_exists`（預設：False）。目錄為唯讀。 |
| `get_lakebase_catalog` | 取得目錄註冊詳細資訊 |
| `delete_lakebase_catalog` | 移除目錄註冊（不會刪除實例） |

### 反向 ETL（同步資料表）

| 工具 | 說明 |
|------|-------------|
| `create_synced_table` | 從 Delta 建立同步資料表到 Lakebase。參數：`instance_name`、`source_table_name`、`target_table_name`、`primary_key_columns`（選用）、`scheduling_policy`（"TRIGGERED"/"SNAPSHOT"/"CONTINUOUS"，預設："TRIGGERED"） |
| `get_synced_table` | 取得同步資料表狀態 |
| `delete_synced_table` | 刪除同步資料表 |

## 參考文件

- [connection-patterns.md](connection-patterns.md) - 不同使用案例的詳細連接模式
- [reverse-etl.md](reverse-etl.md) - 從 Delta Lake 同步資料到 Lakebase

## CLI 快速參考

```bash
# 建立實例
databricks database create-database-instance \
    --name my-lakebase-instance \
    --capacity CU_1

# 取得實例詳細資訊
databricks database get-database-instance --name my-lakebase-instance

# 生成憑證
databricks database generate-database-credential \
    --request-id $(uuidgen) \
    --json '{"instance_names": ["my-lakebase-instance"]}'

# 列出實例
databricks database list-database-instances

# 停止實例（節省成本）
databricks database stop-database-instance --name my-lakebase-instance

# 啟動實例
databricks database start-database-instance --name my-lakebase-instance
```

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **長查詢期間權杖過期** | 實作權杖重新整理迴圈（請參閱「帶有權杖重新整理的 SQLAlchemy」章節）；權杖在 1 小時後到期 |
| **macOS 上 DNS 解析失敗** | 使用 `dig` 命令解析主機名稱，將 `hostaddr` 傳遞給 psycopg |
| **連接被拒** | 確保實例未停止；檢查 `instance.state` |
| **權限被拒** | 必須授予使用者對 Lakebase 實例的存取權限 |
| **需要 SSL 錯誤** | 在連接字串中始終使用 `sslmode=require` |

## SDK 版本需求

- **Databricks SDK for Python**：>= 0.61.0（建議 0.81.0+ 以獲得完整 API 支援）
- **psycopg**：3.x（支援 DNS 解決方法的 `hostaddr` 參數）
- **SQLAlchemy**：2.x 搭配 `postgresql+psycopg` 驅動程式

```python
%pip install -U "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0" sqlalchemy
```

## 注意事項

- **容量值**使用運算單位大小：`CU_1`、`CU_2`、`CU_4`、`CU_8`。
- **Lakebase Autoscaling** 是具有自動擴展功能的較新產品，但區域可用性有限。此技能專注於**Lakebase Provisioned**，其可用性更廣泛。
- 對於 LangChain 代理中的記憶/狀態，使用包含 Lakebase 支援的 `databricks-langchain[memory]`。
- 權杖是短期的（1 小時）- 生產應用程式必須實作權杖重新整理。
