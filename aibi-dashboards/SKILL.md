---
name: aibi-dashboards
description: "建立 AI/BI 儀表板。重要：部署前必須透過 execute_sql 測試所有 SQL 查詢。嚴格遵循指南。"
---

# AI/BI 儀表板技能

建立 Databricks AI/BI 儀表板（前身為 Lakeview 儀表板）。**請嚴格遵循這些指南。**

## 重要：強制驗證工作流程

**您必須完全按照此工作流程執行。跳過驗證會導致儀表板損壞。**

```
┌─────────────────────────────────────────────────────────────────────┐
│  步驟 1：透過 get_table_details(catalog, schema) 取得資料表結構       │
├─────────────────────────────────────────────────────────────────────┤
│  步驟 2：為每個資料集撰寫 SQL 查詢                                    │
├─────────────────────────────────────────────────────────────────────┤
│  步驟 3：透過 execute_sql() 測試每個查詢 ← 不可跳過！                  │
│          - 如果查詢失敗，在繼續之前修正它                             │
│          - 驗證欄位名稱與小工具將引用的名稱相符                        │ 
│          - 驗證資料類型正確（日期、數字、字串）                        │
├─────────────────────────────────────────────────────────────────────┤
│  步驟 4：僅使用已驗證的查詢建立儀表板 JSON                             │
├─────────────────────────────────────────────────────────────────────┤
│  步驟 5：透過 create_or_update_dashboard() 部署                      │
└─────────────────────────────────────────────────────────────────────┘
```

**警告：如果您在未測試查詢的情況下部署，小工具將顯示「無效的小工具定義」錯誤！**

## 🔧 建立儀表板的兩種方式

### 方式 1：使用 Python SDK 模組（推薦 ✅）

我們提供了 `scripts/dashboard_create.py` 模組，封裝了所有儀表板操作功能。

**快速使用**：
```python
# 載入模組
%run /Users/ycliang@fareastone.com.tw/.assistant/skills/aibi-dashboards/scripts/dashboard_create.py

# 建立 FinOps 儀表板
result = create_finops_dashboard(
    dashboard_name="綜合型 FinOps 儀表板",
    months_back=6,
    auto_publish=True
)

if result["success"]:
    print(f"🎉 儀表板已建立：{result['url']}")
```

**優勢**：
* ✅ 自動取得 SQL Warehouse
* ✅ 內建查詢驗證機制
* ✅ 完整的錯誤處理
* ✅ 支援自動發布
* ✅ 可重複使用的函數

**詳細文件**：參見 [databricks-sdk-methods.md](databricks-sdk-methods.md)

---

## 🤖 Assistant 自動執行指引

**當使用者透過自然語言請求建立儀表板時**（例如：「建立一個 FinOps 儀表板」、「幫我建立 dashboard」），Assistant 應該：

### 執行步驟

1. **確認需求**
   - 儀表板名稱（預設：綜合型 FinOps 儀表板）
   - 時間範圍（預設：6 個月）
   - 資料來源（預設：develop_catalog.system_report）

2. **建立載入模組的 Cell**
   ```python
   # 使用 updateCells 建立新 cell
   %run /Users/ycliang@fareastone.com.tw/.assistant/skills/aibi-dashboards/scripts/dashboard_create.py
   ```
   - 執行此 cell 以載入 DashboardCreator 類別和便利函數

3. **建立執行 Cell**
   ```python
   # 使用 updateCells 建立新 cell
   result = create_finops_dashboard(
       dashboard_name="{{使用者指定的名稱}}",
       catalog="develop_catalog",
       schema="system_report",
       months_back={{使用者指定的月數}},
       auto_publish=True
   )
   
   if result["success"]:
       print(f"🎉 儀表板已建立：{result['url']}")
       print(f"Dashboard ID: {result['dashboard_id']}")
   else:
       print(f"❌ 建立失敗：{result.get('error', 'Unknown error')}")
   ```
   - 執行此 cell 以建立儀表板

4. **回報結果**
   - 從執行結果中提取 dashboard_id 和 url
   - 提供可點擊的連結給使用者

### 觸發關鍵字

以下自然語言請求應該觸發此 skill：
- "建立 FinOps 儀表板"
- "幫我建立一個 dashboard"
- "我要一個成本分析儀表板"
- "建立綜合型 FinOps 儀表板"
- "Create a FinOps dashboard"
- "Generate a cost dashboard for me"

### 參數對應

| 使用者說法 | 參數 | 預設值 |
|-----------|------|--------|
| "最近 3 個月" | months_back=3 | 6 |
| "高階主管儀表板" | dashboard_name="高階主管儀表板" | "綜合型 FinOps 儀表板" |
| "不要發布" | auto_publish=False | True |

---

### 方式 2：使用 MCP 工具

如果您的環境支援 MCP 工具，可以使用以下工具：

## 可用的 MCP 工具

| 工具 | 說明 |
|------|-------------|
| `get_table_details` | **步驟 1**：取得資料表結構以設計查詢 |
| `execute_sql` | **步驟 3**：測試 SQL 查詢 - 部署前必須執行！ |
| `get_best_warehouse` | 取得可用的倉儲 ID |
| `create_or_update_dashboard` | **步驟 5**：部署儀表板 JSON（僅在驗證後！） |
| `get_dashboard` | 依 ID 取得儀表板詳細資訊 |
| `list_dashboards` | 列出工作區中的儀表板 |
| `trash_dashboard` | 將儀表板移至垃圾桶 |
| `publish_dashboard` | 發布儀表板供檢視者使用 |
| `unpublish_dashboard` | 取消發布儀表板 |

---

## 實作指南

### 1) 資料集架構（嚴格）

- **每個領域一個資料集**（例如：訂單、客戶、產品）
- **每個資料集只有一個有效的 SQL 查詢**（不允許用 `;` 分隔多個查詢）
- 始終使用**完整限定的資料表名稱**：`catalog.schema.table_name`
- SELECT 必須包含小工具所需的所有維度，以及透過 `AS` 別名定義的所有衍生欄位
- 將所有商業邏輯（CASE/WHEN、COALESCE、比率）放入資料集 SELECT 中，並使用明確的別名
- **契約規則**：每個小工具的 `fieldName` 必須完全符合資料集欄位或別名

### 2) 小工具欄位表達式

> **重要：欄位名稱匹配規則**
> `query.fields` 中的 `name` 必須完全符合 `encodings` 中的 `fieldName`。
> 如果不匹配，小工具會顯示「沒有選擇要視覺化的欄位」錯誤！

**聚合的正確模式：**
```json
// 在 query.fields 中：
{"name": "sum(spend)", "expression": "SUM(`spend`)"}

// 在 encodings 中（必須匹配！）：
{"fieldName": "sum(spend)", "displayName": "Total Spend"}
```

**錯誤 - 名稱不匹配：**
```json
// 在 query.fields 中：
{"name": "spend", "expression": "SUM(`spend`)"}  // name 是 "spend"

// 在 encodings 中：
{"fieldName": "sum(spend)", ...}  // 錯誤："sum(spend)" ≠ "spend"
```

小工具查詢中允許的表達式（您不能在表達式中使用 CAST 或其他 SQL）：

**數字：**
```json
{"name": "sum(revenue)", "expression": "SUM(`revenue`)"}
{"name": "avg(price)", "expression": "AVG(`price`)"}
{"name": "count(orders)", "expression": "COUNT(`order_id`)"}
{"name": "countdistinct(customers)", "expression": "COUNT(DISTINCT `customer_id`)"}
{"name": "min(date)", "expression": "MIN(`order_date`)"}
{"name": "max(date)", "expression": "MAX(`order_date`)"}
```

**日期**（時間序列使用 daily，分組比較使用 weekly/monthly）：
```json
{"name": "daily(date)", "expression": "DATE_TRUNC(\"DAY\", `date`)"}
{"name": "weekly(date)", "expression": "DATE_TRUNC(\"WEEK\", `date`)"}
{"name": "monthly(date)", "expression": "DATE_TRUNC(\"MONTH\", `date`)"}
```

**簡單欄位引用**（用於預先聚合的資料）：
```json
{"name": "category", "expression": "`category`"}
```

如果您需要條件邏輯或多欄位公式，請先在資料集 SQL 中計算衍生欄位。

### 3) SPARK SQL 模式

- 日期運算：`date_sub(current_date(), N)` 用於天數，`add_months(current_date(), -N)` 用於月份
- 日期截斷：`DATE_TRUNC('DAY'|'WEEK'|'MONTH'|'QUARTER'|'YEAR', column)`
- **避免**使用 `INTERVAL` 語法 - 改用函數

### 4) 版面配置（6 欄網格，無間隙）

每個小工具都有一個位置：`{"x": 0, "y": 0, "width": 2, "height": 4}`

**重要**：每一列必須精確填滿 width=6。不允許有間隙。

**建議的小工具大小：**

| 小工具類型 | 寬度 | 高度 | 備註 |
|-------------|-------|--------|-------|
| 文字標題 | 6 | 1 | 全寬；標題和副標題使用分開的小工具 |
| 計數器/KPI | 2 | **3-4** | **絕不使用 height=2** - 太擁擠！ |
| 折線圖/長條圖 | 3 | **5-6** | 並排配對以填滿列 |
| 圓餅圖 | 3 | **5-6** | 需要圖例空間 |
| 全寬圖表 | 6 | 5-7 | 用於詳細的時間序列 |
| 表格 | 6 | 5-8 | 全寬以提高可讀性 |

**標準儀表板結構：**
```text
y=0:  標題 (w=6, h=1) - 儀表板標題（使用分開的小工具！）
y=1:  副標題 (w=6, h=1) - 說明（使用分開的小工具！）
y=2:  KPI (w=2 各, h=3) - 3 個關鍵指標並排
y=5:  區段標題 (w=6, h=1) - 「趨勢」或類似
y=6:  圖表 (w=3 各, h=5) - 兩個圖表並排
y=11: 區段標題 (w=6, h=1) - 「詳細資訊」
y=12: 表格 (w=6, h=6) - 詳細資料
```

### 5) 基數與可讀性（重要）

**儀表板可讀性取決於限制不同值的數量：**

| 維度類型 | 最大值 | 範例 |
|----------------|------------|----------|
| 圖表顏色/群組 | **3-8** | 4 個地區、5 個產品線、3 個層級 |
| 篩選器 | 4-10 | 8 個國家、5 個通路 |
| 高基數 | **僅表格** | customer_id、order_id、SKU |

**在建立任何帶有顏色/分組的圖表之前：**
1. 檢查欄位基數（使用 `get_table_details` 查看不同值）
2. 如果 >10 個不同值，聚合到更高層級或使用 TOP-N + 「其他」桶
3. 對於高基數維度，使用表格小工具而不是圖表

### 6) 小工具規格

**小工具命名慣例（重要）：**
- `widget.name`：僅限字母數字 + 連字號 + 底線（無空格、括號、冒號）
- `frame.title`：人類可讀的名稱（允許任何字元）
- `widget.queries[0].name`：始終使用 `"main_query"`

**重要版本要求：**

| 小工具類型 | 版本 |
|-------------|---------|
| counter | 2 |
| table | 2 |
| filter-multi-select | 2 |
| filter-single-select | 2 |
| filter-date-range-picker | 2 |
| bar | 3 |
| line | 3 |
| pie | 3 |
| text | N/A（無 spec 區塊） |

---

**文字（標題/說明）：**
- **重要：文字小工具不使用 spec 區塊！**
- 直接在小工具上使用 `multilineTextboxSpec`
- 支援 markdown：`#`、`##`、`###`、`**粗體**`、`*斜體*`
- **重要：`lines` 陣列中的多個項目會串連在單行上，不會顯示為分開的行！**
- 對於標題 + 副標題，在不同的 y 位置使用**分開的文字小工具**

```json
// 正確：標題和副標題使用分開的小工具
{
  "widget": {
    "name": "title",
    "multilineTextboxSpec": {
      "lines": ["## 儀表板標題"]
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 1}
},
{
  "widget": {
    "name": "subtitle",
    "multilineTextboxSpec": {
      "lines": ["這裡是說明文字"]
    }
  },
  "position": {"x": 0, "y": 1, "width": 6, "height": 1}
}

// 錯誤：多行會串連成一行！
{
  "widget": {
    "name": "title-widget",
    "multilineTextboxSpec": {
      "lines": ["## 儀表板標題", "這裡是說明文字"]  // 變成 "## 儀表板標題這裡是說明文字"
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 2}
}
```

---

**計數器（KPI）：**
- `version`：**2**（不是 3！）
- `widgetType`：`"counter"`
- **百分比值在資料中必須是 0-1**（不是 0-100）

**計數器的兩種模式：**

**模式 1：預先聚合的資料集（1 列，無篩選器）**
- 資料集恰好返回 1 列
- 使用 `"disaggregated": true` 和簡單欄位引用
- 欄位 `name` 直接匹配資料集欄位

```json
{
  "widget": {
    "name": "total-revenue",
    "queries": [{
      "name": "main_query",
      "query": {
        "datasetName": "summary_ds",
        "fields": [{"name": "revenue", "expression": "`revenue`"}],
        "disaggregated": true
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "counter",
      "encodings": {
        "value": {"fieldName": "revenue", "displayName": "總收入"}
      },
      "frame": {"showTitle": true, "title": "總收入"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 3}
}
```

**模式 2：聚合小工具（多列資料集，支援篩選器）**
- 資料集返回多列（例如，按篩選器維度分組）
- 使用 `"disaggregated": false` 和聚合表達式
- **重要**：欄位 `name` 必須完全匹配 `fieldName`（例如，`"sum(spend)"`）

```json
{
  "widget": {
    "name": "total-spend",
    "queries": [{
      "name": "main_query",
      "query": {
        "datasetName": "by_category",
        "fields": [{"name": "sum(spend)", "expression": "SUM(`spend`)"}],
        "disaggregated": false
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "counter",
      "encodings": {
        "value": {"fieldName": "sum(spend)", "displayName": "總支出"}
      },
      "frame": {"showTitle": true, "title": "總支出"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 3}
}
```

---

**表格：**
- `version`：**2**（不是 1 或 3！）
- `widgetType`：`"table"`
- **欄位只需要 `fieldName` 和 `displayName`** - 不需要其他屬性！
- 對原始列使用 `"disaggregated": true`

```json
{
  "widget": {
    "name": "details-table",
    "queries": [{
      "name": "main_query",
      "query": {
        "datasetName": "details_ds",
        "fields": [
          {"name": "name", "expression": "`name`"},
          {"name": "value", "expression": "`value`"}
        ],
        "disaggregated": true
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "table",
      "encodings": {
        "columns": [
          {"fieldName": "name", "displayName": "名稱"},
          {"fieldName": "value", "displayName": "值"}
        ]
      },
      "frame": {"showTitle": true, "title": "詳細資訊"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 6}
}
```

---

**折線圖 / 長條圖：**
- `version`：**3**
- `widgetType`：`"line"` 或 `"bar"`
- 使用 `x`、`y`、可選的 `color` 編碼
- `scale.type`：`"temporal"`（日期）、`"quantitative"`（數字）、`"categorical"`（字串）
- 對預先聚合的資料集資料使用 `"disaggregated": true`

**多條線 - 兩種方法：**

1. **多 Y 欄位**（同一圖表上的不同指標）：
```json
"y": {
  "scale": {"type": "quantitative"},
  "fields": [
    {"fieldName": "sum(orders)", "displayName": "訂單"},
    {"fieldName": "sum(returns)", "displayName": "退貨"}
  ]
}
```

2. **顏色分組**（按維度拆分的相同指標）：
```json
"y": {"fieldName": "sum(revenue)", "scale": {"type": "quantitative"}},
"color": {"fieldName": "region", "scale": {"type": "categorical"}, "displayName": "地區"}
```

**長條圖模式：**
- **堆疊**（預設）：無 `mark` 欄位 - 長條堆疊在一起
- **分組**：新增 `"mark": {"layout": "group"}` - 長條並排以進行比較

**圓餅圖：**
- `version`：**3**
- `widgetType`：`"pie"`
- `angle`：量化聚合
- `color`：分類維度
- 限制為 3-8 個類別以提高可讀性

### 7) 篩選器（全域 vs 頁面層級）

> **重要**：篩選器小工具使用與圖表不同的小工具類型！
> - 有效類型：`filter-multi-select`、`filter-single-select`、`filter-date-range-picker`
> - **不要**使用 `widgetType: "filter"` - 這不存在且會導致錯誤
> - 篩選器使用 `spec.version: 2`
> - **始終為篩選器小工具包含帶有 `showTitle: true` 的 `frame`**

**篩選器小工具類型：**
- `filter-date-range-picker`：用於 DATE/TIMESTAMP 欄位
- `filter-single-select`：單選的分類
- `filter-multi-select`：多選的分類

---

#### 全域篩選器 vs 頁面層級篩選器

| 類型 | 放置位置 | 範圍 | 使用案例 |
|------|-----------|-------|----------|
| **全域篩選器** | 帶有 `"pageType": "PAGE_TYPE_GLOBAL_FILTERS"` 的專用頁面 | 影響所有包含篩選器欄位的資料集的所有頁面 | 跨儀表板篩選（例如，日期範圍、活動） |
| **頁面層級篩選器** | 帶有 `"pageType": "PAGE_TYPE_CANVAS"` 的常規頁面 | 僅影響同一頁面上的小工具 | 頁面特定篩選（例如，僅在細分頁面上的平台篩選器） |

**關鍵見解**：篩選器僅影響包含篩選器欄位的資料集。要讓篩選器僅影響特定頁面：
1. 在應該被篩選的頁面的資料集中包含篩選器維度
2. 從不應該被篩選的頁面的資料集中排除篩選器維度

---

#### 篩選器小工具結構

> **重要**：不要使用 `associative_filter_predicate_group` - 它會導致 SQL 錯誤！
> 改用簡單的欄位表達式。

```json
{
  "widget": {
    "name": "filter_region",
    "queries": [{
      "name": "ds_data_region",
      "query": {
        "datasetName": "ds_data",
        "fields": [
          {"name": "region", "expression": "`region`"}
        ],
        "disaggregated": false
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "filter-multi-select",
      "encodings": {
        "fields": [{
          "fieldName": "region",
          "displayName": "地區",
          "queryName": "ds_data_region"
        }]
      },
      "frame": {"showTitle": true, "title": "地區"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 2}
}
```

---

#### 全域篩選器範例

放置在專用篩選器頁面上：

```json
{
  "name": "filters",
  "displayName": "篩選器",
  "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
  "layout": [
    {
      "widget": {
        "name": "filter_campaign",
        "queries": [{
          "name": "ds_campaign",
          "query": {
            "datasetName": "overview",
            "fields": [{"name": "campaign_name", "expression": "`campaign_name`"}],
            "disaggregated": false
          }
        }],
        "spec": {
          "version": 2,
          "widgetType": "filter-multi-select",
          "encodings": {
            "fields": [{
              "fieldName": "campaign_name",
              "displayName": "活動",
              "queryName": "ds_campaign"
            }]
          },
          "frame": {"showTitle": true, "title": "活動"}
        }
      },
      "position": {"x": 0, "y": 0, "width": 2, "height": 2}
    }
  ]
}
```

---

#### 頁面層級篩選器範例

直接放置在畫布頁面上（僅影響該頁面）：

```json
{
  "name": "platform_breakdown",
  "displayName": "平台細分",
  "pageType": "PAGE_TYPE_CANVAS",
  "layout": [
    {
      "widget": {
        "name": "page-title",
        "multilineTextboxSpec": {"lines": ["## 平台細分"]}
      },
      "position": {"x": 0, "y": 0, "width": 4, "height": 1}
    },
    {
      "widget": {
        "name": "filter_platform",
        "queries": [{
          "name": "ds_platform",
          "query": {
            "datasetName": "platform_data",
            "fields": [{"name": "platform", "expression": "`platform`"}],
            "disaggregated": false
          }
        }],
        "spec": {
          "version": 2,
          "widgetType": "filter-multi-select",
          "encodings": {
            "fields": [{
              "fieldName": "platform",
              "displayName": "平台",
              "queryName": "ds_platform"
            }]
          },
          "frame": {"showTitle": true, "title": "平台"}
        }
      },
      "position": {"x": 4, "y": 0, "width": 2, "height": 2}
    }
    // ... 此頁面上的其他小工具
  ]
}
```

---

**篩選器版面配置指南：**
- 全域篩選器：放置在專用篩選器頁面上，在 `x=0` 處垂直堆疊
- 頁面層級篩選器：放置在頁面的標題區域（例如，右上角）
- 典型大小：`width: 2, height: 2`

### 8) 品質檢查清單

部署前，請驗證：
1. 所有小工具名稱僅使用字母數字 + 連字號 + 底線
2. 所有列的總和為 width=6，無間隙
3. KPI 使用 height 3-4，圖表使用 height 5-6
4. 圖表維度有 ≤8 個不同值
5. 所有小工具 fieldNames 完全匹配資料集欄位
6. **query.fields 中的欄位 `name` 完全匹配 encodings 中的 `fieldName`**（例如，兩者都是 `"sum(spend)"`）
7. 計數器資料集：對 1 列資料集使用 `disaggregated: true`，對多列使用 `disaggregated: false` 與聚合
8. 百分比值為 0-1（不是 0-100）
9. SQL 使用 Spark 語法（date_sub，不是 INTERVAL）
10. **所有 SQL 查詢透過 `execute_sql` 測試並返回預期資料**

---

## 完整範例

```python
import json

# 步驟 1：檢查資料表結構
table_info = get_table_details(catalog="samples", schema="nyctaxi")

# 步驟 2：測試查詢
execute_sql("SELECT COUNT(*) as trips, AVG(fare_amount) as avg_fare, AVG(trip_distance) as avg_distance FROM samples.nyctaxi.trips")
execute_sql("""
    SELECT pickup_zip, COUNT(*) as trip_count
    FROM samples.nyctaxi.trips
    GROUP BY pickup_zip
    ORDER BY trip_count DESC
    LIMIT 10
""")

# 步驟 3：建立儀表板 JSON
dashboard = {
    "datasets": [
        {
            "name": "summary",
            "displayName": "摘要統計",
            "queryLines": [
                "SELECT COUNT(*) as trips, AVG(fare_amount) as avg_fare, ",
                "AVG(trip_distance) as avg_distance ",
                "FROM samples.nyctaxi.trips "
            ]
        },
        {
            "name": "by_zip",
            "displayName": "按郵遞區號的行程",
            "queryLines": [
                "SELECT pickup_zip, COUNT(*) as trip_count ",
                "FROM samples.nyctaxi.trips ",
                "GROUP BY pickup_zip ",
                "ORDER BY trip_count DESC ",
                "LIMIT 10 "
            ]
        }
    ],
    "pages": [{
        "name": "overview",
        "displayName": "NYC 計程車概覽",
        "pageType": "PAGE_TYPE_CANVAS",
        "layout": [
            # 文字標題 - 無 spec 區塊！標題和副標題使用分開的小工具！
            {
                "widget": {
                    "name": "title",
                    "multilineTextboxSpec": {
                        "lines": ["## NYC 計程車儀表板"]
                    }
                },
                "position": {"x": 0, "y": 0, "width": 6, "height": 1}
            },
            {
                "widget": {
                    "name": "subtitle",
                    "multilineTextboxSpec": {
                        "lines": ["行程統計與分析"]
                    }
                },
                "position": {"x": 0, "y": 1, "width": 6, "height": 1}
            },
            # 計數器 - version 2, width 2!
            {
                "widget": {
                    "name": "total-trips",
                    "queries": [{
                        "name": "main_query",
                        "query": {
                            "datasetName": "summary",
                            "fields": [{"name": "trips", "expression": "`trips`"}],
                            "disaggregated": True
                        }
                    }],
                    "spec": {
                        "version": 2,
                        "widgetType": "counter",
                        "encodings": {
                            "value": {"fieldName": "trips", "displayName": "總行程數"}
                        },
                        "frame": {"title": "總行程數", "showTitle": True}
                    }
                },
                "position": {"x": 0, "y": 2, "width": 2, "height": 3}
            },
            {
                "widget": {
                    "name": "avg-fare",
                    "queries": [{
                        "name": "main_query",
                        "query": {
                            "datasetName": "summary",
                            "fields": [{"name": "avg_fare", "expression": "`avg_fare`"}],
                            "disaggregated": True
                        }
                    }],
                    "spec": {
                        "version": 2,
                        "widgetType": "counter",
                        "encodings": {
                            "value": {"fieldName": "avg_fare", "displayName": "平均票價"}
                        },
                        "frame": {"title": "平均票價", "showTitle": True}
                    }
                },
                "position": {"x": 2, "y": 2, "width": 2, "height": 3}
            },
            {
                "widget": {
                    "name": "total-distance",
                    "queries": [{
                        "name": "main_query",
                        "query": {
                            "datasetName": "summary",
                            "fields": [{"name": "avg_distance", "expression": "`avg_distance`"}],
                            "disaggregated": True
                        }
                    }],
                    "spec": {
                        "version": 2,
                        "widgetType": "counter",
                        "encodings": {
                            "value": {"fieldName": "avg_distance", "displayName": "平均距離"}
                        },
                        "frame": {"title": "平均距離", "showTitle": True}
                    }
                },
                "position": {"x": 4, "y": 2, "width": 2, "height": 3}
            },
            # 長條圖 - version 3
            {
                "widget": {
                    "name": "trips-by-zip",
                    "queries": [{
                        "name": "main_query",
                        "query": {
                            "datasetName": "by_zip",
                            "fields": [
                                {"name": "pickup_zip", "expression": "`pickup_zip`"},
                                {"name": "trip_count", "expression": "`trip_count`"}
                            ],
                            "disaggregated": True
                        }
                    }],
                    "spec": {
                        "version": 3,
                        "widgetType": "bar",
                        "encodings": {
                            "x": {"fieldName": "pickup_zip", "scale": {"type": "categorical"}, "displayName": "郵遞區號"},
                            "y": {"fieldName": "trip_count", "scale": {"type": "quantitative"}, "displayName": "行程數"}
                        },
                        "frame": {"title": "按上車郵遞區號的行程", "showTitle": True}
                    }
                },
                "position": {"x": 0, "y": 5, "width": 6, "height": 5}
            },
            # 表格 - version 2, 最小欄位屬性！
            {
                "widget": {
                    "name": "zip-table",
                    "queries": [{
                        "name": "main_query",
                        "query": {
                            "datasetName": "by_zip",
                            "fields": [
                                {"name": "pickup_zip", "expression": "`pickup_zip`"},
                                {"name": "trip_count", "expression": "`trip_count`"}
                            ],
                            "disaggregated": True
                        }
                    }],
                    "spec": {
                        "version": 2,
                        "widgetType": "table",
                        "encodings": {
                            "columns": [
                                {"fieldName": "pickup_zip", "displayName": "郵遞區號"},
                                {"fieldName": "trip_count", "displayName": "行程數"}
                            ]
                        },
                        "frame": {"title": "熱門郵遞區號", "showTitle": True}
                    }
                },
                "position": {"x": 0, "y": 10, "width": 6, "height": 5}
            }
        ]
    }]
}

# 步驟 4：部署
result = create_or_update_dashboard(
    display_name="NYC 計程車儀表板",
    parent_path="/Workspace/Users/me/dashboards",
    serialized_dashboard=json.dumps(dashboard),
    warehouse_id=get_best_warehouse(),
)
print(result["url"])
```

## 帶篩選器的完整範例

```python
import json

# 帶有地區全域篩選器的儀表板
dashboard_with_filters = {
    "datasets": [
        {
            "name": "sales",
            "displayName": "銷售資料",
            "queryLines": [
                "SELECT region, SUM(revenue) as total_revenue ",
                "FROM catalog.schema.sales ",
                "GROUP BY region"
            ]
        }
    ],
    "pages": [
        {
            "name": "overview",
            "displayName": "銷售概覽",
            "pageType": "PAGE_TYPE_CANVAS",
            "layout": [
                {
                    "widget": {
                        "name": "total-revenue",
                        "queries": [{
                            "name": "main_query",
                            "query": {
                                "datasetName": "sales",
                                "fields": [{"name": "total_revenue", "expression": "`total_revenue`"}],
                                "disaggregated": True
                            }
                        }],
                        "spec": {
                            "version": 2,  # 計數器使用 Version 2！
                            "widgetType": "counter",
                            "encodings": {
                                "value": {"fieldName": "total_revenue", "displayName": "總收入"}
                            },
                            "frame": {"title": "總收入", "showTitle": True}
                        }
                    },
                    "position": {"x": 0, "y": 0, "width": 6, "height": 3}
                }
            ]
        },
        {
            "name": "filters",
            "displayName": "篩選器",
            "pageType": "PAGE_TYPE_GLOBAL_FILTERS",  # 全域篩選器頁面必須！
            "layout": [
                {
                    "widget": {
                        "name": "filter_region",
                        "queries": [{
                            "name": "ds_sales_region",
                            "query": {
                                "datasetName": "sales",
                                "fields": [
                                    {"name": "region", "expression": "`region`"}
                                    # 不要使用 associative_filter_predicate_group - 會導致 SQL 錯誤！
                                ],
                                "disaggregated": False  # 篩選器使用 False！
                            }
                        }],
                        "spec": {
                            "version": 2,  # 篩選器使用 Version 2！
                            "widgetType": "filter-multi-select",  # 不是 "filter"！
                            "encodings": {
                                "fields": [{
                                    "fieldName": "region",
                                    "displayName": "地區",
                                    "queryName": "ds_sales_region"  # 必須匹配查詢名稱！
                                }]
                            },
                            "frame": {"showTitle": True, "title": "地區"}  # 始終顯示標題！
                        }
                    },
                    "position": {"x": 0, "y": 0, "width": 2, "height": 2}
                }
            ]
        }
    ]
}

# 部署帶篩選器的儀表板
result = create_or_update_dashboard(
    display_name="帶篩選器的銷售儀表板",
    parent_path="/Workspace/Users/me/dashboards",
    serialized_dashboard=json.dumps(dashboard_with_filters),
    warehouse_id=get_best_warehouse(),
)
print(result["url"])
```

## 疑難排解

### 小工具顯示「沒有選擇要視覺化的欄位」

**這是欄位名稱不匹配錯誤。** `query.fields` 中的 `name` 必須完全匹配 `encodings` 中的 `fieldName`。

**修正：**確保名稱完全匹配：
```json
// 錯誤 - 名稱不匹配
"fields": [{"name": "spend", "expression": "SUM(`spend`)"}]
"encodings": {"value": {"fieldName": "sum(spend)", ...}}  // 錯誤！

// 正確 - 名稱匹配
"fields": [{"name": "sum(spend)", "expression": "SUM(`spend`)"}]
"encodings": {"value": {"fieldName": "sum(spend)", ...}}  // 正確！
```

### 小工具顯示「無效的小工具定義」

**檢查版本號：**
- 計數器：`version: 2`
- 表格：`version: 2`
- 篩選器：`version: 2`
- 長條圖/折線圖/圓餅圖：`version: 3`

**文字小工具錯誤：**
- 文字小工具不能有 `spec` 區塊
- 直接在小工具物件上使用 `multilineTextboxSpec`
- 不要使用 `widgetType: "text"` - 這是無效的

**表格小工具錯誤：**
- 使用 `version: 2`（不是 1 或 3）
- 欄位物件只需要 `fieldName` 和 `displayName`
- 不要新增 `type`、`numberFormat` 或其他欄位屬性

**計數器小工具錯誤：**
- 使用 `version: 2`（不是 3）
- 確保資料集恰好返回 1 列

### 儀表板顯示空白小工具
- 直接執行資料集 SQL 查詢以檢查資料是否存在
- 驗證欄位別名匹配小工具欄位表達式
- 檢查 `disaggregated` 標誌（對於預先聚合的資料應該是 `true`）

### 版面配置有間隙
- 確保每列的總和為 width=6
- 檢查 y 位置不會跳過值

### 篩選器顯示「無效的小工具定義」
- 檢查 `widgetType` 是以下之一：`filter-multi-select`、`filter-single-select`、`filter-date-range-picker`
- **不要**使用 `widgetType: "filter"` - 這是無效的
- 驗證 `spec.version` 是 `2`
- 確保 encodings 中的 `queryName` 匹配查詢 `name`
- 確認篩選器查詢中的 `disaggregated: false`
- 確保包含帶有 `showTitle: true` 的 `frame`

### 篩選器未影響預期頁面
- **全域篩選器**（在 `PAGE_TYPE_GLOBAL_FILTERS` 頁面上）影響所有包含篩選器欄位的資料集
- **頁面層級篩選器**（在 `PAGE_TYPE_CANVAS` 頁面上）僅影響同一頁面上的小工具
- 篩選器僅對包含篩選器維度欄位的資料集有效

### 篩選器顯示 `associative_filter_predicate_group` 的「UNRESOLVED_COLUMN」錯誤
- **不要**在篩選器查詢中使用 `COUNT_IF(\`associative_filter_predicate_group\`)`
- 當儀表板執行查詢時，此內部表達式會導致 SQL 錯誤
- 改用簡單的欄位表達式：`{"name": "field", "expression": "\`field\`"}`

### 文字小工具在同一行上顯示標題和說明
- `lines` 陣列中的多個項目會**串連**，不會顯示在分開的行上
- 在不同的 y 位置使用**分開的文字小工具**作為標題和副標題
- 範例：標題在 y=0，height=1，副標題在 y=1，height=1
