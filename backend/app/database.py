"""
資料庫連線設定。

這個檔案只負責「怎麼跟資料庫講話」，
不定義任何表、不建表、不存任何資料。

注意：整個檔案不會 import fastapi —— 它跟 Web 框架完全無關。
"""

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ── 1. 資料庫位置 ──────────────────────────────────────
# 優先讀環境變數 DATABASE_URL；沒設定就退回本機的 SQLite 檔案。
#
# 為什麼要這樣設計：
#   同一份程式碼要能跑在不同環境 —— 你的筆電用 SQLite，
#   Docker 裡用 PostgreSQL，正式機用雲端資料庫。
#   差別只在「啟動時給什麼環境變數」，程式碼一個字都不用改。
#   這是十二要素應用（12-Factor App）的核心原則：設定與程式碼分離。
#
# 絕對不要把正式環境的密碼寫死在程式裡 —— 那會跟著進 Git。
BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_URL = f"sqlite:///{BACKEND_DIR / 'townquest.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

IS_SQLITE = DATABASE_URL.startswith("sqlite")


# ── 2. Engine：連線池，整個程式只有一個 ────────────────
# connect_args 只有 SQLite 需要：
#   SQLite 預設禁止跨執行緒共用同一個連線，但 FastAPI 的同步端點
#   會被丟到執行緒池執行，處理請求的執行緒跟建立連線的不一定相同，
#   不關掉這個檢查就會噴：
#     SQLite objects created in a thread can only be used in that same thread
#   PostgreSQL 沒有這個限制，傳這個參數反而會出錯，所以要判斷。
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    # PostgreSQL 專屬：每次拿連線前先確認它還活著。
    # 資料庫重啟或連線閒置太久被切斷時，不加這個會拿到死掉的連線。
    pool_pre_ping=not IS_SQLITE,
    # 把 SQLAlchemy 實際產生的 SQL 印到終端機。
    # 開發時打開才看得見 ORM 背後做了什麼（抓 N+1 全靠它）。
    # 正式環境要關掉：太吵，而且日誌裡會出現使用者資料。
    echo=os.getenv("SQL_ECHO", "1") == "1",
)


# ── 2.5 ⚠ SQLite 必做：每條連線都要打開外鍵強制 ──────────
# SQLite 為了向後相容，**預設不強制外鍵約束**。
# 也就是說 models.py 裡的 ForeignKey 只是「宣告」，資料庫根本不檢查——
# 你可以寫入一個 station_id=888888 的回報，指向不存在的站點，
# 完全不會報錯。這種孤兒資料之後查詢時會神秘地消失或炸掉。
#
# 而且這個設定是「每條連線」而不是「每個資料庫」，
# 所以必須掛在 connect 事件上，讓每次新建連線都執行一次。
#
# PostgreSQL 預設就會強制外鍵，換過去之後這段不會生效（也不需要），
# 但留著無害 —— 所以用 dialect 判斷而不是直接刪掉。
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    # 只對 SQLite 生效。用 module 名稱判斷比用字串比對 URL 可靠。
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ── 3. SessionLocal：Session 的「工廠」 ────────────────
# 它本身不是 Session。要呼叫 SessionLocal() 才會生出一個 Session。
SessionLocal = sessionmaker(
    bind=engine,
    # autoflush=False
    #   預設 True 會在每次查詢前，自動把還沒 commit 的變更偷偷送去資料庫。
    #   關掉之後行為好預測：什麼時候寫入，由我們自己呼叫 commit() 決定。
    autoflush=False,
    # expire_on_commit=False
    #   預設 True 的話，commit() 之後物件的所有欄位會被標記為「過期」，
    #   你再讀 station.name 就會多打一次 SQL；如果 session 已經關了，直接爆錯。
    #   關掉它，commit 後照樣能安心讀取。
    expire_on_commit=False,
)


# ── 4. Base：所有 model 的共同父類別 ──────────────────
# 2-3 定義的每一張表都要繼承它。
# SQLAlchemy 靠這個類別收集「這個專案有哪些表」，
# 2-4 建表時才知道要建什麼。
class Base(DeclarativeBase):
    pass


# ── 5. get_db()：借出 session，用完保證歸還 ────────────
def get_db() -> Generator[Session, None, None]:
    """
    給 FastAPI 依賴注入用的函式。

    為什麼用 yield 而不是 return：
      FastAPI 看到 yield 會這樣處理——
        1. 先執行 yield 前面的部分（開 session）
        2. 把 yield 出來的 session 交給端點函式使用
        3. 端點執行完之後，回來執行 yield 後面的部分（關 session）

      用 return 就沒有第 3 步，session 永遠不會關，連線池遲早耗盡。

    try/finally 的作用：即使端點函式丟出例外，finally 也一定會執行，
    保證連線歸還。少了它，一個 500 錯誤就會漏掉一個連線。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
