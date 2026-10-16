"""系统状态与数据源元信息。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..cache import summary_cache
from ..db import get_session
from ..schemas import MetaOut

router = APIRouter(tags=["系统"])


@router.get("/meta", response_model=MetaOut, summary="系统与数据源状态")
def read_meta(session: Session = Depends(get_session)) -> dict:
    """返回库内数据规模、时间跨度、最近一次采集状态。

    前端「数据管理」模块与总览页的页脚状态栏使用该接口。
    """
    return summary_cache.get_or_set("meta", lambda: crud.get_meta(session))
