"""
建立資料表的一次性腳本。

執行方式（務必在 backend 資料夾，而且要用 -m）：
    python -m app.init_db

為什麼是 -m：
    直接跑檔案的話，Python 把它當獨立腳本，
    from .database import ... 會噴 "attempted relative import"。
    用 -m 以「模組」方式執行，__package__ 會被正確設成 app。
    （你剛剛已經親身踩過這個坑了。）
"""

from .database import Base, engine
from . import models  # noqa: F401


def main() -> None:
    print("建立資料表中…")
    # create_all 會掃過 Base.metadata 裡登記的每一張表，
    # 對「還不存在」的表下 CREATE TABLE。
    #
    # 重要限制：它不會修改已經存在的表。
    # 你之後改了 models.py 加一個欄位，再跑這支也不會生效——
    # 它看到 station 表已存在就跳過了。
    # 這就是為什麼正式專案要用 Alembic 做 migration（第 3 課導入）。
    Base.metadata.create_all(bind=engine)
    print("完成。已建立的表：", list(Base.metadata.tables.keys()))


if __name__ == "__main__":
    main()
