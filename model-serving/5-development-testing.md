# 開發與測試工作流程 (Development & Testing Workflow)

在 Databricks 上開發和測試代理的 MCP 工作流程。

> **如果 MCP 工具不可用**，請直接使用 Databricks CLI 或 Python SDK。參見 [Databricks CLI 文件](https://docs.databricks.com/dev-tools/cli/) 以了解 `databricks workspace import` 和 `databricks clusters spark-submit` 指令。

## 概述

```
┌─────────────────────────────────────────────────────────────┐
│ 步驟 1：在本地撰寫代理程式碼 (agent.py)                     │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 步驟 2：上傳到工作區                                        │
│   → upload_folder MCP 工具                                  │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 步驟 3：安裝套件                                            │
│   → execute_databricks_command MCP 工具                     │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 步驟 4：測試代理 (迭代)                                     │
│   → run_python_file_on_databricks MCP 工具                  │
│   → 若錯誤：本地修正，重新上傳，重新執行                    │
└─────────────────────────────────────────────────────────────┘
```

## 步驟 1：建立本地檔案

建立包含您的代理的專案資料夾：

```
my_agent/
├── agent.py           # 代理實作 (ResponsesAgent)
├── test_agent.py      # 本地測試腳本
├── log_model.py       # MLflow 記錄腳本
└── requirements.txt   # 相依性 (選擇性)
```

### agent.py

```python
import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse
from databricks_langchain import ChatDatabricks

LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"

class MyAgent(ResponsesAgent):
    def __init__(self):
        self.llm = ChatDatabricks(endpoint=LLM_ENDPOINT)
    
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        messages = [{"role": m.role, "content": m.content} for m in request.input]
        response = self.llm.invoke(messages)
        # 關鍵：必須使用輔助方法來處理輸出項目
        return ResponsesAgentResponse(
            output=[self.create_text_output_item(text=response.content, id="msg_1")]
        )

AGENT = MyAgent()
mlflow.models.set_model(AGENT)
```

### test_agent.py

```python
from agent import AGENT
from mlflow.types.responses import ResponsesAgentRequest, ChatContext

# 測試請求
request = ResponsesAgentRequest(
    input=[{"role": "user", "content": "What is Databricks?"}],
    context=ChatContext(user_id="test@example.com")
)

# 執行預測
result = AGENT.predict(request)
print("Response:", result.model_dump(exclude_none=True))
```

## 步驟 2：上傳到工作區

使用 `upload_folder` MCP 工具：

```
upload_folder(
    local_folder="./my_agent",
    workspace_folder="/Workspace/Users/you@company.com/my_agent"
)
```

這會平行上傳所有檔案。

## 步驟 3：安裝套件

使用 `execute_databricks_command` 安裝相依性：

```
execute_databricks_command(
    code="%pip install -U mlflow==3.6.0 databricks-langchain langgraph==0.3.4 databricks-agents pydantic"
)
```

**重要：** 儲存返回的 `cluster_id` 和 `context_id` 以供後續呼叫使用 - 重用 context 更快且能保留已安裝的套件。

### 後續指令 (重用 Context)

```
execute_databricks_command(
    code="dbutils.library.restartPython()",
    cluster_id="<cluster_id>",
    context_id="<context_id>"
)
```

## 步驟 4：測試代理

使用 `run_python_file_on_databricks`：

```
run_python_file_on_databricks(
    file_path="./my_agent/test_agent.py",
    cluster_id="<cluster_id>",
    context_id="<context_id>"
)
```

### 如果測試失敗

1. 從輸出中讀取錯誤
2. 修正本地檔案 (`agent.py` 或 `test_agent.py`)
3. 重新上傳：`upload_folder(...)`
4. 重新執行：`run_python_file_on_databricks(...)`

### 迭代技巧

- **保持 context 存活** - 重用 `cluster_id` 和 `context_id` 以便更快的迭代
- **套件持久化** - 一旦安裝，套件會保留在 context 中
- **先檢查匯入** - 在完整代理測試前執行最小測試

## 快速除錯指令

### 檢查套件是否已安裝

```
execute_databricks_command(
    code="import mlflow; print(mlflow.__version__)",
    cluster_id="<cluster_id>",
    context_id="<context_id>"
)
```

### 列出可用端點

```
execute_databricks_command(
    code="""
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
for ep in list(w.serving_endpoints.list())[:10]:
    print(f"{ep.name}: {ep.state.ready if ep.state else 'unknown'}")
    """,
    cluster_id="<cluster_id>",
    context_id="<context_id>"
)
```

### 直接測試 LLM 端點

```
execute_databricks_command(
    code="""
from databricks_langchain import ChatDatabricks
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")
response = llm.invoke([{"role": "user", "content": "Hello!"}])
print(response.content)
    """,
    cluster_id="<cluster_id>",
    context_id="<context_id>"
)
```

## 工作流程總結

| 步驟 | MCP 工具 | 用途 |
|------|----------|---------|
| 上傳檔案 | `upload_folder` | 將本地檔案同步到工作區 |
| 安裝套件 | `execute_databricks_command` | 設定相依性 |
| 重啟 Python | `execute_databricks_command` | 應用套件變更 |
| 測試代理 | `run_python_file_on_databricks` | 執行測試腳本 |
| 除錯 | `execute_databricks_command` | 快速檢查 |

## 下一步

一旦您的代理測試成功：

1. **記錄到 MLflow** → 參見 [6-logging-registration.md](6-logging-registration.md)
2. **部署端點** → 參見 [7-deployment.md](7-deployment.md)
3. **查詢端點** → 參見 [8-querying-endpoints.md](8-querying-endpoints.md)
