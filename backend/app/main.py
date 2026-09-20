"""
TownQuest API —— 應用程式入口。

路由都掛在這裡。等端點變多之後（下一課加回報功能時），
會拆成 routers/ 資料夾分檔管理。
"""

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Station
from .schemas import DistrictGroup, StationDetail, StationPage, StationSummary

app = FastAPI(
    title="TownQuest API",
    version="0.1.0",
    description="給臺北市民的直飲臺地圖與回報服務，資料來自臺北市資料大平臺。",
)


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

    return StationPage(
        # model_validate 把 SQLAlchemy 物件轉成 Pydantic schema，
        # 靠的就是 schemas.py 裡那個 from_attributes=True。
        items=[StationSummary.model_validate(s) for s in rows],
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
