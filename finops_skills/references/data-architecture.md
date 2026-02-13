# FinOps 資料架構細節

本文件詳細說明 FinOps 技能使用的資料表架構與層級設計。

## 📊 資料層級

### Bronze 層（原始資料）
* **資料表**：`develop_catalog.system_report.infra_azure_cost_usage_actual`
* **用途**：原始 Azure 成本匯出資料（符合 FinOps v1.2 規範）
* **保留期限**：13-24 個月的歷史資料
* **更新頻率**：每日從 Azure Cost Export 更新

### Silver 層（清理與豐富化）
* **資料表**：`develop_catalog.system_report.infra_azure_cost_silver`
* **用途**：標準化、豐富化的成本資料，包含：
  * 資料品質驗證
  * 成本分類（運算、儲存、網路、資料庫、其他）
  * 區域分組（亞洲、美國、歐洲、其他）
  * 標籤提取（用途、環境、成本中心、擁有者）
  * 保留實例識別
* **分區**：依 `year_month` 分區
* **叢集**：依 `ConsumedService`、`ResourceGroup` 叢集
* **使用案例**：詳細的資源層級分析、自訂聚合

### Gold 層（業務就緒的聚合）

#### 1. 每日成本摘要
* **資料表**：`develop_catalog.system_report.finops_daily_cost_summary`
* **用途**：依服務、類別和區域的每日聚合成本
* **關鍵指標**： 
  * 總成本、數量、資源數量
  * 多維度成本拆分：保留實例、Spot 實例、節省方案、隨選成本
  * 平均有效價格與 Pay-as-you-go 價格比較
* **效能**：針對快速儀表板查詢優化（次秒級）
* **完整欄位清單**：
  * `date_key`, `year_month` (分區欄位)
  * `ConsumedService`, `cost_category`, `region_group`
  * `resource_count`, `total_quantity`
  * `avg_payGPrice`, `avg_effective_price`
  * `total_cost`, `reservation_cost`, `spot_cost`, `savingplan_cost`, `on_demand_cost`

#### 2. 資源群組月度
* **資料表**：`develop_catalog.system_report.finops_resource_group_monthly`
* **用途**：依資源群組的月度成本分配
* **使用案例**：成本回收、預算追蹤、團隊責任歸屬
* **關鍵維度**：資源群組、標籤、環境、成本中心

#### 3. 服務月度趨勢
* **資料表**：`develop_catalog.system_report.finops_service_monthly_trend`
* **用途**：服務層級成本趨勢，包含月對月和年對年比較
* **關鍵指標**：成本成長、資源擴展、趨勢分析
* **包含**：歷史比較（上個月、去年同期）

## 📝 關鍵資料表參考

| 層級 | 資料表名稱 | 用途 | 更新頻率 | 分區欄位 |
|-------|-----------|---------|------------------|---------|
| Bronze | `infra_azure_cost_usage_actual` | 原始 Azure 成本匯出 | 每日 | `Date` |
| Silver | `infra_azure_cost_silver` | 清理與豐富化的成本資料 | 每日 | `year_month` |
| Gold | `finops_daily_cost_summary` | 每日聚合成本 | 每日 | `year_month` |
| Gold | `finops_resource_group_monthly` | 月度資源群組成本 | 每月 | `year_month` |
| Gold | `finops_service_monthly_trend` | 月度服務趨勢 | 每月 | `year_month` |

**目錄**：`develop_catalog`  
**結構描述**：`system_report`
