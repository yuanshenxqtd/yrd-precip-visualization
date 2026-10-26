"""本地「达标判定」：把国标暴雨预警阈值应用到实况降水上。

为什么叫「达标判定」而不叫「预警」
--------------------------------
官方暴雨预警是**预报性**的（"未来 3/6/12 小时降雨量将达 50 mm 以上"），
本项目只有历史实况，只能**回看**（"过去 12 小时已累计 50 mm"）。
两者性质不同 —— 所以界面上必须明确区分，绝不能把本地判定伪装成官方发布。

阈值来源：《气象灾害预警信号发布与传播办法》暴雨预警信号
    · 蓝色：12 小时内降雨量将达 50 mm 以上
    · 黄色： 6 小时内降雨量将达 50 mm 以上
    · 橙色： 3 小时内降雨量将达 50 mm 以上
    · 红色： 3 小时内降雨量将达 100 mm 以上

本模块把它们映射成「过去 N 小时累计」的回看口径，取**满足的最高等级**。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import GridPoint, PrecipHourly, Region

NOTE = "本地达标判定（回看口径）：按国标暴雨预警阈值折算为「过去 N 小时累计」，不是气象部门发布的预警信号。"

# 顺序即优先级：红色最高
THRESHOLDS: list[dict[str, Any]] = [
    {"key": "red", "name": "红色", "hours": 3, "min_mm": 100.0, "color": "#e74c3c"},
    {"key": "orange", "name": "橙色", "hours": 3, "min_mm": 50.0, "color": "#f39c12"},
    {"key": "yellow", "name": "黄色", "hours": 6, "min_mm": 50.0, "color": "#f5d76e"},
    {"key": "blue", "name": "蓝色", "hours": 12, "min_mm": 50.0, "color": "#3aa0e0"},
]

_LEVEL_BY_KEY = {t["key"]: t for t in THRESHOLDS}


def _shift(ts: str, hours: int) -> str:
    return (datetime.fromisoformat(ts) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")


def classify(sum3: float, sum6: float, sum12: float) -> dict[str, Any] | None:
    """返回满足的最高预警等级；都不满足时返回 None。"""
    if sum3 >= 100.0:
        return _LEVEL_BY_KEY["red"]
    if sum3 >= 50.0:
        return _LEVEL_BY_KEY["orange"]
    if sum6 >= 50.0:
        return _LEVEL_BY_KEY["yellow"]
    if sum12 >= 50.0:
        return _LEVEL_BY_KEY["blue"]
    return None


def latest_observed(session: Session) -> str | None:
    return session.scalar(
        select(func.max(PrecipHourly.obs_time)).where(PrecipHourly.is_forecast == 0)
    )


def _window_sums(session: Session, hours: int, latest: str) -> dict[int, float]:
    """某个回看窗口内，各点位的累计降水量。"""
    start = _shift(latest, -(hours - 1))
    rows = session.execute(
        select(PrecipHourly.point_id, func.sum(PrecipHourly.precip_mm))
        .where(
            PrecipHourly.is_forecast == 0,
            PrecipHourly.obs_time >= start,
            PrecipHourly.obs_time <= latest,
        )
        .group_by(PrecipHourly.point_id)
    ).all()
    return {int(pid): float(total or 0.0) for pid, total in rows}


def _peak_hourly(session: Session, hours: int, latest: str) -> dict[int, float]:
    start = _shift(latest, -(hours - 1))
    rows = session.execute(
        select(PrecipHourly.point_id, func.max(PrecipHourly.precip_mm))
        .where(
            PrecipHourly.is_forecast == 0,
            PrecipHourly.obs_time >= start,
            PrecipHourly.obs_time <= latest,
        )
        .group_by(PrecipHourly.point_id)
    ).all()
    return {int(pid): float(peak or 0.0) for pid, peak in rows}


def compute_active(session: Session) -> dict[str, Any]:
    """当前时刻，哪些点位达到暴雨预警标准。"""
    latest = latest_observed(session)
    points_total = session.scalar(select(func.count()).select_from(GridPoint)) or 0

    result: dict[str, Any] = {
        "latest_obs_time": latest,
        "points_total": points_total,
        "triggered": 0,
        "points": [],
        "thresholds": THRESHOLDS,
        "note": NOTE,
    }
    if latest is None:
        return result

    sums = {h: _window_sums(session, h, latest) for h in (3, 6, 12)}
    peaks = _peak_hourly(session, 12, latest)

    meta = {
        int(gid): (adcode, label, province)
        for gid, adcode, label, province in session.execute(
            select(GridPoint.id, GridPoint.region_adcode, GridPoint.label, Region.province).join(
                Region, Region.adcode == GridPoint.region_adcode
            )
        ).all()
    }

    hits: list[dict[str, Any]] = []
    for gid, (adcode, label, province) in meta.items():
        s3 = sums[3].get(gid, 0.0)
        s6 = sums[6].get(gid, 0.0)
        s12 = sums[12].get(gid, 0.0)
        level = classify(s3, s6, s12)
        if level is None:
            continue
        hits.append(
            {
                "adcode": adcode,
                "name": label,
                "province": province,
                "level_key": level["key"],
                "level_name": level["name"],
                "level_color": level["color"],
                "rule_hours": level["hours"],
                "rule_min_mm": level["min_mm"],
                "sum_3h": round(s3, 1),
                "sum_6h": round(s6, 1),
                "sum_12h": round(s12, 1),
                "peak_hourly": round(peaks.get(gid, 0.0), 1),
            }
        )

    # 排序：等级优先（红→蓝），同级按 12 小时累计降序
    order = {t["key"]: i for i, t in enumerate(THRESHOLDS)}
    hits.sort(key=lambda x: (order[x["level_key"]], -x["sum_12h"]))

    result["points"] = hits
    result["triggered"] = len(hits)
    return result


def to_alert_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """把判定结果转成 weather_alert 表可写入的行。

    `published_at` 用实况时刻，配合唯一约束
    (region_adcode, alert_type, published_at, source) 实现幂等写入。
    """
    latest = payload.get("latest_obs_time")
    if not latest:
        return []
    rows = []
    for p in payload["points"]:
        rows.append(
            {
                "region_adcode": p["adcode"],
                "alert_type": f"暴雨{p['level_name']}",
                "alert_level": p["level_name"],
                "title": f"{p['name']} 达到暴雨{p['level_name']}预警标准（过去 {p['rule_hours']} 小时累计 ≥ {p['rule_min_mm']:.0f} mm）",
                "published_at": latest,
                "source": "derived",
                "raw_json": __import__("json").dumps(p, ensure_ascii=False),
            }
        )
    return rows
