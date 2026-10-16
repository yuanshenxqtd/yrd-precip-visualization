<script setup lang="ts">
/**
 * 箱线图：展示各城市日降水量的五数概括（min / q1 / 中位数 / q3 / max）。
 * 与排行图配合，可从「总量」与「离散程度」两个角度看城市差异。
 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { SPLIT_LINE, TEXT_MUTED, tooltipStyle } from '@/utils/chartTheme'
import type { BoxplotItem } from '@/types'

const props = withDefaults(
  defineProps<{
    items: BoxplotItem[]
    height?: string
  }>(),
  { height: '340px' },
)

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'item',
    formatter: (raw: unknown) => {
      const p = raw as { name?: string; data?: number[]; seriesType?: string }
      if (!p?.data || p.seriesType === 'scatter') return ''
      const [min, q1, median, q3, max] = p.data
      return [
        `<b>${p.name}</b>`,
        `最大　${max} mm`,
        `上四分位　${q3} mm`,
        `中位数　<b>${median}</b> mm`,
        `下四分位　${q1} mm`,
        `最小　${min} mm`,
      ].join('<br/>')
    },
  },
  grid: { left: 52, right: 18, top: 20, bottom: 46 },
  xAxis: {
    type: 'category',
    data: props.items.map((i) => i.name),
    axisLine: { lineStyle: { color: 'rgba(120,170,255,.2)' } },
    axisTick: { show: false },
    axisLabel: { color: TEXT_MUTED, fontSize: 11, rotate: 28, hideOverlap: true },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    name: '日降水 mm',
    nameTextStyle: { color: TEXT_MUTED, fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: TEXT_MUTED, fontSize: 11 },
    splitLine: { lineStyle: { color: SPLIT_LINE, type: 'dashed' } },
  },
  series: [
    {
      name: '日降水分布',
      type: 'boxplot',
      data: props.items.map((i) => [i.min, i.q1, i.median, i.q3, i.max]),
      boxWidth: [10, 34],
      itemStyle: {
        color: 'rgba(58, 160, 224, 0.25)',
        borderColor: '#7fd0f5',
        borderWidth: 1.4,
      },
      emphasis: {
        itemStyle: { color: 'rgba(127, 208, 245, 0.4)', borderColor: '#9adcfb' },
      },
    },
    {
      name: '平均值',
      type: 'scatter',
      symbolSize: 7,
      data: props.items.map((i) => i.mean),
      itemStyle: { color: '#f5d76e' },
      tooltip: { show: false },
    },
  ],
}))
</script>

<template>
  <BaseChart v-if="items.length" :option="option" :height="height" />
  <p v-else class="chart-empty">该区间无数据</p>
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
