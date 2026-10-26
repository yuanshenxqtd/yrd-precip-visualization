"""采集主流程：自愈补采 + 幂等写入 + 采集审计。

核心设计（对应 docs/PLAN.md 第 7 节）：

    **自愈补采** —— 每轮固定回拉 past_days 天的全部小时并 UPSERT 写入。
    因此程序崩溃 / 电脑关机 / 断网造成的数据缺口，下一轮运行会自动补齐，
    不需要额外的补偿逻辑，也不依赖采集器持续在线。

    **幂等写入** —— 依赖 precip_hourly 上的唯一约束 (point_id, obs_time, source)，
    同一批数据重复写入只会更新、不会重复插入。

    **采集审计** —— 每次运行都写 collect_log，成功与失败都留痕，
    为前端「数据管理」模块与论文的数据质量分析提供依据。

用法：
    .venv\\Scripts\\python -m collector.pipeline
    .venv\\Scripts\\python -m collector.pipeline --past-days 92
    .venv\\Scripts\\python -m collector.pipeline --mode manual --quiet
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import case, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.app.config import (
    FORECAST_DAYS,
    OPENMETEO_SOURCE_NAME,
    PAST_DAYS,
)
from backend.app.db import session_scope
from backend.app.levels import classify
from backend.app.models import CollectLog, GridPoint, PrecipDaily, PrecipHourly

from . import openmeteo
from .alerts import derive_and_store

# SQLite 单条语句的绑定参数有上限，分批 UPSERT
UPSERT_CHUNK = 500
CN_TZ = timezone(timedelta(hours=8))
LINE = "=" * 60


# ------------------------------------------------------------------ 工具

def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _current_hour_str() -> str:
    """当前整点（Asia/Shanghai），用于区分实况与预报。"""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:00")


def _make_logger(verbose: bool) -> Callable[[str], None]:
    def _log(message: str) -> None:
        if verbose:
            print(message, flush=True)

    return _log


# ------------------------------------------------------------------ 采集日志

def start_log(mode: str, points_total: int) -> int:
    with session_scope() as session:
        row = CollectLog(
            source=OPENMETEO_SOURCE_NAME,
            mode=mode,
            started_at=_now_str(),
            status="running",
            points_total=points_total,
        )
        session.add(row)
        session.flush()
        return int(row.id)


def finish_log(
    log_id: int,
    *,
    status: str,
    rows_upserted: int = 0,
    gap_filled_hours: int = 0,
    error_msg: str | None = None,
) -> None:
    with session_scope() as session:
        row = session.get(CollectLog, log_id)
        if row is None:
            return
        row.finished_at = _now_str()
        row.status = status
        row.rows_upserted = rows_upserted
        row.gap_filled_hours = gap_filled_hours
        row.error_msg = (error_msg or "")[:2000] or None


# ------------------------------------------------------------------ 点位

def load_points() -> list[dict[str, Any]]:
    """读取全部启用的采集点。"""
    with session_scope() as session:
        stmt = (
            select(
                GridPoint.id,
                GridPoint.lon,
                GridPoint.lat,
                GridPoint.label,
                GridPoint.region_adcode,
            )
            .where(GridPoint.is_active == 1)
            .order_by(GridPoint.id)
        )
        return [
            {"id": r.id, "lon": r.lon, "lat": r.lat, "label": r.label, "adcode": r.region_adcode}
            for r in session.execute(stmt).all()
        ]


# ------------------------------------------------------------------ 写入

def upsert_hourly(session, rows: list[dict[str, Any]]) -> int:
    """批量 UPSERT 逐小时降水，返回写入行数。"""
    if not rows:
        return 0
    written = 0
    for start in range(0, len(rows), UPSERT_CHUNK):
        chunk = rows[start : start + UPSERT_CHUNK]
        stmt = sqlite_insert(PrecipHourly).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["point_id", "obs_time", "source"],
            set_={
                "precip_mm": stmt.excluded.precip_mm,
                "is_forecast": stmt.excluded.is_forecast,
            },
        )
        session.execute(stmt)
        written += len(chunk)
    return written


def recompute_daily(session, since_date: str) -> int:
    """按小时数据重算日汇总（仅实况，不含预报），返回重算的 (点位×日期) 组合数。"""
    day = func.substr(PrecipHourly.obs_time, 1, 10)
    stmt = (
        select(
            PrecipHourly.point_id.label("point_id"),
            day.label("obs_date"),
            PrecipHourly.source.label("source"),
            func.coalesce(func.sum(PrecipHourly.precip_mm), 0.0).label("precip_sum"),
            func.max(PrecipHourly.precip_mm).label("precip_max_hourly"),
            func.coalesce(
                func.sum(case((PrecipHourly.precip_mm > 0, 1), else_=0)), 0
            ).label("rain_hours"),
        )
        .where(
            PrecipHourly.is_forecast == 0,
            PrecipHourly.obs_time >= f"{since_date}T00:00",
        )
        .group_by(PrecipHourly.point_id, day, PrecipHourly.source)
    )

    payload: list[dict[str, Any]] = []
    for row in session.execute(stmt).all():
        total = round(float(row.precip_sum or 0.0), 2)
        payload.append(
            {
                "point_id": row.point_id,
                "obs_date": row.obs_date,
                "precip_sum": total,
                "precip_max_hourly": (
                    round(float(row.precip_max_hourly), 2)
                    if row.precip_max_hourly is not None
                    else None
                ),
                "rain_hours": int(row.rain_hours or 0),
                "rain_level": classify(total, hours=24),
                "source": row.source,
            }
        )

    for start in range(0, len(payload), UPSERT_CHUNK):
        chunk = payload[start : start + UPSERT_CHUNK]
        ins = sqlite_insert(PrecipDaily).values(chunk)
        ins = ins.on_conflict_do_update(
            index_elements=["point_id", "obs_date", "source"],
            set_={
                "precip_sum": ins.excluded.precip_sum,
                "precip_max_hourly": ins.excluded.precip_max_hourly,
                "rain_hours": ins.excluded.rain_hours,
                "rain_level": ins.excluded.rain_level,
            },
        )
        session.execute(ins)
    return len(payload)


# ------------------------------------------------------------------ 主流程

def collect(
    mode: str = "realtime",
    *,
    past_days: int = PAST_DAYS,
    forecast_days: int = FORECAST_DAYS,
    verbose: bool = True,
) -> dict[str, Any]:
    """执行一次采集。返回汇总信息。"""
    log = _make_logger(verbose)
    t0 = time.perf_counter()

    points = load_points()
    if not points:
        raise RuntimeError("没有可用的采集点，请先运行：python -m collector.init_db")

    log(LINE)
    log(f"  长三角降水采集 · 模式={mode}")
    log(LINE)
    log(f"  点位数={len(points)}  past_days={past_days}  forecast_days={forecast_days}")

    log_id = start_log(mode=mode, points_total=len(points))

    try:
        # -------------------------------------------------- 拉取
        fetched = openmeteo.fetch_hourly_precipitation(
            points, past_days=past_days, forecast_days=forecast_days
        )
        log(f"  Open-Meteo 单次批量请求返回 {len(fetched)} 个点位")

        now_hour = _current_hour_str()

        # -------------------------------------------------- 整理并入库
        rows: list[dict[str, Any]] = []
        observed_times: list[str] = []
        nonzero = 0.0
        nonzero_count = 0
        wettest_label, wettest_sum = None, -1.0
        per_point_sum: dict[int, float] = {}

        for item in fetched:
            point_id = int(item["point"]["id"])
            label = item["point"]["label"]
            for obs_time, value in zip(item["times"], item["values"]):
                is_forecast = 0 if obs_time <= now_hour else 1
                precip = float(value) if value is not None else None
                rows.append(
                    {
                        "point_id": point_id,
                        "obs_time": obs_time,
                        "precip_mm": precip,
                        "source": OPENMETEO_SOURCE_NAME,
                        "is_forecast": is_forecast,
                    }
                )
                if is_forecast == 0:
                    observed_times.append(obs_time)
                    if precip:
                        nonzero += precip
                        nonzero_count += 1
                        per_point_sum[point_id] = per_point_sum.get(point_id, 0.0) + precip
                        if per_point_sum[point_id] > wettest_sum:
                            wettest_sum = per_point_sum[point_id]
                            wettest_label = label

        with session_scope() as session:
            before = session.scalar(select(func.count()).select_from(PrecipHourly)) or 0
            written = upsert_hourly(session, rows)
            after = session.scalar(select(func.count()).select_from(PrecipHourly)) or 0
            inserted = after - before

            since_date = min(observed_times)[:10] if observed_times else _now_str()[:10]
            daily_rows = recompute_daily(session, since_date)

            # 顺带做一次「达标判定」并落库（source='derived'）。
            # 失败不能影响采集本身，所以单独兜住异常。
            try:
                alerts_triggered = derive_and_store(session)
            except Exception:
                alerts_triggered = 0

            total_hourly = after
            total_daily = session.scalar(select(func.count()).select_from(PrecipDaily)) or 0

        elapsed = time.perf_counter() - t0
        observed_count = len(observed_times)
        forecast_count = len(rows) - observed_count

        finish_log(
            log_id,
            status="success",
            rows_upserted=written,
            gap_filled_hours=inserted,
        )

        summary: dict[str, Any] = {
            "status": "success",
            "mode": mode,
            "points": len(points),
            "hours_per_point": len(fetched[0]["times"]) if fetched else 0,
            "rows_written": written,
            "rows_inserted": inserted,
            "rows_updated": written - inserted,
            "observed_rows": observed_count,
            "forecast_rows": forecast_count,
            "daily_rows": daily_rows,
            "total_hourly": total_hourly,
            "total_daily": total_daily,
            "nonzero_hours": nonzero_count,
            "alerts_triggered": alerts_triggered,
            "total_precip_mm": round(nonzero, 2),
            "wettest_point": wettest_label,
            "wettest_mm": round(wettest_sum, 2) if wettest_label else 0.0,
            "elapsed_seconds": round(elapsed, 2),
            "log_id": log_id,
        }

        log("")
        log(f"  写入 {written} 行（新增 {inserted}，更新 {written - inserted}）")
        log(f"  实况 {observed_count} 行 / 预报 {forecast_count} 行")
        log(f"  日汇总重算 {daily_rows} 组（点位×日期）")
        log(f"  库内累计：小时 {total_hourly} 行，日 {total_daily} 行")
        log("")
        if nonzero_count:
            log(f"  有降水的小时数：{nonzero_count}，累计 {round(nonzero, 2)} mm")
            log(f"  最湿点位：{wettest_label}（{round(wettest_sum, 2)} mm）")
        else:
            log("  当前长三角全区无降水（这是正常天气状态，非故障）")
        log(f"  耗时 {elapsed:.1f} 秒")
        log(LINE)
        return summary

    except Exception as exc:  # noqa: BLE001 - 任何异常都要落审计
        finish_log(log_id, status="failed", error_msg=f"{type(exc).__name__}: {exc}")
        # 异常信息可能包含整条 SQL，截断以免刷屏
        log(f"  [失败] {type(exc).__name__}: {str(exc).strip().splitlines()[0][:200]}")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="长三角降水数据采集")
    parser.add_argument(
        "--mode",
        default="manual",
        choices=["realtime", "manual", "backfill"],
        help="采集模式标记，仅用于审计记录（默认 manual）",
    )
    parser.add_argument("--past-days", type=int, default=PAST_DAYS, help=f"回拉天数（默认 {PAST_DAYS}，API 上限 92）")
    parser.add_argument("--forecast-days", type=int, default=FORECAST_DAYS, help=f"预报天数（默认 {FORECAST_DAYS}）")
    parser.add_argument("--quiet", action="store_true", help="静默模式，仅输出错误")
    args = parser.parse_args(argv)

    if not 0 <= args.past_days <= 92:
        print("错误：--past-days 必须在 0~92 之间（实测 API 上限为 92，超过返回 HTTP 400）")
        return 2

    try:
        summary = collect(
            mode=args.mode,
            past_days=args.past_days,
            forecast_days=args.forecast_days,
            verbose=not args.quiet,
        )
    except Exception as exc:  # noqa: BLE001
        first_line = str(exc).strip().splitlines()[0][:300] if str(exc).strip() else ""
        print(f"采集失败：{type(exc).__name__}: {first_line}", file=sys.stderr)
        return 1

    if args.quiet:
        print(
            f"OK points={summary['points']} written={summary['rows_written']} "
            f"inserted={summary['rows_inserted']} total={summary['total_hourly']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
