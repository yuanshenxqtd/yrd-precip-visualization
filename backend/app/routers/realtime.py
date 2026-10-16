"""实时监测：最新观测与逐小时序列。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud
from ..cache import map_cache
from ..db import get_session

router = APIRouter(tags=["实时监测"])


@router.get("/realtime/latest", summary="最新时刻各点位降水与当日累计")
def read_latest(session: Session = Depends(get_session)) -> dict:
    """返回库内最新实况整点的 56 个点位取值，以及各点位当日累计。

    无降水时各点位值为 0 —— 这是正常天气状态，前端应显示空态提示而非留白。
    """
    return map_cache.get_or_set("realtime_latest", lambda: crud.realtime_latest(session))


@router.get("/realtime/timeseries", summary="近 N 小时降水序列")
def read_timeseries(
    adcode: str | None = Query(None, description="行政区划代码；留空表示全区合计"),
    hours: int = Query(48, ge=1, le=720, description="回溯小时数"),
    session: Session = Depends(get_session),
) -> dict:
    """逐小时降水序列，供实时监测模块的柱线图使用。"""
    key = f"realtime_ts:{adcode}:{hours}"
    return map_cache.get_or_set(key, lambda: crud.realtime_timeseries(session, adcode=adcode, hours=hours))
