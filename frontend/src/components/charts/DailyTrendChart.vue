<script setup lang="ts">
/** 日降水趋势：柱为日累计，线为当日最大单点值（仅在全区口径下有意义）。 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { ACCENT, ACCENT_LIGHT, SPLIT_LINE, TEXT_MUTED, barGradient, tooltipStyle } from '@/utils/chartTheme'
import type { DailyPoint } from '@/types'

const props = withDefaults(
  defineProps<{
    points: DailyPoint[]
    showMax?: boolean
    height?: string
  }>(),
  { showMax: false, height: '280px' },
)

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'axis',
    axisPointer: { type: 'line', lineStyle: { color: 'rgba(120,170,255,.35)' } },
    formatter: (raw: unknown) => {
      const list = (Array.isArray(raw) ? raw : [raw]) as {
        axisValue?: string
        seriesName?: string
        data?: number
      }[]
      if (!list.length) return ''
      const head = (list[0].axisValue ?? '').replace('T', ' ')
      const lines = list.map(
        (item) => `${item.seriesName}：<b>${item.data ?? 0}</b> mm`,
      )
      return `${head}<br/>${lines.join('<br/>')}`
    },
  },
  legend: props.showMax
    ? {
        top: 0,
        right: 0,
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { color: TEXT_MUTED, fontSize: 11 },
        data: ['日累计', '当日最大点位'],
      }
    : undefined,
  grid: { left: 46, right: 16, top: props.showMax ? 28 : 16, bottom: 30 },
  xAxis: {
    type: 'category',
    data: props.points.map((p) => p.time),
    boundaryGap: true,
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
  series: [
    {
      name: '日累计',
      type: 'bar',
      data: props.points.map((p) => p.value),
      barMaxWidth: 18,
      itemStyle: { color: barGradient(), borderRadius: [3, 3, 0, 0] },
    },
    ...(props.showMax
      ? [
          {
            name: '当日最大点位',
            type: 'line' as const,
            smooth: true,
            symbol: 'circle',
            symbolSize: 5,
            data: props.points.map((p) => p.max),
            lineStyle: { color: '#f5d76e', width: 1.8 },
            itemStyle: { color: '#f5d76e' },
          },
        ]
      : []),
  ],
  color: [ACCENT, ACCENT_LIGHT],
}))
</script>

<template>
  <BaseChart v-if="points.length" :option="option" :height="height" />
  <p v-else class="chart-empty">该时间段无日数据</p>
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
