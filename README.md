# 城市水路 —— 臺北市直飲臺地圖與報修系統

找離你最近的直飲臺，發現故障可以直接回報，維護單位在後台處理、結案。

資料來自臺北市資料大平臺的「臺北市所屬直飲臺」開放資料（739 筆），後端用 FastAPI + PostgreSQL，前端用 Vue 3 + Leaflet，整套用 Docker Compose 一行指令啟動。

> 這是為 CodeFest 2026（臺北秋季程式設計節）準備的練功專案，目前是 MVP 階段。

## 功能

**市民端**
- 地圖顯示所有直飲臺，可依行政區篩選，或定位後查詢附近站點（依距離排序）
- 站點詳情：地址、開放時間、設備狀態、最近一次水質採樣結果，以及這座站點的回報紀錄
- 回報問題：設備故障、沒有出水、環境髒污，也可以回報「狀況良好」

**維護單位端（`/admin`）**
- 依處理狀態、行政區篩選所有回報
- 更新處理狀態（待處理 → 處理中 → 已完成／不受理）並填寫回覆
- 結案時自動記錄完成時間，重新開啟時清除

## 架構

```
          瀏覽器
            │
            ▼
  ┌──────────────────┐     REST API     ┌──────────────────┐      ┌──────────────┐
  │ frontend (nginx) │ ───────────────▶ │ backend (FastAPI)│ ───▶ │ db           │
  │ Vue 3 + Leaflet  │   :8000/api/v1   │ SQLAlchemy       │      │ PostgreSQL 17│
  │ :8080            │                  │ Alembic          │      │ :5432        │
  └──────────────────┘                  └────────┬─────────┘      └──────────────┘
                                                 │ python -m app.sync
                                                 ▼
                                     臺北市資料大平臺 (data.taipei)
```

| 層 | 技術 |
|---|---|
| 前端 | Vue 3、TypeScript、Vue Router、Leaflet（OpenStreetMap 圖磚）、Tailwind CSS、Vite |
| 後端 | Python 3.13、FastAPI、Pydantic、SQLAlchemy 2.0、Alembic、httpx |
| 資料庫 | PostgreSQL 17（本機開發可退回 SQLite，不用改程式碼） |
| 部署 | Docker Compose（db / backend / frontend 三個容器） |

## 快速開始

### 用 Docker（推薦）

```bash
git clone https://github.com/max930000/water_resource.git
cd water_resource
docker compose up -d --build

# 第一次啟動後，把開放資料同步進資料庫
docker compose exec backend python -m app.sync
```

- 網站：http://localhost:8080
- API 文件（Swagger）：http://localhost:8000/docs

資料庫帳密預設寫在 `.env.example`，要改的話複製成 `.env` 再修改，`.env` 不會進 Git。

### 不用 Docker（本機開發，Windows）

```powershell
# 後端
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head      # 建立資料表（沒設 DATABASE_URL 時使用 SQLite）
python -m app.sync        # 同步開放資料

# 前端
cd ..\frontend
npm install

# 回到專案根目錄，一鍵啟動前後端並開瀏覽器
cd ..
.\start.ps1               # 停止：.\start.ps1 -Stop
```

## API

完整的參數與回傳格式請看啟動後的 `/docs`。

| Method | Path | 說明 |
|---|---|---|
| GET | `/health` | 健康檢查 |
| GET | `/api/v1/stations` | 分頁查詢直飲臺，可依縣市、行政區、關鍵字篩選 |
| GET | `/api/v1/stations/districts` | 行政區清單（依縣市分組） |
| GET | `/api/v1/stations/nearby?lat=&lon=&radius=` | 查詢附近的直飲臺，依距離排序 |
| GET | `/api/v1/stations/{id}` | 單一直飲臺詳細資料 |
| POST | `/api/v1/stations/{id}/reports` | 新增回報 |
| GET | `/api/v1/stations/{id}/reports` | 某一座直飲臺的所有回報 |
| GET | `/api/v1/reports` | 所有回報（後台用），可依狀態、縣市、行政區篩選 |
| GET | `/api/v1/reports/{id}` | 單一回報，查詢處理進度 |
| PATCH | `/api/v1/reports/{id}` | 更新處理狀態與回覆（維護單位用） |

## 設計決策

**附近站點查詢：先用方框粗篩，再用 Haversine 精算**

直接在 SQL 裡對每一筆算球面距離，會讓索引失效、變成全表掃描。這裡的做法是：

1. 依搜尋半徑換算出經緯度方框，用 `BETWEEN` 在 `(lat, lon)` 複合索引上篩出候選
2. 在 Python 裡用 Haversine 公式算精確距離，剔除方框四個角落超出半徑的點，再排序

739 筆資料篩完通常只剩幾十筆，計算時間不到 1 毫秒。資料量到幾十萬筆時，應該改用 PostGIS 的 `ST_DWithin` 搭配 GiST 索引。

**開放資料同步：可重複執行的 upsert**

`app.sync` 會先把資料庫現有的站點一次撈回來，建成以外部編號為 key 的字典，再逐筆比對要新增還是更新，避免在迴圈裡逐筆查詢造成 N+1 問題。同步可以重複執行，不會產生重複資料。

**避免 N+1 查詢**

回報列表需要顯示站點名稱，用 `selectinload` 預先載入關聯的站點。20 筆回報從 21 次查詢降到 2 次。

**分頁排序一定要有唯一的 tiebreaker**

回報依建立時間排序，但同一秒內建立的回報時間完全相同，資料庫不保證它們的順序，分頁時會出現重複或漏掉的資料。因此排序最後一定加上主鍵 `id`。

**設定與程式碼分離**

資料庫位置、CORS 允許來源都由環境變數決定。同一份程式碼在筆電上用 SQLite，在 Docker 裡用 PostgreSQL，不用改任何一行。

## 已知限制與下一步

- **維護端 API 還沒有權限控管**：`PATCH /api/v1/reports/{id}` 目前任何人都能呼叫。下一步是串接身分驗證（例如台北通），並依角色限制只有維護單位能更新狀態。
- **回報沒有防濫用機制**：需要加上頻率限制，避免同一個人大量送出回報。
- **回報不能附照片**：現場照片能幫助維護人員判斷問題，之後要加上圖片上傳。
- **沒有自動化測試**：`app/geo.py` 是純函式，最適合先補單元測試；API 可以用 FastAPI 的 `TestClient` 測試。
- **同步要手動執行**：之後改成排程每日自動同步。

## 資料來源與授權

- 直飲臺資料：[臺北市資料大平臺](https://data.taipei/)「臺北市所屬直飲臺」（臺北自來水事業處），依[政府資料開放授權條款第 1 版](https://data.gov.tw/license)使用
- 地圖圖磚：© [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors
