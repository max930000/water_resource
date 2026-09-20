"""
資料庫連線設定。

這個檔案只負責「怎麼跟資料庫講話」，
不定義任何表、不建表、不存任何資料。

注意：整個檔案不會 import fastapi —— 它跟 Web 框架完全無關。
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ── 1. 資料庫位置 ──────────────────────────────────────
# Path(__file__) 是「這個檔案本身」的路徑：
#   .resolve()     → 轉成絕對路徑
#   .parent        → app/
#   .parent.parent → backend/
#
# 用絕對路徑而不是 "./townquest.db"，是為了避免一個很難查的陷阱：
# "./" 指的是「執行指令時所在的資料夾」，所以從不同目錄啟動
# 會各自建出一個空的資料庫檔案，然後你會以為「資料不見了」。
#
# 之後換 PostgreSQL 時，只有這一行要改：
#   DATABASE_URL = "postgresql+psycopg://townquest:townquest@localhost:5432/townquest"
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'townquest.db'}"


# ── 2. Engine：連線池，整個程式只有一個 ────────────────
engine = create_engine(
    DATABASE_URL,
    # SQLite 專屬設定。
    # SQLite 預設禁止跨執行緒共用同一個連線，但 FastAPI 的同步端點
    # 會被丟到執行緒池執行，處理請求的執行緒跟建立連線的不一定相同，
    # 不關掉這個檢查就會噴：
    #   SQLite objects created in a thread can only be used in that same thread
    # 換成 PostgreSQL 時，這個參數要整段刪掉（PostgreSQL 沒這個限制）。
    connect_args={"check_same_thread": False},
    # 把 SQLAlchemy 實際產生的 SQL 印到終端機。
    # 開發階段一定要打開 —— 這是你唯一能看見「ORM 背後到底做了什麼」的方式。
    # 之後抓 N+1 問題全靠它。正式環境要關掉（太吵而且會洩漏資料）。
    echo=True,
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
