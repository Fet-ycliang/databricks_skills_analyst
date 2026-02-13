# 工具整合 (Tools Integration)

將 Unity Catalog 函數和向量搜尋加入您的代理。

## Unity Catalog 函數 (UCFunctionToolkit)

UC 函數是註冊在 Unity Catalog 中的 SQL/Python UDFs，代理可以將其作為工具呼叫。

### 設定

```python
from databricks_langchain import UCFunctionToolkit

# 依名稱指定函數
uc_toolkit = UCFunctionToolkit(
    function_names=[
        "catalog.schema.my_function",
        "catalog.schema.another_function",
        "system.ai.python_exec",  # 內建 Python 直譯器
    ]
)

# 加入您的工具列表
tools = []
tools.extend(uc_toolkit.tools)
```

### 萬用字元選擇

```python
# schema 中的所有函數
uc_toolkit = UCFunctionToolkit(
    function_names=["catalog.schema.*"]
)
```

### 內建 UC 工具

| 函數 | 用途 |
|----------|---------|
| `system.ai.python_exec` | 執行 Python 程式碼 |
| `system.ai.similarity_search` | 向量相似度搜尋 |

### 建立 UC 函數

```sql
-- 在筆記本或 SQL 編輯器中
CREATE OR REPLACE FUNCTION catalog.schema.get_customer_info(customer_id STRING)
RETURNS TABLE(name STRING, email STRING, tier STRING)
LANGUAGE SQL
COMMENT 'Get customer information by ID'
RETURN
  SELECT name, email, tier
  FROM catalog.schema.customers
  WHERE id = customer_id;
```

### 註冊資源以進行 Auth Passthrough

記錄模型時，將 UC 函數包含為資源：

```python
from mlflow.models.resources import DatabricksFunction

resources = []
for tool in tools:
    if hasattr(tool, "uc_function_name"):
        resources.append(DatabricksFunction(function_name=tool.uc_function_name))
```

## 向量搜尋 (VectorSearchRetrieverTool)

使用 Databricks Vector Search 索引增加 RAG 能力。

### 設定

```python
from databricks_langchain import VectorSearchRetrieverTool

# 建立檢索器工具
vs_tool = VectorSearchRetrieverTool(
    index_name="catalog.schema.my_vector_index",
    num_results=5,
    # 選擇性：過濾結果
    # filters={"category": "documentation"}
)

tools = [vs_tool]
```

### 帶有過濾器

```python
vs_tool = VectorSearchRetrieverTool(
    index_name="catalog.schema.docs_index",
    num_results=10,
    filters={"doc_type": "technical", "status": "published"},
    columns=["content", "title", "url"],  # 要返回的欄位
)
```

### 註冊資源

向量搜尋工具自動提供其資源：

```python
from mlflow.models.resources import DatabricksServingEndpoint

resources = [DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT)]

for tool in tools:
    if isinstance(tool, VectorSearchRetrieverTool):
        resources.extend(tool.resources)  # 包含 VS 索引和 embedding 端點
```

## 使用 @tool 裝飾器的自訂工具

為您的代理建立自訂工具：

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
def get_current_time(timezone: str = "UTC") -> str:
    """Get the current time in the specified timezone.
    
    Args:
        timezone: The timezone (e.g., 'UTC', 'America/New_York')
    """
    from datetime import datetime
    import pytz
    
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.
    
    Args:
        expression: A math expression like '2 + 2' or 'sqrt(16)'
    """
    import math
    # 使用數學函數進行安全評估
    allowed = {k: v for k, v in math.__dict__.items() if not k.startswith('_')}
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)
    except Exception as e:
        return f"Error: {e}"

# 加入工具列表
tools = [get_current_time, calculate]
```

### 帶有 Config 存取的工具

在工具中存取執行時設定 (user_id 等)：

```python
@tool
def get_user_preferences(config: RunnableConfig) -> str:
    """Get preferences for the current user."""
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "No user ID provided"
    
    # 從資料庫獲取
    # ...
    return f"Preferences for {user_id}: ..."
```

## 結合所有工具類型

```python
from databricks_langchain import ChatDatabricks, UCFunctionToolkit, VectorSearchRetrieverTool
from langchain_core.tools import tool

# LLM
llm = ChatDatabricks(endpoint="databricks-meta-llama-3-3-70b-instruct")

# 所有工具
tools = []

# 1. UC 函數
uc_toolkit = UCFunctionToolkit(function_names=["catalog.schema.*"])
tools.extend(uc_toolkit.tools)

# 2. 向量搜尋
vs_tool = VectorSearchRetrieverTool(index_name="catalog.schema.docs_index")
tools.append(vs_tool)

# 3. 自訂工具
@tool
def my_custom_tool(query: str) -> str:
    """Custom tool description."""
    return f"Result for: {query}"

tools.append(my_custom_tool)

# 綁定到 LLM
llm_with_tools = llm.bind_tools(tools)
```

## 模型記錄的資源

收集所有資源以進行自動驗證：

```python
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksFunction,
    DatabricksVectorSearchIndex,
)
from unitycatalog.ai.langchain.toolkit import UnityCatalogTool

resources = [DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT)]

for tool in tools:
    # UC 函數
    if isinstance(tool, UnityCatalogTool):
        resources.append(DatabricksFunction(function_name=tool.uc_function_name))
    # 向量搜尋
    elif isinstance(tool, VectorSearchRetrieverTool):
        resources.extend(tool.resources)
    # 自訂工具不需要資源（它們在端點中執行）

# 記錄帶有資源的模型
mlflow.pyfunc.log_model(
    name="agent",
    python_model="agent.py",
    resources=resources,
    # ...
)
```

## 最佳實踐

1. **限制工具數量** - 代理在 5-10 個專注工具下運作最佳
2. **清晰的描述** - 工具文件字串會顯示給 LLM
3. **類型提示** - 始終為參數包含類型提示
4. **錯誤處理** - 返回錯誤訊息，不要引發異常
5. **獨立測試工具** - 在加入代理前驗證每個工具都能運作
