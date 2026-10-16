"""历史数据回填：3 年日数据 + 1 年小时数据。

策略（对应 docs/PLAN.md 第 7 节）：

    1. **日数据 3 年** —— archive-api 的 `daily=precipitation_sum`，
       写入 precip_daily。日值接口不提供小时明细，因此
       `precip_max_hourly` 与 `rain_hours` 置为 NULL（表示「无小时数据」，
       区别于「确实 0 小时有雨」）。`rain_level` 按 GB/T 28592-2012 判定。
    2. **小时数据 1 年** —— archive-api 的 `hourly=precipitation`，写入 precip_hourly。
    3. **重叠时段重算** —— 用小时数据重算日汇总，把最近一年的
       `precip_max_hourly` / `rain_hours` 补全。

再分析资料有数天延迟，因此回填结束日期留出 `ARCHIVE_LAG_DAYS` 天余量；
最近的这段缺口由 `collector.pipeline --past-days N` 从实时接口补齐（见 scripts\\backfill.bat）。

额度估算（依据 docs/DATA_SOURCE.md）：日数据约 4,400 次调用 + 小时数据约 1,500 次，
合计约 5,900 次，占免费日额度 10,000 的 59%。

用法：
    .venv\\Scripts\\python -m collector.backfill
    .venv\\Scripts\\python -m collector.backfill --skip-hourly
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.app.config import OPENMETEO_SOURCE_NAME
from backend.app.db import session_scope
from backend.app.levels import classify
from backend.app.models import PrecipDaily

from . import openmeteo
from .pipeline import (
    UPSERT_CHUNK,
    finish_log,
    load_points,
    recompute_daily,
    start_log,
    upsert_hourly,
)

# 默认回填范围
DEFAULT_DAILY_YEARS = 3
DEFAULT_HOURLY_DAYS = 365
# 再分析资料的发布延迟余量（天）
ARCHIVE_LAG_DAYS = 30
# 每次 HTTP 请求携带的点位数
DAILY_CHUNK = 8
HOURLY_CHUNK = 4

LINE = "=" * 60


def _chunk_list(seq: list, size: int) -> list[list]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


# ------------------------------------------------------------------ 日数据

def backfill_daily(points: list[dict], start_date: str, end_date: str) -> int:
    """回填日降水总量。返回写入行数。"""
    written = 0
    chunks = _chunk_list(points, DAILY_CHUNK)
    for index, chunk in enumerate(chunks, start=1):
        records = openmeteo.fetch_archive(
            chunk,
            start_date=start_date,
            end_date=end_date,
            daily="precipitation_sum",
        )

        rows: list[dict] = []
        for record in records:
            point_id = int(record["point"]["id"])
            daily = record.get("daily") or {}
            for obs_date, value in zip(daily.get("time") or [], daily.get("precipitation_sum") or []):
                if value is None:
                    continue
                total = round(float(value), 2)
                rows.append(
                    {
                        "point_id": point_id,
                        "obs_date": obs_date,
                        "precip_sum": total,
                        "precip_max_hourly": None,  # 日值接口无小时明细
                        "rain_hours": None,
                        "rain_level": classify(total, hours=24),
                        "source": OPENMETEO_SOURCE_NAME,
                    }
                )

        if rows:
            with session_scope() as session:
                for start in range(0, len(rows), UPSERT_CHUNK):
                    piece = rows[start : start + UPSERT_CHUNK]
                    ins = sqlite_insert(PrecipDaily).values(piece)
                    ins = ins.on_conflict_do_update(
                        index_elements=["point_id", "obs_date", "source"],
                        set_={
                            "precip_sum": ins.excluded.precip_sum,
                            "rain_level": ins.excluded.rain_level,
                        },
                    )
                    session.execute(ins)
            written += len(rows)

        print(
            f"    日数据 [{index}/{len(chunks)}] 批次点数={len(chunk)} "
            f"本批 {len(rows)} 行，累计 {written} 行",
            flush=True,
        )

    return written


# ------------------------------------------------------------------ 小时数据

def backfill_hourly(points: list[dict], start_date: str, end_date: str) -> int:
    """回填逐小时降水。返回写入行数。"""
    written = 0
    chunks = _chunk_list(points, HOURLY_CHUNK)
    for index, chunk in enumerate(chunks, start=1):
        records = openmeteo.fetch_archive(
            chunk,
            start_date=start_date,
            end_date=end_date,
            hourly="precipitation",
        )

        rows: list[dict] = []
        for record in records:
            point_id = int(record["point"]["id"])
            hourly = record.get("hourly") or {}
            for obs_time, value in zip(hourly.get("time") or [], hourly.get("precipitation") or []):
                rows.append(
                    {
                        "point_id": point_id,
                        "obs_time": obs_time,
                        "precip_mm": float(value) if value is not None else None,
                        "source": OPENMETEO_SOURCE_NAME,
                        "is_forecast": 0,
                    }
                )

        if rows:
            with session_scope() as session:
                upsert_hourly(session, rows)
            written += len(rows)

        print(
            f"    小时数据 [{index}/{len(chunks)}] 批次点数={len(chunk)} "
            f"本批 {len(rows)} 行，累计 {written} 行",
            flush=True,
        )

    return written


# ------------------------------------------------------------------ 主流程

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="长三角降水历史数据回填")
    parser.add_argument("--daily-years", type=int, default=DEFAULT_DAILY_YEARS, help="日数据回填年数")
    parser.add_argument("--hourly-days", type=int, default=DEFAULT_HOURLY_DAYS, help="小时数据回填天数")
    parser.add_argument("--lag-days", type=int, default=ARCHIVE_LAG_DAYS, help="为再分析延迟预留的天数")
    parser.add_argument("--skip-daily", action="store_true", help="跳过日数据回填")
    parser.add_argument("--skip-hourly", action="store_true", help="跳过小时数据回填")
    args = parser.parse_args(argv)

    points = load_points()
    if not points:
        print("没有可用的采集点，请先运行：python -m collector.init_db", file=sys.stderr)
        return 1

    today = date.today()
    end = today - timedelta(days=args.lag_days)
    daily_start = end - timedelta(days=round(365.25 * args.daily_years))
    hourly_start = end - timedelta(days=args.hourly_days)

    print(LINE)
    print("  长三角降水历史数据回填")
    print(LINE)
    print(f"  采集点: {len(points)}")
    print(f"  日数据: {daily_start} ~ {end}（{args.daily_years} 年，约 {len(points) * (end - daily_start).days:,} 行）")
    print(f"  小时数据: {hourly_start} ~ {end}（{args.hourly_days} 天，约 {len(points) * (end - hourly_start).days * 24:,} 行）")
    print()

    log_id = start_log(mode="backfill", points_total=len(points))
    t0 = time.perf_counter()
    daily_rows = hourly_rows = 0

    try:
        if not args.skip_daily:
            print("  [1/3] 回填日数据 ...")
            daily_rows = backfill_daily(points, daily_start.isoformat(), end.isoformat())
            print(f"        日数据完成：{daily_rows:,} 行")
            print()

        if not args.skip_hourly:
            print("  [2/3] 回填小时数据 ...")
            hourly_rows = backfill_hourly(points, hourly_start.isoformat(), end.isoformat())
            print(f"        小时数据完成：{hourly_rows:,} 行")
            print()

            print("  [3/3] 用小时数据重算日汇总（补齐最大小时雨强与有雨小时数）...")
            with session_scope() as session:
                groups = recompute_daily(session, hourly_start.isoformat())
            print(f"        重算 {groups:,} 组（点位×日期）")
        else:
            print("  [3/3] 已跳过小时数据，无需重算日汇总")

        elapsed = time.perf_counter() - t0
        finish_log(
            log_id,
            status="success",
            rows_upserted=daily_rows + hourly_rows,
            gap_filled_hours=hourly_rows,
        )

        print()
        print(LINE)
        print(f"  回填完成：日数据 {daily_rows:,} 行 + 小时数据 {hourly_rows:,} 行")
        print(f"  耗时 {elapsed / 60:.1f} 分钟")
        print("  提示：再分析资料有延迟，最近一个月请运行 pipeline 补齐：")
        print("        .venv\\Scripts\\python -m collector.pipeline --past-days 30")
        print(LINE)
        return 0

    except Exception as exc:  # noqa: BLE001 - 任何异常都要落审计
        finish_log(
            log_id,
            status="failed",
            rows_upserted=daily_rows + hourly_rows,
            error_msg=f"{type(exc).__name__}: {exc}",
        )
        first_line = str(exc).strip().splitlines()[0][:300] if str(exc).strip() else ""
        print(f"回填失败：{type(exc).__name__}: {first_line}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
