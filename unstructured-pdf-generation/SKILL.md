---
name: unstructured-pdf-generation
description: "為 RAG 和非結構化資料使用案例生成合成 PDF 文件。在建立測試 PDF、示範文件或檢索系統的評估資料集時使用。"
---

# 非結構化 PDF 生成

使用 LLM 為 RAG（檢索增強生成）和非結構化資料使用案例生成逼真的合成 PDF 文件。

## 概述

此技能使用 `generate_pdf_documents` MCP 工具建立專業的 PDF 文件，包含：
- 基於您的描述的 LLM 生成內容
- 帶有問題和評估指南的配套 JSON 檔案（用於 RAG 測試）
- 自動上傳到 Unity Catalog 磁碟區

## 快速入門

使用 `generate_pdf_documents` MCP 工具：
- `catalog`："my_catalog"
- `schema`："my_schema"
- `description`："雲端基礎設施平台的技術文件，包括設定指南、疑難排解程序和 API 參考。"
- `count`：10

這會生成 10 個 PDF 文件並將它們儲存到 `/Volumes/my_catalog/my_schema/raw_data/pdf_documents/`（使用預設磁碟區和資料夾）。

### 使用自訂位置

使用 `generate_pdf_documents` MCP 工具：
- `catalog`："my_catalog"
- `schema`："my_schema"
- `description`："人力資源政策文件..."
- `count`：10
- `volume`："custom_volume"
- `folder`："hr_policies"
- `overwrite_folder`：true

## 參數

| 參數 | 類型 | 必要 | 預設值 | 說明 |
|-----------|------|----------|---------|-------------|
| `catalog` | string | 是 | - | Unity Catalog 名稱 |
| `schema` | string | 是 | - | 結構描述名稱 |
| `description` | string | 是 | - | PDF 應包含內容的詳細描述 |
| `count` | int | 是 | - | 要生成的 PDF 數量 |
| `volume` | string | 否 | `raw_data` | 磁碟區名稱（如果不存在則建立） |
| `folder` | string | 否 | `pdf_documents` | 磁碟區內用於輸出檔案的資料夾 |
| `doc_size` | string | 否 | `MEDIUM` | 文件大小：`SMALL`（約 1 頁）、`MEDIUM`（約 5 頁）、`LARGE`（約 10+ 頁） |
| `overwrite_folder` | bool | 否 | `false` | 如果為 true，則先刪除現有資料夾內容 |

### 文件大小指南

- **SMALL**：約 1 頁，簡潔內容。最適合快速示範或測試。
- **MEDIUM**：約 4-6 頁，全面涵蓋。大多數使用案例的良好平衡。
- **LARGE**：約 10+ 頁，詳盡的文件。用於徹底的 RAG 評估。

## 輸出檔案

對於每個文件，工具會建立兩個檔案：

1. **PDF 檔案**（`<model_id>.pdf`）：生成的文件
2. **JSON 檔案**（`<model_id>.json`）：用於 RAG 評估的中繼資料

### JSON 結構

```json
{
  "title": "API 驗證指南",
  "category": "技術",
  "pdf_path": "/Volumes/catalog/schema/volume/folder/doc_001.pdf",
  "question": "API 支援哪些驗證方法？",
  "guideline": "答案應該提到 OAuth 2.0、API 金鑰和 JWT 權杖及其使用案例。"
}
```

## 常見模式

### 模式 1：人力資源政策文件

使用 `generate_pdf_documents` MCP 工具：
- `catalog`："ai_dev_kit"
- `schema`："hr_demo"
- `description`："科技公司的人力資源政策文件，包括員工手冊、休假政策、績效評估程序、福利指南和工作場所行為準則。"
- `count`：15
- `folder`："hr_policies"
- `overwrite_folder`：true

### 模式 2：技術文件

使用 `generate_pdf_documents` MCP 工具：
- `catalog`："ai_dev_kit"
- `schema`："tech_docs"
- `description`："SaaS 分析平台的技術文件，包括安裝指南、API 參考、疑難排解程序、安全最佳實踐和整合教學。"
- `count`：20
- `folder`："product_docs"
- `overwrite_folder`：true

### 模式 3：財務報告

使用 `generate_pdf_documents` MCP 工具：
- `catalog`："ai_dev_kit"
- `schema`："finance_demo"
- `description`："零售公司的財務文件，包括季度報告、費用政策、預算指南和稽核程序。"
- `count`：12
- `folder`："reports"
- `overwrite_folder`：true

### 模式 4：培訓材料

使用 `generate_pdf_documents` MCP 工具：
- `catalog`："ai_dev_kit"
- `schema`："training"
- `description`："新軟體開發人員的培訓材料，包括入職指南、編碼標準、程式碼審查程序和部署工作流程。"
- `count`：8
- `folder`："courses"
- `overwrite_folder`：true

## 工作流程

1. **詢問目的地**：預設為 `ai_dev_kit` 目錄，詢問使用者結構描述名稱
2. **取得描述**：詢問他們需要什麼類型的文件
3. **生成 PDF**：使用適當的參數呼叫 `generate_pdf_documents` MCP 工具
4. **驗證輸出**：檢查磁碟區路徑中的生成檔案

## 最佳實踐

1. **詳細描述**：您的描述越具體，生成的內容就越好
   - 不好："生成一些人力資源文件"
   - 好："科技公司的人力資源政策文件，包括涵蓋遠端工作政策的員工手冊、包含 PTO 和病假詳細資訊的休假政策、包含季度和年度週期的績效評估程序，以及工作場所行為準則"

2. **適當的數量**：
   - 用於示範：5-10 個文件
   - 用於 RAG 測試：15-30 個文件
   - 用於全面評估：50+ 個文件

3. **資料夾組織**：使用指示內容類型的描述性資料夾名稱
   - `hr_policies/`
   - `technical_docs/`
   - `training_materials/`

4. **使用 overwrite_folder**：重新生成時設定為 `true` 以確保乾淨狀態

## 與 RAG 管線整合

生成的 JSON 檔案專為 RAG 評估而設計：

1. **擷取 PDF**：使用 PDF 檔案作為向量資料庫的來源文件
2. **測試檢索**：使用 `question` 欄位查詢您的 RAG 系統
3. **評估答案**：使用 `guideline` 欄位評估 RAG 回應是否正確

範例評估工作流程：
```python
# 從 JSON 檔案載入問題
questions = load_json_files(f"/Volumes/{catalog}/{schema}/{volume}/{folder}/*.json")

for q in questions:
    # 查詢 RAG 系統
    response = rag_system.query(q["question"])

    # 使用指南評估
    is_correct = evaluate_response(response, q["guideline"])
```

## 環境配置

工具需要透過環境變數進行 LLM 配置：

```bash
# Databricks Foundation Models（預設）
LLM_PROVIDER=DATABRICKS
DATABRICKS_MODEL=databricks-meta-llama-3-3-70b-instruct

# 或 Azure OpenAI
LLM_PROVIDER=AZURE
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **"未配置 LLM 端點"** | 設定 `DATABRICKS_MODEL` 或 `AZURE_OPENAI_DEPLOYMENT` 環境變數 |
| **"磁碟區不存在"** | 工具會自動建立磁碟區；確保您有 CREATE VOLUME 權限 |
| **"PDF 生成逾時"** | 減少 `count` 或檢查 LLM 端點可用性 |
| **內容品質低** | 提供更詳細的 `description`，包含特定主題和文件類型 |
