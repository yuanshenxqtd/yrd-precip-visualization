"""数据库引擎、会话与建表。

SQLite 调优要点（对应 docs/PLAN.md 风险 R7）：
    - journal_mode=WAL：允许采集器写入的同时后端读取，避免锁冲突
    - foreign_keys=ON：SQLite 默认不启用外键约束，必须显式打开
    - synchronous=NORMAL：WAL 模式下的推荐值，兼顾安全与性能
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


engine = create_engine(DATABASE_URL, echo=False, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    # 临时表放内存：既提速，也避免依赖磁盘临时目录
    # （本机系统临时目录不可用，见 config.py 的「临时目录自愈」）
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """建表。幂等：已存在的表不会被重建或清空。"""
    from . import models  # noqa: F401  确保所有模型注册到 Base.metadata

    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """事务性会话：正常提交，异常回滚。"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI 依赖注入入口（只读场景，不自动提交）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
