<script setup lang="ts">
/**
 * 降水距平图：柱为相对基准的百分比，正距平偏暖色、负距平偏冷色。
 * tooltip 同时给出实际值与基准值，避免"只见百分比不见量"。
 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { SPLIT_LINE, TEXT_MUTED, tooltipStyle } from '@/utils/chartTheme'
import type { AnomalyPoint } from '@/types'

const props = withDefaults(
  defineProps<{
    items: AnomalyPoint[]
    height?: string
  }>(),
  { height: '280px' },
)

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'axis',
    axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120,170,255,.08)' } },
    formatter: (raw: unknown) => {
      const list = (Array.isArray(raw) ? raw : [raw]) as { dataIndex?: number }[]
      const index = list[0]?.dataIndex ?? 0
      const item = props.items[index]
      if (!item) return ''
      const pct = item.anomaly_pct
      const sign = pct === null ? '—' : `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`
      return [
        `<b>${item.month}</b>`,
        `距平：<b>${sign}</b>`,
        `实际：${item.actual} mm`,
        `基准：${item.baseline} mm`,
      ].join('<br/>')
    },
  },
  grid: { left: 52, right: 16, top: 20, bottom: 28 },
  xAxis: {
    type: 'category',
    data: props.items.map((i) => i.month),
    axisLine: { lineStyle: { color: 'rgba(120,170,255,.2)' } },
    axisTick: { show: false },
    axisLabel: {
      color: TEXT_MUTED,
      fontSize: 11,
      formatter: (v: string) => `${Number(v.slice(5, 7))}月`,
    },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    name: '距平 %',
    nameTextStyle: { color: TEXT_MUTED, fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: TEXT_MUTED, fontSize: 11, formatter: '{value}%' },
    splitLine: { lineStyle: { color: SPLIT_LINE, type: 'dashed' } },
  },
  series: [
    {
      type: 'bar',
      data: props.items.map((item) => ({
        value: item.anomaly_pct,
        itemStyle: {
          color:
            item.anomaly_pct === null
              ? '#47597c'
              : item.anomaly_pct >= 0
                ? 'rgba(231, 76, 60, 0.85)'
                : 'rgba(58, 160, 224, 0.85)',
          borderRadius: item.anomaly_pct !== null && item.anomaly_pct >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4],
        },
      })),
      barMaxWidth: 30,
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: 'rgba(168, 188, 216, 0.55)', width: 1 },
        data: [{ yAxis: 0 }],
        label: { show: false },
      },
    },
  ],
}))
</script>

<template>
  <div>
    <BaseChart v-if="items.length" :option="option" :height="height" />
    <p v-else class="chart-empty">该年份无距平数据</p>
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
