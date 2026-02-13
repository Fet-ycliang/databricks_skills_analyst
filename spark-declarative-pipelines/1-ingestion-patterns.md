# SDP 的資料攝取模式 (Data Ingestion Patterns)

涵蓋 Spark Declarative Pipelines 的資料攝取模式，包括用於雲端儲存的 Auto Loader 以及 Kafka 與 Event Hub 等串流來源。

**語言支援**: SQL (主要)，Python 透過現代化 `pyspark.pipelines` API。參見 [5-python-api.md](5-python-api.md) 了解 Python 語法。

---

## Auto Loader (Cloud Files)

Auto Loader 會在雲端儲存中的新資料檔案到達時增量處理它們。在串流資料表查詢中，您 **必須在 `read_files` 使用 `STREAM` 關鍵字**；`read_files` 隨後會利用 Auto Loader。參見 [read_files — Usage in streaming tables](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files#usage-in-streaming-tables)。

### 基本模式

```sql
CREATE OR REPLACE STREAMING TABLE bronze_orders AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS source_file,
  _metadata.file_modification_time AS file_timestamp
FROM STREAM read_files(
  '/mnt/raw/orders/',
  format => 'json',
  schemaHints => 'order_id STRING, amount DECIMAL(10,2)'
);
```

### Bronze 餵入 AUTO CDC

若 Bronze 資料表餵入下游 **AUTO CDC** 流程 (例如 `FROM stream(bronze_orders_cdc)`)，請使用 **`FROM STREAM read_files(...)`** 讓來源成為串流。否則您可能會得到：*"Cannot create a streaming table append once flow from a batch query."* 要求同上：在串流資料表查詢中，您必須在 `read_files` 使用 `STREAM` 關鍵字。

```sql
CREATE OR REPLACE STREAMING TABLE bronze_orders_cdc AS
SELECT ...,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM STREAM read_files(
  '/Volumes/catalog/schema/raw_orders_cdc',
  format => 'parquet',
  schemaHints => '...'
);
```

### Schema 演變 (Schema Evolution)

```sql
CREATE OR REPLACE STREAMING TABLE bronze_customers AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/mnt/raw/customers/',
  format => 'json',
  schemaHints => 'customer_id STRING, email STRING',
  mode => 'PERMISSIVE'  -- 優雅地處理 Schema 變更
);
```

### 檔案格式

**JSON**:
```sql
FROM read_files(
  's3://bucket/data/',
  format => 'json',
  schemaHints => 'id STRING, timestamp TIMESTAMP'
)
```

**CSV**:
```sql
FROM read_files(
  '/mnt/raw/data/',
  format => 'csv',
  schemaHints => 'id STRING, name STRING, amount DECIMAL(10,2)',
  header => true,
  delimiter => ','
)
```

**Parquet** (Schema 自動推斷):
```sql
FROM read_files(
  'abfss://container@storage.dfs.core.windows.net/data/',
  format => 'parquet'
)
```

**Avro**:
```sql
FROM read_files(
  '/mnt/raw/events/',
  format => 'avro',
  schemaHints => 'event_id STRING, event_time TIMESTAMP'
)
```

### Schema 推斷

**明確 Hints** (生產環境推薦):
```sql
FROM read_files(
  '/mnt/raw/sales/',
  format => 'json',
  schemaHints => 'sale_id STRING, customer_id STRING, amount DECIMAL(10,2), sale_date DATE'
)
```

**部分 Hints** (推斷剩餘欄位):
```sql
FROM read_files(
  '/mnt/raw/data/',
  format => 'json',
  schemaHints => 'id STRING, critical_field DECIMAL(10,2)'  -- 其他欄位自動推斷
)
```

將此新增至 `resources/*_etl.pipeline.yml` 中的管線設定：
```yaml
configuration:
  bronze_schema: ${var.bronze_schema}
  silver_schema: ${var.silver_schema}
  gold_schema: ${var.gold_schema}
  schema_location_base: ${var.schema_location_base}
```

並在 `databricks.yml` 中定義變數：
```yaml
variables:
  catalog:
    description: The catalog to use
  bronze_schema:
    description: The bronze schema to use
  silver_schema:
    description: The silver schema to use
  gold_schema:
    description: The gold schema to use
  schema_location_base:
    description: Base path for Auto Loader schema metadata

targets:
  dev:
    variables:
      catalog: my_catalog
      bronze_schema: bronze_dev
      silver_schema: silver_dev
      gold_schema: gold_dev
      schema_location_base: /Volumes/my_catalog/pipeline_metadata/my_pipeline_metadata/schemas

  prod:
    variables:
      catalog: my_catalog
      bronze_schema: bronze
      silver_schema: silver
      gold_schema: gold
      schema_location_base: /Volumes/my_catalog/pipeline_metadata/my_pipeline_metadata/schemas
```

接著在 Python 程式碼中存取這些變數：
```python
bronze_schema = spark.conf.get("bronze_schema")
silver_schema = spark.conf.get("silver_schema")
gold_schema = spark.conf.get("gold_schema")
schema_location_base = spark.conf.get("schema_location_base")
```

### Rescue Data 與隔離區 (Quarantine)

使用 `_rescued_data` 處理格式錯誤的記錄：

```sql
-- 標記有解析錯誤的記錄
CREATE OR REPLACE STREAMING TABLE bronze_events AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  CASE WHEN _rescued_data IS NOT NULL THEN TRUE ELSE FALSE END AS has_parsing_errors
FROM read_files(
  '/mnt/raw/events/',
  format => 'json',
  schemaHints => 'event_id STRING, event_time TIMESTAMP'
);

-- 隔離以供調查
CREATE OR REPLACE STREAMING TABLE bronze_events_quarantine AS
SELECT * FROM STREAM bronze_events WHERE _rescued_data IS NOT NULL;

-- 清理資料以供下游使用
CREATE OR REPLACE STREAMING TABLE silver_events_clean AS
SELECT * FROM STREAM bronze_events WHERE _rescued_data IS NULL;
```

---

## 串流來源 (Kafka, Event Hub, Kinesis)

### Kafka 來源

```sql
CREATE OR REPLACE STREAMING TABLE bronze_kafka_events AS
SELECT
  CAST(key AS STRING) AS event_key,
  CAST(value AS STRING) AS event_value,
  topic,
  partition,
  offset,
  timestamp AS kafka_timestamp,
  current_timestamp() AS _ingested_at
FROM read_stream(
  format => 'kafka',
  kafka.bootstrap.servers => '${kafka_brokers}',
  subscribe => 'events-topic',
  startingOffsets => 'latest',  -- 或 'earliest'
  kafka.security.protocol => 'SASL_SSL',
  kafka.sasl.mechanism => 'PLAIN',
  kafka.sasl.jaas.config => 'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="${kafka_username}" password="${kafka_password}";'
);
```

### 多主題 Kafka

```sql
FROM read_stream(
  format => 'kafka',
  kafka.bootstrap.servers => '${kafka_brokers}',
  subscribe => 'topic1,topic2,topic3',
  startingOffsets => 'latest'
)
```

### Azure Event Hub

```sql
CREATE OR REPLACE STREAMING TABLE bronze_eventhub_events AS
SELECT
  CAST(body AS STRING) AS event_body,
  enqueuedTime AS event_time,
  offset,
  sequenceNumber,
  current_timestamp() AS _ingested_at
FROM read_stream(
  format => 'eventhubs',
  eventhubs.connectionString => '${eventhub_connection_string}',
  eventhubs.consumerGroup => '${consumer_group}',
  startingPosition => 'latest'
);
```

### AWS Kinesis

```sql
CREATE OR REPLACE STREAMING TABLE bronze_kinesis_events AS
SELECT
  CAST(data AS STRING) AS event_data,
  partitionKey,
  sequenceNumber,
  approximateArrivalTimestamp AS arrival_time,
  current_timestamp() AS _ingested_at
FROM read_stream(
  format => 'kinesis',
  kinesis.streamName => '${stream_name}',
  kinesis.region => '${aws_region}',
  kinesis.startingPosition => 'LATEST'
);
```

### 從串流來源解析 JSON

```sql
-- 從 Kafka value 解析 JSON
CREATE OR REPLACE STREAMING TABLE silver_kafka_parsed AS
SELECT
  from_json(
    event_value,
    'event_id STRING, event_type STRING, user_id STRING, timestamp TIMESTAMP, properties MAP<STRING, STRING>'
  ) AS event_data,
  kafka_timestamp,
  _ingested_at
FROM STREAM bronze_kafka_events;

-- 扁平化已解析的 JSON
CREATE OR REPLACE STREAMING TABLE silver_kafka_flattened AS
SELECT
  event_data.event_id,
  event_data.event_type,
  event_data.user_id,
  event_data.timestamp AS event_timestamp,
  event_data.properties,
  kafka_timestamp,
  _ingested_at
FROM STREAM silver_kafka_parsed;
```

---

## 驗證 (Authentication)

### 使用 Databricks Secrets

**Kafka**:
```sql
kafka.sasl.jaas.config => 'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="{{secrets/kafka/username}}" password="{{secrets/kafka/password}}";'
```

**Event Hub**:
```sql
eventhubs.connectionString => '{{secrets/eventhub/connection-string}}'
```

### 使用管線變數

在 SQL 中參考變數：
```sql
kafka.bootstrap.servers => '${kafka_brokers}'
```

在管線設定中定義：
```yaml
variables:
  kafka_brokers:
    default: "broker1:9092,broker2:9092"
```

---

## 關鍵模式

### 1. 始終加入攝取時間戳記

```sql
SELECT
  *,
  current_timestamp() AS _ingested_at  -- 追蹤資料進系統的時間
FROM read_files(...)
```

### 2. 包含檔案 Metadata 以供除錯

```sql
SELECT
  *,
  _metadata.file_path AS source_file,
  _metadata.file_modification_time AS file_timestamp,
  _metadata.file_size AS file_size
FROM read_files(...)
```

### 3. 在生產環境使用 Schema Hints

```sql
-- ✅ 明確 Schema 防止意外
FROM read_files(
  '/mnt/data/',
  format => 'json',
  schemaHints => 'id STRING, amount DECIMAL(10,2), date DATE'
)

-- ❌ 完全推斷的 Schema 可能會漂移
FROM read_files('/mnt/data/', format => 'json')
```

### 4. 處理 Rescue Data 以確保品質

```sql
-- 將錯誤路由至隔離區，清理後的資料至下游
CREATE OR REPLACE STREAMING TABLE bronze_data_quarantine AS
SELECT * FROM STREAM bronze_data WHERE has_errors;

CREATE OR REPLACE STREAMING TABLE silver_data AS
SELECT * FROM STREAM bronze_data WHERE NOT has_errors;
```

### 5. 起始位置

**開發**: `startingOffsets => 'latest'` (僅新資料)
**回填 (Backfill)**: `startingOffsets => 'earliest'` (所有可用資料)
**復原**: Checkpoints 自動處理

---

## 常見問題

| 問題 | 解決方案 |
|-------|----------|
| 檔案未被讀取 | 驗證格式是否符合檔案且路徑正確 |
| Schema 演變導致中斷 | 使用 `mode => 'PERMISSIVE'` 並監控 `_rescued_data` |
| Kafka Lag 增加 | 檢查下游瓶頸，增加平行度 |
| 重複事件 | 在 Silver 層實作去重 (參見 [2-streaming-patterns.md](2-streaming-patterns.md)) |
| 解析錯誤 | 使用 Rescue Data 模式隔離格式錯誤的記錄 |

---

## Python API 範例

對於 Python，使用現代化 `pyspark.pipelines` API。完整指南參見 [5-python-api.md](5-python-api.md)。

**Python 重要事項**: 當使用 `spark.readStream.format("cloudFiles")` 進行雲端儲存攝取時，您 **必須指定 `cloudFiles.schemaLocation`** 用於 Auto Loader Schema Metadata。

### Schema 位置最佳實踐 (僅限 Python)

**絕不要使用來源資料 Volume 儲存 Schema** - 這會導致權限衝突並汙染您的原始資料。

#### 提示使用者輸入 Schema 位置

當建立使用 Auto Loader 的 Python 管線時，**務必詢問使用者** 要將 Schema Metadata 儲存在哪裡：

**推薦模式:**
```
/Volumes/{catalog}/{schema}/{pipeline_name}_metadata/schemas/{table_name}
```

**範例提示:**
```
"請問您想將 Auto Loader Schema Metadata 儲存在哪裡？

我推薦：
  /Volumes/my_catalog/pipeline_metadata/orders_pipeline_metadata/schemas/

此路徑可以：
- 保持來源資料乾淨
- 防止權限問題
- 讓管線狀態易於管理
- 可針對每個環境參數化 (dev/prod)

您可能需要先建立 volume 'pipeline_metadata' (如果尚未存在)。

您要使用這個路徑嗎？"
```

### Auto Loader (Python)

```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F

# 從管線設定獲取 Schema 位置
# 建議格式: /Volumes/{catalog}/{schema}/{pipeline_name}_metadata/schemas
schema_location_base = spark.conf.get("schema_location_base")

@dp.table(name="bronze_orders", cluster_by=["order_date"])
def bronze_orders():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{schema_location_base}/bronze_orders")
        .option("cloudFiles.inferColumnTypes", "true")
        .load("/Volumes/catalog/schema/raw/orders/")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
    )
```

**管線設定** (`pipeline.yml`):
```yaml
configuration:
  schema_location_base: /Volumes/my_catalog/pipeline_metadata/orders_pipeline_metadata/schemas
```

### Kafka (Python)

```python
@dp.table(name="bronze_kafka_events")
def bronze_kafka_events():
    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", spark.conf.get("kafka_brokers"))
        .option("subscribe", "events-topic")
        .option("startingOffsets", "latest")
        .load()
        .selectExpr(
            "CAST(key AS STRING) AS event_key",
            "CAST(value AS STRING) AS event_value",
            "topic", "partition", "offset",
            "timestamp AS kafka_timestamp"
        )
        .withColumn("_ingested_at", F.current_timestamp())
    )
```

### 隔離區 (Python)

```python
# 從管線設定獲取 Schema 位置
schema_location_base = spark.conf.get("schema_location_base")

@dp.table(name="bronze_events", cluster_by=["ingestion_date"])
def bronze_events():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{schema_location_base}/bronze_events")
        .option("rescuedDataColumn", "_rescued_data")
        .load("/Volumes/catalog/schema/raw/events/")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("ingestion_date", F.current_date())
        .withColumn("_has_parsing_errors",
                    F.when(F.col("_rescued_data").isNotNull(), True)
                    .otherwise(False))
    )

@dp.table(name="bronze_events_quarantine")
def bronze_events_quarantine():
    return (
        spark.read.table("catalog.schema.bronze_events")
        .filter(F.col("_has_parsing_errors") == True)
    )
```
