<script setup lang="ts">
/** ECharts 通用容器：负责初始化、响应式尺寸、option 更新与销毁。 */
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    option: echarts.EChartsOption
    height?: string
    loading?: boolean
  }>(),
  { height: '320px', loading: false },
)

const el = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
let observer: ResizeObserver | null = null

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

onMounted(() => {
  if (!el.value) return
  chart.value = echarts.init(el.value, undefined, { renderer: 'canvas' })
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
  <div ref="el" class="chart" :style="{ height }"></div>
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>
