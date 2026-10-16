"""数据库初始化：建表 → 下载并合并 GeoJSON → 写入行政区划与采集点。

幂等：可重复运行，不会产生重复数据。

用法：
    .venv\\Scripts\\python -m collector.init_db
    或双击 scripts\\init_db.bat
"""

from __future__ import annotations

import sys
from datetime import datetime

from sqlalchemy import func, select

from backend.app.config import DB_PATH, OPENMETEO_SOURCE_NAME
from backend.app.db import init_db, session_scope
from backend.app.models import GridPoint, Meta, Region

from . import geojson, regions

LINE = "=" * 60


def _upsert_regions(session, rows: list[dict]) -> tuple[int, int]:
    inserted = updated = 0
    for row in rows:
        obj = session.get(Region, row["adcode"])
        if obj is None:
            session.add(Region(**row))
            inserted += 1
        else:
            for key, value in row.items():
                setattr(obj, key, value)
            updated += 1
    session.flush()
    return inserted, updated


def _upsert_points(session, rows: list[dict]) -> tuple[int, int]:
    inserted = updated = 0
    for row in rows:
        obj = session.scalar(
            select(GridPoint).where(GridPoint.region_adcode == row["region_adcode"])
        )
        if obj is None:
            session.add(GridPoint(**row))
            inserted += 1
        else:
            for key, value in row.items():
                setattr(obj, key, value)
            updated += 1
    session.flush()
    return inserted, updated


def _set_meta(session, key: str, value: str) -> None:
    obj = session.get(Meta, key)
    if obj is None:
        session.add(Meta(key=key, value=value))
    else:
        obj.value = value
        obj.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main() -> int:
    print(LINE)
    print("  长三角降水实时监测系统 · 数据库初始化")
    print(LINE)

    # ---------------------------------------------------------- 1 建表
    print("\n[1/4] 建表 ...")
    init_db()
    print(f"      数据库文件: {DB_PATH}")

    # ---------------------------------------------------------- 2 GeoJSON
    print("\n[2/4] 下载并合并 GeoJSON ...")
    by_adcode = geojson.download_all()
    for prov in by_adcode:
        print(f"      {prov}: {len(by_adcode[prov].get('features', []))} 个要素")

    merged = geojson.merge_features(by_adcode)
    merged_path = geojson.save_merged(merged)
    print(f"      合并地图: {merged_path.name}（{len(merged['features'])} 个要素）")

    # ---------------------------------------------------------- 3 入库
    print("\n[3/4] 写入行政区划与采集点 ...")
    region_rows = regions.build_regions(by_adcode)
    point_rows = regions.build_points(region_rows)

    with session_scope() as session:
        r_ins, r_upd = _upsert_regions(session, region_rows)
        p_ins, p_upd = _upsert_points(session, point_rows)
        _set_meta(session, "db_initialized_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        _set_meta(session, "data_source", OPENMETEO_SOURCE_NAME)
        _set_meta(session, "region_count", str(len(region_rows)))
        _set_meta(session, "point_count", str(len(point_rows)))

    print(f"      行政区划: 新增 {r_ins} 条，更新 {r_upd} 条（共 {len(region_rows)} 条）")
    print(f"      采集点:   新增 {p_ins} 个，更新 {p_upd} 个（共 {len(point_rows)} 个）")

    # ---------------------------------------------------------- 4 校验
    print("\n[4/4] 校验 ...")
    with session_scope() as session:
        total_region = session.scalar(select(func.count()).select_from(Region))
        total_monitored = session.scalar(
            select(func.count()).select_from(Region).where(Region.is_monitored == 1)
        )
        total_point = session.scalar(select(func.count()).select_from(GridPoint))
        breakdown = session.execute(
            select(Region.province, Region.level, func.count())
            .where(Region.is_monitored == 1)
            .group_by(Region.province, Region.level)
            .order_by(Region.province)
        ).all()

    print(f"      region 总数:      {total_region}（其中参与监测 {total_monitored}）")
    print(f"      grid_point 总数:  {total_point}")
    print("      按省/级别分布:")
    for province, level, count in breakdown:
        print(f"        {province:<4} {level:<9} {count:>3}")

    # ---------------------------------------------------------- 结论
    ok = total_point == 56 and total_monitored == 56 and total_region == 60
    print()
    if ok:
        print("  [OK] 校验通过：60 条行政区划 / 56 个采集点，与规划一致。")
        return 0
    print("  [!!] 校验未通过：请检查 GeoJSON 要素数量是否变化。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
