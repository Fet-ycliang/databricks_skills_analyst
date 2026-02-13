# Databricks Model Serving

將 MLflow 模型和 AI 代理部署到可擴展的 REST API 端點。

## 概述

此技能提供將經典 ML 模型、自訂 PyFunc 模型和 GenAI 代理（ResponsesAgent/LangGraph）部署到 Databricks Model Serving 端點的端到端指南。當您需要在 Databricks 上記錄、註冊、部署或查詢任何模型類型時，此技能會啟動。九個參考文件涵蓋從訓練到生產的每個階段，包括工具整合、非同步部署和套件管理。

## 包含內容

```
model-serving/
├── SKILL.md                    # 主要技能參考：決策矩陣、MCP 工具、快速入門
├── 1-classical-ml.md           # sklearn、xgboost、autolog 和透過 SDK/UI 部署
├── 2-custom-pyfunc.md          # 帶有預處理、簽章和工件的自訂 PythonModel
├── 3-genai-agents.md           # ResponsesAgent 和 LangGraph 代理模式
├── 4-tools-integration.md      # UC 函數、向量搜尋和自訂 @tool 整合
├── 5-development-testing.md    # 基於 MCP 的上傳、安裝、測試和迭代工作流程
├── 6-logging-registration.md   # mlflow.pyfunc.log_model、資源、Unity Catalog 註冊
├── 7-deployment.md             # 代理的非同步基於作業部署、ML 的 SDK 部署
├── 8-querying-endpoints.md     # MCP 工具、Python SDK、REST API 和 OpenAI 相容查詢
├── 9-package-requirements.md   # DBR 版本、pip 安裝、已測試的套件組合
```

## 關鍵主題

- 使用 MLflow autolog 的經典 ML 部署（sklearn、xgboost、LightGBM、PyTorch）
- 帶有預處理、簽章和外部相依性的自訂 PyFunc 模型
- 使用 MLflow 3 ResponsesAgent 和 LangGraph 的 GenAI 代理
- 工具整合：Unity Catalog 函數、向量搜尋檢索器、自訂工具
- 基於 MCP 的開發和測試工作流程（上傳、安裝、執行、迭代）
- 帶有資源宣告的模型記錄和 Unity Catalog 註冊
- 非同步基於作業的部署以避免 MCP 逾時
- 透過 MCP 工具、Python SDK、REST API 和 OpenAI 相容客戶端查詢端點
- 套件需求和 DBR 版本相容性（建議 DBR 16.1+）
- ResponsesAgent 輸出格式（輔助方法 vs 原始字典）

## 何時使用

- 您正在將 ML 模型（sklearn、xgboost、自訂 PyFunc）部署到服務端點
- 您正在使用 ResponsesAgent 或 LangGraph 建立和部署 GenAI 代理
- 您需要將 Unity Catalog 函數或向量搜尋整合到代理中
- 您正在將模型記錄並註冊到 Unity Catalog
- 您需要查詢已部署的模型或代理端點
- 您正在檢查端點狀態或疑難排解部署問題
- 您需要確定代理開發的正確套件版本

## 相關技能

- [Agent Bricks](../agent-bricks/) -- 部署到模型服務端點的預建代理磚塊
- [Vector Search](../vector-search/) -- 建立用作代理中檢索器工具的向量索引
- [Databricks Genie](../databricks-genie/) -- Genie Spaces 可以在多代理設定中作為代理
- [MLflow Evaluation](../mlflow-evaluation/) -- 在部署前評估模型和代理品質
- [Databricks Jobs](../databricks-jobs/) -- 用於代理端點的基於作業的非同步部署

## 資源

- [Model Serving 文件](https://docs.databricks.com/machine-learning/model-serving/)
- [MLflow 3 ResponsesAgent](https://mlflow.org/docs/latest/llms/responses-agent-intro/)
- [Agent Framework](https://docs.databricks.com/generative-ai/agent-framework/)
