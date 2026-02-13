# 知識助理（KA）

知識助理是基於文件的問答系統，使用 RAG（檢索增強生成）從索引文件中回答問題。

## 什麼是知識助理？

KA 連接到儲存在 Unity Catalog 磁碟區中的文件，並允許使用者提出自然語言問題。系統會：

1. **索引**磁碟區中的所有文件（PDF、文字檔案等）
2. **檢索**提問時的相關片段
3. **生成**使用檢索到的上下文的答案

## 何時使用

在以下情況使用知識助理：
- 您有一組文件（政策、手冊、指南、報告）
- 使用者需要尋找特定資訊而無需閱讀整份文件
- 您想要為文件提供對話式介面

## 先決條件

在建立 KA 之前，您需要在 Unity Catalog 磁碟區中準備文件：

**選項 1：使用現有文件**
- 手動或透過 SDK 將 PDF/文字檔案上傳到磁碟區

**選項 2：生成合成文件**
- 使用 `unstructured-pdf-generation` 技能建立逼真的 PDF 文件
- 每個 PDF 都會獲得一個配套的 JSON 檔案，其中包含用於評估的問題/指南配對

## 建立知識助理

使用 `create_or_update_ka` 工具：

- `name`："人力資源政策助理"
- `volume_path`："/Volumes/my_catalog/my_schema/raw_data/hr_docs"
- `description`："回答有關人力資源政策和程序的問題"
- `instructions`："要樂於助人，並在回答時始終引用特定的政策文件。如果您不確定，請說明。"

該工具將：
1. 使用指定的磁碟區作為知識來源建立 KA
2. 掃描磁碟區中的 JSON 檔案以尋找範例問題（來自 PDF 生成）
3. 在端點準備就緒後將範例排入佇列以新增

## 佈建時間表

建立後，KA 端點需要佈建：

| 狀態 | 意義 | 持續時間 |
|--------|---------|----------|
| `PROVISIONING` | 正在建立端點 | 2-5 分鐘 |
| `ONLINE` | 準備使用 | - |
| `OFFLINE` | 目前未執行 | - |

使用 `get_ka` 檢查狀態：

- `tile_id`："<來自 create 的 tile_id>"

## 新增範例問題

範例問題有助於：
- **評估**：測試 KA 是否正確回答
- **使用者引導**：向使用者展示可以提出什麼問題

### 自動（來自 PDF 生成）

如果您使用了 `generate_pdf_documents`，每個 PDF 都有一個配套的 JSON，包含：
```json
{
  "question": "公司的遠端工作政策是什麼？",
  "guideline": "應該提到每週至少 3 天到辦公室的要求"
}
```

當 `add_examples_from_volume=true`（預設）時，這些會自動新增。

### 手動

如果需要，也可以在 `create_or_update_ka` 呼叫中指定範例。

## 最佳實踐

### 文件組織

- **每個主題一個磁碟區**：例如，`/Volumes/catalog/schema/raw_data/hr_docs`、`/Volumes/catalog/schema/raw_data/tech_docs`
- **清晰的命名**：以描述性方式命名檔案，以便識別片段

### 指示

好的指示可以提高答案品質：

```
要樂於助人且專業。在回答時：
1. 始終引用特定的文件和章節
2. 如果多個文件相關，請提及所有文件
3. 如果資訊不在文件中，請明確說明
4. 對多部分答案使用項目符號
```

### 更新內容

要更新索引的文件：
1. 在磁碟區中新增/移除/修改檔案
2. 使用相同的名稱和 `tile_id` 呼叫 `create_or_update_ka`
3. KA 將重新索引更新的內容

## 範例工作流程

1. **使用 `unstructured-pdf-generation` 技能生成 PDF 文件**：
   - 在 `/Volumes/catalog/schema/raw_data/pdf_documents` 中建立 PDF
   - 建立帶有問題/指南配對的 JSON 檔案

2. **建立知識助理**：
   - `name`："我的文件助理"
   - `volume_path`："/Volumes/catalog/schema/raw_data/pdf_documents"

3. **等待 ONLINE 狀態**（2-5 分鐘）

4. **範例會自動從 JSON 檔案新增**

5. **在 Databricks UI 中測試 KA**

## 在多代理監督器中使用 KA

知識助理可以用作多代理監督器（MAS）中的代理。每個 KA 都有一個關聯的模型服務端點。

### 尋找端點名稱

使用 `get_ka` 檢索 KA 詳細資訊。回應包括：
- `tile_id`：KA 的唯一識別碼
- `name`：KA 名稱（已清理）
- `endpoint_status`：目前狀態（ONLINE、PROVISIONING 等）

端點名稱遵循此模式：`ka-{tile_id}-endpoint`

### 依名稱尋找 KA

如果您知道 KA 名稱但不知道 tile_id，請使用 `find_ka_by_name`：

```python
find_ka_by_name(name="HR_Policy_Assistant")
# 返回：{"found": True, "tile_id": "01abc...", "name": "HR_Policy_Assistant", "endpoint_name": "ka-01abc...-endpoint"}
```

### 範例：將 KA 新增到 MAS

```python
# 首先，尋找 KA
ka_result = find_ka_by_name(name="HR_Policy_Assistant")

# 然後在 MAS 中使用它
create_or_update_mas(
    name="支援 MAS",
    agents=[
        {
            "name": "hr_agent",
            "endpoint_name": ka_result["endpoint_name"],
            "description": "從員工手冊回答人力資源政策問題"
        }
    ]
)
```

## 疑難排解

### 端點停留在 PROVISIONING 狀態

- 檢查工作區容量和配額
- 驗證磁碟區路徑是否可存取
- 在進一步調查之前等待最多 10 分鐘

### 文件未被索引

- 確保檔案為支援的格式（PDF、TXT、MD）
- 檢查磁碟區中的檔案權限
- 驗證磁碟區路徑是否正確

### 答案品質不佳

- 新增更具體的指示
- 確保文件結構良好
- 考慮將大型文件拆分為較小的檔案
