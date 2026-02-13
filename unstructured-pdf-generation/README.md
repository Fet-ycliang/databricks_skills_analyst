# 非結構化 PDF 生成

為 RAG 和非結構化資料使用案例生成合成 PDF 文件。

## 概述

此技能使用 `generate_pdf_documents` MCP 工具建立逼真的、由 LLM 生成的 PDF 文件，並附帶配套的 JSON 評估檔案，然後將它們上傳到 Unity Catalog 磁碟區。當您需要測試 PDF、示範文件或檢索系統的評估資料集時，此技能會啟動。生成的 JSON 檔案包含問題/指南配對，可立即啟用自動化 RAG 管線評估。

## 包含內容

```
unstructured-pdf-generation/
└── SKILL.md    # 完整參考：參數、模式、輸出格式和整合指南
```

## 關鍵主題

- 根據描述生成由 LLM 產生內容的合成 PDF
- 帶有問題/指南配對的配套 JSON 檔案，用於 RAG 評估
- 自動上傳到 Unity Catalog 磁碟區
- 可配置的文件大小（SMALL、MEDIUM、LARGE）
- 常見模式：人力資源政策、技術文件、財務報告、培訓材料
- 與 RAG 評估管線整合
- LLM 提供者配置（Databricks Foundation Models 或 Azure OpenAI）

## 何時使用

- 您需要用於知識助理的測試或示範 PDF 文件
- 您正在建立 RAG 管線，需要帶有真實問題的評估資料集
- 您想要使用逼真的合成文件填充 Unity Catalog 磁碟區
- 您正在原型設計文件問答系統，需要快速取得內容
- 您需要大規模生成文件（5 到 50+ 個），並具有特定領域焦點

## 相關技能

- [Agent Bricks](../agent-bricks/) -- 建立擷取生成的 PDF 的知識助理
- [Vector Search](../vector-search/) -- 為語義搜尋和 RAG 索引生成的文件
- [Synthetic Data Generation](../synthetic-data-generation/) -- 生成結構化表格資料（非結構化 PDF 的補充）
- [MLflow Evaluation](../mlflow-evaluation/) -- 使用生成的問題/指南配對評估 RAG 系統

## 資源

- [Databricks 磁碟區文件](https://docs.databricks.com/volumes/)
- [Databricks RAG 應用程式](https://docs.databricks.com/generative-ai/retrieval-augmented-generation.html)
