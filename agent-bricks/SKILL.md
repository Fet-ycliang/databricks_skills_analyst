---
name: agent-bricks
description: "建立和管理 Databricks Agent Bricks：用於文件問答的知識助理（KA）、用於 SQL 探索的 Genie Spaces，以及用於多代理編排的多代理監督器（MAS）。在 Databricks 上建立對話式 AI 應用程式時使用。"
---

# Agent Bricks

建立和管理 Databricks Agent Bricks - 用於建立對話式應用程式的預建 AI 元件。

## 概述

Agent Bricks 是 Databricks 中三種類型的預建 AI 磚塊：

| 磚塊 | 用途 | 資料來源 |
|-------|---------|-------------|
| **知識助理（KA）** | 使用 RAG 的基於文件的問答 | 磁碟區中的 PDF/文字檔案 |
| **Genie Space** | 自然語言轉 SQL | Unity Catalog 資料表 |
| **多代理監督器（MAS）** | 多代理編排 | 模型服務端點 |

## 先決條件

在建立 Agent Bricks 之前，請確保您擁有所需的資料：

### 對於知識助理
- **磁碟區中的文件**：儲存在 Unity Catalog 磁碟區中的 PDF、文字或其他檔案
- 如果需要，使用 `unstructured-pdf-generation` 技能生成合成文件

### 對於 Genie Spaces
- **請參閱 `databricks-genie` 技能**以取得全面的 Genie Space 指導
- Unity Catalog 中包含要探索的資料的資料表
- 使用 `synthetic-data-generation` 技能生成原始資料
- 使用 `spark-declarative-pipelines` 技能建立資料表

### 對於多代理監督器
- **模型服務端點**：已部署的代理端點（KA 端點、自訂代理、微調模型）
- **Genie Spaces**：現有的 Genie spaces 可以直接用作基於 SQL 查詢的代理
- 在同一個 MAS 中混合和匹配基於端點和基於 Genie 的代理

## MCP 工具

### 知識助理工具

**create_or_update_ka** - 建立或更新知識助理
- `name`：KA 的名稱
- `volume_path`：文件路徑（例如，`/Volumes/catalog/schema/volume/folder`）
- `description`：（選用）KA 的功能
- `instructions`：（選用）KA 應該如何回答
- `tile_id`：（選用）要更新的現有 tile_id
- `add_examples_from_volume`：（選用，預設：true）從 JSON 檔案自動新增範例

**get_ka** - 取得知識助理詳細資訊
- `tile_id`：KA tile ID

**find_ka_by_name** - 依名稱尋找知識助理
- `name`：要尋找的 KA 的確切名稱
- 返回：`tile_id`、`name`、`endpoint_name`、`endpoint_status`
- 當您知道名稱但不知道 tile_id 時，使用此工具查找現有的 KA

**delete_ka** - 刪除知識助理
- `tile_id`：要刪除的 KA tile ID

### Genie Space 工具

**如需全面的 Genie 指導，請使用 `databricks-genie` 技能。**

可用的基本工具：

- `create_or_update_genie` - 建立或更新 Genie Space
- `get_genie` - 取得 Genie Space 詳細資訊
- `delete_genie` - 刪除 Genie Space

請參閱 `databricks-genie` 技能以了解：
- 資料表檢查工作流程
- 範例問題最佳實踐
- 精選（指示、認證查詢）

**重要**：Genie spaces 沒有系統資料表（例如，`system.ai.genie_spaces` 不存在）。要依名稱尋找 Genie space，請使用 `find_genie_by_name` 工具。

### 多代理監督器工具

**create_or_update_mas** - 建立或更新多代理監督器
- `name`：MAS 的名稱
- `agents`：代理配置列表，每個包含：
  - `name`：代理識別碼（必要）
  - `description`：此代理處理什麼 - 對路由至關重要（必要）
  - `ka_tile_id`：知識助理 tile ID（用於文件問答代理 - 建議用於 KA）
  - `genie_space_id`：Genie space ID（用於基於 SQL 的資料代理）
  - `endpoint_name`：模型服務端點名稱（用於自訂代理）
  - 注意：提供以下其中一個：`ka_tile_id`、`genie_space_id` 或 `endpoint_name`
- `description`：（選用）MAS 的功能
- `instructions`：（選用）監督器的路由指示
- `tile_id`：（選用）要更新的現有 tile_id
- `examples`：（選用）帶有 `question` 和 `guideline` 欄位的範例問題列表

**get_mas** - 取得多代理監督器詳細資訊
- `tile_id`：MAS tile ID

**find_mas_by_name** - 依名稱尋找多代理監督器
- `name`：要尋找的 MAS 的確切名稱
- 返回：`tile_id`、`name`、`endpoint_status`、`agents_count`
- 當您知道名稱但不知道 tile_id 時，使用此工具查找現有的 MAS

**delete_mas** - 刪除多代理監督器
- `tile_id`：要刪除的 MAS tile ID

## 典型工作流程

### 1. 生成來源資料

在建立 Agent Bricks 之前，生成所需的來源資料：

**對於 KA（文件問答）**：
```
1. 使用 `unstructured-pdf-generation` 技能生成 PDF
2. PDF 會與配套的 JSON 檔案（問題/指南配對）一起儲存到磁碟區
```

**對於 Genie（SQL 探索）**：
```
1. 使用 `synthetic-data-generation` 技能建立原始 parquet 資料
2. 使用 `spark-declarative-pipelines` 技能建立 bronze/silver/gold 資料表
```

### 2. 建立 Agent Brick

使用適當的 `create_or_update_*` 工具與您的資料來源。

### 3. 等待佈建

新建立的 KA 和 MAS 磚塊需要時間佈建。端點狀態將進展：
- `PROVISIONING` - 正在建立（可能需要 2-5 分鐘）
- `ONLINE` - 準備使用
- `OFFLINE` - 未執行

### 4. 新增範例（自動）

對於 KA，如果 `add_examples_from_volume=true`，範例會在端點為 `ONLINE` 時自動從磁碟區中的 JSON 檔案提取並新增。

## 最佳實踐

1. **使用有意義的名稱**：名稱會自動清理（空格變成底線）
2. **提供說明**：幫助使用者理解磚塊的功能
3. **新增指示**：引導 AI 的行為和語氣
4. **包含範例問題**：向使用者展示如何與磚塊互動
5. **使用工作流程**：先生成資料，然後建立磚塊

## 另請參閱

- `1-knowledge-assistants.md` - 詳細的 KA 模式和範例
- `databricks-genie` 技能 - 詳細的 Genie 模式、精選和範例
- `3-multi-agent-supervisors.md` - 詳細的 MAS 模式和範例
