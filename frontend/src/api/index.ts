import { http } from './client'
import type {
  AlertItem,
  AnomalyPoint,
  BoxplotItem,
  CollectLog,
  CollectResult,
  DailySeries,
  ExtremeEvent,
  GeoJSONFeatureCollection,
  LevelCount,
  MapFrame,
  MetaInfo,
  MonthlySeries,
  MultiSeries,
  OverviewSummary,
  QualityReport,
  RankingItem,
  RealtimeLatest,
  Region,
  RegionDetail,
  Timeseries,
} from '@/types'

/** 查询参数类型：值为 undefined 的键会被自动剔除。 */
type Params = Record<string, string | number | undefined | null>

function clean(params?: Params): Params | undefined {
  if (!params) return undefined
  const out: Params = {}
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') out[k] = v
  }
  return Object.keys(out).length ? out : undefined
}

const get = async <T>(url: string, params?: Params): Promise<T> => {
  const { data } = await http.get<T>(url, { params: clean(params) })
  return data
}

/* ---------------------------------------------------------------- 系统 */
export const fetchMeta = () => get<MetaInfo>('/meta')

/* ------------------------------------------------------------ 行政区划 */
export const fetchRegions = () => get<Region[]>('/regions')
export const fetchGeoJSON = () => get<GeoJSONFeatureCollection>('/regions/geojson')
/** 单点位详情（下钻抽屉）：一次取回逐小时 + 逐日 + 等级 + 极值 + 汇总 */
export const fetchRegionDetail = (adcode: string, params?: { hours?: number; days?: number }) =>
  get<RegionDetail>(`/regions/${adcode}/detail`, params)

/* ---------------------------------------------------------------- 总览 */
export const fetchSummary = () => get<OverviewSummary>('/overview/summary')
export const fetchRanking = (params?: { limit?: number; hours?: number }) =>
  get<RankingItem[]>('/overview/ranking', params)

/* ------------------------------------------------------------ 实时监测 */
export const fetchRealtimeLatest = () => get<RealtimeLatest>('/realtime/latest')
export const fetchTimeseries = (params?: { adcode?: string; hours?: number }) =>
  get<Timeseries>('/realtime/timeseries', params)

/* ------------------------------------------------------------ 空间分布 */
export const fetchSpatialMap = (params?: { time?: string }) =>
  get<{ time: string | null; points: RealtimeLatest['points'] }>('/spatial/map', params)
export const fetchTimespan = (params: { start: string; end: string; max_frames?: number }) =>
  get<MapFrame[]>('/spatial/timespan', params)

/* ------------------------------------------------------------ 时间分析 */
export const fetchTrendDaily = (params?: { adcode?: string; start?: string; end?: string }) =>
  get<DailySeries>('/trend/daily', params)
export const fetchTrendMonthly = (params: { adcode?: string; year: number }) =>
  get<MonthlySeries>('/trend/monthly', params)
export const fetchTrendAnomaly = (params?: { adcode?: string; year?: number }) =>
  get<AnomalyPoint[]>('/trend/anomaly', params)
export const fetchLevelDistribution = (params?: { adcode?: string; start?: string; end?: string }) =>
  get<LevelCount[]>('/trend/level-distribution', params)
export const fetchExtremes = (params?: {
  adcode?: string
  start?: string
  end?: string
  min_mm?: number
  limit?: number
}) => get<ExtremeEvent[]>('/trend/extremes', params)

/* ------------------------------------------------------------ 城市对比 */
export const fetchCompareRanking = (params?: { start?: string; end?: string; limit?: number }) =>
  get<RankingItem[]>('/compare/ranking', params)
export const fetchCompareMulti = (params: { adcodes: string; start?: string; end?: string }) =>
  get<MultiSeries>('/compare/multi', params)
export const fetchCompareBoxplot = (params?: { start?: string; end?: string; limit?: number }) =>
  get<BoxplotItem[]>('/compare/boxplot', params)

/* ------------------------------------------------------------ 预警统计 */
export const fetchAlerts = (params?: { limit?: number }) => get<AlertItem[]>('/alerts', params)

/* ------------------------------------------------------------ 数据管理 */
export const fetchCollectLogs = (params?: { limit?: number }) =>
  get<CollectLog[]>('/admin/collect-logs', params)
export const fetchQuality = () => get<QualityReport>('/admin/quality')
export const triggerCollect = async (pastDays = 3): Promise<CollectResult> => {
  const { data } = await http.post<CollectResult>('/admin/collect-now', null, {
    params: { past_days: pastDays },
    timeout: 180000,
  })
  return data
}

/** CSV 导出直链（交给浏览器下载，避免前端拼大字符串）。 */
export function exportCsvUrl(params: {
  kind?: 'daily' | 'hourly'
  adcode?: string
  start?: string
  end?: string
}): string {
  const base = import.meta.env.VITE_API_BASE || '/api'
  const query = new URLSearchParams()
  if (params.kind) query.set('kind', params.kind)
  if (params.adcode) query.set('adcode', params.adcode)
  if (params.start) query.set('start', params.start)
  if (params.end) query.set('end', params.end)
  return `${base}/export/csv?${query.toString()}`
}
