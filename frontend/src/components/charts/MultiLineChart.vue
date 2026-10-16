<script setup lang="ts">
/** 多城市降水序列对比折线图。 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { SPLIT_LINE, TEXT_MUTED, tooltipStyle } from '@/utils/chartTheme'
import type { TrendPoint } from '@/types'

interface Series {
  adcode: string
  name: string
  points: TrendPoint[]
}

const props = withDefaults(
  defineProps<{
    series: Series[]
    height?: string
  }>(),
  { height: '320px' },
)

/** 各城市日期取并集并排序，保证多序列在 x 轴上对齐 */
const dates = computed(() => {
  const set = new Set<string>()
  for (const item of props.series) {
    for (const p of item.points) set.add(p.time)
  }
  return [...set].sort()
})

const PALETTE = [
  '#7fd0f5',
  '#f5d76e',
  '#e74c3c',
  '#2ecc71',
  '#b47cf5',
  '#f39c12',
  '#3aa0e0',
  '#e67e9a',
]

const option = computed<EChartsOption>(() => ({
  color: PALETTE,
  tooltip: {
    ...tooltipStyle,
    trigger: 'axis',
    axisPointer: { type: 'line', lineStyle: { color: 'rgba(120,170,255,.35)' } },
    formatter: (raw: unknown) => {
      const list = (Array.isArray(raw) ? raw : [raw]) as {
        axisValue?: string
        seriesName?: string
        data?: number | null
      }[]
      if (!list.length) return ''
      const head = (list[0].axisValue ?? '').replace('T', ' ')
      const rows = list
        .filter((item) => item.data !== null && item.data !== undefined)
        .sort((a, b) => (b.data ?? 0) - (a.data ?? 0))
        .map((item) => `${item.seriesName}：<b>${item.data}</b> mm`)
      return [`<b>${head}</b>`, ...rows].join('<br/>')
    },
  },
  legend: {
    top: 0,
    right: 0,
    itemWidth: 12,
    itemHeight: 8,
    textStyle: { color: TEXT_MUTED, fontSize: 11 },
    type: 'scroll',
  },
  grid: { left: 50, right: 18, top: 34, bottom: 30 },
  xAxis: {
    type: 'category',
    data: dates.value,
    boundaryGap: false,
    axisLine: { lineStyle: { color: 'rgba(120,170,255,.2)' } },
    axisTick: { show: false },
    axisLabel: {
      color: TEXT_MUTED,
      fontSize: 11,
      hideOverlap: true,
      formatter: (v: string) => v.slice(5),
    },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    name: 'mm',
    nameTextStyle: { color: TEXT_MUTED, fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: TEXT_MUTED, fontSize: 11 },
    splitLine: { lineStyle: { color: SPLIT_LINE, type: 'dashed' } },
  },
  series: props.series.map((item) => {
    const byDate = new Map(item.points.map((p) => [p.time, p.value]))
    return {
      name: item.name,
      type: 'line' as const,
      smooth: true,
      showSymbol: dates.value.length <= 40,
      symbolSize: 5,
      connectNulls: false,
      data: dates.value.map((d) => byDate.get(d) ?? null),
      lineStyle: { width: 1.8 },
    }
  }),
}))
</script>

<template>
  <BaseChart v-if="series.length && dates.length" :option="option" :height="height" />
  <p v-else class="chart-empty">请至少选择一个城市</p>
</template>

<style scoped>
.chart-empty {
  display: grid;
  place-items: center;
  min-height: 220px;
  font-size: 13px;
  color: var(--text-2);
}
</style>
