<script setup lang="ts">
/** 月累计降水柱状图。 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { barGradient, tooltipStyle, valueAxis } from '@/utils/chartTheme'
import type { TrendPoint } from '@/types'

const props = withDefaults(
  defineProps<{
    points: TrendPoint[]
    height?: string
  }>(),
  { height: '260px' },
)

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'axis',
    axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120,170,255,.08)' } },
    formatter: (raw: unknown) => {
      const list = (Array.isArray(raw) ? raw : [raw]) as { axisValue?: string; data?: number }[]
      const p = list[0]
      if (!p) return ''
      return `${p.axisValue}<br/><b style="font-size:14px">${p.data ?? 0}</b> mm`
    },
  },
  grid: { left: 52, right: 16, top: 18, bottom: 28 },
  xAxis: {
    type: 'category',
    data: props.points.map((p) => p.time),
    axisLine: { lineStyle: { color: 'rgba(120,170,255,.2)' } },
    axisTick: { show: false },
    axisLabel: {
      color: '#6c80a6',
      fontSize: 11,
      formatter: (v: string) => `${Number(v.slice(5, 7))}月`,
    },
    splitLine: { show: false },
  },
  yAxis: valueAxis('mm'),
  series: [
    {
      type: 'bar',
      data: props.points.map((p) => p.value),
      barMaxWidth: 34,
      itemStyle: { color: barGradient(), borderRadius: [4, 4, 0, 0] },
      label: {
        show: true,
        position: 'top',
        color: '#a8bcd8',
        fontSize: 10,
        formatter: (raw: unknown) => {
          const value = (raw as { data?: number }).data
          return value && value > 0 ? String(value) : ''
        },
      },
    },
  ],
}))
</script>

<template>
  <BaseChart v-if="points.length" :option="option" :height="height" />
  <p v-else class="chart-empty">该年份无月数据</p>
</template>

<style scoped>
.chart-empty {
  display: grid;
  place-items: center;
  min-height: 200px;
  font-size: 13px;
  color: var(--text-2);
}
</style>
