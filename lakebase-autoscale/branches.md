# Lakebase Autoscaling 分支 (Branches)

## 概述

Lakebase Autoscaling 中的分支是隔離的資料庫環境，透過寫入時複製 (copy-on-write) 與其父分支共用儲存。它們為資料庫啟用了類似 Git 的工作流程：建立隔離的開發/測試環境、安全地測試架構變更，以及從錯誤中復原。

## 分支類型

| 選項 | 描述 | 使用案例 |
|--------|-------------|----------|
| **Current data** | 從父分支的最新狀態分支 | 使用當前資料進行開發、測試 |
| **Past data** | 從特定時間點分支 | 時間點復原、歷史分析 |

## 建立分支

### 具有到期時間 (TTL)

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Branch, BranchSpec, Duration

w = WorkspaceClient()

# 建立具有 7 天到期時間的分支
result = w.postgres.create_branch(
    parent="projects/my-app",
    branch=Branch(
        spec=BranchSpec(
            source_branch="projects/my-app/branches/production",
            ttl=Duration(seconds=604800)  # 7 days
        )
    ),
    branch_id="development"
).wait()

print(f"Branch created: {result.name}")
print(f"Expires: {result.status.expire_time}")
```

### 永久分支 (無到期)

```python
result = w.postgres.create_branch(
    parent="projects/my-app",
    branch=Branch(
        spec=BranchSpec(
            source_branch="projects/my-app/branches/production",
            no_expiry=True
        )
    ),
    branch_id="staging"
).wait()
```

### CLI

```bash
# 具有 TTL
databricks postgres create-branch projects/my-app development \
    --json '{
        "spec": {
            "source_branch": "projects/my-app/branches/production",
            "ttl": "604800s"
        }
    }'

# 永久
databricks postgres create-branch projects/my-app staging \
    --json '{
        "spec": {
            "source_branch": "projects/my-app/branches/production",
            "no_expiry": true
        }
    }'
```

## 取得分支詳細資訊

```python
branch = w.postgres.get_branch(
    name="projects/my-app/branches/development"
)

print(f"Branch: {branch.name}")
print(f"Protected: {branch.status.is_protected}")
print(f"Default: {branch.status.default}")
print(f"State: {branch.status.current_state}")
print(f"Size: {branch.status.logical_size_bytes} bytes")
```

## 列出分支

```python
branches = list(w.postgres.list_branches(
    parent="projects/my-app"
))

for branch in branches:
    print(f"Branch: {branch.name}")
    print(f"  Default: {branch.status.default}")
    print(f"  Protected: {branch.status.is_protected}")
```

## 保護分支

受保護的分支無法被刪除、重設或封存。

```python
from databricks.sdk.service.postgres import Branch, BranchSpec, FieldMask

w.postgres.update_branch(
    name="projects/my-app/branches/production",
    branch=Branch(
        name="projects/my-app/branches/production",
        spec=BranchSpec(is_protected=True)
    ),
    update_mask=FieldMask(field_mask=["spec.is_protected"])
).wait()
```

移除保護：

```python
w.postgres.update_branch(
    name="projects/my-app/branches/production",
    branch=Branch(
        name="projects/my-app/branches/production",
        spec=BranchSpec(is_protected=False)
    ),
    update_mask=FieldMask(field_mask=["spec.is_protected"])
).wait()
```

## 更新分支到期時間

```python
# 延長至 14 天
w.postgres.update_branch(
    name="projects/my-app/branches/development",
    branch=Branch(
        name="projects/my-app/branches/development",
        spec=BranchSpec(
            is_protected=False,
            ttl=Duration(seconds=1209600)  # 14 days
        )
    ),
    update_mask=FieldMask(field_mask=["spec.is_protected", "spec.expiration"])
).wait()

# 移除到期
w.postgres.update_branch(
    name="projects/my-app/branches/development",
    branch=Branch(
        name="projects/my-app/branches/development",
        spec=BranchSpec(no_expiry=True)
    ),
    update_mask=FieldMask(field_mask=["spec.expiration"])
).wait()
```

## 從父分支重設分支

重設會用父分支的最新狀態完全取代分支的資料和架構。本地變更將會遺失。

```python
w.postgres.reset_branch(
    name="projects/my-app/branches/development"
).wait()
```

**限制：**
- 根分支 (如 `production`) 無法重設 (無父分支)
- 有子分支的分支無法重設 (先刪除子分支)
- 重設期間連線會暫時中斷

## 刪除分支

```python
w.postgres.delete_branch(
    name="projects/my-app/branches/development"
).wait()
```

**限制：**
- 無法刪除有子分支的分支 (先刪除子分支)
- 無法刪除受保護的分支 (先移除保護)
- 無法刪除預設分支

## 分支到期

分支到期設定自動刪除的時間戳記。適用於：
- **CI/CD 環境**: 2-4 小時
- **示範 (Demos)**: 24-48 小時
- **功能開發**: 1-7 天
- **長期測試**: 最多 30 天

**最大到期期間：** 從當前時間起 30 天。

### 到期限制

- 無法使受保護的分支到期
- 無法使預設分支到期
- 無法使有子分支的分支到期
- 當分支到期時，所有計算資源也會被刪除

## 最佳實踐

1. **對臨時分支使用 TTL**: 為開發/測試分支設定到期時間以避免堆積
2. **保護生產分支**: 防止意外刪除或重設
3. **重設而非重新建立**: 當需要新鮮資料而不需要新分支開銷時，從父分支重設
4. **合併前比較架構**: 在將變更套用到生產環境之前，比較分支之間的架構
5. **監控未封存限制**: 每個專案僅允許 10 個未封存的分支
