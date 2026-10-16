<script setup lang="ts">
/** 逐小时降水柱状图（用于近 24 / 48 小时趋势）。 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { barGradient, categoryAxis, tooltipStyle, valueAxis } from '@/utils/chartTheme'
import type { TrendPoint } from '@/types'

const props = withDefaults(
  defineProps<{
    points: TrendPoint[]
    height?: string
    unit?: string
  }>(),
  { height: '260px', unit: 'mm' },
)

/** 'YYYY-MM-DDTHH:MM' → 'HH:MM' */
const label = (t: string) => t.slice(11, 16)

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'axis',
    axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120, 170, 255, 0.08)' } },
    formatter: (raw: unknown) => {
      const list = Array.isArray(raw) ? raw : [raw]
      const p = list[0] as { axisValue?: string; data?: number } | undefined
      if (!p) return ''
      const label = (p.axisValue ?? '').replace('T', ' ')
      return `${label}<br/><b style="font-size:14px">${p.data ?? 0}</b> ${props.unit}`
    },
  },
  grid: { left: 46, right: 14, top: 18, bottom: 26, containLabel: false },
  xAxis: {
    ...categoryAxis(props.points.map((p) => p.time)),
    axisLabel: {
      color: '#6c80a6',
      fontSize: 11,
      interval: Math.max(Math.floor(props.points.length / 8) - 1, 0),
      formatter: (v: string) => label(v),
    },
  },
  yAxis: valueAxis(props.unit),
  series: [
    {
      type: 'bar',
      name: '小时降水',
      data: props.points.map((p) => p.value),
      barMaxWidth: 16,
      itemStyle: { color: barGradient(), borderRadius: [3, 3, 0, 0] },
      emphasis: { itemStyle: { color: '#9adcfb' } },
    },
  ],
}))
</script>

<template>
  <div>
    <BaseChart v-if="points.length" :option="option" :height="height" />
    <p v-else class="chart-empty">该时段无小时数据</p>
  </div>
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
