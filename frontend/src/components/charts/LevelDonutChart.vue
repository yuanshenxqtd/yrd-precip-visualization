<script setup lang="ts">
/**
 * 降水等级分布环形图（GB/T 28592-2012）。
 *
 * **单位必须由调用方指定，不要用默认的"天"。**
 * 原因：`/api/trend/level-distribution` 返回的 count 是**日汇总行数**，
 * 而一行 = 一个点位的一天。全区（56 个点位）时它是"点位·天"，
 * 单点位时才是真正的"天"。
 * 曾经这里硬编码成"天"，导致 3 年的数据被读成"三万多天"——
 * 数据没错，是标注错了，而错的标注比缺标注更糟。
 */
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
    /**
     * 计数单位。
     * · 多点位（全区）：'点位·天'
     * · 单个点位：'天'
     */
    unit?: string
  }>(),
  { height: '260px', unit: '点位·天' },
)

const total = computed(() => props.items.reduce((sum, i) => sum + i.count, 0))

/** 多点位合计时额外解释口径，避免"3 年却有 3 万多天"的误读 */
const isMultiPoint = computed(() => props.unit.includes('点位'))

const caption = computed(() => {
  const value = total.value.toLocaleString('zh-CN')
  return isMultiPoint.value
    ? `共 ${value} ${props.unit}（1 个点位 1 天 = 1 ${props.unit}）`
    : `共 ${value} ${props.unit}`
})

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'item',
    formatter: (raw: unknown) => {
      const p = raw as { name?: string; value?: number; percent?: number }
      const value = (p.value ?? 0).toLocaleString('zh-CN')
      return `${p.name ?? ''}<br/><b style="font-size:14px">${value}</b> ${props.unit}　${p.percent ?? 0}%`
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
    <p v-if="total" class="donut__caption">{{ caption }}</p>
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

.donut__caption {
  margin-top: 2px;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-2);
  text-align: center;
}
</style>
