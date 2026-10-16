"""ORM 模型：7 张表。

字段定义与 docs/PLAN.md 第 5.2 节 DDL 一一对应。
幂等写入依赖 precip_hourly / precip_daily 上的唯一约束。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Region(Base):
    """行政区划：4 个省级 + 40 个市级 + 16 个区级 = 60 行。"""

    __tablename__ = "region"

    adcode: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)  # province/city/district
    parent_adcode: Mapped[str | None] = mapped_column(String(12), ForeignKey("region.adcode"))
    province: Mapped[str] = mapped_column(String(16), nullable=False)  # 上海/江苏/浙江/安徽
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    is_monitored: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    point: Mapped["GridPoint | None"] = relationship(back_populates="region", uselist=False)

    __table_args__ = (
        Index("idx_region_parent", "parent_adcode"),
        Index("idx_region_level", "level"),
    )

    def __repr__(self) -> str:
        return f"<Region {self.adcode} {self.name} ({self.level})>"


class GridPoint(Base):
    """采集点：一个被监测区域对应一个点，共 56 行。"""

    __tablename__ = "grid_point"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_adcode: Mapped[str] = mapped_column(
        String(12), ForeignKey("region.adcode"), nullable=False, unique=True
    )
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="open-meteo")
    label: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(String(19), nullable=False, default=_now)

    region: Mapped[Region] = relationship(back_populates="point")
    hourly: Mapped[list["PrecipHourly"]] = relationship(
        back_populates="point", cascade="all, delete-orphan"
    )
    daily: Mapped[list["PrecipDaily"]] = relationship(
        back_populates="point", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GridPoint {self.id} {self.region_adcode} ({self.lon},{self.lat})>"


class PrecipHourly(Base):
    """逐小时降水事实表（核心表）。"""

    __tablename__ = "precip_hourly"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    point_id: Mapped[int] = mapped_column(Integer, ForeignKey("grid_point.id"), nullable=False)
    obs_time: Mapped[str] = mapped_column(String(16), nullable=False)  # YYYY-MM-DDTHH:MM
    precip_mm: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="open-meteo")
    is_forecast: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(19), nullable=False, default=_now)

    point: Mapped[GridPoint] = relationship(back_populates="hourly")

    __table_args__ = (
        UniqueConstraint("point_id", "obs_time", "source", name="uq_hourly_point_time_source"),
        Index("idx_hourly_time", "obs_time"),
        Index("idx_hourly_point_time", "point_id", "obs_time"),
    )


class PrecipDaily(Base):
    """日降水汇总表：日累计、最大小时雨强、有雨小时数、国标等级。"""

    __tablename__ = "precip_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    point_id: Mapped[int] = mapped_column(Integer, ForeignKey("grid_point.id"), nullable=False)
    obs_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    precip_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    precip_max_hourly: Mapped[float | None] = mapped_column(Float)
    # 可为空：由日值接口回填的历史日期没有小时数据，此时为 NULL（区别于「确实 0 小时有雨」）
    rain_hours: Mapped[int | None] = mapped_column(Integer)
    rain_level: Mapped[str | None] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="open-meteo")
    created_at: Mapped[str] = mapped_column(String(19), nullable=False, default=_now)

    point: Mapped[GridPoint] = relationship(back_populates="daily")

    __table_args__ = (
        UniqueConstraint("point_id", "obs_date", "source", name="uq_daily_point_date_source"),
        Index("idx_daily_date", "obs_date"),
    )


class CollectLog(Base):
    """采集日志：审计与数据质量分析的数据来源。"""

    __tablename__ = "collect_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # realtime/backfill/manual
    started_at: Mapped[str] = mapped_column(String(19), nullable=False, default=_now)
    finished_at: Mapped[str | None] = mapped_column(String(19))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    points_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gap_filled_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_msg: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("idx_log_started", "started_at"),)


class WeatherAlert(Base):
    """气象预警（预留表，暂未接入数据源）。"""

    __tablename__ = "weather_alert"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_adcode: Mapped[str] = mapped_column(String(12), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)
    alert_level: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[str | None] = mapped_column(String(19))
    source: Mapped[str | None] = mapped_column(String(32))
    raw_json: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "region_adcode", "alert_type", "published_at", "source",
            name="uq_alert_region_type_time_source",
        ),
    )


class Meta(Base):
    """键值元数据：记录初始化时间、数据源、统计口径版本等。"""

    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(String(19), nullable=False, default=_now)
