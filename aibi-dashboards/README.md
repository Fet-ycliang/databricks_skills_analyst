# AI/BI 儀表板

在 Databricks 上使用經過驗證的 SQL 查詢和結構化 JSON 部署建立 AI/BI 儀表板。

## 概述

此技能透過嚴格的驗證工作流程指導建立 Databricks AI/BI 儀表板（前身為 Lakeview 儀表板）：在部署前測試每個 SQL 查詢、建立符合規範的儀表板 JSON，並透過 MCP 工具部署。當使用者需要在 Unity Catalog 資料之上建立包含計數器、圖表、表格和篩選器的互動式儀表板時，此技能會啟動。該技能強制執行有關小工具版本控制、版面配置網格、欄位名稱匹配和基數限制的最佳實踐，以防止常見的「無效小工具」錯誤。

## 包含內容

```
aibi-dashboards/
└── SKILL.md
```

## 關鍵主題

- 強制查詢驗證工作流程（在部署前透過 `execute_sql` 測試所有 SQL）
- 資料集架構，每個領域一個資料集，並使用完整限定的資料表名稱
- 小工具欄位表達式匹配規則（查詢欄位 `name` 必須等於編碼 `fieldName`）
- 計數器（v2）、表格（v2）、長條圖/折線圖/圓餅圖（v3）和文字標題的小工具規格
- 6 欄網格版面配置系統，無間隙定位
- 使用 `PAGE_TYPE_GLOBAL_FILTERS` 和 `PAGE_TYPE_CANVAS` 的全域篩選器與頁面層級篩選器
- 篩選器小工具類型：`filter-multi-select`、`filter-single-select`、`filter-date-range-picker`
- 圖表維度的基數和可讀性指南
- Spark SQL 日期模式（避免 INTERVAL 語法）
- 疑難排解常見錯誤：欄位不匹配、無效的小工具定義、空白小工具、版面配置間隙

## 何時使用

- 在 Databricks 上建立新的 AI/BI 儀表板
- 建立 KPI 計數器、長條圖、折線圖、圓餅圖或資料表格
- 為儀表板新增全域或頁面層級篩選器
- 除錯「無效的小工具定義」或「沒有選擇要視覺化的欄位」錯誤
- 透過 `create_or_update_dashboard` MCP 工具部署儀表板 JSON
- 使用 Lakeview 儀表板規格

## 相關技能

- [Databricks Unity Catalog](../databricks-unity-catalog/) -- 用於查詢底層資料和系統資料表
- [Spark Declarative Pipelines](../spark-declarative-pipelines/) -- 用於建立為儀表板提供資料的資料管線
- [Databricks Jobs](../databricks-jobs/) -- 用於排程儀表板資料重新整理

## 資源

- [AI/BI 儀表板文件](https://docs.databricks.com/en/dashboards/index.html)
- [Lakeview 儀表板 API](https://docs.databricks.com/api/workspace/lakeview)
