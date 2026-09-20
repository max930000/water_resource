"""
資料庫連線設定。

這個檔案只負責「怎麼跟資料庫講話」，
不定義任何表、不建表、不存任何資料。

注意：整個檔案不會 import fastapi —— 它跟 Web 框架完全無關。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ── 1. 資料庫位置 ──────────────────────────────────────
# sqlite:///./townquest.db
#   sqlite  → 用哪種資料庫
#   ///     → 後面接檔案路徑
#   ./      → 相對於「你執行 uvicorn 的那個資料夾」，也就是 backend/
#
# 之後換 PostgreSQL 時，只有這一行要改：
#   postgresql+psycopg://townquest:townquest@localhost:5432/townquest
DATABASE_URL = "sqlite:///./townquest.db"


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
