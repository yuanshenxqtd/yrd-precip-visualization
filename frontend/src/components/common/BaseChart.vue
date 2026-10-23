<script setup lang="ts">
/**
 * ECharts 通用容器：负责初始化、响应式尺寸、option 更新、销毁、加载态与 PNG 导出。
 *
 * **按需引入**：只注册项目实际用到的 7 种 series 与 5 个组件。
 * 全量 `import * as echarts from 'echarts'` 打包后约 1,035 KB（gzip 343 KB），
 * 按需后只保留用得上的那部分 —— 这是首屏体积最大的一块。
 *
 * 改动这里时务必同步更新下面的 `echarts.use([...])` 清单，
 * 漏注册会出现「图表空白但控制台无报错」的隐蔽问题。
 */
import * as echarts from 'echarts/core'
import {
  BarChart,
  BoxplotChart,
  HeatmapChart,
  LineChart,
  MapChart,
  PieChart,
  ScatterChart,
} from 'echarts/charts'
import {
  GeoComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import type { EChartsType } from 'echarts/core'
import type { EChartsOption } from 'echarts'

echarts.use([
  // series
  BarChart,
  BoxplotChart,
  HeatmapChart,
  LineChart,
  MapChart,
  PieChart,
  ScatterChart,
  // components
  GeoComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  // renderer
  CanvasRenderer,
])

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    height?: string
    loading?: boolean
    /** 是否显示「导出 PNG」按钮 */
    exportable?: boolean
    /** 导出文件名（不含扩展名） */
    filename?: string
  }>(),
  { height: '320px', loading: false, exportable: true, filename: 'chart' },
)

const el = ref<HTMLDivElement | null>(null)
const chart = shallowRef<EChartsType | null>(null)
let observer: ResizeObserver | null = null

/**
 * 图表内部元素被点击时抛出。
 *
 * 供上层实现「下钻」：地图点击某个区划、条形图点击某根柱子，
 * 上层从 params.data 里取出 adcode 即可唤起详情抽屉。
 */
const emit = defineEmits<{ chartClick: [unknown] }>()

function render(): void {
  chart.value?.setOption(props.option, true)
}

function syncLoading(): void {
  if (!chart.value) return
  if (props.loading) {
    chart.value.showLoading('default', {
      text: '加载中',
      color: '#3aa0e0',
      textColor: '#a8bcd8',
      maskColor: 'rgba(7, 13, 26, 0.5)',
      fontSize: 13,
    })
  } else {
    chart.value.hideLoading()
  }
}

/** 导出当前图表为 PNG（2 倍分辨率 + 深色底） */
function downloadPng(): void {
  const instance = chart.value
  if (!instance) return
  const url = instance.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#0a1226',
  })
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.filename}.png`
  link.click()
}

onMounted(() => {
  if (!el.value) return
  chart.value = echarts.init(el.value, undefined, { renderer: 'canvas' })
  chart.value.on('click', (params: unknown) => emit('chartClick', params))
  render()
  syncLoading()
  observer = new ResizeObserver(() => chart.value?.resize())
  observer.observe(el.value)
})

watch(() => props.option, render, { deep: true })
watch(() => props.loading, syncLoading)

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  chart.value?.dispose()
  chart.value = null
})
</script>

<template>
  <div class="chart-wrap">
    <div ref="el" class="chart" :style="{ height }"></div>
    <button
      v-if="exportable"
      class="chart-export"
      type="button"
      title="导出 PNG（2 倍分辨率，深色背景）"
      @click.stop="downloadPng"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round">
        <path d="M12 3.5v11M7.5 10.5l4.5 4.5 4.5-4.5M4 20h16" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.chart-wrap {
  position: relative;
  width: 100%;
}

.chart {
  width: 100%;
}

/* 悬停时浮现的导出按钮：不占布局、不干扰读图 */
.chart-export {
  position: absolute;
  top: 2px;
  right: 2px;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  color: var(--text-2);
  background: rgba(10, 18, 36, 0.82);
  border: 1px solid var(--panel-border);
  border-radius: 5px;
  opacity: 0;
  transition: opacity var(--transition), color var(--transition), border-color var(--transition);
  cursor: pointer;
}

.chart-wrap:hover .chart-export {
  opacity: 1;
}

.chart-export:hover {
  color: var(--accent-light);
  border-color: var(--panel-border-hover);
}

.chart-export svg {
  width: 13px;
  height: 13px;
}
</style>
