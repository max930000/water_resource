"""
資料表定義（ORM model）。

一個 class = 一張資料表，一個 mapped_column = 一個欄位。

這個檔案只描述「資料長什麼樣」：
  - 連線是 database.py 的事
  - API 的輸入輸出格式是之後 schemas.py 的事
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Station(Base):
    """
    直飲臺。

    資料來源：臺北市資料大平臺「臺北市所屬直飲臺」（臺北自來水事業處）
    rid: 181097e0-c171-4bcd-ad41-c7b55dbc616e
    """

    __tablename__ = "station"

    # ── 我們自己的主鍵 ──────────────────────────────
    # 不要拿開放資料的編號當主鍵：那是別人家的資料，
    # 對方改格式、重編號、或出現重複值，你的整個資料庫就毀了。
    # 自己的主鍵 + 一個 unique 的來源編號，才是安全的做法。
    id: Mapped[int] = mapped_column(primary_key=True)

    # ── 來源識別碼 ──────────────────────────────────
    # 開放資料的「直飲臺編號」。同步時用它判斷是新增還是更新（upsert）。
    # unique=True 保證不會重複，index=True 讓同步時的查詢走索引。
    external_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # ── 基本資料 ────────────────────────────────────
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    # 注意：這份資料集叫「臺北市所屬直飲臺」，但實際內容包含新北市的點
    # （北水處供水範圍跨到新北）。所以「市別」一定要存，不然之後會搞混。
    city: Mapped[str | None] = mapped_column(String(20), index=True)
    district: Mapped[str | None] = mapped_column(String(20), index=True)
    place_type: Mapped[str | None] = mapped_column(String(50))
    owner_unit: Mapped[str | None] = mapped_column(String(200))
    install_spot: Mapped[str | None] = mapped_column(String(300))
    open_hours: Mapped[str | None] = mapped_column(String(100))

    # ── 座標 ────────────────────────────────────────
    # 開放資料給的是字串（"121.548456"），匯入時要轉成 float。
    # 存成字串的話，之後完全沒辦法做範圍查詢和距離計算。
    lon: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)

    # ── 維護與水質 ──────────────────────────────────
    maintainer: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(30), index=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sampled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coliform: Mapped[str | None] = mapped_column(String(30))
    quality_url: Mapped[str | None] = mapped_column(String(500))
    photo_url: Mapped[str | None] = mapped_column(String(500))

    # ── 稽核欄位（我們自己加的，不是開放資料給的）──────
    # 記錄這筆資料是什麼時候從 data.taipei 同步進來的。
    # 評審問「你們的資料多新」時，這個欄位就是答案。
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── 複合索引 ────────────────────────────────────
    # 「查附近的直飲臺」會用經緯度範圍篩選（WHERE lat BETWEEN ? AND ?
    # AND lon BETWEEN ? AND ?）。兩個欄位一起建一個索引，
    # 比各自建一個快得多。
    __table_args__ = (Index("idx_station_latlon", "lat", "lon"),)

    def __repr__(self) -> str:
        # 除錯時在終端機 print 這個物件，會看到有用的資訊而不是
        # <app.models.Station object at 0x000001F8...>
        return f"<Station {self.external_id} {self.name!r} ({self.lat}, {self.lon})>"
