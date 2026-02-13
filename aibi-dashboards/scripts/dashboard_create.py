"""
Databricks AI/BI Dashboard Creation Script

This module provides a comprehensive toolkit for creating, managing, and deploying
AI/BI Dashboards using Databricks SDK and REST API.

Usage:
    from dashboard_create import DashboardCreator
    
    creator = DashboardCreator()
    result = creator.create_finops_dashboard(
        dashboard_name="My FinOps Dashboard",
        months_back=6
    )

Author: FinOps Team
Last Updated: 2024-01-15
"""

import requests
import json
from typing import Dict, List, Optional, Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Warehouse


class DashboardCreator:
    """
    A class for creating and managing Databricks AI/BI Dashboards.
    
    This class provides methods to:
    - Get available SQL Warehouses
    - Test SQL queries before deployment
    - Create dashboards with various configurations
    - Manage dashboard lifecycle (publish, update, delete)
    """
    
    def __init__(self):
        """Initialize the DashboardCreator with Databricks configuration."""
        try:
            # Get Databricks configuration from notebook context
            ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
            self.api_url = ctx.apiUrl().get()
            self.api_token = ctx.apiToken().get()
            self.workspace_client = WorkspaceClient()
            
            # Set up headers for API calls
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            print("✅ DashboardCreator initialized successfully")
        except Exception as e:
            raise Exception(f"Failed to initialize DashboardCreator: {str(e)}")
    
    def get_warehouses(self, show_details: bool = True) -> List[Warehouse]:
        """
        Get all available SQL Warehouses.
        
        Args:
            show_details: Whether to print warehouse details
            
        Returns:
            List of Warehouse objects
        """
        try:
            warehouses = list(self.workspace_client.warehouses.list())
            
            if show_details and warehouses:
                print(f"找到 {len(warehouses)} 個 SQL Warehouses：\n")
                for wh in warehouses:
                    print(f"  • {wh.name}")
                    print(f"    ID: {wh.id}")
                    print(f"    狀態: {wh.state.value}")
                    print(f"    類型: {wh.warehouse_type.value}\n")
            
            return warehouses
        except Exception as e:
            print(f"❌ 取得 Warehouses 失敗: {str(e)}")
            return []
    
    def get_best_warehouse(self) -> Optional[str]:
        """
        Get the best available warehouse ID (first running or available warehouse).
        
        Returns:
            Warehouse ID string or None if no warehouse available
        """
        warehouses = self.get_warehouses(show_details=False)
        
        if not warehouses:
            print("❌ 找不到可用的 SQL Warehouse")
            return None
        
        # Try to find a running warehouse first
        for wh in warehouses:
            if wh.state.value == "RUNNING":
                print(f"✅ 使用運行中的 Warehouse: {wh.name} ({wh.id})")
                return wh.id
        
        # Otherwise, use the first available warehouse
        warehouse_id = warehouses[0].id
        print(f"✅ 使用 Warehouse: {warehouses[0].name} ({warehouse_id})")
        return warehouse_id
    
    def test_query(self, query: str, query_name: str = "Test Query") -> bool:
        """
        Test a SQL query to ensure it executes successfully.
        
        Args:
            query: SQL query string to test
            query_name: Name of the query for logging
            
        Returns:
            True if query succeeds, False otherwise
        """
        try:
            df = spark.sql(query)
            count = df.count()
            print(f"  ✅ {query_name}: {count} 筆記錄")
            return True
        except Exception as e:
            print(f"  ❌ {query_name} 失敗: {str(e)}")
            return False
    
    def create_dashboard(self, dashboard_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new AI/BI Dashboard.
        
        Args:
            dashboard_spec: Dashboard specification dictionary
            
        Returns:
            Dictionary with dashboard_id, url, and success status
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/2.0/lakeview/dashboards",
                headers=self.headers,
                json=dashboard_spec
            )
            
            if response.status_code == 200:
                dashboard_data = response.json()
                dashboard_id = dashboard_data["dashboard_id"]
                dashboard_url = f"{self.api_url}/sql/dashboardsv3/{dashboard_id}"
                
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
    
    def list_dashboards(self) -> List[Dict[str, Any]]:
        """
        List all available dashboards.
        
        Returns:
            List of dashboard dictionaries
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/2.0/lakeview/dashboards",
                headers=self.headers
            )
            
            if response.status_code == 200:
                dashboards = response.json().get("dashboards", [])
                print(f"找到 {len(dashboards)} 個儀表板：\n")
                for db in dashboards:
                    print(f"  • {db['display_name']}")
                    print(f"    ID: {db['dashboard_id']}")
                    print(f"    URL: {self.api_url}/sql/dashboardsv3/{db['dashboard_id']}\n")
                return dashboards
            else:
                print(f"❌ 列出失敗: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
            return []
    
    def update_dashboard(self, dashboard_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing dashboard.
        
        Args:
            dashboard_id: Dashboard ID to update
            updates: Dictionary with updates to apply
            
        Returns:
            Dictionary with success status and data
        """
        try:
            response = requests.patch(
                f"{self.api_url}/api/2.0/lakeview/dashboards/{dashboard_id}",
                headers=self.headers,
                json=updates
            )
            
            if response.status_code == 200:
                print(f"✅ 儀表板更新成功！")
                return {"success": True, "data": response.json()}
            else:
                print(f"❌ 更新失敗: {response.status_code}")
                print(response.text)
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def delete_dashboard(self, dashboard_id: str) -> Dict[str, bool]:
        """
        Delete a dashboard.
        
        Args:
            dashboard_id: Dashboard ID to delete
            
        Returns:
            Dictionary with success status
        """
        try:
            response = requests.delete(
                f"{self.api_url}/api/2.0/lakeview/dashboards/{dashboard_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                print(f"✅ 儀表板已刪除")
                return {"success": True}
            else:
                print(f"❌ 刪除失敗: {response.status_code}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def publish_dashboard(self, dashboard_id: str, embed_credentials: bool = False) -> Dict[str, Any]:
        """
        Publish a dashboard for viewing by others.
        
        Args:
            dashboard_id: Dashboard ID to publish
            embed_credentials: Whether to embed credentials
            
        Returns:
            Dictionary with success status and published data
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/2.0/lakeview/dashboards/{dashboard_id}/published",
                headers=self.headers,
                json={"embed_credentials": embed_credentials}
            )
            
            if response.status_code == 200:
                published_data = response.json()
                print(f"✅ 儀表板已發布")
                print(f"Published URL: {self.api_url}/sql/dashboardsv3/{dashboard_id}")
                return {"success": True, "data": published_data}
            else:
                print(f"❌ 發布失敗: {response.status_code}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def unpublish_dashboard(self, dashboard_id: str) -> Dict[str, bool]:
        """
        Unpublish a dashboard.
        
        Args:
            dashboard_id: Dashboard ID to unpublish
            
        Returns:
            Dictionary with success status
        """
        try:
            response = requests.delete(
                f"{self.api_url}/api/2.0/lakeview/dashboards/{dashboard_id}/published",
                headers=self.headers
            )
            
            if response.status_code == 200:
                print(f"✅ 儀表板已取消發布")
                return {"success": True}
            else:
                print(f"❌ 取消發布失敗: {response.status_code}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"❌ 發生錯誤: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_finops_dashboard(
        self,
        dashboard_name: str = "綜合型 FinOps 儀表板",
        catalog: str = "develop_catalog",
        schema: str = "system_report",
        months_back: int = 6,
        warehouse_id: Optional[str] = None,
        auto_publish: bool = False
    ) -> Dict[str, Any]:
        """
        Create a comprehensive FinOps dashboard with pre-configured widgets.
        
        Args:
            dashboard_name: Name of the dashboard
            catalog: Data catalog name
            schema: Data schema name
            months_back: Number of months to look back (default: 6)
            warehouse_id: SQL Warehouse ID (auto-detected if not provided)
            auto_publish: Whether to automatically publish the dashboard
            
        Returns:
            Dictionary with dashboard_id, url, and success status
        """
        # Get warehouse ID if not provided
        if not warehouse_id:
            warehouse_id = self.get_best_warehouse()
            if not warehouse_id:
                return {"success": False, "error": "No warehouse available"}
        
        print(f"\n🚀 建立 FinOps 儀表板...")
        print(f"   名稱: {dashboard_name}")
        print(f"   資料來源: {catalog}.{schema}")
        print(f"   時間範圍: 最近 {months_back} 個月\n")
        
        # Define all datasets
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
        
        # Test all queries before creating dashboard
        print("📊 測試所有查詢...")
        all_passed = True
        for ds in datasets:
            if not self.test_query(ds["query"], ds["displayName"]):
                all_passed = False
        
        if not all_passed:
            return {
                "success": False,
                "error": "Some queries failed validation. Please fix them before creating dashboard."
            }
        
        print("\n✅ 所有查詢驗證通過\n")
        
        # Define dashboard layout
        dashboard_spec = {
            "display_name": dashboard_name,
            "warehouse_id": warehouse_id,
            "datasets": datasets,
            "pages": [
                {
                    "name": "overview",
                    "displayName": "成本概覽",
                    "layout": [
                        # Title
                        {
                            "widget": {
                                "name": "title",
                                "multilineTextboxSpec": {"lines": [f"## {dashboard_name}"]}
                            },
                            "position": {"x": 0, "y": 0, "width": 6, "height": 1}
                        },
                        # Subtitle
                        {
                            "widget": {
                                "name": "subtitle",
                                "multilineTextboxSpec": {"lines": [f"Azure 成本管理與優化 - 最近 {months_back} 個月"]}
                            },
                            "position": {"x": 0, "y": 1, "width": 6, "height": 1}
                        },
                        # KPI 1: Total Cost
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
                        # KPI 2: Reservation Usage
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
                        # Section: Trends
                        {
                            "widget": {
                                "name": "trend_section",
                                "multilineTextboxSpec": {"lines": ["### 📈 成本趨勢"]}
                            },
                            "position": {"x": 0, "y": 5, "width": 6, "height": 1}
                        },
                        # Monthly Trend Chart
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
                        # Section: Breakdown
                        {
                            "widget": {
                                "name": "breakdown_section",
                                "multilineTextboxSpec": {"lines": ["### 💰 成本分解"]}
                            },
                            "position": {"x": 0, "y": 11, "width": 6, "height": 1}
                        },
                        # Top Services Chart
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
                        # Resource Groups Chart
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
                        # Cost Category Pie Chart
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
        
        # Create the dashboard
        result = self.create_dashboard(dashboard_spec)
        
        # Auto-publish if requested
        if result["success"] and auto_publish:
            print("\n📢 發布儀表板...")
            publish_result = self.publish_dashboard(result["dashboard_id"])
            result["published"] = publish_result["success"]
        
        return result


# ==========================================
# Convenience Functions (for direct use)
# ==========================================

def create_finops_dashboard(
    dashboard_name: str = "綜合型 FinOps 儀表板",
    catalog: str = "develop_catalog",
    schema: str = "system_report",
    months_back: int = 6,
    auto_publish: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to create a FinOps dashboard without instantiating the class.
    
    Args:
        dashboard_name: Name of the dashboard
        catalog: Data catalog name
        schema: Data schema name
        months_back: Number of months to look back
        auto_publish: Whether to automatically publish the dashboard
        
    Returns:
        Dictionary with dashboard_id, url, and success status
        
    Example:
        result = create_finops_dashboard(
            dashboard_name="Executive Dashboard",
            months_back=6,
            auto_publish=True
        )
        print(result["url"])
    """
    creator = DashboardCreator()
    return creator.create_finops_dashboard(
        dashboard_name=dashboard_name,
        catalog=catalog,
        schema=schema,
        months_back=months_back,
        auto_publish=auto_publish
    )


def list_all_dashboards() -> List[Dict[str, Any]]:
    """
    Convenience function to list all dashboards.
    
    Returns:
        List of dashboard dictionaries
        
    Example:
        dashboards = list_all_dashboards()
        for db in dashboards:
            print(db["display_name"])
    """
    creator = DashboardCreator()
    return creator.list_dashboards()


def delete_dashboard_by_id(dashboard_id: str) -> Dict[str, bool]:
    """
    Convenience function to delete a dashboard.
    
    Args:
        dashboard_id: Dashboard ID to delete
        
    Returns:
        Dictionary with success status
        
    Example:
        result = delete_dashboard_by_id("abc-123-def")
        if result["success"]:
            print("Dashboard deleted")
    """
    creator = DashboardCreator()
    return creator.delete_dashboard(dashboard_id)


def publish_dashboard_by_id(dashboard_id: str) -> Dict[str, Any]:
    """
    Convenience function to publish a dashboard.
    
    Args:
        dashboard_id: Dashboard ID to publish
        
    Returns:
        Dictionary with success status
        
    Example:
        result = publish_dashboard_by_id("abc-123-def")
        if result["success"]:
            print("Dashboard published")
    """
    creator = DashboardCreator()
    return creator.publish_dashboard(dashboard_id)


# ==========================================
# Main Execution (for testing)
# ==========================================

if __name__ == "__main__":
    """
    Main execution block for testing the script.
    Run this in a Databricks Notebook to test functionality.
    """
    print("=" * 60)
    print("Databricks AI/BI Dashboard Creator")
    print("=" * 60)
    print()
    
    try:
        # Create dashboard creator instance
        creator = DashboardCreator()
        
        # Get available warehouses
        print("🔍 檢查可用的 SQL Warehouses...")
        warehouses = creator.get_warehouses()
        
        if not warehouses:
            print("❌ 沒有可用的 SQL Warehouse，無法繼續")
        else:
            # Create FinOps dashboard
            result = creator.create_finops_dashboard(
                dashboard_name="綜合型 FinOps 儀表板",
                catalog="develop_catalog",
                schema="system_report",
                months_back=6,
                auto_publish=True
            )
            
            if result["success"]:
                print("\n" + "=" * 60)
                print("🎉 儀表板建立完成！")
                print("=" * 60)
                print(f"\n請訪問以下 URL 查看您的儀表板：")
                print(result["url"])
            else:
                print("\n❌ 儀表板建立失敗")
                print(f"錯誤: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"\n❌ 執行失敗: {str(e)}")
        raise
