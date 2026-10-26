"""从本机完整数据库生成一份「种子数据库」，让仓库克隆者开箱就有数据。

生成内容（按体积/价值权衡）：
    · region / grid_point / meta        —— 全量（很小）
    · precip_daily                      —— **全量 3 年**（约 6.4 万行，才几 MB，
                                           足够支撑日/月/年趋势、距平、等级分布、极值榜）
    · precip_hourly                     —— **最近 N 天** + **两场演示过程**
                                           （2026-08-09 / 08-10 大暴雨，共 2688 行，
                                           保证「空间分布」的回放预设有画面）
    · collect_log                       —— 最近若干条（数据质量页要用）
    · weather_alert                     —— 全量（当前为空）

用法：
    .venv\\Scripts\\python.exe deploy\\make_seed.py
    .venv\\Scripts\\python.exe deploy\\make_seed.py --days 30 --out data\\seed.db
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 演示过程（答辩/回放用），整段小时数据一并带上
DEMO_RANGES = [
    ("2026-08-09T00:00", "2026-08-11T00:00"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "data", "weather.db"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "seed.db"))
    ap.add_argument("--days", type=int, default=30, help="保留最近多少天的小时数据")
    ap.add_argument("--logs", type=int, default=20, help="保留最近多少条采集日志")
    args = ap.parse_args()

    if not os.path.exists(args.src):
        raise SystemExit(f"源数据库不存在: {args.src}")
    if os.path.exists(args.out):
        os.remove(args.out)

    src = sqlite3.connect(args.src)
    latest = src.execute("select max(obs_time) from precip_hourly where is_forecast = 0").fetchone()[0]
    if not latest:
        raise SystemExit("源库里没有实况小时数据")
    cutoff = (datetime.fromisoformat(latest) - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M")

    # ---- 建表：直接复制源库 DDL ----
    dst = sqlite3.connect(args.out)
    for sql in [r[0] for r in src.execute("select sql from sqlite_master where type='table' and sql is not null")]:
        dst.execute(sql)
    for sql in [r[0] for r in src.execute("select sql from sqlite_master where type='index' and sql is not null")]:
        dst.execute(sql)

    dst.execute("ATTACH DATABASE ? AS s", (args.src,))

    plan: list[tuple[str, str]] = [
        ("region", "select * from s.region"),
        ("grid_point", "select * from s.grid_point"),
        ("meta", "select * from s.meta"),
        ("weather_alert", "select * from s.weather_alert"),
        ("precip_daily", "select * from s.precip_daily"),
    ]

    for table, select_sql in plan:
        cols = [r[1] for r in dst.execute(f"pragma main.table_info({table})")]
        collist = ", ".join(cols)
        dst.execute(f"insert into main.{table} ({collist}) {select_sql}")

    # ---- 小时数据：最近 N 天 + 演示过程 ----
    cols = [r[1] for r in dst.execute("pragma main.table_info(precip_hourly)")]
    collist = ", ".join(cols)
    dst.execute(
        f"insert into main.precip_hourly ({collist}) "
        "select * from s.precip_hourly where obs_time >= ?",
        (cutoff,),
    )
    for start, end in DEMO_RANGES:
        dst.execute(
            f"insert or ignore into main.precip_hourly ({collist}) "
            "select * from s.precip_hourly where obs_time >= ? and obs_time < ?",
            (start, end),
        )

    # ---- 采集日志 ----
    cols = [r[1] for r in dst.execute("pragma main.table_info(collect_log)")]
    collist = ", ".join(cols)
    dst.execute(
        f"insert into main.collect_log ({collist}) "
        "select * from s.collect_log order by id desc limit ?",
        (args.logs,),
    )

    dst.commit()
    dst.execute("DETACH DATABASE s")
    dst.execute("VACUUM")
    dst.commit()

    # ---- 汇报 ----
    size_mb = os.path.getsize(args.out) / 1024 / 1024
    print(f"latest obs_time : {latest}   小时数据保留自 {cutoff}")
    print(f"output          : {args.out}  ({size_mb:.1f} MB)")
    for table in ("region", "grid_point", "precip_hourly", "precip_daily", "collect_log", "meta"):
        n = dst.execute(f"select count(*) from {table}").fetchone()[0]
        print(f"  {table:16} {n:>8}")
    dst.close()
    src.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
