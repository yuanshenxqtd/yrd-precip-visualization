"""时间分析：日/月序列、距平、降水等级分布。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud
from ..cache import trend_cache
from ..db import get_session
from ..schemas import AnomalyPoint, ExtremeEvent, LevelCount

router = APIRouter(tags=["时间分析"])


def _today() -> str:
    return date.today().isoformat()


@router.get("/trend/daily", summary="日降水序列")
def read_daily(
    adcode: str | None = Query(None, description="行政区划代码；留空表示全区平均"),
    start: str | None = Query(None, description="起始日期 YYYY-MM-DD，默认近 90 天"),
    end: str | None = Query(None, description="结束日期 YYYY-MM-DD，默认今天"),
    session: Session = Depends(get_session),
) -> dict:
    """日累计降水序列，含每日最大单点值。"""
    end = end or _today()
    start = start or crud.shift_days(end, -89)
    key = f"trend_daily:{adcode}:{start}:{end}"
    return trend_cache.get_or_set(key, lambda: crud.trend_daily(session, adcode=adcode, start=start, end=end))


@router.get("/trend/monthly", summary="月累计序列")
def read_monthly(
    adcode: str | None = Query(None, description="行政区划代码；留空表示全区"),
    year: int = Query(..., ge=2023, le=2100, description="年份（库内数据自 2023 年起）"),
    session: Session = Depends(get_session),
) -> dict:
    """某年的逐月累计降水。"""
    key = f"trend_monthly:{adcode}:{year}"
    return trend_cache.get_or_set(key, lambda: crud.trend_monthly(session, adcode=adcode, year=year))


@router.get("/trend/anomaly", response_model=list[AnomalyPoint], summary="降水距平")
def read_anomaly(
    adcode: str | None = Query(None, description="行政区划代码；留空表示全区"),
    year: int | None = Query(None, description="目标年份，默认今年"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """当月实际降水 vs 同期基准值的距平百分比。

    **基准只采用完整年份（2024、2025）**：库内 2023 年仅含 9–12 月、
    2026 年截至当前月，均为不完整年份，混入基准会造成严重偏差。
    """
    key = f"trend_anomaly:{adcode}:{year}"
    return trend_cache.get_or_set(key, lambda: crud.trend_anomaly(session, adcode=adcode, year=year))


@router.get("/trend/level-distribution", response_model=list[LevelCount], summary="降水等级分布")
def read_level_distribution(
    adcode: str | None = Query(None, description="行政区划代码；留空表示全部点位"),
    start: str | None = Query(None, description="起始日期，默认不限制"),
    end: str | None = Query(None, description="结束日期，默认不限制"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """按 GB/T 28592-2012 统计各降水等级出现的天数。"""
    key = f"level_dist:{adcode}:{start}:{end}"
    return trend_cache.get_or_set(
        key, lambda: crud.trend_level_distribution(session, start=start, end=end, adcode=adcode)
    )


@router.get("/trend/extremes", response_model=list[ExtremeEvent], summary="极端降水事件榜")
def read_extremes(
    adcode: str | None = Query(None, description="行政区划代码；留空表示全部点位"),
    start: str | None = Query(None, description="起始日期，默认不限制"),
    end: str | None = Query(None, description="结束日期，默认不限制"),
    min_mm: float | None = Query(None, ge=0, description="最小日累计（mm）；传 50 即只看暴雨及以上"),
    limit: int = Query(20, ge=1, le=200, description="返回条数"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """按日累计降水降序返回单日单点的极端事件。

    用于「预警统计」模块的极值榜与历史过程复盘；
    配合 `min_mm` 可按国标阈值筛选（50 = 暴雨、100 = 大暴雨、250 = 特大暴雨）。
    """
    key = f"extremes:{adcode}:{start}:{end}:{min_mm}:{limit}"
    return trend_cache.get_or_set(
        key,
        lambda: crud.trend_extremes(
            session, start=start, end=end, adcode=adcode, min_mm=min_mm, limit=limit
        ),
    )
