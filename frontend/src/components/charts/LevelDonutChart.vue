<script setup lang="ts">
/** 降水等级分布环形图（GB/T 28592-2012）。 */
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { FONT_FAMILY, TEXT_PRIMARY, TEXT_SECONDARY, tooltipStyle } from '@/utils/chartTheme'
import { colorOf } from '@/utils/rainLevels'
import type { LevelCount } from '@/types'

const props = withDefaults(
  defineProps<{
    items: LevelCount[]
    height?: string
  }>(),
  { height: '260px' },
)

const total = computed(() => props.items.reduce((sum, i) => sum + i.count, 0))

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'item',
    formatter: (raw: unknown) => {
      const p = raw as { name?: string; value?: number; percent?: number }
      const value = (p.value ?? 0).toLocaleString('zh-CN')
      return `${p.name ?? ''}<br/><b style="font-size:14px">${value}</b> 天　${p.percent ?? 0}%`
    },
  },
  legend: {
    orient: 'vertical',
    right: 6,
    top: 'center',
    itemWidth: 10,
    itemHeight: 10,
    itemGap: 8,
    icon: 'roundRect',
    textStyle: { color: TEXT_SECONDARY, fontSize: 12, fontFamily: FONT_FAMILY },
  },
  series: [
    {
      type: 'pie',
      radius: ['50%', '76%'],
      center: ['34%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#0b1428', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 6,
        label: {
          show: true,
          position: 'center',
          formatter: (raw: unknown) => (raw as { name?: string }).name ?? '',
          color: TEXT_PRIMARY,
          fontSize: 13,
          fontWeight: 600,
          fontFamily: FONT_FAMILY,
        },
      },
      data: props.items.map((item) => ({
        name: item.rain_level,
        value: item.count,
        itemStyle: { color: item.color ?? colorOf(item.rain_level) },
      })),
    },
  ],
}))
</script>

<template>
  <div class="donut">
    <BaseChart v-if="total" :option="option" :height="height" />
    <p v-else class="chart-empty">暂无等级分布数据</p>
  </div>
</template>

<style scoped>
.donut {
  position: relative;
}

.chart-empty {
  display: grid;
  place-items: center;
  min-height: 220px;
  font-size: 13px;
  color: var(--text-2);
}
</style>
