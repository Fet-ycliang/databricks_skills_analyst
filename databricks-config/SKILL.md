---
name: databricks-config
description: 為 Databricks Connect、Databricks CLI 和 Databricks SDK 配置 Databricks 設定檔和驗證。
---

在 ~/.databrickscfg 中配置 Databricks 設定檔，以便與 Databricks Connect 一起使用。

**用法：** `/databricks-config [profile_name|workspace_host]`

範例：
- `/databricks-config` - 配置 DEFAULT 設定檔（互動式）
- `/databricks-config DEFAULT` - 配置 DEFAULT 設定檔
- `/databricks-config my-workspace` - 配置名為 "my-workspace" 的設定檔
- `/databricks-config https://adb-1234567890123456.7.azuredatabricks.net/` - 使用工作區主機 URL 配置

## 任務

1. 確定設定檔和主機：
   - 如果提供了參數且以 `https://` 開頭，將其視為工作區主機：
     - 從主機擷取設定檔名稱（例如，`adb-1234567890123456.7.azuredatabricks.net` → `adb-1234567890123456`，`my-company-dev.cloud.databricks.com` → `my-company-dev`）
     - 使用此作為設定檔名稱，並使用提供的主機配置它
   - 如果提供了參數且不以 `https://` 開頭，將其視為設定檔名稱
   - 如果未提供參數，詢問使用者想要配置哪個設定檔（預設：DEFAULT）

2. 使用確定的設定檔名稱執行 `databricks auth login -p <profile>`
   - 如果提供了工作區主機，將 `--host <workspace_host>` 新增到命令
   - 這確保驗證完成且設定檔可以運作
3. 檢查設定檔是否存在於 ~/.databrickscfg 中
4. 要求使用者選擇以下運算選項之一：
   - **叢集 ID**：為互動式/通用叢集提供特定的叢集 ID
   - **無伺服器**：使用無伺服器運算（設定 `serverless_compute_id = auto`）
5. 使用選定的配置更新 ~/.databrickscfg 中的設定檔
6. 透過顯示更新的設定檔區段來驗證配置

## 重要注意事項

- 使用 AskUserQuestion 工具將運算選項呈現為選擇
- 只新增以下其中一個：`cluster_id` 或 `serverless_compute_id`（絕不同時新增）
- 對於無伺服器，設定 `serverless_compute_id = auto`（不只是 `serverless = true`）
- 保留設定檔中的所有現有設定（host、auth_type 等）
- 以適當的間距一致地格式化配置檔案
- `databricks auth login` 命令將開啟瀏覽器進行 OAuth 驗證
- **安全性：絕不以純文字列印權杖值**
  - 顯示配置時，隱藏任何 `token` 欄位值（例如，`token = [已隱藏]`）
  - 告知使用者可以在 `~/.databrickscfg` 查看完整配置
  - 這適用於任何顯示設定檔配置的輸出

## 配置範例

**使用叢集 ID：**
```
[DEFAULT]
host       = https://adb-123456789.11.azuredatabricks.net/
cluster_id = 1217-064531-c9c3ngyn
auth_type  = databricks-cli
```

**使用無伺服器：**
```
[DEFAULT]
host                  = https://adb-123456789.11.azuredatabricks.net/
serverless_compute_id = auto
auth_type             = databricks-cli
```

**使用權杖（顯示為已隱藏）：**
```
[DEFAULT]
host       = https://adb-123456789.11.azuredatabricks.net/
token      = [已隱藏]
cluster_id = 1217-064531-c9c3ngyn

在以下位置查看完整配置：~/.databrickscfg
```
