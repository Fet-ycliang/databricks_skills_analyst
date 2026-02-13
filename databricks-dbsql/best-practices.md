# 資料建模和 DBSQL 最佳實踐

Databricks Lakehouse 平台上資料建模模式、DBSQL 效能優化和營運最佳實踐的全面參考。

---

## 資料建模最佳實踐

### Lakehouse 中的星型結構描述 vs 反正規化

Databricks Lakehouse 完全支援維度建模。星型結構描述能很好地轉換為 Delta 資料表，並且通常比完全反正規化的方法提供更優越的效能。

**星型結構描述（維度建模）：**
- 中央事實資料表連結到多個反正規化的維度資料表
- 針對複雜分析和多維度聚合進行優化
- 提供直觀的業務流程對應，並能很好地擴展 SCD
- 支援最多約 10 個篩選維度（5 個資料表 x 每個 2 個叢集鍵）
- 清晰的關注點分離實現細粒度治理

**單一大表（OBT）：**
- 包含所有屬性預先連接的單一寬表
- 消除連接，更簡單的治理（只需管理一個資料表）
- Liquid Clustering 限制為 1-4 個鍵，因此有效篩選限制為 1-3 個維度
- 隨著資料增長，全表掃描成為瓶頸
- 缺乏結構化的業務流程對應
- 使細粒度存取控制和資料品質檢查變得複雜

**關鍵發現：**在基準測試中，維度模型優於 OBT（2.6 秒 vs 3.5 秒），儘管需要連接，因為需要掃描的檔案更少。然而，應用 Liquid Clustering 後，OBT 實現了 >3 倍的改進（降至 1.13 秒）。兩種方法都能透過自動快取實現低於 500 毫秒的效能。

**建議方法：**使用混合的獎章架構：
- Silver 層：OBT 或 Data Vault 用於快速整合和清理
- Gold 層：星型結構描述維度模型作為精選的、業務就緒的呈現層，用於 BI 和報告

### 何時正規化 vs 反正規化

| 使用案例 | 方法 |
|---|---|
| 用於 BI 報告的 Gold 層 | 星型結構描述（反正規化維度，正規化事實） |
| Silver 層資料整合 | 正規化或 Data Vault |
| 單一用途的 IoT/日誌分析 | OBT（按 1-3 個維度篩選） |
| 多維度業務分析 | 星型結構描述 |
| 快速演變的結構描述 | Silver 中的 OBT，Gold 中的星型結構描述 |
| 高基數篩選（5+ 個維度） | 每個資料表使用 Liquid Clustering 的星型結構描述 |

**經驗法則：**維度資料表應該高度反正規化（在單一維度資料表中扁平化多對一關係）。事實資料表應該在業務事件的粒度上保持正規化。

### Databricks 中的 Kimball 風格建模

Kimball 維度建模是 Lakehouse 中 Gold 層的建議方法：

1. **識別業務流程**（銷售、訂單、出貨）
2. **宣告粒度**（每筆交易一列、每天一列等）
3. **選擇維度**（誰、什麼、哪裡、何時、為什麼、如何）
4. **識別事實**（在宣告的粒度上可測量的數值）

**Databricks 特定的實作細節：**
- 使用 Unity Catalog 組織維度模型（catalog.schema.table）
- 在維度代理鍵上定義 PRIMARY KEY 約束
- 在事實資料表維度鍵上定義 FOREIGN KEY 約束以進行查詢優化
- 在所有資料表和欄位上新增 COMMENT 以提高可發現性
- 應用 TAGS 進行治理（例如，PII 標記）以啟用下游 AI/BI 功能
- 在維度鍵上使用 `ANALYZE TABLE ... COMPUTE STATISTICS FOR COLUMNS` 以支援自適應查詢執行

**關鍵原則：**「您在前期對資料建模越好，就越容易開箱即用地在其上利用 AI。」適當的結構描述設計能啟用下游 AI/BI 功能。

### 事實資料表模式

**設計規則：**
- 在最細粒度的交易層級儲存量化的數值度量
- 對財務資料使用 DECIMAL 而非浮點數
- 包含引用維度資料表的外鍵
- 包含退化維度（來源系統識別碼，如訂單號碼）
- 交易事實資料表通常不會更新或版本化
- 按經常連接的維度的外鍵對事實資料表進行叢集

**事實資料表類型：**
- **交易事實：**每個事件一列（最常見）
- **週期快照事實：**每個時間段每個實體一列
- **累積快照事實：**每個實體生命週期一列，隨著里程碑的達成而更新

**事實資料表 Liquid Clustering 策略：**
```sql
CREATE TABLE gold.sales.fact_orders (
  order_key BIGINT GENERATED ALWAYS AS IDENTITY,
  customer_key BIGINT NOT NULL,
  product_key BIGINT NOT NULL,
  date_key INT NOT NULL,
  order_amount DECIMAL(18,2),
  quantity INT,
  CONSTRAINT fk_customer FOREIGN KEY (customer_key) REFERENCES gold.sales.dim_customer(customer_key),
  CONSTRAINT fk_product FOREIGN KEY (product_key) REFERENCES gold.sales.dim_product(product_key)
)
CLUSTER BY (date_key, customer_key);
```

### 維度資料表模式

**設計規則：**
- 對代理鍵使用 `GENERATED ALWAYS AS IDENTITY` 或雜湊值
- 優先使用整數代理鍵而非字串以獲得更好的連接效能
- 高度反正規化：在單一維度資料表中扁平化多對一關係
- 支援複雜類型：MAP 用於可擴展性，STRUCT 用於巢狀屬性，ARRAY 用於多值屬性
- 避免使用 ARRAY/MAP 欄位作為篩選謂詞（它們缺乏欄位層級統計資訊以進行資料跳過）
- 按主鍵加上常見篩選欄位對維度資料表進行叢集

**維度資料表範例：**
```sql
CREATE TABLE gold.sales.dim_customer (
  customer_key BIGINT GENERATED ALWAYS AS IDENTITY,
  customer_id STRING NOT NULL COMMENT '來自來源系統的自然鍵',
  full_name STRING,
  email STRING,
  city STRING,
  state STRING,
  country STRING,
  segment STRING,
  effective_start_date TIMESTAMP,
  effective_end_date TIMESTAMP,
  is_current BOOLEAN,
  CONSTRAINT pk_customer PRIMARY KEY (customer_key)
)
CLUSTER BY (customer_key, segment)
COMMENT '具有 SCD Type 2 歷史追蹤的客戶維度';
```

### 緩慢變化維度（SCD）模式

**SCD Type 1（覆寫）：**
- 就地更新而不追蹤歷史
- 使用 MERGE INTO 搭配匹配的 UPDATE
- 適用於更正或不需要歷史的屬性

**SCD Type 2（歷史追蹤）：**
- 使用代理鍵和中繼資料欄位對記錄進行版本控制
- 包含 `effective_start_date`、`effective_end_date` 和 `is_current` 欄位
- 使用 MERGE INTO 在 DBSQL 中實作 SCD Type 2 邏輯

**使用 MERGE 的 SCD Type 2：**
```sql
MERGE INTO gold.sales.dim_customer AS target
USING (
  SELECT * FROM silver.crm.customers_changes
) AS source
ON target.customer_id = source.customer_id AND target.is_current = TRUE
WHEN MATCHED AND (
  target.full_name != source.full_name OR
  target.city != source.city
) THEN UPDATE SET
  effective_end_date = current_timestamp(),
  is_current = FALSE
WHEN NOT MATCHED THEN INSERT (
  customer_id, full_name, email, city, state, country, segment,
  effective_start_date, effective_end_date, is_current
) VALUES (
  source.customer_id, source.full_name, source.email,
  source.city, source.state, source.country, source.segment,
  current_timestamp(), NULL, TRUE
);
-- 然後在第二次傳遞中為變更的記錄插入新版本
```

**Delta Lake 時間旅行**在配置的日誌保留期限內啟用歷史資料存取，作為 SCD 的補充功能。

### 分割策略

**Databricks 建議對所有新資料表使用 Liquid Clustering 而非傳統分割。**

傳統分割的經驗法則（在需要時）：
- 將分割數量保持在 10,000 以下（理想情況下少於 5,000 個不同值）
- 每個分割應包含至少 1 GB 的資料
- 按 WHERE 子句中經常使用的低基數欄位進行分割（例如，日期、地區）
- 最適合高度選擇性的單分割查詢（例如，篩選一天）

**傳統分割可能仍然適用的情況：**
- 非常大的資料表（數百 TB）具有清晰、穩定的分割鍵
- 查詢始終在同一低基數欄位上進行篩選
- 資料生命週期管理需要分割層級操作

### Liquid Clustering vs 傳統分割

**Liquid Clustering 是所有新 Delta 資料表的預設建議**，包括串流資料表和具體化檢視。它取代了分割和 Z-ORDER。

| 方面 | Liquid Clustering | 分割 + Z-ORDER |
|---|---|---|
| 欄位靈活性 | 隨時變更叢集鍵 | 分割欄位在建立時固定 |
| 維護 | 增量、自動（透過預測性優化） | 需要手動 OPTIMIZE + Z-ORDER |
| 篩選維度 | 最適合 1-4 個叢集鍵 | 一個分割鍵 + Z-ORDER 欄位 |
| 寫入開銷 | 最小（僅重組未叢集的 ZCube） | Z-ORDER 重組整個資料表/分割 |
| 最適合 | 大多數工作負載、演變的存取模式 | 具有穩定、低基數篩選的超大型資料表 |
| 效能 | 可變查詢的查詢速度提升 30-60% | 更適合單分割查找查詢 |

**Liquid Clustering 鍵選擇最佳實踐：**
- 選擇查詢篩選和連接中最常使用的欄位
- 限制為 1-4 個鍵（對於小於 10 TB 的較小資料表，越少越好）
- 對於事實資料表：按最常篩選的外鍵進行叢集
- 對於維度資料表：按主鍵 + 常見篩選欄位進行叢集
- 過多的鍵會稀釋資料跳過的好處；對於小於 10 TB 的資料表，2 個鍵通常優於 4 個鍵

**重要：**Liquid Clustering 與同一資料表上的分割或 Z-ORDER 不相容。

### Z-Ordering 考量

Z-ORDER 是舊方法，現已被 Liquid Clustering 取代：

- Z-ORDER 在優化期間重組整個資料表/分割（寫入開銷較大）
- 不追蹤 ZCube ID，因此每次 OPTIMIZE 都會重新排序所有資料
- 更適合寫入開銷可接受的讀取密集型工作負載
- 對於新資料表，始終優先使用 Liquid Clustering

**遷移路徑：**將現有的分割 + Z-ORDER 資料表遷移到 Liquid Clustering 時：
1. 刪除分割規範
2. 使用選定的鍵啟用 Liquid Clustering
3. 執行 OPTIMIZE 以增量方式叢集資料
4. 允許預測性優化繼續維護佈局

---

## DBSQL 效能

### 查詢優化技巧

**引擎層級優化（在 DBSQL 無伺服器中自動）：**
- **預測性查詢執行（PQE）：**即時監控任務，動態調整查詢執行以避免傾斜、溢出和不必要的工作。與僅在階段完成後重新規劃的自適應查詢執行（AQE）不同，PQE 在發生資料傾斜或記憶體溢出等問題時立即偵測並重新規劃。
- **Photon 向量化 Shuffle：**將資料保持在緊湊的列式格式中，在 CPU 快取內排序，並使用向量化指令以獲得 1.5 倍更高的 shuffle 吞吐量。最適合 CPU 密集型工作負載（大型連接、寬聚合）。
- **低 Shuffle Merge：**優化的 MERGE 實作，減少大多數常見工作負載的 shuffle 開銷。

**手動優化操作：**
- 在維度鍵和經常篩選的欄位上執行 `ANALYZE TABLE ... COMPUTE STATISTICS FOR COLUMNS` 以支援 AQE 和資料跳過
- 設定 `'delta.dataSkippingStatsColumns'` 資料表屬性以指定哪些欄位收集統計資訊
- 定義 PRIMARY KEY 和 FOREIGN KEY 約束以幫助查詢優化器
- 使用確定性查詢（避免在篩選器中使用 `NOW()`、`CURRENT_TIMESTAMP()`）以受益於查詢結果快取
- 優先使用 `CREATE OR REPLACE TABLE` 而非刪除後建立的模式
- 對財務計算使用 `DECIMAL` 而非 `FLOAT`/`DOUBLE`

**DBSQL 的 SQL 撰寫技巧：**
- 早篩選，晚聚合：將 WHERE 子句盡可能推近來源
- 優先使用明確的欄位列表而非 SELECT *
- 使用 CTE 以提高可讀性，但要注意優化器可能會內聯它們
- 當存在原生 SQL 函數時避免使用 Python/Scala UDF（UDF 需要在 Python 和 Spark 之間序列化，顯著減慢查詢速度）
- 在可能的情況下使用視窗函數而非自連接
- 利用 QUALIFY 子句在視窗函數後進行列層級篩選

### 倉儲大小指南

**Databricks 建議對大多數工作負載使用無伺服器 SQL 倉儲。**無伺服器使用智慧工作負載管理（IWM）自動管理查詢工作負載。

**大小策略：**
- 從單一較大的倉儲開始，讓無伺服器功能管理並行性
- 如果需要，縮小規模而不是從小規模開始並擴大
- 如果查詢溢出到磁碟，增加叢集大小

**擴展配置：**
- 低並行性（1-2 個查詢）：保持 max_clusters 較低
- 不可預測的峰值：將 max_num_clusters 設定為高，target_utilization 約 70%
- 對於具有可變/不頻繁負載的儀表板：啟用積極的自動擴展和自動停止

**無伺服器優勢：**
- 在幾秒鐘內啟動和擴展
- 比非無伺服器倉儲更早縮小規模
- 僅在查詢執行時付費
- 30-60 秒冷啟動延遲（無閒置時間的節省遠超過此延遲）
- 所有 2025 年優化（PQE、Photon 向量化 Shuffle）自動可用

### 快取策略

**查詢結果快取：**
- DBSQL 為所有查詢按叢集快取結果
- 當底層 Delta 資料變更時快取會失效
- 要最大化快取命中率，使用確定性查詢（無 `NOW()`、`RAND()` 等）
- OBT 和星型結構描述在第一次執行後都能透過自動快取實現低於 500 毫秒的效能

**Delta 快取（磁碟快取）：**
- 自動將遠端資料以列式格式快取在本地 SSD 上
- 在無伺服器倉儲上無需手動配置即可加速資料讀取
- 對重複掃描相同資料表特別有效

**最佳實踐：**設計儀表板和報告以使用參數化查詢，這些查詢命中相同的底層模式，最大化快取重複使用。

### Photon 引擎優勢

Photon 是用 C++ 編寫的向量化查詢引擎，在 Databricks 上原生執行：

- 在所有 DBSQL 無伺服器倉儲上預設啟用
- 使用 CPU 向量指令（SIMD）以列式批次處理資料
- 擅長：大型連接、寬聚合、字串處理、資料 shuffle
- 2025 年向量化 shuffle 提供 1.5 倍更高的 shuffle 吞吐量
- 與 PQE 結合，在現有 5 倍增益之上提供高達 25% 更快的查詢

### 最近的效能改進（2025）

| 改進 | 影響 |
|---|---|
| 整體生產工作負載 | 高達 40% 更快（自動，無需調整） |
| Photon 向量化 Shuffle | 1.5 倍更高的 shuffle 吞吐量 |
| PQE + Photon 向量化 Shuffle 結合 | 在現有 5 倍增益之上高達 25% 更快 |
| 空間 SQL 查詢 | 高達 17 倍更快（R-tree 索引、優化的空間連接） |
| AI 函數 | 大型批次工作負載高達 85 倍更快 |
| 端到端 Unity Catalog 延遲 | 高達 10 倍改進 |
| 3 年累積改進 | 跨客戶工作負載快 5 倍 |

所有改進都在 DBSQL 無伺服器中上線，無需啟用任何設定。

### 成本優化模式

1. **使用無伺服器 SQL 倉儲：**僅在查詢執行時付費，自動擴展和自動停止
2. **啟用預測性優化：**自動在 Unity Catalog 託管資料表上執行 OPTIMIZE 和 VACUUM
3. **適當調整倉儲大小：**從較大規模開始，根據實際使用模式縮小規模
4. **避免閒置倉儲：**對負載不頻繁的儀表板使用積極的自動停止
5. **利用快取：**設計確定性查詢以最大化結果快取命中率
6. **使用 Liquid Clustering：**減少掃描量，每個查詢消耗更少的 DBU
7. **收集統計資訊：**`ANALYZE TABLE` 啟用更好的查詢計劃，減少浪費的運算
8. **使用查詢設定檔監控：**識別昂貴的操作、溢出和傾斜
9. **使用具體化檢視**用於經常計算的聚合
10. **避免 UDF：**原生函數速度顯著更快，無序列化開銷

---

## 用於 DBSQL 的 Delta Lake 優化

### OPTIMIZE、VACUUM 和 ANALYZE

**建議的執行順序：**OPTIMIZE -> VACUUM -> ANALYZE

**OPTIMIZE：**
- 將小檔案壓縮為較大的檔案（預設目標 1 GB）
- 在具有許多小檔案的資料表上頻繁執行（特別是在串流寫入後）
- 可透過 `delta.targetFileSize` 資料表屬性配置目標大小
- 使用 Liquid Clustering：僅重組未叢集的 ZCube（增量）

**VACUUM：**
- 移除交易日誌中不再存在的舊檔案
- 降低儲存成本
- 使用運算優化實例（AWS C5、Azure F 系列、GCP C2）
- 預設保留期：7 天（可透過 `delta.deletedFileRetentionDuration` 配置）
- 絕不將保留期設定為低於最長執行查詢的持續時間

**ANALYZE TABLE：**
- 計算欄位層級統計資訊以進行查詢優化
- 在資料表覆寫或重大資料變更後立即執行
- 專注於 WHERE 子句、JOIN 和 GROUP BY 中使用的欄位

**預測性優化（建議）：**

> **注意：**在無伺服器 SQL 倉儲上，`delta.enableOptimizeWrite` 和 `delta.autoOptimize.autoCompact` 會自動管理，無法手動設定（它們會引發 `DELTA_UNKNOWN_CONFIGURATION`）。以下屬性僅適用於傳統運算。對於無伺服器，只需在目錄/結構描述層級啟用預測性優化。

```sql
-- 僅限傳統運算：
ALTER TABLE catalog.schema.table_name
SET TBLPROPERTIES ('delta.enableOptimizeWrite' = 'true');
-- 對於 Unity Catalog 託管資料表，預測性優化
-- 自動處理 OPTIMIZE 和 VACUUM
```

### 檔案大小和壓縮

- **自動壓縮：**寫入後自動在分割內組合小檔案
- **優化寫入：**在寫入前透過 shuffle 重新平衡資料以減少小檔案
- **目標檔案大小：**預設 1 GB；針對特定工作負載使用 `delta.targetFileSize` 調整
- 對於具有許多小檔案的資料表（串流擷取），排程定期 OPTIMIZE 作業

### 效能的資料表屬性

> **注意：**`delta.enableOptimizeWrite` 和 `delta.autoOptimize.autoCompact` 僅在傳統運算上有效。在無伺服器 SQL 倉儲上，這些會自動管理，設定它們會引發 `DELTA_UNKNOWN_CONFIGURATION`。其餘屬性在傳統和無伺服器上都有效。

```sql
-- 僅限傳統運算（無伺服器自動管理這些）：
-- 'delta.enableOptimizeWrite' = 'true',
-- 'delta.autoOptimize.autoCompact' = 'true',

-- 在傳統和無伺服器上都有效：
ALTER TABLE catalog.schema.my_table SET TBLPROPERTIES (
  'delta.columnMapping.mode' = 'name',
  'delta.enableChangeDataFeed' = 'true',
  'delta.deletedFileRetentionDuration' = '30 days',
  'delta.dataSkippingStatsColumns' = 'col1,col2,col3'
);
```

---

## Unity Catalog 整合模式

### 組織最佳實踐

- 使用三層命名空間：`catalog.schema.table`
- 在目錄層級按環境（dev/staging/prod）組織
- 在結構描述層級按業務領域組織
- 使用託管資料表（非外部）以受益於預測性優化和增強的治理

### 資料建模的治理功能

- **主鍵/外鍵約束：**告知查詢優化器資料表關聯性
- **列篩選器和欄位遮罩：**資料表層級的細粒度存取控制
- **標籤：**將治理標籤（例如，PII、敏感度層級）應用於資料表和欄位
- **註解：**記錄所有資料表和欄位以提高 AI/BI 可發現性
- **血緣追蹤：**自動血緣以了解資料流經獎章架構

### 實體關聯視覺化

當定義主鍵和外鍵約束時，Unity Catalog 會呈現實體關聯圖，提供維度模型的視覺化文件。

---

## 監控和可觀察性

- **查詢設定檔：**分析執行計劃，識別瓶頸、溢出和資料傾斜
- **查詢歷史記錄：**追蹤查詢效能隨時間的趨勢
- **倉儲監控：**追蹤利用率、佇列時間和擴展事件
- **系統資料表：**查詢 `system.billing`、`system.access` 和 `system.query` 以取得營運見解
- **警報：**為資料品質檢查和 SLA 監控設定 SQL 警報

---

## 要避免的常見反模式

### 資料建模反模式

1. **在 Gold 層跳過維度建模：**OBT 適用於 Silver，但 Gold 應該使用星型結構描述進行多維度分析
2. **過度分割：**超過 5,000-10,000 個分割會降低效能；改用 Liquid Clustering
3. **字串代理鍵：**使用整數 IDENTITY 欄位以獲得更好的連接效能
4. **缺少約束：**不定義 PK/FK 約束會使優化器失去關聯性資訊
5. **缺少註解和標籤：**降低 AI/BI 工具和治理的可發現性
6. **對財務資料使用 FLOAT：**使用 DECIMAL 以避免精度錯誤
7. **在 ARRAY/MAP 欄位上篩選：**這些類型缺乏欄位層級統計資訊以進行資料跳過

### 查詢和效能反模式

1. **刪除後重新建立資料表：**改用 `CREATE OR REPLACE TABLE` 以保留時間旅行並避免讀取器中斷
2. **當存在原生函數時使用 Python/Scala UDF：**序列化開銷顯著減慢查詢速度
3. **不收集統計資訊：**缺少 `ANALYZE TABLE` 會導致次優查詢計劃
4. **在快取查詢中使用非確定性函數：**`NOW()`、`RAND()` 等會阻止查詢結果快取
5. **按錯誤的欄位分割：**按篩選器中未使用的欄位分割會導致全掃描
6. **過多的 Liquid Clustering 鍵：**對於小於 10 TB 的資料表，2 個鍵通常優於 4 個鍵
7. **沒有預測性優化的手動 OPTIMIZE/VACUUM：**為 Unity Catalog 託管資料表啟用預測性優化

### 營運反模式

1. **閒置倉儲：**始終啟用自動停止；對可變工作負載使用無伺服器
2. **倉儲規模過小：**溢出到磁碟的查詢比較大的倉儲浪費更多 DBU
3. **當託管資料表可以時使用外部資料表：**外部資料表錯過預測性優化和增強的治理
4. **跳過 VACUUM：**無限制的檔案增長會增加儲存成本並減慢中繼資料操作
5. **使用過短保留期執行 VACUUM：**可能會破壞長時間執行的查詢和時間旅行

---

## 快速參考：AI 代理的 SQL 模式

為 Databricks 生成 SQL 時，優先使用這些模式：

```sql
-- 使用 CREATE OR REPLACE（不是 DROP + CREATE）
CREATE OR REPLACE TABLE catalog.schema.my_table AS
SELECT ...;

-- 使用 MERGE 進行更新插入（不是 DELETE + INSERT）
MERGE INTO target USING source
ON target.key = source.key
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...;

-- 使用 QUALIFY 進行視窗函數篩選（不是子查詢）
SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) AS rn
FROM my_table
QUALIFY rn = 1;

-- 對金額使用 DECIMAL
SELECT CAST(amount AS DECIMAL(18,2)) AS revenue FROM orders;

-- 載入後收集統計資訊
ANALYZE TABLE catalog.schema.my_table COMPUTE STATISTICS FOR ALL COLUMNS;

-- 啟用預測性優化（僅限傳統運算；無伺服器自動管理此項）
ALTER TABLE catalog.schema.my_table
SET TBLPROPERTIES ('delta.enableOptimizeWrite' = 'true');
```
