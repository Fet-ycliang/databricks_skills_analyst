---
name: detect-cost-anomalies
description: 使用統計方法檢測異常的成本激增或下降，及早發現問題
tags: [anomaly-detection, monitoring, alerts, z-score]
---

# 檢測成本異常

## 描述
使用 Z-score 統計方法檢測最近 7 天內的成本異常，識別與歷史模式顯著偏離的服務。用於及早發現成本問題和異常支出。

## 使用時機
* 每日成本監控
* 異常警報設定
* 成本激增調查
* 預算超支預警

## 查詢

```sql
-- 使用 Z-score 方法檢測成本異常（最近 7 天）
WITH daily_costs AS (
  SELECT 
    date_key,
    TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd') AS date,
    ConsumedService,
    cost_category,
    SUM(total_cost) AS daily_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ConsumedService, cost_category
),
baseline_stats AS (
  SELECT 
    ConsumedService,
    cost_category,
    AVG(daily_cost) AS avg_cost,
    STDDEV(daily_cost) AS stddev_cost,
    MIN(daily_cost) AS min_cost,
    MAX(daily_cost) AS max_cost,
    PERCENTILE(daily_cost, 0.95) AS p95_cost,
    COUNT(*) AS sample_size
  FROM daily_costs
  WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), 90) AND DATE_SUB(CURRENT_DATE(), 8)
  GROUP BY ConsumedService, cost_category
  HAVING COUNT(*) >= 30  -- 確保統計顯著性
),
recent_costs AS (
  SELECT 
    date,
    ConsumedService,
    cost_category,
    daily_cost
  FROM daily_costs
  WHERE date >= DATE_SUB(CURRENT_DATE(), 7)
)
SELECT 
  rc.date,
  rc.ConsumedService,
  rc.cost_category,
  ROUND(rc.daily_cost, 2) AS daily_cost,
  ROUND(bs.avg_cost, 2) AS baseline_avg,
  ROUND(bs.stddev_cost, 2) AS baseline_stddev,
  ROUND(bs.p95_cost, 2) AS p95_threshold,
  ROUND((rc.daily_cost - bs.avg_cost) / NULLIF(bs.stddev_cost, 0), 2) AS z_score,
  ROUND(rc.daily_cost - bs.avg_cost, 2) AS deviation,
  ROUND((rc.daily_cost - bs.avg_cost) / NULLIF(bs.avg_cost, 0) * 100, 2) AS deviation_pct,
  CASE 
    WHEN rc.daily_cost > bs.p95_cost * 1.5 THEN '🔴 極端異常'
    WHEN ABS((rc.daily_cost - bs.avg_cost) / NULLIF(bs.stddev_cost, 0)) > 3 THEN '🔴 嚴重異常'
    WHEN rc.daily_cost > bs.p95_cost THEN '🟡 超過 P95'
    WHEN ABS((rc.daily_cost - bs.avg_cost) / NULLIF(bs.stddev_cost, 0)) > 2 THEN '🟡 警告'
    ELSE '🟢 正常'
  END AS anomaly_status,
  CASE 
    WHEN rc.daily_cost > bs.avg_cost THEN '成本激增'
    WHEN rc.daily_cost < bs.avg_cost THEN '成本下降'
    ELSE '正常'
  END AS trend_direction,
  bs.sample_size AS baseline_days
FROM recent_costs rc
JOIN baseline_stats bs 
  ON rc.ConsumedService = bs.ConsumedService 
  AND rc.cost_category = bs.cost_category
WHERE ABS((rc.daily_cost - bs.avg_cost) / NULLIF(bs.stddev_cost, 0)) > 2
   OR rc.daily_cost > bs.p95_cost
ORDER BY z_score DESC, rc.date DESC
```

## 輸出欄位

* `date` - 異常發生日期
* `ConsumedService` - Azure 服務名稱
* `cost_category` - 成本類別
* `daily_cost` - 當日成本
* `baseline_avg` - 基準平均成本（過去 30-90 天）
* `baseline_stddev` - 基準標準差
* `p95_threshold` - 第 95 百分位閾值
* `z_score` - Z-score 值（標準差倍數）
* `deviation` - 偏差金額
* `deviation_pct` - 偏差百分比
* `anomaly_status` - 異常狀態
* `trend_direction` - 趨勢方向（激增/下降）
* `baseline_days` - 基準期天數

## 異常等級說明

### 🔴 極端異常（Z-score > 3 或 > P95 × 1.5）
* **嚴重程度**：最高
* **行動**：立即調查
* **典型原因**：
  * 新資源大量部署
  * 配置錯誤
  * 安全事件
  * 資料處理異常

### 🔴 嚴重異常（Z-score > 3）
* **嚴重程度**：高
* **行動**：24 小時內調查
* **典型原因**：
  * 資源規模擴大
  * 使用量激增
  * 定價變更

### 🟡 超過 P95（> 第 95 百分位）
* **嚴重程度**：中
* **行動**：48 小時內檢閱
* **典型原因**：
  * 正常的尖峰使用
  * 季節性變化
  * 計畫內的擴展

### 🟡 警告（Z-score > 2）
* **嚴重程度**：低-中
* **行動**：監控趨勢
* **典型原因**：
  * 使用模式變化
  * 新專案啟動

## 使用範例

### 範例 1：只看嚴重異常
```sql
-- 在最後加入篩選
WHERE ABS((rc.daily_cost - bs.avg_cost) / NULLIF(bs.stddev_cost, 0)) > 3
ORDER BY z_score DESC
```

### 範例 2：按日期彙總異常數量
```sql
-- 查看每日異常數量趨勢
SELECT 
  date,
  COUNT(*) AS anomaly_count,
  SUM(CASE WHEN z_score > 3 THEN 1 ELSE 0 END) AS critical_count,
  ROUND(SUM(deviation), 2) AS total_deviation
FROM (
  -- 原查詢
)
GROUP BY date
ORDER BY date DESC
```

### 範例 3：只看特定服務
```sql
-- 只檢測 Databricks 的異常（在 baseline_stats CTE 中加入此條件）
WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), 90) AND DATE_SUB(CURRENT_DATE(), 8)
  AND ConsumedService = 'Microsoft.Databricks'
```

## 調查步驟

### 1. 確認異常（5-10 分鐘）
* 檢查異常是否真實存在
* 確認不是資料品質問題
* 查看相關服務是否也有異常

### 2. 識別根本原因（30-60 分鐘）
```sql
-- 查看異常日期的資源詳情
SELECT 
  ResourceGroup,
  ResourceName,
  ProductName,
  ROUND(SUM(CostInBillingCurrency), 2) AS cost,
  SUM(Quantity) AS quantity
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key = 20240115  -- 異常日期（格式：yyyyMMdd）
  AND ConsumedService = 'Microsoft.Compute'  -- 異常服務
GROUP BY ResourceGroup, ResourceName, ProductName
ORDER BY cost DESC
LIMIT 20
```

### 3. 評估影響（10-20 分鐘）
* 計算額外成本
* 評估是否會持續
* 確定是否需要立即行動

### 4. 採取行動
* **配置錯誤**：立即修正
* **計畫內擴展**：更新預算
* **非預期使用**：聯絡資源擁有者
* **安全事件**：啟動安全流程

## 常見異常原因

### 成本激增
1. **新資源部署**：大量新 VM 或服務
2. **自動縮放觸發**：負載增加導致自動擴展
3. **資料處理**：大量資料處理或 ETL 作業
4. **配置錯誤**：錯誤的 SKU 或數量設定
5. **安全事件**：未授權的資源使用

### 成本下降
1. **資源刪除**：計畫內或意外刪除
2. **服務中斷**：Azure 服務問題
3. **排程執行**：週末或假日減少使用
4. **優化實施**：成本優化措施生效

## 警報設定建議

### 即時警報（Z-score > 3）
* **頻率**：每小時檢查
* **通知**：Slack/Email/Teams
* **接收者**：FinOps 團隊、值班工程師

### 每日摘要（Z-score > 2）
* **頻率**：每日早上
* **通知**：Email 摘要
* **接收者**：FinOps 團隊、成本中心負責人

### 週報（趨勢分析）
* **頻率**：每週一
* **通知**：儀表板 + Email
* **接收者**：管理層、FinOps 團隊

## 相關 Commands

* `show-monthly-cost-summary` - 查看整體成本趨勢
* `show-top-cost-drivers` - 識別高成本服務
* `find-idle-resources` - 檢查是否有新的閒置資源
* `check-tag-coverage` - 確認新資源是否正確標記

## 資料來源

* **主要表格**：`develop_catalog.system_report.finops_daily_cost_summary`
* **資料層級**：Gold 層（已聚合）
* **更新頻率**：每日
* **基準期**：過去 30-90 天（排除最近 7 天）
* **檢測期**：最近 7 天

## 注意事項

1. **統計顯著性**：需要至少 30 天的基準資料
2. **季節性**：考慮業務季節性（如月底、季末）
3. **計畫內變更**：大型部署前應更新預期
4. **假陽性**：正常的業務成長可能觸發警報
5. **資料延遲**：Azure 成本資料可能有 1-2 天延遲
6. **效能**：使用 Gold 層表格，查詢時間約 3-5 秒
