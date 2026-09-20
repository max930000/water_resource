"""
API 的輸入 / 輸出格式（Pydantic schema）。

跟 models.py 的分工：
  models.py  → 資料「在資料庫裡」長什麼樣
  schemas.py → 資料「在 API 上」長什麼樣

兩者刻意分開，這樣改資料庫不會直接打破前端契約，
也不會不小心把內部欄位外洩出去。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import ReportStatus, ReportType


class StationSummary(BaseModel):
    """
    列表與地圖用的精簡版。

    from_attributes=True 是關鍵：
    預設 Pydantic 只認得 dict，加上這個設定之後，
    它就能直接從 SQLAlchemy 的物件讀取屬性（station.name、station.lat…）。
    （Pydantic v1 時代這個設定叫 orm_mode，網路上舊文章會這樣寫。）
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    name: str
    city: str | None
    district: str | None
    address: str | None
    lat: float
    lon: float
    status: str | None
    # 這座站目前有幾筆「待處理」回報。地圖上用它決定標紅點還是綠點。
    # 不是資料庫欄位，是每次查詢時算出來的。
    open_report_count: int = 0


class StationDetail(StationSummary):
    """
    詳情頁用的完整版。

    直接繼承 Summary，只要補上多出來的欄位 ——
    不用重寫一次共同欄位，之後 Summary 改了 Detail 也會跟著改。
    """

    place_type: str | None
    owner_unit: str | None
    install_spot: str | None
    open_hours: str | None
    maintainer: str | None
    phone: str | None
    status_changed_at: datetime | None
    last_sampled_at: datetime | None
    coliform: str | None
    quality_url: str | None
    photo_url: str | None
    synced_at: datetime


class StationPage(BaseModel):
    """
    分頁結果的統一格式。

    為什麼要包一層而不是直接回 list：
    前端需要知道「總共幾筆、現在第幾頁」才能畫分頁元件。
    只回一個陣列的話，前端永遠不知道還有沒有下一頁。
    """

    items: list[StationSummary]
    page: int
    size: int
    total: int
    total_pages: int


class DistrictGroup(BaseModel):
    """
    行政區清單，依縣市分組。

    刻意不回平面的 ["大安", "信義", "板橋", ...] ——
    那 30 個混在一起，前端做不出可用的下拉選單。
    回分組結構，前端才能直接塞進 <optgroup>。
    """

    city: str
    districts: list[str]
class StationNearby(StationSummary):
    """
    「附近」查詢的結果，比 Summary 多一個距離欄位。

    distance_meters 不是資料庫欄位，是每次查詢依使用者位置「算出來」的 ——
    所以它只能存在於 schema，不可能出現在 models.py。

    這正好示範了為什麼 schema 和 model 要分開：
    API 回傳的東西，不一定跟資料庫存的東西一樣。
    """

    distance_meters: float


class ReportCreate(BaseModel):
    """
    建立回報的「輸入」格式。

    ⚠ 最重要的觀念：輸入和輸出 schema 一定要分開。

    如果用同一個 schema 當輸入又當輸出，使用者就能在 POST 的 body 裡塞
    {"id": 1, "status": "RESOLVED", "created_at": "1999-01-01"} ——
    自己指定 id、自己把案件標記成已完成、自己偽造時間。

    輸入 schema 只放「使用者有權決定」的欄位。
    id、status、created_at 都由伺服器決定，所以不出現在這裡。
    """

    type: ReportType
    # Field 用來加驗證規則。max_length=500 要跟 models.py 的 String(500) 一致，
    # 不然超長字串會過得了 API、卻在寫入資料庫時炸掉（500 錯誤，很難查）。
    description: str | None = Field(None, max_length=500, description="補充說明")


class ReportOut(BaseModel):
    """回報的「輸出」格式。比輸入多了伺服器決定的欄位。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    # 這個欄位對應 models.py 裡的 station_name property。
    # from_attributes 讀的是「屬性」，property 也算，所以拿得到。
    station_name: str
    type: ReportType
    description: str | None
    status: ReportStatus
    admin_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class ReportPage(BaseModel):
    """回報的分頁結果，格式跟 StationPage 一致。"""

    items: list[ReportOut]
    page: int
    size: int
    total: int
    total_pages: int


class ReportUpdate(BaseModel):
    """
    更新回報的輸入格式（PATCH 用）。

    兩個欄位都是選填 —— 維護人員只送他要改的部分。
    沒列在這裡的欄位（id、created_at、type…）使用者一律改不到，
    這就是防止偽造的方式。
    """

    status: ReportStatus | None = None
    admin_note: str | None = Field(None, max_length=500, description="給市民看的處理說明")
