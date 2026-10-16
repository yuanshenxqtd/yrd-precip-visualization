"""FastAPI 应用入口。

启动方式：
    .venv\\Scripts\\python -m uvicorn backend.app.main:app --reload --port 8000
    或双击 scripts\\run_backend.bat

接口文档：http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import API_HOST, API_PORT, COLLECT_INTERVAL_MINUTES, CORS_ORIGINS
from .db import init_db
from .levels import LEVEL_COLORS
from .routers import (
    admin,
    alerts,
    compare,
    meta,
    overview,
    realtime,
    regions,
    spatial,
    trend,
)

API_PREFIX = "/api"

DESCRIPTION = f"""
长三角地区（上海市、江苏省、浙江省、安徽省）**降水实时监测与可视化分析系统**后端接口。

- **采集点**：56 个（上海 16 个区 + 江苏 13 市 + 浙江 11 市 + 安徽 16 市）
- **数据源**：Open-Meteo（ECMWF ERA5 / ERA5-Land 再分析资料，CC BY 4.0）
- **采集频率**：每 {COLLECT_INTERVAL_MINUTES} 分钟一次，可随时手动触发
- **幂等写入**：重复采集不会产生重复数据
- **分级标准**：GB/T 28592-2012《降水量等级》

**降水等级配色**：{'、'.join(f'{k}={v}' for k, v in LEVEL_COLORS.items())}

> 数据许可：Open-Meteo 数据采用 CC BY 4.0，非商业用途免费，使用时须署名。
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时确保数据表存在（幂等，不会动已有数据）。"""
    init_db()
    yield


app = FastAPI(
    title="长三角地区降水实时监测与可视化分析系统",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 9 个模块化路由
for _module in (meta, regions, overview, realtime, spatial, trend, compare, alerts, admin):
    app.include_router(_module.router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    """根路径跳转到交互式接口文档。"""
    return RedirectResponse(url="/docs")


@app.get(f"{API_PREFIX}/health", tags=["系统"], summary="健康检查")
def health() -> dict:
    """探活接口，用于确认后端是否已就绪。"""
    return {"status": "ok", "service": "yrd-precip-api", "version": app.version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host=API_HOST, port=API_PORT, reload=True)
