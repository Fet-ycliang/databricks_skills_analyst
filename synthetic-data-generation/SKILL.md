---
name: synthetic-data-generation
description: "使用 Faker 和 Spark 生成逼真的合成資料，具有非線性分佈、完整性約束，並儲存到 Databricks。在建立測試資料、示範資料集或合成資料表時使用。"
---

# 合成資料生成

使用 Python 搭配 Faker 和 Spark 為 Databricks 生成逼真的、故事驅動的合成資料。

## 常用函式庫

這些函式庫對於生成逼真的合成資料很有用：

- **faker**：生成逼真的姓名、地址、電子郵件、公司、日期等
- **holidays**：提供特定國家的假日日曆以實現逼真的日期模式

這些通常**不會**預先安裝在 Databricks 上。使用 `execute_databricks_command` 工具安裝它們：
- `code`："%pip install faker holidays"

儲存返回的 `cluster_id` 和 `context_id` 以供後續呼叫使用。

## 工作流程

1. **將 Python 程式碼寫入專案中的本地檔案**（例如，`scripts/generate_data.py`）
2. **在 Databricks 上執行**，使用 `run_python_file_on_databricks` MCP 工具
3. **如果執行失敗**：編輯本地檔案以修復錯誤，然後重新執行
4. **重複使用上下文**以進行後續執行，透過傳遞返回的 `cluster_id` 和 `context_id`

**始終先處理本地檔案，然後執行。**這使除錯更容易 - 您可以看到和編輯程式碼。

### 上下文重複使用模式

第一次執行會自動選擇正在執行的叢集並建立執行上下文。**為後續呼叫重複使用此上下文** - 它更快（約 1 秒 vs 約 15 秒）並共享變數/匯入：

**第一次執行** - 使用 `run_python_file_on_databricks` 工具：
- `file_path`："scripts/generate_data.py"

返回：`{ success, output, error, cluster_id, context_id, ... }`

儲存 `cluster_id` 和 `context_id` 以供後續呼叫使用。

**如果執行失敗：**
1. 從結果中讀取錯誤
2. 編輯本地 Python 檔案以修復問題
3. 使用相同上下文重新執行，使用 `run_python_file_on_databricks` 工具：
   - `file_path`："scripts/generate_data.py"
   - `cluster_id`："<saved_cluster_id>"
   - `context_id`："<saved_context_id>"

**後續執行**重複使用上下文（更快，共享狀態）：
- `file_path`："scripts/validate_data.py"
- `cluster_id`："<saved_cluster_id>"
- `context_id`："<saved_context_id>"

### 處理失敗

當執行失敗時：
1. 從結果中讀取錯誤
2. **編輯本地 Python 檔案**以修復問題
3. 使用相同的 `cluster_id` 和 `context_id` 重新執行（更快，保留已安裝的函式庫）
4. 如果上下文損壞，省略 `context_id` 以建立新的上下文

### 安裝函式庫

Databricks 預設提供 Spark、pandas、numpy 和常見的資料函式庫。**僅在遇到匯入錯誤時才安裝函式庫。**

使用 `execute_databricks_command` 工具：
- `code`："%pip install faker"
- `cluster_id`："<cluster_id>"
- `context_id`："<context_id>"

函式庫在相同上下文中立即可用。

**注意：**保持相同的 `context_id` 意味著已安裝的函式庫會在呼叫之間持續存在。

## 儲存目的地

### 詢問結構描述名稱

預設使用 `ai_dev_kit` 目錄。詢問使用者要使用哪個結構描述：

> "我將把資料儲存到 `ai_dev_kit.<schema>`。您想使用什麼結構描述名稱？（如果需要，您也可以指定不同的目錄。）"

如果使用者只提供結構描述名稱，使用 `ai_dev_kit.{schema}`。如果他們提供 `catalog.schema`，則使用該名稱。

### 在腳本中建立基礎設施

始終**在 Python 腳本內**使用 `spark.sql()` 建立目錄、結構描述和磁碟區。不要進行單獨的 MCP SQL 呼叫 - 這樣慢得多。

`spark` 變數在 Databricks 叢集上預設可用。

```python
# =============================================================================
# 建立基礎設施（在 Python 腳本內）
# =============================================================================
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")
```

### 儲存到磁碟區作為原始資料（絕不直接儲存到資料表）

**始終將資料儲存到磁碟區作為 parquet 檔案，絕不直接儲存到資料表**（除非使用者明確要求資料表）。這是下游 Spark 宣告式管線（SDP）的輸入，該管線將處理 bronze/silver/gold 層。

```python
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

# 儲存為 parquet 檔案（原始資料）
spark.createDataFrame(customers_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/customers")
spark.createDataFrame(orders_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/orders")
spark.createDataFrame(tickets_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/tickets")
```

## 僅原始資料 - 無預先聚合欄位（除非另有指示）

**預設情況下，僅生成原始的交易資料。**不要建立代表總和、總計、平均值或計數的欄位。

- 一列 = 一個事件/交易/記錄
- 沒有像 `total_orders`、`sum_revenue`、`avg_csat`、`order_count` 這樣的欄位
- 每列都有自己的個別值，而非彙總

**為什麼？**Spark 宣告式管線（SDP）通常會在資料生成後建立，以：
- 擷取原始資料（bronze 層）
- 清理和驗證（silver 層）
- 聚合和計算指標（gold 層）

合成資料是此管線的**來源**。聚合發生在下游。

**注意：**如果使用者特別要求聚合欄位或摘要資料表，請遵循他們的指示。

```python
# 好 - 原始交易資料
# 客戶資料表：每個客戶一列，無聚合欄位
customers_data.append({
    "customer_id": cid,
    "name": fake.company(),
    "tier": "Enterprise",
    "region": "North",
})

# 訂單資料表：每個訂單一列
orders_data.append({
    "order_id": f"ORD-{i:06d}",
    "customer_id": cid,
    "amount": 150.00,  # 此訂單的金額
    "order_date": "2024-10-15",
})

# 不好 - 不要新增預先聚合的欄位
# customers_data.append({
#     "customer_id": cid,
#     "total_orders": 47,        # 否 - 這是聚合
#     "total_revenue": 12500.00, # 否 - 這是總和
#     "avg_order_value": 265.95, # 否 - 這是平均值
# })
```

## 時間性和資料量

### 日期範圍：從今天起過去 6 個月

**始終生成從當前日期結束的過去約 6 個月的資料。**這確保：
- 資料對示範來說感覺是最新和相關的
- 最近的模式在儀表板中可見
- 下游聚合（每日/每週/每月）有足夠的歷史記錄

```python
from datetime import datetime, timedelta

# 動態日期範圍 - 從今天起過去 6 個月
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# 在此範圍內放置特殊事件（例如，3 週前的事件）
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)
```

### 用於聚合的資料量

生成足夠的資料，以便在下游聚合後模式仍然可見（SDP 管線通常按日/週/地區/類別聚合）。經驗法則：

| 粒度 | 最少記錄數 | 理由 |
|-------|-----------------|-----------|
| 每日時間序列 | 每天 50-100 筆 | 在每週彙總後看到趨勢 |
| 每個類別 | 每個類別 500+ 筆 | 統計顯著性 |
| 每個客戶 | 每個客戶 5-20 個事件 | 足夠進行客戶層級分析 |
| 總列數 | 最少 10K-50K | 模式在 GROUP BY 後仍存在 |

```python
# 範例：180 天內 8000 張工單 = 平均每天約 44 張
# 每週聚合後：每週每個類別約 310 筆記錄
# 按地區每月聚合後：仍然足以看到模式
N_TICKETS = 8000
N_CUSTOMERS = 2500  # 每個平均約 3 張工單
N_ORDERS = 25000    # 每個客戶平均約 10 個訂單
```

## 腳本結構

始終在頂部使用配置變數來結構化腳本：

```python
"""為 [使用案例] 生成合成資料。"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
import holidays
from pyspark.sql import SparkSession

# =============================================================================
# 配置 - 編輯這些值
# =============================================================================
CATALOG = "my_catalog"
SCHEMA = "my_schema"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

# 資料大小 - 足夠讓聚合模式存在
N_CUSTOMERS = 2500
N_ORDERS = 25000
N_TICKETS = 8000

# 日期範圍 - 從今天起過去 6 個月
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# 特殊事件（在日期範圍內）
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)

# 用於逼真模式的假日日曆
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

# 可重現性
SEED = 42

# =============================================================================
# 設定
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
spark = SparkSession.builder.getOrCreate()

# ... 腳本的其餘部分
```

## 關鍵原則

### 1. 使用 Pandas 生成，Spark 儲存

使用 pandas 生成資料（更快、更容易），轉換為 Spark 以儲存：

```python
import pandas as pd

# 使用 pandas 生成
customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "name": [fake.company() for _ in range(N_CUSTOMERS)],
    "tier": np.random.choice(['Free', 'Pro', 'Enterprise'], N_CUSTOMERS, p=[0.6, 0.3, 0.1]),
    "region": np.random.choice(['North', 'South', 'East', 'West'], N_CUSTOMERS, p=[0.4, 0.25, 0.2, 0.15]),
    "created_at": [fake.date_between(start_date='-2y', end_date='-6m') for _ in range(N_CUSTOMERS)],
})

# 轉換為 Spark 並儲存
customers_df = spark.createDataFrame(customers_pdf)
customers_df.write.mode("overwrite").parquet(f"{VOLUME_PATH}/customers")
```

### 2. 迭代 DataFrame 以實現參照完整性

先生成主資料表，然後迭代它們以建立具有匹配 ID 的相關資料表：

```python
# 1. 生成客戶（主資料表）
customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "tier": np.random.choice(['Free', 'Pro', 'Enterprise'], N_CUSTOMERS, p=[0.6, 0.3, 0.1]),
    # ...
})

# 2. 建立用於外鍵生成的查找
customer_ids = customers_pdf["customer_id"].tolist()
customer_tier_map = dict(zip(customers_pdf["customer_id"], customers_pdf["tier"]))

# 按層級加權 - Enterprise 客戶生成更多訂單
tier_weights = customers_pdf["tier"].map({'Enterprise': 5.0, 'Pro': 2.0, 'Free': 1.0})
customer_weights = (tier_weights / tier_weights.sum()).tolist()

# 3. 使用有效外鍵和基於層級的邏輯生成訂單
orders_data = []
for i in range(N_ORDERS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    tier = customer_tier_map[cid]

    # 金額取決於層級
    if tier == 'Enterprise':
        amount = np.random.lognormal(7, 0.8)
    elif tier == 'Pro':
        amount = np.random.lognormal(5, 0.7)
    else:
        amount = np.random.lognormal(3.5, 0.6)

    orders_data.append({
        "order_id": f"ORD-{i:06d}",
        "customer_id": cid,
        "amount": round(amount, 2),
        "order_date": fake.date_between(start_date=START_DATE, end_date=END_DATE),
    })

orders_pdf = pd.DataFrame(orders_data)

# 4. 生成引用客戶和訂單的工單
order_ids = orders_pdf["order_id"].tolist()
tickets_data = []
for i in range(N_TICKETS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    oid = np.random.choice(order_ids)  # 或 None 表示一般查詢

    tickets_data.append({
        "ticket_id": f"TKT-{i:06d}",
        "customer_id": cid,
        "order_id": oid if np.random.random() > 0.3 else None,
        # ...
    })

tickets_pdf = pd.DataFrame(tickets_data)
```

### 3. 非線性分佈

**絕不使用均勻分佈** - 真實資料很少是均勻的：

```python
# 不好 - 均勻（不真實）
prices = np.random.uniform(10, 1000, size=N_ORDERS)

# 好 - 對數常態（對價格、薪資、訂單金額真實）
prices = np.random.lognormal(mean=4.5, sigma=0.8, size=N_ORDERS)

# 好 - Pareto/冪律（人氣、財富、頁面瀏覽量）
popularity = (np.random.pareto(a=2.5, size=N_PRODUCTS) + 1) * 10

# 好 - 指數（事件之間的時間、解決時間）
resolution_hours = np.random.exponential(scale=24, size=N_TICKETS)

# 好 - 加權分類
regions = np.random.choice(
    ['North', 'South', 'East', 'West'],
    size=N_CUSTOMERS,
    p=[0.40, 0.25, 0.20, 0.15]
)
```

### 4. 基於時間的模式

新增工作日/週末效應、假日、季節性和事件高峰：

```python
import holidays

# 載入假日日曆
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

def get_daily_multiplier(date):
    """計算給定日期的數量乘數。"""
    multiplier = 1.0

    # 週末下降
    if date.weekday() >= 5:
        multiplier *= 0.6

    # 假日下降（甚至低於週末）
    if date in US_HOLIDAYS:
        multiplier *= 0.3

    # Q4 季節性（10-12 月較高）
    multiplier *= 1 + 0.15 * (date.month - 6) / 6

    # 事件高峰
    if INCIDENT_START <= date <= INCIDENT_END:
        multiplier *= 3.0

    # 隨機雜訊
    multiplier *= np.random.normal(1, 0.1)

    return max(0.1, multiplier)

# 使用逼真模式在日期間分配工單
date_range = pd.date_range(START_DATE, END_DATE, freq='D')
daily_volumes = [int(BASE_DAILY_TICKETS * get_daily_multiplier(d)) for d in date_range]
```

### 5. 列連貫性

列內的屬性應該在邏輯上相關：

```python
def generate_ticket(customer_id, tier, date):
    """生成屬性相關的連貫工單。"""

    # 優先順序與層級相關
    if tier == 'Enterprise':
        priority = np.random.choice(['Critical', 'High', 'Medium'], p=[0.3, 0.5, 0.2])
    else:
        priority = np.random.choice(['Critical', 'High', 'Medium', 'Low'], p=[0.05, 0.2, 0.45, 0.3])

    # 解決時間與優先順序相關
    resolution_scale = {'Critical': 4, 'High': 12, 'Medium': 36, 'Low': 72}
    resolution_hours = np.random.exponential(scale=resolution_scale[priority])

    # CSAT 與解決時間相關
    if resolution_hours < 4:
        csat = np.random.choice([4, 5], p=[0.3, 0.7])
    elif resolution_hours < 24:
        csat = np.random.choice([3, 4, 5], p=[0.2, 0.5, 0.3])
    else:
        csat = np.random.choice([1, 2, 3, 4], p=[0.1, 0.3, 0.4, 0.2])

    return {
        "customer_id": customer_id,
        "priority": priority,
        "resolution_hours": round(resolution_hours, 1),
        "csat_score": csat,
        "created_at": date,
    }
```

## 完整範例

儲存為 `scripts/generate_data.py`：

```python
"""生成合成客戶、訂單和工單資料。"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
import holidays
from pyspark.sql import SparkSession

# =============================================================================
# 配置
# =============================================================================
CATALOG = "my_catalog"
SCHEMA = "my_schema"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

N_CUSTOMERS = 2500
N_ORDERS = 25000
N_TICKETS = 8000

# 日期範圍 - 從今天起過去 6 個月
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# 特殊事件（在日期範圍內）
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)

# 假日日曆
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

SEED = 42

# =============================================================================
# 設定
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
spark = SparkSession.builder.getOrCreate()

# =============================================================================
# 建立基礎設施
# =============================================================================
print(f"如果需要，建立目錄/結構描述/磁碟區...")
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")

print(f"生成：{N_CUSTOMERS:,} 個客戶、{N_ORDERS:,} 個訂單、{N_TICKETS:,} 張工單")

# =============================================================================
# 1. 客戶（主資料表）
# =============================================================================
print("生成客戶...")

customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "name": [fake.company() for _ in range(N_CUSTOMERS)],
    "tier": np.random.choice(['Free', 'Pro', 'Enterprise'], N_CUSTOMERS, p=[0.6, 0.3, 0.1]),
    "region": np.random.choice(['North', 'South', 'East', 'West'], N_CUSTOMERS, p=[0.4, 0.25, 0.2, 0.15]),
})

# ARR 與層級相關
customers_pdf["arr"] = customers_pdf["tier"].apply(
    lambda t: round(np.random.lognormal(11, 0.5), 2) if t == 'Enterprise'
              else round(np.random.lognormal(8, 0.6), 2) if t == 'Pro' else 0
)

# 用於外鍵的查找
customer_ids = customers_pdf["customer_id"].tolist()
customer_tier_map = dict(zip(customers_pdf["customer_id"], customers_pdf["tier"]))
tier_weights = customers_pdf["tier"].map({'Enterprise': 5.0, 'Pro': 2.0, 'Free': 1.0})
customer_weights = (tier_weights / tier_weights.sum()).tolist()

print(f"  已建立 {len(customers_pdf):,} 個客戶")

# =============================================================================
# 2. 訂單（引用客戶）
# =============================================================================
print("生成訂單...")

orders_data = []
for i in range(N_ORDERS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    tier = customer_tier_map[cid]
    amount = np.random.lognormal(7 if tier == 'Enterprise' else 5 if tier == 'Pro' else 3.5, 0.7)

    orders_data.append({
        "order_id": f"ORD-{i:06d}",
        "customer_id": cid,
        "amount": round(amount, 2),
        "status": np.random.choice(['completed', 'pending', 'cancelled'], p=[0.85, 0.10, 0.05]),
        "order_date": fake.date_between(start_date=START_DATE, end_date=END_DATE),
    })

orders_pdf = pd.DataFrame(orders_data)
print(f"  已建立 {len(orders_pdf):,} 個訂單")

# =============================================================================
# 3. 工單（引用客戶，帶有事件高峰）
# =============================================================================
print("生成工單...")

def get_daily_volume(date, base=25):
    vol = base * (0.6 if date.weekday() >= 5 else 1.0)
    if date in US_HOLIDAYS:
        vol *= 0.3  # 假日時更低
    if INCIDENT_START <= date <= INCIDENT_END:
        vol *= 3.0
    return int(vol * np.random.normal(1, 0.15))

# 在日期間分配工單
tickets_data = []
ticket_idx = 0
for day in pd.date_range(START_DATE, END_DATE):
    daily_count = get_daily_volume(day.to_pydatetime())
    is_incident = INCIDENT_START <= day.to_pydatetime() <= INCIDENT_END

    for _ in range(daily_count):
        if ticket_idx >= N_TICKETS:
            break

        cid = np.random.choice(customer_ids, p=customer_weights)
        tier = customer_tier_map[cid]

        # 類別 - 事件期間 Auth 佔主導
        if is_incident:
            category = np.random.choice(['Auth', 'Network', 'Billing', 'Account'], p=[0.65, 0.15, 0.1, 0.1])
        else:
            category = np.random.choice(['Auth', 'Network', 'Billing', 'Account'], p=[0.25, 0.30, 0.25, 0.20])

        # 優先順序與層級相關
        priority = np.random.choice(['Critical', 'High', 'Medium'], p=[0.3, 0.5, 0.2]) if tier == 'Enterprise' \
                   else np.random.choice(['Critical', 'High', 'Medium', 'Low'], p=[0.05, 0.2, 0.45, 0.3])

        # 解決時間與優先順序相關
        res_scale = {'Critical': 4, 'High': 12, 'Medium': 36, 'Low': 72}
        resolution = np.random.exponential(scale=res_scale[priority])

        # CSAT 在事件期間對 Auth 降級
        if is_incident and category == 'Auth':
            csat = np.random.choice([1, 2, 3, 4, 5], p=[0.15, 0.25, 0.35, 0.2, 0.05])
        else:
            csat = 5 if resolution < 4 else (4 if resolution < 12 else np.random.choice([2, 3, 4], p=[0.2, 0.5, 0.3]))

        tickets_data.append({
            "ticket_id": f"TKT-{ticket_idx:06d}",
            "customer_id": cid,
            "category": category,
            "priority": priority,
            "resolution_hours": round(resolution, 1),
            "csat_score": csat,
            "created_at": day.strftime("%Y-%m-%d"),
        })
        ticket_idx += 1

    if ticket_idx >= N_TICKETS:
        break

tickets_pdf = pd.DataFrame(tickets_data)
print(f"  已建立 {len(tickets_pdf):,} 張工單")

# =============================================================================
# 4. 儲存到磁碟區
# =============================================================================
print(f"\n儲存到 {VOLUME_PATH}...")

spark.createDataFrame(customers_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/customers")
spark.createDataFrame(orders_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/orders")
spark.createDataFrame(tickets_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/tickets")

print("完成！")

# =============================================================================
# 5. 驗證
# =============================================================================
print("\n=== 驗證 ===")
print(f"層級分佈：{customers_pdf['tier'].value_counts(normalize=True).to_dict()}")
print(f"按層級的平均訂單：{orders_pdf.merge(customers_pdf[['customer_id', 'tier']]).groupby('tier')['amount'].mean().to_dict()}")

incident_tickets = tickets_pdf[tickets_pdf['created_at'].between(
    INCIDENT_START.strftime("%Y-%m-%d"), INCIDENT_END.strftime("%Y-%m-%d")
)]
print(f"事件期間工單：{len(incident_tickets):,} ({len(incident_tickets)/len(tickets_pdf)*100:.1f}%)")
print(f"事件 Auth %：{(incident_tickets['category'] == 'Auth').mean()*100:.1f}%")
```

使用 `run_python_file_on_databricks` 工具執行：
- `file_path`："scripts/generate_data.py"

如果失敗，編輯檔案並使用相同的 `cluster_id` 和 `context_id` 重新執行。

### 驗證生成的資料

成功執行後，使用 `get_volume_folder_details` 工具驗證生成的資料：
- `volume_path`："my_catalog/my_schema/raw_data/customers"
- `format`："parquet"
- `table_stat_level`："SIMPLE"

這會返回結構描述、列數和欄位統計資訊，以確認資料已正確寫入。

## 最佳實踐

1. **詢問結構描述**：預設使用 `ai_dev_kit` 目錄，詢問使用者結構描述名稱
2. **建立基礎設施**：使用 `CREATE CATALOG/SCHEMA/VOLUME IF NOT EXISTS`
3. **僅原始資料**：無 `total_x`、`sum_x`、`avg_x` 欄位 - SDP 管線計算這些
4. **儲存到磁碟區，而非資料表**：將 parquet 寫入 `/Volumes/{catalog}/{schema}/raw_data/<input_datasource_name>`
5. **配置在頂部**：所有大小、日期和路徑作為變數
6. **動態日期**：使用 `datetime.now() - timedelta(days=180)` 表示過去 6 個月
7. **Pandas 用於生成**：比 Spark 更快、更容易進行逐列邏輯
8. **主資料表優先**：生成客戶，然後訂單引用 customer_ids
9. **加權取樣**：Enterprise 客戶生成更多活動
10. **分佈**：值使用對數常態，時間使用指數，加權分類
11. **時間模式**：工作日/週末、假日、季節性、事件高峰
12. **列連貫性**：優先順序影響解決時間影響 CSAT
13. **用於聚合的數量**：最少 10K-50K 列，以便模式在 GROUP BY 後仍存在
14. **始終使用檔案**：寫入本地檔案、執行、如果錯誤則編輯、重新執行
15. **上下文重複使用**：傳遞 `cluster_id` 和 `context_id` 以實現更快的迭代
16. **函式庫**：先安裝 `faker` 和 `holidays`；大多數其他函式庫都已預先安裝
