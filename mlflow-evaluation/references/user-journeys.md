# 使用者旅程指南 (User Journey Guides)

常見評估情境的逐步工作流程。

---

## 旅程 0：策略對齊 (始終從這裡開始)

**起點**：您需要評估一個代理
**目標**：在編寫任何程式碼之前，對要評估的內容達成共識

**優先事項：** 在編寫評估程式碼之前，完成策略對齊。這確保評估能夠衡量重要的內容並提供可行的見解。

### 步驟 1：了解代理

在評估之前，收集有關您正在評估內容的背景資訊：

**要問的問題 (或在程式碼庫中調查)：**
1. **這個代理做什麼？** (資料分析、RAG、多輪對話、任務自動化)
2. **它使用什麼工具？** (UC 函數、向量搜尋、外部 API)
3. **輸入/輸出格式是什麼？** (訊息格式、結構化輸出)
4. **目前的狀態是什麼？** (原型、生產、需要改進)

**採取的行動：**
- 閱讀代理的主要程式碼檔案 (例如 `agent.py`)
- 審查設定檔中的系統提示和工具定義
- 檢查現有的測試或評估腳本
- 查看 CLAUDE.md 或 README 以獲取專案背景

### 步驟 2：對要評估的內容達成共識

**要考慮的評估維度：**

| 維度 | 何時使用 | 範例評分器 |
|-----------|-------------|----------------|
| **安全性 (Safety)** | 始終 (基本要求) | `Safety()` |
| **正確性 (Correctness)** | 當存在基本真值時 | `Correctness()` |
| **相關性 (Relevance)** | 當回應應該解決查詢時 | `RelevanceToQuery()` |
| **依據性 (Groundedness)** | 帶有檢索上下文的 RAG 系統 | `RetrievalGroundedness()` |
| **領域準則 (Domain Guidelines)** | 特定領域的需求 | `Guidelines(name="...", guidelines="...")` |
| **格式/結構 (Format/Structure)** | 結構化輸出需求 | 自訂評分器 |
| **工具使用 (Tool Usage)** | 帶有工具呼叫的代理 | 檢查工具選擇的自訂評分器 |

**要問使用者的問題：**
1. 什麼是 **必須具備** 的品質標準？(安全性、準確性、相關性)
2. 什麼是 **最好具備** 的標準？(簡潔性、語氣、格式)
3. 是否有您見過或擔心的 **特定失敗模式**？
4. 您是否有測試案例的 **基本真值** 或預期答案？

### 步驟 3：定義使用者情境 (評估資料集)

**要包含的測試案例類型：**

| 類別 | 目的 | 範例 |
|----------|---------|---------|
| **快樂路徑 (Happy Path)** | 核心功能運作 | 典型使用者問題 |
| **邊緣案例 (Edge Cases)** | 邊界條件 | 空輸入、非常長的查詢 |
| **對抗性 (Adversarial)** | 穩健性測試 | 提示注入、離題 |
| **多輪 (Multi-turn)** | 對話處理 | 後續問題、上下文回憶 |
| **特定領域 (Domain-specific)** | 業務邏輯 | 行業術語、特定格式 |

**要問使用者的問題：**
1. 使用者 **最常問** 的問題是什麼？
2. 代理應該處理的 **具挑戰性** 問題是什麼？
3. 是否有它應該 **拒絕** 回答的問題？
4. 您是否有 **現有的測試案例** 或生產追蹤可以開始使用？

### 步驟 4：建立成功標準

**在執行評估之前定義品質閘門：**

```python
QUALITY_GATES = {
    "safety": 1.0,           # 100% - 不可協商
    "correctness": 0.9,      # 90% - 高標準的準確性
    "relevance": 0.85,       # 85% - 良好的相關性
    "concise": 0.8,          # 80% - 最好具備
}
```

**要問使用者的問題：**
1. 每個維度的 **可接受** 通過率是多少？
2. 哪些指標是 **阻礙性** vs **資訊性** 的？
3. 評估結果將如何 **告知決策**？(發布/不發布、迭代、調查)

### 策略對齊檢查清單

在實作評估之前，確認：
- [ ] 已了解代理目的和架構
- [ ] 已同意評估維度
- [ ] 已識別測試案例類別
- [ ] 已定義成功標準
- [ ] 已識別資料來源 (新、追蹤、現有資料集)

---

## 旅程 3："東西壞了" - 回歸檢測

**起點**：您對代理進行了更改，並懷疑某些東西退化了
**目標**：識別壞掉的地方並驗證修復

### 步驟

1. **建立基準指標**
   ```bash
   # 在先前版本上執行評估 (或使用已儲存的基準)
   cd agents/tool_calling_dspy
   python run_quick_eval.py
   ```
   記錄關鍵指標：`classifier_accuracy`、`tool_selection_accuracy`、`follows_instructions`

2. **在當前版本上執行評估**
   ```bash
   python run_quick_eval.py
   ```

3. **比較指標**
   ```python
   from evaluation.optimization_history import OptimizationHistory

   history = OptimizationHistory()
   print(history.compare_iterations(-2, -1))  # 比較最後兩次
   ```

4. **識別回歸來源**
   - 如果 `classifier_accuracy` 下降 → 檢查 ClassifierSignature 更改
   - 如果 `tool_selection_accuracy` 下降 → 檢查工具描述、required_tools 欄位
   - 如果 `follows_instructions` 下降 → 檢查 ExecutorSignature 輸出格式

5. **分析失敗的追蹤**
   ```
   /eval:analyze-traces [experiment-id]
   ```
   尋找：
   - 特定測試類別中的錯誤模式
   - 工具呼叫失敗
   - 意外的輸出

6. **修復並重新評估**
   - 還原問題更改或應用針對性修復
   - 重新執行評估
   - 驗證指標已恢復

### 使用的指令
- `python run_quick_eval.py` - 執行評估
- `/eval:analyze-traces` - 深度追蹤分析
- `OptimizationHistory.compare_iterations()` - 指標比較

### 成功指標
- 指標恢復到基準或有所改善
- 沒有新的失敗測試案例
- 追蹤分析顯示預期行為

---

## 旅程 7："我的多代理很慢" - 效能最佳化

**起點**：您的代理回應太慢
**目標**：識別瓶頸並減少延遲

### 步驟

1. **執行帶有延遲評分的評估**
   ```bash
   cd agents/tool_calling_dspy
   python run_quick_eval.py
   ```
   注意延遲指標：
   - `classifier_latency_ms`
   - `rewriter_latency_ms`
   - `executor_latency_ms`
   - `total_latency_ms`

2. **識別瓶頸階段**
   | 延遲 | 典型範圍 | 如果高，檢查 |
   |---------|---------------|----------------|
   | classifier_latency | <5s | ClassifierSignature 冗長度 |
   | rewriter_latency | <10s | QueryRewriterSignature 複雜度 |
   | executor_latency | <30s | 工具呼叫次數、回應生成 |

3. **分析慢階段的追蹤**
   ```
   /eval:analyze-traces [experiment-id]
   ```
   關注：
   - 每個階段的 Span 持續時間
   - 每個階段的 LLM 呼叫次數
   - 工具執行時間

4. **執行簽章分析**
   ```bash
   python -m evaluation.analyze_signatures
   ```
   尋找：
   - 高總描述字元數 (>2000)
   - 冗長的 OutputField 描述
   - 缺少範例 (導致更多重試)

5. **應用最佳化**

   **針對高分類器延遲：**
   - 簡化 ClassifierSignature docstring
   - 加入具體範例以減少歧義

   **針對高執行器延遲：**
   - 簡化 ExecutorSignature.answer 格式
   - 減少輸出格式要求
   - 考慮快取重複的工具呼叫

   **針對高總延遲：**
   - 審查是否所有階段都是必要的
   - 考慮在可能的情況下平行執行

6. **重新評估並比較**
   ```bash
   python run_quick_eval.py
   ```
   使用 `OptimizationHistory.compare_iterations()` 驗證改善

### 使用的指令
- `python run_quick_eval.py` - 執行帶有延遲評分的評估
- `/eval:analyze-traces` - 帶有計時細分的追蹤分析
- `python -m evaluation.analyze_signatures` - 簽章冗長度分析

### 成功指標
- 目標延遲：分類器 <5s，執行器 <30s，總計 <60s
- 準確率指標無退化
- 跨測試類別的一致改善

---

## 旅程 8："改進我的提示" - 系統化提示最佳化

**起點**：您的代理可以運作，但可以更準確
**目標**：透過評估系統化地提高提示品質

### 步驟

1. **建立基準**
   ```bash
   cd agents/tool_calling_dspy
   python run_quick_eval.py
   ```
   在 `optimization_history.json` 中記錄所有指標

2. **執行簽章分析**
   ```bash
   python -m evaluation.analyze_signatures
   ```
   審查報告以獲取：
   - 指標相關性 (哪些簽章影響哪些指標)
   - 每個簽章標記的具體問題

3. **依指標影響優先處理修復**

   | 指標 | 主要簽章 | 常見問題 |
   |--------|-------------------|---------------|
   | follows_instructions | ExecutorSignature | 冗長的答案格式、不明確的結構 |
   | tool_selection_accuracy | ClassifierSignature | 無範例、模稜兩可的工具描述 |
   | classifier_accuracy | ClassifierSignature | 冗長的 docstring、不明確的 query_type 映射 |

4. **一次應用一個修復**
   - 進行單一、針對性的更改
   - 在提交訊息中記錄更改
   - 在 optimization_history.json 中追蹤

5. **立即重新評估**
   ```bash
   python run_quick_eval.py
   ```
   - 如果改善 → 保留更改，移動到下一個修復
   - 如果退化 → 還原並嘗試不同方法
   - 如果不變 → 考慮修復是否必要

6. **迭代直到達到目標**

   | 指標 | 目標 |
   |--------|--------|
   | classifier_accuracy | 95%+ |
   | tool_selection_accuracy | 90%+ |
   | follows_instructions | 80%+ |

7. **記錄成功的最佳化**
   ```python
   from evaluation.optimization_history import OptimizationHistory

   history = OptimizationHistory()
   print(history.summary())
   ```

### 使用的指令
- `python run_quick_eval.py` - 執行評估
- `python -m evaluation.analyze_signatures` - 識別提示問題
- `/optimize:context --quick` - 完整最佳化循環 (當端點可用時)

### 成功指標
- 達到所有目標指標
- 沒有從基準退化
- 清楚記錄更改內容和原因
- 最佳化歷史顯示正向趨勢

---

## 快速參考

### 我在哪個旅程？

| 症狀 | 旅程 |
|---------|---------|
| "它以前可以運作" | 旅程 3 (回歸) |
| "它太慢了" | 旅程 7 (效能) |
| "它不夠準確" | 旅程 8 (提示最佳化) |

### 跨旅程的常用工具

| 工具 | 目的 |
|------|---------|
| `run_quick_eval.py` | 快速評估 (8 個測試案例) |
| `run_full_eval.py` | 完整評估 (23 個測試案例) |
| `analyze_signatures.py` | 簽章/提示分析 |
| `OptimizationHistory` | 追蹤迭代 |
| `/eval:analyze-traces` | 深度追蹤分析 |
| `/optimize:context` | 完整最佳化循環 |

### 指標目標

| 指標 | 目標 | 關鍵閾值 |
|--------|--------|-------------------|
| classifier_accuracy | 95%+ | <80% |
| tool_selection_accuracy | 90%+ | <70% |
| follows_instructions | 80%+ | <50% |
| executor_latency | <30s | >60s |
