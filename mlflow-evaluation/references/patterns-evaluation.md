# MLflow 3 評估模式 (MLflow 3 Evaluation Patterns)

執行評估、比較結果和迭代品質的工作模式。

---

## 模式 0：首先進行本地代理測試 (關鍵)

**始終透過直接匯入代理在本地測試，而不是透過 Model Serving 端點。**

這可以實現更快的迭代、更容易的除錯，並且沒有部署開銷。

```python
import mlflow
from mlflow.genai.scorers import Guidelines, Safety

# ✅ 正確：直接從模組匯入代理
from plan_execute_agent import AGENT  # 或您的代理模組

# 啟用自動追蹤
mlflow.openai.autolog()
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/my-evaluation-experiment")

# 建立評估資料
eval_data = [
    {"inputs": {"messages": [{"role": "user", "content": "What is MLflow?"}]}},
    {"inputs": {"messages": [{"role": "user", "content": "How do I track experiments?"}]}},
]

# 使用本地代理定義 predict 函數
def predict_fn(messages):
    """直接呼叫本地代理的包裝器。"""
    result = AGENT.predict({"messages": messages})
    # 從代理輸出格式提取回應
    if isinstance(result, dict) and "messages" in result:
        # ResponsesAgent 格式 - 獲取最後一個助理訊息
        for msg in reversed(result["messages"]):
            if msg.get("role") == "assistant":
                return {"response": msg.get("content", "")}
    return {"response": str(result)}

# 使用本地代理執行評估
results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=predict_fn,
    scorers=[
        Safety(),
        Guidelines(name="helpful", guidelines="Response must be helpful and informative"),
    ]
)

print(f"Run ID: {results.run_id}")
print(f"Metrics: {results.metrics}")
```

### 為何首先進行本地測試？

| 面向 | 本地代理 | Model Serving 端點 |
|--------|-------------|------------------------|
| 迭代速度 | 快 (無需部署) | 慢 (每次變更需部署) |
| 除錯 | 完整堆疊追蹤 | 有限的可見性 |
| 成本 | 無服務成本 | 端點運算成本 |
| 依賴性 | 直接存取 | 網路延遲 |
| 使用案例 | 開發、測試 | 生產監控 |

### 何時使用 Model Serving 端點

僅在以下情況使用已部署的端點：
- 生產監控和品質追蹤
- 對已部署的模型進行負載測試
- 在已部署版本之間進行 A/B 測試
- 外部整合測試

---

## 模式 1：基本評估執行

```python
import mlflow
from mlflow.genai.scorers import Guidelines, Safety

# 啟用自動追蹤
mlflow.openai.autolog()

# 設定實驗
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment("/Shared/my-evaluation-experiment")

# 定義您的應用程式
@mlflow.trace
def my_app(query: str) -> dict:
    # 您的應用程式邏輯
    response = call_llm(query)
    return {"response": response}

# 建立評估資料
eval_data = [
    {"inputs": {"query": "What is MLflow?"}},
    {"inputs": {"query": "How do I track experiments?"}},
    {"inputs": {"query": "What are best practices?"}},
]

# 定義評分器
scorers = [
    Safety(),
    Guidelines(name="helpful", guidelines="Response must be helpful and informative"),
    Guidelines(name="concise", guidelines="Response must be under 200 words"),
]

# 執行評估
results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=scorers
)

print(f"Run ID: {results.run_id}")
print(f"Metrics: {results.metrics}")
```

---

## 模式 2：使用預先計算輸出的評估

當您已經有輸出（例如，來自生產日誌）時使用。

```python
# 帶有預先計算輸出的資料 - 不需要 predict_fn
eval_data = [
    {
        "inputs": {"query": "What is X?"},
        "outputs": {"response": "X is a platform for..."}
    },
    {
        "inputs": {"query": "How to use Y?"},
        "outputs": {"response": "To use Y, follow these steps..."}
    }
]

# 在沒有 predict_fn 的情況下執行評估
results = mlflow.genai.evaluate(
    data=eval_data,
    scorers=[Guidelines(name="quality", guidelines="Response must be accurate")]
)
```

---

## 模式 3：使用基本真值的評估

```python
from mlflow.genai.scorers import Correctness, Guidelines

# 帶有用於正確性檢查的 expectations 的資料
eval_data = [
    {
        "inputs": {"query": "What is the capital of France?"},
        "expectations": {
            "expected_facts": ["Paris is the capital of France"]
        }
    },
    {
        "inputs": {"query": "What are MLflow's components?"},
        "expectations": {
            "expected_facts": [
                "Tracking",
                "Projects", 
                "Models",
                "Registry"
            ]
        }
    }
]

results = mlflow.genai.evaluate(
    data=eval_data,
    predict_fn=my_app,
    scorers=[
        Correctness(),  # 使用 expected_facts
        Guidelines(name="format", guidelines="Must list items clearly")
    ]
)
```

---

## 模式 4：用於比較的具名評估執行

```python
import mlflow

# 版本 1 評估
with mlflow.start_run(run_name="prompt_v1"):
    results_v1 = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=app_v1,
        scorers=scorers
    )

# 版本 2 評估
with mlflow.start_run(run_name="prompt_v2"):
    results_v2 = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=app_v2,
        scorers=scorers
    )

# 比較指標
print("V1 Metrics:", results_v1.metrics)
print("V2 Metrics:", results_v2.metrics)
```

---

## 模式 5：分析評估結果

```python
import mlflow
import pandas as pd

# 執行評估後
results = mlflow.genai.evaluate(data=eval_data, predict_fn=my_app, scorers=scorers)

# 獲取詳細追蹤
traces_df = mlflow.search_traces(run_id=results.run_id)

# 存取每列結果
for idx, row in traces_df.iterrows():
    print(f"\n--- Row {idx} ---")
    print(f"Input: {row['request']}")
    print(f"Output: {row['response']}")
    
    # 存取 assessments (評分器結果)
    for assessment in row['assessments']:
        name = assessment['assessment_name']
        value = assessment['feedback']['value']
        rationale = assessment.get('rationale', 'N/A')
        print(f"  {name}: {value}")

# 過濾失敗
def has_failures(assessments):
    return any(
        a['feedback']['value'] in ['no', False, 0] 
        for a in assessments
    )

failures = traces_df[traces_df['assessments'].apply(has_failures)]
print(f"\nFound {len(failures)} rows with failures")
```

---

## 模式 6：比較兩個評估執行

```python
import mlflow
import pandas as pd

# 獲取執行
run_v1 = mlflow.search_runs(filter_string=f"run_id = '{results_v1.run_id}'")
run_v2 = mlflow.search_runs(filter_string=f"run_id = '{results_v2.run_id}'")

# 提取指標 (以 /mean 結尾)
metric_cols = [col for col in run_v1.columns 
               if col.startswith('metrics.') and col.endswith('/mean')]

# 建立比較
comparison = []
for metric in metric_cols:
    metric_name = metric.replace('metrics.', '').replace('/mean', '')
    v1_val = run_v1[metric].iloc[0]
    v2_val = run_v2[metric].iloc[0]
    improvement = v2_val - v1_val
    
    comparison.append({
        'Metric': metric_name,
        'V1': f"{v1_val:.3f}",
        'V2': f"{v2_val:.3f}",
        'Change': f"{improvement:+.3f}",
        'Improved': '✓' if improvement >= 0 else '✗'
    })

comparison_df = pd.DataFrame(comparison)
print(comparison_df.to_string(index=False))
```

---

## 模式 7：尋找版本間的回歸

```python
import mlflow

# 從兩個執行獲取追蹤
traces_v1 = mlflow.search_traces(run_id=results_v1.run_id)
traces_v2 = mlflow.search_traces(run_id=results_v2.run_id)

# 從輸入建立合併鍵
traces_v1['merge_key'] = traces_v1['request'].apply(lambda x: str(x))
traces_v2['merge_key'] = traces_v2['request'].apply(lambda x: str(x))

# 依輸入合併
merged = traces_v1.merge(traces_v2, on='merge_key', suffixes=('_v1', '_v2'))

# 尋找回歸 (v1 通過, v2 失敗)
regressions = []
for idx, row in merged.iterrows():
    v1_assessments = {a['assessment_name']: a for a in row['assessments_v1']}
    v2_assessments = {a['assessment_name']: a for a in row['assessments_v2']}
    
    for scorer_name in v1_assessments:
        v1_val = v1_assessments[scorer_name]['feedback']['value']
        v2_val = v2_assessments.get(scorer_name, {}).get('feedback', {}).get('value')
        
        # 檢查回歸 (yes->no 或 True->False)
        if v1_val in ['yes', True] and v2_val in ['no', False]:
            regressions.append({
                'input': row['request_v1'],
                'metric': scorer_name,
                'v1_output': row['response_v1'],
                'v2_output': row['response_v2'],
                'v1_rationale': v1_assessments[scorer_name].get('rationale'),
                'v2_rationale': v2_assessments[scorer_name].get('rationale')
            })

print(f"Found {len(regressions)} regressions")
for r in regressions[:5]:  # 顯示前 5 個
    print(f"\nRegression in '{r['metric']}':")
    print(f"  Input: {r['input']}")
    print(f"  V2 Rationale: {r['v2_rationale']}")
```

---

## 模式 8：迭代改進循環

```python
import mlflow
from mlflow.genai.scorers import Guidelines

# 定義品質標準
QUALITY_THRESHOLD = 0.9  # 90% 通過率

def evaluate_and_improve(app_fn, eval_data, scorers, max_iterations=5):
    """迭代改進直到達到品質標準。"""
    
    for iteration in range(max_iterations):
        print(f"\n=== Iteration {iteration + 1} ===")
        
        with mlflow.start_run(run_name=f"iteration_{iteration + 1}"):
            results = mlflow.genai.evaluate(
                data=eval_data,
                predict_fn=app_fn,
                scorers=scorers
            )
        
        # 計算整體通過率
        pass_rates = {}
        for metric, value in results.metrics.items():
            if metric.endswith('/mean'):
                metric_name = metric.replace('/mean', '')
                pass_rates[metric_name] = value
        
        avg_pass_rate = sum(pass_rates.values()) / len(pass_rates)
        print(f"Average pass rate: {avg_pass_rate:.2%}")
        
        if avg_pass_rate >= QUALITY_THRESHOLD:
            print(f"✓ Quality threshold {QUALITY_THRESHOLD:.0%} met!")
            return results
        
        # 尋找表現最差的指標
        worst_metric = min(pass_rates, key=pass_rates.get)
        print(f"Worst metric: {worst_metric} ({pass_rates[worst_metric]:.2%})")
        
        # 分析該指標的失敗
        traces = mlflow.search_traces(run_id=results.run_id)
        failures = analyze_failures(traces, worst_metric)
        
        print(f"Sample failures for {worst_metric}:")
        for f in failures[:3]:
            print(f"  - Input: {f['input'][:50]}...")
            print(f"    Rationale: {f['rationale']}")
        
        # 在這裡您會根據失敗更新 app_fn
        # 這可能是手動或自動的提示優化
        print("\n[Update your app based on failures before next iteration]")
    
    print(f"✗ Did not meet threshold after {max_iterations} iterations")
    return results

def analyze_failures(traces, metric_name):
    """提取特定指標的失敗案例。"""
    failures = []
    for _, row in traces.iterrows():
        for assessment in row['assessments']:
            if (assessment['assessment_name'] == metric_name and 
                assessment['feedback']['value'] in ['no', False]):
                failures.append({
                    'input': row['request'],
                    'output': row['response'],
                    'rationale': assessment.get('rationale', 'N/A')
                })
    return failures
```

---

## 模式 9：從生產追蹤進行評估

```python
import mlflow
import time

# 搜尋最近的生產追蹤
one_day_ago = int((time.time() - 86400) * 1000)  # 24 小時的毫秒數

prod_traces = mlflow.search_traces(
    filter_string=f"""
        attributes.status = 'OK' AND 
        attributes.timestamp_ms > {one_day_ago} AND
        tags.environment = 'production'
    """,
    order_by=["attributes.timestamp_ms DESC"],
    max_results=100
)

print(f"Found {len(prod_traces)} production traces")

# 轉換為評估格式
eval_data = []
for _, trace in prod_traces.iterrows():
    eval_data.append({
        "inputs": trace['request'],
        "outputs": trace['response']
    })

# 對生產資料執行評估
results = mlflow.genai.evaluate(
    data=eval_data,
    scorers=[
        Safety(),
        Guidelines(name="quality", guidelines="Response must be helpful")
    ]
)
```

---

## 模式 10：A/B 測試兩個提示

```python
import mlflow
from mlflow.genai.scorers import Guidelines, Safety

# 兩個不同的系統提示
PROMPT_A = "You are a helpful assistant. Be concise."
PROMPT_B = "You are an expert assistant. Provide detailed, comprehensive answers."

def create_app(system_prompt):
    @mlflow.trace
    def app(query):
        response = client.chat.completions.create(
            model="databricks-claude-sonnet-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
        )
        return {"response": response.choices[0].message.content}
    return app

app_a = create_app(PROMPT_A)
app_b = create_app(PROMPT_B)

scorers = [
    Safety(),
    Guidelines(name="helpful", guidelines="Must be helpful"),
    Guidelines(name="accurate", guidelines="Must be accurate"),
    Guidelines(name="concise", guidelines="Must be under 100 words"),
]

# 執行 A/B 測試
with mlflow.start_run(run_name="prompt_a_concise"):
    results_a = mlflow.genai.evaluate(
        data=eval_data, predict_fn=app_a, scorers=scorers
    )

with mlflow.start_run(run_name="prompt_b_detailed"):
    results_b = mlflow.genai.evaluate(
        data=eval_data, predict_fn=app_b, scorers=scorers
    )

# 比較
print("Prompt A (Concise):", results_a.metrics)
print("Prompt B (Detailed):", results_b.metrics)
```

---

## 模式 11：帶有平行化的評估

用於大型資料集或複雜的應用程式。

```python
import mlflow

# 透過環境變數或執行設定配置平行化
# 預設為循序執行；增加以加快評估速度

results = mlflow.genai.evaluate(
    data=large_eval_data,  # 1000+ 記錄
    predict_fn=my_app,
    scorers=scorers,
    # 平行化在內部處理
    # 對於複雜代理，考慮分批處理您的資料
)
```

---

## 模式 12：CI/CD 中的持續評估

```python
import mlflow
import sys

def run_ci_evaluation():
    """作為 CI/CD 管線的一部分執行評估。"""
    
    # 載入測試資料
    eval_data = load_test_data()  # 從檔案或測試固件
    
    # 定義品質閘門
    QUALITY_GATES = {
        "safety": 1.0,           # 必須通過 100%
        "helpful": 0.9,          # 必須通過 90%
        "concise": 0.8,          # 必須通過 80%
    }
    
    # 執行評估
    results = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=my_app,
        scorers=[
            Safety(),
            Guidelines(name="helpful", guidelines="Must be helpful"),
            Guidelines(name="concise", guidelines="Must be concise"),
        ]
    )
    
    # 檢查品質閘門
    failures = []
    for metric, threshold in QUALITY_GATES.items():
        actual = results.metrics.get(f"{metric}/mean", 0)
        if actual < threshold:
            failures.append(f"{metric}: {actual:.2%} < {threshold:.2%}")
    
    if failures:
        print("❌ Quality gates failed:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✅ All quality gates passed")
        sys.exit(0)

if __name__ == "__main__":
    run_ci_evaluation()
```

---

## 評估最佳實踐

1. **從小開始**：從 20-50 個多樣化的測試案例開始
2. **涵蓋邊緣案例**：包含對抗性、模糊和超出範圍的輸入
3. **使用多個評分器**：結合安全性、品質和特定領域檢查
4. **隨時間追蹤**：為執行命名以便於比較
5. **分析失敗**：不要只看聚合指標
6. **迭代**：使用失敗來改進提示/邏輯，然後重新評估
7. **版本化您的資料**：使用 MLflow 託管的資料集以實現可重現性
