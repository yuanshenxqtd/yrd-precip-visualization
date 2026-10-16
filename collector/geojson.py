"""行政区划 GeoJSON 的下载、合并与本地缓存。

数据源：阿里云 DataV GeoAtlas
    https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json

四份文件（沪苏浙皖）合并为一个 FeatureCollection，
即得到「长三角 56 个行政单元」的单一地图，前端可直接注册为 ECharts 地图。
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

from backend.app.config import (
    GEOJSON_DIR,
    GEOJSON_URL_TEMPLATE,
    MERGED_GEOJSON_NAME,
    REQUEST_TIMEOUT,
    YRD_PROVINCES,
)


def province_file(adcode: str) -> Path:
    """单个省/直辖市 GeoJSON 的本地缓存路径。"""
    return GEOJSON_DIR / f"{adcode}.json"


def merged_file() -> Path:
    """合并后地图的本地路径。"""
    return GEOJSON_DIR / MERGED_GEOJSON_NAME


def fetch_province(adcode: str, *, force: bool = False) -> dict:
    """获取单个省/直辖市的 GeoJSON；本地有缓存且未强制刷新时直接读缓存。"""
    path = province_file(adcode)
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))

    url = GEOJSON_URL_TEMPLATE.format(adcode=adcode)
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    GEOJSON_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def download_all(*, force: bool = False) -> dict[str, dict]:
    """下载（或读缓存）长三角四份 GeoJSON，返回 {adcode: geojson}。"""
    return {p["adcode"]: fetch_province(p["adcode"], force=force) for p in YRD_PROVINCES}


def merge_features(by_adcode: dict[str, dict]) -> dict:
    """把四份 GeoJSON 合并成一个长三角 FeatureCollection。

    每个要素额外写入 province / province_adcode，便于前端按省筛选。
    """
    features: list[dict] = []
    for prov in YRD_PROVINCES:
        adcode = prov["adcode"]
        for feat in by_adcode.get(adcode, {}).get("features", []):
            props = feat.setdefault("properties", {})
            props["province"] = prov["province"]
            props["province_adcode"] = adcode
            features.append(feat)

    return {
        "type": "FeatureCollection",
        "name": "yrd_merged",
        "features": features,
    }


def save_merged(collection: dict) -> Path:
    """保存合并地图到 data/geojson/。"""
    path = merged_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
    return path


def load_merged() -> dict:
    """读取合并后的长三角地图。"""
    path = merged_file()
    if not path.exists():
        raise FileNotFoundError(
            f"合并地图不存在：{path}\n请先运行：.venv\\Scripts\\python -m collector.init_db"
        )
    return json.loads(path.read_text(encoding="utf-8"))
