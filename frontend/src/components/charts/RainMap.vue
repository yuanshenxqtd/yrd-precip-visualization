<script setup lang="ts">
/**
 * 长三角降水分级设色地图。
 *
 * 组件只负责渲染：接收按行政区划名称对齐好的数据，
 * 名称必须与 GeoJSON 要素的 properties.name 一致（ECharts 按 name 匹配）。
 *
 * ⚠️ 地图注册必须早于图表初始化。
 * Vue 中「子组件的 mounted 先于父组件执行」，若把 ensureYrdMap() 放在父组件的
 * onMounted 里，BaseChart 初始化时地图还没注册，ECharts 会在
 * MapSeries.getInitialData 里抛 "Cannot read properties of undefined (reading 'regions')"。
 * 因此这里由组件自身保证：注册完成前不渲染图表。
 */
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/common/BaseChart.vue'
import { YRD_MAP_NAME, ensureYrdMap, isYrdMapReady } from '@/composables/useYrdMap'
import { describeError } from '@/api/client'
import { ACCENT_LIGHT, FONT_FAMILY, TEXT_PRIMARY, TEXT_SECONDARY, tooltipStyle } from '@/utils/chartTheme'
import { NO_DATA_COLOR, RAIN_PIECES, classifyMm } from '@/utils/rainLevels'

const readyMap = ref(isYrdMapReady())
const mapError = ref<string | null>(null)

onMounted(async () => {
  if (readyMap.value) return
  try {
    await ensureYrdMap()
    readyMap.value = true
  } catch (err) {
    mapError.value = describeError(err)
  }
})

const props = withDefaults(
  defineProps<{
    /** adcode 可选：带上它以后，点击区划就能直接下钻到该点位详情 */
    data: { name: string; value: number; adcode?: string }[]
    height?: string
    unit?: string
  }>(),
  { height: '460px', unit: 'mm' },
)

const emit = defineEmits<{ select: [string] }>()

function onChartClick(raw: unknown): void {
  const params = raw as { data?: { adcode?: string } }
  const code = params.data?.adcode
  if (code) emit('select', code)
}

const option = computed<EChartsOption>(() => ({
  tooltip: {
    ...tooltipStyle,
    trigger: 'item',
    formatter: (raw: unknown) => {
      const p = raw as { name?: string; value?: number | null }
      const name = p.name ?? ''
      const value = p.value
      if (value === undefined || value === null || Number.isNaN(value)) {
        return `${name}<br/>无数据`
      }
      return `${name}<br/><b style="font-size:14px">${value}</b> ${props.unit}　${classifyMm(value)}`
    },
  },
  visualMap: {
    type: 'piecewise',
    left: 10,
    bottom: 10,
    itemWidth: 14,
    itemHeight: 10,
    itemGap: 4,
    showLabel: true,
    text: ['强', '弱'],
    textStyle: { color: TEXT_SECONDARY, fontSize: 11, fontFamily: FONT_FAMILY },
    pieces: RAIN_PIECES,
    outOfRange: { color: NO_DATA_COLOR },
  },
  series: [
    {
      type: 'map',
      map: YRD_MAP_NAME,
      roam: true,
      zoom: 1.02,
      aspectScale: 0.86,
      selectedMode: false,
      label: { show: false },
      itemStyle: {
        areaColor: NO_DATA_COLOR,
        borderColor: 'rgba(120, 170, 255, 0.34)',
        borderWidth: 0.8,
      },
      emphasis: {
        label: {
          show: true,
          color: TEXT_PRIMARY,
          fontSize: 12,
          fontFamily: FONT_FAMILY,
        },
        itemStyle: {
          borderColor: ACCENT_LIGHT,
          borderWidth: 1.6,
          shadowBlur: 14,
          shadowColor: 'rgba(58, 160, 224, 0.55)',
        },
      },
      data: props.data,
    },
  ],
}))
</script>

<template>
  <div class="rain-map">
    <BaseChart
      v-if="readyMap"
      :option="option"
      :height="height"
      class="rain-map__chart"
      @chart-click="onChartClick"
    />
    <div v-else class="rain-map__hint" :class="{ 'rain-map__hint--error': mapError }">
      {{ mapError ? `地图加载失败：${mapError}` : '正在加载长三角地图…' }}
    </div>
  </div>
</template>

<style scoped>
.rain-map {
  position: relative;
}

/* 提示可点击下钻 */
.rain-map__chart :deep(canvas) {
  cursor: pointer;
}

.rain-map__hint {
  display: grid;
  place-items: center;
  height: 452px;
  font-size: 13px;
  color: var(--text-2);
}

.rain-map__hint--error {
  color: #ff9d94;
}
</style>
