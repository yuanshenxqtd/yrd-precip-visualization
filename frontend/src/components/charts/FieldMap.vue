<script setup lang="ts">
/**
 * 连续降水场（IDW 空间插值）。
 *
 * 与 `RainMap.vue` 的区别：
 *   · RainMap  —— 按行政区划整体着色（业界惯例，看"哪个市下了多少"）
 *   · FieldMap —— 连续插值场（看"雨带怎么走"、识别区域内的强中心）
 *
 * 三个交互点：
 *   1. 悬停任意位置 → 显示该处**插值**降水量
 *   2. 滚轮/拖拽缩放平移地图
 *   3. 点击站点圆点 → 聚焦并打开该点位详情
 *
 * 诚实性处理：
 *   · 网格落在行政区划之外的部分按边界掩膜剔除（否则会糊到海上）
 *   · 图上保留站点圆点，让使用者看得见"插值是从哪些实况点推出来的"
 *   · 单位是 mm/h（小时雨强），国标 GB/T 28592 只定义 12/24 小时口径，
 *     因此这里用相对强度色阶而**不套用等级名称**
 */
import { computed, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import type { EChartsOption } from 'echarts'

import { fetchField } from '@/api'
import { describeError } from '@/api/client'
import BaseChart from '@/components/common/BaseChart.vue'
import { ensureYrdMap, YRD_MAP_NAME } from '@/composables/useYrdMap'
import type { FieldGrid, MapPoint } from '@/types'
import { formatNumber } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    /** 要展示的时刻；留空取最新实况 */
    time?: string | null
    height?: string
    /** 站点覆盖层（点击可下钻） */
    points?: MapPoint[]
  }>(),
  { time: null, height: '470px', points: () => [] },
)

const emit = defineEmits<{ select: [string] }>()

const ready = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const field = ref<FieldGrid | null>(null)
/** 掩膜：1 = 该格落在行政区划内部 */
const mask = ref<Uint8Array | null>(null)

/** 场最大值，向上取整到一个好看的刻度 */
const niceMax = computed(() => {
  const max = field.value?.max_value ?? 0
  if (max <= 0) return 1
  const steps = [1, 2, 3, 5, 10, 15, 20, 30, 50, 80, 120]
  return steps.find((s) => s >= max) ?? Math.ceil(max)
})

/** 是否全场接近 0（此时不画热力，只画站点） */
const isDry = computed(() => (field.value?.max_value ?? 0) < 0.05)

/**
 * 用 GeoJSON 边界在网格分辨率上栅格化掩膜。
 *
 * 用 canvas 填充 + 读 alpha 通道，比逐点多边形判定快几个数量级，
 * 且不需要引入几何库。
 */
function buildMask(grid: FieldGrid): Uint8Array | null {
  const map = echarts.getMap(YRD_MAP_NAME) as
    | { geoJson?: unknown; geoJSON?: unknown }
    | undefined
  const geo = (map?.geoJson ?? map?.geoJSON) as
    | { features: { geometry: { type: string; coordinates: unknown } }[] }
    | undefined
  if (!geo?.features?.length) return null

  const { cols, rows, lon_min, lon_max, lat_min, lat_max } = grid
  const canvas = document.createElement('canvas')
  canvas.width = cols
  canvas.height = rows
  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const px = (lon: number) => ((lon - lon_min) / (lon_max - lon_min)) * (cols - 1)
  const py = (lat: number) => ((lat_max - lat) / (lat_max - lat_min)) * (rows - 1)

  ctx.fillStyle = '#000'
  for (const feature of geo.features) {
    const geom = feature.geometry
    const polygons =
      geom.type === 'Polygon'
        ? [geom.coordinates as number[][][]]
        : (geom.coordinates as number[][][][])

    for (const poly of polygons) {
      ctx.beginPath()
      for (const ring of poly) {
        ring.forEach((coord, index) => {
          const x = px(coord[0])
          const y = py(coord[1])
          if (index === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        })
        ctx.closePath()
      }
      ctx.fill('evenodd')
    }
  }

  const data = ctx.getImageData(0, 0, cols, rows).data
  const out = new Uint8Array(cols * rows)
  for (let i = 0; i < out.length; i++) out[i] = data[i * 4 + 3] > 0 ? 1 : 0
  return out
}

async function load(): Promise<void> {
  loading.value = true
  try {
    await ensureYrdMap()
    ready.value = true
    const grid = await fetchField({ time: props.time ?? undefined, step: 0.12, power: 2 })
    field.value = grid
    mask.value = grid.cols > 0 ? buildMask(grid) : null
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.time, load)

/** [lon, lat, value] 列表，已按行政区划掩膜剔除 */
const heatData = computed<[number, number, number][]>(() => {
  const grid = field.value
  if (!grid || !grid.cols) return []
  const m = mask.value
  const out: [number, number, number][] = []
  for (let r = 0; r < grid.rows; r++) {
    for (let c = 0; c < grid.cols; c++) {
      const i = r * grid.cols + c
      if (m && !m[i]) continue
      const v = grid.values[i] ?? 0
      if (v < 0.05) continue
      out.push([
        grid.lon_min + c * grid.step,
        grid.lat_min + r * grid.step,
        Math.round(v * 10) / 10,
      ])
    }
  }
  return out
})

const stationData = computed(() =>
  (props.points ?? []).map((p) => ({
    name: p.name,
    adcode: p.adcode,
    value: [p.lon, p.lat, p.value ?? 0],
  })),
)

const option = computed<EChartsOption>(() => ({
  animation: false,
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(10, 18, 36, 0.94)',
    borderColor: 'rgba(120, 170, 255, 0.35)',
    borderWidth: 1,
    padding: [8, 11],
    textStyle: { color: '#eaf2ff', fontSize: 12 },
    extraCssText: 'border-radius:8px;backdrop-filter:blur(6px);',
    formatter: (raw: unknown) => {
      const p = raw as { seriesType?: string; name?: string; value?: unknown }
      const value = p.value as [number, number, number] | undefined
      if (!value) return ''
      if (p.seriesType === 'scatter') {
        return `<div><b>${p.name ?? ''}</b>　实况</div>
          <div style="font-size:15px;font-weight:600">${formatNumber(value[2], 1)} <span style="font-size:11px;opacity:.7">mm/h</span></div>
          <div style="font-size:11px;opacity:.6">点击查看该点位详情</div>`
      }
      return `<div style="font-size:11px;opacity:.65">插值位置</div>
        <div style="font-size:15px;font-weight:600">${formatNumber(value[2], 1)} <span style="font-size:11px;opacity:.7">mm/h</span></div>
        <div style="font-size:11px;opacity:.6">${value[1].toFixed(2)}°N, ${value[0].toFixed(2)}°E</div>
        <div style="font-size:11px;opacity:.5">由邻近站点点位反距离加权推算</div>`
    },
  },
  geo: {
    map: YRD_MAP_NAME,
    roam: true,
    z: 5,
    scaleLimit: { min: 0.8, max: 8 },
    itemStyle: {
      areaColor: 'transparent',
      borderColor: 'rgba(150, 190, 255, 0.42)',
      borderWidth: 0.7,
    },
    emphasis: { disabled: true },
    select: { disabled: true },
  },
  visualMap: {
    type: 'continuous',
    seriesIndex: 0,
    min: 0,
    max: niceMax.value,
    left: 8,
    bottom: 12,
    itemWidth: 11,
    itemHeight: 96,
    text: [`${niceMax.value}`, '0'],
    textStyle: { color: '#a8bcd8', fontSize: 10 },
    inRange: {
      color: ['#1b4f8f', '#2b7fc4', '#2bb3c0', '#4cc38a', '#f5d76e', '#f39c12', '#e74c3c'],
    },
  },
  series: [
    {
      type: 'heatmap',
      coordinateSystem: 'geo',
      geoIndex: 0,
      z: 2,
      pointSize: 17,
      blurSize: 21,
      minOpacity: 0,
      maxOpacity: 0.9,
      data: heatData.value,
    },
    {
      type: 'scatter',
      coordinateSystem: 'geo',
      geoIndex: 0,
      z: 6,
      symbolSize: 4.5,
      itemStyle: {
        color: 'rgba(240, 246, 255, 0.9)',
        borderColor: 'rgba(8, 16, 32, 0.9)',
        borderWidth: 0.8,
      },
      data: stationData.value,
    },
  ],
}))

function onChartClick(raw: unknown): void {
  const p = raw as { seriesType?: string; data?: { adcode?: string } }
  if (p.seriesType !== 'scatter') return
  const code = p.data?.adcode
  if (code) emit('select', code)
}
</script>

<template>
  <div class="field-map">
    <BaseChart
      v-if="ready && field && field.cols > 0"
      :option="option"
      :height="height"
      class="field-map__chart"
      @chart-click="onChartClick"
    />
    <div v-else class="field-map__hint" :class="{ 'field-map__hint--error': error }">
      {{ error ? `插值场加载失败：${error}` : '正在计算连续降水场…' }}
    </div>

    <p v-if="ready && field && field.cols > 0" class="field-map__caption">
      <span v-if="isDry" class="field-map__dry">
        该时刻全区插值结果接近 0（无有效降水），仅显示 {{ field.point_count }} 个站点位置
      </span>
      <span v-else>
        网格 {{ field.cols }}×{{ field.rows }}（{{ field.step }}°）· 由 {{ field.point_count }} 个站点反距离加权插值
      </span>
      <span class="field-map__sep">·</span>
      <span class="text-muted">悬停看插值 · 点击站点看详情 · 单位 mm/h</span>
    </p>
  </div>
</template>

<style scoped>
.field-map {
  position: relative;
}

.field-map__chart :deep(canvas) {
  cursor: crosshair;
}

.field-map__hint {
  display: grid;
  place-items: center;
  height: 440px;
  font-size: 13px;
  color: var(--text-2);
}

.field-map__hint--error {
  color: #ff9d94;
}

.field-map__caption {
  margin-top: var(--gap-sm);
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--text-2);
}

.field-map__dry {
  color: var(--warning);
}

.field-map__sep {
  margin: 0 6px;
  color: var(--text-3);
}
</style>
