/** 与后端 backend/app/schemas.py 一一对应的类型定义。 */

export interface MetaInfo {
  data_source: string
  points_total: number
  regions_total: number
  hourly_rows: number
  daily_rows: number
  hourly_start: string | null
  /** 含预报，可能落在未来 —— 不能用来判断数据时效 */
  hourly_end: string | null
  observed_start: string | null
  /** 实况数据最新时刻 —— 判断数据时效只用这个字段 */
  observed_end: string | null
  forecast_end: string | null
  /** 服务器当前时间，用于抵消客户端时钟偏差 */
  server_now: string
  daily_start: string | null
  daily_end: string | null
  last_collect_at: string | null
  last_collect_status: string | null
  db_initialized_at: string | null
  collect_interval_minutes: number
}

export interface Region {
  adcode: string
  name: string
  level: 'province' | 'city' | 'district'
  parent_adcode: string | null
  province: string
  lon: number
  lat: number
  is_monitored: number
}

export interface TrendPoint {
  time: string
  value: number
}

export interface DailyPoint {
  time: string
  value: number
  max: number
}

export interface RankingItem {
  adcode: string
  name: string
  province: string
  total: number
  peak: number | null
}

export interface MapPoint {
  adcode: string
  name: string
  province: string
  lon: number
  lat: number
  value: number | null
  level: string | null
  color: string | null
}

export interface MapFrame {
  time: string
  values: Record<string, number | null>
}

export interface OverviewSummary {
  latest_obs_time: string | null
  points_total: number
  points_with_rain: number
  rain_coverage_pct: number
  sum_24h_mm: number
  max_hourly_mm: number | null
  max_hourly_point: string | null
  max_hourly_time: string | null
  wettest_point: string | null
  wettest_24h_mm: number
  today_wettest_point: string | null
  today_wettest_mm: number
  last_collect_at: string | null
  last_collect_status: string | null
  forecast_hours: number
}

export interface LevelCount {
  rain_level: string
  count: number
  color: string | null
}

/** 极端降水事件（单日单点） */
export interface ExtremeEvent {
  adcode: string
  name: string
  province: string
  obs_date: string
  precip_sum: number
  precip_max_hourly: number | null
  rain_hours: number | null
  rain_level: string | null
  color: string | null
}

export interface AnomalyPoint {
  month: string
  actual: number
  baseline: number
  anomaly_pct: number | null
}

export interface BoxplotItem {
  adcode: string
  name: string
  province: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
  mean: number
}

export interface CollectLog {
  id: number
  source: string
  mode: string
  status: string
  points_total: number
  rows_upserted: number
  gap_filled_hours: number
  started_at: string
  finished_at: string | null
  error_msg: string | null
}

export interface QualityReport {
  hourly_rows: number
  hourly_null: number
  hourly_null_pct: number
  hourly_observed_rows: number
  hourly_forecast_rows: number
  observed_start: string | null
  observed_end: string | null
  distinct_hours: number
  expected_hours: number
  missing_hours: number
  coverage_pct: number
  daily_rows: number
  daily_with_detail: number
  daily_without_detail: number
  collect_total: number
  collect_success: number
  collect_failed: number
  last_collect_at: string | null
}

export interface CollectResult {
  status: string
  points: number
  rows_written: number
  rows_inserted: number
  elapsed_seconds: number
  message: string | null
}

export interface DailyValue {
  adcode: string
  value: number
  level: string | null
}

export interface RealtimeLatest {
  time: string | null
  points: MapPoint[]
  daily: DailyValue[]
}

export interface Timeseries {
  adcode: string | null
  start: string | null
  end: string | null
  points: TrendPoint[]
}

export interface DailySeries {
  adcode: string | null
  start: string
  end: string
  points: DailyPoint[]
}

export interface MonthlySeries {
  adcode: string | null
  year: number
  points: TrendPoint[]
}

export interface MultiSeries {
  start: string
  end: string
  series: { adcode: string; name: string; points: TrendPoint[] }[]
}

export interface AlertItem {
  id: number
  region_adcode: string
  alert_type: string
  alert_level: string | null
  title: string | null
  published_at: string | null
  source: string | null
}

/** GeoJSON 结构（要素属性由 DataV GeoAtlas 提供，前端按需读取） */
export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection'
  name?: string
  features: {
    type: 'Feature'
    properties: Record<string, unknown>
    geometry: unknown
  }[]
}

/* ---------------------------------------------------------------- 点位下钻详情 */

export interface DetailHourly {
  time: string
  value: number
}

export interface DetailDaily {
  time: string
  value: number
  max: number | null
  level: string | null
}

export interface RegionSummary {
  latest_time: string | null
  latest_value: number | null
  sum_hours: number
  peak_hour_value: number | null
  peak_hour_time: string | null
  sum_days: number
  rain_days: number
  peak_day_value: number | null
  peak_day_date: string | null
  first_time: string | null
  total_records: number
  historic_max: number | null
  historic_max_date: string | null
}

/** 单点位完整档案（下钻抽屉一次取全） */
export interface RegionDetail {
  region: Region
  hours: number
  days: number
  hourly: DetailHourly[]
  daily: DetailDaily[]
  levels: LevelCount[]
  extremes: ExtremeEvent[]
  summary: RegionSummary
}

/* ---------------------------------------------------------------- 自动摘要素材 */

export interface HighlightPoint {
  adcode: string | null
  name: string | null
  value: number
  time: string | null
  max_hourly: number | null
  level: string | null
}

export interface HighlightCurrent {
  total_mm: number
  wet_points: number
  points_total: number
  dry: boolean
  peak: HighlightPoint | null
  wettest: HighlightPoint | null
}

export interface HighlightPrevious {
  total_mm: number
  change_pct: number | null
}

export interface HighlightStrongestDay {
  date: string
  total_mm: number
  peak: HighlightPoint | null
}

/** 总览页「读图要点」素材：结构化事实，句子由前端组织 */
export interface OverviewHighlights {
  latest_obs_time: string | null
  hours: number
  window_days: number
  points_total: number
  current: HighlightCurrent | null
  previous: HighlightPrevious | null
  strongest_day: HighlightStrongestDay | null
  rain_days: number
}

/* ---------------------------------------------------------------- 空间插值降水场 */

/** IDW 插值得到的连续降水场（一维 row-major 网格） */
export interface FieldGrid {
  obs_time: string
  lon_min: number
  lon_max: number
  lat_min: number
  lat_max: number
  step: number
  cols: number
  rows: number
  max_value: number
  point_count: number
  /** index = row * cols + col；lon = lon_min + col*step，lat = lat_min + row*step */
  values: number[]
}