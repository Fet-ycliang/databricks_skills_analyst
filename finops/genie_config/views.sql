-- 閒置資源檢視表
-- 定義：成本 > 0 但無使用量，或使用天數極少的資源
CREATE OR REPLACE VIEW finops.optimization.v_idle_resources AS
SELECT 
  ResourceGroup,
  ResourceName,
  ConsumedService,
  cost_category,
  COUNT(DISTINCT date_key) AS days_with_cost,
  SUM(CostInBillingCurrency) AS total_cost_30d,
  MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS last_seen
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyyMMdd') AS INT)
GROUP BY ResourceGroup, ResourceName, ConsumedService, cost_category
HAVING (SUM(Quantity) = 0 AND SUM(CostInBillingCurrency) > 0)
   OR (COUNT(DISTINCT date_key) < 5);

-- 調整規模建議檢視表
-- 定義：平均每日使用時數低於 8 小時的運算資源
CREATE OR REPLACE VIEW finops.optimization.v_right_sizing_recommendations AS
WITH compute_usage AS (
  SELECT 
    ResourceGroup,
    ResourceName,
    ProductName,
    year_month,
    SUM(CostInBillingCurrency) AS monthly_cost,
    AVG(Quantity) AS avg_daily_hours
  FROM develop_catalog.system_report.infra_azure_cost_silver
  WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 60), 'yyyy-MM')
    AND cost_category = 'Compute'
  GROUP BY ResourceGroup, ResourceName, ProductName, year_month
)
SELECT 
  *,
  CASE 
    WHEN avg_daily_hours < 8 THEN '高優先級：考慮縮編或排程'
    ELSE '正常'
  END AS recommendation
FROM compute_usage
WHERE avg_daily_hours < 16;

-- 孤兒快照檢視表
-- 定義：超過 90 天的快照
CREATE OR REPLACE VIEW finops.optimization.v_orphaned_snapshots AS
SELECT 
  ResourceGroup,
  ResourceName,
  SUM(CostInBillingCurrency) AS total_cost_90d,
  COUNT(DISTINCT date_key) AS billing_days
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  AND MeterName LIKE '%Snapshot%'
GROUP BY ResourceGroup, ResourceName
HAVING billing_days >= 85;

-- 儲存冗餘檢查檢視表
-- 定義：非生產環境中的 GRS 儲存帳戶
CREATE OR REPLACE VIEW finops.optimization.v_storage_redundancy_check AS
SELECT 
  ResourceGroup,
  ResourceName,
  MeterName,
  SUM(CostInBillingCurrency) AS monthly_cost
FROM develop_catalog.system_report.infra_azure_cost_silver
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 30), 'yyyy-MM')
  AND ConsumedService = 'Microsoft.Storage'
  AND (MeterName LIKE '%GRS%' OR MeterName LIKE '%Geo-Redundant%')
  AND (tag_environment IN ('dev', 'test', 'qa') OR ResourceGroup LIKE '%dev%')
GROUP BY ResourceGroup, ResourceName, MeterName;

-- 優化機會總結檢視表
CREATE OR REPLACE VIEW finops.optimization.v_all_opportunities_summary AS
SELECT 'Idle Resources' as type, count(*) as count, sum(total_cost_30d) as potential_savings FROM finops.optimization.v_idle_resources
UNION ALL
SELECT 'Orphaned Snapshots' as type, count(*) as count, sum(total_cost_90d) as potential_savings FROM finops.optimization.v_orphaned_snapshots;

-- 異常檢測：Z-Score (每日)
-- 定義：Z-Score > 3 為嚴重異常
CREATE OR REPLACE VIEW finops.optimization.v_anomaly_zscore_daily AS
WITH daily_costs AS (
  SELECT 
    date_key,
    ConsumedService,
    cost_category,
    SUM(total_cost) AS daily_cost
  FROM develop_catalog.system_report.finops_daily_cost_summary
  WHERE date_key >= CAST(DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 90), 'yyyyMMdd') AS INT)
  GROUP BY date_key, ConsumedService, cost_category
),
stats AS (
  SELECT 
    ConsumedService,
    cost_category,
    AVG(daily_cost) AS avg_cost,
    STDDEV(daily_cost) AS stddev_cost
  FROM daily_costs
  GROUP BY ConsumedService, cost_category
)
SELECT 
  dc.date_key,
  dc.ConsumedService,
  dc.cost_category,
  dc.daily_cost,
  s.avg_cost,
  (dc.daily_cost - s.avg_cost) / NULLIF(s.stddev_cost, 0) AS z_score
FROM daily_costs dc
JOIN stats s ON dc.ConsumedService = s.ConsumedService AND dc.cost_category = s.cost_category
WHERE ABS((dc.daily_cost - s.avg_cost) / NULLIF(s.stddev_cost, 0)) > 2;

-- KPI：承諾覆蓋率 (RI + Savings Plan)
-- 定義：保留與節省計畫成本佔總成本的比例
CREATE OR REPLACE VIEW finops.optimization.v_kpi_commitment_coverage AS
SELECT 
  year_month,
  cost_category,
  SUM(reservation_cost + savingplan_cost) AS commitment_cost,
  SUM(total_cost) AS total_cost,
  SUM(reservation_cost + savingplan_cost) / NULLIF(SUM(total_cost), 0) * 100 AS coverage_pct
FROM develop_catalog.system_report.finops_daily_cost_summary
WHERE year_month >= DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 365), 'yyyy-MM')
  AND cost_category IN ('Compute', 'Database')
GROUP BY year_month, cost_category;

-- KPI：資料新鮮度
-- 定義：各層級資料的延遲天數
CREATE OR REPLACE VIEW finops.optimization.v_kpi_data_freshness AS
SELECT 
  'Gold Layer' AS layer,
  MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd')) AS latest_date,
  DATEDIFF(CURRENT_DATE(), MAX(TO_DATE(CAST(date_key AS STRING), 'yyyyMMdd'))) AS days_lag
FROM develop_catalog.system_report.finops_daily_cost_summary;
