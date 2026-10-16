"""由 GeoJSON 构建 region（行政区划）与 grid_point（采集点）记录。

规则（对应 docs/PLAN.md 第 2 节已锁定决策）：
    - 4 条省级记录：上海市 / 江苏省 / 浙江省 / 安徽省，is_monitored = 0（不参与采集）
    - 上海市下钻到「区」(district) —— 16 个
    - 江苏 / 浙江 / 安徽 下钻到「市」(city) —— 13 + 11 + 16 = 40 个
    - 合计 60 条 region，其中 56 条 is_monitored = 1，各生成 1 个采集点
"""

from __future__ import annotations

from backend.app.config import DISTRICT_LEVEL_PROVINCES, OPENMETEO_SOURCE_NAME, YRD_PROVINCES


def build_regions(by_adcode: dict[str, dict]) -> list[dict]:
    """构建 region 表记录（省级 + 市/区级）。"""
    rows: list[dict] = []

    for prov in YRD_PROVINCES:
        adcode = prov["adcode"]
        features = by_adcode.get(adcode, {}).get("features", [])

        # 省级记录：用下辖单元中心点的均值作为近似省级中心（仅用于展示，不参与采集）
        centers = [
            f["properties"].get("center") or f["properties"].get("centroid")
            for f in features
        ]
        centers = [c for c in centers if c]
        if centers:
            lon = sum(float(c[0]) for c in centers) / len(centers)
            lat = sum(float(c[1]) for c in centers) / len(centers)
        else:  # 理论上不会发生
            lon = lat = 0.0

        rows.append(
            {
                "adcode": adcode,
                "name": prov["name"],
                "level": "province",
                "parent_adcode": None,
                "province": prov["province"],
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "is_monitored": 0,
            }
        )

        child_level = "district" if adcode in DISTRICT_LEVEL_PROVINCES else "city"
        for feat in features:
            props = feat.get("properties", {})
            center = props.get("center") or props.get("centroid")
            if not center or not props.get("adcode"):
                continue
            rows.append(
                {
                    "adcode": str(props["adcode"]),
                    "name": props["name"],
                    "level": child_level,
                    "parent_adcode": adcode,
                    "province": prov["province"],
                    "lon": round(float(center[0]), 6),
                    "lat": round(float(center[1]), 6),
                    "is_monitored": 1,
                }
            )

    return rows


def build_points(region_rows: list[dict], source: str = OPENMETEO_SOURCE_NAME) -> list[dict]:
    """为每个被监测区域生成一个采集点。"""
    return [
        {
            "region_adcode": r["adcode"],
            "lon": r["lon"],
            "lat": r["lat"],
            "source": source,
            "label": r["name"],
            "is_active": 1,
        }
        for r in region_rows
        if r["is_monitored"] == 1
    ]
