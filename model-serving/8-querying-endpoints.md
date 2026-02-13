# 查詢端點 (Querying Endpoints)

向已部署的 Model Serving 端點發送請求。

> **如果 MCP 工具不可用**，請使用下面的 Python SDK 或 REST API 範例。

## MCP 工具

### 檢查端點狀態

查詢前，驗證端點是否已準備就緒：

```
get_serving_endpoint_status(name="my-agent-endpoint")
```

回應：
```json
{
    "name": "my-agent-endpoint",
    "state": "READY",
    "served_entities": [
        {"name": "my_agent-1", "entity_name": "main.agents.my_agent", "deployment_state": "READY"}
    ]
}
```

### 查詢聊天/代理端點

```
query_serving_endpoint(
    name="my-agent-endpoint",
    messages=[
        {"role": "user", "content": "What is Databricks?"}
    ],
    max_tokens=500,
    temperature=0.7
)
```

回應：
```json
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Databricks is a unified data intelligence platform..."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 150,
        "total_tokens": 160
    }
}
```

### 查詢 ML 模型端點

```
query_serving_endpoint(
    name="sklearn-classifier",
    dataframe_records=[
        {"age": 25, "income": 50000, "credit_score": 720},
        {"age": 35, "income": 75000, "credit_score": 680}
    ]
)
```

回應：
```json
{
    "predictions": [0.85, 0.72]
}
```

### 列出所有端點

```
list_serving_endpoints(limit=20)
```

## Python SDK

### 查詢代理/聊天端點

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

response = w.serving_endpoints.query(
    name="my-agent-endpoint",
    messages=[
        {"role": "user", "content": "What is Databricks?"}
    ],
    max_tokens=500
)

print(response.choices[0].message.content)
```

### 查詢 ML 模型

```python
response = w.serving_endpoints.query(
    name="sklearn-classifier",
    dataframe_records=[
        {"age": 25, "income": 50000, "credit_score": 720}
    ]
)

print(response.predictions)
```

### 串流 (代理端點)

```python
for chunk in w.serving_endpoints.query(
    name="my-agent-endpoint",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
):
    if chunk.choices:
        print(chunk.choices[0].delta.content, end="")
```

## REST API

### 獲取端點狀態

```bash
curl -X GET \
  "https://<workspace>.databricks.com/api/2.0/serving-endpoints/<endpoint-name>" \
  -H "Authorization: Bearer <token>"
```

### 查詢聊天/代理端點

```bash
curl -X POST \
  "https://<workspace>.databricks.com/serving-endpoints/<endpoint-name>/invocations" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
        {"role": "user", "content": "What is Databricks?"}
    ],
    "max_tokens": 500
  }'
```

### 查詢 ML 模型

```bash
curl -X POST \
  "https://<workspace>.databricks.com/serving-endpoints/<endpoint-name>/invocations" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "dataframe_records": [
        {"age": 25, "income": 50000, "credit_score": 720}
    ]
  }'
```

## 整合模式

### 在 Python 應用程式中

```python
from databricks.sdk import WorkspaceClient
import os

# 使用環境變數中的 DATABRICKS_HOST 和 DATABRICKS_TOKEN
w = WorkspaceClient()

def ask_agent(question: str) -> str:
    response = w.serving_endpoints.query(
        name="my-agent-endpoint",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# 使用
answer = ask_agent("What is a Delta table?")
print(answer)
```

### 在另一個代理中 (代理鏈接)

```python
from databricks.sdk import WorkspaceClient
from langchain_core.tools import tool

w = WorkspaceClient()

@tool
def ask_specialist_agent(question: str) -> str:
    """Ask a specialist agent for domain-specific answers."""
    response = w.serving_endpoints.query(
        name="specialist-agent-endpoint",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

# 加入主代理的工具列表
tools = [ask_specialist_agent]
```

### 透過 OpenAI 相容函式庫

Databricks 端點與 OpenAI 相容：

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<workspace>.databricks.com/serving-endpoints/<endpoint-name>",
    api_key="<databricks-token>"
)

response = client.chat.completions.create(
    model="<endpoint-name>",  # 任何值皆可，端點決定模型
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## 錯誤處理

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, PermissionDenied

w = WorkspaceClient()

try:
    response = w.serving_endpoints.query(
        name="my-endpoint",
        messages=[{"role": "user", "content": "Test"}]
    )
except NotFound:
    print("Endpoint not found - check name or wait for deployment")
except PermissionDenied:
    print("No permission to query this endpoint")
except Exception as e:
    if "NOT_READY" in str(e):
        print("Endpoint is still starting up")
    else:
        raise
```

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **端點 NOT_READY** | 等待部署（代理需約 15 分鐘） |
| **404 Not Found** | 檢查端點名稱，可能與模型名稱不同 |
| **Permission Denied** | 確保 token 擁有服務端點權限 |
| **Timeout 逾時** | 增加逾時時間，減少 max_tokens |
| **空的回應** | 檢查模型簽章是否匹配輸入格式 |
