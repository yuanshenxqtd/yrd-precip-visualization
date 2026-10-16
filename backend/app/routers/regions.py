"""行政区划与地图边界。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud
from ..cache import trend_cache
from ..config import GEOJSON_DIR, MERGED_GEOJSON_NAME
from ..db import get_session
from ..schemas import RegionOut

router = APIRouter(tags=["行政区划"])


@router.get("/regions", response_model=list[RegionOut], summary="行政区划列表（含中心坐标）")
def read_regions(session: Session = Depends(get_session)) -> list[dict]:
    """返回 60 条行政区划（4 省级 + 40 市级 + 16 区级），含中心经纬度。

    前端用于构建省→市/区的选择器与下钻逻辑。
    """
    return trend_cache.get_or_set("regions", lambda: crud.list_regions(session))


@router.get("/regions/geojson", summary="长三角合并地图 GeoJSON（56 个要素）")
def read_geojson() -> JSONResponse:
    """返回沪苏浙皖合并后的 FeatureCollection，可直接注册为 ECharts 地图。

    由 `collector.init_db` 生成并缓存于 `data/geojson/yrd_merged.json`。
    """
    path = GEOJSON_DIR / MERGED_GEOJSON_NAME
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="地图数据未生成，请先运行：python -m collector.init_db",
        )
    return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))
