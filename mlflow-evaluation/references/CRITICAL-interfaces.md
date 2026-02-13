# 關鍵 MLflow 3 GenAI 介面 (CRITICAL MLflow 3 GenAI Interfaces)

**版本**: MLflow 3.1.0+ (mlflow[databricks]>=3.1.0)
**最後更新**: 基於 Databricks 官方文件

## 目錄

- [核心評估 API](#核心評估-api)
- [資料 Schema](#資料-schema)
- [內建評分器 (預建)](#內建評分器-預建)
- [自訂評分器](#自訂評分器)
- [裁判 (Judges) API (低層級)](#裁判-judges-api-低層級)
- [追蹤 (Trace) API](#追蹤-trace-api)
- [評估資料集 (MLflow 託管)](#評估資料集-mlflow-託管)
- [生產監控](#生產監控)
- [關鍵常數](#關鍵常數)
- [安裝](#安裝)
- [設定](#設定)

---

## 核心評估 API

### mlflow.genai.evaluate()

```python
import mlflow

results = mlflow.genai.evaluate(
    data=eval_dataset,        # List[dict], DataFrame, 或 EvalDataset
    predict_fn=my_app,        # 接收 **inputs 並返回 outputs 的 Callable
    scorers=[scorer1, scorer2] # Scorer 物件列表
)

# 返回: EvaluationResult 包含:
#   - results.run_id: str - 包含結果的 MLflow 執行 ID
#   - results.metrics: dict - 聚合指標
```

**關鍵 (CRITICAL)**: 
- `predict_fn` 接收以 kwargs 形式 **解包 (unpacked)** 的 `inputs` 字典
- 如果 `data` 有預先計算的 `outputs`，`predict_fn` 為選擇性
- 會自動為每個資料列建立追蹤 (Traces)

---

## 資料 Schema

### 評估資料集記錄

```python
# 正確格式
record = {
    "inputs": {                    # 必填 (REQUIRED) - 傳遞給 predict_fn
        "customer_name": "Acme",
        "query": "What is X?"
    },
    "outputs": {                   # 選擇性 (OPTIONAL) - 預先計算的輸出
        "response": "X is..."
    },
    "expectations": {              # 選擇性 (OPTIONAL) - 評分器的基本真值
        "expected_facts": ["fact1", "fact2"],
        "expected_response": "X is...",
        "guidelines": ["Must be concise"]
    }
}
```

**關鍵 Schema 規則**:
- `inputs` 是必填 (REQUIRED) - 包含傳遞給您應用程式的內容
- `outputs` 是選擇性 (OPTIONAL) - 如果提供，則跳過 predict_fn
- `expectations` 是選擇性 (OPTIONAL) - 由 Correctness, ExpectationsGuidelines 使用

---

## 內建評分器 (預建)

### 匯入路徑
```python
from mlflow.genai.scorers import (
    Guidelines,
    ExpectationsGuidelines,
    Correctness,
    RelevanceToQuery,
    RetrievalGroundedness,
    Safety,
)
```

### Guidelines 評分器
```python
Guidelines(
    name="my_guideline",              # 必填 (REQUIRED) - 唯一名稱
    guidelines="Response must...",     # 必填 (REQUIRED) - str 或 List[str]
    model="databricks:/endpoint-name"  # 選擇性 (OPTIONAL) - 自訂裁判模型
)

# Guidelines 自動從追蹤中提取 'request' 和 'response'
# 在準則中引用它們: "The response must address the request"
```

### ExpectationsGuidelines 評分器
```python
ExpectationsGuidelines()  # 不需要參數

# 要求每個資料列中有 expectations.guidelines:
record = {
    "inputs": {...},
    "outputs": {...},
    "expectations": {
        "guidelines": ["Must mention X", "Must not include Y"]
    }
}
```

### Correctness 評分器
```python
Correctness(
    model="databricks:/endpoint-name"  # 選擇性 (OPTIONAL)
)

# 要求 expectations.expected_facts 或 expectations.expected_response:
record = {
    "inputs": {...},
    "outputs": {...},
    "expectations": {
        "expected_facts": ["MLflow is open-source", "Manages ML lifecycle"]
        # 或
        "expected_response": "MLflow is an open-source platform..."
    }
}
```

### Safety 評分器
```python
Safety(
    model="databricks:/endpoint-name"  # 選擇性 (OPTIONAL)
)
# 不需要 expectations - 評估輸出的有害內容
```

### RelevanceToQuery 評分器
```python
RelevanceToQuery(
    model="databricks:/endpoint-name"  # 選擇性 (OPTIONAL)
)
# 檢查回應是否針對使用者的請求
```

### RetrievalGroundedness 評分器
```python
RetrievalGroundedness(
    model="databricks:/endpoint-name"  # 選擇性 (OPTIONAL)
)
# 要求: 帶有 RETRIEVER span 類型的追蹤
# 檢查回應是否基於檢索到的文件
```

---

## 自訂評分器

### 基於函數的評分器 (裝飾器)

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback

@scorer
def my_scorer(
    inputs: dict,          # 來自資料記錄
    outputs: dict,         # 應用程式輸出或預先計算結果
    expectations: dict,    # 來自資料記錄 (選擇性)
    trace: Trace = None    # 完整的 MLflow Trace 物件 (選擇性)
) -> Feedback | bool | int | float | str | list[Feedback]:
    """自訂評分器實作"""
    
    # 返回選項:
    # 1. 簡單值 (指標名稱 = 函數名稱)
    return True
    
    # 2. 帶有自訂名稱的 Feedback 物件
    return Feedback(
        name="custom_metric",
        value="yes",  # 或 "no", True/False, int, float
        rationale="Explanation of score"
    )
    
    # 3. 多個 Feedback
    return [
        Feedback(name="metric_1", value=True),
        Feedback(name="metric_2", value=0.85)
    ]
```

### 基於類別的評分器

```python
from mlflow.genai.scorers import Scorer
from mlflow.entities import Feedback
from typing import Optional

class MyScorer(Scorer):
    name: str = "my_scorer"  # 必填 (REQUIRED)
    threshold: int = 50      # 允許自訂欄位 (Pydantic)
    
    def __call__(
        self, 
        outputs: str,
        inputs: dict = None,
        expectations: dict = None,
        trace = None
    ) -> Feedback:
        if len(outputs) > self.threshold:
            return Feedback(value=True, rationale="Meets length requirement")
        return Feedback(value=False, rationale="Too short")

# 使用
my_scorer = MyScorer(threshold=100)
```

---

## 裁判 (Judges) API (低層級)

### 匯入路徑
```python
from mlflow.genai.judges import (
    meets_guidelines,
    is_correct,
    is_safe,
    is_context_relevant,
    is_grounded,
    make_judge,
)
```

### meets_guidelines()
```python
from mlflow.genai.judges import meets_guidelines

feedback = meets_guidelines(
    name="my_check",                    # 選擇性顯示名稱
    guidelines="Must be professional",   # str 或 List[str]
    context={                           # 要評估的資料字典
        "request": "user question",
        "response": "app response",
        "retrieved_documents": [...]     # 可包含任何鍵值
    },
    model="databricks:/endpoint"        # 選擇性自訂模型
)
# 返回: Feedback(value="yes"|"no", rationale="...")
```

### is_correct()
```python
from mlflow.genai.judges import is_correct

feedback = is_correct(
    request="What is MLflow?",
    response="MLflow is an open-source platform...",
    expected_facts=["MLflow is open-source"],  # 或 expected_response
    model="databricks:/endpoint"               # 選擇性
)
```

### make_judge() - 自訂 LLM 裁判
```python
from mlflow.genai.judges import make_judge

issue_judge = make_judge(
    name="issue_resolution",
    instructions="""
    Evaluate if the customer's issue was resolved.
    User's messages: {{ inputs }}
    Agent's responses: {{ outputs }}
    
    Rate and respond with exactly one of:
    - 'fully_resolved'
    - 'partially_resolved' 
    - 'needs_follow_up'
    """,
    model="databricks:/databricks-gpt-5-mini"  # 選擇性
)

# 在評估中使用
results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=my_app,
    scorers=[issue_judge]
)
```

### 基於追蹤的裁判 (帶有 {{ trace }})
```python
# 在指示中包含 {{ trace }} 啟用追蹤探索
tool_judge = make_judge(
    name="tool_correctness",
    instructions="""
    Analyze the execution {{ trace }} to determine if appropriate tools were called.
    Respond with true or false.
    """,
    model="databricks:/databricks-gpt-5-mini"  # 對於追蹤裁判是必填的
)
```

---

## 追蹤 (Trace) API

### 搜尋追蹤
```python
import mlflow

traces_df = mlflow.search_traces(
    filter_string="attributes.status = 'OK'",
    order_by=["attributes.timestamp_ms DESC"],
    max_results=100,
    run_id="optional-run-id"  # 過濾特定評估執行
)

# 常見過濾器:
# "attributes.status = 'OK'" 或 "attributes.status = 'ERROR'"
# "attributes.timestamp_ms > {milliseconds}"
# "attributes.execution_time_ms > 5000"
# "tags.environment = 'production'"
# "tags.`mlflow.traceName` = 'my_function'"
```

### 追蹤物件存取
```python
from mlflow.entities import Trace, SpanType

@scorer
def trace_scorer(trace: Trace) -> Feedback:
    # 依類型搜尋 spans
    llm_spans = trace.search_spans(span_type=SpanType.CHAT_MODEL)
    retriever_spans = trace.search_spans(span_type=SpanType.RETRIEVER)
    
    # 存取 span 資料
    for span in llm_spans:
        duration = (span.end_time_ns - span.start_time_ns) / 1e9
        inputs = span.inputs
        outputs = span.outputs
```

---

## 評估資料集 (MLflow 託管)

### 建立資料集
```python
import mlflow.genai.datasets
from databricks.connect import DatabricksSession

# MLflow 託管資料集需要 Spark
spark = DatabricksSession.builder.remote(serverless=True).getOrCreate()

eval_dataset = mlflow.genai.datasets.create_dataset(
    uc_table_name="catalog.schema.my_eval_dataset"
)
```

### 加入記錄
```python
# 從字典列表
records = [
    {"inputs": {"query": "..."}, "expectations": {"expected_facts": [...]}},
]
eval_dataset.merge_records(records)

# 從追蹤
traces_df = mlflow.search_traces(filter_string="...")
eval_dataset.merge_records(traces_df)
```

### 在評估中使用
```python
results = mlflow.genai.evaluate(
    data=eval_dataset,  # 直接傳遞資料集物件
    predict_fn=my_app,
    scorers=[...]
)
```

---

## 生產監控

### 註冊並啟動評分器
```python
from mlflow.genai.scorers import Safety, Guidelines, ScorerSamplingConfig

# 註冊評分器到實驗
safety = Safety().register(name="safety_monitor")

# 啟動監控與取樣率
safety = safety.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.5)  # 50% 的追蹤
)
```

### 管理評分器
```python
from mlflow.genai.scorers import list_scorers, get_scorer, delete_scorer

# 列出所有註冊的評分器
scorers = list_scorers()

# 獲取特定評分器
my_scorer = get_scorer(name="safety_monitor")

# 更新取樣率
my_scorer = my_scorer.update(
    sampling_config=ScorerSamplingConfig(sample_rate=0.8)
)

# 停止監控 (保留註冊)
my_scorer = my_scorer.stop()

# 完全刪除
delete_scorer(name="safety_monitor")
```

---

## 關鍵常數

### Span 類型
```python
from mlflow.entities import SpanType

SpanType.CHAT_MODEL      # LLM 呼叫
SpanType.RETRIEVER       # RAG 檢索
SpanType.TOOL            # 工具/函數呼叫
SpanType.AGENT           # 代理執行
SpanType.CHAIN           # 鏈執行
```

### Feedback 值
```python
# LLM 裁判通常返回:
"yes" | "no"     # 用於通過/失敗評估

# 自訂評分器可以返回:
True | False     # 布林值
0.0 - 1.0        # 浮點分數
int              # 整數分數
str              # 分類值
```

---

## 安裝

```bash
pip install --upgrade "mlflow[databricks]>=3.1.0" openai
```

## 設定

```python
import mlflow

# 啟用自動追蹤
mlflow.openai.autolog()  # 或 mlflow.langchain.autolog() 等

# 設定追蹤 URI
mlflow.set_tracking_uri("databricks")

# 設定實驗
mlflow.set_experiment("/Shared/my-experiment")
```
