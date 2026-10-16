"""城市对比：排行、多城序列、箱线统计。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud
from ..cache import trend_cache
from ..db import get_session
from ..schemas import BoxplotItem, RankingItem

router = APIRouter(tags=["城市对比"])


def _range(start: str | None, end: str | None) -> tuple[str, str]:
    end = end or date.today().isoformat()
    start = start or crud.shift_days(end, -29)
    if start > end:
        raise HTTPException(status_code=400, detail="start 不能晚于 end")
    return start, end


@router.get("/compare/ranking", response_model=list[RankingItem], summary="区间降水排行")
def read_ranking(
    start: str | None = Query(None, description="起始日期，默认近 30 天"),
    end: str | None = Query(None, description="结束日期，默认今天"),
    limit: int = Query(20, ge=1, le=56, description="返回条数"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """按区间累计降水量排序的点位榜单。"""
    start, end = _range(start, end)
    key = f"cmp_rank:{start}:{end}:{limit}"
    return trend_cache.get_or_set(key, lambda: crud.compare_ranking(session, start=start, end=end, limit=limit))


@router.get("/compare/multi", summary="多城市日降水序列对比")
def read_multi(
    adcodes: str = Query(..., description="逗号分隔的行政区划代码，如 310101,320500,330100"),
    start: str | None = Query(None, description="起始日期，默认近 30 天"),
    end: str | None = Query(None, description="结束日期，默认今天"),
    session: Session = Depends(get_session),
) -> dict:
    """同时返回多个城市的日降水序列，供折线对比图使用。"""
    codes = [c.strip() for c in adcodes.split(",") if c.strip()]
    if not codes:
        raise HTTPException(status_code=400, detail="adcodes 不能为空")
    if len(codes) > 12:
        raise HTTPException(status_code=400, detail="最多同时对比 12 个城市")
    start, end = _range(start, end)
    key = f"cmp_multi:{','.join(codes)}:{start}:{end}"
    return trend_cache.get_or_set(key, lambda: crud.compare_multi(session, adcodes=codes, start=start, end=end))


@router.get("/compare/boxplot", response_model=list[BoxplotItem], summary="城市日降水分布箱线统计")
def read_boxplot(
    start: str | None = Query(None, description="起始日期，默认近 30 天"),
    end: str | None = Query(None, description="结束日期，默认今天"),
    limit: int = Query(10, ge=2, le=56, description="取累计最多的前 N 个点位"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """返回五数概括（min/q1/median/q3/max）与均值，供箱线图使用。"""
    start, end = _range(start, end)
    key = f"cmp_box:{start}:{end}:{limit}"
    return trend_cache.get_or_set(key, lambda: crud.compare_boxplot(session, start=start, end=end, limit=limit))
