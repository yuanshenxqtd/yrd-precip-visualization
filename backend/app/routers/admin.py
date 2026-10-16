"""数据管理：采集日志、手动采集、数据质量、CSV 导出。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud
from ..cache import map_cache, summary_cache, trend_cache
from ..db import get_session, session_scope
from ..schemas import CollectLogOut, CollectResult, QualityOut

router = APIRouter(tags=["数据管理"])


def _clear_caches() -> None:
    summary_cache.clear()
    map_cache.clear()
    trend_cache.clear()


@router.get("/admin/collect-logs", response_model=list[CollectLogOut], summary="采集日志")
def read_logs(
    limit: int = Query(50, ge=1, le=500, description="返回条数"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """采集审计记录（含失败记录）。前端「数据管理」模块的时间线使用。"""
    return crud.list_collect_logs(session, limit=limit)


@router.get("/admin/quality", response_model=QualityOut, summary="数据质量报告")
def read_quality(session: Session = Depends(get_session)) -> dict:
    """缺测率、时间覆盖率、采集成功率等指标。

    这些数字是论文「数据真实性与可用性」一节的直接证据。
    """
    return summary_cache.get_or_set("quality", lambda: crud.data_quality(session))


@router.post("/admin/collect-now", response_model=CollectResult, summary="手动触发一次采集")
def collect_now(
    past_days: int = Query(3, ge=0, le=92, description="自愈补采窗口（天），API 上限 92"),
) -> dict:
    """立即向 Open-Meteo 拉取一次数据并写库（约 3–5 秒）。

    采集是幂等的：重复调用不会产生重复数据，只会更新。
    """
    # 延迟导入，避免 Web 进程启动时加载采集器依赖
    from collector.pipeline import collect

    try:
        summary = collect(mode="manual", past_days=past_days, forecast_days=7, verbose=False)
    except Exception as exc:  # noqa: BLE001
        first_line = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else ""
        return {
            "status": "failed",
            "points": 0,
            "rows_written": 0,
            "rows_inserted": 0,
            "elapsed_seconds": 0.0,
            "message": f"{type(exc).__name__}: {first_line}",
        }

    _clear_caches()
    return {
        "status": "success",
        "points": summary["points"],
        "rows_written": summary["rows_written"],
        "rows_inserted": summary["rows_inserted"],
        "elapsed_seconds": summary["elapsed_seconds"],
        "message": (
            f"覆盖 {summary['observed_rows']:,} 条实况 + {summary['forecast_rows']:,} 条预报；"
            f"库内累计 {summary['total_hourly']:,} 条小时记录"
        ),
    }


@router.get("/export/csv", summary="导出 CSV")
def export_csv(
    kind: str = Query("daily", pattern="^(daily|hourly)$", description="daily 或 hourly"),
    adcode: str | None = Query(None, description="行政区划代码；留空导出全部"),
    start: str | None = Query(None, description="起始时间（含）"),
    end: str | None = Query(None, description="结束时间（含）"),
) -> StreamingResponse:
    """以流式方式导出数据，避免大结果集占用内存。"""
    filename = f"yrd_precip_{kind}_{start or 'all'}_{end or 'all'}.csv"

    def generate():
        # 会话在生成器内部创建，确保流式响应期间连接有效
        with session_scope() as session:
            yield from crud.iter_csv(session, kind=kind, adcode=adcode, start=start, end=end)

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
