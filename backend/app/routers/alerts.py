"""气象预警（预留模块）。

当前数据源未包含预警信息，表结构已就绪，后续接入和风天气等预警接口即可生效。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import alerting, crud
from ..db import get_session
from ..schemas import ActiveAlerts

router = APIRouter(tags=["预警"])


@router.get("/alerts", summary="预警列表")
def read_alerts(
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """返回预警记录。

    **当前库内为空**：Open-Meteo 不提供中国气象预警数据。
    如需该模块生效，可接入和风天气的预警接口（见 docs/PLAN.md 第 12 节）。
    """
    return crud.list_alerts(session, limit=limit)


@router.get(
    "/alerts/active",
    response_model=ActiveAlerts,
    summary="当前达到暴雨预警标准的点位（本地达标判定）",
)
def read_active_alerts(session: Session = Depends(get_session)) -> dict:
    """按国标暴雨预警阈值判定**当前**哪些点位达标。

    与 `/alerts` 的区别：
    · `/alerts`        —— 表里存的预警记录（目前为空，等官方源接入）
    · `/alerts/active` —— 用实况降水**实时算**出来的达标判定，不依赖外部数据源

    口径是**回看**而非预报：官方预警说"未来 12 小时将达"，这里判定"过去 12 小时已累计"。
    两者性质不同，界面必须标注清楚，不能当成官方预警展示。
    """
    return alerting.compute_active(session)