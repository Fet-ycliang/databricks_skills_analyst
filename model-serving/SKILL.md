---
name: model-serving
description: "部署和查詢 Databricks Model Serving 端點。在以下情況使用：(1) 將 MLflow 模型或 AI 代理部署到端點，(2) 建立 ChatAgent/ResponsesAgent 代理，(3) 整合 UC 函數或向量搜尋工具，(4) 查詢已部署的端點，(5) 檢查端點狀態。涵蓋經典 ML 模型、自訂 pyfunc 和 GenAI 代理。"
---

# Databricks Model Serving

將 MLflow 模型和 AI 代理部署到可擴展的 REST API 端點。

## 快速決策：您要部署什麼？

| 模型類型 | 模式 | 參考 |
|------------|---------|-----------|
| **傳統 ML**（sklearn、xgboost） | `mlflow.sklearn.autolog()` | [1-classical-ml.md](1-classical-ml.md) |
| **自訂 Python 模型** | `mlflow.pyfunc.PythonModel` | [2-custom-pyfunc.md](2-custom-pyfunc.md) |
| **GenAI 代理**（LangGraph、工具呼叫） | `ResponsesAgent` | [3-genai-agents.md](3-genai-agents.md) |

## 先決條件

- **DBR 16.1+** 建議（預先安裝 GenAI 套件）
- 啟用 Unity Catalog 的工作區
- 啟用 Model Serving

## 參考文件

| 主題 | 檔案 | 何時閱讀 |
|-------|------|--------------|
| 經典 ML | [1-classical-ml.md](1-classical-ml.md) | sklearn、xgboost、autolog |
| 自訂 PyFunc | [2-custom-pyfunc.md](2-custom-pyfunc.md) | 自訂預處理、簽章 |
| GenAI 代理 | [3-genai-agents.md](3-genai-agents.md) | ResponsesAgent、LangGraph |
| 工具整合 | [4-tools-integration.md](4-tools-integration.md) | UC 函數、向量搜尋 |
| 開發與測試 | [5-development-testing.md](5-development-testing.md) | MCP 工作流程、迭代 |
| 記錄與註冊 | [6-logging-registration.md](6-logging-registration.md) | mlflow.pyfunc.log_model |
| 部署 | [7-deployment.md](7-deployment.md) | 基於作業的非同步部署 |
| 查詢端點 | [8-querying-endpoints.md](8-querying-endpoints.md) | SDK、REST、MCP 工具 |
| 套件需求 | [9-package-requirements.md](9-package-requirements.md) | DBR 版本、pip |

---

## 快速入門：部署 GenAI 代理

### 步驟 1：安裝套件（在 notebook 中或透過 MCP）

```python
%pip install -U mlflow==3.6.0 databricks-langchain langgraph==0.3.4 databricks-agents pydantic
dbutils.library.restartPython()
```

或透過 MCP：
```
execute_databricks_command(code="%pip install -U mlflow==3.6.0 databricks-langchain langgraph==0.3.4 databricks-agents pydantic")
```

### 步驟 2：建立代理檔案

在本地建立 `agent.py`，使用 `ResponsesAgent` 模式（請參閱 [3-genai-agents.md](3-genai-agents.md)）。

### 步驟 3：上傳到工作區

```
upload_folder(
    local_folder="./my_agent",
    workspace_folder="/Workspace/Users/you@company.com/my_agent"
)
```

### 步驟 4：測試代理

```
run_python_file_on_databricks(
    file_path="./my_agent/test_agent.py",
    cluster_id="<cluster_id>"
)
```

### 步驟 5：記錄模型

```
run_python_file_on_databricks(
    file_path="./my_agent/log_model.py",
    cluster_id="<cluster_id>"
)
```

### 步驟 6：部署（透過作業非同步）

請參閱 [7-deployment.md](7-deployment.md) 以了解不會逾時的基於作業的部署。

### 步驟 7：查詢端點

```
query_serving_endpoint(
    name="my-agent-endpoint",
    messages=[{"role": "user", "content": "你好！"}]
)
```

---

## 快速入門：部署經典 ML 模型

```python
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression

# 啟用帶有自動註冊的 autolog
mlflow.sklearn.autolog(
    log_input_examples=True,
    registered_model_name="main.models.my_classifier"
)

# 訓練 - 模型會自動記錄和註冊
model = LogisticRegression()
model.fit(X_train, y_train)
```

然後透過 UI 或 SDK 部署。請參閱 [1-classical-ml.md](1-classical-ml.md)。

---

## MCP 工具

> **如果 MCP 工具不可用**，請使用下面參考文件中的 SDK/CLI 範例。

### 開發與測試

| 工具 | 用途 |
|------|---------|
| `upload_folder` | 將代理檔案上傳到工作區 |
| `run_python_file_on_databricks` | 測試代理、記錄模型 |
| `execute_databricks_command` | 安裝套件、快速測試 |

### 部署

| 工具 | 用途 |
|------|---------|
| `create_job` | 建立部署作業（一次性） |
| `run_job_now` | 啟動部署（非同步） |
| `get_run` | 檢查部署作業狀態 |

### 查詢

| 工具 | 用途 |
|------|---------|
| `get_serving_endpoint_status` | 檢查端點是否為 READY |
| `query_serving_endpoint` | 向端點發送請求 |
| `list_serving_endpoints` | 列出所有端點 |

---

## 常見工作流程

### 部署後檢查端點狀態

```
get_serving_endpoint_status(name="my-agent-endpoint")
```

返回：
```json
{
    "name": "my-agent-endpoint",
    "state": "READY",
    "served_entities": [...]
}
```

### 查詢聊天/代理端點

```
query_serving_endpoint(
    name="my-agent-endpoint",
    messages=[
        {"role": "user", "content": "什麼是 Databricks？"}
    ],
    max_tokens=500
)
```

### 查詢傳統 ML 端點

```
query_serving_endpoint(
    name="sklearn-classifier",
    dataframe_records=[
        {"age": 25, "income": 50000, "credit_score": 720}
    ]
)
```

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **無效的輸出格式** | 使用 `self.create_text_output_item(text, id)` - 不要使用原始字典！ |
| **端點 NOT_READY** | 部署需要約 15 分鐘。使用 `get_serving_endpoint_status` 輪詢。 |
| **找不到套件** | 在記錄模型時於 `pip_requirements` 中指定確切版本 |
| **工具逾時** | 使用基於作業的部署，而非同步呼叫 |
| **端點上的驗證錯誤** | 確保在 `log_model` 中指定 `resources` 以進行自動傳遞 |
| **找不到模型** | 檢查 Unity Catalog 路徑：`catalog.schema.model_name` |

### 關鍵：ResponsesAgent 輸出格式

**錯誤** - 原始字典無法運作：
```python
return ResponsesAgentResponse(output=[{"role": "assistant", "content": "..."}])
```

**正確** - 使用輔助方法：
```python
return ResponsesAgentResponse(
    output=[self.create_text_output_item(text="...", id="msg_1")]
)
```

可用的輔助方法：
- `self.create_text_output_item(text, id)` - 文字回應
- `self.create_function_call_item(id, call_id, name, arguments)` - 工具呼叫
- `self.create_function_call_output_item(call_id, output)` - 工具結果

---

## 資源

- [Model Serving 文件](https://docs.databricks.com/machine-learning/model-serving/)
- [MLflow 3 ResponsesAgent](https://mlflow.org/docs/latest/llms/responses-agent-intro/)
- [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)
