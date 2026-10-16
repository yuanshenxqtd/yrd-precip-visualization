"""降水数据采集器包。

模块划分：
    regions.py    56 个采集点的构建
    geojson.py    行政区划 GeoJSON 下载与合并
    openmeteo.py  Open-Meteo API 客户端
    pipeline.py   采集主流程（自愈补采 + 幂等写入）
    backfill.py   历史数据回填
    scheduler.py  30 分钟定时调度
"""

__version__ = "0.1.0"
