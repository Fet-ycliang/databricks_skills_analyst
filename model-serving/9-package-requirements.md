# 套件需求 (Package Requirements)

Databricks Runtime 版本和 pip 套件相容性。

## 推薦的 Databricks Runtime

| DBR 版本 | 狀態 | 備註 |
|-------------|--------|-------|
| **16.1+** | 推薦 | 預先安裝最新的 GenAI 套件 |
| **15.4 LTS** | 支援 | 需要更多 pip 安裝 |
| **14.x** | 舊版 | 缺少許多 GenAI 功能 |

**使用 DBR 16.1+ 進行代理開發** - 它預先安裝了大多數套件。

## 預先安裝的套件 (DBR 16.1+)

無需 `%pip install` 即可使用：

- `mlflow` (3.x)
- `langchain`
- `pydantic`
- `pandas`, `numpy`, `scipy`
- `scikit-learn`
- `databricks-sdk`

## 需要安裝的套件

對於 GenAI 代理，安裝這些：

```python
%pip install -U mlflow==3.6.0 databricks-langchain langgraph==0.3.4 databricks-agents pydantic
dbutils.library.restartPython()
```

### 套件細目

| 套件 | 用途 | 版本 |
|---------|---------|---------|
| `mlflow` | 模型記錄、服務 | `==3.6.0` |
| `databricks-langchain` | ChatDatabricks, UCFunctionToolkit | 最新 |
| `langgraph` | 代理圖框架 | `==0.3.4` |
| `databricks-agents` | `agents.deploy()` | 最新 |
| `pydantic` | 資料驗證 | 最新 |

### 帶有 Memory/Lakebase 支援

```python
%pip install -U mlflow==3.6.0 databricks-langchain[memory] langgraph==0.3.4 databricks-agents
```

### 用於 Vector Search

```python
%pip install -U mlflow==3.6.0 databricks-langchain databricks-vectorsearch langgraph==0.3.4
```

### 測試用最小安裝

```python
%pip install -U mlflow-skinny[databricks] databricks-agents
```

## 模型記錄的 pip_requirements

記錄模型時，指定確切版本：

```python
pip_requirements=[
    "mlflow==3.6.0",
    "databricks-langchain",
    "langgraph==0.3.4",
    "pydantic",
]
```

### 動態獲取當前版本

```python
from pkg_resources import get_distribution

pip_requirements=[
    f"mlflow=={get_distribution('mlflow').version}",
    f"databricks-langchain=={get_distribution('databricks-langchain').version}",
    f"langgraph=={get_distribution('langgraph').version}",
]
```

## 經測試的組合

### 代理開發（推薦）

```
mlflow==3.6.0
databricks-langchain>=0.3.0
langgraph==0.3.4
databricks-agents>=0.20.0
pydantic>=2.0
```

### LangChain 追蹤

```
mlflow==2.14.0
langchain==0.2.1
langchain-openai==0.1.8
langchain-community==0.2.1
```

### 經典 ML

```
mlflow>=2.10.0
scikit-learn>=1.3.0
pandas>=2.0.0
```

## 常見版本問題

| 問題 | 原因 | 解決方案 |
|-------|-------|----------|
| **ImportError: ResponsesAgent** | 舊 mlflow | `pip install mlflow>=3.0` |
| **LangGraph 錯誤** | 版本不匹配 | 固定為 `langgraph==0.3.4` |
| **Pydantic 驗證錯誤** | v1 vs v2 | 使用 `pydantic>=2.0` |
| **ChatDatabricks 找不到** | 缺少套件 | `pip install databricks-langchain` |
| **agents.deploy 失敗** | 缺少套件 | `pip install databricks-agents` |

## 環境變數

設定這些以進行驗證：

```bash
# 選項 1：Host + Token
export DATABRICKS_HOST="https://your-workspace.databricks.com"
export DATABRICKS_TOKEN="your-token"

# 選項 2：Profile
export DATABRICKS_CONFIG_PROFILE="your-profile"
```

## 透過 MCP 安裝套件

使用 `execute_databricks_command`：

```
execute_databricks_command(
    code="%pip install -U mlflow==3.6.0 databricks-langchain langgraph==0.3.4 databricks-agents pydantic"
)
```

然後重啟 Python：

```
execute_databricks_command(
    code="dbutils.library.restartPython()",
    cluster_id="<cluster_id>",
    context_id="<context_id>"
)
```

## 檢查已安裝版本

```python
import pkg_resources

packages = ['mlflow', 'langchain', 'langgraph', 'pydantic', 'databricks-langchain']
for pkg in packages:
    try:
        version = pkg_resources.get_distribution(pkg).version
        print(f"{pkg}: {version}")
    except pkg_resources.DistributionNotFound:
        print(f"{pkg}: NOT INSTALLED")
```

透過 MCP：

```
execute_databricks_command(
    code="""
import pkg_resources
for pkg in ['mlflow', 'langchain', 'langgraph', 'pydantic', 'databricks-langchain']:
    try:
        print(f"{pkg}: {pkg_resources.get_distribution(pkg).version}")
    except:
        print(f"{pkg}: NOT INSTALLED")
    """
)
```
