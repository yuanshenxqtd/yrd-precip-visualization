<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { fetchCompareBoxplot, fetchCompareMulti, fetchCompareRanking } from '@/api'
import { describeError } from '@/api/client'
import BoxplotChart from '@/components/charts/BoxplotChart.vue'
import MultiLineChart from '@/components/charts/MultiLineChart.vue'
import RankingBarChart from '@/components/charts/RankingBarChart.vue'
import { useFilterStore } from '@/stores/filter'
import type { BoxplotItem, RankingItem } from '@/types'
import { daysAgo, formatNumber, today } from '@/utils/format'

const filter = useFilterStore()

const rangeDays = ref(30)
const series = ref<{ adcode: string; name: string; points: { time: string; value: number }[] }[]>([])
const ranking = ref<RankingItem[]>([])
const boxplot = ref<BoxplotItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const RANGES = [
  { days: 7, label: '近 7 天' },
  { days: 30, label: '近 30 天' },
  { days: 90, label: '近 90 天' },
  { days: 365, label: '近 1 年' },
]

const MAX_COMPARE = 8

const start = computed(() => daysAgo(rangeDays.value - 1))
const end = computed(() => today())

const selectedNames = computed(() =>
  filter.compareAdcodes
    .map((code) => filter.nameByAdcode[code] ?? code)
    .join('、'),
)

async function load(): Promise<void> {
  loading.value = true
  try {
    await filter.loadRegions()
    const params = { start: start.value, end: end.value }
    const tasks: Promise<unknown>[] = [
      fetchCompareRanking({ ...params, limit: 15 }).then((data) => {
        ranking.value = data
      }),
      fetchCompareBoxplot({ ...params, limit: 10 }).then((data) => {
        boxplot.value = data
      }),
    ]
    if (filter.compareAdcodes.length) {
      tasks.push(
        fetchCompareMulti({ adcodes: filter.compareAdcodes.join(','), ...params }).then((data) => {
          series.value = data.series
        }),
      )
    } else {
      series.value = []
    }
    await Promise.all(tasks)
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

function toggle(adcode: string): void {
  if (
    !filter.compareAdcodes.includes(adcode) &&
    filter.compareAdcodes.length >= MAX_COMPARE
  ) {
    error.value = `最多同时对比 ${MAX_COMPARE} 个城市，请先取消一个`
    return
  }
  filter.toggleCompare(adcode)
}

watch(rangeDays, load)
watch(
  () => filter.compareAdcodes.slice().join(','),
  () => load(),
)

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">城市对比</h2>
        <p class="page__desc">
          从<strong>总量</strong>（排行）与<strong>离散程度</strong>（箱线图）两个角度刻画城市间的降水差异，
          并支持多城市日降水序列叠加对比。区间 {{ start }} ~ {{ end }}。
        </p>
      </div>
      <div class="seg">
        <button
          v-for="item in RANGES"
          :key="item.days"
          class="seg__btn"
          :class="{ 'seg__btn--active': rangeDays === item.days }"
          @click="rangeDays = item.days"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <p v-if="error" class="notice notice--error">{{ error }}</p>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">选择对比城市</div>
        <span class="panel__subtitle">最多 {{ MAX_COMPARE }} 个 · 已选：{{ selectedNames || '无' }}</span>
      </header>
      <div class="panel__body">
        <div v-for="group in filter.groupedByProvince" :key="group.province" class="picker">
          <span class="picker__province">{{ group.province }}</span>
          <div class="picker__items">
            <button
              v-for="item in group.items"
              :key="item.adcode"
              class="chip"
              :class="{ 'chip--active': filter.compareAdcodes.includes(item.adcode) }"
              @click="toggle(item.adcode)"
            >
              {{ item.name }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">多城市日降水序列</div>
        <span class="panel__subtitle">叠加对比</span>
      </header>
      <div class="panel__body">
        <MultiLineChart :series="series" height="330px" />
      </div>
    </section>

    <div class="grid-2">
      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">区间降水排行</div>
          <span class="panel__subtitle">前 15 名 · 累计 mm</span>
        </header>
        <div class="panel__body">
          <RankingBarChart :items="ranking" height="400px" />
        </div>
      </section>

      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">日降水分布（箱线图）</div>
          <span class="panel__subtitle">取累计前 10 名 · 黄点为均值</span>
        </header>
        <div class="panel__body">
          <BoxplotChart :items="boxplot" height="400px" />
        </div>
      </section>
    </div>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">箱线统计明细</div>
        <span class="panel__subtitle">五数概括</span>
      </header>
      <div class="panel__body panel__body--flush">
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>城市</th>
                <th>省份</th>
                <th class="num">最小</th>
                <th class="num">下四分位</th>
                <th class="num">中位数</th>
                <th class="num">上四分位</th>
                <th class="num">最大</th>
                <th class="num">均值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in boxplot" :key="item.adcode">
                <td>{{ item.name }}</td>
                <td class="text-dim">{{ item.province }}</td>
                <td class="num text-mono">{{ formatNumber(item.min, 1) }}</td>
                <td class="num text-mono">{{ formatNumber(item.q1, 1) }}</td>
                <td class="num text-mono">{{ formatNumber(item.median, 1) }}</td>
                <td class="num text-mono">{{ formatNumber(item.q3, 1) }}</td>
                <td class="num text-mono">{{ formatNumber(item.max, 1) }}</td>
                <td class="num text-mono">{{ formatNumber(item.mean, 1) }}</td>
              </tr>
              <tr v-if="!boxplot.length">
                <td colspan="8" class="empty">该区间无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  padding: 2px;
  background: rgba(120, 170, 255, 0.07);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.seg__btn {
  padding: 3px 11px;
  font-size: 12px;
  color: var(--text-2);
  border-radius: 4px;
}

.seg__btn--active {
  color: var(--text-0);
  background: var(--accent-dim);
}

.notice {
  padding: 10px 14px;
  font-size: 13px;
  border-radius: var(--radius-sm);
}

.notice--error {
  color: #ffd9d4;
  background: rgba(231, 76, 60, 0.14);
  border: 1px solid rgba(231, 76, 60, 0.3);
}

.picker {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  margin-bottom: 8px;
}

.picker__province {
  padding-top: 4px;
  font-size: 12px;
  color: var(--text-2);
  text-align: right;
}

.picker__items {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.chip {
  padding: 3px 10px;
  font-size: 12px;
  color: var(--text-1);
  background: rgba(120, 170, 255, 0.05);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
  transition: color var(--transition), background var(--transition), border-color var(--transition);
}

.chip:hover {
  border-color: var(--panel-border-hover);
}

.chip--active {
  color: #04121e;
  font-weight: 600;
  background: linear-gradient(180deg, var(--accent-light), var(--accent));
  border-color: transparent;
}

.panel__body--flush {
  padding: 0;
}

.table-wrap {
  max-height: 380px;
  overflow: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.table th,
.table td {
  padding: 8px 14px;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid rgba(120, 170, 255, 0.1);
}

.table thead th {
  position: sticky;
  top: 0;
  color: var(--text-2);
  font-weight: 500;
  background: var(--panel-bg-solid);
}

.table .num {
  text-align: right;
}

.empty {
  padding: 20px;
  text-align: center;
  color: var(--text-2);
}
</style>
