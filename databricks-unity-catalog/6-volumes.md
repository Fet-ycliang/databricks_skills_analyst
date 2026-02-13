# Unity Catalog 磁碟區

使用 Unity Catalog 磁碟區的完整參考：檔案操作、權限和最佳實踐。

## 概述

磁碟區是 Unity Catalog 用於存取、儲存和治理檔案的功能。與資料表（結構化資料）不同，磁碟區儲存非結構化或半結構化檔案。

| 磁碟區類型 | 說明 | 儲存 |
|-------------|-------------|---------|
| **託管** | Databricks 管理儲存位置 | 預設 metastore 位置 |
| **外部** | 您管理儲存位置 | 您的雲端儲存（S3、ADLS、GCS） |

**常見使用案例：**
- ML 訓練資料（影像、音訊、影片、PDF）
- 資料探索和暫存
- 程式庫檔案（.whl、.jar）
- 配置檔案和腳本
- ETL 登陸區

---

## 磁碟區路徑格式

所有磁碟區操作使用路徑格式：

```
/Volumes/<catalog>/<schema>/<volume>/<path_to_file>
```

**範例：**
```
/Volumes/main/default/my_volume/data.csv
/Volumes/analytics/raw/landing_zone/2024/01/orders.parquet
/Volumes/ml/training/images/cats/cat_001.jpg
```

---

## MCP 工具

### 列出磁碟區中的檔案

```python
# 列出檔案和目錄
list_volume_files(
    volume_path="/Volumes/main/default/my_volume/data/"
)
# 返回：[{"name": "file.csv", "path": "...", "is_directory": false, "file_size": 1024, "last_modified": "..."}]
```

### 上傳檔案到磁碟區

```python
# 上傳本地檔案
upload_to_volume(
    local_path="/tmp/data.csv",
    volume_path="/Volumes/main/default/my_volume/data.csv",
    overwrite=True
)
# 返回：{"local_path": "...", "volume_path": "...", "success": true}
```

### 從磁碟區下載檔案

```python
# 下載到本地路徑
download_from_volume(
    volume_path="/Volumes/main/default/my_volume/data.csv",
    local_path="/tmp/downloaded.csv",
    overwrite=True
)
# 返回：{"volume_path": "...", "local_path": "...", "success": true}
```

### 建立目錄

```python
# 建立目錄（像 mkdir -p 一樣建立父目錄）
create_volume_directory(
    volume_path="/Volumes/main/default/my_volume/data/2024/01"
)
# 返回：{"volume_path": "...", "success": true}
```

### 刪除檔案

```python
# 刪除檔案
delete_volume_file(
    volume_path="/Volumes/main/default/my_volume/old_data.csv"
)
# 返回：{"volume_path": "...", "success": true}
```

### 取得檔案資訊

```python
# 取得檔案中繼資料
get_volume_file_info(
    volume_path="/Volumes/main/default/my_volume/data.csv"
)
# 返回：{"name": "data.csv", "file_size": 1024, "last_modified": "...", "success": true}
```

---

## Python SDK 範例

### 磁碟區 CRUD 操作

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import VolumeType

w = WorkspaceClient()

# 列出結構描述中的磁碟區
for volume in w.volumes.list(catalog_name="main", schema_name="default"):
    print(f"{volume.full_name}: {volume.volume_type}")

# 取得磁碟區詳細資訊
volume = w.volumes.read(name="main.default.my_volume")
print(f"儲存：{volume.storage_location}")

# 建立託管磁碟區
managed = w.volumes.create(
    catalog_name="main",
    schema_name="default",
    name="my_managed_volume",
    volume_type=VolumeType.MANAGED,
    comment="ML 資料的託管磁碟區"
)

# 建立外部磁碟區
external = w.volumes.create(
    catalog_name="main",
    schema_name="default",
    name="my_external_volume",
    volume_type=VolumeType.EXTERNAL,
    storage_location="s3://my-bucket/volumes/data",
    comment="S3 上的外部磁碟區"
)

# 更新磁碟區
w.volumes.update(
    name="main.default.my_volume",
    comment="更新的說明"
)

# 刪除磁碟區
w.volumes.delete(name="main.default.my_volume")
```

### 檔案操作

```python
from databricks.sdk import WorkspaceClient
import io

w = WorkspaceClient()

# 從記憶體上傳檔案
data = b"col1,col2\n1,2\n3,4"
w.files.upload(
    file_path="/Volumes/main/default/my_volume/data.csv",
    contents=io.BytesIO(data),
    overwrite=True
)

# 從磁碟上傳檔案（建議用於大型檔案）
w.files.upload_from(
    file_path="/Volumes/main/default/my_volume/large_file.parquet",
    source_path="/local/path/large_file.parquet",
    overwrite=True,
    use_parallel=True  # 大型檔案的平行上傳
)

# 列出目錄內容
for entry in w.files.list_directory_contents("/Volumes/main/default/my_volume/"):
    file_type = "目錄" if entry.is_directory else "檔案"
    print(f"{entry.name}: {file_type} ({entry.file_size} 位元組)")

# 下載檔案到記憶體
response = w.files.download("/Volumes/main/default/my_volume/data.csv")
content = response.contents.read()

# 下載檔案到磁碟（建議用於大型檔案）
w.files.download_to(
    file_path="/Volumes/main/default/my_volume/large_file.parquet",
    destination="/local/path/downloaded.parquet",
    use_parallel=True  # 大型檔案的平行下載
)

# 建立目錄
w.files.create_directory("/Volumes/main/default/my_volume/new_folder/")

# 刪除檔案
w.files.delete("/Volumes/main/default/my_volume/old_data.csv")

# 刪除空目錄
w.files.delete_directory("/Volumes/main/default/my_volume/empty_folder/")

# 取得檔案中繼資料
metadata = w.files.get_metadata("/Volumes/main/default/my_volume/data.csv")
print(f"大小：{metadata.content_length}，修改時間：{metadata.last_modified}")
```

---

## SQL 操作

### 查詢磁碟區中繼資料

```sql
-- 列出目錄中的所有磁碟區
SELECT
    volume_catalog,
    volume_schema,
    volume_name,
    volume_type,
    storage_location,
    comment,
    created,
    created_by
FROM system.information_schema.volumes
WHERE volume_catalog = 'analytics'
ORDER BY volume_schema, volume_name;

-- 按類型尋找磁碟區
SELECT volume_name, storage_location
FROM system.information_schema.volumes
WHERE volume_type = 'EXTERNAL';
```

### 從磁碟區讀取檔案

```sql
-- 讀取 CSV 檔案
SELECT * FROM read_files('/Volumes/main/default/my_volume/data.csv');

-- 使用選項讀取
SELECT * FROM read_files(
    '/Volumes/main/default/my_volume/data/',
    format => 'csv',
    header => true,
    inferSchema => true
);

-- 讀取 Parquet 檔案
SELECT * FROM read_files(
    '/Volumes/main/default/my_volume/parquet_data/',
    format => 'parquet'
);

-- 讀取 JSON 檔案
SELECT * FROM read_files(
    '/Volumes/main/default/my_volume/events/*.json',
    format => 'json'
);

-- 從磁碟區檔案建立資料表
CREATE TABLE analytics.bronze.raw_orders AS
SELECT * FROM read_files('/Volumes/analytics/raw/landing/orders/');
```

### 將檔案寫入磁碟區

```sql
-- 將資料複製到磁碟區為 Parquet
COPY INTO '/Volumes/main/default/my_volume/export/'
FROM (SELECT * FROM analytics.gold.customers)
FILEFORMAT = PARQUET;

-- 匯出為 CSV
COPY INTO '/Volumes/main/default/my_volume/export/'
FROM (SELECT * FROM analytics.gold.report)
FILEFORMAT = CSV
HEADER = true;
```

---

## 權限

### 所需權限

| 操作 | 所需權限 |
|-----------|-------------------|
| 列出檔案 | `READ VOLUME` |
| 讀取檔案 | `READ VOLUME` |
| 寫入檔案 | `WRITE VOLUME` |
| 建立磁碟區 | 結構描述上的 `CREATE VOLUME` |
| 刪除磁碟區 | 擁有者或 `MANAGE` |

**注意：**還需要父目錄上的 `USE CATALOG` 和父結構描述上的 `USE SCHEMA`。

### 授予權限

```sql
-- 授予磁碟區的讀取存取權限
GRANT READ VOLUME ON VOLUME main.default.my_volume TO `data_readers`;

-- 授予寫入存取權限
GRANT WRITE VOLUME ON VOLUME main.default.my_volume TO `data_writers`;

-- 授予在結構描述中建立磁碟區的能力
GRANT CREATE VOLUME ON SCHEMA main.default TO `data_engineers`;

-- 撤銷存取權限
REVOKE WRITE VOLUME ON VOLUME main.default.my_volume FROM `data_writers`;
```

### Python SDK 權限

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import SecurableType, PermissionsChange, Privilege

w = WorkspaceClient()

# 授予權限
w.grants.update(
    securable_type=SecurableType.VOLUME,
    full_name="main.default.my_volume",
    changes=[
        PermissionsChange(
            add=[Privilege.READ_VOLUME],
            principal="data_readers"
        )
    ]
)

# 取得目前權限
grants = w.grants.get(
    securable_type=SecurableType.VOLUME,
    full_name="main.default.my_volume"
)
for grant in grants.privilege_assignments:
    print(f"{grant.principal}: {grant.privileges}")
```

---

## 最佳實踐

### 組織

1. **使用有意義的路徑** - 按日期、來源或類型組織
   ```
   /Volumes/catalog/schema/volume/year=2024/month=01/file.parquet
   /Volumes/catalog/schema/volume/source=salesforce/accounts.csv
   ```

2. **分離原始和處理過的資料** - 對登陸區和精選資料使用不同的磁碟區
   ```
   /Volumes/analytics/raw/landing_zone/    # 原始上傳
   /Volumes/analytics/curated/processed/   # 清理後的資料
   ```

3. **封存舊資料** - 將不常存取的檔案移至封存磁碟區

### 效能

1. **對大型檔案使用平行上傳**（SDK v0.72.0+）
   ```python
   w.files.upload_from(..., use_parallel=True)
   ```

2. **批次處理小檔案** - 將許多小檔案合併為較大的封存檔

3. **對分析使用 Parquet** - 列式格式更有效率

4. **按日期分割** - 在查詢中實現有效的修剪

### 安全性

1. **當 Databricks 應該控制儲存時使用託管磁碟區**

2. **當您需要以下情況時使用外部磁碟區：**
   - 雲端儲存中的現有資料
   - 跨工作區存取
   - 自訂保留政策

3. **套用最小權限** - 僅授予所需權限

4. **稽核存取** - 在稽核日誌中監控磁碟區存取
   ```sql
   SELECT *
   FROM system.access.audit
   WHERE action_name LIKE '%Volume%'
     AND event_date >= current_date() - 7;
   ```

---

## 疑難排解

### 常見錯誤

| 錯誤 | 原因 | 解決方案 |
|-------|-------|----------|
| `PERMISSION_DENIED` | 缺少磁碟區權限 | 授予 `READ VOLUME` 或 `WRITE VOLUME` |
| `NOT_FOUND` | 磁碟區或路徑不存在 | 檢查路徑拼寫，確保磁碟區存在 |
| `ALREADY_EXISTS` | 檔案存在，overwrite=False | 設定 `overwrite=True` 或先刪除 |
| `RESOURCE_DOES_NOT_EXIST` | 父目錄不存在 | 先建立父目錄 |
| `INVALID_PARAMETER_VALUE` | 無效的路徑格式 | 使用 `/Volumes/catalog/schema/volume/path` 格式 |

### 除錯檢查清單

1. **驗證磁碟區存在：**
   ```sql
   SELECT * FROM system.information_schema.volumes
   WHERE volume_name = 'my_volume';
   ```

2. **檢查權限：**
   ```python
   grants = w.grants.get(
       securable_type=SecurableType.VOLUME,
       full_name="catalog.schema.volume"
   )
   ```

3. **驗證路徑格式：**
   - 必須以 `/Volumes/` 開頭
   - 三層命名空間：`catalog/schema/volume`
   - 沒有雙斜線（`//`）

4. **檢查檔案是否存在：**
   ```python
   try:
       w.files.get_metadata("/Volumes/catalog/schema/volume/file.csv")
   except Exception as e:
       print(f"找不到檔案：{e}")
   ```

### 外部磁碟區問題

1. **需要儲存憑證** - 外部磁碟區需要儲存憑證
   ```python
   # 先建立儲存憑證
   w.storage_credentials.create(
       name="my_s3_cred",
       aws_iam_role={"role_arn": "arn:aws:iam::..."}
   )
   
   # 建立外部位置
   w.external_locations.create(
       name="my_s3_location",
       url="s3://my-bucket/path",
       credential_name="my_s3_cred"
   )
   
   # 然後建立外部磁碟區
   w.volumes.create(
       ...
       volume_type=VolumeType.EXTERNAL,
       storage_location="s3://my-bucket/path/volume"
   )
   ```

2. **網路存取** - 確保工作區可以連接到雲端儲存

3. **IAM 權限** - 驗證 IAM 角色具有儲存桶存取權限
