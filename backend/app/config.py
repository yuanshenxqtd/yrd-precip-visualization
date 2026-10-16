"""全局配置：路径、数据库连接、外部数据源参数。

所有可调项均支持环境变量覆盖，便于在本机 / 局域网 / 公网三种部署形态间切换，
无需改动代码（对应 docs/PLAN.md 第 12 节的部署方案）。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- 路径
# 本文件位于 <项目根>/backend/app/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
GEOJSON_DIR = DATA_DIR / "geojson"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

for _d in (DATA_DIR, GEOJSON_DIR, SNAPSHOT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 临时目录自愈
# 本机的系统临时目录对 Python 不可用：tempfile 会报
#   FileNotFoundError: No usable temporary directory found
# 导致 pip / venv 卡死，以及 SQLite 写入时报
#   sqlite3.OperationalError: unable to open database file
# 因此这里在导入配置时就把 TMP/TEMP/TMPDIR 指向项目内的 .tmp 并确保其存在，
# 做到自愈 —— 任何入口只要 import 了本模块，就无需人工设置环境变量。
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)
for _var in ("TMP", "TEMP", "TMPDIR"):
    os.environ[_var] = str(TMP_DIR)
tempfile.tempdir = None  # 清除 tempfile 的目录缓存，使上面的设置立即生效


# ---------------------------------------------------------------- 数据库
DB_PATH = DATA_DIR / "weather.db"
DATABASE_URL = os.getenv("YRD_DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

# ---------------------------------------------------------------- 长三角行政区划
# 沪苏浙皖三省一市；上海下钻到「区」，其余三省到「市」
YRD_PROVINCES: tuple[dict[str, str], ...] = (
    {"adcode": "310000", "name": "上海市", "province": "上海"},
    {"adcode": "320000", "name": "江苏省", "province": "江苏"},
    {"adcode": "330000", "name": "浙江省", "province": "浙江"},
    {"adcode": "340000", "name": "安徽省", "province": "安徽"},
)

# 这些省/直辖市的下一级行政区类型是 district，其余是 city
DISTRICT_LEVEL_PROVINCES: frozenset[str] = frozenset({"310000"})

GEOJSON_URL_TEMPLATE = "https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json"
MERGED_GEOJSON_NAME = "yrd_merged.json"

# ---------------------------------------------------------------- Open-Meteo
OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPENMETEO_SOURCE_NAME = "open-meteo"

# 采集频率（分钟）。实测：56 点 × 48 轮 = 2688 次/天，占免费额度 26.9%
COLLECT_INTERVAL_MINUTES = int(os.getenv("YRD_COLLECT_INTERVAL_MINUTES", "30"))
# 自愈补采窗口。实测 API 上限为 92 天，超过会返回 HTTP 400
PAST_DAYS = int(os.getenv("YRD_PAST_DAYS", "3"))
FORECAST_DAYS = int(os.getenv("YRD_FORECAST_DAYS", "7"))
REQUEST_TIMEOUT = int(os.getenv("YRD_REQUEST_TIMEOUT", "90"))
TIMEZONE = "Asia/Shanghai"

# ---------------------------------------------------------------- 后端服务
API_HOST = os.getenv("YRD_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("YRD_API_PORT", "8000"))
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "YRD_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]
CACHE_TTL_SECONDS = int(os.getenv("YRD_CACHE_TTL", "60"))
