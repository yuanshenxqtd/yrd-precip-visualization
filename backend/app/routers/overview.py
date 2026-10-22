"""总览大屏：指标卡与排行榜。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud
from ..cache import summary_cache
from ..db import get_session
from ..schemas import OverviewHighlights, RankingItem, SummaryOut

router = APIRouter(tags=["总览"])


@router.get("/overview/summary", response_model=SummaryOut, summary="总览指标卡")
def read_summary(session: Session = Depends(get_session)) -> dict:
    """最新实况时刻、降水覆盖率、近 24 小时累计与极值、今日最湿点位等。

    结果缓存 60 秒，供大屏自动刷新使用。
    """
    return summary_cache.get_or_set("overview_summary", lambda: crud.overview_summary(session))


@router.get(
    "/overview/highlights",
    response_model=OverviewHighlights,
    summary="自动摘要素材（读图要点）",
)
def read_highlights(
    hours: int = Query(24, ge=6, le=168, description="当前态势窗口（小时）"),
    window_days: int = Query(30, ge=7, le=365, description="历史定位窗口（天）"),
    session: Session = Depends(get_session),
) -> dict:
    """返回**结构化事实**而非成品句子，供前端组织成「读图要点」。

    包含：窗口内累计/有雨点位数/最强单小时/最湿点位、与前一窗口的对比、
    近 N 天最强的一天及其最强点位、有降水天数。

    把「从图里读结论」这件事从用户脑中搬到界面上 ——
    这是数据可视化流水线最后一环「知识、灵感」的落点。
    """
    key = f"overview_highlights:{hours}:{window_days}"
    return summary_cache.get_or_set(
        key, lambda: crud.overview_highlights(session, hours=hours, window_days=window_days)
    )


@router.get("/overview/ranking", response_model=list[RankingItem], summary="城市降水排行")
def read_ranking(
    limit: int = Query(10, ge=1, le=56, description="返回条数"),
    hours: int = Query(24, ge=1, le=720, description="统计窗口（小时）"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """按近 N 小时累计降水量降序排列的点位榜单。"""
    key = f"overview_ranking:{limit}:{hours}"
    return summary_cache.get_or_set(key, lambda: crud.overview_ranking(session, limit=limit, hours=hours))
