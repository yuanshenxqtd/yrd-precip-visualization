"""前台定时采集器（B 方案的新形态）。

设计要点 —— 与「开机自启的计划任务」完全不同：

    * **不做任何系统注册**：不写注册表、不放启动文件夹、不建计划任务。
      因此无论正常重启还是「快速启动」，下一次开机时它**默认就是关闭的**。
    * **由用户手动启动**：双击 scripts\\start_autocollect.bat，或运行本模块。
    * **前台常驻**：启动后立即采集一次，之后每 N 分钟采集一次，
      直到用户关闭窗口（Ctrl+C）或电脑关机/休眠终止进程。
    * **自愈不变**：每轮仍回拉 past_days 天并幂等 UPSERT，
      所以停机期间产生的时间缺口，下次启动时自动补齐，数据始终完整。

用法：
    .venv\\Scripts\\python -m collector.scheduler
    .venv\\Scripts\\python -m collector.scheduler --interval 30
    .venv\\Scripts\\python -m collector.scheduler --once      # 只跑一次
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.app.config import COLLECT_INTERVAL_MINUTES, PAST_DAYS

from .pipeline import collect

LINE = "=" * 62
_stop_requested = False


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _handle_stop(signum, _frame) -> None:
    global _stop_requested
    _stop_requested = True
    print(f"\n[{_now()}] 收到停止信号（{signum}），本轮结束后退出 ...", flush=True)


def _run_once(interval_minutes: int, past_days: int) -> None:
    """执行一次采集；任何异常都不得中断常驻循环。"""
    print(f"\n[{_now()}] ── 开始采集 ──", flush=True)
    try:
        summary = collect(
            mode="realtime",
            past_days=past_days,
            forecast_days=7,
            verbose=True,
        )
        print(
            f"[{_now()}] ── 完成：写入 {summary['rows_written']:,} 行"
            f"（新增 {summary['rows_inserted']:,}），耗时 {summary['elapsed_seconds']}s"
            f"；下次 {interval_minutes} 分钟后 ──",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001 - 单次失败不能终止常驻循环
        first_line = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else ""
        print(f"[{_now()}] ── 本轮失败：{type(exc).__name__}: {first_line}", flush=True)
        print(f"[{_now()}] ── 已在 collect_log 留痕；{interval_minutes} 分钟后自动重试 ──", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="长三角降水 · 前台定时采集")
    parser.add_argument(
        "--interval",
        type=int,
        default=COLLECT_INTERVAL_MINUTES,
        help=f"采集间隔（分钟），默认 {COLLECT_INTERVAL_MINUTES}",
    )
    parser.add_argument("--past-days", type=int, default=PAST_DAYS, help=f"自愈补采窗口（天），默认 {PAST_DAYS}")
    parser.add_argument("--once", action="store_true", help="只采集一次后退出")
    args = parser.parse_args(argv)

    if args.once:
        _run_once(args.interval, args.past_days)
        return 0

    signal.signal(signal.SIGINT, _handle_stop)
    try:
        signal.signal(signal.SIGTERM, _handle_stop)
    except (AttributeError, ValueError):  # 某些平台不支持
        pass

    print(LINE)
    print("  长三角降水 · 前台定时采集")
    print(LINE)
    print(f"  采集间隔: {args.interval} 分钟")
    print(f"  自愈窗口: 每轮回拉过去 {args.past_days} 天（幂等 UPSERT，不产生重复）")
    print("  运行方式: 前台常驻，关闭窗口或关机即停止")
    print("  开机自启: 无（未做任何系统注册，下次开机默认关闭）")
    print(LINE)
    print("  按 Ctrl+C 可随时停止\n")

    # 立即先跑一次，避免等一个间隔
    _run_once(args.interval, args.past_days)

    if _stop_requested:
        print(f"[{_now()}] 已退出。")
        return 0

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _run_once,
        trigger=IntervalTrigger(minutes=args.interval),
        args=[args.interval, args.past_days],
        id="collect",
        name=f"每 {args.interval} 分钟采集长三角降水",
        max_instances=1,
        coalesce=True,          # 若因休眠错过多次，只补跑一次（其余由自愈补采覆盖）
        misfire_grace_time=300,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)

    print(f"\n[{_now()}] 采集器已停止。")
    print(f"[{_now()}] 提示：停机期间的数据缺口会在下次启动时自动补齐（自愈补采）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
