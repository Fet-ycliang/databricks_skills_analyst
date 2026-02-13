# Lakebase Autoscaling 專案 (Projects)

## 概述

專案是 Lakebase Autoscaling 資源的頂層容器，包含分支、計算、資料庫和角色。每個專案都是隔離的，包含自己的 Postgres 版本、計算預設值和還原視窗設定。

## 專案結構

```
Project
  └── Branches (production, development, staging, etc.)
        ├── Computes (R/W compute, read replicas)
        ├── Roles (Postgres roles)
        └── Databases (Postgres databases)
```

當專案建立時，預設包含：
- 一個 `production` 分支 (預設分支)
- 一個主要讀寫計算 (8-32 CU，已啟用自動擴展，已停用縮減至零)
- 一個 `databricks_postgres` 資料庫
- 一個用於建立者 Databricks 身分的 Postgres 角色

## 資源命名

專案遵循階層式命名慣例：
```
projects/{project_id}
```

**資源 ID 需求：**
- 1-63 個字元長
- 僅限小寫字母、數字和連字號
- 不能以連字號開頭或結尾
- 建立後無法更改

## 建立專案

### Python SDK

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

# 等待完成
result = operation.wait()
print(f"Created project: {result.name}")
print(f"Display name: {result.status.display_name}")
print(f"Postgres version: {result.status.pg_version}")
```

### CLI

```bash
databricks postgres create-project \
    --project-id my-app \
    --json '{
        "spec": {
            "display_name": "My Application",
            "pg_version": "17"
        }
    }'
```

## 取得專案詳細資訊

### Python SDK

```python
project = w.postgres.get_project(name="projects/my-app")

print(f"Project: {project.name}")
print(f"Display name: {project.status.display_name}")
print(f"Postgres version: {project.status.pg_version}")
```

### CLI

```bash
databricks postgres get-project projects/my-app
```

**注意：** GET 操作不會填入 `spec` 欄位。所有屬性都在 `status` 欄位中返回。

## 列出專案

```python
projects = w.postgres.list_projects()

for project in projects:
    print(f"Project: {project.name}")
    print(f"  Display name: {project.status.display_name}")
    print(f"  Postgres version: {project.status.pg_version}")
```

## 更新專案

更新需要 `update_mask` 指定要修改的欄位：

```python
from databricks.sdk.service.postgres import Project, ProjectSpec, FieldMask

# 更新顯示名稱
operation = w.postgres.update_project(
    name="projects/my-app",
    project=Project(
        name="projects/my-app",
        spec=ProjectSpec(
            display_name="My Updated Application"
        )
    ),
    update_mask=FieldMask(field_mask=["spec.display_name"])
)
result = operation.wait()
```

### CLI

```bash
databricks postgres update-project projects/my-app spec.display_name \
    --json '{
        "spec": {
            "display_name": "My Updated Application"
        }
    }'
```

## 刪除專案

**警告：** 刪除專案是永久性的，且會刪除所有分支、計算、資料庫、角色和資料。

在刪除專案之前，請刪除所有 Unity Catalog 目錄和同步資料表。

```python
operation = w.postgres.delete_project(name="projects/my-app")
# 這是一個長時間執行的操作
```

### CLI

```bash
databricks postgres delete-project projects/my-app
```

## 專案設定

### 計算預設值

新主要計算的預設設定：
- 計算大小範圍 (0.5-112 CU)
- 縮減至零逾時 (預設：5 分鐘)

### 即時還原

配置還原視窗長度 (2-35 天)。較長的視窗會增加儲存成本。

### Postgres 版本

支援 Postgres 16 和 Postgres 17。

## 專案限制

| 資源 | 限制 |
|----------|-------|
| 並發活動計算 | 20 |
| 每個專案的分支 | 500 |
| 每個分支的 Postgres 角色 | 500 |
| 每個分支的 Postgres 資料庫 | 500 |
| 每個分支的邏輯資料大小 | 8 TB |
| 每個工作區的專案 | 1000 |
| 受保護的分支 | 1 |
| 根分支 | 3 |
| 未封存的分支 | 10 |
| 快照 | 10 |
| 最大歷史保留 | 35 天 |
| 最小縮減至零時間 | 60 秒 |

## 長時間執行操作 (Long-Running Operations)

所有建立、更新和刪除操作都會返回一個長時間執行操作 (LRO)。在 SDK 中使用 `.wait()` 以阻擋直到完成：

```python
# 開始操作
operation = w.postgres.create_project(...)

# 等待完成
result = operation.wait()

# 或手動檢查狀態
op_status = w.postgres.get_operation(name=operation.name)
print(f"Done: {op_status.done}")
```
