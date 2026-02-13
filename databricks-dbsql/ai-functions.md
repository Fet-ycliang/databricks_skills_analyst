# AI 函數、http_request、remote_query 和 read_files 參考

Databricks SQL 進階函數的全面參考：內建 AI 函數、HTTP 請求、Lakehouse Federation 遠端查詢和檔案讀取。

---

## 目錄

- [AI 函數概述](#ai-函數概述)
- [ai_query -- 通用 AI 函數](#ai_query----通用-ai-函數)
- [特定任務的 AI 函數](#特定任務的-ai-函數)
  - [ai_gen](#ai_gen)
  - [ai_classify](#ai_classify)
  - [ai_extract](#ai_extract)
  - [ai_analyze_sentiment](#ai_analyze_sentiment)
  - [ai_similarity](#ai_similarity)
  - [ai_summarize](#ai_summarize)
  - [ai_translate](#ai_translate)
  - [ai_fix_grammar](#ai_fix_grammar)
  - [ai_mask](#ai_mask)
- [文件和多模態 AI 函數](#文件和多模態-ai-函數)
  - [ai_parse_document](#ai_parse_document)
- [時間序列 AI 函數](#時間序列-ai-函數)
  - [ai_forecast](#ai_forecast)
- [向量搜尋函數](#向量搜尋函數)
  - [vector_search](#vector_search)
- [http_request 函數](#http_request-函數)
- [remote_query 函數（Lakehouse Federation）](#remote_query-函數lakehouse-federation)
- [read_files 資料表值函數](#read_files-資料表值函數)

---

## AI 函數概述

Databricks AI 函數是內建的 SQL 函數，可直接從 SQL 呼叫最先進的生成式 AI 模型。它們在 Databricks Foundation Model API 上執行，可從 Databricks SQL、notebook、Lakeflow Spark 宣告式管線和工作流程中使用。

**所有 AI 函數的共同需求：**
- 工作區必須位於支援針對批次推論優化的 AI 函數的區域
- 不適用於 Databricks SQL Classic（需要無伺服器 SQL 倉儲）
- Databricks Runtime 15.1+ 用於 notebook；建議使用 15.4 ML LTS 用於批次工作負載
- 模型根據 Apache 2.0 或 LLAMA 3.3 社群授權許可
- 目前針對英文進行調整（底層模型支援多種語言）
- 公開預覽版，符合 HIPAA 規範

**速率限制和計費：**
- AI 函數受 Foundation Model API 速率限制約束
- 計費為 Databricks SQL 運算加上 Foundation Model API 上的權杖使用量
- 在開發期間於查詢中使用 `LIMIT` 以控制成本

---

## ai_query -- 通用 AI 函數

最強大且靈活的 AI 函數。查詢任何服務端點（Foundation Models、外部模型或自訂 ML 模型）以進行即時或批次推論。

### 語法

```sql
-- 基本呼叫
ai_query(endpoint, request)

-- 包含所有選用參數的完整呼叫
ai_query(
  endpoint,
  request,
  returnType          => type_expression,
  failOnError         => boolean,
  modelParameters     => named_struct(...),
  responseFormat      => format_string,
  files               => content_expression
)
```

### 參數

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `endpoint` | STRING | 是 | 同一工作區中的 Foundation Model、外部模型或自訂模型服務端點的名稱 |
| `request` | STRING 或 STRUCT | 是 | 對於 LLM 端點：STRING 提示。對於自訂 ML 端點：單一欄位或符合預期輸入特徵的 STRUCT |
| `returnType` | 表達式 | 否 | 預期的返回類型（DDL 樣式）。在 Runtime 15.2+ 中為選用；在 15.1 及以下版本中為必要 |
| `failOnError` | BOOLEAN | 否 | 預設 `true`。當為 `false` 時，返回帶有 `response` 和 `errorStatus` 欄位的 STRUCT，而不是失敗 |
| `modelParameters` | STRUCT | 否 | 透過 `named_struct()` 的模型參數（Runtime 15.3+） |
| `responseFormat` | STRING | 否 | 控制輸出格式：`'text'`、`'json_object'` 或 DDL/JSON 結構描述字串（Runtime 15.4 LTS+，僅限聊天模型） |
| `files` | 表達式 | 否 | 用於影像處理的多模態檔案輸入（支援 JPEG、PNG） |

### 返回類型

| 情境 | 返回類型 |
|----------|-------------|
| `failOnError => true`（預設） | 符合端點類型或 `returnType` 的解析回應 |
| `failOnError => false` | `STRUCT<result: T, errorMessage: STRING>`，其中 T 是解析的類型 |
| 使用 `responseFormat` | 符合指定結構描述的結構化輸出 |

### 模型參數

```sql
-- 使用 modelParameters 控制生成
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  '用 3 句話解釋量子運算。',
  modelParameters => named_struct(
    'max_tokens', 256,
    'temperature', 0.1,
    'top_p', 0.9
  )
) AS response;
```

常見模型參數：
- `max_tokens`（INT）-- 要生成的最大權杖數
- `temperature`（DOUBLE）-- 隨機性（0.0 = 確定性，2.0 = 最大隨機）
- `top_p`（DOUBLE）-- 核心採樣閾值
- `stop`（ARRAY<STRING>）-- 停止序列

### 使用 responseFormat 的結構化輸出

> **注意：**頂層 `responseFormat` STRUCT 必須恰好包含一個欄位。要返回多個欄位，請將它們包裝在單一外部欄位中。

```sql
-- 強制 JSON 輸出符合結構描述（頂層 STRUCT 必須恰好有一個欄位）
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  '從以下內容提取產品名稱、價格和類別："Sony WH-1000XM5 耳機，$348，電子產品"',
  responseFormat => 'STRUCT<result: STRUCT<product_name: STRING, price: DOUBLE, category: STRING>>'
) AS extracted;
```

### 資料表上的批次推論

```sql
-- 分類資料表中的所有列
SELECT
  review_id,
  review_text,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    CONCAT('將以下評論分類為正面、負面或中性：', review_text),
    responseFormat => 'STRUCT<result: STRUCT<sentiment: STRING, confidence: STRING>>'
  ) AS classification
FROM catalog.schema.product_reviews;
```

### 自訂 ML 模型推論

```sql
-- 查詢自訂 sklearn/MLflow 模型
SELECT ai_query(
  endpoint  => 'spam-classification-endpoint',
  request   => named_struct(
    'text', email_body,
    'subject', email_subject
  ),
  returnType => 'BOOLEAN'
) AS is_spam
FROM catalog.schema.inbox_messages;
```

### 多模態（影像）輸入

```sql
-- 使用視覺模型分析影像
SELECT ai_query(
  'databricks-meta-llama-3-2-90b-instruct',
  '描述此影像的內容。',
  files => READ_FILES('/Volumes/catalog/schema/images/photo.jpg', format => 'binaryFile')
) AS description;
```

### 使用 failOnError 的錯誤處理

```sql
-- 批次處理的優雅錯誤處理
SELECT
  id,
  result.result AS answer,
  result.errorMessage AS error
FROM (
  SELECT
    id,
    ai_query(
      'databricks-meta-llama-3-3-70b-instruct',
      question,
      failOnError => false
    ) AS result
  FROM catalog.schema.questions
);
```

### 嵌入生成

```sql
-- 使用 ai_query 生成嵌入
SELECT
  text,
  ai_query('databricks-gte-large-en', text) AS embedding
FROM catalog.schema.documents;
```

---

## 特定任務的 AI 函數

這些函數提供簡化的單一用途介面，不需要指定端點或模型。

### ai_gen

從提示生成文字。

```sql
ai_gen(prompt)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `prompt` | STRING | 使用者的請求/提示 |

**返回：**STRING

```sql
-- 簡單生成
SELECT ai_gen('為夏季自行車促銷活動生成簡潔、愉快的電子郵件標題，享 20% 折扣');
-- 返回："夏季自行車促銷：以 20% 折扣購買您夢想中的自行車！"

-- 使用資料表資料生成
SELECT
  question,
  ai_gen('您是一位老師。用 50 個字回答學生的問題：' || question) AS answer
FROM catalog.schema.questions
LIMIT 10;
```

---

### ai_classify

將文字分類為提供的標籤之一。

```sql
ai_classify(content, labels)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `content` | STRING | 要分類的文字 |
| `labels` | ARRAY<STRING> | 分類選項（最少 2 個，最多 20 個元素） |

**返回：**符合其中一個標籤的 STRING，如果分類失敗則為 NULL。

```sql
-- 簡單分類
SELECT ai_classify('我的密碼洩漏了。', ARRAY('緊急', '不緊急'));
-- 返回："緊急"

-- 批次產品分類
SELECT
  product_name,
  description,
  ai_classify(description, ARRAY('服裝', '鞋子', '配件', '家具')) AS category
FROM catalog.schema.products
LIMIT 100;

-- 支援工單路由
SELECT
  ticket_id,
  ai_classify(
    description,
    ARRAY('帳務', '技術', '帳戶', '功能請求', '其他')
  ) AS department
FROM catalog.schema.support_tickets;
```

---

### ai_extract

從文字中提取命名實體。

```sql
ai_extract(content, labels)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `content` | STRING | 要從中提取實體的文字 |
| `labels` | ARRAY<STRING> | 要提取的實體類型 |

**返回：**STRUCT，其中每個欄位對應一個標籤，包含提取的實體作為 STRING。如果 content 為 NULL 則返回 NULL。

```sql
-- 提取人物、地點、組織
SELECT ai_extract(
  'John Doe 住在紐約，為 Acme Corp 工作。',
  ARRAY('person', 'location', 'organization')
);
-- 返回：{"person": "John Doe", "location": "紐約", "organization": "Acme Corp"}

-- 提取聯絡詳細資訊
SELECT ai_extract(
  '發送電子郵件到 jane.doe@example.com 關於上午 10 點的會議。',
  ARRAY('email', 'time')
);
-- 返回：{"email": "jane.doe@example.com", "time": "上午 10 點"}

-- 從客戶回饋批次提取實體
SELECT
  feedback_id,
  ai_extract(feedback_text, ARRAY('product', 'issue', 'person')) AS entities
FROM catalog.schema.customer_feedback;
```

---

### ai_analyze_sentiment

對文字執行情感分析。

```sql
ai_analyze_sentiment(content)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `content` | STRING | 要分析的文字 |

**返回：**STRING -- `'positive'`、`'negative'`、`'neutral'` 或 `'mixed'` 之一。如果無法確定情感則返回 NULL。

```sql
SELECT ai_analyze_sentiment('我很開心');     -- 返回："positive"
SELECT ai_analyze_sentiment('我很難過');       -- 返回："negative"
SELECT ai_analyze_sentiment('就是這樣'); -- 返回："neutral"

-- 按產品聚合情感
SELECT
  product_id,
  ai_analyze_sentiment(review_text) AS sentiment,
  COUNT(*) AS review_count
FROM catalog.schema.reviews
GROUP BY product_id, ai_analyze_sentiment(review_text);
```

---

### ai_similarity

計算兩個文字字串之間的語義相似度。

```sql
ai_similarity(expr1, expr2)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `expr1` | STRING | 要比較的第一個文字 |
| `expr2` | STRING | 要比較的第二個文字 |

**返回：**FLOAT -- 語義相似度分數，其中 1.0 表示相同。分數是相對的，應僅用於排名。

```sql
-- 完全匹配
SELECT ai_similarity('Apache Spark', 'Apache Spark');
-- 返回：1.0

-- 尋找相似的公司名稱（模糊匹配）
SELECT company_name, ai_similarity(company_name, 'Databricks') AS score
FROM catalog.schema.customers
ORDER BY score DESC
LIMIT 10;

-- 重複偵測
SELECT
  a.id AS id_a,
  b.id AS id_b,
  ai_similarity(a.description, b.description) AS similarity
FROM catalog.schema.products a
JOIN catalog.schema.products b ON a.id < b.id
WHERE ai_similarity(a.description, b.description) > 0.85;
```

---

### ai_summarize

生成文字摘要。

```sql
ai_summarize(content [, max_words])
```

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `content` | STRING | 是 | 要摘要的文字 |
| `max_words` | INTEGER | 否 | 摘要的目標字數。預設：50。設定為 0 表示無限制 |

**返回：**STRING。如果 content 為 NULL 則返回 NULL。

```sql
-- 使用預設 50 字限制摘要
SELECT ai_summarize(
  'Apache Spark 是用於大規模資料處理的統一分析引擎。'
  || '它提供 Java、Scala、Python 和 R 的高階 API，以及支援通用執行圖的優化引擎。'
);

-- 使用自訂字數限制摘要
SELECT ai_summarize(article_body, 100) AS summary
FROM catalog.schema.articles;

-- 報告的執行摘要
SELECT
  report_id,
  report_title,
  ai_summarize(report_body, 30) AS executive_summary
FROM catalog.schema.quarterly_reports;
```

---

### ai_translate

將文字翻譯為目標語言。

```sql
ai_translate(content, to_lang)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `content` | STRING | 要翻譯的文字 |
| `to_lang` | STRING | 目標語言代碼 |

**支援的語言：**英文（`en`）、德文（`de`）、法文（`fr`）、義大利文（`it`）、葡萄牙文（`pt`）、印地文（`hi`）、西班牙文（`es`）、泰文（`th`）。

**返回：**STRING。如果 content 為 NULL 則返回 NULL。

```sql
-- 英文到西班牙文
SELECT ai_translate('Hello, how are you?', 'es');
-- 返回："Hola, como estas?"

-- 西班牙文到英文
SELECT ai_translate('La vida es un hermoso viaje.', 'en');
-- 返回："Life is a beautiful journey."

-- 翻譯產品描述以進行本地化
SELECT
  product_id,
  description AS original,
  ai_translate(description, 'fr') AS french,
  ai_translate(description, 'de') AS german
FROM catalog.schema.products;
```

---

### ai_fix_grammar

更正文字中的語法錯誤。

```sql
ai_fix_grammar(content)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `content` | STRING | 要更正的文字 |

**返回：**帶有更正語法的 STRING。如果 content 為 NULL 則返回 NULL。

```sql
SELECT ai_fix_grammar('This sentence have some mistake');
-- 返回："This sentence has some mistakes"

SELECT ai_fix_grammar('She dont know what to did.');
-- 返回："She doesn't know what to do."

-- 清理使用者生成的內容
SELECT
  comment_id,
  original_text,
  ai_fix_grammar(original_text) AS corrected_text
FROM catalog.schema.user_comments;
```

---

### ai_mask

遮罩文字中的指定實體類型（PII 編輯）。

```sql
ai_mask(content, labels)
```

| 參數 | 類型 | 說明 |
|-----------|------|-------------|
| `content` | STRING | 包含要遮罩的實體的文字 |
| `labels` | ARRAY<STRING> | 要遮罩的實體類型（例如，`'person'`、`'email'`、`'phone'`、`'address'`、`'location'`、`'ssn'`、`'credit_card'`） |

**返回：**將指定實體替換為 `[MASKED]` 的 STRING。如果 content 為 NULL 則返回 NULL。

```sql
-- 遮罩個人資訊
SELECT ai_mask(
  'John Doe 住在紐約。他的電子郵件是 john.doe@example.com。',
  ARRAY('person', 'email')
);
-- 返回："[MASKED] 住在紐約。他的電子郵件是 [MASKED]。"

-- 遮罩聯絡詳細資訊
SELECT ai_mask(
  '請致電 555-1234 或訪問我們位於 123 Main St 的地址。',
  ARRAY('phone', 'address')
);
-- 返回："請致電 [MASKED] 或訪問我們位於 [MASKED] 的地址。"

-- 建立匿名化資料集
CREATE TABLE catalog.schema.anonymized_feedback AS
SELECT
  feedback_id,
  ai_mask(feedback_text, ARRAY('person', 'email', 'phone', 'address')) AS masked_text,
  category
FROM catalog.schema.customer_feedback;
```

---

## 文件和多模態 AI 函數

### ai_parse_document

從非結構化文件（PDF、DOCX、PPTX、影像）中提取結構化內容。

```sql
ai_parse_document(content)
ai_parse_document(content, options_map)
```

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `content` | BINARY | 是 | 文件作為二進位 blob 資料 |
| `options` | MAP<STRING, STRING> | 否 | 配置選項 |

**選項 Map 鍵：**

| 鍵 | 值 | 說明 |
|-----|--------|-------------|
| `version` | `'2.0'` | 輸出結構描述版本 |
| `imageOutputPath` | 磁碟區路徑 | 在 Unity Catalog 磁碟區中儲存渲染頁面影像的路徑 |
| `descriptionElementTypes` | `''`、`'figure'`、`'*'` | 控制 AI 生成的描述。預設：`'*'`（所有元素） |

**返回：**VARIANT，結構為：
- `document.pages[]` -- 頁面中繼資料（id、image_uri）
- `document.elements[]` -- 提取的內容（type、content、bbox、description）
- `error_status[]` -- 每頁的錯誤詳細資訊
- `metadata` -- 檔案和結構描述版本資訊

**支援的格式：**PDF、JPG/JPEG、PNG、DOC/DOCX、PPT/PPTX

**需求：**Databricks Runtime 17.1+，美國/歐盟區域或啟用跨地理路由。

```sql
-- 基本文件解析
SELECT ai_parse_document(content)
FROM READ_FILES('/Volumes/catalog/schema/volume/docs/', format => 'binaryFile');

-- 使用選項解析（儲存影像，版本 2.0）
SELECT ai_parse_document(
  content,
  map(
    'version', '2.0',
    'imageOutputPath', '/Volumes/catalog/schema/volume/images/',
    'descriptionElementTypes', '*'
  )
)
FROM READ_FILES('/Volumes/catalog/schema/volume/invoices/', format => 'binaryFile');

-- 解析文件然後使用 ai_query 提取結構化資料
WITH parsed AS (
  SELECT
    path,
    ai_parse_document(content) AS doc
  FROM READ_FILES('/Volumes/catalog/schema/volume/invoices/', format => 'binaryFile')
)
SELECT
  path,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    CONCAT('從以下內容提取供應商名稱、發票號碼和總額：', doc:document:elements[0]:content::STRING),
    responseFormat => 'STRUCT<vendor: STRING, invoice_number: STRING, total: DOUBLE>'
  ) AS invoice_data
FROM parsed;
```

---

## 時間序列 AI 函數

### ai_forecast

使用內建的類 prophet 模型預測時間序列資料。這是一個資料表值函數（TVF）。

```sql
ai_forecast(
  observed                  TABLE,
  horizon                   DATE | TIMESTAMP | STRING,
  time_col                  STRING,
  value_col                 STRING | ARRAY<STRING>,
  group_col                 STRING | ARRAY<STRING> | NULL  DEFAULT NULL,
  prediction_interval_width DOUBLE                         DEFAULT 0.95,
  frequency                 STRING                         DEFAULT 'auto',
  seed                      INTEGER | NULL                 DEFAULT NULL,
  parameters                STRING                         DEFAULT '{}'
)
```

### 參數

| 參數 | 類型 | 預設值 | 說明 |
|-----------|------|---------|-------------|
| `observed` | TABLE | 必要 | 作為 `TABLE(subquery)` 或 `TABLE(table_name)` 傳遞的訓練資料 |
| `horizon` | DATE/TIMESTAMP/STRING | 必要 | 右排除的預測結束時間 |
| `time_col` | STRING | 必要 | 觀察資料中的 DATE 或 TIMESTAMP 欄位名稱 |
| `value_col` | STRING 或 ARRAY<STRING> | 必要 | 要預測的一個或多個數值欄位 |
| `group_col` | STRING、ARRAY<STRING> 或 NULL | NULL | 用於獨立每組預測的分割欄位 |
| `prediction_interval_width` | DOUBLE | 0.95 | 預測界限的信賴水準（0 到 1） |
| `frequency` | STRING | `'auto'` | 時間粒度。從最近的資料自動推斷。對於 DATE 欄位使用：`'day'`、`'week'`、`'month'`。對於 TIMESTAMP 欄位：`'D'`、`'W'`、`'M'`、`'H'` 等。 |
| `seed` | INTEGER 或 NULL | NULL | 用於可重現性的隨機種子 |
| `parameters` | STRING | `'{}'` | JSON 編碼的進階設定 |

**進階參數（JSON）：**
- `global_cap` -- 邏輯增長的上限
- `global_floor` -- 邏輯增長的下限
- `daily_order` -- 每日季節性的傅立葉階數
- `weekly_order` -- 每週季節性的傅立葉階數

### 返回欄位

對於每個名為 `v` 的 `value_col`，輸出包含：
- `{v}_forecast`（DOUBLE）-- 點預測
- `{v}_upper`（DOUBLE）-- 預測上限
- `{v}_lower`（DOUBLE）-- 預測下限
- 加上原始時間欄位和群組欄位

**需求：**無伺服器 SQL 倉儲。

```sql
-- 基本收入預測
SELECT * FROM ai_forecast(
  TABLE(SELECT ds, revenue FROM catalog.schema.daily_sales),
  horizon    => '2025-12-31',
  time_col   => 'ds',
  value_col  => 'revenue'
);

-- 按群組的多指標預測
SELECT * FROM ai_forecast(
  TABLE(
    SELECT date, zipcode, revenue, trip_count
    FROM catalog.schema.regional_metrics
  ),
  horizon                   => '2025-06-30',
  time_col                  => 'date',
  value_col                 => ARRAY('revenue', 'trip_count'),
  group_col                 => 'zipcode',
  prediction_interval_width => 0.90,
  frequency                 => 'D'
);

-- 帶有增長約束的每月預測（對 DATE 欄位使用 'month'，而非 'M'）
SELECT * FROM ai_forecast(
  TABLE(catalog.schema.monthly_kpis),
  horizon    => '2026-01-01',
  time_col   => 'month',
  value_col  => 'active_users',
  frequency  => 'month',
  parameters => '{"global_floor": 0}'
);
```

---

## 向量搜尋函數

### vector_search

使用 SQL 查詢 Mosaic AI 向量搜尋索引。這是一個資料表值函數。

```sql
-- Databricks Runtime 15.3+
SELECT * FROM vector_search(
  index       => index_name,
  query_text  => search_text,         -- 或 query_vector => embedding_array
  num_results => max_results,
  query_type  => 'ANN' | 'HYBRID'
)
```

### 參數（需要命名引數）

| 參數 | 類型 | 預設值 | 說明 |
|-----------|------|---------|-------------|
| `index` | STRING 常數 | 必要 | 向量搜尋索引的完全限定名稱 |
| `query_text` | STRING | -- | 搜尋字串（用於帶有嵌入來源的 Delta 同步索引） |
| `query_vector` | ARRAY<FLOAT\|DOUBLE\|DECIMAL> | -- | 要搜尋的預先計算的嵌入向量 |
| `num_results` | INTEGER | 10 | 返回的最大記錄數（最多 100） |
| `query_type` | STRING | `'ANN'` | `'ANN'` 用於近似最近鄰，`'HYBRID'` 用於混合搜尋 |

**返回：**包含所有索引欄位和最匹配記錄的資料表。

**需求：**無伺服器 SQL 倉儲，索引上的 Select 權限。

```sql
-- 基於文字的相似度搜尋
SELECT * FROM vector_search(
  index      => 'catalog.schema.product_index',
  query_text => '無線降噪耳機',
  num_results => 5
);

-- 混合搜尋（結合關鍵字 + 語義）
SELECT * FROM vector_search(
  index       => 'catalog.schema.support_docs_index',
  query_text  => '路由器型號 LMP-9R2 的 Wi-Fi 連接問題',
  query_type  => 'HYBRID',
  num_results => 3
);

-- 使用預先計算的嵌入進行基於向量的搜尋
SELECT * FROM vector_search(
  index        => 'catalog.schema.embeddings_index',
  query_vector => ARRAY(0.45, -0.35, 0.78, 0.22),
  num_results  => 10
);

-- 使用 LATERAL 連接的批次搜尋
SELECT
  q.query_text,
  q.query_id,
  results.*
FROM catalog.schema.search_queries q,
LATERAL (
  SELECT * FROM vector_search(
    index       => 'catalog.schema.knowledge_base_index',
    query_text  => q.query_text,
    num_results => 3
  )
) AS results;
```

---

## http_request 函數

使用 Unity Catalog HTTP 連接從 SQL 向外部服務發出 HTTP 請求。

### 語法

```sql
http_request(
  CONN    => connection_name,
  METHOD  => http_method,
  PATH    => path,
  HEADERS => header_map,
  PARAMS  => param_map,
  JSON    => json_body
)
```

### 參數

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `CONN` | STRING 常數 | 是 | 現有 HTTP 連接的名稱 |
| `METHOD` | STRING 常數 | 是 | HTTP 方法：`'GET'`、`'POST'`、`'PUT'`、`'DELETE'`、`'PATCH'` |
| `PATH` | STRING 常數 | 是 | 附加到連接的 base_path 的路徑。不能包含目錄遍歷（`../`） |
| `HEADERS` | MAP<STRING, STRING> | 否 | 請求標頭。預設：NULL |
| `PARAMS` | MAP<STRING, STRING> | 否 | 查詢參數。預設：NULL |
| `JSON` | STRING 表達式 | 否 | 請求主體作為 JSON 字串 |

### 返回類型

`STRUCT<status_code: INT, text: STRING>`
- `status_code` -- HTTP 回應狀態（例如，200、403、404）
- `text` -- 回應主體（通常為 JSON）

**需求：**Databricks Runtime 16.2+，啟用 Unity Catalog 的工作區，USE CONNECTION 權限。

### 建立 HTTP 連接

```sql
-- Bearer token 驗證
CREATE CONNECTION slack_conn TYPE HTTP
OPTIONS (
  host         'https://slack.com',
  port         '443',
  base_path    '/api/',
  bearer_token secret('my-scope', 'slack-token')
);

-- OAuth Machine-to-Machine
CREATE CONNECTION github_conn TYPE HTTP
OPTIONS (
  host           'https://api.github.com',
  port           '443',
  base_path      '/',
  client_id      secret('my-scope', 'github-client-id'),
  client_secret  secret('my-scope', 'github-client-secret'),
  oauth_scope    'repo read:org',
  token_endpoint 'https://github.com/login/oauth/access_token'
);
```

**連接選項：**

| 選項 | 類型 | 說明 |
|--------|------|-------------|
| `host` | STRING | 外部服務的基礎 URL |
| `port` | STRING | 網路埠（HTTPS 通常為 `'443'`） |
| `base_path` | STRING | API 端點的根路徑 |
| `bearer_token` | STRING | 驗證權杖（使用 `secret()` 以確保安全） |
| `client_id` | STRING | OAuth 應用程式識別碼 |
| `client_secret` | STRING | OAuth 應用程式密鑰 |
| `oauth_scope` | STRING | 以空格分隔的 OAuth 範圍 |
| `token_endpoint` | STRING | OAuth 權杖端點 URL |
| `authorization_endpoint` | STRING | OAuth 授權重定向 URL |
| `oauth_credential_exchange_method` | STRING | `'header_and_body'`、`'body_only'` 或 `'header_only'` |

### 範例

```sql
-- POST Slack 訊息
SELECT http_request(
  CONN   => 'slack_conn',
  METHOD => 'POST',
  PATH   => '/chat.postMessage',
  JSON   => to_json(named_struct('channel', '#alerts', 'text', '管線成功完成'))
);

-- 帶有標頭和參數的 GET 請求
SELECT http_request(
  CONN    => 'github_conn',
  METHOD  => 'GET',
  PATH    => '/repos/databricks/spark/issues',
  HEADERS => map('Accept', 'application/vnd.github+json'),
  PARAMS  => map('state', 'open', 'per_page', '5')
);

-- 解析 JSON 回應
SELECT
  response.status_code,
  from_json(response.text, 'STRUCT<id: INT, title: STRING, state: STRING>') AS issue
FROM (
  SELECT http_request(
    CONN   => 'github_conn',
    METHOD => 'GET',
    PATH   => '/repos/databricks/spark/issues/1'
  ) AS response
);

-- 由資料變更觸發的 Webhook 通知
SELECT http_request(
  CONN   => 'webhook_conn',
  METHOD => 'POST',
  PATH   => '/notify',
  JSON   => to_json(named_struct(
    'event', 'data_quality_alert',
    'table', 'catalog.schema.orders',
    'message', CONCAT('空值率超過閾值：', CAST(null_pct AS STRING))
  ))
)
FROM catalog.schema.data_quality_metrics
WHERE null_pct > 0.05;
```

---

## remote_query 函數（Lakehouse Federation）

使用外部資料庫的原生 SQL 語法對其執行 SQL 查詢，在 Databricks SQL 中以資料表形式返回結果。這是一個資料表值函數。

### 概述

Lakehouse Federation 能夠在不遷移資料的情況下查詢外部資料庫。它支援兩種模式：
- **查詢聯邦** -- 查詢透過 JDBC 下推到外部資料庫
- **目錄聯邦** -- 查詢直接存取物件儲存中的外部資料表

### 語法

```sql
SELECT * FROM remote_query(
  '<connection-name>',
  <option-key> => '<option-value>'
  [, ...]
)
```

### 支援的資料庫

| 資料庫 | 連接類型 |
|----------|----------------|
| PostgreSQL | `POSTGRESQL` |
| MySQL | `MYSQL` |
| Microsoft SQL Server | `SQLSERVER` |
| Oracle | `ORACLE` |
| Teradata | `TERADATA` |
| Amazon Redshift | `REDSHIFT` |
| Snowflake | `SNOWFLAKE` |
| Google BigQuery | `BIGQUERY` |
| Databricks | `DATABRICKS` |

### 按資料庫類型的參數

**PostgreSQL / MySQL / SQL Server / Redshift / Teradata：**

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `database` | STRING | 是 | 遠端資料庫名稱 |
| `query` | STRING | query/dbtable 二選一 | 遠端資料庫原生語法的 SQL 查詢 |
| `dbtable` | STRING | query/dbtable 二選一 | 完全限定的資料表名稱 |
| `fetchsize` | STRING | 否 | 每次往返要獲取的列數 |
| `partitionColumn` | STRING | 否 | 用於平行讀取分割的欄位 |
| `lowerBound` | STRING | 否 | 分割欄位的下限 |
| `upperBound` | STRING | 否 | 分割欄位的上限 |
| `numPartitions` | STRING | 否 | 平行分割數 |

**Oracle（使用 `service_name` 而非 `database`）：**

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `service_name` | STRING | 是 | Oracle 服務名稱 |
| `query` 或 `dbtable` | STRING | 是（二選一） | 查詢或資料表引用 |

**Snowflake：**

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `database` | STRING | 是 | Snowflake 資料庫 |
| `schema` | STRING | 否 | 結構描述名稱（預設為 `public`） |
| `query` 或 `dbtable` | STRING | 是（二選一） | 查詢或資料表引用 |
| `query_timeout` | STRING | 否 | 查詢逾時（秒） |
| `partition_size_in_mb` | STRING | 否 | 讀取的分割大小 |

**BigQuery：**

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `query` 或 `dbtable` | STRING | 是（二選一） | 查詢或資料表引用 |
| `materializationDataset` | STRING | 用於檢視/複雜查詢 | 用於具體化的資料集 |
| `materializationProject` | STRING | 否 | 用於具體化的 GCP 專案 |
| `parentProject` | STRING | 否 | 父 GCP 專案 |

### 下推控制

| 選項 | 預設值 | 說明 |
|--------|---------|-------------|
| `pushdown.limit.enabled` | `true` | 將 LIMIT 下推到遠端 |
| `pushdown.offset.enabled` | `true` | 將 OFFSET 下推到遠端 |
| `pushdown.filters.enabled` | `true` | 將 WHERE 篩選器下推到遠端 |
| `pushdown.aggregates.enabled` | `true` | 將聚合下推到遠端 |
| `pushdown.sortLimit.enabled` | `true` | 將 ORDER BY + LIMIT 下推到遠端 |

### 需求

- 啟用 Unity Catalog 的工作區
- Databricks Runtime 17.3+（叢集）或 SQL Warehouse 2025.35+（Pro/無伺服器）
- 與目標資料庫的網路連接
- `USE CONNECTION` 權限或包裝檢視上的 `SELECT`

### 限制

- **唯讀**：僅支援 SELECT 查詢（不支援 INSERT、UPDATE、DELETE、MERGE、DDL 或預存程序）

### 建立連接

```sql
-- PostgreSQL 連接
CREATE CONNECTION my_postgres TYPE POSTGRESQL
OPTIONS (
  host     'pg-server.example.com',
  port     '5432',
  user     secret('my-scope', 'pg-user'),
  password secret('my-scope', 'pg-password')
);

-- SQL Server 連接
CREATE CONNECTION my_sqlserver TYPE SQLSERVER
OPTIONS (
  host     'sql-server.example.com',
  port     '1433',
  user     secret('my-scope', 'sql-user'),
  password secret('my-scope', 'sql-password')
);
```

### 範例

```sql
-- 對 PostgreSQL 的基本查詢
SELECT * FROM remote_query(
  'my_postgres',
  database => 'sales_db',
  query    => 'SELECT customer_id, name, email FROM customers WHERE active = true'
);

-- 從 SQL Server 平行讀取
SELECT * FROM remote_query(
  'my_sqlserver',
  database        => 'orders_db',
  dbtable         => 'dbo.transactions',
  partitionColumn => 'transaction_id',
  lowerBound      => '0',
  upperBound      => '1000000',
  numPartitions   => '10'
);

-- 將聯邦資料與本地 Delta 資料表連接
SELECT
  o.order_id,
  o.amount,
  c.name,
  c.email
FROM catalog.schema.orders o
JOIN remote_query(
  'my_postgres',
  database => 'crm_db',
  query    => 'SELECT customer_id, name, email FROM customers'
) c ON o.customer_id = c.customer_id;

-- 透過檢視進行存取委派
CREATE VIEW catalog.schema.federated_customers AS
SELECT * FROM remote_query(
  'my_postgres',
  database => 'crm_db',
  query    => 'SELECT customer_id, name, region FROM customers'
);

-- 使用者只需要檢視上的 SELECT，不需要 USE CONNECTION
GRANT SELECT ON VIEW catalog.schema.federated_customers TO `analysts`;
```

---

## read_files 資料表值函數

直接在 SQL 中從雲端儲存或 Unity Catalog 磁碟區讀取檔案，具有自動格式偵測和結構描述推斷功能。

### 語法

```sql
SELECT * FROM read_files(
  path
  [, option_key => option_value ] [...]
)
```

### 核心參數

| 參數 | 類型 | 必要 | 說明 |
|-----------|------|----------|-------------|
| `path` | STRING | 是 | 資料位置的 URI。支援 `s3://`、`abfss://`、`gs://`、`/Volumes/...` 路徑。接受 glob 模式 |

### 常見選項

| 選項 | 類型 | 預設值 | 說明 |
|--------|------|---------|-------------|
| `format` | STRING | 自動偵測 | 檔案格式：`'csv'`、`'json'`、`'parquet'`、`'avro'`、`'orc'`、`'text'`、`'binaryFile'`、`'xml'` |
| `schema` | STRING | 推斷 | DDL 格式的明確結構描述定義 |
| `schemaHints` | STRING | 無 | 覆寫推斷結構描述欄位的子集 |
| `rescuedDataColumn` | STRING | `'_rescued_data'` | 無法解析的資料的欄位名稱。設定為空字串以停用 |
| `pathGlobFilter` / `fileNamePattern` | STRING | 無 | 用於篩選檔案的 Glob 模式（例如，`'*.csv'`） |
| `recursiveFileLookup` | BOOLEAN | `false` | 搜尋巢狀目錄 |
| `modifiedAfter` | TIMESTAMP STRING | 無 | 僅讀取在此時間戳記之後修改的檔案 |
| `modifiedBefore` | TIMESTAMP STRING | 無 | 僅讀取在此時間戳記之前修改的檔案 |
| `partitionColumns` | STRING | 自動偵測 | 以逗號分隔的 Hive 樣式分割欄位。空字串忽略所有分割 |
| `useStrictGlobber` | BOOLEAN | `true` | 嚴格的 glob 模式匹配 |
| `inferColumnTypes` | BOOLEAN | `true` | 推斷確切的欄位類型（vs 將所有視為 STRING） |
| `schemaEvolutionMode` | STRING | -- | 結構描述演化行為：`'none'` 以刪除救援資料欄位 |

### CSV 特定選項

| 選項 | 類型 | 預設值 | 說明 |
|--------|------|---------|-------------|
| `sep` / `delimiter` | STRING | `','` | 欄位分隔符號 |
| `header` | BOOLEAN | `false` | 第一列包含欄位名稱 |
| `encoding` | STRING | `'UTF-8'` | 字元編碼 |
| `quote` | STRING | `'"'` | 引號字元 |
| `escape` | STRING | `'\'` | 跳脫字元 |
| `nullValue` | STRING | `''` | null 的字串表示 |
| `dateFormat` | STRING | `'yyyy-MM-dd'` | 日期解析格式 |
| `timestampFormat` | STRING | `'yyyy-MM-dd\'T\'HH:mm:ss...'` | 時間戳記解析格式 |
| `mode` | STRING | `'PERMISSIVE'` | 解析模式：`'PERMISSIVE'`、`'DROPMALFORMED'`、`'FAILFAST'` |
| `multiLine` | BOOLEAN | `false` | 允許跨多列的記錄 |
| `ignoreLeadingWhiteSpace` | BOOLEAN | `false` | 修剪前導空白 |
| `ignoreTrailingWhiteSpace` | BOOLEAN | `false` | 修剪尾隨空白 |
| `comment` | STRING | 無 | 行註解字元 |
| `maxCharsPerColumn` | INTEGER | 無 | 每欄位的最大字元數 |
| `maxColumns` | INTEGER | 無 | 最大欄位數 |
| `mergeSchema` | BOOLEAN | `false` | 跨檔案合併結構描述 |
| `enforceSchema` | BOOLEAN | `true` | 強制執行指定的結構描述 |
| `locale` | STRING | `'US'` | 數字/日期解析的區域設定 |
| `charToEscapeQuoteEscaping` | STRING | 無 | 用於跳脫引號跳脫字元的字元 |
| `readerCaseSensitive` | BOOLEAN | `true` | 區分大小寫的欄位名稱匹配 |

### JSON 特定選項

| 選項 | 類型 | 預設值 | 說明 |
|--------|------|---------|-------------|
| `multiLine` | BOOLEAN | `false` | 解析多行 JSON 記錄 |
| `allowComments` | BOOLEAN | `false` | 允許 Java/C++ 樣式註解 |
| `allowSingleQuotes` | BOOLEAN | `true` | 允許字串使用單引號 |
| `allowUnquotedFieldNames` | BOOLEAN | `false` | 允許未加引號的欄位名稱 |
| `allowBackslashEscapingAnyCharacter` | BOOLEAN | `false` | 允許反斜線跳脫任何字元 |
| `allowNonNumericNumbers` | BOOLEAN | `true` | 允許 NaN、Infinity、-Infinity |
| `encoding` | STRING | `'UTF-8'` | 字元編碼 |
| `dateFormat` | STRING | `'yyyy-MM-dd'` | 日期解析格式 |
| `timestampFormat` | STRING | -- | 時間戳記解析格式 |
| `inferTimestamp` | BOOLEAN | `false` | 推斷時間戳記類型 |
| `prefersDecimal` | BOOLEAN | `false` | 優先使用 DECIMAL 而非 DOUBLE |
| `primitivesAsString` | BOOLEAN | `false` | 將所有基本類型推斷為 STRING |
| `singleVariantColumn` | STRING | 無 | 將整個 JSON 讀取為單一 VARIANT 欄位 |
| `locale` | STRING | `'US'` | 解析的區域設定 |
| `mode` | STRING | `'PERMISSIVE'` | 解析模式 |
| `readerCaseSensitive` | BOOLEAN | `true` | 區分大小寫的欄位匹配 |
| `timeZone` | STRING | 工作階段時區 | 時間戳記解析的時區 |

### XML 特定選項

| 選項 | 類型 | 預設值 | 說明 |
|--------|------|---------|-------------|
| `rowTag` | STRING | **必要** | 分隔列的 XML 標籤 |
| `attributePrefix` | STRING | `'_'` | XML 屬性的前綴 |
| `valueTag` | STRING | `'_VALUE'` | 元素文字內容的標籤 |
| `encoding` | STRING | `'UTF-8'` | 字元編碼 |
| `ignoreSurroundingSpaces` | BOOLEAN | `true` | 忽略值周圍的空白 |
| `ignoreNamespace` | BOOLEAN | `false` | 忽略 XML 命名空間 |
| `mode` | STRING | `'PERMISSIVE'` | 解析模式 |
| `dateFormat` | STRING | `'yyyy-MM-dd'` | 日期解析格式 |
| `timestampFormat` | STRING | -- | 時間戳記解析格式 |
| `locale` | STRING | `'US'` | 解析的區域設定 |
| `readerCaseSensitive` | BOOLEAN | `true` | 區分大小寫的匹配 |
| `samplingRatio` | DOUBLE | `1.0` | 用於結構描述推斷的列採樣比例 |

### Parquet / Avro / ORC 選項

| 選項 | 類型 | 預設值 | 說明 |
|--------|------|---------|-------------|
| `mergeSchema` | BOOLEAN | `false` | 跨檔案合併結構描述 |
| `readerCaseSensitive` | BOOLEAN | `true` | 區分大小寫的欄位匹配 |
| `rescuedDataColumn` | STRING | -- | 救援資料的欄位 |
| `datetimeRebaseMode` | STRING | -- | 日期時間值的重定基準模式 |
| `int96RebaseMode` | STRING | -- | INT96 時間戳記的重定基準模式（僅限 Parquet） |

### 串流選項

| 選項 | 類型 | 預設值 | 說明 |
|--------|------|---------|-------------|
| `includeExistingFiles` | BOOLEAN | `true` | 在首次執行時處理現有檔案 |
| `maxFilesPerTrigger` | INTEGER | 無 | 每個微批次的最大檔案數 |
| `maxBytesPerTrigger` | STRING | 無 | 每個微批次的最大位元組數 |
| `allowOverwrites` | BOOLEAN | `false` | 允許處理被覆寫的檔案 |
| `schemaEvolutionMode` | STRING | -- | 結構描述演化行為 |
| `schemaLocation` | STRING | -- | 儲存推斷結構描述的位置 |

### 需求

- Databricks Runtime 13.3 LTS 及以上
- Databricks SQL

### 範例

```sql
-- 從雲端儲存自動偵測格式和結構描述
SELECT * FROM read_files('s3://my-bucket/data/');

-- 使用明確結構描述讀取 CSV
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/sales.csv',
  format => 'csv',
  header => true,
  schema => 'order_id INT, customer_id INT, amount DOUBLE, order_date DATE'
);

-- 使用結構描述提示讀取 CSV（僅覆寫特定欄位）
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/events/',
  format      => 'csv',
  header      => true,
  schemaHints => 'event_timestamp TIMESTAMP, amount DECIMAL(10,2)'
);

-- 使用多行支援讀取 JSON
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/api_responses/',
  format    => 'json',
  multiLine => true
);

-- 使用跨檔案合併結構描述讀取 Parquet
SELECT * FROM read_files(
  's3://my-bucket/parquet-data/',
  format      => 'parquet',
  mergeSchema => true
);

-- 使用列標籤讀取 XML
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/feed.xml',
  format => 'xml',
  rowTag => 'record'
);

-- 為 ai_parse_document 讀取二進位檔案（影像、PDF）
SELECT path, content FROM read_files(
  '/Volumes/catalog/schema/volume/documents/',
  format => 'binaryFile'
);

-- 按 glob 模式和修改日期篩選檔案
SELECT * FROM read_files(
  's3://my-bucket/logs/',
  format          => 'json',
  pathGlobFilter  => '*.json',
  modifiedAfter   => '2025-01-01T00:00:00Z',
  modifiedBefore  => '2025-02-01T00:00:00Z'
);

-- 帶有分割發現的遞迴目錄掃描
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/partitioned_data/',
  recursiveFileLookup => true,
  partitionColumns    => 'year,month'
);

-- 包含檔案中繼資料
SELECT *, _metadata.file_path, _metadata.file_name, _metadata.file_size
FROM read_files('/Volumes/catalog/schema/volume/data/');

-- 從檔案建立資料表
CREATE TABLE catalog.schema.imported_data AS
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/export.csv',
  format => 'csv',
  header => true
);

-- 從雲端儲存的串流資料表
CREATE STREAMING TABLE catalog.schema.streaming_events AS
SELECT * FROM STREAM read_files(
  's3://my-bucket/events/',
  format              => 'json',
  includeExistingFiles => false,
  maxFilesPerTrigger   => 100
);

-- 為半結構化 JSON 讀取單一 VARIANT 欄位
SELECT * FROM read_files(
  '/Volumes/catalog/schema/volume/complex.json',
  format              => 'json',
  singleVariantColumn => 'raw_data'
);
```

---

## 組合函數 -- 生產模式

### AI 增強的 ETL 管線

```sql
-- 使用多個 AI 函數處理客戶回饋
CREATE OR REPLACE TABLE catalog.schema.enriched_feedback AS
SELECT
  feedback_id,
  feedback_text,
  ai_analyze_sentiment(feedback_text) AS sentiment,
  ai_classify(feedback_text, ARRAY('產品', '服務', '帳務', '其他')) AS category,
  ai_extract(feedback_text, ARRAY('product', 'issue')) AS entities,
  ai_summarize(feedback_text, 20) AS summary,
  ai_mask(feedback_text, ARRAY('person', 'email', 'phone')) AS anonymized_text
FROM catalog.schema.raw_feedback;
```

### 文件處理管線

```sql
-- 擷取、解析和查詢文件
WITH raw_docs AS (
  SELECT path, content
  FROM read_files('/Volumes/catalog/schema/volume/contracts/', format => 'binaryFile')
),
parsed AS (
  SELECT path, ai_parse_document(content, map('version', '2.0')) AS doc
  FROM raw_docs
)
SELECT
  path,
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    CONCAT('從以下內容提取合約方、生效日期和終止條款：',
           doc:document:elements[0]:content::STRING),
    responseFormat => 'STRUCT<party_a: STRING, party_b: STRING, effective_date: STRING, termination_clause: STRING>'
  ) AS contract_info
FROM parsed;
```

### 使用 http_request 的外部 API 整合

```sql
-- 透過呼叫外部 API 並連接結果來豐富資料
SELECT
  o.order_id,
  o.tracking_number,
  from_json(
    tracking.text,
    'STRUCT<status: STRING, location: STRING, estimated_delivery: STRING>'
  ) AS tracking_info
FROM catalog.schema.orders o
CROSS JOIN LATERAL (
  SELECT http_request(
    CONN   => 'shipping_api_conn',
    METHOD => 'GET',
    PATH   => CONCAT('/track/', o.tracking_number)
  ) AS response
) tracking
WHERE tracking.response.status_code = 200;
```

### 聯邦分析

```sql
-- 結合遠端資料庫資料與本地 lakehouse 資料和 AI
SELECT
  remote_orders.customer_id,
  remote_orders.total_spend,
  local_profiles.segment,
  ai_classify(
    CONCAT('客戶在區隔 ', local_profiles.segment, ' 中花費 $', CAST(remote_orders.total_spend AS STRING)),
    ARRAY('高價值', '中等價值', '低價值', '有風險')
  ) AS value_tier
FROM remote_query(
  'my_postgres',
  database => 'sales_db',
  query    => 'SELECT customer_id, SUM(amount) as total_spend FROM orders GROUP BY customer_id'
) remote_orders
JOIN catalog.schema.customer_profiles local_profiles
  ON remote_orders.customer_id = local_profiles.customer_id;
```
