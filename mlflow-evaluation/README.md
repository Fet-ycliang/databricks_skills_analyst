# MLflow 評估 (MLflow Evaluation)

用於代理開發的 MLflow 3 GenAI 評估。在撰寫評估程式碼、建立評分器、從追蹤建立資料集、使用內建評分器、分析追蹤、優化代理上下文或除錯評估失敗時使用。

## 概述

此技能涵蓋完整的 MLflow 3 GenAI 評估工作流程，從追蹤分析到資料集建立、評分器建立和評估執行。當您需要使用 `mlflow.genai.evaluate()` 評估代理品質、建立自訂或內建評分器、從生產追蹤建構評估資料集或優化代理效能時，此技能會啟動。參考文件提供了評估生命週期每個階段的關鍵 API 介面、常見陷阱和工作程式碼模式。

## 包含內容

```
mlflow-evaluation/
  SKILL.md
  README.md
  references/
    CRITICAL-interfaces.md
    GOTCHAS.md
    patterns-context-optimization.md
    patterns-datasets.md
    patterns-evaluation.md
    patterns-scorers.md
    patterns-trace-analysis.md
    user-journeys.md
```

## 關鍵主題

- 核心 `mlflow.genai.evaluate()` API 和資料 Schema (輸入、輸出、預期結果)
- 內建評分器：Guidelines, Correctness, Safety, RelevanceToQuery, RetrievalGroundedness, ExpectationsGuidelines
- 自訂評分器開發：使用 `@scorer` 裝飾器、基於類別的評分器和 `make_judge`
- 評估資料集建立：從記憶體資料、生產追蹤、標記追蹤和 Unity Catalog 資料表
- 追蹤分析：Span 層級結構、延遲分析、瓶頸偵測、錯誤模式、工具/LLM 呼叫分析
- 上下文優化策略：工具結果管理、訊息歷史壓縮、提示工程
- 使用註冊的評分器和採樣設定進行生產監控
- 回歸偵測和版本比較工作流程
- 常見錯誤和陷阱 (記錄了 15+ 個失敗模式)

## 何時使用

- 撰寫 `mlflow.genai.evaluate()` 程式碼以評估代理品質
- 建立 `@scorer` 函數或基於類別的評分器以用於自訂指標
- 從生產追蹤或基本真值建立評估資料集
- 使用內建評分器 (Guidelines, Correctness, Safety, RetrievalGroundedness)
- 分析 MLflow 追蹤以了解延遲、錯誤或架構模式
- 優化代理上下文視窗、提示或 Token 使用量
- 除錯評估失敗或意外的評分器行為
- 比較代理版本以偵測回歸
- 為代理部署設定 CI/CD 品質閘門

## 相關技能

- [Databricks Docs](../databricks-docs/) -- 一般 Databricks 文件參考
- [Model Serving](../model-serving/) -- 將模型和代理部署到服務端點
- [Agent Bricks](../agent-bricks/) -- 建立可使用此技能評估的代理
- [Databricks Python SDK](../databricks-python-sdk/) -- 與 MLflow API 一起使用的 SDK 模式
- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 用於託管評估資料集的 Unity Catalog 資料表

## 資源

- [MLflow GenAI Evaluation Documentation](https://docs.databricks.com/en/mlflow/llm-evaluate.html)
- [MLflow Scorers Documentation](https://docs.databricks.com/en/mlflow/llm-evaluate-scorers.html)
- [MLflow Tracing Documentation](https://docs.databricks.com/en/mlflow/mlflow-tracing.html)
- [MLflow Python Package (PyPI)](https://pypi.org/project/mlflow/)
