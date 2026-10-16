"""Open-Meteo API 客户端。

设计要点（依据 docs/DATA_SOURCE.md 的实测结论）：
    - 56 个点位合并为 **一次 HTTP 请求**（实测 4.4 秒返回，URL 仅 1299 字符）
    - 免 API Key，免费额度 10,000 次/天
    - timezone 固定 Asia/Shanghai，返回的 hourly.time 形如 "2026-10-05T00:00"
"""

from __future__ import annotations

import time
from typing import Any, Callable, Sequence

import requests

from backend.app.config import (
    FORECAST_DAYS,
    OPENMETEO_ARCHIVE_URL,
    OPENMETEO_FORECAST_URL,
    PAST_DAYS,
    REQUEST_TIMEOUT,
    TIMEZONE,
)

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3.0


class OpenMeteoError(RuntimeError):
    """Open-Meteo 调用失败。"""


def fetch_hourly_precipitation(
    points: Sequence[dict[str, Any]],
    *,
    past_days: int = PAST_DAYS,
    forecast_days: int = FORECAST_DAYS,
) -> list[dict[str, Any]]:
    """批量获取多个点位的逐小时降水量。

    Args:
        points: [{"id": 1, "lon": 121.49, "lat": 31.22, "label": "黄浦区"}, ...]

    Returns:
        与 points 顺序一致的列表：
        [{"point": {...}, "times": [...], "values": [...], "lat": .., "lon": ..}, ...]

    Raises:
        OpenMeteoError: 重试 MAX_ATTEMPTS 次后仍失败，或返回点位数量不匹配。
    """
    if not points:
        return []

    lats = ",".join(f"{float(p['lat']):.4f}" for p in points)
    lons = ",".join(f"{float(p['lon']):.4f}" for p in points)

    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": "precipitation",
        "past_days": int(past_days),
        "forecast_days": int(forecast_days),
        "timezone": TIMEZONE,
    }

    data: Any = None
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(OPENMETEO_FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:  # noqa: BLE001 - 网络异常种类多，统一重试
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    else:
        raise OpenMeteoError(f"请求 Open-Meteo 失败（已重试 {MAX_ATTEMPTS} 次）：{last_error}")

    records = data if isinstance(data, list) else [data]
    if len(records) != len(points):
        raise OpenMeteoError(
            f"返回点位数量不匹配：请求 {len(points)} 个，返回 {len(records)} 个"
        )

    results: list[dict[str, Any]] = []
    for point, record in zip(points, records):
        hourly = record.get("hourly") or {}
        results.append(
            {
                "point": point,
                "times": hourly.get("time") or [],
                "values": hourly.get("precipitation") or [],
                "api_lat": record.get("latitude"),
                "api_lon": record.get("longitude"),
            }
        )
    return results


# ---------------------------------------------------------------- 历史接口

def _archive_request(
    chunk: Sequence[dict[str, Any]],
    *,
    start_date: str,
    end_date: str,
    daily: str | None,
    hourly: str | None,
) -> list[dict[str, Any]]:
    """对一批坐标调用一次 archive-api。"""
    params: dict[str, Any] = {
        "latitude": ",".join(f"{float(p['lat']):.4f}" for p in chunk),
        "longitude": ",".join(f"{float(p['lon']):.4f}" for p in chunk),
        "start_date": start_date,
        "end_date": end_date,
        "timezone": TIMEZONE,
    }
    if daily:
        params["daily"] = daily
    if hourly:
        params["hourly"] = hourly

    data: Any = None
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(OPENMETEO_ARCHIVE_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    else:
        raise OpenMeteoError(
            f"请求 archive-api 失败（{start_date}~{end_date}，{len(chunk)} 个点位，"
            f"已重试 {MAX_ATTEMPTS} 次）：{last_error}"
        )

    records = data if isinstance(data, list) else [data]
    if len(records) != len(chunk):
        raise OpenMeteoError(
            f"archive 返回点位数量不匹配：请求 {len(chunk)} 个，返回 {len(records)} 个"
        )

    return [
        {
            "point": point,
            "daily": record.get("daily"),
            "hourly": record.get("hourly"),
            "api_lat": record.get("latitude"),
            "api_lon": record.get("longitude"),
        }
        for point, record in zip(chunk, records)
    ]


def fetch_archive(
    points: Sequence[dict[str, Any]],
    *,
    start_date: str,
    end_date: str,
    daily: str | None = None,
    hourly: str | None = None,
    chunk_size: int = 8,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[dict[str, Any]]:
    """调用 archive-api 批量获取历史数据（可回溯至 1940 年）。

    自动按 chunk_size 分批，避免单次请求过大。
    on_progress(已完成点位数, 总点位数) 用于输出进度。
    """
    results: list[dict[str, Any]] = []
    total = len(points)
    for start in range(0, total, chunk_size):
        chunk = points[start : start + chunk_size]
        results.extend(
            _archive_request(
                chunk, start_date=start_date, end_date=end_date, daily=daily, hourly=hourly
            )
        )
        if on_progress:
            on_progress(min(start + chunk_size, total), total)
    return results
