# Databricks SQL 中的地理空間 SQL 和定序

---

## 第一部分：地理空間 SQL

Databricks SQL 透過兩個函數系列提供全面的地理空間支援：用於六邊形網格索引的 **H3 函數**和用於標準空間操作的 **ST 函數**。它們共同實現大規模的高效能地理空間分析。

### 地理空間資料類型

| 類型 | 說明 | 座標系統 | SRID 支援 |
|------|-------------|-------------------|--------------|
| `GEOMETRY` | 使用歐幾里得座標（X、Y、選用 Z）的空間物件 -- 將地球視為平面 | 任何投影 CRS | 11,000+ 個 SRID |
| `GEOGRAPHY` | 使用經度/緯度的地球表面地理物件 | WGS 84 | 僅 SRID 4326 |

**何時使用哪種：**
- 對投影座標系統、歐幾里得距離計算，以及使用公尺或英尺處理本地/區域資料時，使用 `GEOMETRY`。
- 對使用經度/緯度座標的全球資料和球面距離計算，使用 `GEOGRAPHY`。

### 支援的幾何子類型

`GEOMETRY` 和 `GEOGRAPHY` 都支援：**Point**、**LineString**、**Polygon**、**MultiPoint**、**MultiLineString**、**MultiPolygon** 和 **GeometryCollection**。

### 格式支援

| 格式 | 說明 | 匯入函數 | 匯出函數 |
|--------|-------------|-----------------|-----------------|
| WKT | Well-Known Text | `ST_GeomFromWKT`、`ST_GeogFromWKT` | `ST_AsWKT`、`ST_AsText` |
| WKB | Well-Known Binary | `ST_GeomFromWKB`、`ST_GeogFromWKB` | `ST_AsWKB`、`ST_AsBinary` |
| EWKT | Extended WKT（包含 SRID） | `ST_GeomFromEWKT`、`ST_GeogFromEWKT` | `ST_AsEWKT` |
| EWKB | Extended WKB（包含 SRID） | `ST_GeomFromEWKB` | `ST_AsEWKB` |
| GeoJSON | 基於 JSON 的格式 | `ST_GeomFromGeoJSON`、`ST_GeogFromGeoJSON` | `ST_AsGeoJSON` |
| Geohash | 階層式網格編碼 | `ST_GeomFromGeoHash`、`ST_PointFromGeoHash` | `ST_GeoHash` |

---

### H3 地理空間函數

H3 是 Uber 的六邊形階層式空間索引。它將地球劃分為 16 個解析度（0-15）的六邊形單元。自 Databricks Runtime 11.2（H3 Java 函式庫 3.7.0）起可用。無需單獨安裝。

#### H3 匯入函數（座標/幾何到 H3）

| 函數 | 說明 | 返回 |
|----------|-------------|---------|
| `h3_longlatash3(lon, lat, resolution)` | 將經度/緯度轉換為 H3 單元 ID | `BIGINT` |
| `h3_longlatash3string(lon, lat, resolution)` | 將經度/緯度轉換為 H3 單元 ID | `STRING`（十六進位） |
| `h3_pointash3(geogExpr, resolution)` | 將 GEOGRAPHY 點轉換為 H3 單元 ID | `BIGINT` |
| `h3_pointash3string(geogExpr, resolution)` | 將 GEOGRAPHY 點轉換為 H3 單元 ID | `STRING`（十六進位） |
| `h3_polyfillash3(geogExpr, resolution)` | 用包含的 H3 單元填充多邊形 | `ARRAY<BIGINT>` |
| `h3_polyfillash3string(geogExpr, resolution)` | 用包含的 H3 單元填充多邊形 | `ARRAY<STRING>` |
| `h3_coverash3(geogExpr, resolution)` | 用最小 H3 單元集覆蓋地理區域 | `ARRAY<BIGINT>` |
| `h3_coverash3string(geogExpr, resolution)` | 用最小 H3 單元集覆蓋地理區域 | `ARRAY<STRING>` |
| `h3_tessellateaswkb(geogExpr, resolution)` | 使用 H3 單元鑲嵌地理區域 | `ARRAY<STRUCT>` |
| `h3_try_polyfillash3(geogExpr, resolution)` | 安全的 polyfill（錯誤時返回 NULL） | `ARRAY<BIGINT>` |
| `h3_try_polyfillash3string(geogExpr, resolution)` | 安全的 polyfill（錯誤時返回 NULL） | `ARRAY<STRING>` |
| `h3_try_coverash3(geogExpr, resolution)` | 安全的 cover（錯誤時返回 NULL） | `ARRAY<BIGINT>` |
| `h3_try_coverash3string(geogExpr, resolution)` | 安全的 cover（錯誤時返回 NULL） | `ARRAY<STRING>` |
| `h3_try_tessellateaswkb(geogExpr, resolution)` | 安全的 tessellate（錯誤時返回 NULL） | `ARRAY<STRUCT>` |

#### H3 匯出函數（H3 到幾何/格式）

| 函數 | 說明 | 返回 |
|----------|-------------|---------|
| `h3_boundaryaswkt(h3CellId)` | H3 單元邊界作為 WKT 多邊形 | `STRING` |
| `h3_boundaryaswkb(h3CellId)` | H3 單元邊界作為 WKB 多邊形 | `BINARY` |
| `h3_boundaryasgeojson(h3CellId)` | H3 單元邊界作為 GeoJSON | `STRING` |
| `h3_centeraswkt(h3CellId)` | H3 單元中心作為 WKT 點 | `STRING` |
| `h3_centeraswkb(h3CellId)` | H3 單元中心作為 WKB 點 | `BINARY` |
| `h3_centerasgeojson(h3CellId)` | H3 單元中心作為 GeoJSON 點 | `STRING` |

#### H3 轉換函數

| 函數 | 說明 |
|----------|-------------|
| `h3_h3tostring(h3CellId)` | 將 BIGINT 單元 ID 轉換為十六進位 STRING |
| `h3_stringtoh3(h3CellIdString)` | 將十六進位 STRING 轉換為 BIGINT 單元 ID |

#### H3 階層/遍歷函數

| 函數 | 說明 |
|----------|-------------|
| `h3_resolution(h3CellId)` | 取得單元的解析度 |
| `h3_toparent(h3CellId, resolution)` | 取得較粗解析度的父單元 |
| `h3_tochildren(h3CellId, resolution)` | 取得較細解析度的所有子單元 |
| `h3_maxchild(h3CellId, resolution)` | 取得具有最大值的子單元 |
| `h3_minchild(h3CellId, resolution)` | 取得具有最小值的子單元 |
| `h3_ischildof(h3CellId1, h3CellId2)` | 測試 cell1 是否等於或為 cell2 的子單元 |

#### H3 距離/鄰居函數

| 函數 | 說明 |
|----------|-------------|
| `h3_distance(h3CellId1, h3CellId2)` | 兩個單元之間的網格距離 |
| `h3_try_distance(h3CellId1, h3CellId2)` | 網格距離，如果未定義則為 NULL |
| `h3_kring(h3CellId, k)` | 網格距離 k 內的所有單元（填充圓盤） |
| `h3_kringdistances(h3CellId, k)` | 距離 k 內的單元及其距離 |
| `h3_hexring(h3CellId, k)` | 恰好在距離 k 處的空心單元環 |

#### H3 壓縮函數

| 函數 | 說明 |
|----------|-------------|
| `h3_compact(h3CellIds)` | 將單元陣列壓縮為最小表示 |
| `h3_uncompact(h3CellIds, resolution)` | 將壓縮的單元擴展到目標解析度 |

#### H3 驗證函數

| 函數 | 說明 |
|----------|-------------|
| `h3_isvalid(expr)` | 檢查 BIGINT 或 STRING 是否為有效的 H3 單元 |
| `h3_validate(h3CellId)` | 如果有效則返回單元 ID，否則錯誤 |
| `h3_try_validate(h3CellId)` | 如果有效則返回單元 ID，否則返回 NULL |
| `h3_ispentagon(h3CellId)` | 檢查單元是否為五邊形（每個解析度 12 個） |

#### H3 範例

```sql
-- 將座標轉換為解析度 9 的 H3 單元
SELECT h3_longlatash3(-73.985428, 40.748817, 9) AS h3_cell;

-- 按上車位置索引計程車行程
CREATE TABLE trips_h3 AS
SELECT
  h3_longlatash3(pickup_longitude, pickup_latitude, 12) AS pickup_cell,
  h3_longlatash3(dropoff_longitude, dropoff_latitude, 12) AS dropoff_cell,
  *
FROM taxi_trips;

-- 用 H3 單元填充郵遞區號多邊形以進行空間索引
CREATE TABLE zipcode_h3 AS
SELECT
  explode(h3_polyfillash3(geom_wkt, 12)) AS cell,
  zipcode, city, state
FROM zipcodes;

-- 使用 H3 連接尋找在特定郵遞區號上車的所有行程
SELECT t.*
FROM trips_h3 t
INNER JOIN zipcode_h3 z ON t.pickup_cell = z.cell
WHERE z.zipcode = '10001';

-- 鄰近搜尋：尋找位置 2 環內的所有 H3 單元
SELECT explode(h3_kring(h3_longlatash3(-73.985, 40.748, 9), 2)) AS nearby_cell;

-- 聚合行程計數並取得質心以進行視覺化
SELECT
  dropoff_cell,
  h3_centerasgeojson(dropoff_cell):coordinates[0] AS lon,
  h3_centerasgeojson(dropoff_cell):coordinates[1] AS lat,
  count(*) AS trip_count
FROM trips_h3
GROUP BY dropoff_cell;

-- 匯總到較粗解析度
SELECT
  h3_toparent(pickup_cell, 7) AS parent_cell,
  count(*) AS trip_count
FROM trips_h3
GROUP BY h3_toparent(pickup_cell, 7);

-- 壓縮一組單元以實現高效儲存
SELECT h3_compact(collect_set(cell)) AS compacted
FROM zipcode_h3
WHERE zipcode = '10001';
```

---

### ST 地理空間函數

在 `GEOMETRY` 和 `GEOGRAPHY` 類型上操作的原生空間 SQL 函數。需要 Databricks Runtime 17.1+。公開預覽版。提供超過 80 個函數。

#### ST 匯入函數（建立幾何/地理）

| 函數 | 說明 | 輸出類型 |
|----------|-------------|-------------|
| `ST_GeomFromText(wkt [, srid])` | 從 WKT 建立 GEOMETRY | `GEOMETRY` |
| `ST_GeomFromWKT(wkt [, srid])` | 從 WKT 建立 GEOMETRY（別名） | `GEOMETRY` |
| `ST_GeomFromWKB(wkb [, srid])` | 從 WKB 建立 GEOMETRY | `GEOMETRY` |
| `ST_GeomFromEWKT(ewkt)` | 從 Extended WKT 建立 GEOMETRY | `GEOMETRY` |
| `ST_GeomFromEWKB(ewkb)` | 從 Extended WKB 建立 GEOMETRY | `GEOMETRY` |
| `ST_GeomFromGeoJSON(geojson)` | 從 GeoJSON 建立 GEOMETRY(4326) | `GEOMETRY` |
| `ST_GeomFromGeoHash(geohash)` | 從 geohash 建立多邊形 GEOMETRY | `GEOMETRY` |
| `ST_GeogFromText(wkt)` | 從 WKT 建立 GEOGRAPHY(4326) | `GEOGRAPHY` |
| `ST_GeogFromWKT(wkt)` | 從 WKT 建立 GEOGRAPHY(4326) | `GEOGRAPHY` |
| `ST_GeogFromWKB(wkb)` | 從 WKB 建立 GEOGRAPHY(4326) | `GEOGRAPHY` |
| `ST_GeogFromEWKT(ewkt)` | 從 Extended WKT 建立 GEOGRAPHY | `GEOGRAPHY` |
| `ST_GeogFromGeoJSON(geojson)` | 從 GeoJSON 建立 GEOGRAPHY(4326) | `GEOGRAPHY` |
| `ST_Point(x, y [, srid])` | 從座標建立點 | `GEOMETRY` |
| `ST_PointFromGeoHash(geohash)` | 從 geohash 中心建立點 | `GEOMETRY` |
| `to_geometry(georepExpr)` | 自動偵測格式並建立 GEOMETRY | `GEOMETRY` |
| `to_geography(georepExpr)` | 自動偵測格式並建立 GEOGRAPHY | `GEOGRAPHY` |
| `try_to_geometry(georepExpr)` | 安全的幾何建立（錯誤時返回 NULL） | `GEOMETRY` |
| `try_to_geography(georepExpr)` | 安全的地理建立（錯誤時返回 NULL） | `GEOGRAPHY` |

#### ST 匯出函數

| 函數 | 說明 | 輸出 |
|----------|-------------|--------|
| `ST_AsText(geo)` | 匯出為 WKT | `STRING` |
| `ST_AsWKT(geo)` | 匯出為 WKT（別名） | `STRING` |
| `ST_AsBinary(geo)` | 匯出為 WKB | `BINARY` |
| `ST_AsWKB(geo)` | 匯出為 WKB（別名） | `BINARY` |
| `ST_AsEWKT(geo)` | 匯出為 Extended WKT | `STRING` |
| `ST_AsEWKB(geo)` | 匯出為 Extended WKB | `BINARY` |
| `ST_AsGeoJSON(geo)` | 匯出為 GeoJSON | `STRING` |
| `ST_GeoHash(geo)` | 匯出為 geohash 字串 | `STRING` |

#### ST 建構函數

| 函數 | 說明 |
|----------|-------------|
| `ST_Point(x, y [, srid])` | 建立點幾何 |
| `ST_MakeLine(pointArray)` | 從點陣列建立線串 |
| `ST_MakePolygon(outer [, innerArray])` | 從外環和選用孔洞建立多邊形 |

#### ST 存取器函數

| 函數 | 說明 | 返回 |
|----------|-------------|---------|
| `ST_X(geo)` | 點的 X 座標 | `DOUBLE` |
| `ST_Y(geo)` | 點的 Y 座標 | `DOUBLE` |
| `ST_Z(geo)` | 點的 Z 座標 | `DOUBLE` |
| `ST_M(geo)` | 點的 M 座標 | `DOUBLE` |
| `ST_XMin(geo)` | 邊界框的最小 X | `DOUBLE` |
| `ST_XMax(geo)` | 邊界框的最大 X | `DOUBLE` |
| `ST_YMin(geo)` | 邊界框的最小 Y | `DOUBLE` |
| `ST_YMax(geo)` | 邊界框的最大 Y | `DOUBLE` |
| `ST_ZMin(geo)` | 最小 Z 座標 | `DOUBLE` |
| `ST_ZMax(geo)` | 最大 Z 座標 | `DOUBLE` |
| `ST_Dimension(geo)` | 拓撲維度（0=點，1=線，2=多邊形） | `INT` |
| `ST_NDims(geo)` | 座標維度數量 | `INT` |
| `ST_NPoints(geo)` | 點的總數 | `INT` |
| `ST_NumGeometries(geo)` | 集合中的幾何數量 | `INT` |
| `ST_NumInteriorRings(geo)` | 內環數量（多邊形） | `INT` |
| `ST_GeometryType(geo)` | 幾何類型作為字串 | `STRING` |
| `ST_GeometryN(geo, n)` | 集合中的第 N 個幾何（從 1 開始） | `GEOMETRY` |
| `ST_PointN(geo, n)` | 線串中的第 N 個點 | `GEOMETRY` |
| `ST_StartPoint(geo)` | 線串的第一個點 | `GEOMETRY` |
| `ST_EndPoint(geo)` | 線串的最後一個點 | `GEOMETRY` |
| `ST_ExteriorRing(geo)` | 多邊形的外環 | `GEOMETRY` |
| `ST_InteriorRingN(geo, n)` | 多邊形的第 N 個內環 | `GEOMETRY` |
| `ST_Envelope(geo)` | 最小邊界矩形 | `GEOMETRY` |
| `ST_Envelope_Agg(geo)` | 聚合：所有幾何的邊界框 | `GEOMETRY` |
| `ST_Dump(geo)` | 將多幾何展開為單一幾何陣列 | `ARRAY` |
| `ST_IsEmpty(geo)` | 如果幾何沒有點則為 True | `BOOLEAN` |

#### ST 測量函數

| 函數 | 說明 |
|----------|-------------|
| `ST_Area(geo)` | 多邊形的面積（以 CRS 單位） |
| `ST_Length(geo)` | 線串的長度（以 CRS 單位） |
| `ST_Perimeter(geo)` | 多邊形的周長（以 CRS 單位） |
| `ST_Distance(geo1, geo2)` | 幾何之間的笛卡爾距離 |
| `ST_DistanceSphere(geo1, geo2)` | 球面距離（公尺）（快速、近似） |
| `ST_DistanceSpheroid(geo1, geo2)` | WGS84 上的大地測量距離（公尺）（精確） |
| `ST_Azimuth(geo1, geo2)` | 基於北方的方位角（弧度） |
| `ST_ClosestPoint(geo1, geo2)` | geo1 上最接近 geo2 的點 |

#### ST 拓撲關係函數（謂詞）

| 函數 | 說明 |
|----------|-------------|
| `ST_Contains(geo1, geo2)` | 如果 geo1 完全包含 geo2 則為 True |
| `ST_Within(geo1, geo2)` | 如果 geo1 完全在 geo2 內則為 True（Contains 的反向） |
| `ST_Intersects(geo1, geo2)` | 如果幾何共享任何空間則為 True |
| `ST_Disjoint(geo1, geo2)` | 如果幾何不共享空間則為 True |
| `ST_Touches(geo1, geo2)` | 如果邊界接觸但內部不接觸則為 True |
| `ST_Covers(geo1, geo2)` | 如果 geo1 覆蓋 geo2（geo2 的點都不在外部）則為 True |
| `ST_Equals(geo1, geo2)` | 如果幾何在拓撲上相等則為 True |
| `ST_DWithin(geo1, geo2, distance)` | 如果幾何在給定距離內則為 True |

#### ST 覆蓋函數（集合操作）

| 函數 | 說明 |
|----------|-------------|
| `ST_Intersection(geo1, geo2)` | 共享空間的幾何 |
| `ST_Union(geo1, geo2)` | 組合兩個輸入的幾何 |
| `ST_Union_Agg(geo)` | 聚合：欄位中所有幾何的聯集 |
| `ST_Difference(geo1, geo2)` | geo1 減去 geo2 的幾何 |

#### ST 處理函數

| 函數 | 說明 |
|----------|-------------|
| `ST_Buffer(geo, radius)` | 按半徑距離擴展幾何 |
| `ST_Centroid(geo)` | 幾何的中心點 |
| `ST_ConvexHull(geo)` | 包含幾何的最小凸多邊形 |
| `ST_ConcaveHull(geo, ratio [, allowHoles])` | 具有長度比的凹包 |
| `ST_Boundary(geo)` | 幾何的邊界（並非所有 SQL Warehouse 版本都可用） |
| `ST_Simplify(geo, tolerance)` | 使用 Douglas-Peucker 演算法簡化 |

#### ST 編輯器函數

| 函數 | 說明 |
|----------|-------------|
| `ST_AddPoint(linestring, point [, index])` | 將點新增到線串 |
| `ST_RemovePoint(linestring, index)` | 從線串移除點 |
| `ST_SetPoint(linestring, index, point)` | 替換線串中的點 |
| `ST_FlipCoordinates(geo)` | 交換 X 和 Y 座標 |
| `ST_Multi(geo)` | 將單一幾何轉換為多幾何 |
| `ST_Reverse(geo)` | 反轉頂點順序 |

#### ST 仿射變換函數

| 函數 | 說明 |
|----------|-------------|
| `ST_Translate(geo, xOffset, yOffset [, zOffset])` | 按偏移量移動幾何 |
| `ST_Scale(geo, xFactor, yFactor [, zFactor])` | 按因子縮放幾何 |
| `ST_Rotate(geo, angle)` | 圍繞原點旋轉幾何（弧度） |

#### ST 空間參考系統函數

| 函數 | 說明 |
|----------|-------------|
| `ST_SRID(geo)` | 取得幾何的 SRID |
| `ST_SetSRID(geo, srid)` | 設定 SRID 值（無重新投影） |
| `ST_Transform(geo, targetSrid)` | 重新投影到目標座標系統 |

#### ST 驗證

| 函數 | 說明 |
|----------|-------------|
| `ST_IsValid(geo)` | 檢查幾何是否符合 OGC 標準 |

#### ST 實用範例

> **注意：**`CREATE TABLE` 中的 `GEOMETRY` 和 `GEOGRAPHY` 欄位類型需要 DBR 17.1+ 的無伺服器運算。在不支援這些欄位類型的 SQL Warehouse 上，使用帶有 WKT 表示的 `STRING` 欄位，並在查詢時使用 `ST_GeomFromText()` / `ST_GeogFromText()` 進行轉換。

```sql
-- 建立帶有幾何欄位的資料表（需要無伺服器 DBR 17.1+）
CREATE TABLE retail_stores (
  store_id INT,
  name STRING,
  location GEOMETRY
);

INSERT INTO retail_stores VALUES
  (1, 'Downtown Store', ST_Point(-73.9857, 40.7484, 4326)),
  (2, 'Midtown Store',  ST_Point(-73.9787, 40.7614, 4326)),
  (3, 'Uptown Store',   ST_Point(-73.9680, 40.7831, 4326));

-- 建立配送區域作為多邊形
CREATE TABLE delivery_zones (
  zone_id INT,
  zone_name STRING,
  boundary GEOMETRY
);

INSERT INTO delivery_zones VALUES
  (1, 'Zone A', ST_GeomFromText(
    'POLYGON((-74.00 40.74, -73.97 40.74, -73.97 40.76, -74.00 40.76, -74.00 40.74))', 4326
  ));

-- 點在多邊形內：尋找配送區域內的商店
SELECT s.name, z.zone_name
FROM retail_stores s
JOIN delivery_zones z
  ON ST_Contains(z.boundary, s.location);

-- 距離計算：尋找商店 5 公里內的客戶
-- 注意：to_geography() 期望 STRING（WKT/GeoJSON）或 BINARY（WKB）輸入，而非 GEOMETRY。
-- 首先使用 ST_AsText() 將 GEOMETRY 轉換為 WKT。
SELECT c.customer_id, c.name,
  ST_DistanceSphere(c.location, s.location) AS distance_meters
FROM customers c
CROSS JOIN retail_stores s
WHERE s.store_id = 1
  AND ST_DWithin(
    ST_GeogFromText(ST_AsText(c.location)),
    ST_GeogFromText(ST_AsText(s.location)),
    5000  -- 5 公里（公尺）
  );

-- 緩衝區：在商店周圍建立 1 公里緩衝區（使用投影 CRS 以公尺為單位）
SELECT ST_Buffer(
  ST_Transform(location, 5070),  -- 投影到 NAD83/Albers（公尺）
  1000                            -- 1000 公尺
) AS buffer_zone
FROM retail_stores
WHERE store_id = 1;

-- 面積計算
SELECT zone_name,
  ST_Area(ST_Transform(boundary, 5070)) AS area_sq_meters
FROM delivery_zones;

-- 重疊區域的聯集
SELECT ST_Union_Agg(boundary) AS combined_coverage
FROM delivery_zones;

-- 格式之間的轉換
SELECT
  ST_AsText(location) AS wkt,
  ST_AsGeoJSON(location) AS geojson,
  ST_GeoHash(location) AS geohash
FROM retail_stores;

-- 使用 BROADCAST 提示進行效能優化的空間連接
SELECT /*+ BROADCAST(zones) */
  c.customer_id, z.zone_name
FROM customers c
JOIN delivery_zones zones
  ON ST_Contains(zones.boundary, c.location);
```

### 結合 H3 和 ST 函數

```sql
-- 使用 H3 進行快速預篩選，然後使用 ST 進行精確空間操作
-- 步驟 1：使用 H3 索引商店位置
CREATE TABLE store_h3 AS
SELECT store_id, name, location,
  h3_longlatash3(ST_X(location), ST_Y(location), 9) AS h3_cell
FROM retail_stores;

-- 步驟 2：使用 H3 索引客戶位置
CREATE TABLE customer_h3 AS
SELECT customer_id, name, location,
  h3_longlatash3(ST_X(location), ST_Y(location), 9) AS h3_cell
FROM customers;

-- 步驟 3：使用 H3 預篩選 + 精確 ST 距離的快速鄰近搜尋
SELECT s.name AS store, c.name AS customer,
  ST_DistanceSphere(s.location, c.location) AS distance_m
FROM store_h3 s
JOIN customer_h3 c
  ON c.h3_cell IN (SELECT explode(h3_kring(s.h3_cell, 2)))
WHERE ST_DistanceSphere(s.location, c.location) < 2000;
```

### 空間連接效能

Databricks 使用內建空間索引自動優化空間連接。JOIN 條件中的空間謂詞（如 `ST_Intersects`、`ST_Contains` 和 `ST_Within`）與傳統叢集相比，效能提升高達 **17 倍**。無需變更程式碼 -- 優化器會自動應用空間索引。

**效能提示：**
- 當連接的一側足夠小以適合記憶體時，使用 `BROADCAST` 提示。
- 對距離計算使用投影座標系統（例如，以公尺為單位的 SRID 5070）以避免昂貴的球體函數。
- 結合 H3 進行粗略預篩選與 ST 進行精確操作。
- 在 H3 單元欄位上使用 Delta Lake liquid clustering 以優化資料佈局。
- 啟用自動優化：`delta.autoOptimize.optimizeWrite` 和 `delta.autoOptimize.autoCompact`。

---

## 第二部分：定序

定序定義比較和排序字串的規則。Databricks 使用 ICU 函式庫支援二進位、不區分大小寫、不區分重音和特定區域設定的定序。自 Databricks Runtime 16.1+ 起可用。

### 定序類型

| 定序 | 說明 | 行為 |
|-----------|-------------|----------|
| `UTF8_BINARY` | 預設。UTF-8 編碼的逐位元組比較 | `'A' < 'Z' < 'a'` -- 二進位順序，區分大小寫/重音 |
| `UTF8_LCASE` | 不區分大小寫的二進位。轉換為小寫後使用 UTF8_BINARY 比較 | `'A' == 'a'` 但 `'e' != 'é'`（區分重音） |
| `UNICODE` | ICU 根區域設定。與語言無關的 Unicode 排序 | `'a' < 'A' < 'Á' < 'b'` -- 將相似字元分組 |
| 特定區域設定 | 基於 ICU 區域設定（例如，`DE`、`FR`、`JA`） | 語言感知的排序規則 |

### 定序語法

```
{ UTF8_BINARY | UTF8_LCASE | { UNICODE | locale } [ _ modifier [...] ] }
```

其中 `locale` 為：
```
language_code [ _ script_code ] [ _ country_code ]
```

- `language_code`：ISO 639-1（例如，`EN`、`DE`、`FR`、`JA`、`ZH`）
- `script_code`：ISO 15924（例如，`Hant` 表示繁體中文，`Latn` 表示拉丁文）
- `country_code`：ISO 3166-1（例如，`US`、`DE`、`CAN`）

### 定序修飾符（DBR 16.2+）

| 修飾符 | 說明 | 預設值 |
|----------|-------------|---------|
| `CS` | 區分大小寫：`'A' != 'a'` | 是（預設） |
| `CI` | 不區分大小寫：`'A' == 'a'` | 否 |
| `AS` | 區分重音：`'e' != 'é'` | 是（預設） |
| `AI` | 不區分重音：`'e' == 'é'` | 否 |
| `RTRIM` | 不區分尾隨空格：`'Hello' == 'Hello '` | 否 |

從每對（CS/CI、AS/AI）中最多指定一個，加上選用的 RTRIM。順序無關緊要。

### 區域設定範例

| 定序名稱 | 說明 |
|----------------|-------------|
| `UNICODE` | ICU 根區域設定，與語言無關 |
| `UNICODE_CI` | Unicode，不區分大小寫 |
| `UNICODE_CI_AI` | Unicode，不區分大小寫和重音 |
| `DE` | 德文排序規則 |
| `DE_CI_AI` | 德文，不區分大小寫和重音 |
| `FR_CAN` | 法文（加拿大） |
| `EN_US` | 英文（美國） |
| `ZH_Hant_MAC` | 繁體中文（澳門） |
| `SR` | 塞爾維亞文（從 `SR_CYR_SRN_CS_AS` 正規化） |
| `JA` | 日文 |
| `EN_CS_AI` | 英文，區分大小寫，不區分重音 |
| `UTF8_LCASE_RTRIM` | 不區分大小寫，修剪尾隨空格 |

### 定序優先順序

從最高到最低：

1. **明確** -- 透過 `COLLATE` 表達式指定
2. **隱式** -- 從欄位、欄位或變數定義衍生
3. **預設** -- 應用於字串字面值和函數結果
4. **無** -- 當組合不同的隱式定序時

在同一表達式中混合兩個不同的**明確**定序會產生錯誤。

### 在不同層級設定定序

#### 目錄層級（DBR 17.1+）

```sql
-- 建立帶有預設定序的目錄
CREATE CATALOG customer_cat
  DEFAULT COLLATION UNICODE_CI_AI;

-- 在此目錄中建立的所有結構描述、資料表和字串欄位
-- 繼承 UNICODE_CI_AI，除非被覆寫
```

#### 結構描述層級（DBR 17.1+）

```sql
-- 建立帶有預設定序的結構描述
CREATE SCHEMA my_schema
  DEFAULT COLLATION UNICODE_CI;

-- 變更新物件的預設定序（現有物件不變）
ALTER SCHEMA my_schema
  DEFAULT COLLATION UNICODE_CI_AI;
```

#### 資料表層級（DBR 16.3+）

```sql
-- 資料表層級預設定序
CREATE TABLE users (
  id INT,
  username STRING,           -- 從資料表預設繼承 UNICODE_CI
  email STRING,              -- 從資料表預設繼承 UNICODE_CI
  password_hash STRING COLLATE UTF8_BINARY  -- 明確覆寫
) DEFAULT COLLATION UNICODE_CI;
```

#### 欄位層級（DBR 16.1+）

```sql
-- 欄位層級定序
CREATE TABLE products (
  id INT,
  name STRING COLLATE UNICODE_CI,
  sku STRING COLLATE UTF8_BINARY,
  description STRING COLLATE UNICODE_CI_AI
);

-- 新增帶有定序的欄位
ALTER TABLE products
  ADD COLUMN category STRING COLLATE UNICODE_CI;

-- 變更欄位定序（需要 DBR 17.2+；可能並非所有 SQL Warehouse 版本都可用）
ALTER TABLE products
  ALTER COLUMN name SET COLLATION UNICODE_CI_AI;
```

#### 表達式層級

```sql
-- 在查詢中內聯應用定序
SELECT *
FROM products
WHERE name COLLATE UNICODE_CI = 'laptop';

-- 檢查表達式的定序
SELECT collation('test' COLLATE UNICODE_CI);
-- 返回：UNICODE_CI
```

### 定序繼承階層

```
Catalog DEFAULT COLLATION
  -> Schema DEFAULT COLLATION（覆寫目錄）
    -> Table DEFAULT COLLATION（覆寫結構描述）
      -> Column COLLATE（覆寫資料表）
        -> Expression COLLATE（覆寫欄位）
```

如果在任何層級都未指定定序，則使用 `UTF8_BINARY`。

### 定序感知字串函數

大多數字串函數都尊重定序。關鍵的定序感知操作：

| 函數/運算子 | 定序行為 |
|-------------------|-------------------|
| `=`、`!=`、`<`、`>`、`<=`、`>=` | 比較使用欄位/表達式定序 |
| `LIKE` | 模式匹配尊重定序 |
| `CONTAINS(str, substr)` | 子字串搜尋尊重定序 |
| `STARTSWITH(str, prefix)` | 前綴匹配尊重定序 |
| `ENDSWITH(str, suffix)` | 後綴匹配尊重定序 |
| `IN (...)` | 成員測試尊重定序 |
| `BETWEEN` | 範圍比較尊重定序 |
| `ORDER BY` | 排序尊重定序 |
| `GROUP BY` | 分組尊重定序 |
| `DISTINCT` | 去重尊重定序 |
| `REPLACE(str, old, new)` | 搜尋尊重定序 |
| `TRIM` / `LTRIM` / `RTRIM` | 修剪字元尊重定序 |

**效能注意事項：**使用 `UTF8_LCASE` 定序的 `STARTSWITH` 和 `ENDSWITH` 與等效的 `LOWER()` 解決方法相比，顯示高達 **10 倍的效能提升**。

### 實用函數

```sql
-- 取得表達式的定序
SELECT collation(name) FROM products;

-- 列出所有支援的定序
SELECT * FROM collations();

-- 使用 COLLATE 測試定序
SELECT collation('hello' COLLATE DE_CI_AI);
-- 返回：DE_CI_AI
```

### 實用定序範例

#### 不區分大小寫的搜尋

```sql
-- 使用欄位定序（首選 - 利用索引）
CREATE TABLE users (
  id INT,
  username STRING COLLATE UTF8_LCASE,
  email STRING COLLATE UTF8_LCASE
);

INSERT INTO users VALUES
  (1, 'JohnDoe', 'John@Example.com'),
  (2, 'janedoe', 'JANE@EXAMPLE.COM');

-- 自動不區分大小寫匹配
SELECT * FROM users WHERE username = 'johndoe';
-- 返回：JohnDoe

SELECT * FROM users WHERE email = 'john@example.com';
-- 返回：John@Example.com
```

#### 使用表達式定序的不區分大小寫搜尋

```sql
-- 在 UTF8_BINARY 欄位上進行臨時不區分大小寫比較
SELECT * FROM products
WHERE name COLLATE UNICODE_CI = 'MacBook Pro';
-- 匹配：macbook pro、MACBOOK PRO、MacBook Pro 等
```

#### 不區分重音的搜尋

```sql
-- 不區分重音的匹配
CREATE TABLE cities (
  id INT,
  name STRING COLLATE UNICODE_CI_AI
);

INSERT INTO cities VALUES (1, 'Montreal'), (2, 'Montréal');

SELECT * FROM cities WHERE name = 'Montreal';
-- 返回兩者：Montreal 和 Montréal（將 e 和 é 視為相等）
```

#### 區域設定感知排序

```sql
-- 德文排序（變音符號正確排序）
SELECT name
FROM german_customers
ORDER BY name COLLATE DE;
-- 排序：Ärzte 在 Bauer 之前（Ä 在德文排序中視為 A+e）

-- 瑞典文排序（Å、Ä、Ö 排在 Z 之後）
SELECT name
FROM swedish_customers
ORDER BY name COLLATE SV;
```

#### 尾隨空格處理

```sql
-- RTRIM 修飾符忽略尾隨空格
SELECT 'Hello' COLLATE UTF8_BINARY_RTRIM = 'Hello   ';
-- 返回：true

SELECT 'Hello' COLLATE UTF8_BINARY = 'Hello   ';
-- 返回：false
```

#### 目錄範圍的不區分大小寫設定

```sql
-- 建立一個預設所有內容都不區分大小寫的目錄
CREATE CATALOG app_data DEFAULT COLLATION UNICODE_CI;

USE CATALOG app_data;
CREATE SCHEMA users_schema;
USE SCHEMA users_schema;

-- 所有 STRING 欄位自動使用 UNICODE_CI
CREATE TABLE accounts (
  id INT,
  username STRING,  -- 從目錄繼承 UNICODE_CI
  email STRING       -- 從目錄繼承 UNICODE_CI
);

-- 查詢自動不區分大小寫
SELECT * FROM accounts WHERE username = 'admin';
-- 匹配：Admin、ADMIN、admin、aDmIn 等
```

### 限制和注意事項

- `CHECK` 約束和生成欄位表達式需要 `UTF8_BINARY` 預設定序。
- `hive_metastore` 目錄資料表不支援定序約束。
- `ALTER SCHEMA ... DEFAULT COLLATION` 僅影響新建立的物件，不影響現有物件。
- 在同一表達式中混合兩個不同的明確定序會引發錯誤。
- `UTF8_LCASE` 在內部用於 Databricks 識別碼解析（目錄、結構描述、資料表、欄位名稱）。
- Databricks 透過移除預設值來正規化定序名稱（例如，`SR_CYR_SRN_CS_AS` 簡化為 `SR`）。
- 定序修飾符需要 Databricks Runtime 16.2+。
- 目錄/結構描述層級的 `DEFAULT COLLATION` 需要 Databricks Runtime 17.1+。
