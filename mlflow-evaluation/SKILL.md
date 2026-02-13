---
name: mlflow-evaluation
description: "用於代理開發的 MLflow 3 GenAI 評估。在以下情況使用：(1) 撰寫 mlflow.genai.evaluate() 程式碼，(2) 建立 @scorer 函數，(3) 從追蹤 (traces) 建立評估資料集，(4) 使用內建評分器 (Guidelines, Correctness, Safety, RetrievalGroundedness)，(5) 分析追蹤的延遲/錯誤/架構，(6) 優化代理上下文/提示/Token 使用，(7) 除錯評估失敗。涵蓋完整的評估工作流程：追蹤分析 -> 資料集建立 -> 評分器建立 -> 執行評估。"
---

# MLflow 3 GenAI 評估 (MLflow 3 GenAI Evaluation)

## 在撰寫任何程式碼之前

1. **閱讀 GOTCHAS.md** - 15+ 個導致失敗的常見錯誤
2. **閱讀 CRITICAL-interfaces.md** - 確切的 API 簽章和資料 Schema

## 端到端工作流程

根據您的目標遵循這些工作流程。每個步驟都指出要閱讀的參考文件。

### 工作流程 1：首次評估設定

適用於剛接觸 MLflow GenAI 評估或為新代理設定評估的使用者。

| 步驟 | 動作 | 參考文件 |
|------|--------|-----------------|
| 1 | 了解要評估什麼 | `user-journeys.md` (旅程 0：策略) |
| 2 | 學習 API 模式 | `GOTCHAS.md` + `CRITICAL-interfaces.md` |
| 3 | 建立初始資料集 | `patterns-datasets.md` (模式 1-4) |
| 4 | 選擇/建立評分器 | `patterns-scorers.md` + `CRITICAL-interfaces.md` (內建列表) |
| 5 | 執行評估 | `patterns-evaluation.md` (模式 1-3) |

### 工作流程 2：生產追蹤 -> 評估資料集

適用於從生產追蹤建立評估資料集。

| 步驟 | 動作 | 參考文件 |
|------|--------|-----------------|
| 1 | 搜尋並過濾追蹤 | `patterns-trace-analysis.md` (MCP 工具部分) |
| 2 | 分析追蹤品質 | `patterns-trace-analysis.md` (模式 1-7) |
| 3 | 標記追蹤以供納入 | `patterns-datasets.md` (模式 16-17) |
| 4 | 從追蹤建立資料集 | `patterns-datasets.md` (模式 6-7) |
| 5 | 加入預期結果/基本真值 | `patterns-datasets.md` (模式 2) |

### 工作流程 3：效能優化

適用於除錯緩慢或昂貴的代理執行。

| 步驟 | 動作 | 參考文件 |
|------|--------|-----------------|
| 1 | 依 Span 分析延遲 | `patterns-trace-analysis.md` (模式 4-6) |
| 2 | 分析 Token 使用量 | `patterns-trace-analysis.md` (模式 9) |
| 3 | 偵測上下文問題 | `patterns-context-optimization.md` (第 5 節) |
| 4 | 應用優化 | `patterns-context-optimization.md` (第 1-4, 6 節) |
| 5 | 重新評估以測量影響 | `patterns-evaluation.md` (模式 6-7) |

### 工作流程 4：回歸偵測

適用於比較代理版本並尋找回歸 (Regression)。

| 步驟 | 動作 | 參考文件 |
|------|--------|-----------------|
| 1 | 建立基準 (Baseline) | `patterns-evaluation.md` (模式 4：具名執行) |
| 2 | 執行當前版本 | `patterns-evaluation.md` (模式 1) |
| 3 | 比較指標 | `patterns-evaluation.md` (模式 6-7) |
| 4 | 分析失敗的追蹤 | `patterns-trace-analysis.md` (模式 7) |
| 5 | 除錯特定失敗 | `patterns-trace-analysis.md` (模式 8-9) |

### 工作流程 5：自訂評分器開發

適用於建立專案特定的評估指標。

| 步驟 | 動作 | 參考文件 |
|------|--------|-----------------|
| 1 | 了解評分器介面 | `CRITICAL-interfaces.md` (評分器部分) |
| 2 | 選擇評分器模式 | `patterns-scorers.md` (模式 4-11) |
| 3 | 用於多代理評分器 | `patterns-scorers.md` (模式 13-16) |
| 4 | 透過評估進行測試 | `patterns-evaluation.md` (模式 1) |

## 參考文件快速查詢

| 參考 | 用途 | 何時閱讀 |
|-----------|---------|--------------|
| `GOTCHAS.md` | 常見錯誤 | **務必先閱讀**，在撰寫程式碼之前 |
| `CRITICAL-interfaces.md` | API 簽章，Schemas | 撰寫任何評估程式碼時 |
| `patterns-evaluation.md` | 執行評估，比較 | 執行評估時 |
| `patterns-scorers.md` | 自訂評分器建立 | 當內建評分器不足時 |
| `patterns-datasets.md` | 資料集建立 | 準備評估資料時 |
| `patterns-trace-analysis.md` | 追蹤除錯 | 分析代理行為時 |
| `patterns-context-optimization.md` | Token/延遲修復 | 當代理緩慢或昂貴時 |
| `user-journeys.md` | 高層級工作流程 | 開始新評估專案時 |

## 關鍵 API 事實

- **使用：** `mlflow.genai.evaluate()` (不是 `mlflow.evaluate()`)
- **資料格式：** `{"inputs": {"query": "..."}}` (需要巢狀結構)
- **predict_fn:** 接收 `**unpacked kwargs` (不是字典)

完整列表請見 `GOTCHAS.md`。
