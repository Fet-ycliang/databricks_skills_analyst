# 向量搜尋索引類型

## 比較矩陣

| 功能 | Delta 同步（託管） | Delta 同步（自管理） | 直接存取 |
|---------|---------------------|---------------------------|---------------|
| **嵌入** | Databricks 計算 | 您提供 | 您提供 |
| **同步** | 從 Delta 自動同步 | 從 Delta 自動同步 | 手動 CRUD |
| **設定** | 最簡單 | 中等 | 最多控制 |
| **來源** | Delta 資料表 + 文字 | Delta 資料表 + 向量 | API 呼叫 |
| **最適合** | 快速入門、RAG | 自訂模型 | 即時應用程式 |

## 使用託管嵌入的 Delta 同步

Databricks 自動從您的文字欄位計算嵌入。

### 需求

- 來源 Delta 資料表包含：
  - 主鍵欄位（唯一識別碼）
  - 文字欄位（要嵌入的內容）
- 嵌入模型端點（或使用內建）

### 建立索引

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

index = w.vector_search_indexes.create_index(
    name="catalog.schema.docs_index",
    endpoint_name="my-vs-endpoint",
    primary_key="doc_id",
    index_type="DELTA_SYNC",
    delta_sync_index_spec={
        "source_table": "catalog.schema.documents",
        "embedding_source_columns": [
            {
                "name": "content",
                "embedding_model_endpoint_name": "databricks-gte-large-en"
            }
        ],
        "pipeline_type": "TRIGGERED",  # 或 "CONTINUOUS"
        "columns_to_sync": ["doc_id", "content", "title", "category"]
    }
)
```

### 管線類型

| 類型 | 行為 | 成本 | 使用案例 |
|------|----------|------|----------|
| `TRIGGERED` | 透過 API 手動同步 | 較低 | 批次更新 |
| `CONTINUOUS` | 變更時自動同步 | 較高 | 即時同步 |

### 來源資料表範例

```sql
CREATE TABLE catalog.schema.documents (
    doc_id STRING,
    title STRING,
    content STRING,  -- 要嵌入的文字
    category STRING,
    created_at TIMESTAMP
);
```

## 使用自管理嵌入的 Delta 同步

您預先計算嵌入並將其儲存在來源資料表中。

### 需求

- 來源 Delta 資料表包含：
  - 主鍵欄位
  - 嵌入向量欄位（浮點數陣列）

### 建立索引

```python
index = w.vector_search_indexes.create_index(
    name="catalog.schema.custom_index",
    endpoint_name="my-vs-endpoint",
    primary_key="id",
    index_type="DELTA_SYNC",
    delta_sync_index_spec={
        "source_table": "catalog.schema.embedded_docs",
        "embedding_vector_columns": [
            {
                "name": "embedding",
                "embedding_dimension": 768
            }
        ],
        "pipeline_type": "TRIGGERED"
    }
)
```

### 計算嵌入

```python
from databricks.sdk import WorkspaceClient
import pandas as pd

w = WorkspaceClient()

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """為文字呼叫嵌入端點。"""
    response = w.serving_endpoints.query(
        name="databricks-gte-large-en",
        input=texts
    )
    return [item.embedding for item in response.data]

# 將嵌入新增到您的資料
df = spark.table("catalog.schema.documents").toPandas()
df["embedding"] = get_embeddings(df["content"].tolist())

# 寫回 Delta
spark.createDataFrame(df).write.mode("overwrite").saveAsTable(
    "catalog.schema.embedded_docs"
)
```

### 來源資料表範例

```sql
CREATE TABLE catalog.schema.embedded_docs (
    id STRING,
    content STRING,
    embedding ARRAY<FLOAT>,  -- 預先計算的嵌入
    metadata STRING
);
```

## 直接存取索引

透過 CRUD API 完全控制向量資料。無 Delta 資料表同步。

### 需求

- 預先定義結構描述
- 自行管理更新插入/刪除操作

### 建立索引

```python
import json

index = w.vector_search_indexes.create_index(
    name="catalog.schema.realtime_index",
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
            "category": "string",
            "score": "float"
        })
    }
)
```

### 更新插入資料

```python
import json

# 插入或更新向量
w.vector_search_indexes.upsert_data_vector_index(
    index_name="catalog.schema.realtime_index",
    inputs_json=json.dumps([
        {
            "id": "doc-001",
            "text": "機器學習基礎",
            "embedding": [0.1, 0.2, 0.3, ...],  # 768 個浮點數
            "category": "ml",
            "score": 0.95
        },
        {
            "id": "doc-002",
            "text": "深度學習概述",
            "embedding": [0.4, 0.5, 0.6, ...],
            "category": "dl",
            "score": 0.88
        }
    ])
)
```

### 刪除資料

```python
w.vector_search_indexes.delete_data_vector_index(
    index_name="catalog.schema.realtime_index",
    primary_keys=["doc-001", "doc-002"]
)
```

### 附加嵌入模型（選用）

對於使用文字查詢的直接存取：

```python
# 建立帶有嵌入模型的索引，用於查詢時嵌入
index = w.vector_search_indexes.create_index(
    name="catalog.schema.hybrid_index",
    endpoint_name="my-vs-endpoint",
    primary_key="id",
    index_type="DIRECT_ACCESS",
    direct_access_index_spec={
        "embedding_vector_columns": [
            {"name": "embedding", "embedding_dimension": 768}
        ],
        "embedding_model_endpoint_name": "databricks-gte-large-en",  # 用於 query_text
        "schema_json": json.dumps({...})
    }
)
```

## 選擇正確的類型

```
從這裡開始：
│
├─ 您有預先計算的嵌入嗎？
│   ├─ 是 → 您想要從 Delta 自動同步嗎？
│   │         ├─ 是 → Delta 同步（自管理）
│   │         └─ 否  → 直接存取
│   │
│   └─ 否 → Delta 同步（託管嵌入）
│
└─ 您需要即時更新（<1 秒）嗎？
    ├─ 是 → 直接存取
    └─ 否  → Delta 同步（任何類型）
```

## 端點選擇

選擇索引類型後，選擇端點：

| 情境 | 端點類型 |
|----------|---------------|
| 需要 <100ms 延遲 | 標準 |
| >1 億個向量 | 儲存優化 |
| 成本敏感 | 儲存優化 |
| 預設選擇 | 儲存優化 |
