<script setup lang="ts">
/**
 * 点位矩阵：把全部点位按省市分组，用色块 + 数值呈现当前降水量。
 *
 * 配色采用**相对当前最大值的连续色阶**（见 rainLevels.intensityColor），
 * 不等于国标等级 —— GB/T 28592-2012 只定义 12/24 小时口径，
 * 小时尺度没有官方等级，因此同时显示真实数值以免误读。
 */
import { computed } from 'vue'

import type { MapPoint } from '@/types'
import { formatNumber } from '@/utils/format'
import { intensityColor } from '@/utils/rainLevels'

const props = withDefaults(
  defineProps<{
    points: MapPoint[]
    unit?: string
  }>(),
  { unit: 'mm' },
)

const maxValue = computed(() => props.points.reduce((max, p) => Math.max(max, p.value ?? 0), 0))

const groups = computed(() => {
  const map = new Map<string, MapPoint[]>()
  for (const point of props.points) {
    const list = map.get(point.province) ?? []
    list.push(point)
    map.set(point.province, list)
  }
  return [...map.entries()]
    .map(([province, items]) => ({
      province,
      items: [...items].sort((a, b) => (b.value ?? 0) - (a.value ?? 0)),
    }))
    .sort((a, b) => a.province.localeCompare(b.province, 'zh'))
})

function background(value: number | null): string {
  return intensityColor(value, maxValue.value)
}
</script>

<template>
  <div class="matrix">
    <p v-if="!points.length" class="matrix__empty">暂无点位数据</p>
    <div v-for="group in groups" :key="group.province" class="matrix__row">
      <span class="matrix__province">{{ group.province }}</span>
      <div class="matrix__tiles">
        <span
          v-for="point in group.items"
          :key="point.adcode"
          class="tile"
          :style="{ background: background(point.value) }"
          :title="`${point.name}：${point.value ?? 0} ${unit}（${point.level ?? '—'}）`"
        >
          <em class="tile__name">{{ point.name }}</em>
          <b class="tile__value text-mono">{{ formatNumber(point.value, 1) }}</b>
        </span>
      </div>
    </div>
    <p class="matrix__legend text-muted">
      色阶按当前最大降水 {{ formatNumber(maxValue, 1) }} {{ unit }} 线性映射；数值为该时刻降水量。
    </p>
  </div>
</template>

<style scoped>
.matrix {
  display: grid;
  gap: 8px;
}

.matrix__empty {
  padding: 20px;
  font-size: 13px;
  color: var(--text-2);
  text-align: center;
}

.matrix__row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
}

.matrix__province {
  padding-top: 4px;
  font-size: 12px;
  color: var(--text-2);
  text-align: right;
}

.matrix__tiles {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tile {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1px;
  min-width: 78px;
  padding: 4px 7px;
  border: 1px solid rgba(120, 170, 255, 0.14);
  border-radius: 5px;
  transition: transform var(--transition), border-color var(--transition);
  cursor: default;
}

.tile:hover {
  transform: translateY(-1px);
  border-color: var(--panel-border-hover);
}

.tile__name {
  font-size: 11px;
  font-style: normal;
  color: rgba(234, 242, 255, 0.82);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tile__value {
  font-size: 12px;
  font-weight: 650;
  color: #ffffff;
}

.matrix__legend {
  font-size: 11px;
}
</style>
