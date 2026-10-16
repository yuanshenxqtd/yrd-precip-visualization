/**
 * 降水等级与配色 —— 前端唯一权威定义。
 *
 * 必须与以下两处保持一致：
 *   - 后端 backend/app/levels.py 的 LEVEL_COLORS（GB/T 28592-2012 分级）
 *   - 样式变量 frontend/src/styles/tokens.css 的 --rain-* 变量
 *
 * ECharts 绘制在 canvas 上，无法使用 CSS 变量，因此这里用十六进制字面量。
 */

export const RAIN_COLORS = {
  none: '#2b3a55',
  light: '#7fd0f5',
  moderate: '#3aa0e0',
  heavy: '#f5d76e',
  storm: '#f39c12',
  downpour: '#e74c3c',
  extreme: '#8e1b1b',
} as const

/** 无数据（该点位当期不在结果集中）*/
export const NO_DATA_COLOR = 'rgba(43, 58, 85, 0.35)'

export interface RainPiece {
  name: string
  color: string
  gte?: number
  gt?: number
  lt?: number
  lte?: number
  value?: number
}

/** visualMap 分段（按降水强度从高到低，ECharts 要求分段互斥） */
export const RAIN_PIECES: RainPiece[] = [
  { name: '特大暴雨', gte: 250, color: RAIN_COLORS.extreme },
  { name: '大暴雨', gte: 100, lt: 250, color: RAIN_COLORS.downpour },
  { name: '暴雨', gte: 50, lt: 100, color: RAIN_COLORS.storm },
  { name: '大雨', gte: 25, lt: 50, color: RAIN_COLORS.heavy },
  { name: '中雨', gte: 10, lt: 25, color: RAIN_COLORS.moderate },
  { name: '小雨', gt: 0, lt: 10, color: RAIN_COLORS.light },
  { name: '无降水', value: 0, color: RAIN_COLORS.none },
]

/** 按 24 小时口径判定等级（与后端 classify(mm, hours=24) 一致） */
export function classifyMm(mm: number | null | undefined): string {
  if (mm === null || mm === undefined || mm < 0.1) return '无降水'
  if (mm >= 250) return '特大暴雨'
  if (mm >= 100) return '大暴雨'
  if (mm >= 50) return '暴雨'
  if (mm >= 25) return '大雨'
  if (mm >= 10) return '中雨'
  return '小雨'
}

export function colorOf(level: string | null | undefined): string {
  switch (level) {
    case '特大暴雨':
      return RAIN_COLORS.extreme
    case '大暴雨':
      return RAIN_COLORS.downpour
    case '暴雨':
      return RAIN_COLORS.storm
    case '大雨':
      return RAIN_COLORS.heavy
    case '中雨':
      return RAIN_COLORS.moderate
    case '小雨':
      return RAIN_COLORS.light
    default:
      return RAIN_COLORS.none
  }
}

/** 供图表图例使用：只保留本项目实际出现过的等级 */
export const LEVEL_ORDER = ['无降水', '小雨', '中雨', '大雨', '暴雨', '大暴雨', '特大暴雨'] as const

/* ------------------------------------------------------------------ 连续色阶 */

/**
 * 连续强度色阶（冷 → 暖）。
 *
 * ⚠️ 与上面的国标分级**不是一回事**：GB/T 28592-2012 只定义 12/24 小时口径，
 * 没有小时尺度的等级。小时矩阵/强度图需要的是"相对强弱"的视觉表达，
 * 因此这里用相对当前最大值的线性映射，**不宣称任何标准**，
 * 拼图上同时显示真实数值以免误读。
 */
const COLOR_STOPS: [number, [number, number, number]][] = [
  [0.0, [43, 58, 85]], // 深蓝灰（无/弱）
  [0.22, [58, 130, 200]], // 蓝
  [0.46, [127, 208, 245]], // 浅蓝
  [0.7, [245, 215, 110]], // 黄
  [0.86, [243, 156, 18]], // 橙
  [1.0, [231, 76, 60]], // 红
]

export function intensityColor(value: number | null | undefined, max: number): string {
  if (value === null || value === undefined || value <= 0 || max <= 0) return RAIN_COLORS.none
  const t = Math.min(Math.max(value / max, 0), 1)

  for (let i = 0; i < COLOR_STOPS.length - 1; i += 1) {
    const [t0, c0] = COLOR_STOPS[i]
    const [t1, c1] = COLOR_STOPS[i + 1]
    if (t >= t0 && t <= t1) {
      const k = t1 === t0 ? 0 : (t - t0) / (t1 - t0)
      const mix = c0.map((c, idx) => Math.round(c + (c1[idx] - c) * k))
      return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
    }
  }
  const last = COLOR_STOPS[COLOR_STOPS.length - 1][1]
  return `rgb(${last[0]}, ${last[1]}, ${last[2]})`
}
