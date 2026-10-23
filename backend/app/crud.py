"""数据访问层：所有 SQL 聚合集中在此，路由层只负责 HTTP 语义。

设计约定：
    - 函数只接收 Session 与普通参数，返回可 JSON 序列化的 dict/list
    - 时间一律用字符串比较（obs_time 形如 2026-10-07T15:00，obs_date 形如 2026-10-07），
      字典序与时间序一致，SQLite 可直接比较，无需转换
"""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta
from typing import Any, Iterator, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import COLLECT_INTERVAL_MINUTES, OPENMETEO_SOURCE_NAME
from .levels import LEVEL_COLORS, classify
from .models import (
    CollectLog,
    GridPoint,
    Meta,
    PrecipDaily,
    PrecipHourly,
    Region,
    WeatherAlert,
)

TIME_FMT = "%Y-%m-%dT%H:%M"
DATE_FMT = "%Y-%m-%d"

# 距平基准年份：只用完整年份。
# 2023 仅含 9–12 月、2026 截至 10 月，均为不完整年份，混入会严重偏差。
COMPLETE_YEARS: tuple[int, ...] = (2024, 2025)

_NO_RAIN_COLOR = LEVEL_COLORS.get("无降水", "#2b3a55")


# ------------------------------------------------------------------ 小工具

def shift_hours(obs_time: str, hours: int) -> str:
    """在 'YYYY-MM-DDTHH:MM' 上加减小时。"""
    return (datetime.strptime(obs_time, TIME_FMT) + timedelta(hours=hours)).strftime(TIME_FMT)


def shift_days(obs_date: str, days: int) -> str:
    """在 'YYYY-MM-DD' 上加减天数。"""
    return (datetime.strptime(obs_date, DATE_FMT) + timedelta(days=days)).strftime(DATE_FMT)


def _five_number(values: Sequence[float]) -> dict[str, float]:
    """计算箱线图五数概括。"""
    vals = sorted(float(v) for v in values)
    n = len(vals)
    if n == 1:
        v = round(vals[0], 2)
        return {"min": v, "q1": v, "median": v, "q3": v, "max": v, "mean": v}
    q1, _q2, q3 = statistics.quantiles(vals, n=4, method="inclusive")
    return {
        "min": round(vals[0], 2),
        "q1": round(q1, 2),
        "median": round(statistics.median(vals), 2),
        "q3": round(q3, 2),
        "max": round(vals[-1], 2),
        "mean": round(sum(vals) / n, 2),
    }


def latest_observed_time(session: Session) -> str | None:
    """库内最新的实况整点时刻。"""
    return session.scalar(
        select(func.max(PrecipHourly.obs_time)).where(PrecipHourly.is_forecast == 0)
    )


def _point_id(session: Session, adcode: str | None) -> int | None:
    if not adcode:
        return None
    return session.scalar(select(GridPoint.id).where(GridPoint.region_adcode == adcode))


# ------------------------------------------------------------------ meta

def get_meta(session: Session) -> dict[str, Any]:
    hourly_rows = session.scalar(select(func.count()).select_from(PrecipHourly)) or 0
    daily_rows = session.scalar(select(func.count()).select_from(PrecipDaily)) or 0
    regions_total = session.scalar(select(func.count()).select_from(Region)) or 0
    points_total = session.scalar(select(func.count()).select_from(GridPoint)) or 0

    hourly_start, hourly_end = session.execute(
        select(func.min(PrecipHourly.obs_time), func.max(PrecipHourly.obs_time))
    ).one()

    # 实况与预报必须分开暴露：hourly_end 含预报，可能落在未来若干天，
    # 用它来表示「数据时刻」会误导用户（实测预报可到 6 天后）。
    # 数据时效判断只能用 observed_end。
    observed_start, observed_end = session.execute(
        select(func.min(PrecipHourly.obs_time), func.max(PrecipHourly.obs_time)).where(
            PrecipHourly.is_forecast == 0
        )
    ).one()
    forecast_end = session.scalar(
        select(func.max(PrecipHourly.obs_time)).where(PrecipHourly.is_forecast == 1)
    )

    daily_start, daily_end = session.execute(
        select(func.min(PrecipDaily.obs_date), func.max(PrecipDaily.obs_date))
    ).one()

    last_log = session.scalars(select(CollectLog).order_by(CollectLog.id.desc()).limit(1)).first()
    initialized = session.scalar(select(Meta.value).where(Meta.key == "db_initialized_at"))

    return {
        "data_source": OPENMETEO_SOURCE_NAME,
        "points_total": points_total,
        "regions_total": regions_total,
        "hourly_rows": hourly_rows,
        "daily_rows": daily_rows,
        "hourly_start": hourly_start,
        "hourly_end": hourly_end,
        "observed_start": observed_start,
        "observed_end": observed_end,
        "forecast_end": forecast_end,
        "server_now": datetime.now().replace(microsecond=0).isoformat(),
        "daily_start": daily_start,
        "daily_end": daily_end,
        "last_collect_at": last_log.started_at if last_log else None,
        "last_collect_status": last_log.status if last_log else None,
        "db_initialized_at": initialized,
        "collect_interval_minutes": COLLECT_INTERVAL_MINUTES,
    }


# ------------------------------------------------------------------ regions

def list_regions(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(select(Region).order_by(Region.adcode)).all()
    return [
        {
            "adcode": r.adcode,
            "name": r.name,
            "level": r.level,
            "parent_adcode": r.parent_adcode,
            "province": r.province,
            "lon": r.lon,
            "lat": r.lat,
            "is_monitored": r.is_monitored,
        }
        for r in rows
    ]


def region_map(session: Session) -> dict[str, dict[str, Any]]:
    return {r["adcode"]: r for r in list_regions(session)}


def region_detail(
    session: Session,
    adcode: str,
    *,
    hours: int = 48,
    days: int = 30,
    extremes_limit: int = 5,
) -> dict[str, Any] | None:
    """单个点位的详情档案，供前端「下钻抽屉」一次取全。

    把「近 N 小时逐小时 + 近 N 天逐日 + 历史等级分布 + 历史极值 + 汇总指标」
    合并为一个响应，避免下钻时打 4~5 个请求。
    返回 None 表示该 adcode 不存在或不是采集点（如省级区划）。
    """
    region = session.get(Region, adcode)
    if region is None:
        return None

    point_id = _point_id(session, adcode)
    if point_id is None:
        return None

    latest = session.scalar(
        select(func.max(PrecipHourly.obs_time)).where(
            PrecipHourly.point_id == point_id,
            PrecipHourly.is_forecast == 0,
        )
    )

    # ---------------------------------------------------------- 逐小时
    hourly: list[dict[str, Any]] = []
    if latest:
        start = shift_hours(latest, -(hours - 1))
        rows = session.execute(
            select(PrecipHourly.obs_time, PrecipHourly.precip_mm)
            .where(
                PrecipHourly.point_id == point_id,
                PrecipHourly.is_forecast == 0,
                PrecipHourly.obs_time >= start,
                PrecipHourly.obs_time <= latest,
            )
            .order_by(PrecipHourly.obs_time)
        ).all()
        hourly = [{"time": t, "value": round(float(v or 0.0), 1)} for t, v in rows]

    # ---------------------------------------------------------- 逐日
    daily: list[dict[str, Any]] = []
    last_date = session.scalar(
        select(func.max(PrecipDaily.obs_date)).where(PrecipDaily.point_id == point_id)
    )
    if last_date:
        start_date = shift_days(last_date, -(days - 1))
        rows = session.execute(
            select(
                PrecipDaily.obs_date,
                PrecipDaily.precip_sum,
                PrecipDaily.precip_max_hourly,
                PrecipDaily.rain_level,
            )
            .where(
                PrecipDaily.point_id == point_id,
                PrecipDaily.obs_date >= start_date,
                PrecipDaily.obs_date <= last_date,
            )
            .order_by(PrecipDaily.obs_date)
        ).all()
        daily = [
            {
                "time": d,
                "value": round(float(total or 0.0), 1),
                "max": round(float(peak), 1) if peak is not None else None,
                "level": level,
            }
            for d, total, peak, level in rows
        ]

    # ---------------------------------------------------------- 汇总
    total_records = (
        session.scalar(
            select(func.count())
            .select_from(PrecipHourly)
            .where(PrecipHourly.point_id == point_id, PrecipHourly.is_forecast == 0)
        )
        or 0
    )
    first_time = session.scalar(
        select(func.min(PrecipHourly.obs_time)).where(
            PrecipHourly.point_id == point_id, PrecipHourly.is_forecast == 0
        )
    )

    peak_hour = max(hourly, key=lambda x: x["value"], default=None)
    peak_day = max(daily, key=lambda x: x["value"], default=None)
    historic_peak = session.execute(
        select(PrecipDaily.obs_date, PrecipDaily.precip_sum)
        .where(PrecipDaily.point_id == point_id)
        .order_by(PrecipDaily.precip_sum.desc())
        .limit(1)
    ).first()

    summary = {
        "latest_time": latest,
        "latest_value": hourly[-1]["value"] if hourly else None,
        "sum_hours": round(sum(x["value"] for x in hourly), 1),
        "peak_hour_value": peak_hour["value"] if peak_hour else None,
        "peak_hour_time": peak_hour["time"] if peak_hour else None,
        "sum_days": round(sum(x["value"] for x in daily), 1),
        "rain_days": sum(1 for x in daily if x["value"] > 0),
        "peak_day_value": peak_day["value"] if peak_day else None,
        "peak_day_date": peak_day["time"] if peak_day else None,
        "first_time": first_time,
        "total_records": total_records,
        "historic_max": round(float(historic_peak[1] or 0.0), 1) if historic_peak else None,
        "historic_max_date": historic_peak[0] if historic_peak else None,
    }

    return {
        "region": {
            "adcode": region.adcode,
            "name": region.name,
            "level": region.level,
            "parent_adcode": region.parent_adcode,
            "province": region.province,
            "lon": region.lon,
            "lat": region.lat,
            "is_monitored": region.is_monitored,
        },
        "hours": hours,
        "days": days,
        "hourly": hourly,
        "daily": daily,
        "levels": trend_level_distribution(session, adcode=adcode),
        "extremes": trend_extremes(session, adcode=adcode, limit=extremes_limit),
        "summary": summary,
    }


# ------------------------------------------------------------------ overview

def overview_summary(session: Session) -> dict[str, Any]:
    latest = latest_observed_time(session)
    points_total = session.scalar(select(func.count()).select_from(GridPoint)) or 0
    forecast_hours = (
        session.scalar(
            select(func.count()).select_from(PrecipHourly).where(PrecipHourly.is_forecast == 1)
        )
        or 0
    )

    summary: dict[str, Any] = {
        "latest_obs_time": latest,
        "points_total": points_total,
        "points_with_rain": 0,
        "rain_coverage_pct": 0.0,
        "sum_24h_mm": 0.0,
        "max_hourly_mm": None,
        "max_hourly_point": None,
        "max_hourly_time": None,
        "wettest_point": None,
        "wettest_24h_mm": 0.0,
        "today_wettest_point": None,
        "today_wettest_mm": 0.0,
        "forecast_hours": forecast_hours,
    }

    last_log = session.scalars(select(CollectLog).order_by(CollectLog.id.desc()).limit(1)).first()
    summary["last_collect_at"] = last_log.started_at if last_log else None
    summary["last_collect_status"] = last_log.status if last_log else None

    if latest is None:
        return summary

    # 当前时刻有降水的点位
    summary["points_with_rain"] = (
        session.scalar(
            select(func.count())
            .select_from(PrecipHourly)
            .where(
                PrecipHourly.is_forecast == 0,
                PrecipHourly.obs_time == latest,
                PrecipHourly.precip_mm > 0,
            )
        )
        or 0
    )
    if points_total:
        summary["rain_coverage_pct"] = round(100 * summary["points_with_rain"] / points_total, 1)

    # 近 24 小时窗口（含当前时刻，共 24 个整点）
    window_start = shift_hours(latest, -23)
    window = (
        PrecipHourly.is_forecast == 0,
        PrecipHourly.obs_time >= window_start,
        PrecipHourly.obs_time <= latest,
    )

    summary["sum_24h_mm"] = round(
        float(
            session.scalar(
                select(func.coalesce(func.sum(PrecipHourly.precip_mm), 0.0)).where(*window)
            )
            or 0.0
        ),
        1,
    )

    peak = session.execute(
        select(PrecipHourly.precip_mm, PrecipHourly.obs_time, GridPoint.label)
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .where(*window)
        .order_by(PrecipHourly.precip_mm.desc())
        .limit(1)
    ).first()
    if peak and peak[0] is not None and float(peak[0]) > 0:
        summary["max_hourly_mm"] = round(float(peak[0]), 1)
        summary["max_hourly_time"] = peak[1]
        summary["max_hourly_point"] = peak[2]

    wettest = session.execute(
        select(GridPoint.label, func.sum(PrecipHourly.precip_mm).label("total"))
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .where(*window)
        .group_by(GridPoint.id)
        .order_by(func.sum(PrecipHourly.precip_mm).desc())
        .limit(1)
    ).first()
    if wettest and wettest[1] is not None and float(wettest[1]) > 0:
        summary["wettest_point"] = wettest[0]
        summary["wettest_24h_mm"] = round(float(wettest[1]), 1)

    # 今日累计最多点位（来自日汇总表）
    today = session.scalar(
        select(func.max(PrecipDaily.obs_date)).where(PrecipDaily.source == OPENMETEO_SOURCE_NAME)
    )
    if today:
        row = session.execute(
            select(GridPoint.label, PrecipDaily.precip_sum)
            .join(GridPoint, GridPoint.id == PrecipDaily.point_id)
            .where(PrecipDaily.obs_date == today)
            .order_by(PrecipDaily.precip_sum.desc())
            .limit(1)
        ).first()
        if row and float(row[1] or 0) > 0:
            summary["today_wettest_point"] = row[0]
            summary["today_wettest_mm"] = round(float(row[1] or 0), 1)

    return summary


def overview_ranking(session: Session, *, limit: int = 10, hours: int = 24) -> list[dict[str, Any]]:
    latest = latest_observed_time(session)
    if latest is None:
        return []
    start = shift_hours(latest, -(hours - 1))
    rows = session.execute(
        select(
            GridPoint.region_adcode,
            GridPoint.label,
            Region.province,
            func.sum(PrecipHourly.precip_mm).label("total"),
            func.max(PrecipHourly.precip_mm).label("peak"),
        )
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .join(Region, Region.adcode == GridPoint.region_adcode)
        .where(
            PrecipHourly.is_forecast == 0,
            PrecipHourly.obs_time >= start,
            PrecipHourly.obs_time <= latest,
        )
        .group_by(GridPoint.id)
        .order_by(func.sum(PrecipHourly.precip_mm).desc())
        .limit(limit)
    ).all()
    return [
        {
            "adcode": r[0],
            "name": r[1],
            "province": r[2],
            "total": round(float(r[3] or 0), 1),
            "peak": round(float(r[4]), 1) if r[4] is not None else None,
        }
        for r in rows
    ]


def overview_highlights(
    session: Session, *, hours: int = 24, window_days: int = 30
) -> dict[str, Any]:
    """总览页「自动摘要」所需的素材。

    **返回结构化事实，而不是成品句子。**
    句式与措辞留给前端，这样同一批事实可以同时用于：
    · 总览页顶部的「读图要点」
    · 聚焦某点位时的要点
    · 将来导出简报

    计算口径与 overview_summary 保持一致（实况、含当前时刻、逐小时求和）。
    """
    latest = latest_observed_time(session)
    points_total = session.scalar(select(func.count()).select_from(GridPoint)) or 0

    result: dict[str, Any] = {
        "latest_obs_time": latest,
        "hours": hours,
        "window_days": window_days,
        "points_total": points_total,
        "current": None,
        "previous": None,
        "strongest_day": None,
        "rain_days": 0,
    }
    if latest is None:
        return result

    start = shift_hours(latest, -(hours - 1))
    window = (
        PrecipHourly.is_forecast == 0,
        PrecipHourly.obs_time >= start,
        PrecipHourly.obs_time <= latest,
    )

    total = float(
        session.scalar(
            select(func.coalesce(func.sum(PrecipHourly.precip_mm), 0.0)).where(*window)
        )
        or 0.0
    )

    # 窗口内累计降水 > 0 的点位数（不是「当前时刻有雨」，而是「整段窗口下过雨」）
    wet_points = (
        session.scalar(
            select(func.count()).select_from(
                select(PrecipHourly.point_id)
                .where(*window)
                .group_by(PrecipHourly.point_id)
                .having(func.sum(PrecipHourly.precip_mm) > 0)
                .subquery()
            )
        )
        or 0
    )

    peak_row = session.execute(
        select(
            PrecipHourly.precip_mm,
            PrecipHourly.obs_time,
            GridPoint.region_adcode,
            GridPoint.label,
        )
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .where(*window)
        .order_by(PrecipHourly.precip_mm.desc())
        .limit(1)
    ).first()

    wettest_row = session.execute(
        select(
            GridPoint.region_adcode,
            GridPoint.label,
            func.sum(PrecipHourly.precip_mm).label("total"),
        )
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .where(*window)
        .group_by(GridPoint.id)
        .order_by(func.sum(PrecipHourly.precip_mm).desc())
        .limit(1)
    ).first()

    result["current"] = {
        "total_mm": round(total, 1),
        "wet_points": int(wet_points),
        "points_total": points_total,
        "dry": round(total, 1) == 0.0,
        "peak": (
            {
                "adcode": peak_row[2],
                "name": peak_row[3],
                "value": round(float(peak_row[0]), 1),
                "time": peak_row[1],
            }
            if peak_row and peak_row[0] is not None and float(peak_row[0]) > 0
            else None
        ),
        "wettest": (
            {
                "adcode": wettest_row[0],
                "name": wettest_row[1],
                "value": round(float(wettest_row[2]), 1),
            }
            if wettest_row and wettest_row[2] is not None and float(wettest_row[2]) > 0
            else None
        ),
    }

    # 上一个同长度窗口，用于「比前 N 小时偏多 / 偏少」
    prev_end = shift_hours(start, -1)
    prev_start = shift_hours(start, -hours)
    prev_total = float(
        session.scalar(
            select(func.coalesce(func.sum(PrecipHourly.precip_mm), 0.0)).where(
                PrecipHourly.is_forecast == 0,
                PrecipHourly.obs_time >= prev_start,
                PrecipHourly.obs_time <= prev_end,
            )
        )
        or 0.0
    )
    change_pct = round(100 * (total - prev_total) / prev_total, 1) if prev_total > 0 else None
    result["previous"] = {"total_mm": round(prev_total, 1), "change_pct": change_pct}

    # 近 N 天最强的一天，以及那天的最强点位
    last_date = session.scalar(
        select(func.max(PrecipDaily.obs_date)).where(PrecipDaily.source == OPENMETEO_SOURCE_NAME)
    )
    if last_date:
        first_date = shift_days(last_date, -(window_days - 1))
        result["rain_days"] = int(
            session.scalar(
                select(func.count(func.distinct(PrecipDaily.obs_date))).where(
                    PrecipDaily.obs_date >= first_date,
                    PrecipDaily.obs_date <= last_date,
                    PrecipDaily.precip_sum > 0,
                )
            )
            or 0
        )

        best_day = session.execute(
            select(PrecipDaily.obs_date, func.sum(PrecipDaily.precip_sum).label("total"))
            .where(
                PrecipDaily.obs_date >= first_date,
                PrecipDaily.obs_date <= last_date,
            )
            .group_by(PrecipDaily.obs_date)
            .order_by(func.sum(PrecipDaily.precip_sum).desc())
            .limit(1)
        ).first()

        if best_day and best_day[1] is not None:
            point_row = session.execute(
                select(
                    GridPoint.region_adcode,
                    GridPoint.label,
                    PrecipDaily.precip_sum,
                    PrecipDaily.precip_max_hourly,
                    PrecipDaily.rain_level,
                )
                .join(GridPoint, GridPoint.id == PrecipDaily.point_id)
                .where(PrecipDaily.obs_date == best_day[0])
                .order_by(PrecipDaily.precip_sum.desc())
                .limit(1)
            ).first()
            result["strongest_day"] = {
                "date": best_day[0],
                "total_mm": round(float(best_day[1]), 1),
                "peak": (
                    {
                        "adcode": point_row[0],
                        "name": point_row[1],
                        "value": round(float(point_row[2] or 0), 1),
                        "max_hourly": (
                            round(float(point_row[3]), 1) if point_row[3] is not None else None
                        ),
                        "level": point_row[4],
                    }
                    if point_row
                    else None
                ),
            }

    return result


# ------------------------------------------------------------------ realtime / spatial

def _map_points(session: Session, obs_time: str) -> list[dict[str, Any]]:
    """取指定时刻全部点位的降水值。"""
    rows = session.execute(
        select(
            Region.adcode,
            Region.name,
            Region.province,
            GridPoint.lon,
            GridPoint.lat,
            GridPoint.label,
            PrecipHourly.precip_mm,
        )
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .join(Region, Region.adcode == GridPoint.region_adcode)
        .where(PrecipHourly.obs_time == obs_time, PrecipHourly.is_forecast == 0)
        .order_by(Region.adcode)
    ).all()

    points: list[dict[str, Any]] = []
    for adcode, name, province, lon, lat, label, mm in rows:
        value = round(float(mm), 1) if mm is not None else None
        level = classify(value, hours=24) if value is not None else None
        points.append(
            {
                "adcode": adcode,
                "name": label or name,
                "province": province,
                "lon": lon,
                "lat": lat,
                "value": value,
                "level": level,
                "color": LEVEL_COLORS.get(level or "", _NO_RAIN_COLOR),
            }
        )
    return points


def realtime_latest(session: Session) -> dict[str, Any]:
    latest = latest_observed_time(session)
    if latest is None:
        return {"time": None, "points": [], "daily": []}

    daily = session.execute(
        select(GridPoint.region_adcode, PrecipDaily.precip_sum, PrecipDaily.rain_level)
        .join(GridPoint, GridPoint.id == PrecipDaily.point_id)
        .where(PrecipDaily.obs_date == latest[:10])
    ).all()

    return {
        "time": latest,
        "points": _map_points(session, latest),
        "daily": [
            {"adcode": r[0], "value": round(float(r[1] or 0), 1), "level": r[2]} for r in daily
        ],
    }


def realtime_timeseries(session: Session, *, adcode: str | None = None, hours: int = 48) -> dict[str, Any]:
    latest = latest_observed_time(session)
    if latest is None:
        return {"adcode": adcode, "start": None, "end": None, "points": []}
    start = shift_hours(latest, -(hours - 1))

    stmt = (
        select(PrecipHourly.obs_time, func.sum(PrecipHourly.precip_mm).label("total"))
        .where(
            PrecipHourly.is_forecast == 0,
            PrecipHourly.obs_time >= start,
            PrecipHourly.obs_time <= latest,
        )
        .group_by(PrecipHourly.obs_time)
        .order_by(PrecipHourly.obs_time)
    )
    point_id = _point_id(session, adcode)
    if point_id:
        stmt = stmt.where(PrecipHourly.point_id == point_id)

    rows = session.execute(stmt).all()
    return {
        "adcode": adcode,
        "start": start,
        "end": latest,
        "points": [{"time": r[0], "value": round(float(r[1] or 0), 1)} for r in rows],
    }


def spatial_map(session: Session, obs_time: str | None = None) -> dict[str, Any]:
    t = obs_time or latest_observed_time(session)
    if t is None:
        return {"time": None, "points": []}
    return {"time": t, "points": _map_points(session, t)}


def spatial_field(
    session: Session,
    *,
    time: str | None = None,
    step: float = 0.12,
    power: float = 2.0,
) -> dict[str, Any]:
    """用反距离加权（IDW）把 56 个点位插值成规则网格上的连续降水场。

    取最近 `k=12` 个点参与加权（全量 56 个会让远处点贡献过多噪声），
    权重 w = 1 / d^power，落点重合时直接取该点值。

    返回 **一维 row-major 网格**（index = row * cols + col），
    由前端按下面的字段还原经纬度，避免 JSON 里塞几十万个坐标。
    """
    import numpy as np

    t = time or latest_observed_time(session)
    if t is None:
        return {
            "obs_time": "",
            "lon_min": 0.0,
            "lon_max": 0.0,
            "lat_min": 0.0,
            "lat_max": 0.0,
            "step": step,
            "cols": 0,
            "rows": 0,
            "max_value": 0.0,
            "point_count": 0,
            "values": [],
        }

    rows = session.execute(
        select(GridPoint.lon, GridPoint.lat, PrecipHourly.precip_mm)
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .where(
            PrecipHourly.is_forecast == 0,
            PrecipHourly.obs_time == t,
            PrecipHourly.precip_mm.is_not(None),
        )
    ).all()

    if not rows:
        return {
            "obs_time": t,
            "lon_min": 0.0,
            "lon_max": 0.0,
            "lat_min": 0.0,
            "lat_max": 0.0,
            "step": step,
            "cols": 0,
            "rows": 0,
            "max_value": 0.0,
            "point_count": 0,
            "values": [],
        }

    src_lon = np.array([float(r[0]) for r in rows], dtype=np.float64)
    src_lat = np.array([float(r[1]) for r in rows], dtype=np.float64)
    src_val = np.array([float(r[2] or 0.0) for r in rows], dtype=np.float64)

    pad = 0.15
    lon_min = float(src_lon.min()) - pad
    lon_max = float(src_lon.max()) + pad
    lat_min = float(src_lat.min()) - pad
    lat_max = float(src_lat.max()) + pad

    cols = int(round((lon_max - lon_min) / step)) + 1
    rows_n = int(round((lat_max - lat_min) / step)) + 1
    # 上限保护：避免有人传极小 step 把服务打爆
    cols = min(cols, 400)
    rows_n = min(rows_n, 400)
    lon_max = lon_min + (cols - 1) * step
    lat_max = lat_min + (rows_n - 1) * step

    gx = np.linspace(lon_min, lon_max, cols)
    gy = np.linspace(lat_min, lat_max, rows_n)
    gxx, gyy = np.meshgrid(gx, gy)

    # 距离矩阵：rows_n × cols × n_points
    d2 = (gxx[..., None] - src_lon) ** 2 + (gyy[..., None] - src_lat) ** 2
    np.maximum(d2, 1e-10, out=d2)

    k = min(12, len(src_val))
    if k < len(src_val):
        # 只保留最近的 k 个点参与加权
        nearest = np.argpartition(d2, k - 1, axis=-1)[..., :k]
        d2k = np.take_along_axis(d2, nearest, axis=-1)
        valk = src_val[nearest]
    else:
        d2k = d2
        valk = np.broadcast_to(src_val, d2.shape)

    w = 1.0 / np.power(d2k, power / 2.0)
    field = (w * valk).sum(axis=-1) / w.sum(axis=-1)
    field = np.clip(field, 0.0, None)

    return {
        "obs_time": t,
        "lon_min": round(lon_min, 4),
        "lon_max": round(lon_max, 4),
        "lat_min": round(lat_min, 4),
        "lat_max": round(lat_max, 4),
        "step": step,
        "cols": cols,
        "rows": rows_n,
        "max_value": round(float(field.max()), 2),
        "point_count": int(len(src_val)),
        "values": [round(float(v), 2) for v in field.ravel()],
    }


def spatial_timespan(
    session: Session, *, start: str, end: str, max_frames: int = 48
) -> list[dict[str, Any]]:
    """取时间区间内的若干帧，供前端时间轴回放使用。"""
    times = list(
        session.scalars(
            select(PrecipHourly.obs_time)
            .where(
                PrecipHourly.is_forecast == 0,
                PrecipHourly.obs_time >= start,
                PrecipHourly.obs_time <= end,
            )
            .distinct()
            .order_by(PrecipHourly.obs_time)
        ).all()
    )
    if not times:
        return []

    if len(times) > max_frames:
        step = len(times) / max_frames
        times = [times[min(int(i * step), len(times) - 1)] for i in range(max_frames)]

    rows = session.execute(
        select(PrecipHourly.obs_time, Region.adcode, PrecipHourly.precip_mm)
        .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
        .join(Region, Region.adcode == GridPoint.region_adcode)
        .where(PrecipHourly.obs_time.in_(times), PrecipHourly.is_forecast == 0)
    ).all()

    frames: dict[str, dict[str, float | None]] = {t: {} for t in times}
    for obs_time, adcode, mm in rows:
        frames[obs_time][adcode] = round(float(mm), 1) if mm is not None else None

    return [{"time": t, "values": frames[t]} for t in times]


# ------------------------------------------------------------------ trend

def trend_daily(
    session: Session, *, adcode: str | None, start: str, end: str
) -> dict[str, Any]:
    stmt = (
        select(
            PrecipDaily.obs_date,
            func.sum(PrecipDaily.precip_sum).label("total"),
            func.max(PrecipDaily.precip_sum).label("peak"),
        )
        .where(PrecipDaily.obs_date >= start, PrecipDaily.obs_date <= end)
        .group_by(PrecipDaily.obs_date)
        .order_by(PrecipDaily.obs_date)
    )
    point_id = _point_id(session, adcode)
    if point_id:
        stmt = stmt.where(PrecipDaily.point_id == point_id)
    else:
        # 不带 adcode 时按点位数取平均，避免「总和」随点位数变化
        stmt = (
            select(
                PrecipDaily.obs_date,
                func.avg(PrecipDaily.precip_sum).label("total"),
                func.max(PrecipDaily.precip_sum).label("peak"),
            )
            .where(PrecipDaily.obs_date >= start, PrecipDaily.obs_date <= end)
            .group_by(PrecipDaily.obs_date)
            .order_by(PrecipDaily.obs_date)
        )

    rows = session.execute(stmt).all()
    return {
        "adcode": adcode,
        "start": start,
        "end": end,
        "points": [
            {"time": r[0], "value": round(float(r[1] or 0), 1), "max": round(float(r[2] or 0), 1)}
            for r in rows
        ],
    }


def trend_monthly(session: Session, *, adcode: str | None, year: int) -> dict[str, Any]:
    month = func.substr(PrecipDaily.obs_date, 1, 7)
    stmt = (
        select(month.label("m"), func.sum(PrecipDaily.precip_sum).label("total"))
        .where(func.substr(PrecipDaily.obs_date, 1, 4) == str(year))
        .group_by(month)
        .order_by(month)
    )
    point_id = _point_id(session, adcode)
    if point_id:
        stmt = stmt.where(PrecipDaily.point_id == point_id)

    rows = session.execute(stmt).all()
    return {
        "adcode": adcode,
        "year": year,
        "points": [{"time": r[0], "value": round(float(r[1] or 0), 1)} for r in rows],
    }


def trend_anomaly(
    session: Session,
    *,
    adcode: str | None = None,
    year: int | None = None,
    baseline_years: Sequence[int] = COMPLETE_YEARS,
) -> list[dict[str, Any]]:
    """降水距平：当月实际值 vs 同期基准值（仅用完整年份）。"""
    target_year = year or date.today().year
    point_id = _point_id(session, adcode)

    def monthly_sums(y: int) -> dict[str, float]:
        month = func.substr(PrecipDaily.obs_date, 1, 7)
        stmt = (
            select(month.label("m"), func.sum(PrecipDaily.precip_sum).label("total"))
            .where(func.substr(PrecipDaily.obs_date, 1, 4) == str(y))
            .group_by(month)
        )
        if point_id:
            stmt = stmt.where(PrecipDaily.point_id == point_id)
        return {m: float(t or 0) for m, t in session.execute(stmt).all()}

    actual = monthly_sums(target_year)
    baseline: dict[str, list[float]] = {}
    for y in baseline_years:
        for m, total in monthly_sums(y).items():
            baseline.setdefault(m[5:], []).append(total)

    result: list[dict[str, Any]] = []
    for m in sorted(actual):
        same_month = baseline.get(m[5:], [])
        base = sum(same_month) / len(same_month) if same_month else 0.0
        a = actual[m]
        pct = round((a - base) / base * 100, 1) if base > 0 else None
        result.append(
            {
                "month": m,
                "actual": round(a, 1),
                "baseline": round(base, 1),
                "anomaly_pct": pct,
            }
        )
    return result


def trend_level_distribution(
    session: Session, *, start: str | None = None, end: str | None = None, adcode: str | None = None
) -> list[dict[str, Any]]:
    stmt = select(PrecipDaily.rain_level, func.count().label("c")).group_by(PrecipDaily.rain_level)
    if start:
        stmt = stmt.where(PrecipDaily.obs_date >= start)
    if end:
        stmt = stmt.where(PrecipDaily.obs_date <= end)
    point_id = _point_id(session, adcode)
    if point_id:
        stmt = stmt.where(PrecipDaily.point_id == point_id)

    rows = session.execute(stmt.order_by(func.count().desc())).all()
    order = ["无降水", "小雨", "中雨", "大雨", "暴雨", "大暴雨", "特大暴雨"]
    items = [
        {"rain_level": r[0] or "未知", "count": r[1], "color": LEVEL_COLORS.get(r[0] or "", _NO_RAIN_COLOR)}
        for r in rows
    ]
    items.sort(key=lambda x: order.index(x["rain_level"]) if x["rain_level"] in order else 99)
    return items


def trend_extremes(
    session: Session,
    *,
    start: str | None = None,
    end: str | None = None,
    adcode: str | None = None,
    min_mm: float | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """历史极端降水事件（单日单点），按日累计降序。

    用于「预警统计」模块的极值榜；`min_mm` 可按国标阈值过滤
    （例如 50 表示只看暴雨及以上）。
    """
    stmt = (
        select(
            GridPoint.region_adcode,
            GridPoint.label,
            Region.province,
            PrecipDaily.obs_date,
            PrecipDaily.precip_sum,
            PrecipDaily.precip_max_hourly,
            PrecipDaily.rain_hours,
            PrecipDaily.rain_level,
        )
        .join(GridPoint, GridPoint.id == PrecipDaily.point_id)
        .join(Region, Region.adcode == GridPoint.region_adcode)
        .where(PrecipDaily.precip_sum > 0)
        .order_by(PrecipDaily.precip_sum.desc())
        .limit(limit)
    )
    if start:
        stmt = stmt.where(PrecipDaily.obs_date >= start)
    if end:
        stmt = stmt.where(PrecipDaily.obs_date <= end)
    if min_mm is not None:
        stmt = stmt.where(PrecipDaily.precip_sum >= min_mm)
    point_id = _point_id(session, adcode)
    if point_id:
        stmt = stmt.where(PrecipDaily.point_id == point_id)

    return [
        {
            "adcode": r[0],
            "name": r[1],
            "province": r[2],
            "obs_date": r[3],
            "precip_sum": round(float(r[4] or 0), 1),
            "precip_max_hourly": round(float(r[5]), 1) if r[5] is not None else None,
            "rain_hours": int(r[6]) if r[6] is not None else None,
            "rain_level": r[7],
            "color": LEVEL_COLORS.get(r[7] or "", _NO_RAIN_COLOR),
        }
        for r in session.execute(stmt).all()
    ]


# ------------------------------------------------------------------ compare

def compare_ranking(
    session: Session, *, start: str, end: str, limit: int = 20
) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            GridPoint.region_adcode,
            GridPoint.label,
            Region.province,
            func.sum(PrecipDaily.precip_sum).label("total"),
            func.max(PrecipDaily.precip_max_hourly).label("peak"),
        )
        .join(GridPoint, GridPoint.id == PrecipDaily.point_id)
        .join(Region, Region.adcode == GridPoint.region_adcode)
        .where(PrecipDaily.obs_date >= start, PrecipDaily.obs_date <= end)
        .group_by(GridPoint.id)
        .order_by(func.sum(PrecipDaily.precip_sum).desc())
        .limit(limit)
    ).all()
    return [
        {
            "adcode": r[0],
            "name": r[1],
            "province": r[2],
            "total": round(float(r[3] or 0), 1),
            "peak": round(float(r[4]), 1) if r[4] is not None else None,
        }
        for r in rows
    ]


def compare_multi(
    session: Session, *, adcodes: Sequence[str], start: str, end: str
) -> dict[str, Any]:
    """多城市日降水序列对比。"""
    id_by_adcode = {a: _point_id(session, a) for a in adcodes}
    id_by_adcode = {a: pid for a, pid in id_by_adcode.items() if pid}
    if not id_by_adcode:
        return {"start": start, "end": end, "series": []}

    regions = region_map(session)
    rows = session.execute(
        select(PrecipDaily.point_id, PrecipDaily.obs_date, PrecipDaily.precip_sum)
        .where(
            PrecipDaily.point_id.in_(list(id_by_adcode.values())),
            PrecipDaily.obs_date >= start,
            PrecipDaily.obs_date <= end,
        )
        .order_by(PrecipDaily.obs_date)
    ).all()

    data: dict[int, dict[str, float]] = {pid: {} for pid in id_by_adcode.values()}
    for pid, obs_date, total in rows:
        data[pid][obs_date] = round(float(total or 0), 1)

    series = [
        {
            "adcode": adcode,
            "name": regions.get(adcode, {}).get("name", adcode),
            "points": [
                {"time": d, "value": v} for d, v in sorted(data[pid].items())
            ],
        }
        for adcode, pid in id_by_adcode.items()
    ]
    return {"start": start, "end": end, "series": series}


def compare_boxplot(
    session: Session, *, start: str, end: str, limit: int = 10
) -> list[dict[str, Any]]:
    """各点位日降水的箱线统计（取区间内累计最多的前 limit 个点位）。"""
    top = compare_ranking(session, start=start, end=end, limit=limit)
    if not top:
        return []

    adcodes = [t["adcode"] for t in top]
    id_by_adcode = {a: _point_id(session, a) for a in adcodes}
    id_by_adcode = {a: pid for a, pid in id_by_adcode.items() if pid}
    inv = {pid: a for a, pid in id_by_adcode.items()}
    if not inv:
        return []

    rows = session.execute(
        select(PrecipDaily.point_id, PrecipDaily.precip_sum).where(
            PrecipDaily.point_id.in_(list(inv)),
            PrecipDaily.obs_date >= start,
            PrecipDaily.obs_date <= end,
        )
    ).all()

    grouped: dict[int, list[float]] = {}
    for pid, total in rows:
        grouped.setdefault(pid, []).append(float(total or 0))

    result: list[dict[str, Any]] = []
    for pid, values in grouped.items():
        if not values:
            continue
        adcode = inv[pid]
        stats = _five_number(values)
        result.append(
            {
                "adcode": adcode,
                "name": next((t["name"] for t in top if t["adcode"] == adcode), adcode),
                "province": next((t["province"] for t in top if t["adcode"] == adcode), ""),
                **stats,
            }
        )
    result.sort(key=lambda x: x["median"], reverse=True)
    return result


# ------------------------------------------------------------------ alerts / admin

def list_alerts(session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(WeatherAlert).order_by(WeatherAlert.published_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": a.id,
            "region_adcode": a.region_adcode,
            "alert_type": a.alert_type,
            "alert_level": a.alert_level,
            "title": a.title,
            "published_at": a.published_at,
            "source": a.source,
        }
        for a in rows
    ]


def list_collect_logs(session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = session.scalars(select(CollectLog).order_by(CollectLog.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "source": r.source,
            "mode": r.mode,
            "status": r.status,
            "points_total": r.points_total,
            "rows_upserted": r.rows_upserted,
            "gap_filled_hours": r.gap_filled_hours,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "error_msg": r.error_msg,
        }
        for r in rows
    ]


def data_quality(session: Session) -> dict[str, Any]:
    hourly_rows = session.scalar(select(func.count()).select_from(PrecipHourly)) or 0
    hourly_null = (
        session.scalar(
            select(func.count()).select_from(PrecipHourly).where(PrecipHourly.precip_mm.is_(None))
        )
        or 0
    )
    observed_rows = (
        session.scalar(
            select(func.count()).select_from(PrecipHourly).where(PrecipHourly.is_forecast == 0)
        )
        or 0
    )
    forecast_rows = hourly_rows - observed_rows

    observed_start, observed_end = session.execute(
        select(func.min(PrecipHourly.obs_time), func.max(PrecipHourly.obs_time)).where(
            PrecipHourly.is_forecast == 0
        )
    ).one()
    distinct_hours = (
        session.scalar(
            select(func.count(func.distinct(PrecipHourly.obs_time))).where(
                PrecipHourly.is_forecast == 0
            )
        )
        or 0
    )

    expected_hours = 0
    if observed_start and observed_end:
        delta = datetime.strptime(observed_end, TIME_FMT) - datetime.strptime(observed_start, TIME_FMT)
        expected_hours = int(delta.total_seconds() // 3600) + 1

    coverage = round(100 * distinct_hours / expected_hours, 2) if expected_hours else 0.0

    daily_rows = session.scalar(select(func.count()).select_from(PrecipDaily)) or 0
    daily_without_detail = (
        session.scalar(
            select(func.count()).select_from(PrecipDaily).where(PrecipDaily.rain_hours.is_(None))
        )
        or 0
    )

    collect_total = session.scalar(select(func.count()).select_from(CollectLog)) or 0
    collect_failed = (
        session.scalar(
            select(func.count()).select_from(CollectLog).where(CollectLog.status == "failed")
        )
        or 0
    )
    last_log = session.scalars(select(CollectLog).order_by(CollectLog.id.desc()).limit(1)).first()

    return {
        "hourly_rows": hourly_rows,
        "hourly_null": hourly_null,
        "hourly_null_pct": round(100 * hourly_null / hourly_rows, 2) if hourly_rows else 0.0,
        "hourly_observed_rows": observed_rows,
        "hourly_forecast_rows": forecast_rows,
        "observed_start": observed_start,
        "observed_end": observed_end,
        "distinct_hours": distinct_hours,
        "expected_hours": expected_hours,
        "missing_hours": max(expected_hours - distinct_hours, 0),
        "coverage_pct": coverage,
        "daily_rows": daily_rows,
        "daily_with_detail": daily_rows - daily_without_detail,
        "daily_without_detail": daily_without_detail,
        "collect_total": collect_total,
        "collect_success": collect_total - collect_failed,
        "collect_failed": collect_failed,
        "last_collect_at": last_log.started_at if last_log else None,
    }


# ------------------------------------------------------------------ 导出

def iter_csv(
    session: Session,
    *,
    kind: str = "daily",
    adcode: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> Iterator[str]:
    """以 CSV 文本流形式导出数据（供 StreamingResponse 使用）。"""
    buffer: list[str] = []

    def flush() -> str:
        chunk = "".join(buffer)
        buffer.clear()
        return chunk

    regions = region_map(session)

    if kind == "hourly":
        buffer.append("adcode,name,province,obs_time,precip_mm,is_forecast\n")
        stmt = (
            select(
                GridPoint.region_adcode,
                GridPoint.label,
                Region.province,
                PrecipHourly.obs_time,
                PrecipHourly.precip_mm,
                PrecipHourly.is_forecast,
            )
            .join(GridPoint, GridPoint.id == PrecipHourly.point_id)
            .join(Region, Region.adcode == GridPoint.region_adcode)
            .order_by(PrecipHourly.obs_time, GridPoint.region_adcode)
        )
        point_id = _point_id(session, adcode)
        if point_id:
            stmt = stmt.where(PrecipHourly.point_id == point_id)
        if start:
            stmt = stmt.where(PrecipHourly.obs_time >= start)
        if end:
            stmt = stmt.where(PrecipHourly.obs_time <= end)

        for row in session.execute(stmt).yield_per(2000):
            buffer.append(
                f"{row[0]},{row[1]},{row[2]},{row[3]},"
                f"{'' if row[4] is None else row[4]},{row[5]}\n"
            )
            if len(buffer) >= 500:
                yield flush()
    else:
        buffer.append("adcode,name,province,obs_date,precip_sum,precip_max_hourly,rain_hours,rain_level\n")
        stmt = (
            select(
                GridPoint.region_adcode,
                GridPoint.label,
                Region.province,
                PrecipDaily.obs_date,
                PrecipDaily.precip_sum,
                PrecipDaily.precip_max_hourly,
                PrecipDaily.rain_hours,
                PrecipDaily.rain_level,
            )
            .join(GridPoint, GridPoint.id == PrecipDaily.point_id)
            .join(Region, Region.adcode == GridPoint.region_adcode)
            .order_by(PrecipDaily.obs_date, GridPoint.region_adcode)
        )
        point_id = _point_id(session, adcode)
        if point_id:
            stmt = stmt.where(PrecipDaily.point_id == point_id)
        if start:
            stmt = stmt.where(PrecipDaily.obs_date >= start)
        if end:
            stmt = stmt.where(PrecipDaily.obs_date <= end)

        for row in session.execute(stmt).yield_per(2000):
            rh = "" if row[6] is None else row[6]
            mh = "" if row[5] is None else row[5]
            buffer.append(
                f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{mh},{rh},{row[7] or ''}\n"
            )
            if len(buffer) >= 500:
                yield flush()

    if buffer:
        yield flush()
