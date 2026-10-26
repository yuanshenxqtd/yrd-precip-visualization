"""采集完成后的一步：把「达标判定」结果落库。

为什么先落库、又还要实时算：
    · 落库（weather_alert, source='derived'）保留**历史轨迹** —— 将来可以看
      "某点位在哪些时刻达到过暴雨橙色标准"，也能和官方预警接进来后做对照。
    · 但界面上的「当前预警状态」必须**实时算**（`/api/alerts/active`），
      而不是读这张表 —— 因为表里的记录是采集时刻的快照，可能已过期。

唯一约束 (region_adcode, alert_type, published_at, source) 保证幂等：
同一时刻重复采集不会产生重复记录。
"""

from __future__ import annotations

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from backend.app.alerting import compute_active, to_alert_rows
from backend.app.models import WeatherAlert


def derive_and_store(session: Session) -> int:
    """计算当前达标点位并写入 weather_alert，返回本次命中的点位数。"""
    payload = compute_active(session)
    rows = to_alert_rows(payload)
    if not rows:
        return 0

    stmt = sqlite_insert(WeatherAlert).values(rows)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["region_adcode", "alert_type", "published_at", "source"]
    )
    session.execute(stmt)
    return len(rows)
