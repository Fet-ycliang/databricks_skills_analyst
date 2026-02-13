# 記錄與註冊 (Logging & Registration)

將模型記錄到 MLflow 並註冊到 Unity Catalog。

## 基於檔案的記錄 (推薦用於代理)

從 Python 檔案而不是類別實例記錄：

```python
# log_model.py
import mlflow
from agent import AGENT, LLM_ENDPOINT
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksFunction
from unitycatalog.ai.langchain.toolkit import UnityCatalogTool
from databricks_langchain import VectorSearchRetrieverTool

mlflow.set_registry_uri("databricks-uc")

# 收集資源以進行自動驗證
resources = [DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT)]

# 加入 UC 函數資源
from agent import tools  # 若您的代理匯出工具
for tool in tools:
    if isinstance(tool, UnityCatalogTool):
        resources.append(DatabricksFunction(function_name=tool.uc_function_name))
    elif isinstance(tool, VectorSearchRetrieverTool):
        resources.extend(tool.resources)

# 輸入範例
input_example = {
    "input": [{"role": "user", "content": "What is Databricks?"}]
}

# 記錄模型
with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",  # 檔案路徑
        input_example=input_example,
        resources=resources,
        pip_requirements=[
            "mlflow==3.6.0",
            "databricks-langchain",
            "langgraph==0.3.4",
            "pydantic",
        ],
    )
    print(f"Model URI: {model_info.model_uri}")

# 註冊到 Unity Catalog
catalog = "main"
schema = "agents"
model_name = "my_agent"

uc_model_info = mlflow.register_model(
    model_uri=model_info.model_uri,
    name=f"{catalog}.{schema}.{model_name}"
)
print(f"Registered: {uc_model_info.name} version {uc_model_info.version}")
```

透過 MCP 執行：

```
run_python_file_on_databricks(file_path="./my_agent/log_model.py")
```

## 自動驗證的資源

Databricks 自動為這些資源類型配置憑證：

| 資源類型 | 匯入 | 用途 |
|--------------|--------|-------|
| `DatabricksServingEndpoint` | `mlflow.models.resources` | LLM 端點 |
| `DatabricksFunction` | `mlflow.models.resources` | UC SQL/Python 函數 |
| `DatabricksVectorSearchIndex` | `mlflow.models.resources` | Vector Search 索引 |
| `DatabricksLakebase` | `mlflow.models.resources` | Lakebase 實例 |

```python
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksFunction,
    DatabricksVectorSearchIndex,
    DatabricksLakebase,
)

resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-meta-llama-3-3-70b-instruct"),
    DatabricksFunction(function_name="catalog.schema.my_function"),
    DatabricksVectorSearchIndex(index_name="catalog.schema.my_index"),
    DatabricksLakebase(database_instance_name="my-lakebase"),
]
```

## pip_requirements

### 推薦版本 (已測試)

```python
pip_requirements=[
    "mlflow==3.6.0",
    "databricks-langchain",  # 最新版
    "langgraph==0.3.4",
    "pydantic",
    "databricks-agents",
]
```

### 帶有 Memory 支援

```python
pip_requirements=[
    "mlflow==3.6.0",
    "databricks-langchain[memory]",  # 包含 Lakebase 支援
    "langgraph==0.3.4",
]
```

### 獲取當前版本

```python
from pkg_resources import get_distribution

pip_requirements=[
    f"mlflow=={get_distribution('mlflow').version}",
    f"databricks-langchain=={get_distribution('databricks-langchain').version}",
]
```

## 部署前驗證

部署前，驗證模型可載入並執行：

```python
# 在本地驗證 (使用 uv 快速建立環境)
mlflow.models.predict(
    model_uri=model_info.model_uri,
    input_data={"input": [{"role": "user", "content": "Test"}]},
    env_manager="uv",
)
```

透過 MCP 執行 (在 log_model.py 或單獨檔案中)：

```python
# validate_model.py
import mlflow

# 從上一步獲取 model URI
model_uri = "runs:/<run_id>/agent"  # 或從 UC: "models:/catalog.schema.model/1"

result = mlflow.models.predict(
    model_uri=model_uri,
    input_data={"input": [{"role": "user", "content": "Hello"}]},
    env_manager="uv",
)
print("Validation result:", result)
```

## 經典 ML 記錄

對於傳統 ML 模型，autolog 處理一切：

```python
import mlflow
import mlflow.sklearn

mlflow.sklearn.autolog(
    log_input_examples=True,
    registered_model_name="main.models.my_model"
)

# 訓練 - 自動記錄並註冊
model.fit(X_train, y_train)
```

## 手動註冊 (分開步驟)

如果您記錄時未註冊：

```python
import mlflow

mlflow.set_registry_uri("databricks-uc")

# 從 run
mlflow.register_model(
    model_uri="runs:/<run_id>/agent",
    name="main.agents.my_agent"
)

# 從 logged model info
mlflow.register_model(
    model_uri=model_info.model_uri,
    name="main.agents.my_agent"
)
```

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **服務時找不到套件** | 在 `pip_requirements` 中指定確切版本 |
| **存取端點時的 Auth 錯誤** | 將資源加入 `resources` 列表 |
| **模型簽章不匹配** | 提供與您輸入格式匹配的 `input_example` |
| **模型載入緩慢** | 使用 `env_manager="uv"` 進行更快的驗證 |
| **找不到程式碼** | 對於額外相依性使用 `code_paths=["file.py"]` |
