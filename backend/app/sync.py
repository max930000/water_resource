"""
把 data.taipei 的開放資料同步進我們的資料庫。

執行：python -m app.sync

這支是「upsert」：已存在的更新、不存在的新增。
所以可以重複執行，不會產生重複資料。
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Station
from .opendata import TAIPEI_TZ, fetch_rows, to_station_dict


def sync_stations(db: Session) -> dict[str, int]:
    """回傳統計：抓了幾筆、新增幾筆、更新幾筆、跳過幾筆。"""
    rows = fetch_rows()

    # ── 關鍵效能決策：一次把現有資料全撈回來 ──────────────
    #
    # 天真的寫法會在迴圈裡逐筆查詢：
    #     for row in rows:
    #         station = db.scalar(select(Station).where(
    #             Station.external_id == row["直飲臺編號"]))
    # 那會對資料庫發出 739 次 SELECT —— 這就是惡名昭彰的 N+1 問題。
    #
    # 正確做法：一次查完，在記憶體裡做成字典查表。
    # 739 筆資料量很小，全部載入完全沒問題。
    # 資料量到幾十萬筆時才需要改成分批處理。
    existing: dict[str, Station] = {
        station.external_id: station for station in db.scalars(select(Station)).all()
    }
    print(f"資料庫現有 {len(existing)} 筆")

    now = datetime.now(TAIPEI_TZ)
    created = 0
    updated = 0
    skipped = 0

    for row in rows:
        values = to_station_dict(row)
        if values is None:
            skipped += 1
            continue

        station = existing.get(values["external_id"])

        if station is None:
            # 新增：Station(**values) 是把 dict 展開成關鍵字參數，
            # 等同 Station(external_id=..., name=..., ...)
            db.add(Station(**values, synced_at=now))
            created += 1
        else:
            # 更新：直接改物件的屬性就好，不用呼叫任何 save()。
            # SQLAlchemy 的「dirty checking」會在 commit 時
            # 自動偵測哪些欄位變了，只對變動的欄位發 UPDATE。
            for key, value in values.items():
                setattr(station, key, value)
            station.synced_at = now
            updated += 1

    # ── 一次 commit，不要在迴圈裡 commit ──────────────────
    #
    # 為什麼：
    #   1. 效能 —— 每次 commit 都要寫磁碟並同步，739 次會慢好幾十倍
    #   2. 原子性 —— 中途失敗時整批回滾，不會留下「一半新一半舊」的資料庫
    #
    # 這就是「交易」(transaction) 的意義：要麼全部成功，要麼全部沒發生。
    db.commit()

    return {
        "fetched": len(rows),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


def main() -> None:
    # with SessionLocal() as db: 離開時會自動 close()，
    # 即使中間丟例外也一樣 —— 跟 database.py 裡 get_db() 的 try/finally 同樣道理。
    with SessionLocal() as db:
        result = sync_stations(db)

    print()
    print("同步完成")
    print(f"  抓取 : {result['fetched']}")
    print(f"  新增 : {result['created']}")
    print(f"  更新 : {result['updated']}")
    print(f"  跳過 : {result['skipped']}")


if __name__ == "__main__":
    main()
