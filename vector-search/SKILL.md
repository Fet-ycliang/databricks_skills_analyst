---
name: vector-search
description: "Databricks 向量搜尋模式：建立端點和索引、使用篩選器查詢、管理嵌入。用於建立 RAG 應用程式、語義搜尋或相似度匹配。涵蓋儲存優化和標準端點。"
---

# Databricks 向量搜尋

建立、管理和查詢向量搜尋索引的模式，用於 RAG 和語義搜尋應用程式。

## 何時使用

在以下情況使用此技能：
- 建立 RAG（檢索增強生成）應用程式
- 實作語義搜尋或相似度匹配
- 從 Delta 資料表建立向量索引
- 在儲存優化和標準端點之間選擇
- 使用篩選器查詢向量索引

## 概述

Databricks 向量搜尋提供託管的向量相似度搜尋，具有自動嵌入生成和 Delta Lake 整合功能。

| 元件 | 說明 |
|-----------|-------------|
| **端點** | 託管索引的運算資源（標準或儲存優化） |
| **索引** | 用於相似度搜尋的向量資料結構 |
| **Delta 同步** | 與來源 Delta 資料表自動同步 |
| **直接存取** | 對向量進行手動 CRUD 操作 |

## 端點類型

| 類型 | 延遲 | 容量 | 成本 | 最適合 |
|------|---------|----------|------|----------|
| **標準** | ~50-100ms | 3.2 億個向量（768 維） | 較高 | 即時、低延遲 |
| **儲存優化** | ~250ms | 10 億+個向量（768 維） | 低 7 倍 | 大規模、成本敏感 |

## 索引類型

| 類型 | 嵌入 | 同步 | 使用案例 |
|------|------------|------|----------|
| **Delta 同步（託管）** | Databricks 計算 | 從 Delta 自動同步 | 最簡單的設定 |
| **Delta 同步（自管理）** | 您提供 | 從 Delta 自動同步 | 自訂嵌入 |
| **直接存取** | 您提供 | 手動 CRUD | 即時更新 |

## 快速入門

### 建立端點

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# 建立標準端點
endpoint = w.vector_search_endpoints.create_endpoint(
    name="my-vs-endpoint",
    endpoint_type="STANDARD"  # 或 "STORAGE_OPTIMIZED"
)
# 注意：端點建立是非同步的；使用 get_endpoint() 檢查狀態
```

### 建立 Delta 同步索引（託管嵌入）

```python
# 來源資料表必須有：主鍵欄位 + 文字欄位
index = w.vector_search_indexes.create_index(
    name="catalog.schema.my_index",
    endpoint_name="my-vs-endpoint",
    primary_key="id",
    index_type="DELTA_SYNC",
    delta_sync_index_spec={
        "source_table": "catalog.schema.documents",
        "embedding_source_columns": [
            {
                "name": "content",  # 要嵌入的文字欄位
                "embedding_model_endpoint_name": "databricks-gte-large-en"
            }
        ],
        "pipeline_type": "TRIGGERED"  # 或 "CONTINUOUS"
    }
)
```

### 查詢索引

```python
results = w.vector_search_indexes.query_index(
    index_name="catalog.schema.my_index",
    columns=["id", "content", "metadata"],
    query_text="什麼是機器學習？",
    num_results=5
)

for doc in results.result.data_array:
    score = doc[-1]  # 相似度分數是最後一欄
    print(f"分數：{score}，內容：{doc[1][:100]}...")
```

## 常見模式

### 建立儲存優化端點

```python
# 用於大規模、具成本效益的部署
endpoint = w.vector_search_endpoints.create_endpoint(
    name="my-storage-endpoint",
    endpoint_type="STORAGE_OPTIMIZED"
)
```

### 使用自管理嵌入的 Delta 同步

```python
# 來源資料表必須有：主鍵 + 嵌入向量欄位
index = w.vector_search_indexes.create_index(
    name="catalog.schema.my_index",
    endpoint_name="my-vs-endpoint",
    primary_key="id",
    index_type="DELTA_SYNC",
    delta_sync_index_spec={
        "source_table": "catalog.schema.documents",
        "embedding_vector_columns": [
            {
                "name": "embedding",  # 預先計算的嵌入欄位
                "embedding_dimension": 768
            }
        ],
        "pipeline_type": "TRIGGERED"
    }
)
```

### 直接存取索引

```python
import json

# 建立用於手動 CRUD 的索引
index = w.vector_search_indexes.create_index(
    name="catalog.schema.direct_index",
    endpoint_name="my-vs-endpoint",
    primary_key="id",
    index_type="DIRECT_ACCESS",
    direct_access_index_spec={
        "embedding_vector_columns": [
            {"name": "embedding", "embedding_dimension": 768}
        ],
        "schema_json": json.dumps({
            "id": "string",
            "text": "string",
            "embedding": "array<float>",
            "metadata": "string"
        })
    }
)

# 更新插入資料
w.vector_search_indexes.upsert_data_vector_index(
    index_name="catalog.schema.direct_index",
    inputs_json=json.dumps([
        {"id": "1", "text": "你好", "embedding": [0.1, 0.2, ...], "metadata": "doc1"},
        {"id": "2", "text": "世界", "embedding": [0.3, 0.4, ...], "metadata": "doc2"},
    ])
)

# 刪除資料
w.vector_search_indexes.delete_data_vector_index(
    index_name="catalog.schema.direct_index",
    primary_keys=["1", "2"]
)
```

### 使用嵌入向量查詢

```python
# 當您有預先計算的查詢嵌入時
results = w.vector_search_indexes.query_index(
    index_name="catalog.schema.my_index",
    columns=["id", "text"],
    query_vector=[0.1, 0.2, 0.3, ...],  # 您的 768 維向量
    num_results=10
)
```

### 混合搜尋（語義 + 關鍵字）

```python
# 結合向量相似度與關鍵字匹配
results = w.vector_search_indexes.query_index(
    index_name="catalog.schema.my_index",
    columns=["id", "content"],
    query_text="機器學習演算法",
    query_type="hybrid",  # 啟用混合搜尋
    num_results=10
)
```

## 篩選

### 標準端點篩選器（字典格式）

```python
# filters_json 使用字典格式
results = w.vector_search_indexes.query_index(
    index_name="catalog.schema.my_index",
    columns=["id", "content"],
    query_text="機器學習",
    num_results=10,
    filters_json='{"category": "ai", "status": ["active", "pending"]}'
)
```

### 儲存優化篩選器（類 SQL）

```python
# filter_string 使用類 SQL 語法
results = w.vector_search_indexes.query_index(
    index_name="catalog.schema.my_index",
    columns=["id", "content"],
    query_text="機器學習",
    num_results=10,
    filter_string="category = 'ai' AND status IN ('active', 'pending')"
)

# 更多篩選器範例
filter_string="price > 100 AND price < 500"
filter_string="department LIKE 'eng%'"
filter_string="created_at >= '2024-01-01'"
```

### 觸發索引同步

```python
# 對於 TRIGGERED 管線類型，手動同步
w.vector_search_indexes.sync_index(
    index_name="catalog.schema.my_index"
)
```

### 掃描所有索引項目

```python
# 檢索所有向量（用於除錯/匯出）
scan_result = w.vector_search_indexes.scan_index(
    index_name="catalog.schema.my_index",
    num_results=100
)
```

## 參考文件

- [index-types.md](index-types.md) - 索引類型的詳細比較和建立模式

## CLI 快速參考

```bash
# 列出端點
databricks vector-search endpoints list

# 建立端點
databricks vector-search endpoints create \
    --name my-endpoint \
    --endpoint-type STANDARD

# 列出端點上的索引
databricks vector-search indexes list-indexes \
    --endpoint-name my-endpoint

# 取得索引狀態
databricks vector-search indexes get-index \
    --index-name catalog.schema.my_index

# 同步索引（用於 TRIGGERED）
databricks vector-search indexes sync-index \
    --index-name catalog.schema.my_index

# 刪除索引
databricks vector-search indexes delete-index \
    --index-name catalog.schema.my_index
```

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **索引同步緩慢** | 使用儲存優化端點（索引速度快 20 倍） |
| **查詢延遲高** | 使用標準端點以獲得 <100ms 延遲 |
| **filters_json 無法運作** | 儲存優化使用 `filter_string`（SQL 語法） |
| **嵌入維度不匹配** | 確保查詢和索引維度匹配 |
| **索引未更新** | 檢查 pipeline_type；對 TRIGGERED 使用 sync_index() |
| **容量不足** | 升級到儲存優化（10 億+個向量） |

## 嵌入模型

Databricks 提供內建的嵌入模型：

| 模型 | 維度 | 使用案例 |
|-------|------------|----------|
| `databricks-gte-large-en` | 1024 | 英文文字，高品質 |
| `databricks-bge-large-en` | 1024 | 英文文字，通用 |

```python
# 與託管嵌入一起使用
embedding_source_columns=[
    {
        "name": "content",
        "embedding_model_endpoint_name": "databricks-gte-large-en"
    }
]
```

## MCP 工具

以下 MCP 工具可用於管理向量搜尋基礎設施。這些是用於建立和配置端點/索引的**管理工具**。對於代理執行時查詢，請使用 Databricks 託管的向量搜尋 MCP 伺服器或 `VectorSearchRetrieverTool`。

### 端點管理

| 工具 | 說明 |
|------|-------------|
| `create_vs_endpoint` | 建立向量搜尋端點（STANDARD 或 STORAGE_OPTIMIZED） |
| `get_vs_endpoint` | 取得端點狀態和詳細資訊 |
| `list_vs_endpoints` | 列出工作區中的所有端點 |
| `delete_vs_endpoint` | 刪除端點（必須先刪除索引） |

### 索引管理

| 工具 | 說明 |
|------|-------------|
| `create_vs_index` | 建立 Delta 同步或直接存取索引 |
| `get_vs_index` | 取得索引狀態和配置 |
| `list_vs_indexes` | 列出端點上的所有索引 |
| `delete_vs_index` | 刪除索引 |
| `sync_vs_index` | 觸發 TRIGGERED 管線索引的同步 |

### 查詢和資料

| 工具 | 說明 |
|------|-------------|
| `query_vs_index` | 使用文字、向量或混合搜尋查詢索引（用於測試） |
| `upsert_vs_data` | 將向量更新插入直接存取索引 |
| `delete_vs_data` | 從直接存取索引刪除向量 |
| `scan_vs_index` | 掃描/匯出索引項目（用於除錯） |

## 注意事項

- **儲存優化是較新的選項** - 除非您需要 <100ms 延遲，否則適用於大多數使用案例
- **建議使用 Delta 同步** - 對於大多數情境比直接存取更容易
- **混合搜尋** - 適用於 Delta 同步和直接存取索引
- **管理 vs 執行時** - 上述 MCP 工具處理生命週期管理；對於執行時的代理工具呼叫，請使用 Databricks 託管的向量搜尋 MCP 伺服器
