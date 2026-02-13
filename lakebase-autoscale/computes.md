# Lakebase Autoscaling 計算 (Computes)

## 概述

計算是為分支執行 Postgres 的虛擬化服務。每個分支有一個主要讀寫計算，並可以有選用的讀取副本。計算支援自動擴展、縮減至零 (scale-to-zero) 和從 0.5 到 112 CU 的細粒度調整。

## 計算大小調整

每個計算單元 (Compute Unit, CU) 分配大約 2 GB 的 RAM。

### 可用大小

| 類別 | 範圍 | 備註 |
|----------|-------|-------|
| **自動擴展計算** | 0.5-32 CU | 範圍內的動態擴展 (最大值-最小值 <= 8 CU) |
| **大型固定大小** | 36-112 CU | 固定大小，無自動擴展 |

### 代表性大小

| 計算單元 (Compute Units) | RAM | 最大連線數 |
|--------------|-----|-----------------|
| 0.5 CU | ~1 GB | 104 |
| 1 CU | ~2 GB | 209 |
| 4 CU | ~8 GB | 839 |
| 8 CU | ~16 GB | 1,678 |
| 16 CU | ~32 GB | 3,357 |
| 32 CU | ~64 GB | 4,000 |
| 64 CU | ~128 GB | 4,000 |
| 112 CU | ~224 GB | 4,000 |

**注意：** Lakebase Provisioned 每 CU 使用 ~16 GB。Lakebase Autoscaling 每 CU 使用 ~2 GB 以實現更細粒度的擴展。

## 建立計算

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Endpoint, EndpointSpec, EndpointType

w = WorkspaceClient()

# 建立讀寫計算端點
result = w.postgres.create_endpoint(
    parent="projects/my-app/branches/production",
    endpoint=Endpoint(
        spec=EndpointSpec(
            endpoint_type=EndpointType.ENDPOINT_TYPE_READ_WRITE,
            autoscaling_limit_min_cu=0.5,
            autoscaling_limit_max_cu=4.0
        )
    ),
    endpoint_id="my-compute"
).wait()

print(f"Endpoint created: {result.name}")
print(f"Host: {result.status.hosts.host}")
```

### CLI

```bash
databricks postgres create-endpoint \
    projects/my-app/branches/production my-compute \
    --json '{
        "spec": {
            "endpoint_type": "ENDPOINT_TYPE_READ_WRITE",
            "autoscaling_limit_min_cu": 0.5,
            "autoscaling_limit_max_cu": 4.0
        }
    }'
```

**重要：** 每個分支只能有一個讀寫計算。

## 取得計算詳細資訊

```python
endpoint = w.postgres.get_endpoint(
    name="projects/my-app/branches/production/endpoints/my-compute"
)

print(f"Endpoint: {endpoint.name}")
print(f"Type: {endpoint.status.endpoint_type}")
print(f"State: {endpoint.status.current_state}")
print(f"Host: {endpoint.status.hosts.host}")
print(f"Min CU: {endpoint.status.autoscaling_limit_min_cu}")
print(f"Max CU: {endpoint.status.autoscaling_limit_max_cu}")
```

## 列出計算

```python
endpoints = list(w.postgres.list_endpoints(
    parent="projects/my-app/branches/production"
))

for ep in endpoints:
    print(f"Endpoint: {ep.name}")
    print(f"  Type: {ep.status.endpoint_type}")
    print(f"  CU Range: {ep.status.autoscaling_limit_min_cu}-{ep.status.autoscaling_limit_max_cu}")
```

## 調整計算大小

使用 `update_mask` 指定要更新的欄位：

```python
from databricks.sdk.service.postgres import Endpoint, EndpointSpec, FieldMask

# 更新最小和最大 CU
w.postgres.update_endpoint(
    name="projects/my-app/branches/production/endpoints/my-compute",
    endpoint=Endpoint(
        name="projects/my-app/branches/production/endpoints/my-compute",
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

### CLI

```bash
# 更新單個欄位
databricks postgres update-endpoint \
    projects/my-app/branches/production/endpoints/my-compute \
    spec.autoscaling_limit_max_cu \
    --json '{"spec": {"autoscaling_limit_max_cu": 8.0}}'

# 更新多個欄位
databricks postgres update-endpoint \
    projects/my-app/branches/production/endpoints/my-compute \
    "spec.autoscaling_limit_min_cu,spec.autoscaling_limit_max_cu" \
    --json '{"spec": {"autoscaling_limit_min_cu": 2.0, "autoscaling_limit_max_cu": 8.0}}'
```

## 刪除計算

```python
w.postgres.delete_endpoint(
    name="projects/my-app/branches/production/endpoints/my-compute"
).wait()
```

## 自動擴展 (Autoscaling)

自動擴展根據工作負載需求動態調整計算資源。

### 配置

- **範圍:** 0.5-32 CU
- **限制:** 最大值 - 最小值不能超過 8 CU
- **有效範例:** 4-8 CU, 8-16 CU, 16-24 CU
- **無效範例:** 0.5-32 CU (範圍為 31.5 CU)

### 最佳實踐

- 設定足夠大的最小 CU 以將工作集緩存在記憶體中
- 在計算擴展並緩存資料之前，效能可能會降低
- 連線限制基於範圍內的最大 CU

## 縮減至零 (Scale-to-Zero)

在一段時間不活動後自動暫停計算。

| 設定 | 描述 |
|---------|-------------|
| **已啟用** | 計算在不活動逾時後暫停 (節省成本) |
| **已停用** | 始終活動的計算 (消除喚醒延遲) |

**預設行為：**
- `production` 分支：縮減至零 **已停用** (始終活動)
- 其他分支：可以配置縮減至零

**預設不活動逾時：** 5 分鐘
**最小不活動逾時：** 60 秒

### 喚醒行為

當連線到達暫停的計算時：
1. 計算自動啟動 (重新啟動需要幾百毫秒)
2. 一旦活動，連線請求將被透明地處理
3. 計算以最小自動擴展大小重新啟動 (如果啟用了自動擴展)
4. 應用程式應為短暫的重新啟動期間實作連線重試邏輯

### 重新啟動後的 Session 上下文

當計算暫停並重新啟動時，Session 上下文會被 **重設**：
- 記憶體中的統計資料和緩存內容被清除
- 臨時資料表和準備好的語句 (prepared statements) 遺失
- 特定於 Session 的配置設定重設
- 連線池和活動事務被終止

如果您的應用程式需要持久的 Session 資料，請考慮停用縮減至零。

## 大小調整指南

| 因素 | 建議 |
|--------|---------------|
| 查詢複雜度 | 複雜的分析查詢受益於較大的計算 |
| 並發連線 | 更多連線需要更多 CPU 和記憶體 |
| 資料量 | 較大的資料集可能需要更多記憶體以獲得效能 |
| 回應時間 | 關鍵應用程式可能需要較大的計算 |
