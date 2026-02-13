# 使用 Databricks SDK 建立 AI/BI 儀表板

本文件提供使用 **Databricks SDK** 和 **REST API** 直接建立 AI/BI Dashboard 的完整指南，作為 MCP 工具的替代方案。

## 📋 概述

在 Databricks Notebook 環境中，您可以直接使用 Databricks SDK 和 REST API 來建立儀表板，無需依賴外部 MCP 工具。

### 優勢
* ✅ 在 Databricks Assistant 中直接可用
* ✅ 完整的程式化控制
* ✅ 可整合到自動化工作流程
* ✅ 支援所有 Lakeview Dashboard 功能
* ✅ 易於版本控制和重複使用

---

## 📦 使用 dashboard_create.py 模組（推薦）

我們提供了一個完整的 Python 模組 `scripts/dashboard_create.py`，封裝了所有儀表板操作功能。

**檔案位置**：`/Users/ycliang@fareastone.com.tw/.assistant/skills/aibi-dashboards/scripts/dashboard_create.py`

### 快速使用

```python
# 方法 1：使用便利函數（最簡單）
%run ./scripts/dashboard_create.py

# 建立 FinOps 儀表板
result = create_finops_dashboard(
    dashboard_name="綜合型 FinOps 儀表板",
    months_back=6,
    auto_publish=True
)

if result["success"]:
    print(f"🎉 儀表板已建立：{result['url']}")
```

```python
# 方法 2：使用類別（更多控制）
%run ./scripts/dashboard_create.py

creator = DashboardCreator()

# 列出所有儀表板
dashboards = creator.list_dashboards()

# 建立自訂儀表板
result = creator.create_finops_dashboard(
    dashboard_name="我的 FinOps 儀表板",
    catalog="develop_catalog",
    schema="system_report",
    months_back=6,
    auto_publish=False
)

# 手動發布
if result["success"]:
    creator.publish_dashboard(result["dashboard_id"])
```

### DashboardCreator 類別方法

| 方法 | 說明 |
|------|------|
| `get_warehouses()` | 取得所有可用的 SQL Warehouses |
| `get_best_warehouse()` | 自動選擇最佳的 Warehouse |
| `test_query(query, name)` | 測試 SQL 查詢是否有效 |
| `create_dashboard(spec)` | 建立儀表板 |
| `list_dashboards()` | 列出所有儀表板 |
| `update_dashboard(id, updates)` | 更新儀表板 |
| `delete_dashboard(id)` | 刪除儀表板 |
| `publish_dashboard(id)` | 發布儀表板 |
| `unpublish_dashboard(id)` | 取消發布儀表板 |
| `create_finops_dashboard(...)` | 建立預配置的 FinOps 儀表板 |

### 便利函數

| 函數 | 說明 |
|------|------|
| `create_finops_dashboard(...)` | 快速建立 FinOps 儀表板 |
| `list_all_dashboards()` | 列出所有儀表板 |
| `delete_dashboard_by_id(id)` | 刪除指定儀表板 |
| `publish_dashboard_by_id(id)` | 發布指定儀表板 |

---

## 🚀 快速開始（手動方式）

如果您想要完全自訂儀表板，可以直接使用 SDK 和 REST API：

### 前置條件

在 Databricks Notebook 中，以下套件已預先安裝：
- `databricks-sdk` - Databricks Python SDK
- `requests` - HTTP 請求庫
- `dbutils` - Databricks 工具函數

### 步驟 1：取得 SQL Warehouse ID

```python
from databricks.sdk import WorkspaceClient

# 在 Databricks Notebook 中，WorkspaceClient 會自動使用當前認證
w = WorkspaceClient()

# 列出所有可用的 SQL Warehouses
warehouses = list(w.warehouses.list())

# 顯示所有 warehouses
print("可用的 SQL Warehouses：\n")
for wh in warehouses:
    print(f"  • {wh.name}")
    print(f"    ID: {wh.id}")
    print(f"    狀態: {wh.state.value}")
    print(f"    類型: {wh.warehouse_type.value}\n")

# 取得第一個可用的 warehouse
if warehouses:
    warehouse_id = warehouses[0].id
    warehouse_name = warehouses[0].name
    print(f"✅ 將使用 Warehouse: {warehouse_name}")
    print(f"   ID: {warehouse_id}")
else:
    raise Exception("❌ 找不到可用的 SQL Warehouse")
```

### 步驟 2：測試 SQL 查詢

**重要**：在建立儀表板前，務必先測試所有 SQL 查詢！

```python
# 測試查詢範例
test_query = """
SELECT 
  ROUND(SUM(total_cost), 2) AS total_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM')
"""

# 執行測試
try:
    df = spark.sql(test_query)
    result = df.collect()
    
    if result:
        print(f"✅ 查詢成功")
        print(f"   總成本: ${result[0]['total_cost']:,.2f}")
        display(df)
    else:
        print("⚠️ 查詢返回空結果")
except Exception as e:
    print(f"❌ 查詢失敗: {str(e)}")
    raise
```

### 步驟 3：建立儀表板

```python
import requests
import json

# 取得 Databricks 配置
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
api_url = ctx.apiUrl().get()
api_token = ctx.apiToken().get()

# 定義儀表板結構
dashboard_spec = {
    "display_name": "我的第一個 FinOps 儀表板",
    "warehouse_id": warehouse_id,
    "datasets": [
        {
            "name": "total_cost_ds",
            "displayName": "總成本資料集",
            "query": """
SELECT 
  ROUND(SUM(total_cost), 2) AS total_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM')
"""
        }
    ],
    "pages": [
        {
            "name": "overview",
            "displayName": "概覽",
            "layout": [
                # 標題
                {
                    "widget": {
                        "name": "title",
                        "multilineTextboxSpec": {
                            "lines": ["## 我的第一個 FinOps 儀表板"]
                        }
                    },
                    "position": {"x": 0, "y": 0, "width": 6, "height": 1}
                },
                # KPI: 總成本
                {
                    "widget": {
                        "name": "total_cost_kpi",
                        "queries": [{
                            "name": "main_query",
                            "query": {
                                "datasetName": "total_cost_ds",
                                "fields": [{"name": "total_cost", "expression": "`total_cost`"}],
                                "disaggregated": True
                            }
                        }],
                        "spec": {
                            "version": 2,
                            "widgetType": "counter",
                            "encodings": {
                                "value": {"fieldName": "total_cost", "displayName": "總成本 (USD)"}
                            },
                            "frame": {"showTitle": True, "title": "總成本"}
                        }
                    },
                    "position": {"x": 0, "y": 1, "width": 2, "height": 3}
                }
            ]
        }
    ]
}

# 建立儀表板
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{api_url}/api/2.0/lakeview/dashboards",
    headers=headers,
    json=dashboard_spec
)

if response.status_code == 200:
    dashboard_data = response.json()
    dashboard_id = dashboard_data["dashboard_id"]
    print(f"✅ 儀表板建立成功！")
    print(f"Dashboard ID: {dashboard_id}")
    print(f"URL: {api_url}/sql/dashboardsv3/{dashboard_id}")
else:
    print(f"❌ 建立失敗: {response.status_code}")
    print(response.text)
```

---

## 🛠️ 完整的 FinOps 儀表板建立函數

以下是一個完整的、可重複使用的函數，用於建立綜合型 FinOps 儀表板：

```python
def create_finops_dashboard(
    warehouse_id: str,
    dashboard_name: str = "綜合型 FinOps 儀表板",
    catalog: str = "develop_catalog",
    schema: str = "system_report",
    months_back: int = 6
):
    """
    建立完整的 FinOps 儀表板
    
    Args:
        warehouse_id: SQL Warehouse ID
        dashboard_name: 儀表板名稱
        catalog: 資料目錄名稱
        schema: 資料結構描述名稱
        months_back: 回溯月數（預設 6 個月）
    
    Returns:
        dict: 包含 dashboard_id、url 和 success 狀態的字典
    """
    import requests
    import json
    
    # 取得 Databricks 配置
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    api_url = ctx.apiUrl().get()
    api_token = ctx.apiToken().get()
    
    # 定義所有資料集
    datasets = [
        {
            "name": "total_cost_ds",
            "displayName": "總成本",
            "query": f"""
SELECT ROUND(SUM(total_cost), 2) AS total_cost
FROM {catalog}.{schema}.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months_back}), 'yyyy-MM')
"""
        },
        {
            "name": "monthly_trend_ds",
            "displayName": "月度趨勢",
            "query": f"""
WITH monthly_costs AS (
  SELECT 
    year_month,
    SUM(total_cost) AS monthly_cost,
    SUM(reservation_cost) AS reserved_cost,
    SUM(on_demand_cost) AS on_demand_cost
  FROM {catalog}.{schema}.finops_daily_cost_summary
  WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months_back}), 'yyyy-MM')
  GROUP BY year_month
)
SELECT 
  year_month,
  ROUND(monthly_cost, 2) AS monthly_cost,
  ROUND(reserved_cost, 2) AS reserved_cost,
  ROUND(on_demand_cost, 2) AS on_demand_cost,
  ROUND((reserved_cost / NULLIF(monthly_cost, 0)) * 100, 2) AS reserved_pct,
  ROUND(monthly_cost - LAG(monthly_cost) OVER (ORDER BY year_month), 2) AS mom_change,
  ROUND(((monthly_cost - LAG(monthly_cost) OVER (ORDER BY year_month)) / 
         NULLIF(LAG(monthly_cost) OVER (ORDER BY year_month), 0)) * 100, 2) AS mom_change_pct
FROM monthly_costs
ORDER BY year_month
"""
        },
        {
            "name": "top_services_ds",
            "displayName": "Top 服務",
            "query": f"""
SELECT 
  ConsumedService,
  ROUND(SUM(total_cost), 2) AS total_cost
FROM {catalog}.{schema}.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months_back}), 'yyyy-MM')
GROUP BY ConsumedService
ORDER BY total_cost DESC
LIMIT 10
"""
        },
        {
            "name": "resource_groups_ds",
            "displayName": "資源群組",
            "query": f"""
SELECT 
  ResourceGroup,
  ROUND(SUM(total_cost), 2) AS total_cost
FROM {catalog}.{schema}.finops_resource_group_monthly
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months_back}), 'yyyy-MM')
GROUP BY ResourceGroup
ORDER BY total_cost DESC
LIMIT 10
"""
        },
        {
            "name": "reservation_pct_ds",
            "displayName": "保留實例使用率",
            "query": f"""
SELECT 
  ROUND((SUM(reservation_cost) / NULLIF(SUM(total_cost), 0)) * 100, 2) AS reservation_pct
FROM {catalog}.{schema}.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months_back}), 'yyyy-MM')
"""
        },
        {
            "name": "cost_category_ds",
            "displayName": "成本分類",
            "query": f"""
SELECT 
  cost_category,
  ROUND(SUM(total_cost), 2) AS total_cost
FROM {catalog}.{schema}.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months_back}), 'yyyy-MM')
GROUP BY cost_category
ORDER BY total_cost DESC
"""
        }
    ]
    
    # 定義儀表板佈局
    dashboard_spec = {
        "display_name": dashboard_name,
        "warehouse_id": warehouse_id,
        "datasets": datasets,
        "pages": [
            {
                "name": "overview",
                "displayName": "成本概覽",
                "layout": [
                    # 標題
                    {
                        "widget": {
                            "name": "title",
                            "multilineTextboxSpec": {"lines": [f"## {dashboard_name}"]}
                        },
                        "position": {"x": 0, "y": 0, "width": 6, "height": 1}
                    },
                    # 副標題
                    {
                        "widget": {
                            "name": "subtitle",
                            "multilineTextboxSpec": {"lines": [f"Azure 成本管理與優化 - 最近 {months_back} 個月"]}
                        },
                        "position": {"x": 0, "y": 1, "width": 6, "height": 1}
                    },
                    # KPI 1: 總成本
                    {
                        "widget": {
                            "name": "total_cost_kpi",
                            "queries": [{
                                "name": "main_query",
                                "query": {
                                    "datasetName": "total_cost_ds",
                                    "fields": [{"name": "total_cost", "expression": "`total_cost`"}],
                                    "disaggregated": True
                                }
                            }],
                            "spec": {
                                "version": 2,
                                "widgetType": "counter",
                                "encodings": {
                                    "value": {"fieldName": "total_cost", "displayName": "總成本 (USD)"}
                                },
                                "frame": {"showTitle": True, "title": "總成本"}
                            }
                        },
                        "position": {"x": 0, "y": 2, "width": 2, "height": 3}
                    },
                    # KPI 2: 保留實例使用率
                    {
                        "widget": {
                            "name": "reservation_kpi",
                            "queries": [{
                                "name": "main_query",
                                "query": {
                                    "datasetName": "reservation_pct_ds",
                                    "fields": [{"name": "reservation_pct", "expression": "`reservation_pct`"}],
                                    "disaggregated": True
                                }
                            }],
                            "spec": {
                                "version": 2,
                                "widgetType": "counter",
                                "encodings": {
                                    "value": {"fieldName": "reservation_pct", "displayName": "保留實例使用率 (%)"}
                                },
                                "frame": {"showTitle": True, "title": "保留實例使用率"}
                            }
                        },
                        "position": {"x": 2, "y": 2, "width": 2, "height": 3}
                    },
                    # 區段標題：趨勢
                    {
                        "widget": {
                            "name": "trend_section",
                            "multilineTextboxSpec": {"lines": ["### 📈 成本趨勢"]}
                        },
                        "position": {"x": 0, "y": 5, "width": 6, "height": 1}
                    },
                    # 月度趨勢圖
                    {
                        "widget": {
                            "name": "monthly_trend_chart",
                            "queries": [{
                                "name": "main_query",
                                "query": {
                                    "datasetName": "monthly_trend_ds",
                                    "fields": [
                                        {"name": "year_month", "expression": "`year_month`"},
                                        {"name": "monthly_cost", "expression": "`monthly_cost`"},
                                        {"name": "reserved_cost", "expression": "`reserved_cost`"}
                                    ],
                                    "disaggregated": True
                                }
                            }],
                            "spec": {
                                "version": 3,
                                "widgetType": "line",
                                "encodings": {
                                    "x": {
                                        "fieldName": "year_month",
                                        "displayName": "月份",
                                        "scale": {"type": "categorical"}
                                    },
                                    "y": {
                                        "scale": {"type": "quantitative"},
                                        "fields": [
                                            {"fieldName": "monthly_cost", "displayName": "總成本"},
                                            {"fieldName": "reserved_cost", "displayName": "保留實例成本"}
                                        ]
                                    }
                                },
                                "frame": {"showTitle": True, "title": "月度成本趨勢"}
                            }
                        },
                        "position": {"x": 0, "y": 6, "width": 6, "height": 5}
                    },
                    # 區段標題：分解
                    {
                        "widget": {
                            "name": "breakdown_section",
                            "multilineTextboxSpec": {"lines": ["### 💰 成本分解"]}
                        },
                        "position": {"x": 0, "y": 11, "width": 6, "height": 1}
                    },
                    # Top 服務圖表
                    {
                        "widget": {
                            "name": "top_services_chart",
                            "queries": [{
                                "name": "main_query",
                                "query": {
                                    "datasetName": "top_services_ds",
                                    "fields": [
                                        {"name": "ConsumedService", "expression": "`ConsumedService`"},
                                        {"name": "total_cost", "expression": "`total_cost`"}
                                    ],
                                    "disaggregated": True
                                }
                            }],
                            "spec": {
                                "version": 3,
                                "widgetType": "bar",
                                "encodings": {
                                    "x": {
                                        "fieldName": "total_cost",
                                        "displayName": "成本",
                                        "scale": {"type": "quantitative"}
                                    },
                                    "y": {
                                        "fieldName": "ConsumedService",
                                        "displayName": "服務",
                                        "scale": {"type": "categorical"}
                                    }
                                },
                                "frame": {"showTitle": True, "title": "Top 10 服務成本"}
                            }
                        },
                        "position": {"x": 0, "y": 12, "width": 3, "height": 5}
                    },
                    # 資源群組圖表
                    {
                        "widget": {
                            "name": "resource_groups_chart",
                            "queries": [{
                                "name": "main_query",
                                "query": {
                                    "datasetName": "resource_groups_ds",
                                    "fields": [
                                        {"name": "ResourceGroup", "expression": "`ResourceGroup`"},
                                        {"name": "total_cost", "expression": "`total_cost`"}
                                    ],
                                    "disaggregated": True
                                }
                            }],
                            "spec": {
                                "version": 3,
                                "widgetType": "bar",
                                "encodings": {
                                    "x": {
                                        "fieldName": "total_cost",
                                        "displayName": "成本",
                                        "scale": {"type": "quantitative"}
                                    },
                                    "y": {
                                        "fieldName": "ResourceGroup",
                                        "displayName": "資源群組",
                                        "scale": {"type": "categorical"}
                                    }
                                },
                                "frame": {"showTitle": True, "title": "Top 10 資源群組成本"}
                            }
                        },
                        "position": {"x": 3, "y": 12, "width": 3, "height": 5}
                    },
                    # 成本分類圓餅圖
                    {
                        "widget": {
                            "name": "cost_category_chart",
                            "queries": [{
                                "name": "main_query",
                                "query": {
                                    "datasetName": "cost_category_ds",
                                    "fields": [
                                        {"name": "cost_category", "expression": "`cost_category`"},
                                        {"name": "total_cost", "expression": "`total_cost`"}
                                    ],
                                    "disaggregated": True
                                }
                            }],
                            "spec": {
                                "version": 3,
                                "widgetType": "pie",
                                "encodings": {
                                    "label": {
                                        "fieldName": "cost_category",
                                        "displayName": "分類"
                                    },
                                    "value": {
                                        "fieldName": "total_cost",
                                        "displayName": "成本"
                                    }
                                },
                                "frame": {"showTitle": True, "title": "成本分類分布"}
                            }
                        },
                        "position": {"x": 0, "y": 17, "width": 3, "height": 5}
                    }
                ]
            }
        ]
    }
    
    # 建立儀表板
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{api_url}/api/2.0/lakeview/dashboards",
            headers=headers,
            json=dashboard_spec
        )
        
        if response.status_code == 200:
            dashboard_data = response.json()
            dashboard_id = dashboard_data["dashboard_id"]
            dashboard_url = f"{api_url}/sql/dashboardsv3/{dashboard_id}"
            
            print(f"✅ 儀表板建立成功！")
            print(f"Dashboard ID: {dashboard_id}")
            print(f"URL: {dashboard_url}")
            
            return {
                "dashboard_id": dashboard_id,
                "url": dashboard_url,
                "success": True
            }
        else:
            print(f"❌ 建立失敗: {response.status_code}")
            print(response.text)
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    except Exception as e:
        print(f"❌ 發生錯誤: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
```

---

## 🔧 其他 SDK 操作

### 列出所有儀表板

```python
def list_dashboards():
    """列出所有可用的儀表板"""
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    api_url = ctx.apiUrl().get()
    api_token = ctx.apiToken().get()
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{api_url}/api/2.0/lakeview/dashboards",
        headers=headers
    )
    
    if response.status_code == 200:
        dashboards = response.json().get("dashboards", [])
        print(f"找到 {len(dashboards)} 個儀表板：\n")
        for db in dashboards:
            print(f"  • {db['display_name']}")
            print(f"    ID: {db['dashboard_id']}")
            print(f"    URL: {api_url}/sql/dashboardsv3/{db['dashboard_id']}\n")
        return dashboards
    else:
        print(f"❌ 列出失敗: {response.status_code}")
        return []
```

### 更新儀表板

```python
def update_dashboard(dashboard_id: str, updates: dict):
    """更新現有的儀表板"""
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    api_url = ctx.apiUrl().get()
    api_token = ctx.apiToken().get()
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.patch(
        f"{api_url}/api/2.0/lakeview/dashboards/{dashboard_id}",
        headers=headers,
        json=updates
    )
    
    if response.status_code == 200:
        print(f"✅ 儀表板更新成功！")
        return {"success": True, "data": response.json()}
    else:
        print(f"❌ 更新失敗: {response.status_code}")
        print(response.text)
        return {"success": False, "error": response.text}
```

### 刪除儀表板

```python
def delete_dashboard(dashboard_id: str):
    """刪除指定的儀表板"""
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    api_url = ctx.apiUrl().get()
    api_token = ctx.apiToken().get()
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.delete(
        f"{api_url}/api/2.0/lakeview/dashboards/{dashboard_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ 儀表板已刪除")
        return {"success": True}
    else:
        print(f"❌ 刪除失敗: {response.status_code}")
        return {"success": False, "error": response.text}
```

### 發布儀表板

```python
def publish_dashboard(dashboard_id: str, embed_credentials: bool = False):
    """發布儀表板供其他使用者檢視"""
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    api_url = ctx.apiUrl().get()
    api_token = ctx.apiToken().get()
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{api_url}/api/2.0/lakeview/dashboards/{dashboard_id}/published",
        headers=headers,
        json={"embed_credentials": embed_credentials}
    )
    
    if response.status_code == 200:
        published_data = response.json()
        print(f"✅ 儀表板已發布")
        print(f"Published URL: {api_url}/sql/dashboardsv3/{dashboard_id}")
        return {"success": True, "data": published_data}
    else:
        print(f"❌ 發布失敗: {response.status_code}")
        return {"success": False, "error": response.text}
```

### 取消發布儀表板

```python
def unpublish_dashboard(dashboard_id: str):
    """取消發布儀表板"""
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    api_url = ctx.apiUrl().get()
    api_token = ctx.apiToken().get()
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.delete(
        f"{api_url}/api/2.0/lakeview/dashboards/{dashboard_id}/published",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ 儀表板已取消發布")
        return {"success": True}
    else:
        print(f"❌ 取消發布失敗: {response.status_code}")
        return {"success": False, "error": response.text}
```

---

## 📊 完整使用範例

```python
# ==========================================
# 完整的 FinOps 儀表板建立工作流程
# ==========================================

from databricks.sdk import WorkspaceClient
import requests

# 步驟 1：取得 Warehouse ID
print("🔍 步驟 1：取得 SQL Warehouse...")
w = WorkspaceClient()
warehouses = list(w.warehouses.list())

if not warehouses:
    raise Exception("❌ 找不到可用的 SQL Warehouse")

warehouse_id = warehouses[0].id
warehouse_name = warehouses[0].name
print(f"✅ 使用 Warehouse: {warehouse_name} ({warehouse_id})\n")

# 步驟 2：測試關鍵查詢
print("📊 步驟 2：測試查詢...")

test_queries = [
    ("總成本", """
SELECT ROUND(SUM(total_cost), 2) AS total_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM')
"""),
    ("月度趨勢", """
SELECT 
  year_month,
  ROUND(SUM(total_cost), 2) AS monthly_cost
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -6), 'yyyy-MM')
GROUP BY year_month
ORDER BY year_month
LIMIT 5
""")
]

for name, query in test_queries:
    try:
        df = spark.sql(query)
        count = df.count()
        print(f"  ✅ {name}: {count} 筆記錄")
    except Exception as e:
        print(f"  ❌ {name}: {str(e)}")
        raise

print()

# 步驟 3：建立儀表板
print("🚀 步驟 3：建立儀表板...")
result = create_finops_dashboard(
    warehouse_id=warehouse_id,
    dashboard_name="綜合型 FinOps 儀表板",
    catalog="develop_catalog",
    schema="system_report",
    months_back=6
)

if result["success"]:
    dashboard_id = result["dashboard_id"]
    print()
    
    # 步驟 4：發布儀表板
    print("📢 步驟 4：發布儀表板...")
    publish_result = publish_dashboard(dashboard_id)
    
    if publish_result["success"]:
        print(f"\n🎉 完成！請訪問：")
        print(result["url"])
    else:
        print("\n⚠️ 儀表板已建立但發布失敗")
        print(f"您仍可以訪問：{result['url']}")
else:
    print("\n❌ 儀表板建立失敗")
    print(f"錯誤: {result.get('error', 'Unknown error')}")
```

---

## 🔍 疑難排解

### 常見錯誤與解決方案

#### 1. 認證錯誤
```
Error: 401 Unauthorized
```
**原因**：無法取得有效的認證 token

**解決方案**：
- 確保在 Databricks Notebook 中執行
- 檢查 `dbutils` 是否可用
- 驗證您有適當的權限

#### 2. Warehouse 不可用
```
Error: Warehouse not found or not accessible
```
**原因**：指定的 warehouse 不存在或無權限存取

**解決方案**：
```python
# 檢查所有可用的 warehouses
for wh in w.warehouses.list():
    print(f"{wh.name}: {wh.state.value} - {wh.id}")
```

#### 3. 查詢錯誤
```
Error: Table or view not found
```
**原因**：表不存在或無權限存取

**解決方案**：
```python
# 驗證表存取
spark.sql("SHOW TABLES IN develop_catalog.system_report").show()

# 測試簡單查詢
spark.sql("SELECT * FROM develop_catalog.system_report.finops_daily_cost_summary LIMIT 1").show()
```

#### 4. JSON 格式錯誤
```
Error: Invalid dashboard specification
```
**原因**：儀表板規格不符合 API 要求

**解決方案**：
- 檢查所有 widget 名稱只包含字母數字、連字號和底線
- 確認 version 號碼正確（counter/table/filter=2, charts=3）
- 驗證 fieldName 與 dataset 欄位完全匹配
- 確保所有必要欄位都已提供

#### 5. 欄位名稱不匹配
```
Error: No fields selected to visualize
```
**原因**：widget 的 `fieldName` 與 dataset 欄位不匹配

**解決方案**：
```python
# 確保 query.fields 中的 name 與 encodings 中的 fieldName 完全一致
# 正確範例：
{
    "query": {
        "fields": [{"name": "total_cost", "expression": "`total_cost`"}]
    },
    "spec": {
        "encodings": {
            "value": {"fieldName": "total_cost", "displayName": "總成本"}
        }
    }
}
```

---

## 📚 API 參考

### Lakeview Dashboard API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/2.0/lakeview/dashboards` | 建立新儀表板 |
| GET | `/api/2.0/lakeview/dashboards` | 列出所有儀表板 |
| GET | `/api/2.0/lakeview/dashboards/{id}` | 取得儀表板詳情 |
| PATCH | `/api/2.0/lakeview/dashboards/{id}` | 更新儀表板 |
| DELETE | `/api/2.0/lakeview/dashboards/{id}` | 刪除儀表板 |
| POST | `/api/2.0/lakeview/dashboards/{id}/published` | 發布儀表板 |
| DELETE | `/api/2.0/lakeview/dashboards/{id}/published` | 取消發布 |

### Databricks SDK 參考

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Warehouse 操作
w.warehouses.list()
w.warehouses.get(id="warehouse_id")
w.warehouses.start(id="warehouse_id")
w.warehouses.stop(id="warehouse_id")

# Query 操作（如果需要建立 SQL 查詢物件）
w.queries.create(name="My Query", query="SELECT ...", warehouse_id="...")
w.queries.list()
w.queries.get(id="query_id")
```

---

## ✅ 最佳實踐

1. **測試優先**：在建立儀表板前，先在 notebook 中測試所有 SQL 查詢
2. **參數化**：使用函數參數來支援不同的 catalog/schema
3. **錯誤處理**：包含完整的錯誤處理和狀態檢查
4. **版本控制**：將儀表板規格儲存為 JSON 檔案進行版本控制
5. **文件化**：為每個 dataset 和 widget 加入清楚的 displayName
6. **效能優化**：使用預先聚合的資料集來提升儀表板載入速度
7. **權限管理**：發布前確認適當的存取權限設定

---

## 🎯 下一步

* 探索 [SKILL.md](SKILL.md) 了解完整的儀表板設計指南
* 查看 widget 規格和佈局最佳實踐
* 學習如何加入篩選器和互動功能
* 了解如何優化查詢效能

---

**最後更新**：2024-01-15  
**維護者**：FinOps 團隊  
**相關文件**：[SKILL.md](SKILL.md) | [README.md](README.md)
