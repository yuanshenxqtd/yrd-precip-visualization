/** ECharts 通用主题常量：让所有图表视觉统一。 */

export const FONT_FAMILY =
  "'Inter', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif"

export const TEXT_PRIMARY = '#eaf2ff'
export const TEXT_SECONDARY = '#a8bcd8'
export const TEXT_MUTED = '#6c80a6'
export const ACCENT = '#3aa0e0'
export const ACCENT_LIGHT = '#7fd0f5'
export const SPLIT_LINE = 'rgba(120, 170, 255, 0.12)'
export const AXIS_LINE = 'rgba(120, 170, 255, 0.2)'

/** 统一的 tooltip 样式（深色玻璃面板） */
export const tooltipStyle = {
  backgroundColor: 'rgba(9, 17, 34, 0.94)',
  borderColor: 'rgba(120, 170, 255, 0.28)',
  borderWidth: 1,
  padding: [8, 12] as [number, number],
  textStyle: { color: TEXT_PRIMARY, fontSize: 12, fontFamily: FONT_FAMILY },
  extraCssText: 'border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.4);',
}

/** 统一的坐标轴样式 */
export const axisStyle = {
  axisLine: { lineStyle: { color: AXIS_LINE } },
  axisTick: { show: false },
  axisLabel: { color: TEXT_MUTED, fontSize: 11, fontFamily: FONT_FAMILY },
  splitLine: { lineStyle: { color: SPLIT_LINE, type: 'dashed' as const } },
}

/** 数值坐标轴标签（带单位更易读） */
export function valueAxis(name: string) {
  return {
    type: 'value' as const,
    name,
    nameTextStyle: { color: TEXT_MUTED, fontSize: 11, padding: [0, 0, 0, 4] },
    nameGap: 12,
    ...axisStyle,
  }
}

export function categoryAxis(data: string[], rotate = 0) {
  return {
    type: 'category' as const,
    data,
    boundaryGap: true,
    ...axisStyle,
    splitLine: { show: false },
    axisLabel: { ...axisStyle.axisLabel, rotate, hideOverlap: true },
  }
}

/** 柱状图的渐变填充 */
export function barGradient(from = ACCENT, to = ACCENT_LIGHT) {
  return {
    type: 'linear' as const,
    x: 0,
    y: 1,
    x2: 0,
    y2: 0,
    colorStops: [
      { offset: 0, color: `${from}55` },
      { offset: 1, color: to },
    ],
  }
}
