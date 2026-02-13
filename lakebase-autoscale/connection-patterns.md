# Lakebase Autoscaling 連線模式 (Connection Patterns)

## 概述

本文件涵蓋 Lakebase Autoscaling 的不同連線模式，從簡單的腳本到具有權杖重新整理的生產應用程式。

## 驗證方法

Lakebase Autoscaling 支援兩種驗證方法：

| 方法 | 權杖生命週期 | 最適合 |
|--------|---------------|----------|
| **OAuth 權杖** | 1 小時 (必須重新整理) | 互動式工作階段、工作區整合應用程式 |
| **原生 Postgres 密碼** | 無到期 | 長時間執行的程序、無權杖輪替的工具 |

**連線逾時 (兩種方法)：**
- **24 小時閒置逾時**：24 小時無活動的連線將被自動關閉
- **3 天最大連線壽命**：存活超過 3 天的連線可能會被關閉

設計您的應用程式以使用重試邏輯處理連線逾時。

## 連線方法

### 1. 直接 psycopg 連線 (簡單腳本)

對於一次性腳本或筆記本：

```python
import psycopg
from databricks.sdk import WorkspaceClient

def get_connection(project_id: str, branch_id: str = "production",
                   endpoint_id: str = None, database_name: str = "databricks_postgres"):
    """取得具有新鮮 OAuth 權杖的資料庫連線。"""
    w = WorkspaceClient()

    # 取得端點詳細資訊以尋找主機
    if endpoint_id:
        ep_name = f"projects/{project_id}/branches/{branch_id}/endpoints/{endpoint_id}"
    else:
        # 列出端點並選擇主要 R/W 端點
        endpoints = list(w.postgres.list_endpoints(
            parent=f"projects/{project_id}/branches/{branch_id}"
        ))
        ep_name = endpoints[0].name

    endpoint = w.postgres.get_endpoint(name=ep_name)
    host = endpoint.status.hosts.host

    # 產生 OAuth 權杖 (有效 1 小時)
    cred = w.postgres.generate_database_credential(endpoint=ep_name)

    # 建構連線字串
    conn_string = (
        f"host={host} "
        f"dbname={database_name} "
        f"user={w.current_user.me().user_name} "
        f"password={cred.token} "
        f"sslmode=require"
    )

    return psycopg.connect(conn_string)

# 用法
with get_connection("my-app") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT NOW()")
        print(cur.fetchone())
```

### 2. 具有權杖重新整理的連線池 (生產)

對於需要連線池的長時間執行應用程式：

```python
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from databricks.sdk import WorkspaceClient


class LakebaseAutoscaleConnectionManager:
    """管理具有自動權杖重新整理的 Lakebase Autoscaling 連線。"""

    def __init__(
        self,
        project_id: str,
        branch_id: str = "production",
        database_name: str = "databricks_postgres",
        pool_size: int = 5,
        max_overflow: int = 10,
        token_refresh_seconds: int = 3000  # 50 分鐘
    ):
        self.project_id = project_id
        self.branch_id = branch_id
        self.database_name = database_name
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.token_refresh_seconds = token_refresh_seconds

        self._current_token: Optional[str] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._engine = None
        self._session_maker = None

    def _generate_token(self) -> str:
        """產生新鮮的 OAuth 權杖。"""
        w = WorkspaceClient()
        # 取得主要端點名稱以進行權杖範圍設定
        endpoints = list(w.postgres.list_endpoints(
            parent=f"projects/{self.project_id}/branches/{self.branch_id}"
        ))
        endpoint_name = endpoints[0].name if endpoints else None
        cred = w.postgres.generate_database_credential(endpoint=endpoint_name)
        return cred.token

    def _get_host(self) -> str:
        """從主要端點取得連線主機。"""
        w = WorkspaceClient()
        endpoints = list(w.postgres.list_endpoints(
            parent=f"projects/{self.project_id}/branches/{self.branch_id}"
        ))
        if not endpoints:
            raise RuntimeError(
                f"No endpoints found for projects/{self.project_id}/branches/{self.branch_id}"
            )
        endpoint = w.postgres.get_endpoint(name=endpoints[0].name)
        return endpoint.status.hosts.host

    async def _refresh_loop(self):
        """定期重新整理權杖的背景任務。"""
        while True:
            await asyncio.sleep(self.token_refresh_seconds)
            try:
                self._current_token = await asyncio.to_thread(self._generate_token)
            except Exception as e:
                print(f"Token refresh failed: {e}")

    def initialize(self):
        """初始化資料庫引擎並開始權杖重新整理。"""
        w = WorkspaceClient()

        # 取得主機資訊
        host = self._get_host()
        username = w.current_user.me().user_name

        # 產生初始權杖
        self._current_token = self._generate_token()

        # 建立引擎 (密碼透過事件注入)
        url = (
            f"postgresql+psycopg://{username}@"
            f"{host}:5432/{self.database_name}"
        )

        self._engine = create_async_engine(
            url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=3600,
            connect_args={"sslmode": "require"}
        )

        # 在連線時注入權杖
        @event.listens_for(self._engine.sync_engine, "do_connect")
        def inject_token(dialect, conn_rec, cargs, cparams):
            cparams["password"] = self._current_token

        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    def start_refresh(self):
        """開始背景權杖重新整理任務。"""
        if not self._refresh_task:
            self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def stop_refresh(self):
        """停止權杖重新整理任務。"""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """取得資料庫 Session。"""
        async with self._session_maker() as session:
            yield session

    async def close(self):
        """關閉所有連線。"""
        await self.stop_refresh()
        if self._engine:
            await self._engine.dispose()


# 在 FastAPI 中的用法
from fastapi import FastAPI

app = FastAPI()
db_manager = LakebaseAutoscaleConnectionManager("my-app", "production", "my_database")

@app.on_event("startup")
async def startup():
    db_manager.initialize()
    db_manager.start_refresh()

@app.on_event("shutdown")
async def shutdown():
    await db_manager.close()

@app.get("/data")
async def get_data():
    async with db_manager.session() as session:
        result = await session.execute("SELECT * FROM my_table")
        return result.fetchall()
```

### 3. 靜態 URL 模式 (本地開發)

對於本地開發，使用靜態連線 URL：

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine

# 設定環境變數為完整的連線 URL
# LAKEBASE_PG_URL=postgresql://user:password@host:5432/database

def get_database_url() -> str:
    """從環境取得資料庫 URL。"""
    url = os.environ.get("LAKEBASE_PG_URL")
    if url and url.startswith("postgresql://"):
        # 轉換為 psycopg3 async driver
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

engine = create_async_engine(
    get_database_url(),
    pool_size=5,
    connect_args={"sslmode": "require"}
)
```

### 4. DNS 解析解決方案 (macOS)

Python 的 `socket.getaddrinfo()` 在 macOS 上遇到長主機名稱會失敗。使用 `dig` 作為後備方案：

```python
import subprocess
import socket

def resolve_hostname(hostname: str) -> str:
    """使用 dig 命令解析主機名稱 (macOS 解決方案)。"""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        pass

    try:
        result = subprocess.run(
            ["dig", "+short", hostname],
            capture_output=True, text=True, timeout=5
        )
        ips = result.stdout.strip().split('\n')
        for ip in ips:
            if ip and not ip.startswith(';'):
                return ip
    except Exception:
        pass

    raise RuntimeError(f"Could not resolve hostname: {hostname}")

# 與 psycopg 一起使用
conn_params = {
    "host": hostname,       # For TLS SNI
    "hostaddr": resolve_hostname(hostname),  # Actual IP
    "dbname": database_name,
    "user": username,
    "password": token,
    "sslmode": "require"
}
conn = psycopg.connect(**conn_params)
```

## 最佳實踐

1. **始終使用 SSL**: 在所有連線中設定 `sslmode=require`
2. **實作權杖重新整理**: 權杖在 1 小時後過期；在 50 分鐘時重新整理
3. **使用連線池**: 避免每個請求建立新連線
4. **在 macOS 上處理 DNS 問題**: 如有需要，使用 `hostaddr` 解決方案
5. **正確關閉連線**: 使用上下文管理器或顯式清理
6. **處理縮減至零喚醒**: 閒置後的第一個連線可能需要 2-5 秒
7. **記錄權杖重新整理事件**: 有助於除錯驗證問題
