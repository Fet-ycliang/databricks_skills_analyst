# MLflow 3 GenAI - 陷阱與常見錯誤 (GOTCHAS & Common Mistakes)

**關鍵 (CRITICAL)**: 在撰寫任何評估程式碼之前請先閱讀此文。這些是導致失敗的最常見錯誤。

## 目錄

- [在開發中使用 Model Serving 端點 (錯誤)](#-錯誤-在開發中使用-model-serving-端點)
- [錯誤的 API 匯入](#-錯誤的-api-匯入)
- [錯誤的 Evaluate 函數](#-錯誤的-evaluate-函數)
- [錯誤的資料格式](#-錯誤的-資料格式)
- [錯誤的 predict_fn 簽章](#-錯誤的-predict_fn-簽章)
- [錯誤的評分器裝飾器用法](#-錯誤的-評分器裝飾器用法)
- [錯誤的 Feedback 返回](#-錯誤的-feedback-返回)
- [錯誤的 Guidelines 評分器設定](#-錯誤的-guidelines-評分器設定)
- [錯誤的追蹤搜尋語法](#-錯誤的-追蹤搜尋語法)
- [錯誤的 Expectations 用法](#-錯誤的-expectations-用法)
- [錯誤的 RetrievalGroundedness 用法](#-錯誤的-retrievalgroundedness-用法)
- [錯誤的自訂評分器匯入](#-錯誤的-自訂評分器匯入)
- [評分器中錯誤的類型提示](#-評分器中錯誤的類型提示)
- [錯誤的資料集建立](#-錯誤的-資料集建立)
- [錯誤的多重 Feedback 名稱](#-錯誤的-多重-feedback-名稱)
- [錯誤的 Guidelines 上下文引用](#-錯誤的-guidelines-上下文引用)
- [錯誤的生產監控設定](#-錯誤的-生產監控設定)
- [錯誤的自訂裁判模型格式](#-錯誤的自訂裁判模型格式)
- [錯誤的聚合值](#-錯誤的-聚合值)
- [總結檢查表](#總結檢查表)

---

## ❌ 錯誤：在開發中使用 Model Serving 端點

### 錯誤：呼叫已部署的端點進行初始測試
```python
# ❌ 錯誤 - 開發期間不要使用 Model Serving 端點
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
client = w.serving_endpoints.get_open_ai_client()

def predict_fn(messages):
    response = client.chat.completions.create(
        model="my-agent-endpoint",  # Deployed endpoint
        messages=messages
    )
    return {"response": response.choices[0].message.content}
```

### ✅ 正確：在本地匯入並測試代理
```python
# ✅ 正確 - 直接匯入代理以進行快速迭代
from plan_execute_agent import AGENT  # 您的本地代理模組

def predict_fn(messages):
    result = AGENT.predict({"messages": messages})
    # 從 ResponsesAgent 格式提取回應
    if isinstance(result, dict) and "messages" in result:
        for msg in reversed(result["messages"]):
            if msg.get("role") == "assistant":
                return {"response": msg.get("content", "")}
    return {"response": str(result)}
```

**為什麼？**
- 本地測試可加快迭代速度（無需部署）
- 完整的堆疊追蹤便於除錯
- 無服務端點成本
- 直接存取代理內部

**何時使用端點**：僅用於生產監控、負載測試或已部署版本的 A/B 測試。

---

## ❌ 錯誤的 API 匯入

### 錯誤：使用舊的 MLflow 2 匯入
```python
# ❌ 錯誤 - 這些在 MLflow 3 GenAI 中不存在
from mlflow.evaluate import evaluate
from mlflow.metrics import genai
import mlflow.llm
```

### ✅ 正確：MLflow 3 GenAI 匯入
```python
# ✅ 正確
import mlflow.genai
from mlflow.genai.scorers import Guidelines, Safety, Correctness, scorer
from mlflow.genai.judges import meets_guidelines, is_correct, make_judge
from mlflow.entities import Feedback, Trace
```

---

## ❌ 錯誤的 EVALUATE 函數

### 錯誤：使用 mlflow.evaluate()
```python
# ❌ 錯誤 - 這是用於經典 ML 的舊 API
results = mlflow.evaluate(
    model=my_model,
    data=eval_data,
    model_type="text"
)
```

### ✅ 正確：使用 mlflow.genai.evaluate()
```python
# ✅ 正確 - MLflow 3 GenAI 評估
results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=my_app,
    scorers=[Guidelines(name="test", guidelines="...")]
)
```

---

## ❌ 錯誤的資料格式

### 錯誤：扁平的資料結構
```python
# ❌ 錯誤 - 缺少巢狀結構
eval_data = [
    {"query": "What is X?", "expected": "X is..."}
]
```

### ✅ 正確：適當的巢狀結構
```python
# ✅ 正確 - 必須有 'inputs' 鍵
eval_data = [
    {
        "inputs": {"query": "What is X?"},
        "expectations": {"expected_response": "X is..."}
    }
]
```

---

## ❌ 錯誤的 predict_fn 簽章

### 錯誤：函數期望字典
```python
# ❌ 錯誤 - predict_fn 接收 **unpacked inputs
def my_app(inputs):  # 接收字典
    query = inputs["query"]
    return {"response": "..."}
```

### ✅ 正確：函數接收關鍵字參數
```python
# ✅ 正確 - inputs 被解包為 kwargs
def my_app(query, context=None):  # 接收個別鍵值
    return {"response": f"Answer to {query}"}

# 如果 inputs = {"query": "What is X?", "context": "..."}
# 則 my_app 被呼叫為: my_app(query="What is X?", context="...")
```

---

## ❌ 錯誤的評分器裝飾器用法

### 錯誤：缺少裝飾器
```python
# ❌ 錯誤 - 這將無法作為評分器運作
def my_scorer(inputs, outputs):
    return True
```

### ✅ 正確：使用 @scorer 裝飾器
```python
# ✅ 正確
from mlflow.genai.scorers import scorer

@scorer
def my_scorer(inputs, outputs):
    return True
```

---

## ❌ 錯誤的 FEEDBACK 返回

### 錯誤：返回錯誤的類型
```python
@scorer
def bad_scorer(outputs):
    # ❌ 錯誤 - 不能返回字典
    return {"score": 0.5, "reason": "..."}
    
    # ❌ 錯誤 - 不能返回元組
    return (True, "rationale")
```

### ✅ 正確：返回 Feedback 或基本類型
```python
from mlflow.entities import Feedback

@scorer
def good_scorer(outputs):
    # ✅ 正確 - 返回基本類型
    return True
    return 0.85
    return "yes"
    
    # ✅ 正確 - 返回 Feedback 物件
    return Feedback(
        value=True,
        rationale="Explanation"
    )
    
    # ✅ 正確 - 返回 Feedback 列表
    return [
        Feedback(name="metric_1", value=True),
        Feedback(name="metric_2", value=0.9)
    ]
```

---

## ❌ 錯誤的 GUIDELINES 評分器設定

### 錯誤：缺少必要的參數
```python
# ❌ 錯誤 - 缺少 'name' 參數
scorer = Guidelines(guidelines="Must be professional")
```

### ✅ 正確：包含 name 和 guidelines
```python
# ✅ 正確
scorer = Guidelines(
    name="professional_tone",  # 必填 (REQUIRED)
    guidelines="The response must be professional"  # 必填 (REQUIRED)
)
```

---

## ❌ 錯誤的追蹤搜尋語法

### 錯誤：缺少前綴和錯誤引號
```python
# ❌ 錯誤 - 缺少前綴
mlflow.search_traces("status = 'OK'")

# ❌ 錯誤 - 使用雙引號
mlflow.search_traces('attributes.status = "OK"')

# ❌ 錯誤 - 點號名稱缺少反引號
mlflow.search_traces("tags.mlflow.traceName = 'my_app'")

# ❌ 錯誤 - 使用 OR (不支援)
mlflow.search_traces("attributes.status = 'OK' OR attributes.status = 'ERROR'")
```

### ✅ 正確：適當的過濾語法
```python
# ✅ 正確 - 使用前綴和單引號
mlflow.search_traces("attributes.status = 'OK'")

# ✅ 正確 - 點號名稱使用反引號
mlflow.search_traces("tags.`mlflow.traceName` = 'my_app'")

# ✅ 正確 - 支援 AND
mlflow.search_traces("attributes.status = 'OK' AND tags.env = 'prod'")

# ✅ 正確 - 時間以毫秒為單位
import time
cutoff = int((time.time() - 3600) * 1000)  # 1 小時前
mlflow.search_traces(f"attributes.timestamp_ms > {cutoff}")
```

---

## ❌ 錯誤的 EXPECTATIONS 用法

### 錯誤：使用 Correctness 但無 expectations
```python
# ❌ 錯誤 - Correctness 需要 expected_facts 或 expected_response
eval_data = [
    {"inputs": {"query": "What is X?"}}
]
results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=[Correctness()]  # 會失敗 - 無基本真值！
)
```

### ✅ 正確：為 Correctness 包含 expectations
```python
# ✅ 正確
eval_data = [
    {
        "inputs": {"query": "What is X?"},
        "expectations": {
            "expected_facts": ["X is a platform", "X is open-source"]
        }
    }
]
```

---

## ❌ 錯誤的 RetrievalGroundedness 用法

### 錯誤：使用時無 RETRIEVER span
```python
# ❌ 錯誤 - App 沒有 RETRIEVER span 類型
@mlflow.trace
def my_rag_app(query):
    docs = get_documents(query)  # 未標記為 retriever
    return generate_response(docs, query)

# RetrievalGroundedness 會失敗 - 找不到 retriever spans
```

### ✅ 正確：使用適當的 span 類型標記檢索
```python
# ✅ 正確 - 使用 span_type="RETRIEVER"
@mlflow.trace(span_type="RETRIEVER")
def retrieve_documents(query):
    return [doc1, doc2]

@mlflow.trace
def my_rag_app(query):
    docs = retrieve_documents(query)  # 現在有 RETRIEVER span
    return generate_response(docs, query)
```

---

## ❌ 錯誤的自訂評分器匯入

### 錯誤：模組層級的外部匯入
```python
# ❌ 錯誤 - 對於生產監控，外部匯入位於函數外
import my_custom_library

@scorer
def production_scorer(outputs):
    return my_custom_library.process(outputs)
```

### ✅ 正確：生產評分器的行內匯入
```python
# ✅ 正確 - 在函數內匯入以進行序列化
@scorer
def production_scorer(outputs):
    import json  # 用於生產監控，匯入在內部
    return len(json.dumps(outputs)) > 100
```

---

## ❌ 評分器中錯誤的類型提示

### 錯誤：簽章中需要匯入的類型提示
```python
# ❌ 錯誤 - 類型提示破壞生產監控的序列化
from typing import List

@scorer
def bad_scorer(outputs: List[str]) -> bool:
    return True
```

### ✅ 正確：避免複雜的類型提示或使用 dict
```python
# ✅ 正確 - 簡單類型可行
@scorer
def good_scorer(outputs):
    return True

# ✅ 正確 - dict 是可以的
@scorer
def good_scorer(outputs: dict) -> bool:
    return True
```

---

## ❌ 錯誤的資料集建立

### 錯誤：MLflow 資料集缺少 Spark session
```python
# ❌ 錯誤 - MLflow 託管資料集需要 Spark
import mlflow.genai.datasets

dataset = mlflow.genai.datasets.create_dataset(
    uc_table_name="catalog.schema.my_dataset"
)
# 錯誤: 無可用的 Spark session
```

### ✅ 正確：先初始化 Spark
```python
# ✅ 正確
from databricks.connect import DatabricksSession

spark = DatabricksSession.builder.remote(serverless=True).getOrCreate()

dataset = mlflow.genai.datasets.create_dataset(
    uc_table_name="catalog.schema.my_dataset"
)
```

---

## ❌ 錯誤的多重 Feedback 名稱

### 錯誤：多重 feedbacks 無唯一名稱
```python
@scorer
def bad_multi_scorer(outputs):
    # ❌ 錯誤 - Feedbacks 會衝突
    return [
        Feedback(value=True),
        Feedback(value=0.8)
    ]
```

### ✅ 正確：為每個 Feedback 使用唯一名稱
```python
@scorer
def good_multi_scorer(outputs):
    # ✅ 正確 - 每個都有唯一名稱
    return [
        Feedback(name="check_1", value=True),
        Feedback(name="check_2", value=0.8)
    ]
```

---

## ❌ 錯誤的 Guidelines 上下文引用

### 錯誤：準則中使用錯誤的變數名稱
```python
# ❌ 錯誤 - Guidelines 使用 'request' 和 'response'，而非自訂鍵值
Guidelines(
    name="check",
    guidelines="The output must address the query"  # 'output' 和 'query' 不可用
)
```

### ✅ 正確：使用 'request' 和 'response'
```python
# ✅ 正確 - 這些是自動提取的
Guidelines(
    name="check",
    guidelines="The response must address the request"
)
```

---

## ❌ 錯誤的生產監控設定

### 錯誤：註冊後忘記啟動
```python
# ❌ 錯誤 - 已註冊但未啟動
from mlflow.genai.scorers import Safety

safety = Safety().register(name="safety_check")
# 評分器存在但未執行！
```

### ✅ 正確：註冊然後啟動
```python
# ✅ 正確 - 同時註冊和啟動
from mlflow.genai.scorers import Safety, ScorerSamplingConfig

safety = Safety().register(name="safety_check")
safety = safety.start(
    sampling_config=ScorerSamplingConfig(sample_rate=0.5)
)
```

---

## ❌ 錯誤的自訂裁判模型格式

### 錯誤：錯誤的模型格式
```python
# ❌ 錯誤 - 缺少提供者前綴
Guidelines(name="test", guidelines="...", model="gpt-4o")

# ❌ 錯誤 - 錯誤的分隔符
Guidelines(name="test", guidelines="...", model="databricks:gpt-4o")
```

### ✅ 正確：使用 provider:/model 格式
```python
# ✅ 正確 - 使用 :/ 分隔符
Guidelines(name="test", guidelines="...", model="databricks:/my-endpoint")
Guidelines(name="test", guidelines="...", model="openai:/gpt-4o")
```

---

## ❌ 錯誤的聚合值

### 錯誤：無效的聚合名稱
```python
# ❌ 錯誤 - p50, p99, sum 不是有效的
@scorer(aggregations=["mean", "p50", "p99", "sum"])
def my_scorer(outputs) -> float:
    return 0.5
```

### ✅ 正確：使用有效的聚合名稱
```python
# ✅ 正確 - 只有這 6 個是有效的
@scorer(aggregations=["min", "max", "mean", "median", "variance", "p90"])
def my_scorer(outputs) -> float:
    return 0.5
```

**有效的聚合:**
- `min` - 最小值
- `max` - 最大值
- `mean` - 平均值
- `median` - 第 50 百分位數 (不是 `p50`)
- `variance` - 統計變異數
- `p90` - 第 90 百分位數 (只有 p90，不是 p50 或 p99)

---

## 總結檢查表

執行評估前，請驗證：

- [ ] 使用 `mlflow.genai.evaluate()` (不是 `mlflow.evaluate()`)
- [ ] 資料有 `inputs` 鍵 (巢狀結構)
- [ ] `predict_fn` 接收 **unpacked kwargs (不是字典)
- [ ] 評分器有 `@scorer` 裝飾器
- [ ] Guidelines 同時有 `name` 和 `guidelines`
- [ ] Correctness 有 `expectations.expected_facts` 或 `expected_response`
- [ ] RetrievalGroundedness 在已追蹤中有 `RETRIEVER` span
- [ ] 追蹤過濾器使用 `attributes.` 前綴和單引號
- [ ] 生產評分器有行內匯入
- [ ] 多個 Feedbacks 有唯一名稱
- [ ] 聚合使用有效名稱：min, max, mean, median, variance, p90
