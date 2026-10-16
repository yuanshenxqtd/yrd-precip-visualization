<script setup lang="ts">
/** 横向排行条形图（按累计降水量降序）。 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { TEXT_MUTED, tooltipStyle } from '@/utils/chartTheme'
import type { RankingItem } from '@/types'

const props = withDefaults(
  defineProps<{
    items: RankingItem[]
    height?: string
    unit?: string
  }>(),
  { height: '360px', unit: 'mm' },
)

/** ECharts 的类目轴自下而上排布，反转后让第一名显示在最上方 */
const ordered = computed(() => [...props.items].reverse())

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'axis',
    axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(120,170,255,.08)' } },
    formatter: (raw: unknown) => {
      const list = (Array.isArray(raw) ? raw : [raw]) as { name?: string; data?: number }[]
      const p = list[0]
      if (!p) return ''
      const item = props.items.find((i) => i.name === p.name)
      return [
        `<b>${p.name}</b>${item ? `　${item.province}` : ''}`,
        `累计：<b>${p.data ?? 0}</b> ${props.unit}`,
        item?.peak != null ? `最大小时：${item.peak} mm/h` : '',
      ]
        .filter(Boolean)
        .join('<br/>')
    },
  },
  grid: { left: 8, right: 56, top: 10, bottom: 24, containLabel: true },
  xAxis: {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: TEXT_MUTED, fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(120,170,255,.1)', type: 'dashed' } },
  },
  yAxis: {
    type: 'category',
    data: ordered.value.map((i) => i.name),
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#a8bcd8', fontSize: 12 },
  },
  series: [
    {
      type: 'bar',
      data: ordered.value.map((i) => i.total),
      barMaxWidth: 16,
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 1,
          y2: 0,
          colorStops: [
            { offset: 0, color: 'rgba(58, 160, 224, 0.35)' },
            { offset: 1, color: '#7fd0f5' },
          ],
        },
      },
      label: {
        show: true,
        position: 'right',
        color: '#eaf2ff',
        fontSize: 11,
        formatter: (raw: unknown) => String((raw as { data?: number }).data ?? 0),
      },
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
