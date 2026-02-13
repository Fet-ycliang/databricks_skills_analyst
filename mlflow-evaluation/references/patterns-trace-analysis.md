# MLflow 3 追蹤分析模式 (MLflow 3 Trace Analysis Patterns)

跨代理架構分析 MLflow 追蹤的工作程式碼模式。

## 何時使用 MCP vs Python SDK

| 使用案例 | 推薦方法 |
|----------|---------------------|
| 互動式追蹤探索 | **MLflow MCP Server** - 快速搜尋、欄位提取 |
| 基於代理的分析 | **MLflow MCP Server** - 子代理搜尋並標記追蹤 |
| 評估腳本產生 | **MLflow Python SDK** - 產生可執行的 Python 程式碼 |
| 自訂分析管線 | **MLflow Python SDK** - 完全控制、複雜聚合 |
| 從追蹤建立資料集 | **MLflow Python SDK** - 將追蹤轉換為評估格式 |
| CI/CD 整合 | **MLflow Python SDK** - 獨立腳本 |

### MLflow MCP Server (供代理使用)

最適合互動式探索和基於代理的追蹤分析：
- `search_traces` - 使用 `extract_fields` 進行過濾和搜尋
- `get_trace` - 深入研究並選擇性提取欄位
- `set_trace_tag` - 標記追蹤以供稍後建立資料集
- `log_feedback` - 持久儲存分析發現
- `log_expectation` - 儲存評估用的基本真值

### MLflow Python SDK (供程式碼產生使用)

最適合產生可執行的評估腳本：
- `mlflow.search_traces()` - 程式化存取追蹤
- `mlflow.genai.evaluate()` - 執行評估
- `MlflowClient()` - 完整的 API 存取
- DataFrame operations - 複雜聚合和分析

---

## 目錄

| # | 模式 | 描述 |
|---|---------|-------------|
| 1 | [獲取追蹤](#模式-1-從-mlflow-獲取追蹤) | 從實驗獲取追蹤 |
| 2 | [獲取單個追蹤](#模式-2-依-id-獲取單個追蹤) | 依 ID 獲取特定追蹤 |
| 3 | [Span 層級](#模式-3-span-層級分析) | 分析父子結構 |
| 4 | [依 Span 類型延遲](#模式-4-依-span-類型延遲細分) | LLM, TOOL, RETRIEVER 細分 |
| 5 | [依元件延遲](#模式-5-依元件名稱延遲細分) | 階段/元件計時 |
| 6 | [瓶頸檢測](#模式-6-瓶頸檢測) | 尋找最慢的元件 |
| 7 | [錯誤檢測](#模式-7-錯誤模式檢測) | 尋找並分類錯誤 |
| 8 | [工具呼叫分析](#模式-8-工具呼叫分析) | 分析工具/函數呼叫 |
| 9 | [LLM 呼叫分析](#模式-9-llm-呼叫分析) | Token 使用量和延遲 |
| 10 | [追蹤比較](#模式-10-追蹤比較) | 比較多個追蹤 |
| 11 | [追蹤報告](#模式-11-產生追蹤分析報告) | 產生綜合報告 |
| 12 | [MCP Server 用法](#模式-12-使用-mlflow-mcp-server-進行追蹤分析) | 透過 MCP 快速查找追蹤 |
| 13 | [架構檢測](#模式-13-架構檢測) | 自動檢測代理類型 |
| 14 | [透過 MCP 評估](#模式-14-使用-assessments-進行持久化分析) | 將發現儲存在 MLflow 中 |

---

## 模式 1：從 MLflow 獲取追蹤

從實驗獲取追蹤以進行分析。

```python
import mlflow
from mlflow import MlflowClient

client = MlflowClient()

# 依 ID 從實驗獲取追蹤
traces = client.search_traces(
    experiment_ids=["your_experiment_id"],
    max_results=100
)

# 依名稱從實驗獲取追蹤
experiment = mlflow.get_experiment_by_name("/Users/user@domain.com/my-experiment")
traces = client.search_traces(
    experiment_ids=[experiment.experiment_id],
    max_results=50
)

# 依時間範圍過濾追蹤
from datetime import datetime, timedelta
yesterday = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
traces = client.search_traces(
    experiment_ids=["your_experiment_id"],
    filter_string=f"timestamp_ms > {yesterday}"
)
```

---

## 模式 2：依 ID 獲取單個追蹤

獲取特定追蹤以進行詳細分析。

```python
from mlflow import MlflowClient

client = MlflowClient()

# 依 ID 獲取追蹤
trace = client.get_trace(trace_id="tr-abc123def456")

# 存取追蹤資訊
print(f"Trace ID: {trace.info.trace_id}")
print(f"Status: {trace.info.status}")
print(f"Execution time: {trace.info.execution_time_ms}ms")

# 存取追蹤資料 (spans)
spans = trace.data.spans
print(f"Total spans: {len(spans)}")
```

---

## 模式 3：Span 層級分析

分析追蹤中 span 的層級結構。

```python
from mlflow.entities import Trace
from typing import Dict, List, Any

def analyze_span_hierarchy(trace: Trace) -> Dict[str, Any]:
    """分析 Span 層級和結構。

    適用於任何代理架構 (DSPy, LangGraph 等)
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

    # 建立父子關係
    span_by_id = {s.span_id: s for s in spans}
    children = {}
    root_spans = []

    for span in spans:
        if span.parent_id is None:
            root_spans.append(span)
        else:
            if span.parent_id not in children:
                children[span.parent_id] = []
            children[span.parent_id].append(span)

    def build_tree(span, depth=0):
        """遞迴建立 span 樹。"""
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6
        node = {
            "name": span.name,
            "span_type": str(span.span_type) if span.span_type else "UNKNOWN",
            "duration_ms": round(duration_ms, 2),
            "depth": depth,
            "children": []
        }
        for child in children.get(span.span_id, []):
            node["children"].append(build_tree(child, depth + 1))
        return node

    return {
        "root_count": len(root_spans),
        "total_spans": len(spans),
        "hierarchy": [build_tree(root) for root in root_spans]
    }

# 用法
hierarchy = analyze_span_hierarchy(trace)
print(f"Root spans: {hierarchy['root_count']}")
print(f"Total spans: {hierarchy['total_spans']}")
```

---

## 模式 4：依 Span 類型延遲細分

分析跨 Span 類型的延遲分佈。

```python
from mlflow.entities import Trace, SpanType
from typing import Dict, List
from collections import defaultdict

def latency_by_span_type(trace: Trace) -> Dict[str, Dict]:
    """依 Span 類型細分延遲。

    返回每種 Span 類型 (LLM, TOOL, RETRIEVER 等) 的延遲統計。
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

    type_latencies = defaultdict(list)

    for span in spans:
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6
        span_type = str(span.span_type) if span.span_type else "UNKNOWN"
        type_latencies[span_type].append({
            "name": span.name,
            "duration_ms": duration_ms
        })

    results = {}
    for span_type, items in type_latencies.items():
        durations = [i["duration_ms"] for i in items]
        results[span_type] = {
            "count": len(items),
            "total_ms": round(sum(durations), 2),
            "avg_ms": round(sum(durations) / len(durations), 2),
            "max_ms": round(max(durations), 2),
            "min_ms": round(min(durations), 2),
            "spans": items
        }

    return results

# 用法
latency_stats = latency_by_span_type(trace)
for span_type, stats in sorted(latency_stats.items(), key=lambda x: -x[1]["total_ms"]):
    print(f"{span_type}: {stats['total_ms']}ms total ({stats['count']} spans)")
```

---

## 模式 5：依元件名稱延遲細分

依元件/階段名稱分析延遲 (架構無關)。

```python
from mlflow.entities import Trace
from typing import Dict, List
from collections import defaultdict

def latency_by_component(
    trace: Trace,
    component_patterns: List[str] = None
) -> Dict[str, Dict]:
    """依元件名稱模式細分延遲。

    Args:
        trace: 要分析的 MLflow 追蹤
        component_patterns: 選用的要查找的模式列表。
                           如果為 None，則提取所有唯一的 span 名稱。

    適用於任何架構 - DSPy 階段、LangGraph 節點等。
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

    component_latencies = defaultdict(list)

    for span in spans:
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6
        span_name = span.name.lower()

        if component_patterns:
            # 對照模式進行匹配
            for pattern in component_patterns:
                if pattern.lower() in span_name:
                    component_latencies[pattern].append({
                        "span_name": span.name,
                        "duration_ms": duration_ms
                    })
                    break
        else:
            # 直接使用 span 名稱
            component_latencies[span.name].append({
                "duration_ms": duration_ms
            })

    results = {}
    for component, items in component_latencies.items():
        durations = [i["duration_ms"] for i in items]
        results[component] = {
            "count": len(items),
            "total_ms": round(sum(durations), 2),
            "avg_ms": round(sum(durations) / len(durations), 2) if durations else 0,
            "max_ms": round(max(durations), 2) if durations else 0,
        }

    return results

# 用法 - DSPy 多代理
dspy_components = ["classifier", "rewriter", "gatherer", "executor"]
stats = latency_by_component(trace, dspy_components)

# 用法 - LangGraph
langgraph_components = ["planner", "executor", "tool_call", "compress"]
stats = latency_by_component(trace, langgraph_components)

# 用法 - 自動檢測所有元件
stats = latency_by_component(trace)
```

---

## 模式 6：瓶頸檢測

尋找追蹤中最慢的元件。

```python
from mlflow.entities import Trace
from typing import Dict, List, Tuple

def find_bottlenecks(
    trace: Trace,
    top_n: int = 5,
    exclude_patterns: List[str] = None
) -> List[Dict]:
    """尋找追蹤中最慢的 spans。

    Args:
        trace: 要分析的 MLflow 追蹤
        top_n: 返回的最慢 spans 數量
        exclude_patterns: 要排除的 Span 名稱模式 (例如，包裝器 spans)

    Returns:
        帶有計時資訊的最慢 spans 列表
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()
    exclude_patterns = exclude_patterns or ["forward", "predict", "root"]

    span_timings = []
    for span in spans:
        # 跳過排除的模式
        span_name_lower = span.name.lower()
        if any(p in span_name_lower for p in exclude_patterns):
            continue

        duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6
        span_timings.append({
            "name": span.name,
            "span_type": str(span.span_type) if span.span_type else "UNKNOWN",
            "duration_ms": round(duration_ms, 2),
            "span_id": span.span_id
        })

    # 依持續時間降序排序
    span_timings.sort(key=lambda x: -x["duration_ms"])

    return span_timings[:top_n]

# 用法
bottlenecks = find_bottlenecks(trace, top_n=5)
print("Top 5 Slowest Spans:")
for i, b in enumerate(bottlenecks, 1):
    print(f"  {i}. {b['name']} ({b['span_type']}): {b['duration_ms']}ms")
```

---

## 模式 7：錯誤模式檢測

尋找並分析追蹤中的錯誤模式。

```python
from mlflow.entities import Trace, SpanStatusCode
from typing import Dict, List

def detect_errors(trace: Trace) -> Dict[str, List]:
    """檢測追蹤中的錯誤模式。

    返回帶有上下文的分類錯誤。
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

    errors = {
        "failed_spans": [],
        "exceptions": [],
        "empty_outputs": [],
        "warnings": []
    }

    for span in spans:
        # 檢查 span 狀態
        if span.status and span.status.status_code == SpanStatusCode.ERROR:
            errors["failed_spans"].append({
                "name": span.name,
                "span_type": str(span.span_type),
                "error_message": span.status.description if span.status.description else "Unknown error"
            })

        # 檢查事件中的異常
        if span.events:
            for event in span.events:
                if "exception" in event.name.lower():
                    errors["exceptions"].append({
                        "span_name": span.name,
                        "event": event.name,
                        "attributes": event.attributes
                    })

        # 檢查空輸出 (潛在問題)
        if span.outputs is None or span.outputs == {} or span.outputs == []:
            errors["empty_outputs"].append({
                "name": span.name,
                "span_type": str(span.span_type)
            })

    return errors

# 用法
errors = detect_errors(trace)
if errors["failed_spans"]:
    print(f"Found {len(errors['failed_spans'])} failed spans")
    for e in errors["failed_spans"]:
        print(f"  - {e['name']}: {e['error_message']}")
```

---

## 模式 8：工具呼叫分析

分析追蹤中的工具/函數呼叫。

```python
from mlflow.entities import Trace, SpanType
from typing import Dict, List

def analyze_tool_calls(trace: Trace) -> Dict[str, Any]:
    """分析追蹤中的工具呼叫。

    適用於 UC 函數、LangChain 工具或任何 TOOL span 類型。
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

    # 尋找工具 spans
    tool_spans = [s for s in spans if s.span_type == SpanType.TOOL]

    tool_calls = []
    for span in tool_spans:
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6

        # 提取工具名稱 (處理全限定名稱)
        tool_name = span.name
        if "." in tool_name:
            tool_name_short = tool_name.split(".")[-1]
        else:
            tool_name_short = tool_name

        tool_calls.append({
            "tool_name": tool_name_short,
            "full_name": span.name,
            "duration_ms": round(duration_ms, 2),
            "inputs": span.inputs,
            "outputs_preview": str(span.outputs)[:200] if span.outputs else None,
            "success": span.status.status_code != SpanStatusCode.ERROR if span.status else True
        })

    # 聚合統計
    tool_stats = {}
    for tc in tool_calls:
        name = tc["tool_name"]
        if name not in tool_stats:
            tool_stats[name] = {"count": 0, "total_ms": 0, "successes": 0}
        tool_stats[name]["count"] += 1
        tool_stats[name]["total_ms"] += tc["duration_ms"]
        if tc["success"]:
            tool_stats[name]["successes"] += 1

    return {
        "total_tool_calls": len(tool_calls),
        "unique_tools": len(tool_stats),
        "calls": tool_calls,
        "stats": tool_stats
    }

# 用法
tool_analysis = analyze_tool_calls(trace)
print(f"Total tool calls: {tool_analysis['total_tool_calls']}")
for tool, stats in tool_analysis['stats'].items():
    print(f"  {tool}: {stats['count']} calls, {stats['total_ms']}ms total")
```

---

## 模式 9：LLM 呼叫分析

分析追蹤中的 LLM 呼叫。

```python
from mlflow.entities import Trace, SpanType
from typing import Dict, List, Any

def analyze_llm_calls(trace: Trace) -> Dict[str, Any]:
    """分析追蹤中的 LLM 呼叫。

    提取模型資訊、Token 使用量和延遲。
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

    # 尋找 LLM/CHAT_MODEL spans
    llm_spans = [s for s in spans
                 if s.span_type in [SpanType.LLM, SpanType.CHAT_MODEL]]

    llm_calls = []
    for span in llm_spans:
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1e6

        # 從屬性提取 token 資訊
        attributes = span.attributes or {}

        llm_calls.append({
            "name": span.name,
            "duration_ms": round(duration_ms, 2),
            "model": attributes.get("mlflow.chat_model.model") or attributes.get("llm.model_name"),
            "input_tokens": attributes.get("mlflow.chat_model.input_tokens"),
            "output_tokens": attributes.get("mlflow.chat_model.output_tokens"),
            "total_tokens": attributes.get("mlflow.chat_model.total_tokens"),
        })

    # 計算總和
    total_input = sum(c["input_tokens"] or 0 for c in llm_calls)
    total_output = sum(c["output_tokens"] or 0 for c in llm_calls)
    total_latency = sum(c["duration_ms"] for c in llm_calls)

    return {
        "total_llm_calls": len(llm_calls),
        "total_latency_ms": round(total_latency, 2),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "calls": llm_calls
    }

# 用法
llm_analysis = analyze_llm_calls(trace)
print(f"LLM calls: {llm_analysis['total_llm_calls']}")
print(f"Total tokens: {llm_analysis['total_input_tokens']} in / {llm_analysis['total_output_tokens']} out")
print(f"LLM latency: {llm_analysis['total_latency_ms']}ms")
```

---

## 模式 10：追蹤比較

比較多個追蹤以識別模式。

```python
from mlflow.entities import Trace
from typing import List, Dict, Any

def compare_traces(traces: List[Trace]) -> Dict[str, Any]:
    """比較多個追蹤以識別模式。

    適用於前後比較或批次分析。
    """
    trace_stats = []

    for trace in traces:
        spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()

        # 獲取 root span 以計算總時間
        root_spans = [s for s in spans if s.parent_id is None]
        total_ms = 0
        if root_spans:
            root = root_spans[0]
            total_ms = (root.end_time_ns - root.start_time_ns) / 1e6

        trace_stats.append({
            "trace_id": trace.info.trace_id,
            "total_ms": round(total_ms, 2),
            "span_count": len(spans),
            "status": str(trace.info.status)
        })

    # 計算聚合
    latencies = [t["total_ms"] for t in trace_stats]

    return {
        "trace_count": len(traces),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "min_latency_ms": round(min(latencies), 2) if latencies else 0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0,
        "p50_latency_ms": round(sorted(latencies)[len(latencies)//2], 2) if latencies else 0,
        "success_rate": sum(1 for t in trace_stats if "OK" in t["status"]) / len(trace_stats) if trace_stats else 0,
        "traces": trace_stats
    }

# 用法
comparison = compare_traces(traces)
print(f"Analyzed {comparison['trace_count']} traces")
print(f"Avg latency: {comparison['avg_latency_ms']}ms")
print(f"Success rate: {comparison['success_rate']:.1%}")
```

---

## 模式 11：產生追蹤分析報告

將多個分析模式組合成一份綜合報告。

```python
from mlflow.entities import Trace
from typing import Dict, Any

def generate_trace_report(trace: Trace) -> Dict[str, Any]:
    """產生綜合追蹤分析報告。

    結合層級、延遲、錯誤和瓶頸分析。
    """
    # 匯入分析函數 (來自上述模式)
    hierarchy = analyze_span_hierarchy(trace)
    latency_by_type = latency_by_span_type(trace)
    bottlenecks = find_bottlenecks(trace, top_n=3)
    errors = detect_errors(trace)
    tool_analysis = analyze_tool_calls(trace)
    llm_analysis = analyze_llm_calls(trace)

    # 獲取 root span 資訊
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()
    root_spans = [s for s in spans if s.parent_id is None]
    total_ms = 0
    if root_spans:
        root = root_spans[0]
        total_ms = (root.end_time_ns - root.start_time_ns) / 1e6

    return {
        "summary": {
            "trace_id": trace.info.trace_id,
            "status": str(trace.info.status),
            "total_duration_ms": round(total_ms, 2),
            "total_spans": len(spans),
        },
        "hierarchy": hierarchy,
        "latency_by_type": latency_by_type,
        "bottlenecks": bottlenecks,
        "errors": errors,
        "tool_calls": tool_analysis,
        "llm_calls": llm_analysis,
        "recommendations": generate_recommendations(
            bottlenecks, errors, llm_analysis, total_ms
        )
    }

def generate_recommendations(
    bottlenecks: List[Dict],
    errors: Dict,
    llm_analysis: Dict,
    total_ms: float
) -> List[str]:
    """從分析中產生可行的建議。"""
    recommendations = []

    # 延遲建議
    if bottlenecks and bottlenecks[0]["duration_ms"] > total_ms * 0.5:
        b = bottlenecks[0]
        recommendations.append(
            f"BOTTLENECK: '{b['name']}' takes {b['duration_ms']/total_ms*100:.0f}% of total time. "
            f"Consider optimizing this component."
        )

    # LLM 建議
    if llm_analysis["total_llm_calls"] > 5:
        recommendations.append(
            f"HIGH LLM CALLS: {llm_analysis['total_llm_calls']} LLM calls detected. "
            f"Consider batching or reducing calls."
        )

    # 錯誤建議
    if errors["failed_spans"]:
        recommendations.append(
            f"ERRORS: {len(errors['failed_spans'])} failed spans detected. "
            f"Review: {[e['name'] for e in errors['failed_spans'][:3]]}"
        )

    if not recommendations:
        recommendations.append("No major issues detected. Trace looks healthy.")

    return recommendations

# 用法
report = generate_trace_report(trace)
print(f"Trace {report['summary']['trace_id']}")
print(f"Duration: {report['summary']['total_duration_ms']}ms")
print(f"Spans: {report['summary']['total_spans']}")
print("\nRecommendations:")
for rec in report['recommendations']:
    print(f"  - {rec}")
```

---

## 模式 12：使用 MLflow MCP Server 進行追蹤分析

使用 MLflow MCP server 進行快速追蹤查找。

```python
# 透過 Claude Code，使用 MCP server 工具：

# 搜尋實驗中的追蹤
mcp__mlflow-mcp__search_traces(
    experiment_id="your_experiment_id",
    max_results=10,
    output="table"
)

# 獲取詳細追蹤資訊
mcp__mlflow-mcp__get_trace(
    trace_id="tr-abc123",
    extract_fields="info.trace_id,info.status,data.spans.*.name"
)

# 依狀態過濾
mcp__mlflow-mcp__search_traces(
    experiment_id="123",
    filter_string="status = 'OK'",
    max_results=20
)
```

---

## 模式 13：架構檢測

從追蹤結構自動檢測代理架構。

```python
from mlflow.entities import Trace, SpanType
from typing import Dict, Any

def detect_architecture(trace: Trace) -> Dict[str, Any]:
    """從追蹤模式檢測代理架構。

    返回架構類型和關鍵特徵。
    """
    spans = trace.data.spans if hasattr(trace, 'data') else trace.search_spans()
    span_names = [s.name.lower() for s in spans]
    span_types = [s.span_type for s in spans]

    # 架構指標
    indicators = {
        "dspy_multi_agent": any(
            p in " ".join(span_names)
            for p in ["classifier", "rewriter", "gatherer", "executor"]
        ),
        "langgraph": any(
            p in " ".join(span_names)
            for p in ["langgraph", "graph", "node", "state"]
        ),
        "rag": SpanType.RETRIEVER in span_types,
        "tool_calling": SpanType.TOOL in span_types,
        "simple_chat": len(set(span_types)) <= 2 and SpanType.CHAT_MODEL in span_types,
    }

    # 確定主要架構
    if indicators["dspy_multi_agent"]:
        arch_type = "dspy_multi_agent"
    elif indicators["langgraph"]:
        arch_type = "langgraph"
    elif indicators["rag"] and indicators["tool_calling"]:
        arch_type = "rag_with_tools"
    elif indicators["rag"]:
        arch_type = "rag"
    elif indicators["tool_calling"]:
        arch_type = "tool_calling"
    else:
        arch_type = "simple_chat"

    return {
        "architecture": arch_type,
        "indicators": indicators,
        "span_type_distribution": {
            str(st): sum(1 for s in spans if s.span_type == st)
            for st in set(span_types)
        }
    }

# 用法
arch = detect_architecture(trace)
print(f"Detected architecture: {arch['architecture']}")
print(f"Span types: {arch['span_type_distribution']}")
```

---

## 最佳實踐

### 1. 始終處理遺失資料
```python
# 追蹤可能有不完整的資料
spans = trace.data.spans if hasattr(trace, 'data') else []
duration = (span.end_time_ns - span.start_time_ns) / 1e6 if span.end_time_ns else 0
```

### 2. 正規化 Span 名稱
```python
# 處理全限定名稱 (UC 函數等)
def normalize_name(name: str) -> str:
    return name.split(".")[-1] if "." in name else name
```

### 3. 使用適當的過濾器
```python
# 排除包裝器 spans 以進行準確的瓶頸檢測
exclude = ["forward", "predict", "__init__", "root"]
```

### 4. 快取昂貴的分析
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_trace_analysis(trace_id: str):
    trace = client.get_trace(trace_id)
    return generate_trace_report(trace)
```
