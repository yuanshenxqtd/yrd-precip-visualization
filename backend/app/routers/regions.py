"""行政区划与地图边界。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud
from ..cache import map_cache, trend_cache
from ..config import GEOJSON_DIR, MERGED_GEOJSON_NAME
from ..db import get_session
from ..schemas import RegionDetail, RegionOut

router = APIRouter(tags=["行政区划"])


@router.get("/regions", response_model=list[RegionOut], summary="行政区划列表（含中心坐标）")
def read_regions(session: Session = Depends(get_session)) -> list[dict]:
    """返回 60 条行政区划（4 省级 + 40 市级 + 16 区级），含中心经纬度。

    前端用于构建省→市/区的选择器与下钻逻辑。
    """
    return trend_cache.get_or_set("regions", lambda: crud.list_regions(session))


@router.get(
    "/regions/{adcode}/detail",
    response_model=RegionDetail,
    summary="单点位详情（下钻抽屉）",
)
def read_region_detail(
    adcode: str = Path(description="行政区划代码，如 330200（宁波市）"),
    hours: int = Query(48, ge=6, le=168, description="逐小时窗口长度（小时）"),
    days: int = Query(30, ge=7, le=365, description="逐日窗口长度（天）"),
    session: Session = Depends(get_session),
) -> dict:
    """**按需细节（Details-on-demand）**：一次取全某个点位的档案。

    包含：基本信息、近 N 小时逐小时、近 N 天逐日、历史等级分布、
    历史极值榜、以及一组汇总指标。

    设计目的：让界面上看到的任何一个数字都可追溯 ——
    点开点位即可核对它是由哪些小时值汇总而来的。

    省级区划（如 330000）没有采集点，会返回 404。
    """
    detail = crud.region_detail(session, adcode, hours=hours, days=days)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"未找到行政区划 {adcode}，或该区划不是采集点（省级区划无采集点）",
        )
    return detail


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
