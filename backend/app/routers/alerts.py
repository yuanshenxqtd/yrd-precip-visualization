"""气象预警（预留模块）。

当前数据源未包含预警信息，表结构已就绪，后续接入和风天气等预警接口即可生效。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud
from ..db import get_session

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
