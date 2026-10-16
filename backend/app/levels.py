"""降水量等级判定（GB/T 28592-2012）。

阈值来源：中国气象局官网《降雨量等级》
https://www.cma.gov.cn/2011xzt/2013zhuant/20130620_3/2013062002/201308/t20130816_223400.html

    等级        12 小时 (mm)      24 小时 (mm)
    微量降雨     —                < 0.1
    小雨         0.1 – 4.9        0.1 – 9.9
    中雨         5.0 – 14.9       10.0 – 24.9
    大雨         15.0 – 29.9      25.0 – 49.9
    暴雨         30.0 – 69.9      50.0 – 99.9
    大暴雨       70.0 – 139.9     100.0 – 249.9
    特大暴雨     ≥ 140.0          ≥ 250.0
"""

from __future__ import annotations

# (等级名, 该等级的下界)，按降序排列，取第一个满足 value >= 下界的等级
_THRESHOLDS_24H: tuple[tuple[str, float], ...] = (
    ("特大暴雨", 250.0),
    ("大暴雨", 100.0),
    ("暴雨", 50.0),
    ("大雨", 25.0),
    ("中雨", 10.0),
    ("小雨", 0.1),
)

_THRESHOLDS_12H: tuple[tuple[str, float], ...] = (
    ("特大暴雨", 140.0),
    ("大暴雨", 70.0),
    ("暴雨", 30.0),
    ("大雨", 15.0),
    ("中雨", 5.0),
    ("小雨", 0.1),
)

NO_RAIN = "无降水"


def classify(precip_mm: float | None, *, hours: int = 24) -> str:
    """按国标返回降水等级名。

    hours = 24 用 24 小时口径（本项目日数据默认），hours = 12 用 12 小时口径。
    """
    if precip_mm is None or precip_mm < 0.1:
        return NO_RAIN

    table = _THRESHOLDS_12H if hours == 12 else _THRESHOLDS_24H
    for name, lower in table:
        if precip_mm >= lower:
            return name
    return NO_RAIN


# 前端配色用（浅蓝 -> 红，符合气象习惯）
LEVEL_COLORS: dict[str, str] = {
    NO_RAIN: "#2b3a55",
    "小雨": "#7fd0f5",
    "中雨": "#3aa0e0",
    "大雨": "#f5d76e",
    "暴雨": "#f39c12",
    "大暴雨": "#e74c3c",
    "特大暴雨": "#8e1b1b",
}
