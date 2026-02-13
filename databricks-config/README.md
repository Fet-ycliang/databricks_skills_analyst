# Databricks Config

為 Databricks Connect、Databricks CLI 和 Databricks SDK 配置 Databricks 設定檔和驗證。

## 概述

此技能引導您在 `~/.databrickscfg` 中配置 Databricks 設定檔，並透過 `databricks auth login` 進行驗證。當使用者需要設定或更新其本地 Databricks 連接設定檔、在基於叢集或無伺服器運算之間選擇，以及驗證其配置時，此技能會啟動。該技能確保適當的安全實踐，包括在輸出中隱藏權杖。

## 包含內容

```
databricks-config/
└── SKILL.md    # 設定檔配置工作流程、運算選項和範例配置
```

## 關鍵主題

- `~/.databrickscfg` 中的設定檔配置
- 透過 `databricks auth login` 進行 OAuth 驗證
- 工作區主機 URL 解析和設定檔名稱擷取
- 運算選項選擇（叢集 ID vs 無伺服器）
- 無伺服器運算配置（`serverless_compute_id = auto`）
- 權杖安全性和隱藏實踐

## 何時使用

- 首次設定新的 Databricks 設定檔
- 在工作區環境或運算目標之間切換
- 為 Databricks Connect、CLI 或 SDK 配置驗證
- 疑難排解連接或驗證問題
- 使用者使用選用的設定檔名稱或工作區 URL 呼叫 `/databricks-config`

## 相關技能

- [Databricks Python SDK](../databricks-python-sdk/) -- 使用此技能配置的設定檔
- [Asset Bundles](../asset-bundles/) -- 為部署目標引用工作區設定檔
- [Databricks Apps (APX)](../databricks-app-apx/) -- 透過配置的設定檔連接的應用程式
- [Databricks Apps (Python)](../databricks-app-python/) -- 使用配置的設定檔的 Python 應用程式

## 資源

- [Databricks CLI 驗證](https://docs.databricks.com/dev-tools/cli/authentication.html)
- [Databricks 配置設定檔](https://docs.databricks.com/dev-tools/auth/index.html#configuration-profiles)
- [Databricks Connect 設定](https://docs.databricks.com/dev-tools/databricks-connect.html)
