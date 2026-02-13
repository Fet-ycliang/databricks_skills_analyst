# MLflow 3 評分器模式 (MLflow 3 Scorer Patterns)

在 MLflow 3 GenAI 中建立和使用評分器的工作程式碼模式。

## 目錄

| # | 模式 | 描述 |
|---|---------|-------------|
| 1 | [內建 Guidelines 評分器](#模式-1-內建-guidelines-評分器) | 自然語言標準評估 |
| 2 | [帶有基本真值的 Correctness](#模式-2-帶有基本真值的-correctness-評分器) | 預期答案/事實驗證 |
| 3 | [帶有 RetrievalGroundedness 的 RAG](#模式-3-帶有-retrievalgroundedness-的-rag-評估) | 檢查回應是否基於上下文 |
| 4 | [簡單自訂評分器 (布林值)](#模式-4-簡單自訂評分器-布林值) | 通過/失敗檢查 |
| 5 | [帶有 Feedback 的自訂評分器](#模式-5-帶有-feedback-物件的自訂評分器) | 返回基本原理和自訂名稱 |
| 6 | [多指標評分器](#模式-6-帶有多指標的自訂評分器) | 一個評分器，多個指標 |
| 7 | [包裝 LLM 裁判](#模式-7-包裝-llm-裁判的自訂評分器) | 內建裁判的自訂上下文 |
| 8 | [基於追蹤的評分器](#模式-8-基於追蹤的評分器) | 分析執行細節 |
| 9 | [基於類別的評分器](#模式-9-帶有配置的基於類別的評分器) | 可配置/有狀態的評分器 |
| 10 | [條件式評分](#模式-10-基於輸入的條件式評分) | 每個輸入類型有不同規則 |
| 11 | [聚合](#模式-11-帶有聚合的評分器) | 數值統計 (平均值, 中位數, p90) |
| 12 | [自訂建立裁判](#模式-12-自訂建立裁判-make-judge) | 複雜的多層級評估 |
| 13 | [每階段準確率](#模式-13-每階段元件準確率評分器) | 多代理元件驗證 |
| 14 | [工具選擇準確率](#模式-14-工具選擇準確率評分器) | 驗證呼叫了正確的工具 |
| 15 | [階段延遲評分器](#模式-15-階段延遲評分器-多指標) | 每個階段的延遲指標 |
| 16 | [元件準確率工廠](#模式-16-元件準確率工廠) | 可重用的評分器工廠 |

---

## 模式 1：內建 Guidelines 評分器

用於根據自然語言標準進行評估。

```python
from mlflow.genai.scorers import Guidelines
import mlflow

# 單一準則
tone_scorer = Guidelines(
    name="professional_tone",
    guidelines="The response must maintain a professional, helpful tone throughout"
)

# 多個準則 (一起評估)
quality_scorer = Guidelines(
    name="response_quality",
    guidelines=[
        "The response must be concise and under 200 words",
        "The response must directly address the user's question",
        "The response must not include made-up information"
    ]
)

# 帶有自訂裁判模型
custom_scorer = Guidelines(
    name="custom_check",
    guidelines="Response must follow company policy",
    model="databricks:/databricks-gpt-oss-120b"
)

# 在評估中使用
results = mlflow.genai.evaluate(
    data=eval_dataset,
    predict_fn=my_app,
    scorers=[tone_scorer, quality_scorer]
)
```

---

## 模式 2：帶有基本真值的 Correctness 評分器

當您有預期答案或事實時使用。

```python
from mlflow.genai.scorers import Correctness

# 帶有預期事實的資料集
eval_data = [
    {
        "inputs": {"question": "What is MLflow?"},
        "expectations": {
            "expected_facts": [
                "MLflow is open-source",
                "MLflow manages the ML lifecycle",
                "MLflow includes experiment tracking"
            ]
        }
    },
    {
        "inputs": {"question": "Who created MLflow?"},
        "expectations": {
            "expected_response": "MLflow was created by Databricks and released in June 2018."
        }
    }
]

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=[Correctness()]
)
```

---

## 模式 3：帶有 RetrievalGroundedness 的 RAG 評估

用於 RAG 應用程式，檢查回應是否基於檢索到的上下文。

```python
from mlflow.genai.scorers import RetrievalGroundedness, RelevanceToQuery
import mlflow
from mlflow.entities import Document

# 應用程式必須有 RETRIEVER span 類型
@mlflow.trace(span_type="RETRIEVER")
def retrieve_docs(query: str) -> list[Document]:
    """Retrieval function marked with RETRIEVER span type."""
    # 您的檢索邏輯
    return [
        Document(
            id="doc1",
            page_content="Retrieved content here...",
            metadata={"source": "knowledge_base"}
        )
    ]

@mlflow.trace
def rag_app(query: str):
    docs = retrieve_docs(query)
    context = "\n".join([d.page_content for d in docs])
    
    response = generate_response(query, context)
    return {"response": response}

# 使用 RAG 特定評分器進行評估
results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=rag_app,
    scorers=[
        RetrievalGroundedness(),  # 檢查回應與檢索文件的關係
        RelevanceToQuery(),        # 檢查回應是否針對查詢
    ]
)
```

---

## 模式 4：簡單自訂評分器 (布林值)

用於簡單的通過/失敗檢查。

```python
from mlflow.genai.scorers import scorer

@scorer
def contains_greeting(outputs):
    """檢查回應是否包含問候。"""
    response = outputs.get("response", "").lower()
    greetings = ["hello", "hi", "hey", "greetings"]
    return any(g in response for g in greetings)

@scorer
def response_not_empty(outputs):
    """檢查回應是否不為空。"""
    return len(str(outputs.get("response", ""))) > 0

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=[contains_greeting, response_not_empty]
)
```

---

## 模式 5：帶有 Feedback 物件的自訂評分器

當您需要基本原理或自訂名稱時使用。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback

@scorer
def response_length_check(outputs):
    """檢查回應長度是否適當。"""
    response = str(outputs.get("response", ""))
    word_count = len(response.split())
    
    if word_count < 10:
        return Feedback(
            value="no",
            rationale=f"Response too short: {word_count} words (minimum 10)"
        )
    elif word_count > 500:
        return Feedback(
            value="no", 
            rationale=f"Response too long: {word_count} words (maximum 500)"
        )
    else:
        return Feedback(
            value="yes",
            rationale=f"Response length acceptable: {word_count} words"
        )
```

---

## 模式 6：帶有多指標的自訂評分器

當一個評分器應該產生多個指標時使用。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback

@scorer
def comprehensive_check(inputs, outputs):
    """從一個評分器返回多個指標。"""
    response = str(outputs.get("response", ""))
    query = inputs.get("query", "")
    
    feedbacks = []
    
    # 檢查 1：回應存在
    feedbacks.append(Feedback(
        name="has_response",
        value=len(response) > 0,
        rationale="Response is present" if response else "No response"
    ))
    
    # 檢查 2：字數統計
    word_count = len(response.split())
    feedbacks.append(Feedback(
        name="word_count",
        value=word_count,
        rationale=f"Response contains {word_count} words"
    ))
    
    # 檢查 3：回應中的查詢術語
    query_terms = set(query.lower().split())
    response_terms = set(response.lower().split())
    overlap = len(query_terms & response_terms) / len(query_terms) if query_terms else 0
    feedbacks.append(Feedback(
        name="query_coverage",
        value=round(overlap, 2),
        rationale=f"{overlap*100:.0f}% of query terms found in response"
    ))
    
    return feedbacks
```

---

## 模式 7：包裝 LLM 裁判的自訂評分器

當您需要為內建裁判提供自訂上下文時使用。

```python
from mlflow.genai.scorers import scorer
from mlflow.genai.judges import meets_guidelines

@scorer
def custom_grounding_check(inputs, outputs, trace=None):
    """使用自訂上下文提取檢查回應是否有依據。"""
    
    # 從 inputs/outputs 提取您需要的內容
    query = inputs.get("query", "")
    response = outputs.get("response", "")
    
    # 從 outputs 獲取檢索到的文件 (或從 trace 提取)
    retrieved_docs = outputs.get("retrieved_documents", [])
    
    # 使用自訂上下文呼叫裁判
    return meets_guidelines(
        name="factual_grounding",
        guidelines=[
            "The response must only use facts from retrieved_documents",
            "The response must not make claims not supported by retrieved_documents"
        ],
        context={
            "request": query,
            "response": response,
            "retrieved_documents": retrieved_docs
        }
    )
```

---

## 模式 8：基於追蹤的評分器

當您需要分析執行細節時使用。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback, Trace, SpanType

@scorer
def llm_latency_check(trace: Trace) -> Feedback:
    """檢查 LLM 回應時間是否可接受。"""
    
    # 在追蹤中尋找 LLM spans
    llm_spans = trace.search_spans(span_type=SpanType.CHAT_MODEL)
    
    if not llm_spans:
        return Feedback(
            value="no",
            rationale="No LLM calls found in trace"
        )
    
    # 計算總 LLM 時間
    total_llm_time = 0
    for span in llm_spans:
        duration = (span.end_time_ns - span.start_time_ns) / 1e9
        total_llm_time += duration
    
    max_acceptable = 5.0  # 秒
    
    if total_llm_time <= max_acceptable:
        return Feedback(
            value="yes",
            rationale=f"LLM latency {total_llm_time:.2f}s within {max_acceptable}s limit"
        )
    else:
        return Feedback(
            value="no",
            rationale=f"LLM latency {total_llm_time:.2f}s exceeds {max_acceptable}s limit"
        )

@scorer  
def tool_usage_check(trace: Trace) -> Feedback:
    """檢查是否呼叫了適當的工具。"""
    
    tool_spans = trace.search_spans(span_type=SpanType.TOOL)
    
    tool_names = [span.name for span in tool_spans]
    
    return Feedback(
        value=len(tool_spans) > 0,
        rationale=f"Tools called: {tool_names}" if tool_names else "No tools called"
    )
```

---

## 模式 9：帶有配置的基於類別的評分器

當評分器需要持久狀態或配置時使用。

```python
from mlflow.genai.scorers import Scorer
from mlflow.entities import Feedback
from typing import Optional, List

class KeywordRequirementScorer(Scorer):
    """檢查必要關鍵字的特定配置評分器。"""
    
    name: str = "keyword_requirement"
    required_keywords: List[str] = []
    case_sensitive: bool = False
    
    def __call__(self, outputs) -> Feedback:
        response = str(outputs.get("response", ""))
        
        if not self.case_sensitive:
            response = response.lower()
            keywords = [k.lower() for k in self.required_keywords]
        else:
            keywords = self.required_keywords
        
        missing = [k for k in keywords if k not in response]
        
        if not missing:
            return Feedback(
                value="yes",
                rationale=f"All required keywords present: {self.required_keywords}"
            )
        else:
            return Feedback(
                value="no",
                rationale=f"Missing keywords: {missing}"
            )

# 使用不同的配置
product_scorer = KeywordRequirementScorer(
    name="product_mentions",
    required_keywords=["MLflow", "Databricks"],
    case_sensitive=False
)

compliance_scorer = KeywordRequirementScorer(
    name="compliance_terms",
    required_keywords=["Terms of Service", "Privacy Policy"],
    case_sensitive=True
)

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=[product_scorer, compliance_scorer]
)
```

---

## 模式 10：基於輸入的條件式評分

當不同的輸入需要不同的評估時使用。

```python
from mlflow.genai.scorers import scorer, Guidelines

@scorer
def conditional_scorer(inputs, outputs):
    """根據查詢類型應用不同的準則。"""
    
    query = inputs.get("query", "").lower()
    
    if "technical" in query or "how to" in query:
        # 技術查詢需要詳細的回應
        judge = Guidelines(
            name="technical_quality",
            guidelines=[
                "Response must include step-by-step instructions",
                "Response must include code examples where relevant"
            ]
        )
    elif "price" in query or "cost" in query:
        # 定價查詢需要特定資訊
        judge = Guidelines(
            name="pricing_quality",
            guidelines=[
                "Response must include specific pricing information",
                "Response must mention any conditions or limitations"
            ]
        )
    else:
        # 一般查詢
        judge = Guidelines(
            name="general_quality",
            guidelines=[
                "Response must directly address the question",
                "Response must be clear and concise"
            ]
        )
    
    return judge(inputs=inputs, outputs=outputs)
```

---

## 模式 11：帶有聚合的評分器

用於需要聚合統計的數值評分器。

```python
from mlflow.genai.scorers import scorer

@scorer(aggregations=["mean", "min", "max", "median", "p90"])
def response_latency(outputs) -> float:
    """返回回應生成時間。"""
    return outputs.get("latency_ms", 0) / 1000.0  # 轉換為秒

@scorer(aggregations=["mean", "min", "max"])
def token_count(outputs) -> int:
    """返回回應中的 Token 數量。"""
    response = str(outputs.get("response", ""))
    # 粗略的 Token 估計
    return len(response.split())

# 有效的聚合: min, max, mean, median, variance, p90
# 注意: p50, p99, sum 不是有效的 - 使用 median 代替 p50
```

---

## 模式 12：自訂建立裁判 (make_judge)

用於帶有自訂指令的複雜多層級評估。

```python
from mlflow.genai.judges import make_judge

# 帶有多種結果的問題解決裁判
resolution_judge = make_judge(
    name="issue_resolution",
    instructions="""
    Evaluate if the customer's issue was resolved.
    
    User's messages: {{ inputs }}
    Agent's responses: {{ outputs }}
    
    Assess the resolution status and respond with exactly one of:
    - 'fully_resolved': Issue completely addressed with clear solution
    - 'partially_resolved': Some help provided but not fully solved  
    - 'needs_follow_up': Issue not adequately addressed
    
    Your response must be exactly one of these three values.
    """,
    model="databricks:/databricks-gpt-5-mini"  # 選擇性
)

# 在評估中使用
results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=support_agent,
    scorers=[resolution_judge]
)
```

---

## 組合多種評分器類型

```python
from mlflow.genai.scorers import (
    Guidelines, Safety, Correctness,
    RelevanceToQuery, scorer
)
from mlflow.entities import Feedback

# 內建評分器
safety = Safety()
relevance = RelevanceToQuery()

# Guidelines 評分器
tone = Guidelines(name="tone", guidelines="Must be professional")
format_check = Guidelines(name="format", guidelines="Must use bullet points for lists")

# 自訂程式碼評分器
@scorer
def has_cta(outputs):
    """檢查是否有行動呼籲 (call-to-action)。"""
    response = outputs.get("response", "").lower()
    ctas = ["contact us", "learn more", "get started", "sign up"]
    return any(cta in response for cta in ctas)

# 組合所有
results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=[
        safety,
        relevance,
        tone,
        format_check,
        has_cta
    ]
)
```

---

## 模式 13：每階段/元件準確率評分器

用於多代理或多階段管線，以驗證每個元件是否正確運作。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback, Trace
from typing import Dict, Any

@scorer
def classifier_accuracy(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    expectations: Dict[str, Any],
    trace: Trace
) -> Feedback:
    """檢查分類器是否正確識別了查詢類型。"""

    expected_type = expectations.get("expected_query_type")

    if expected_type is None:
        return Feedback(
            name="classifier_accuracy",
            value="skip",
            rationale="No expected_query_type in expectations"
        )

    # 依名稱模式在追蹤中尋找分類器 span
    classifier_spans = [
        span for span in trace.search_spans()
        if "classifier" in span.name.lower()
    ]

    if not classifier_spans:
        return Feedback(
            name="classifier_accuracy",
            value="no",
            rationale="No classifier span found in trace"
        )

    # 從 span 輸出中提取實際值
    span_outputs = classifier_spans[0].outputs or {}
    actual_type = span_outputs.get("query_type") if isinstance(span_outputs, dict) else None

    if actual_type is None:
        return Feedback(
            name="classifier_accuracy",
            value="no",
            rationale=f"No query_type in classifier outputs"
        )

    is_correct = actual_type == expected_type

    return Feedback(
        name="classifier_accuracy",
        value="yes" if is_correct else "no",
        rationale=f"Expected '{expected_type}', got '{actual_type}'"
    )
```

---

## 模式 14：工具選擇準確率評分器

檢查在代理執行期間是否呼叫了正確的工具。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback, Trace, SpanType
from typing import Dict, Any, List

@scorer
def tool_selection_accuracy(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    expectations: Dict[str, Any],
    trace: Trace
) -> Feedback:
    """檢查是否呼叫了正確的工具。"""

    expected_tools = expectations.get("expected_tools", [])

    if not expected_tools:
        return Feedback(
            name="tool_selection_accuracy",
            value="skip",
            rationale="No expected_tools in expectations"
        )

    # 從 TOOL spans 獲取實際工具呼叫
    tool_spans = trace.search_spans(span_type=SpanType.TOOL)
    actual_tools = {span.name for span in tool_spans}

    # 正規化名稱 (處理如 "catalog.schema.func" 的全限定名稱)
    def normalize(name: str) -> str:
        return name.split(".")[-1] if "." in name else name

    expected_normalized = {normalize(t) for t in expected_tools}
    actual_normalized = {normalize(t) for t in actual_tools}

    # 檢查是否呼叫了所有預期的工具
    missing = expected_normalized - actual_normalized
    extra = actual_normalized - expected_normalized

    all_expected_called = len(missing) == 0

    rationale = f"Expected: {list(expected_normalized)}, Actual: {list(actual_normalized)}"
    if missing:
        rationale += f" | Missing: {list(missing)}"

    return Feedback(
        name="tool_selection_accuracy",
        value="yes" if all_expected_called else "no",
        rationale=rationale
    )
```

---

## 模式 15：階段延遲評分器 (多指標)

測量每個管線階段的延遲並識別瓶頸。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback, Trace
from typing import List

@scorer
def stage_latency_scorer(trace: Trace) -> List[Feedback]:
    """測量每個管線階段的延遲。"""

    feedbacks = []
    all_spans = trace.search_spans()

    # 總追蹤時間
    root_spans = [s for s in all_spans if s.parent_id is None]
    if root_spans:
        root = root_spans[0]
        total_ms = (root.end_time_ns - root.start_time_ns) / 1e6
        feedbacks.append(Feedback(
            name="total_latency_ms",
            value=round(total_ms, 2),
            rationale=f"Total execution time: {total_ms:.2f}ms"
        ))

    # 每階段延遲 (為您的管線自訂模式)
    stage_patterns = ["classifier", "rewriter", "executor", "retriever"]
    stage_times = {}

    for span in all_spans:
        span_name_lower = span.name.lower()
        for pattern in stage_patterns:
            if pattern in span_name_lower:
                duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6
                stage_times[pattern] = stage_times.get(pattern, 0) + duration_ms
                break

    for stage, time_ms in stage_times.items():
        feedbacks.append(Feedback(
            name=f"{stage}_latency_ms",
            value=round(time_ms, 2),
            rationale=f"Stage '{stage}' took {time_ms:.2f}ms"
        ))

    # 識別瓶頸
    if stage_times:
        bottleneck = max(stage_times, key=stage_times.get)
        feedbacks.append(Feedback(
            name="bottleneck_stage",
            value=bottleneck,
            rationale=f"Slowest stage: '{bottleneck}' at {stage_times[bottleneck]:.2f}ms"
        ))

    return feedbacks
```

---

## 模式 16：元件準確率工廠

為任何元件/欄位組合建立可重用的評分器。

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback, Trace
from typing import Dict, Any

def component_accuracy(
    component_name: str,
    output_field: str,
    expected_key: str = None
):
    """元件特定準確率評分器的工廠。

    Args:
        component_name: 匹配 span 名稱的模式 (例如 "classifier")
        output_field: span 輸出中要檢查的欄位 (例如 "query_type")
        expected_key: expectations 中的鍵 (預設為 f"expected_{output_field}")

    Example:
        router_accuracy = component_accuracy("router", "route", "expected_route")
    """
    if expected_key is None:
        expected_key = f"expected_{output_field}"

    @scorer
    def _scorer(
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        expectations: Dict[str, Any],
        trace: Trace
    ) -> Feedback:
        expected = expectations.get(expected_key)

        if expected is None:
            return Feedback(
                name=f"{component_name}_{output_field}_accuracy",
                value="skip",
                rationale=f"No {expected_key} in expectations"
            )

        # 尋找元件 span
        spans = [
            s for s in trace.search_spans()
            if component_name.lower() in s.name.lower()
        ]

        if not spans:
            return Feedback(
                name=f"{component_name}_{output_field}_accuracy",
                value="no",
                rationale=f"No {component_name} span found"
            )

        actual = spans[0].outputs.get(output_field) if isinstance(spans[0].outputs, dict) else None

        return Feedback(
            name=f"{component_name}_{output_field}_accuracy",
            value="yes" if actual == expected else "no",
            rationale=f"Expected '{expected}', got '{actual}'"
        )

    return _scorer

# 用法範例:
classifier_accuracy = component_accuracy("classifier", "query_type", "expected_query_type")
router_accuracy = component_accuracy("router", "route", "expected_route")
intent_accuracy = component_accuracy("intent", "intent_type", "expected_intent")
```
