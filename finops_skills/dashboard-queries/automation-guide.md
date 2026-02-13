# 透過程式碼自動化 FinOps 儀表板 (Dashboard as Code)

本指南介紹如何使用 **Databricks Asset Bundles (DABs)** 與 **Python SDK** 來自動化部署 FinOps 儀表板，實現版本控制與 CI/CD。

## 方法一：使用 Databricks Asset Bundles (DABs) - 推薦用於生產環境

DABs 是 Databricks 官方推薦的專案管理與部署工具，支援將儀表板定義為 YAML 設定檔。

### 1. 專案結構範例
```text
my-finops-project/
├── databricks.yml      # DABs 設定檔
├── resources/
│   ├── finops_dashboard.yml  # 儀表板定義
│   └── queries/              # SQL 查詢檔案
│       ├── monthly_cost.sql
│       └── ...
```

### 2. `databricks.yml` 設定
```yaml
bundle:
  name: finops_dashboard_bundle

resources:
  dashboards:
    finops_main:
      display_name: "FinOps 核心儀表板"
      warehouse_id: "${var.warehouse_id}"
      widgets:
        - text:
            content: "# FinOps Executive Summary"
        - visualization:
            query_path: ./queries/monthly_cost.sql
            visualization_type: counter
```

### 3. 部署指令
```bash
# 驗證設定
databricks bundle validate

# 部署至開發環境
databricks bundle deploy -t dev
```

---

## 方法二：使用 Python SDK - 適用於動態生成

若需根據不同部門或專案動態產生多個儀表板，可使用 `databricks-sdk`。

### 1. 安裝 SDK
```bash
pip install databricks-sdk
```

### 2. 自動化腳本範例 (`create_dashboard.py`)

此腳本將讀取 SQL 查詢並建立一個包含多個 Widget 的儀表板。

```python
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import dashboarding

# 初始化客戶端 (需設定 DATABRICKS_HOST 與 DATABRICKS_TOKEN 環境變數)
w = WorkspaceClient()

def create_finops_dashboard(name, warehouse_id):
    print(f"Creating dashboard: {name}...")
    
    # 定義 Widget (這裡僅為範例，實際可讀取 .sql 檔案內容)
    widgets = [
        dashboarding.Widget(
            text=dashboarding.TextWidget(content="# FinOps 月度報告")
        ),
        dashboarding.Widget(
            visualization=dashboarding.VisualizationWidget(
                query_definition=dashboarding.QueryDefinition(
                    name="月度成本摘要",
                    query="SELECT sum(total_cost) FROM develop_catalog.system_report.finops_daily_cost_summary WHERE year_month = current_date()",
                    warehouse_id=warehouse_id
                )
            )
        )
    ]

    # 建立儀表板
    dashboard = w.dashboards.create(
        display_name=name,
        warehouse_id=warehouse_id,
        widgets=widgets
    )
    
    print(f"Dashboard created successfully! Link: {dashboard.url}")
    return dashboard

if __name__ == "__main__":
    # 請替換為您的 SQL Warehouse ID
    WAREHOUSE_ID = "YOUR_SQL_WAREHOUSE_ID"
    create_finops_dashboard("FinOps 自動化儀表板 - PySDK", WAREHOUSE_ID)
```

## 🔄 自動化流程建議

1.  **SQL 檔案集中管理**：將所有查詢 (如 `dashboard-queries/SKILL.md` 中的查詢) 存為獨立的 `.sql` 檔案。
2.  **Git 版本控制**：將 DABs 設定檔或 Python 腳本納入 Git 管理。
3.  **CI/CD 整合**：透過 GitHub Actions 或 Azure DevOps Pipeline，在 SQL 變更時自動觸發 `databricks bundle deploy`，確保儀表板與程式碼同步。
