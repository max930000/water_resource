"""
Alembic 的執行環境設定。

每次你下 alembic 指令，這個檔案都會被執行一次。
它負責回答三個問題：
  1. 資料庫在哪？           → config.set_main_option("sqlalchemy.url", ...)
  2. 程式期望的結構長怎樣？  → target_metadata = Base.metadata
  3. 怎麼產生 SQL？         → context.configure(...) 的參數
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── 讓 env.py 找得到 app 套件 ─────────────────────────────
# __file__ 是 alembic/env.py，parents[0] = alembic/，parents[1] = backend/
# 把 backend/ 加進 sys.path，下面才 import 得到 app.database。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import DATABASE_URL, Base  # noqa: E402
from app import models  # noqa: F401,E402

# ⚠ 上面那行 `from app import models` 看起來沒被使用，但絕對不能刪。
# Base.metadata 是在「model 的 class 被定義時」才登記表的，
# 沒有匯入 models，metadata 就是空的 —— autogenerate 會以為
# 「你一張表都沒有」，然後產生一個要把所有表 DROP 掉的 migration。
# 用 noqa 標註「我知道它沒被使用，這是刻意的」。

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── 資料庫位址 ────────────────────────────────────────────
# 從 app/database.py 讀，不要寫在 alembic.ini。
# 因為 alembic.ini 會進 Git —— 正式環境的帳號密碼寫進去就是資安事故。
# 附帶好處：程式和 migration 永遠指向同一個資料庫，不會改到不同的 DB。
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# ── 程式期望的結構 ────────────────────────────────────────
# Alembic 靠這個知道「你的 models.py 希望資料庫長什麼樣」，
# 再跟實際資料庫比對，自動產生差異的 migration。
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """離線模式：只輸出 SQL 文字，不真的連資料庫。

    用途：正式環境要求「先給我 SQL，人工審核過再執行」時使用。
    指令：alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """線上模式：真的連上資料庫執行 migration。平常用的就是這個。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # ── render_as_batch：SQLite 專屬，非常重要 ──
            # SQLite 幾乎不支援 ALTER TABLE：不能改欄位型別、不能刪欄位、
            # 不能加約束。不開這個，之後任何「修改既有欄位」的 migration
            # 在 SQLite 上都會直接失敗。
            # 開啟後 Alembic 會自動改用迂迴做法：
            #   建一張新表 → 複製資料 → 刪舊表 → 把新表改名
            # 之後換成 PostgreSQL 時留著也無害（會被忽略）。
            render_as_batch=True,
            # 連「欄位型別變了」也一起偵測。
            # 預設只比對欄位有無，String(200) 改成 String(500) 不會被發現。
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
