"""
API 的輸入 / 輸出格式（Pydantic schema）。

跟 models.py 的分工：
  models.py  → 資料「在資料庫裡」長什麼樣
  schemas.py → 資料「在 API 上」長什麼樣

兩者刻意分開，這樣改資料庫不會直接打破前端契約，
也不會不小心把內部欄位外洩出去。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
