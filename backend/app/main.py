"""
TownQuest API —— 應用程式入口。

路由都掛在這裡。等端點變多之後（下一課加回報功能時），
會拆成 routers/ 資料夾分檔管理。
"""

# import 依 PEP 8 分成三段：標準函式庫 → 第三方套件 → 自己的模組
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import geo
from .database import get_db
from .models import Report, ReportStatus, Station
from .schemas import (
    DistrictGroup,
    ReportCreate,
    ReportOut,
    ReportPage,
    ReportUpdate,
    StationDetail,
    StationNearby,
    StationPage,
    StationSummary,
)

app = FastAPI(
    title="TownQuest API",
    version="0.1.0",
    description="給臺北市民的直飲臺地圖與回報服務，資料來自臺北市資料大平臺。",
)

# ── CORS：允許前端網頁呼叫這個 API ──────────────────────
# 瀏覽器有「同源政策」：網頁只能呼叫「同一個網址」的後端。
# 我們的前端在 127.0.0.1:5173、後端在 127.0.0.1:8000，port 不同 = 不同來源，
# 不設定的話瀏覽器會直接擋下請求（後端根本收不到）。
#
# allow_origins 要列出明確的網址，不要用 ["*"]：
# 那等於允許網路上任何網站呼叫你的 API。
# 之後上線時，這裡要換成台北通 WebView 實際使用的來源。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _open_report_counts(db: Session, station_ids: list[int]) -> dict[int, int]:
    """
    一次算出這批站點各有幾筆待處理回報。

    為什麼不在迴圈裡逐站查？那會對 20 個站發 20 次查詢（N+1）。
    一句 GROUP BY 就解決，永遠只有 1 次。
    """
    if not station_ids:
        return {}
    rows = db.execute(
        select(Report.station_id, func.count())
        .where(Report.station_id.in_(station_ids), Report.status == ReportStatus.OPEN)
        .group_by(Report.station_id)
    ).all()
    return {sid: n for sid, n in rows}


@app.get("/health")
def read_health():
    """服務健康檢查。刻意放在 /api/v1 外面，因為它不是業務 API。"""
    return {"status": "UP"}


@app.get("/api/v1/stations", response_model=StationPage)
def list_stations(
    # Query(...) 讓你替查詢參數加上預設值、驗證規則和說明文字。
    # 這些說明會自動出現在 /docs，前端不用另外問你。
    city: str | None = Query(None, description="縣市，例如「臺北市」"),
    district: str | None = Query(None, description="行政區，例如「大安」"),
    keyword: str | None = Query(None, description="關鍵字，比對場所名稱與地址"),
    page: int = Query(0, ge=0, description="第幾頁，從 0 開始"),
    # le=200 是保護措施：不讓別人用 size=999999 一次把整個資料庫拖走。
    # 公開 API 一定要設上限，否則等於開放讓人打你的資料庫。
    size: int = Query(20, ge=1, le=200, description="每頁幾筆"),
    # Depends(get_db) 就是依賴注入：
    # FastAPI 會幫你呼叫 get_db()、把 session 傳進來、
    # 等這個函式跑完再自動關掉。你完全不用管開關。
    db: Session = Depends(get_db),
):
    """分頁查詢直飲臺，可用縣市、行政區、關鍵字篩選。"""
    # 條件先收集成 list，最後一次展開給 where()。
    # 這樣「有給才篩」的邏輯很清楚，不用寫一堆 if/else 組查詢。
    conditions = []
    if city:
        conditions.append(Station.city == city)
    if district:
        conditions.append(Station.district == district)
    if keyword:
        pattern = f"%{keyword}%"
        # or_ 表示「名稱符合 或 地址符合」。
        # 注意這裡沒有自己拼 SQL 字串 —— SQLAlchemy 會用參數化查詢，
        # 所以使用者輸入 '; DROP TABLE station; -- 也不會出事。
        conditions.append(
            or_(Station.name.ilike(pattern), Station.address.ilike(pattern))
        )

    # 兩次查詢：一次算總數（給分頁用），一次取這一頁的資料。
    # where(*conditions) 的 * 是把 list 展開成多個參數；
    # conditions 是空的時候等同 where()，也就是不加任何條件。
    total = db.scalar(select(func.count()).select_from(Station).where(*conditions)) or 0

    rows = db.scalars(
        select(Station)
        .where(*conditions)
        # 一定要有穩定的排序。沒有 ORDER BY 的話，
        # 資料庫不保證每次回傳順序一致 —— 分頁就會出現
        # 「第 2 頁有些資料跟第 1 頁重複、有些永遠看不到」的詭異 bug。
        .order_by(Station.city, Station.district, Station.name)
        .offset(page * size)
        .limit(size)
    ).all()

    counts = _open_report_counts(db, [s.id for s in rows])
    items = []
    for s in rows:
        item = StationSummary.model_validate(s)
        item.open_report_count = counts.get(s.id, 0)
        items.append(item)

    return StationPage(
        items=items,
        page=page,
        size=size,
        total=total,
        # 無條件進位的整數寫法：(a + b - 1) // b
        # 例如 739 筆、每頁 20 筆 → (739 + 19) // 20 = 37 頁
        total_pages=(total + size - 1) // size if size else 0,
    )


# ⚠ 這支一定要寫在 /api/v1/stations/{station_id} 上面，原因見下方說明
@app.get("/api/v1/stations/districts", response_model=list[DistrictGroup])
def list_districts(db: Session = Depends(get_db)):
    """行政區清單，依縣市分組，給前端下拉選單用。"""
    rows = db.execute(
        select(Station.city, Station.district)
        .where(Station.district.is_not(None))
        # distinct() 讓 739 筆變成 30 組不重複的 (縣市, 行政區)
        .distinct()
        .order_by(Station.city, Station.district)
    ).all()

    # 分組在後端做完，前端拿到就能直接用。
    # SQL 已經照 (city, district) 排好序，所以這個迴圈很單純。
    grouped: dict[str, list[str]] = {}
    for city, district in rows:
        grouped.setdefault(city or "其他", []).append(district)

    return [DistrictGroup(city=c, districts=d) for c, d in grouped.items()]

@app.get("/api/v1/stations/nearby", response_model=list[StationNearby])
def list_nearby(
    # Query(...) 的第一個參數是 ...（Ellipsis）代表「必填」。
    # 沒給預設值的話，使用者不帶 lat 就會收到 422，而不是拿到莫名其妙的結果。
    lat: float = Query(..., ge=-90, le=90, description="緯度，例如 25.0478"),
    lon: float = Query(..., ge=-180, le=180, description="經度，例如 121.5170"),
    radius: float = Query(1000, gt=0, le=20000, description="搜尋半徑（公尺），上限 20 公里"),
    limit: int = Query(20, ge=1, le=100, description="最多回傳幾筆"),
    db: Session = Depends(get_db),
):
    """
    查詢指定座標附近的直飲臺，依距離由近到遠排序。

    做法是「先粗篩再精算」：
      1. 用經緯度方框在資料庫篩出候選（走 idx_station_latlon 索引，很快）
      2. 在 Python 裡用 Haversine 算精確距離、過濾、排序

    為什麼不直接在 SQL 裡算距離？
      - SQLite 的數學函式是編譯選項，不保證可用
      - 就算可用，對每一筆都算三角函式會讓索引失效，變成全表掃描
      - 739 筆資料量極小，方框篩完通常只剩幾十筆，Python 算起來不到 1 毫秒
      資料量到幾十萬筆時，才需要換成 PostgreSQL + PostGIS 的
      ST_DWithin + GiST 索引 —— 那才是真正的空間查詢。
    """
    # 步驟 1：算出方框範圍
    d_lat = geo.lat_delta(radius)
    d_lon = geo.lon_delta(radius, lat)

    candidates = db.scalars(
        select(Station).where(
            # between 會產生 SQL 的 BETWEEN，能吃到 (lat, lon) 複合索引
            Station.lat.between(lat - d_lat, lat + d_lat),
            Station.lon.between(lon - d_lon, lon + d_lon),
        )
    ).all()

    # 步驟 2：精算距離並過濾
    # 方框是「正方形」，半徑是「圓形」——
    # 四個角落會落在方框內但超出半徑，所以這一步不能省。
    ranked = [
        (geo.distance_meters(lat, lon, s.lat, s.lon), s)
        for s in candidates
    ]
    ranked = [pair for pair in ranked if pair[0] <= radius]

    # key=... 不能省：不指定的話，距離相同時 Python 會去比較第二個元素
    # （Station 物件），而 Station 沒有定義比較方法，會直接丟 TypeError。
    # 這個 bug 平常測不出來，要剛好兩個點等距才會爆。
    ranked.sort(key=lambda pair: pair[0])

    # model_dump() 把 Pydantic 物件轉成 dict，再用 ** 展開，
    # 加上 distance_meters 組成 StationNearby。
    top = ranked[:limit]
    counts = _open_report_counts(db, [s.id for _, s in top])

    result = []
    for distance, station in top:
        data = StationSummary.model_validate(station).model_dump()
        data["open_report_count"] = counts.get(station.id, 0)
        result.append(StationNearby(**data, distance_meters=round(distance, 1)))
    return result
@app.get("/api/v1/stations/{station_id}", response_model=StationDetail)
def get_station(station_id: int, db: Session = Depends(get_db)):
    """取得單一直飲臺的完整資訊。"""
    # db.get() 是「用主鍵找一筆」的專用方法，
    # 比 select().where(id == x) 更直接，而且會用到 SQLAlchemy 的快取。
    station = db.get(Station, station_id)
    if station is None:
        # 找不到就回 404，不要回 200 加一個 null ——
        # HTTP 狀態碼本身就是契約的一部分，前端靠它判斷要不要顯示錯誤畫面。
        raise HTTPException(status_code=404, detail="找不到這座直飲臺")
    return station


# ══════════════════════════════════════════════════════════
#  市民回報
# ══════════════════════════════════════════════════════════


@app.post(
    "/api/v1/stations/{station_id}/reports",
    response_model=ReportOut,
    # 201 Created 是「新增資源成功」的正確狀態碼。
    # 不要通通回 200 —— 前端和監控系統會依狀態碼判斷行為。
    status_code=201,
)
def create_report(
    station_id: int,
    # 沒有用 Query() 包起來的 Pydantic model 參數，
    # FastAPI 會自動認定它來自 request body 的 JSON。
    # 驗證失敗會自動回 422 並指出是哪個欄位錯，你不用寫任何驗證程式碼。
    payload: ReportCreate,
    db: Session = Depends(get_db),
):
    """新增一筆市民回報。"""
    # 先確認站點存在。
    # 不檢查的話，外鍵約束會在 commit 時失敗，前端收到 500 ——
    # 但這其實是使用者給錯 id，應該回 404。狀態碼要說實話。
    if db.get(Station, station_id) is None:
        raise HTTPException(status_code=404, detail="找不到這座直飲臺")

    report = Report(
        station_id=station_id,
        type=payload.type,
        description=payload.description,
        # status 沒給，會套用 model 裡的 default=ReportStatus.OPEN
    )
    db.add(report)
    db.commit()

    # db.refresh() 重新從資料庫把這筆讀回來。
    # 為什麼需要：created_at 是 server_default（由資料庫的 CURRENT_TIMESTAMP 填），
    # commit 之前 Python 端根本不知道那個值，不 refresh 就會拿到 None。
    db.refresh(report)
    return report


@app.get("/api/v1/stations/{station_id}/reports", response_model=list[ReportOut])
def list_station_reports(station_id: int, db: Session = Depends(get_db)):
    """某一座直飲臺的所有回報，新的在前。"""
    if db.get(Station, station_id) is None:
        raise HTTPException(status_code=404, detail="找不到這座直飲臺")

    return db.scalars(
        select(Report)
        # selectinload 預先把關聯的 station 一次撈回來。
        # 不加的話，ReportOut 的 station_name 會對每一筆各發一次 SELECT ——
        # 20 筆回報 = 21 次查詢，這就是 N+1 問題。
        # 加上之後只有 2 次：一次查 report，一次用 IN (...) 撈所有相關 station。
        .options(selectinload(Report.station))
        .where(Report.station_id == station_id)
        # ⚠ 一定要加 id 當第二排序鍵（tiebreaker）。
        # SQLite 的 CURRENT_TIMESTAMP 只有「秒」的精度，同一秒內建立的多筆
        # created_at 完全相同 —— 這時資料庫不保證順序，分頁還會出現
        # 「同一筆出現在兩頁」或「某筆永遠看不到」。
        # 排序的最後一個鍵一定要是唯一值（這裡是主鍵）。
        .order_by(Report.created_at.desc(), Report.id.desc())
    ).all()


@app.get("/api/v1/reports", response_model=ReportPage)
def list_reports(
    status: ReportStatus | None = Query(None, description="依處理狀態篩選"),
    city: str | None = Query(None, description="依縣市篩選"),
    district: str | None = Query(None, description="依行政區篩選"),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    所有回報的列表，給維護單位後台用。

    這支是「服務落地可能性」那 30 分的關鍵 ——
    評審會問「市民回報進來之後，誰處理、怎麼結案」。
    """
    conditions = []
    if status:
        conditions.append(Report.status == status)
    # 縣市和行政區在 station 表上，要 join 過去才篩得到。
    # 這就是關聯式資料庫的價值：資料不重複儲存，需要時 join 起來用。
    if city:
        conditions.append(Station.city == city)
    if district:
        conditions.append(Station.district == district)

    total = (
        db.scalar(
            select(func.count()).select_from(Report).join(Station).where(*conditions)
        )
        or 0
    )

    rows = db.scalars(
        select(Report)
        .join(Station)
        .options(selectinload(Report.station))
        .where(*conditions)
        # ⚠ 一定要加 id 當第二排序鍵（tiebreaker）。
        # SQLite 的 CURRENT_TIMESTAMP 只有「秒」的精度，同一秒內建立的多筆
        # created_at 完全相同 —— 這時資料庫不保證順序，分頁還會出現
        # 「同一筆出現在兩頁」或「某筆永遠看不到」。
        # 排序的最後一個鍵一定要是唯一值（這裡是主鍵）。
        .order_by(Report.created_at.desc(), Report.id.desc())
        .offset(page * size)
        .limit(size)
    ).all()

    return ReportPage(
        items=[ReportOut.model_validate(r) for r in rows],
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size,
    )


@app.get("/api/v1/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """取得單一回報 —— 讓市民查自己那筆的處理進度。"""
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="找不到這筆回報")
    return report


@app.patch("/api/v1/reports/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
):
    """
    更新回報的處理狀態與回覆（維護單位用）。

    ⚠ 目前沒有權限控管，任何人都打得到。
    正式版要接台北通身分 + 角色授權，發表時要主動說明。
    """
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="找不到這筆回報")

    # 只取「使用者真的有送」的欄位。
    # 沒送的欄位不會出現在這個 dict 裡，所以不會被動到 ——
    # 維護人員只改狀態時，上次寫好的回覆不會被洗掉。
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="沒有提供任何要更新的欄位")

    for field, value in changes.items():
        setattr(report, field, value)

    # 業務規則：結案時自動蓋完成時間，重新開啟時清掉。
    # 這種連動的值交給伺服器決定，不讓前端填（會被偽造、會忘記、格式會亂）。
    if "status" in changes:
        if report.status in (ReportStatus.RESOLVED, ReportStatus.REJECTED):
            report.resolved_at = func.now()
        else:
            report.resolved_at = None

    db.commit()
    db.refresh(report)
    return report
