"""空间分布：指定时刻降水场与时间轴回放。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud
from ..cache import map_cache
from ..db import get_session
from ..schemas import FieldGrid, MapFrame

router = APIRouter(tags=["空间分布"])


@router.get(
    "/spatial/field",
    response_model=FieldGrid,
    summary="IDW 空间插值生成的连续降水场",
)
def read_field(
    time: str | None = Query(None, description="时刻，形如 2026-10-07T15:00；留空取最新实况"),
    step: float = Query(0.12, ge=0.05, le=0.5, description="网格步长（度）"),
    power: float = Query(2.0, ge=1.0, le=4.0, description="反距离权重的幂次"),
    session: Session = Depends(get_session),
) -> dict:
    """把 56 个离散点位插值成规则网格上的**连续降水场**（反距离加权 IDW）。

    与 `/spatial/map` 的区别：
    · map    —— 按行政区划整体着色，业界惯例，适合看"哪个市下了多少"
    · field  —— 连续插值场，适合看"雨带怎么走"、识别区域内的强中心

    插值是**模型**不是观测：网格值由邻近点位加权得出，不代表该处真实雨量。
    网格落在区划之外的单元由前端按边界掩膜剔除。
    """
    key = f"spatial_field:{time or 'latest'}:{step}:{power}"
    return map_cache.get_or_set(
        key, lambda: crud.spatial_field(session, time=time, step=step, power=power)
    )


@router.get("/spatial/map", summary="指定时刻的全区分级设色数据")
def read_map(
    time: str | None = Query(None, description="时刻，形如 2026-10-07T15:00；留空取最新实况"),
    session: Session = Depends(get_session),
) -> dict:
    """返回该时刻 56 个点位的降水值与国标等级、建议配色，供地图分级设色。"""
    key = f"spatial_map:{time or 'latest'}"
    return map_cache.get_or_set(key, lambda: crud.spatial_map(session, time))


@router.get("/spatial/timespan", response_model=list[MapFrame], summary="时间区间的降水场序列（回放用）")
def read_timespan(
    start: str = Query(..., description="起始时刻，形如 2026-08-09T00:00"),
    end: str = Query(..., description="结束时刻，形如 2026-08-10T23:00"),
    max_frames: int = Query(48, ge=2, le=240, description="最大帧数，超出则等间隔抽样"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """一次返回若干帧的降水场，前端拖动时间轴即可播放。

    推荐演示时段：2026-08-10（长三角区域性大暴雨过程）。
    """
    if start > end:
        raise HTTPException(status_code=400, detail="start 不能晚于 end")
    key = f"timespan:{start}:{end}:{max_frames}"
    return map_cache.get_or_set(key, lambda: crud.spatial_timespan(session, start=start, end=end, max_frames=max_frames))
