# Lakebase 連接模式

## 概述

本文件涵蓋 Lakebase Provisioned 的不同連接模式，從簡單腳本到具有權杖重新整理的生產應用程式。

## 連接方法

### 1. 直接 psycopg 連接（簡單腳本）

用於一次性腳本或 notebook：

```python
import psycopg
from databricks.sdk import WorkspaceClient
import uuid

def get_connection(instance_name: str, database_name: str = "postgres"):
    """使用新的 OAuth 權杖取得資料庫連接。"""
    w = WorkspaceClient()
    
    # 取得實例詳細資訊
    instance = w.database.get_database_instance(name=instance_name)
    
    # 生成 OAuth 權杖（有效期 1 小時）
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_name]
    )
    
    # 建立連接字串
    conn_string = (
        f"host={instance.read_write_dns} "
        f"dbname={database_name} "
        f"user={w.current_user.me().user_name} "
        f"password={cred.token} "
        f"sslmode=require"
    )
    
    return psycopg.connect(conn_string)

# 使用方式
with get_connection("my-instance") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT NOW()")
        print(cur.fetchone())
```

### 2. 帶有權杖重新整理的連接池（生產環境）

用於需要連接池的長時間執行應用程式：

```python
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from databricks.sdk import WorkspaceClient

class LakebaseConnectionManager:
    """管理帶有自動權杖重新整理的 Lakebase 連接。"""
    
    def __init__(
        self,
        instance_name: str,
        database_name: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        token_refresh_seconds: int = 3000  # 50 分鐘
    ):
        self.instance_name = instance_name
        self.database_name = database_name
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.token_refresh_seconds = token_refresh_seconds
        
        self._current_token: Optional[str] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._engine = None
        self._session_maker = None
    
    def _generate_token(self) -> str:
        """生成新的 OAuth 權杖。"""
        w = WorkspaceClient()
        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[self.instance_name]
        )
        return cred.token
    
    async def _refresh_loop(self):
        """背景任務，定期重新整理權杖。"""
        while True:
            await asyncio.sleep(self.token_refresh_seconds)
            try:
                self._current_token = await asyncio.to_thread(self._generate_token)
            except Exception as e:
                print(f"權杖重新整理失敗：{e}")
    
    def initialize(self):
        """初始化資料庫引擎並啟動權杖重新整理。"""
        w = WorkspaceClient()
        
        # 取得實例資訊
        instance = w.database.get_database_instance(name=self.instance_name)
        username = w.current_user.me().user_name
        
        # 生成初始權杖
        self._current_token = self._generate_token()
        
        # 建立引擎（密碼透過事件注入）
        url = (
            f"postgresql+psycopg://{username}@"
            f"{instance.read_write_dns}:5432/{self.database_name}"
        )
        
        self._engine = create_async_engine(
            url,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=3600,
            connect_args={"sslmode": "require"}
        )
        
        # 在連接時注入權杖
        @event.listens_for(self._engine.sync_engine, "do_connect")
        def inject_token(dialect, conn_rec, cargs, cparams):
            cparams["password"] = self._current_token
        
        self._session_maker = async_sessionmaker(
            self._engine, 
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    def start_refresh(self):
        """啟動背景權杖重新整理任務。"""
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
        """取得資料庫 session。"""
        async with self._session_maker() as session:
            yield session
    
    async def close(self):
        """關閉所有連接。"""
        await self.stop_refresh()
        if self._engine:
            await self._engine.dispose()

# FastAPI 中的使用方式
from fastapi import FastAPI

app = FastAPI()
db_manager = LakebaseConnectionManager("my-instance", "my_database")

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

### 3. 靜態 URL 模式（本地開發）

用於本地開發，使用靜態連接 URL：

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine

# 使用完整連接 URL 設定環境變數
# LAKEBASE_PG_URL=postgresql://user:password@host:5432/database

def get_database_url() -> str:
    """從環境取得資料庫 URL。"""
    url = os.environ.get("LAKEBASE_PG_URL")
    if url and url.startswith("postgresql://"):
        # 轉換為 psycopg3 非同步驅動程式
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

engine = create_async_engine(
    get_database_url(),
    pool_size=5,
    connect_args={"sslmode": "require"}
)
```

### 4. DNS 解析解決方法（macOS）

Python 的 `socket.getaddrinfo()` 在 macOS 上對長主機名稱會失敗。使用 `dig` 作為備用方案：

```python
import subprocess
import socket

def resolve_hostname(hostname: str) -> str:
    """使用 dig 命令解析主機名稱（macOS 解決方法）。"""
    try:
        # 先嘗試 Python 的解析器
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        pass
    
    # 備用方案使用 dig 命令
    try:
        result = subprocess.run(
            ["dig", "+short", hostname],
            capture_output=True,
            text=True,
            timeout=5
        )
        ips = result.stdout.strip().split('\n')
        for ip in ips:
            if ip and not ip.startswith(';'):
                return ip
    except Exception:
        pass
    
    raise RuntimeError(f"無法解析主機名稱：{hostname}")

# 與 psycopg 一起使用
conn_params = {
    "host": hostname,  # 用於 TLS SNI
    "hostaddr": resolve_hostname(hostname),  # 實際 IP
    "dbname": database_name,
    "user": username,
    "password": token,
    "sslmode": "require"
}
conn = psycopg.connect(**conn_params)
```

## 環境變數

| 變數 | 說明 | 必要 |
|----------|-------------|----------|
| `LAKEBASE_PG_URL` | 靜態 PostgreSQL URL（本地開發） | 此項或 instance/database |
| `LAKEBASE_INSTANCE_NAME` | Lakebase 實例名稱 | 與 DATABASE_NAME 一起 |
| `LAKEBASE_DATABASE_NAME` | 資料庫名稱 | 與 INSTANCE_NAME 一起 |
| `LAKEBASE_USERNAME` | 覆寫使用者名稱 | 否 |
| `LAKEBASE_HOST` | 覆寫主機 | 否 |
| `DB_POOL_SIZE` | 連接池大小 | 否（預設：5） |
| `DB_MAX_OVERFLOW` | 最大池溢出 | 否（預設：10） |
| `DB_POOL_RECYCLE_INTERVAL` | 池回收秒數 | 否（預設：3600） |

## 最佳實踐

1. **始終使用 SSL**：在所有連接中設定 `sslmode=require`
2. **實作權杖重新整理**：權杖在 1 小時後到期；在 50 分鐘時重新整理
3. **使用連接池**：避免為每個請求建立新連接
4. **處理 macOS 上的 DNS 問題**：如果需要，使用 `hostaddr` 解決方法
5. **正確關閉連接**：使用上下文管理器或明確清理
6. **記錄權杖重新整理事件**：有助於除錯驗證問題
