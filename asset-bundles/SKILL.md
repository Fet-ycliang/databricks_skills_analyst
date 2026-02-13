---
name: asset-bundles
description: "使用最佳實踐建立和配置 Databricks Asset Bundles (DABs)，用於多環境部署。在以下情況使用：(1) 建立新的 DAB 專案，(2) 新增資源（儀表板、管線、作業、警報），(3) 配置多環境部署，(4) 設定權限，(5) 部署或執行 bundle 資源"
---

# Databricks Asset Bundle (DABs) 撰寫器

## 概述
建立 DABs 用於多環境部署（dev/staging/prod）。

## 參考文件

- **[SDP_guidance.md](SDP_guidance.md)** - Spark 宣告式管線配置
- **[alerts_guidance.md](alerts_guidance.md)** - SQL 警報結構描述（重要 - API 不同）

## Bundle 結構

```
project/
├── databricks.yml           # 主要配置 + 目標
├── resources/*.yml          # 資源定義
└── src/                     # 程式碼/儀表板檔案
```

### 主要配置 (databricks.yml)

```yaml
bundle:
  name: project-name

include:
  - resources/*.yml

variables:
  catalog:
    default: "default_catalog"
  schema:
    default: "default_schema"
  warehouse_id:
    lookup:
      warehouse: "Shared SQL Warehouse"

targets:
  dev:
    default: true
    mode: development
    workspace:
      profile: dev-profile
    variables:
      catalog: "dev_catalog"
      schema: "dev_schema"

  prod:
    mode: production
    workspace:
      profile: prod-profile
    variables:
      catalog: "prod_catalog"
      schema: "prod_schema"
```

### 儀表板資源

**Databricks CLI 0.281.0（2026 年 1 月）新增對 dataset_catalog 和 dataset_schema 參數的支援**

```yaml
resources:
  dashboards:
    dashboard_name:
      display_name: "[${bundle.target}] Dashboard Title"
      file_path: ../src/dashboards/dashboard.lvdash.json  # 相對於 resources/
      warehouse_id: ${var.warehouse_id}
      dataset_catalog: ${var.catalog} # 儀表板中所有資料集使用的預設目錄（如果查詢中未另外指定）
      dataset_schema: ${var.schema} # 儀表板中所有資料集使用的預設結構描述（如果查詢中未另外指定）
      permissions:
        - level: CAN_RUN
          group_name: "users"
```

**權限層級**：`CAN_READ`、`CAN_RUN`、`CAN_EDIT`、`CAN_MANAGE`

### 管線

**請參閱 [SDP_guidance.md](SDP_guidance.md)** 以了解管線配置

### SQL 警報

**請參閱 [alerts_guidance.md](alerts_guidance.md)** - 警報結構描述與其他資源有顯著差異

### 作業資源

```yaml
resources:
  jobs:
    job_name:
      name: "[${bundle.target}] Job Name"
      tasks:
        - task_key: "main_task"
          notebook_task:
            notebook_path: ../src/notebooks/main.py  # 相對於 resources/
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 2
      schedule:
        quartz_cron_expression: "0 0 9 * * ?"
        timezone_id: "America/Los_Angeles"
      permissions:
        - level: CAN_VIEW
          group_name: "users"
```

**權限層級**：`CAN_VIEW`、`CAN_MANAGE_RUN`、`CAN_MANAGE`

⚠️ **無法修改作業上的 "admins" 群組權限** - 使用前請驗證自訂群組是否存在

### 路徑解析

⚠️ **重要**：路徑取決於檔案位置：

| 檔案位置 | 路徑格式 | 範例 |
|--------------|-------------|---------|
| `resources/*.yml` | `../src/...` | `../src/dashboards/file.json` |
| `databricks.yml` targets | `./src/...` | `./src/dashboards/file.json` |

**原因**：`resources/` 檔案深度為一層，因此使用 `../` 到達 bundle 根目錄。`databricks.yml` 位於根目錄，因此使用 `./`

### 磁碟區資源

```yaml
resources:
  volumes:
    my_volume:
      catalog_name: ${var.catalog}
      schema_name: ${var.schema}
      name: "volume_name"
      volume_type: "MANAGED"
```

⚠️ **磁碟區使用 `grants` 而非 `permissions`** - 與其他資源的格式不同

### 應用程式資源

**Databricks CLI 0.239.0（2025 年 1 月）新增應用程式資源支援**

DABs 中的應用程式具有最小配置 - 環境變數定義在來源目錄的 `app.yaml` 中，而非 databricks.yml 中。

#### 從現有應用程式生成（建議）

```bash
# 從現有 CLI 部署的應用程式生成 bundle 配置
databricks bundle generate app --existing-app-name my-app --key my_app --profile DEFAULT

# 這會建立：
# - resources/my_app.app.yml（最小資源定義）
# - src/app/（下載的來源檔案，包括 app.yaml）
```

#### 手動配置

**resources/my_app.app.yml:**
```yaml
resources:
  apps:
    my_app:
      name: my-app-${bundle.target}        # 環境特定命名
      description: "My application"
      source_code_path: ../src/app         # 相對於 resources/ 目錄
```

**src/app/app.yaml:**（環境變數放在這裡）
```yaml
command:
  - "python"
  - "dash_app.py"

env:
  - name: USE_MOCK_BACKEND
    value: "false"
  - name: DATABRICKS_WAREHOUSE_ID
    value: "your-warehouse-id"
  - name: DATABRICKS_CATALOG
    value: "main"
  - name: DATABRICKS_SCHEMA
    value: "my_schema"
```

**databricks.yml:**
```yaml
bundle:
  name: my-bundle

include:
  - resources/*.yml

variables:
  warehouse_id:
    default: "default-warehouse-id"

targets:
  dev:
    default: true
    mode: development
    workspace:
      profile: dev-profile
    variables:
      warehouse_id: "dev-warehouse-id"
```

#### 與其他資源的主要差異

| 方面 | 應用程式 | 其他資源 |
|--------|------|-----------------|
| **環境變數** | 在 `app.yaml`（來源目錄） | 在 databricks.yml 或資源檔案中 |
| **配置** | 最小（名稱、說明、路徑） | 廣泛（任務、叢集等） |
| **來源路徑** | 指向應用程式目錄 | 指向特定檔案 |

⚠️ **重要**：當來源程式碼在專案根目錄（而非 src/app）時，在資源檔案中使用 `source_code_path: ..`

### 其他資源

DABs 支援結構描述、模型、實驗、叢集、倉儲等。使用 `databricks bundle schema` 檢查結構描述。

**參考**：[DABs 資源類型](https://docs.databricks.com/dev-tools/bundles/resources)

## 常用命令

### 驗證
```bash
databricks bundle validate                    # 驗證預設目標
databricks bundle validate -t prod           # 驗證特定目標
```

### 部署
```bash
databricks bundle deploy                      # 部署到預設目標
databricks bundle deploy -t prod             # 部署到特定目標
databricks bundle deploy --auto-approve      # 跳過確認提示
databricks bundle deploy --force             # 強制覆寫遠端變更
```

### 執行資源
```bash
databricks bundle run resource_name          # 執行管線或作業
databricks bundle run pipeline_name -t prod  # 在特定環境中執行

# 應用程式需要 bundle run 才能在部署後啟動
databricks bundle run app_resource_key -t dev    # 啟動/部署應用程式
```

### 監控與日誌

**檢視應用程式日誌（用於應用程式資源）：**
```bash
# 檢視已部署應用程式的日誌
databricks apps logs <app-name> --profile <profile-name>

# 範例：
databricks apps logs my-dash-app-dev -p DEFAULT
databricks apps logs my-streamlit-app-prod -p DEFAULT
```

**日誌顯示內容：**
- `[SYSTEM]` - 部署進度、檔案更新、相依性安裝
- `[APP]` - 應用程式輸出（print 陳述式、錯誤）
- 後端連接狀態
- 部署 ID 和時間戳記
- 錯誤的堆疊追蹤

**要尋找的關鍵日誌模式：**
- ✅ `Deployment successful` - 確認部署完成
- ✅ `App started successfully` - 應用程式正在執行
- ✅ `Initialized real backend` - 後端已連接到 Unity Catalog
- ❌ `Error:` - 尋找錯誤訊息和堆疊追蹤
- 📝 `Requirements installed` - 相依性正確載入

### 清理
```bash
databricks bundle destroy -t dev
databricks bundle destroy -t prod --auto-approve
```

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| **應用程式部署失敗** | 檢查日誌：`databricks apps logs <app-name>` 以取得錯誤詳細資訊 |
| **應用程式未連接到 Unity Catalog** | 檢查日誌中的後端連接錯誤；驗證倉儲 ID 和權限 |
| **錯誤的權限層級** | 儀表板：CAN_READ/RUN/EDIT/MANAGE；作業：CAN_VIEW/MANAGE_RUN/MANAGE |
| **路徑解析失敗** | 在 resources/*.yml 中使用 `../src/`，在 databricks.yml 中使用 `./src/` |
| **目錄不存在** | 先建立目錄或更新變數 |
| **作業上的 "admins" 群組錯誤** | 無法修改作業上的 admins 權限 |
| **磁碟區權限** | 對磁碟區使用 `grants` 而非 `permissions` |
| **儀表板中的硬編碼目錄** | 使用 dataset_catalog 參數（CLI v0.281.0+）、建立環境特定檔案或參數化 JSON |
| **應用程式在部署後未啟動** | 應用程式需要 `databricks bundle run <resource_key>` 才能啟動 |
| **應用程式環境變數無法運作** | 環境變數放在 `app.yaml`（來源目錄），而非 databricks.yml |
| **錯誤的應用程式來源路徑** | 如果來源在專案根目錄，從 resources/ 目錄使用 `../` |
| **除錯任何應用程式問題** | 第一步：`databricks apps logs <app-name>` 查看出了什麼問題 |

## 關鍵原則

1. **路徑解析**：在 resources/*.yml 中使用 `../src/`，在 databricks.yml 中使用 `./src/`
2. **變數**：參數化 catalog、schema、warehouse
3. **模式**：dev/staging 使用 `development`，prod 使用 `production`
4. **群組**：對所有工作區使用者使用 `"users"`
5. **作業權限**：驗證自訂群組是否存在；無法修改 "admins"

## 資源

- [Databricks Asset Bundles 文件](https://docs.databricks.com/dev-tools/bundles/)
- [Bundle 資源參考](https://docs.databricks.com/dev-tools/bundles/resources)
- [Bundle 配置參考](https://docs.databricks.com/dev-tools/bundles/settings)
- [支援的資源類型](https://docs.databricks.com/aws/en/dev-tools/bundles/resources#resource-types)
- [範例儲存庫 1](https://github.com/databricks-solutions/databricks-dab-examples)
- [範例儲存庫 2](https://github.com/databricks/bundle-examples)
