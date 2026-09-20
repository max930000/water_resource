"""
資料表定義（ORM model）。

一個 class = 一張資料表，一個 mapped_column = 一個欄位。

這個檔案只描述「資料長什麼樣」：
  - 連線是 database.py 的事
  - API 的輸入輸出格式是之後 schemas.py 的事
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ReportType(str, enum.Enum):
    """
    回報的種類。

    為什麼繼承 str？
      這樣 ReportType.BROKEN 同時也是字串 "BROKEN"，
      可以直接丟進 JSON、直接跟字串比較，不用到處寫 .value。
      FastAPI 和 Pydantic 對 str Enum 的支援也最好。
    """

    BROKEN = "BROKEN"        # 設備故障
    NO_WATER = "NO_WATER"    # 沒有出水
    DIRTY = "DIRTY"          # 環境髒污
    GOOD = "GOOD"            # 狀況良好（正向回饋也要收，才知道哪些點維護得好）
    OTHER = "OTHER"


class ReportStatus(str, enum.Enum):
    """回報的處理狀態，對應維護單位的實際工作流程。"""

    OPEN = "OPEN"                  # 待處理
    IN_PROGRESS = "IN_PROGRESS"    # 處理中
    RESOLVED = "RESOLVED"          # 已完成
    REJECTED = "REJECTED"          # 不受理


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

    # ── 關聯：一座直飲臺有多筆回報 ──────────────────────
    # 這一行不會產生任何資料庫欄位，純粹是 Python 端的便利：
    # 寫 station.reports 就能拿到那座站的所有回報。
    #
    # cascade="all, delete-orphan"：刪掉 station 時，它底下的 report 也一起刪。
    # 沒有這個的話，刪 station 會留下一堆指向不存在站點的孤兒資料。
    reports: Mapped[list["Report"]] = relationship(
        back_populates="station", cascade="all, delete-orphan"
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


class Report(Base):
    """市民對某座直飲臺的回報。"""

    __tablename__ = "report"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ── 外鍵：指向 station.id ────────────────────────────
    # ForeignKey 是資料庫層級的約束，它保證：
    #   1. 你不可能寫入一個不存在的 station_id（資料庫會直接拒絕）
    #   2. ondelete="CASCADE" → 直接在資料庫刪掉 station 時，
    #      相關的 report 也會被自動刪除
    #
    # 為什麼 Station.reports 的 cascade 和這裡的 ondelete 都要寫？
    #   cascade="all, delete-orphan" 是「Python / SQLAlchemy 層」的規則
    #   ondelete="CASCADE"          是「資料庫層」的規則
    #   走 ORM 刪除時前者生效；有人直接下 SQL 刪除時後者生效。
    #   兩層都設，才是真的安全。
    station_id: Mapped[int] = mapped_column(
        ForeignKey("station.id", ondelete="CASCADE"), index=True
    )

    # ── Enum 欄位 ───────────────────────────────────────
    # native_enum=False 很重要：
    #   它讓 SQLAlchemy 存成 VARCHAR + CHECK 約束，
    #   而不是資料庫原生的 ENUM 型別。
    #   原因：SQLite 沒有 ENUM；PostgreSQL 有，但要新增一個 enum 值
    #   得寫 ALTER TYPE，migration 會變得很痛。用字串最好維護。
    type: Mapped[ReportType] = mapped_column(
        SAEnum(ReportType, native_enum=False, length=20)
    )

    description: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(ReportStatus, native_enum=False, length=20),
        # default 是「Python 端」的預設值，insert 時由 SQLAlchemy 填。
        # 跟 server_default（資料庫端）不同，兩者都可以，這裡用 Python 端比較直觀。
        default=ReportStatus.OPEN,
        index=True,
    )

    # 維護單位的處理回覆，會顯示給回報的市民看
    admin_note: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 關聯的另一半。back_populates 讓兩邊互相對應：
    # 設定 report.station 之後，station.reports 也會自動包含它。
    station: Mapped["Station"] = relationship(back_populates="reports")

    @property
    def station_name(self) -> str:
        """
        方便 API 直接回傳站名，不用讓前端再打一次 /stations/{id}。

        ⚠ 注意：這個 property 會觸發 self.station 的載入。
        查單筆沒問題，但查 100 筆回報時就會發出 100 次額外查詢（N+1）。
        所以列表查詢一定要用 selectinload 預先載入 —— main.py 裡有示範。
        """
        return self.station.name

    def __repr__(self) -> str:
        return f"<Report {self.id} station={self.station_id} {self.type} {self.status}>"
