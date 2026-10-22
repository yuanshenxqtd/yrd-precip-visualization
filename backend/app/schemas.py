"""API 响应契约（Pydantic 模型）。

这些模型会直接呈现在 FastAPI 自动生成的 Swagger 文档中
（http://127.0.0.1:8000/docs），是论文「接口设计」一节的截图素材。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetaOut(BaseModel):
    """系统与数据源状态。"""

    data_source: str = Field(description="数据源标识")
    points_total: int = Field(description="采集点总数")
    regions_total: int = Field(description="行政区划总数")
    hourly_rows: int = Field(description="逐小时降水总行数")
    daily_rows: int = Field(description="日汇总总行数")
    hourly_start: str | None = Field(default=None, description="小时数据起始时刻")
    hourly_end: str | None = Field(
        default=None, description="小时数据结束时刻（含预报，可能在未来）"
    )
    observed_start: str | None = Field(default=None, description="实况数据起始时刻")
    observed_end: str | None = Field(
        default=None, description="实况数据最新时刻 —— 判断数据时效只能用这个字段"
    )
    forecast_end: str | None = Field(default=None, description="预报数据最远时刻")
    server_now: str = Field(description="服务器当前时间（供前端计算数据时效，避免时钟偏差）")
    daily_start: str | None = Field(default=None, description="日数据起始日期")
    daily_end: str | None = Field(default=None, description="日数据结束日期")
    last_collect_at: str | None = Field(default=None, description="最近一次采集开始时间")
    last_collect_status: str | None = Field(default=None, description="最近一次采集状态")
    db_initialized_at: str | None = Field(default=None, description="数据库初始化时间")
    collect_interval_minutes: int = Field(description="采集间隔（分钟）")


class RegionOut(BaseModel):
    """行政区划。"""

    adcode: str = Field(description="行政区划代码")
    name: str = Field(description="名称")
    level: str = Field(description="层级：province / city / district")
    parent_adcode: str | None = Field(default=None, description="上级代码")
    province: str = Field(description="所属省市")
    lon: float = Field(description="中心经度")
    lat: float = Field(description="中心纬度")
    is_monitored: int = Field(description="是否参与采集：1 是，0 否")


class TrendPoint(BaseModel):
    """时间序列上的一个点。"""

    time: str = Field(description="时间标签")
    value: float = Field(description="降水值（mm）")


class RankingItem(BaseModel):
    """排行榜条目。"""

    adcode: str = Field(description="行政区划代码")
    name: str = Field(description="点位名称")
    province: str = Field(description="所属省市")
    total: float = Field(description="区间累计降水（mm）")
    peak: float | None = Field(default=None, description="最大小时雨强（mm）")


class MapPoint(BaseModel):
    """地图上的一个点位取值。"""

    adcode: str = Field(description="行政区划代码")
    name: str = Field(description="点位名称")
    province: str = Field(description="所属省市")
    lon: float = Field(description="经度")
    lat: float = Field(description="纬度")
    value: float | None = Field(default=None, description="降水值（mm）")
    level: str | None = Field(default=None, description="降水等级（GB/T 28592-2012）")
    color: str | None = Field(default=None, description="建议配色")


class MapFrame(BaseModel):
    """时间轴回放的一帧。"""

    time: str = Field(description="时刻")
    values: dict[str, float | None] = Field(description="行政区划代码 -> 降水量（mm）")


class SummaryOut(BaseModel):
    """总览指标卡。"""

    latest_obs_time: str | None = Field(default=None, description="最新实况时刻")
    points_total: int = Field(description="点位总数")
    points_with_rain: int = Field(description="该时刻有降水的点位数")
    rain_coverage_pct: float = Field(description="降水覆盖率（%）")
    sum_24h_mm: float = Field(description="近 24 小时全区累计（mm）")
    max_hourly_mm: float | None = Field(default=None, description="近 24 小时最大小时雨强")
    max_hourly_point: str | None = Field(default=None, description="最大小时雨强点位")
    max_hourly_time: str | None = Field(default=None, description="最大小时雨强出现时刻")
    wettest_point: str | None = Field(default=None, description="近 24 小时累计最多点位")
    wettest_24h_mm: float = Field(default=0.0, description="该点位近 24 小时累计")
    today_wettest_point: str | None = Field(default=None, description="今日累计最多点位")
    today_wettest_mm: float = Field(default=0.0, description="今日最大累计")
    last_collect_at: str | None = Field(default=None, description="最近一次采集时间")
    last_collect_status: str | None = Field(default=None, description="最近一次采集状态")
    forecast_hours: int = Field(default=0, description="库内预报小时数")


class LevelCount(BaseModel):
    """降水等级计数。"""

    rain_level: str = Field(description="等级名")
    count: int = Field(description="天数")
    color: str | None = Field(default=None, description="建议配色")


class ExtremeEvent(BaseModel):
    """极端降水事件（单日单点）。"""

    adcode: str = Field(description="行政区划代码")
    name: str = Field(description="点位名称")
    province: str = Field(description="所属省市")
    obs_date: str = Field(description="日期")
    precip_sum: float = Field(description="日累计降水（mm）")
    precip_max_hourly: float | None = Field(default=None, description="最大小时雨强（mm/h）")
    rain_hours: int | None = Field(default=None, description="有雨小时数；null 表示无小时明细")
    rain_level: str | None = Field(default=None, description="降水等级")
    color: str | None = Field(default=None, description="建议配色")


class AnomalyPoint(BaseModel):
    """降水距平。"""

    month: str = Field(description="月份，如 2026-08")
    actual: float = Field(description="当月实际降水累计（mm）")
    baseline: float = Field(description="同期基准值（mm）")
    anomaly_pct: float | None = Field(default=None, description="距平百分比（%）")


class BoxplotItem(BaseModel):
    """箱线图统计量。"""

    adcode: str = Field(description="行政区划代码")
    name: str = Field(description="点位名称")
    province: str = Field(description="所属省市")
    min: float = Field(description="最小值")
    q1: float = Field(description="下四分位")
    median: float = Field(description="中位数")
    q3: float = Field(description="上四分位")
    max: float = Field(description="最大值")
    mean: float = Field(description="平均值")


class CollectLogOut(BaseModel):
    """采集日志条目。"""

    id: int
    source: str = Field(description="数据源")
    mode: str = Field(description="采集模式")
    status: str = Field(description="状态：running / success / failed")
    points_total: int = Field(description="点位数")
    rows_upserted: int = Field(description="写入行数")
    gap_filled_hours: int = Field(description="新补充的小时数")
    started_at: str = Field(description="开始时间")
    finished_at: str | None = Field(default=None, description="结束时间")
    error_msg: str | None = Field(default=None, description="错误信息")


class QualityOut(BaseModel):
    """数据质量报告。"""

    hourly_rows: int = Field(description="小时行数")
    hourly_null: int = Field(description="小时降水为 NULL 的行数")
    hourly_null_pct: float = Field(description="缺测率（%）")
    hourly_observed_rows: int = Field(description="实况行数")
    hourly_forecast_rows: int = Field(description="预报行数")
    observed_start: str | None = Field(default=None, description="实况起始时刻")
    observed_end: str | None = Field(default=None, description="实况结束时刻")
    distinct_hours: int = Field(description="实况覆盖的整点数")
    expected_hours: int = Field(description="理论应覆盖的整点数")
    missing_hours: int = Field(description="缺失整点数")
    coverage_pct: float = Field(description="时间覆盖率（%）")
    daily_rows: int = Field(description="日汇总行数")
    daily_with_detail: int = Field(description="有小时明细的日行数")
    daily_without_detail: int = Field(description="无小时明细的日行数（历史回填）")
    collect_total: int = Field(description="采集总次数")
    collect_success: int = Field(description="成功次数")
    collect_failed: int = Field(description="失败次数")
    last_collect_at: str | None = Field(default=None, description="最近一次采集时间")


class CollectResult(BaseModel):
    """手动采集的返回结果。"""

    status: str = Field(description="success / failed")
    points: int = Field(description="点位数")
    rows_written: int = Field(description="写入行数")
    rows_inserted: int = Field(description="新增行数")
    elapsed_seconds: float = Field(description="耗时（秒）")
    message: str | None = Field(default=None, description="附加信息")


# ---------------------------------------------------------------- 点位下钻详情

class DetailHourly(BaseModel):
    """下钻抽屉中的逐小时点。"""

    time: str = Field(description="时刻")
    value: float = Field(description="降水量（mm）")


class DetailDaily(BaseModel):
    """下钻抽屉中的逐日点。"""

    time: str = Field(description="日期")
    value: float = Field(description="日累计（mm）")
    max: float | None = Field(default=None, description="当日最大小时雨强（mm/h）")
    level: str | None = Field(default=None, description="降水等级")


class RegionSummary(BaseModel):
    """下钻抽屉的汇总指标。"""

    latest_time: str | None = Field(default=None, description="最新实况时刻")
    latest_value: float | None = Field(default=None, description="最新小时降水量")
    sum_hours: float = Field(description="近 N 小时累计（mm）")
    peak_hour_value: float | None = Field(default=None, description="窗口内最大小时雨强")
    peak_hour_time: str | None = Field(default=None, description="该小时出现时刻")
    sum_days: float = Field(description="近 N 天累计（mm）")
    rain_days: int = Field(description="近 N 天有雨日数")
    peak_day_value: float | None = Field(default=None, description="窗口内最大日累计")
    peak_day_date: str | None = Field(default=None, description="该日日期")
    first_time: str | None = Field(default=None, description="该点位最早数据时刻")
    total_records: int = Field(description="该点位实况小时记录总数")
    historic_max: float | None = Field(default=None, description="历史最大日累计（mm）")
    historic_max_date: str | None = Field(default=None, description="历史最大日累计日期")


class RegionDetail(BaseModel):
    """单个点位的完整档案（下钻抽屉一次取全）。"""

    region: RegionOut = Field(description="行政区划基本信息")
    hours: int = Field(description="逐小时窗口长度")
    days: int = Field(description="逐日窗口长度")
    hourly: list[DetailHourly] = Field(description="近 N 小时逐小时降水")
    daily: list[DetailDaily] = Field(description="近 N 天逐日降水")
    levels: list[LevelCount] = Field(description="该点位历史降水等级分布")
    extremes: list[ExtremeEvent] = Field(description="该点位历史极值榜")
    summary: RegionSummary = Field(description="汇总指标")


# ---------------------------------------------------------------- 自动摘要素材

class HighlightPoint(BaseModel):
    """摘要里引用的单个点位。"""

    adcode: str | None = Field(default=None, description="行政区划代码")
    name: str | None = Field(default=None, description="点位名称")
    value: float = Field(description="数值（mm 或 mm/h）")
    time: str | None = Field(default=None, description="出现时刻")
    max_hourly: float | None = Field(default=None, description="当日最大小时雨强")
    level: str | None = Field(default=None, description="降水等级")


class HighlightCurrent(BaseModel):
    """当前窗口的态势。"""

    total_mm: float = Field(description="窗口内全区累计（mm）")
    wet_points: int = Field(description="窗口内下过雨的点位数")
    points_total: int = Field(description="点位总数")
    dry: bool = Field(description="窗口内全区是否无降水")
    peak: HighlightPoint | None = Field(default=None, description="窗口内最强单小时")
    wettest: HighlightPoint | None = Field(default=None, description="窗口内累计最多的点位")


class HighlightPrevious(BaseModel):
    """上一个同长度窗口，用于对比。"""

    total_mm: float = Field(description="前一窗口全区累计（mm）")
    change_pct: float | None = Field(
        default=None, description="相对变化百分比；前值为 0 时为 null"
    )


class HighlightStrongestDay(BaseModel):
    """近 N 天里最强的一天。"""

    date: str = Field(description="日期")
    total_mm: float = Field(description="当日全区合计（mm）")
    peak: HighlightPoint | None = Field(default=None, description="当日最强点位")


class OverviewHighlights(BaseModel):
    """总览页「自动摘要」素材 —— 结构化事实，句子由前端组织。"""

    latest_obs_time: str | None = Field(default=None, description="最新实况时刻")
    hours: int = Field(description="当前窗口长度（小时）")
    window_days: int = Field(description="历史窗口长度（天）")
    points_total: int = Field(description="点位总数")
    current: HighlightCurrent | None = Field(default=None, description="当前窗口态势")
    previous: HighlightPrevious | None = Field(default=None, description="前一窗口对比")
    strongest_day: HighlightStrongestDay | None = Field(
        default=None, description="窗口内最强一天"
    )
    rain_days: int = Field(description="窗口内有降水的天数")
