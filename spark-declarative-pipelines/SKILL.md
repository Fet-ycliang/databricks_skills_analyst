---
name: spark-declarative-pipelines
description: "使用 Serverless Compute 建立、設定與更新 Databricks Lakeflow Spark Declarative Pipelines (SDP/LDP)。處理串流資料表 (Streaming Tables)、物化視圖 (Materialized Views)、CDC、SCD Type 2 以及 Auto Loader 攝取模式。適用於建置資料管線、使用 Delta Live Tables、攝取串流資料、實作變更資料擷取 (CDC)，或當使用者提及 SDP、LDP、DLT、Lakeflow Pipelines、Streaming Tables 或 Bronze/Silver/Gold 獎章架構時。"
---

# Lakeflow Spark Declarative Pipelines (SDP)

重要：若這是一個新的管線 (尚不存在)，請參閱快速入門。請務必僅使用使用者指定的語言 (Python 或 SQL)。新專案請務必使用 Databricks Asset Bundles。

---

## 關鍵規則 (務必遵守)
- **必須** 確認語言為 Python 或 SQL。除非另有指示，否則請堅持使用該語言。
- **必須** 若非修改現有管線，請使用下方的 [快速入門](#quick-start)。
- **必須** 預設建立 Serverless 管線。**僅在使用者明確要求 R 語言、Spark RDD API 或 JAR 函式庫時使用 Classic Clusters。**

## 必要步驟

複製此檢核清單並驗證每個項目：
```
- [ ] 已選擇語言: Python 或 SQL
- [ ] 已決定運算類型: Serverless 或 Classic Compute
- [ ] 決定使用多個 Catalog/Schema 還是全部放在一個預設 Schema
- [ ] 考慮哪些應在管線層級參數化以便於部署。
- [ ] 參考下方的 [多 Schema 模式](#multi-schema-patterns)，若不清楚最佳選擇請詢問。
- [ ] 參考下方的 [現代化預設值](#modern-defaults)，若不清楚最佳選擇請詢問。
```

## 快速入門：初始化新管線專案 (Quick Start)

**推薦**: 使用 `databricks pipelines init` 建立具備多環境支援的生產級 Asset Bundle 專案。

### 何時使用 Bundle 初始化

對 **新管線專案** 使用 Bundle 初始化，以便從一開始就有專業的結構。

使用手動工作流程於：
- 不需要多環境的快速原型製作
- 想要繼續使用的現有手動專案
- 學習/實驗

### 步驟 1: 初始化專案

當您要求建立新管線時，我會自動執行此指令：

```bash
databricks pipelines init
```

**互動式提示:**
- **專案名稱**: 例如 `customer_orders_pipeline`
- **初始 Catalog**: Unity Catalog 名稱 (例如 `main`, `prod_catalog`)
- **每位使用者的個人 Schema?**: `yes` 用於開發 (每位使用者有自己的 Schema), `no` 用於生產
- **語言**: SQL 或 Python (從您的請求自動偵測 - 參見下方的語言偵測)

**生成的結構:**
```
my_pipeline/
├── databricks.yml              # 多環境設定 (dev/prod)
├── resources/
│   └── *_etl.pipeline.yml      # 管線資源定義
└── src/
    └── *_etl/
        ├── explorations/       # .ipynb 中的探索程式碼
        └── transformations/    # 您的 .sql 或 .py 檔案
```

### 步驟 2: 客製化轉換 (Transformations)

根據需求，使用此技能中的最佳實踐指南，以客製化的轉換檔案替換 `src/transformations/` 中由初始化過程產生的範例程式碼。

**對於使用 cloudFiles 的 Python 管線**: 詢問使用者要將 Auto Loader Schema Metadata 儲存在哪裡。推薦：
```
/Volumes/{catalog}/{schema}/{pipeline_name}_metadata/schemas
```

### 步驟 3: 部署與執行

```bash
# 部署至 Workspace (預設為 dev)
databricks bundle deploy

# 執行管線
databricks bundle run my_pipeline_etl

# 部署至生產環境
databricks bundle deploy --target prod
```

## 快速參考 (Quick Reference)

| 概念 | 詳細資訊 |
|---------|---------|
| **名稱** | SDP = Spark Declarative Pipelines = LDP = Lakeflow Declarative Pipelines = Lakeflow Pipelines (皆可互通) |
| **Python 匯入** | `from pyspark import pipelines as dp` |
| **主要裝飾器** | `@dp.table()`, `@dp.materialized_view()`, `@dp.temporary_view()` |
| **暫存視圖** | `@dp.temporary_view()` 建立管線內暫存視圖 (無 Catalog/Schema, 無 Cluster By)。適用於 AUTO CDC 前的中介邏輯，或當視圖需要多次參考但不需持久化時。 |
| **取代** | 透過 `import dlt` 使用的 Delta Live Tables (DLT) |
| **基於** | Apache Spark 4.1+ (Databricks 的現代化資料管線框架) |
| **文件** | https://docs.databricks.com/aws/en/ldp/developer/python-dev |

---

## 詳細指南 (Detailed Guides)

**攝取模式 (Ingestion patterns)**: 規劃如何將新資料獲取至 Lakeflow 管線時，請使用 [1-ingestion-patterns.md](1-ingestion-patterns.md) — 涵蓋檔案格式、批次/串流選項，以及增量與全量載入的技巧。(關鍵字: Auto Loader, Kafka, Event Hub, Kinesis, file formats)

**串流管線模式 (Streaming pipeline patterns)**: 參見 [2-streaming-patterns.md](2-streaming-patterns.md) 以設計具備串流資料來源、變更資料偵測、觸發器與視窗功能的管線。(關鍵字: deduplication, windowing, stateful operations, joins)

**SCD 查詢模式 (SCD query patterns)**: 參見 [3-scd-query-patterns.md](3-scd-query-patterns.md) 以查詢緩慢變更維度 (SCD) Type 2 歷史資料表，包括當前狀態查詢、時間點分析、時序關聯與變更追蹤。(關鍵字: SCD Type 2 history tables, temporal joins, querying historical data)

**效能調校 (Performance tuning)**: 使用 [4-performance-tuning.md](4-performance-tuning.md) 以透過 Liquid Clustering、狀態管理與高效能串流工作負載的最佳實踐來優化管線。(關鍵字: Liquid Clustering, optimization, state management)

**Python API 參考**: 參見 [5-python-api.md](5-python-api.md) 了解現代化 `pyspark.pipelines` (dp) API 參考與從舊版 `dlt` API 模式遷移的資訊。(關鍵字: dp API, dlt API comparison)

**DLT 遷移**: 將現有 Delta Live Tables (DLT) 管線遷移至 Spark Declarative Pipelines (SDP) 時，請使用 [6-dlt-migration.md](6-dlt-migration.md)。(關鍵字: migrating DLT pipelines to SDP)

**進階設定 (Advanced configuration)**: 參見 [7-advanced-configuration.md](7-advanced-configuration.md) 了解進階管線設定，包括開發模式、持續執行、通知、Python 相依性與自訂叢集設定。(關鍵字: extra_settings parameter reference, examples)

**專案初始化**: 使用 [8-project-initialization.md](8-project-initialization.md) 透過 `databricks pipelines init`、Asset Bundles、多環境部署與語言偵測邏輯來設定新管線專案。(關鍵字: databricks pipelines init, Asset Bundles, language detection, migration guides)

**AUTO CDC 模式**: 使用 [9-auto_cdc.md](9-auto_cdc.md) 實作 AUTO CDC 的變更資料擷取，包括用於追蹤變更與去重的緩慢變更維度 (SCD Type 1 與 Type 2)。(關鍵字: AUTO CDC, Slow Changing Dimension, SCD, SCD Type 1, SCD Type 2, change data capture, deduplication)

---

## 工作流程 (Workflow)

1. 決定任務類型:

   **設定新專案?** → 先閱讀 [8-project-initialization.md](8-project-initialization.md)
   **建立新管線?** → 閱讀 [1-ingestion-patterns.md](1-ingestion-patterns.md)
   **建立串流資料表?** → 閱讀 [2-streaming-patterns.md](2-streaming-patterns.md)
   **查詢 SCD 歷史資料表?** → 閱讀 [3-scd-query-patterns.md](3-scd-query-patterns.md)
   **實作 AUTO CDC 或 SCD?** → 閱讀 [9-auto_cdc.md](9-auto_cdc.md)
   **效能問題?** → 閱讀 [4-performance-tuning.md](4-performance-tuning.md)
   **使用 Python API?** → 閱讀 [5-python-api.md](5-python-api.md)
   **從 DLT 遷移?** → 閱讀 [6-dlt-migration.md](6-dlt-migration.md)
   **進階設定?** → 閱讀 [7-advanced-configuration.md](7-advanced-configuration.md)
   **驗證?** → 閱讀 [validation-checklist.md](validation-checklist.md)

2. 遵循相關指南中的說明

3. 對下一個任務類型重複步驟

---

## 官方文件

- **[Lakeflow Spark Declarative Pipelines Overview](https://docs.databricks.com/aws/en/ldp/)** - 主要文件中心
- **[SQL Language Reference](https://docs.databricks.com/aws/en/ldp/developer/sql-dev)** - 串流資料表與物化視圖的 SQL 語法
- **[Python Language Reference](https://docs.databricks.com/aws/en/ldp/developer/python-ref)** - `pyspark.pipelines` API
- **[Loading Data](https://docs.databricks.com/aws/en/ldp/load)** - Auto Loader, Kafka, Kinesis 攝取
- **[Change Data Capture (CDC)](https://docs.databricks.com/aws/en/ldp/cdc)** - AUTO CDC, SCD Type 1/2

### 獎章架構模式 (Medallion Architecture Pattern)

  **Bronze Layer (原始層)**
  - 以原始格式從來源攝取原始資料
  - 最小化轉換 (僅附加，增加如 `_ingested_at`, `_source_file` 等中繼資料)
  - 保留資料血緣的單一真實來源

  **Silver Layer (驗證層)**
  - 已清理與驗證的資料。
  - 可能會在此處使用 auto_cdc 進行去重，但若可能，通常會等到最後一步再使用 auto_cdc。
  - 應用業務邏輯 (型別轉換、品質檢查、過濾無效記錄)
  - 關鍵業務實體的企業視圖
  - 支援自助式分析與 ML

  **Gold Layer (業務就緒層)**
  - 聚合、反正規化、特定專案的資料表
  - 針對取用進行優化 (報表、儀表板、BI 工具)
  - 較少的 Joins，讀取優化的資料模型
  - Kimball 星狀綱要資料表 - dim_<entity_name>, fact_<entity_name>
  - 去重通常在此處透過緩慢變更維度 (SCD) 使用 auto_cdc 進行。有時這會在上游 Silver 層發生，例如當關聯多個資料表或業務使用者計畫從 Silver 層查詢資料表時。

  **典型流程 (可能有所不同)**
  Bronze: read_files() 或 spark.readStream.format("cloudFiles") → streaming table
  Silver: read bronze → filter/clean/validate → streaming table
  Gold: read silver → aggregate/denormalize → auto_cdc 或 materialized view

  來源:
  - https://www.databricks.com/glossary/medallion-architecture
  - https://docs.databricks.com/aws/en/lakehouse/medallion
  - https://www.databricks.com/blog/2022/06/24/data-warehousing-modeling-techniques-and-their-implementation-on-the-databricks-lakehouse-platform.html
  
**對於獎章架構** (bronze/silver/gold)，兩種方法皆可行：
- **扁平式命名** (範本預設): `bronze_*.sql`, `silver_*.sql`, `gold_*.sql`
- **子目錄**: `bronze/orders.sql`, `silver/cleaned.sql`, `gold/summary.sql`

兩者皆適用 `transformations/**` Glob 模式。請根據偏好選擇。

請參閱 **[8-project-initialization.md](8-project-initialization.md)** 以獲取有關 Bundle 初始化、遷移與故障排除的完整詳細資訊。

---

## 一般 SDP 開發指南

### 步驟 1: 在本地撰寫管線檔案

在本地資料夾建立 `.sql` 或 `.py` 檔案：

```
my_pipeline/
├── bronze/
│   ├── ingest_orders.sql       # SQL (多數情況下的預設值)
│   └── ingest_events.py        # Python (用於複雜邏輯)
├── silver/
│   └── clean_orders.sql
└── gold/
    └── daily_summary.sql
```

**SQL 範例** (`bronze/ingest_orders.sql`):
```sql
CREATE OR REFRESH STREAMING TABLE bronze_orders
CLUSTER BY (order_date)
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM read_files(
  '/Volumes/catalog/schema/raw/orders/',
  format => 'json',
  schemaHints => 'order_id STRING, customer_id STRING, amount DECIMAL(10,2), order_date DATE'
);
```

**Python 範例** (`bronze/ingest_events.py`):
```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col, current_timestamp

# 從管線設定取得 Schema 位置
schema_location_base = spark.conf.get("schema_location_base")

@dp.table(name="bronze_events", cluster_by=["event_date"])
def bronze_events():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{schema_location_base}/bronze_events")
        .load("/Volumes/catalog/schema/raw/events/")
        .withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_file", col("_metadata.file_path"))
    )
```

**Python 管線重要事項**: 當使用 `spark.readStream.format("cloudFiles")` 進行雲端儲存攝取，且使用 Schema 推斷 (未指定 Schema) 時，您 **必須指定 schema location**。

**務必詢問使用者** 要將 Auto Loader Schema Metadata 儲存在哪裡。推薦：
```
/Volumes/{catalog}/{schema}/{pipeline_name}_metadata/schemas
```

範例: `/Volumes/my_catalog/pipeline_metadata/orders_pipeline_metadata/schemas`

**絕不要使用來源資料 Volume** - 這會導致權限衝突。Schema 位置應在管線設定中配置，並透過 `spark.conf.get("schema_location_base")` 存取。

**語言選擇:**

**關鍵規則**: 若使用者在請求中明確提及 "Python" (例如 "Python Spark Declarative Pipeline", "Python SDP", "use Python")，**務必使用 Python，無需詢問**。SQL 亦同 - 若他們說 "SQL pipeline"，就使用 SQL。

- **明確語言請求**: 使用者說 "Python" → 使用 Python。使用者說 "SQL" → 使用 SQL。**不要要求澄清。**
- **自動偵測** (僅當未明確提及語言時):
  - **SQL 指標**: "sql files", "simple transformations", "aggregations", "materialized view", "CREATE OR REFRESH"
  - **Python 指標**: ".py files", "UDF", "complex logic", "ML inference", "external API", "@dp.table", "pandas", "decorator"
- **要求澄清** 僅當語言意圖真的很模糊 (無明確提及，訊號混合)
- **預設為 SQL** 僅當模糊且無 Python 指標時

參見 **[8-project-initialization.md](8-project-initialization.md)** 了解詳細的語言偵測邏輯。

## 選項 1: 搭配 DABs 的管線
使用 Asset Bundles 與 Pipeline CLI。
參閱 [快速入門](#quick-start) 與 **[8-project-initialization.md](8-project-initialization.md)** 了解完整詳細資訊。

## 選項 2: 手動工作流程 (進階)

對於快速原型製作、實驗，或當您偏好直接控制而不使用 Asset Bundles 時，使用搭配 MCP 工具的手動工作流程。

使用 MCP 工具來建立、執行並迭代 **Serverless SDP 管線**。**主要工具是 `create_or_update_pipeline`**，它處理整個生命週期。

**重要: 始終建立 Serverless 管線 (預設)。** 僅當使用者明確要求 Classic、Pro、Advanced Compute 或需要 R 語言、Spark RDD API 或 JAR 函式庫時才使用 Classic Cluster。

參見 **[10-mcp-approach.md](10-mcp-approach.md)** 了解詳細指南。

## 最佳實踐 (2026)

### 專案結構
- **新專案預設使用 `databricks pipelines init`** (建立 Asset Bundle)
- **使用 Asset Bundles** 進行多環境部署 (dev/staging/prod)
- **僅用於快速原型或遺留遷移** 使用手動結構
- **獎章架構**: 兩種方法適用於 Asset Bundles:
  - **扁平式結構** (範本預設): `transformations/` 中的 `bronze_*.sql`, `silver_*.sql`, `gold_*.sql`
  - **子目錄**: `transformations/bronze/`, `transformations/silver/`, `transformations/gold/`
  - 兩者皆適用 `transformations/**` Glob 模式 - 根據團隊偏好選擇
- 參見 **[8-project-initialization.md](8-project-initialization.md)** 了解專案設定細節

### 極簡管線設定要點
- 在管線設定中定義參數，並在程式碼中以 `spark.conf.get("key")` 存取。
- 在 Databricks Asset Bundles 中，將這些設定在 `resources.pipelines.<pipeline>.configuration` 下；使用 `databricks bundle validate` 驗證。

### 現代化預設值
- **CLUSTER BY** (Liquid Clustering)，而非 PARTITION BY - 參見 [4-performance-tuning.md](4-performance-tuning.md)
- **Raw `.sql`/`.py` 檔案**，而非 Notebooks
- **僅限 Serverless Compute** - 除非明確要求，否則不要使用 Classic Clusters
- **Unity Catalog** (Serverless 必需)
- **read_files()** 當使用 SQL 進行雲端儲存攝取時 - 參見 [1-ingestion-patterns.md](1-ingestion-patterns.md)

### 多 Schema 模式 (Multi-Schema Patterns)

**預設: 每個管線單一目標 Schema。** 每個管線有一個目標 `catalog` 與 `schema`，所有資料表都寫入其中。

#### 選項 1: 單一管線，單一 Schema 搭配前綴 (推薦)

使用一個 Schema 並以資料表名稱前綴區分層級：

```python
# 所有資料表寫入至: catalog.schema.bronze_*, silver_*, gold_*
@dp.table(name="bronze_orders")  # → catalog.schema.bronze_orders
@dp.table(name="silver_orders")  # → catalog.schema.silver_orders
@dp.table(name="gold_summary")   # → catalog.schema.gold_summary
```

**優點:**
- 設定較簡單 (單一管線)
- 所有資料表在一個 Schema 中，易於發現

#### 選項 2:
使用變數為不同步驟指定獨立的 Catalog 及/或 Schema。

以下是 Python SDP 範例，透過 `spark.conf.get` 從管線配置獲取變數，並對 Bronze 層使用預設 Catalog/Schema。

##### 相同 Catalog，獨立 Schema；Bronze 使用管線預設值
- 設定管線的預設 Catalog 與預設 Schema 為 Bronze 層 (例如 catalog=my_catalog, schema=bronze)。當您在程式碼中省略 catalog/schema 時，讀取/寫入會使用這些預設值。
- 為其他 Schema 及任何來源 Schema/Path 使用管線參數，在程式碼中以 `spark.conf.get(...)` 檢索。

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col

# 從管線設定參數獲取變數
silver_schema = spark.conf.get("silver_schema")  # 例如 "silver"
gold_schema   = spark.conf.get("gold_schema")    # 例如 "gold"
landing_schema = spark.conf.get("landing_schema")  # 例如 "landing"

# Bronze → 使用預設 catalog/schema (在管線設定中設為 bronze)
@dp.table(name="orders_bronze")
def orders_bronze():
    # 從同一個預設 catalog 中的另一個 schema 讀取
    return spark.readStream.table(f"{landing_schema}.orders_raw")

# Silver → 相同 catalog，schema 來自參數
@dp.table(name=f"{silver_schema}.orders_clean")
def orders_clean():
    return (spark.read.table("orders_bronze")  # 未限定 = 預設 catalog/schema
            .filter(col("order_id").isNotNull()))

# Gold → 相同 catalog，schema 來自參數
@dp.materialized_view(name=f"{gold_schema}.orders_by_date")
def orders_by_date():
    return (spark.read.table(f"{silver_schema}.orders_clean")
            .groupBy("order_date")
            .count().withColumnRenamed("count", "order_count"))
```
- 對 Bronze 使用未限定名稱確保它落在管線的預設 Catalog/Schema；Silver/Gold 則在同一 Catalog 中明確限定 Schema。

---

##### 每層自訂 Catalog/Schema；Bronze 仍使用管線預設值
- 保持 Bronze 在管線預設值 (預設 Catalog/Schema 設為您的 Bronze 層)。對於 Silver/Gold，使用來自管線設定的 Catalog 與 Schema 變數的完全限定名稱。

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col

# 從管線設定參數獲取變數
silver_catalog = spark.conf.get("silver_catalog")  # 例如 "my_catalog"
silver_schema  = spark.conf.get("silver_schema")   # 例如 "silver"
gold_catalog   = spark.conf.get("gold_catalog")    # 例如 "my_catalog"
gold_schema    = spark.conf.get("gold_schema")     # 例如 "gold"
landing_catalog = spark.conf.get("landing_catalog")  # 可選，若來源在另一個 catalog
landing_schema  = spark.conf.get("landing_schema")

# Bronze → 使用預設 catalog/schema (設為 bronze)
@dp.table(name="orders_bronze")
def orders_bronze():
    # 若來源在指定的 catalog/schema 中:
    return spark.readStream.table(f"{landing_catalog}.{landing_schema}.orders_raw")

# Silver → 透過參數自訂 catalog + schema
@dp.table(name=f"{silver_catalog}.{silver_schema}.orders_clean")
def orders_clean():
    # 讀取 bronze (使用未限定名稱作為預設值)，或根據偏好使用完全限定名稱
    return (spark.read.table("orders_bronze")
            .filter(col("order_id").isNotNull()))

# Gold → 透過參數自訂 catalog + schema
@dp.materialized_view(name=f"{gold_catalog}.{gold_schema}.orders_by_date}")
def orders_by_date():
    return (spark.read.table(f"{silver_catalog}.{silver_schema}.orders_clean")
            .groupBy("order_date")
            .count().withColumnRenamed("count", "order_count"))
```
- 裝飾器 name 參數中的多部名稱讓您能在單一管線中發佈至明確的 catalog.schema 目標。
- 未限定的讀取/寫入使用管線預設值；當跨越 Catalog 或需要明確命名空間控制時使用完全限定名稱。

---

**注意:** `@dp.table()` 裝飾器目前不支援分開的 `schema=` 或 `catalog=` 參數。table 參數是一個字串，包含 catalog.schema.table_name，或者省略 catalog 及/或 schema 以使用管線設定的預設目標 schema。

### 在 Python 中讀取資料表

**現代化 SDP 最佳實踐:**
- 批次讀取使用 `spark.read.table()`
- 串流讀取使用 `spark.readStream.table()`
- 不要使用 `dp.read()` 或 `dp.read_stream()` (舊語法，不再有文件)
- 不要使用 `dlt.read()` 或 `dlt.read_stream()` (舊版 DLT API)

**關鍵點:** SDP 會從標準 Spark DataFrame 操作中自動追蹤資料表依賴關係。不需要特殊的 Read API。

#### 三層識別符解析

SDP 支援三種層級的資料表名稱限定：

| 層級 | 語法 | 何時使用 |
|-------|--------|-------------|
| **未限定 (Unqualified)** | `spark.read.table("my_table")` | 讀取同一管線目標 Catalog/Schema 中的資料表 (推薦) |
| **部分限定 (Partially-qualified)** | `spark.read.table("other_schema.my_table")` | 從同一 Catalog 的不同 Schema 讀取 |
| **完全限定 (Fully-qualified)** | `spark.read.table("other_catalog.other_schema.my_table")` | 從外部 Catalogs/Schemas 讀取 |

#### 選項 1: 未限定名稱 (Pipeline 資料表推薦)

**同一管線內資料表的最佳實踐。** SDP 將未限定名稱解析為管線設定的目標 Catalog 與 Schema。這使程式碼在環境間 (dev/prod) 具備可移植性。

```python
@dp.table(name="silver_clean")
def silver_clean():
    # 從管線的目標 catalog/schema 讀取 (例如 dev_catalog.dev_schema.bronze_raw)
    return (
        spark.read.table("bronze_raw")
        .filter(F.col("valid") == True)
    )

@dp.table(name="silver_events")
def silver_events():
    # 從同一管線的 bronze_events 資料表進行串流讀取
    return (
        spark.readStream.table("bronze_events")
        .withColumn("processed_at", F.current_timestamp())
    )
```

#### 選項 2: 管線參數 (用於外部來源)

**使用 `spark.conf.get()` 將外部 Catalog/Schema 參考參數化。** 在管線設定中定義參數，然後在模組層級參考它們。

```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F

# 在模組層級獲取參數值 (管線啟動時評估一次)
source_catalog = spark.conf.get("source_catalog")
source_schema = spark.conf.get("source_schema", "sales")  # 預設值

@dp.table(name="transaction_summary")
def transaction_summary():
    return (
        spark.read.table(f"{source_catalog}.{source_schema}.transactions")
        .groupBy("account_id")
        .agg(
            F.count("txn_id").alias("txn_count"),
            F.sum("txn_amount").alias("account_revenue")
        )
    )
```

**在管線設定中配置參數:**
- **Asset Bundles**: 新增至 `pipeline.yml` 的 `configuration:` 下
- **Manual/MCP**: 透過 `extra_settings.configuration` dict 傳遞

```yaml
# In resources/my_pipeline.pipeline.yml
configuration:
  source_catalog: "shared_catalog"
  source_schema: "sales"
```

#### 選項 3: 完全限定名稱 (用於固定外部參考)

當參考不隨環境變化的特定外部資料表時使用：

```python
@dp.table(name="enriched_orders")
def enriched_orders():
    # 管線內部資料表 (未限定)
    orders = spark.read.table("bronze_orders")

    # 外部參考資料表 (完全限定)
    products = spark.read.table("shared_catalog.reference.products")

    return orders.join(products, "product_id")
```

#### 選擇正確方法

| 情境 | 推薦方法 |
|----------|---------------------|
| 讀取在同一管線中建立的資料表 | **未限定名稱** - 可移植，使用目標 Catalog/Schema |
| 讀取隨環境變化的外部來源 | **管線參數** - 每次部署可設定 |
| 讀取具固定位置的共享/參考資料表 | **完全限定名稱** - 明確且清晰 |
| 混合管線 (部分內部，部分外部) | **結合方法** - 內部用未限定，外部用參數 |

---

## 常見問題 (Common Issues)

| 問題 | 解決方案 |
|-------|----------|
| **輸出資料表為空** | 使用 `get_table_details` 驗證，檢查上游來源 |
| **Pipeline 卡在 INITIALIZING** | 對於 Serverless 為正常現象，請等待幾分鐘 |
| **"Column not found"** | Check `schemaHints` match actual data |
| **串流讀取失敗** | 對於串流資料表中的檔案攝取，您必須在 `read_files` 使用 `STREAM` 關鍵字：`FROM STREAM read_files(...)`。資料表串流使用 `FROM stream(table)`。參見 [read_files — Usage in streaming tables](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files#usage-in-streaming-tables). |
| **執行期間逾時** | 增加 `timeout`，或使用 `wait_for_completion=False` 並透過 `get_update` 輪詢 |
| **MV 不重新整理** | 在來源資料表啟用 Row Tracking |
| **SCD2: query column not found** | Lakeflow 使用 `__START_AT` 與 `__END_AT` (雙底線)，而非 `START_AT`/`END_AT`。對目前資料列使用 `WHERE __END_AT IS NULL`。參見 [3-scd-patterns.md](3-scd-patterns.md). |
| **AUTO CDC parse error at APPLY/SEQUENCE** | 將 `APPLY AS DELETE WHEN` 放在 `SEQUENCE BY` **之前**。在 `COLUMNS * EXCEPT (...)` 中僅列出來源中存在的欄位 (除非 Bronze 使用 Rescue Data，否則省略 `_rescued_data`)。若 `TRACK HISTORY ON *` 導致 "end of input" 錯誤則省略；預設即為相同效果。參見 [2-streaming-patterns.md](2-streaming-patterns.md). |
| **"Cannot create streaming table from batch query"** | 在串流資料表查詢中，使用 `FROM STREAM read_files(...)` 讓 `read_files` 利用 Auto Loader；單獨使用 `FROM read_files(...)` 是批次處理。參見 [1-ingestion-patterns.md](1-ingestion-patterns.md) 與 [read_files — Usage in streaming tables](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files#usage-in-streaming-tables). |

**關於詳細錯誤**，來自 `create_or_update_pipeline` 的 `result["message"]` 包含建議的下一步。使用 `get_pipeline_events(pipeline_id=...)` 獲取完整 Stack Traces。

---

## 進階管線設定

關於進階設定選項 (開發模式、持續管線、自訂叢集、通知、Python 相依性等)，參見 **[7-advanced-configuration.md](7-advanced-configuration.md)**。

---

## 平台限制 (Platform Constraints)

### Serverless 管線需求 (預設)
| 需求 | 詳細資訊 |
|-------------|---------|
| **Unity Catalog** | 必要 - Serverless 管線一律使用 UC |
| **Workspace Region** | 必須在啟用 Serverless 的區域 |
| **Serverless Terms** | 必須接受 Serverless 使用條款 |
| **CDC Features** | 需要 Serverless (或具備 Classic Clusters 的 Pro/Advanced 版本) |

### Serverless 限制 (何時需要 Classic Clusters)
| 限制 | 變通方案 |
|------------|-----------|
| **R 語言** | 不支援 - 若需要請使用 Classic Clusters |
| **Spark RDD APIs** | 不支援 - 若需要請使用 Classic Clusters |
| **JAR 函式庫** | 不支援 - 若需要請使用 Classic Clusters |
| **Maven 座標** | 不支援 - 若需要請使用 Classic Clusters |
| **DBFS Root 存取** | 受限 - 必須使用 Unity Catalog 指定位置 |
| **Global Temp Views** | 不支援 |

### 一般限制
| 限制 | 詳細資訊 |
|------------|---------|
| **Schema Evolution** | 對於不相容的變更，串流資料表需要完全重新整理 (Full Refresh) |
| **SQL 限制** | 不支援 PIVOT 子句 |
| **Sinks** | 僅限 Python，僅限串流，僅限附加流程 (Append Flows) |

**預設為 Serverless**，除非使用者明確要求 R、RDD API 或 JAR 函式庫。
