<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { fetchLevelDistribution, fetchTrendAnomaly, fetchTrendDaily, fetchTrendMonthly } from '@/api'
import { describeError } from '@/api/client'
import AnomalyChart from '@/components/charts/AnomalyChart.vue'
import DailyTrendChart from '@/components/charts/DailyTrendChart.vue'
import LevelDonutChart from '@/components/charts/LevelDonutChart.vue'
import MonthlyBarChart from '@/components/charts/MonthlyBarChart.vue'
import RegionSelect from '@/components/common/RegionSelect.vue'
import { useFilterStore } from '@/stores/filter'
import type { AnomalyPoint, DailyPoint, LevelCount, TrendPoint } from '@/types'
import { daysAgo, formatNumber, today } from '@/utils/format'

const filter = useFilterStore()

/** 区域选择直接读全局聚焦状态，与其他模块共用同一份选择 */
const adcode = computed(() => filter.selectedAdcode)
const rangeDays = ref(90)
const year = ref(new Date().getFullYear())
const customStart = ref(daysAgo(89))
const customEnd = ref(today())

const daily = ref<DailyPoint[]>([])
const monthly = ref<TrendPoint[]>([])
const anomaly = ref<AnomalyPoint[]>([])
const levels = ref<LevelCount[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const RANGES = [
  { days: 30, label: '近 30 天' },
  { days: 90, label: '近 90 天' },
  { days: 365, label: '近 1 年' },
  { days: 1129, label: '全部（约 3 年）' },
]

/** 数据起始年份（库内日数据自 2023-09 起） */
const YEARS = [2023, 2024, 2025, 2026]

const rangeLabel = computed(() => `${customStart.value} ~ ${customEnd.value}`)

const dailyTotal = computed(
  () => Math.round(daily.value.reduce((sum, p) => sum + p.value, 0) * 10) / 10,
)
const dailyPeak = computed(() =>
  daily.value.reduce((max, p) => (p.value > max.value ? p : max), { time: '—', value: 0, max: 0 }),
)
const anomalyPeak = computed(() => {
  const valid = anomaly.value.filter((a) => a.anomaly_pct !== null)
  if (!valid.length) return null
  return valid.reduce((max, a) => (Math.abs(a.anomaly_pct!) > Math.abs(max.anomaly_pct!) ? a : max))
})

async function loadTrend(): Promise<void> {
  loading.value = true
  try {
    await filter.loadRegions()
    const [dailyData, levelData] = await Promise.all([
      fetchTrendDaily({ adcode: adcode.value ?? undefined, start: customStart.value, end: customEnd.value }),
      fetchLevelDistribution({ adcode: adcode.value ?? undefined }),
    ])
    daily.value = dailyData.points
    levels.value = levelData
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

async function loadYearly(): Promise<void> {
  try {
    const [monthlyData, anomalyData] = await Promise.all([
      fetchTrendMonthly({ adcode: adcode.value ?? undefined, year: year.value }),
      fetchTrendAnomaly({ adcode: adcode.value ?? undefined, year: year.value }),
    ])
    monthly.value = monthlyData.points
    anomaly.value = anomalyData
  } catch (err) {
    error.value = describeError(err)
  }
}

function applyRange(days: number): void {
  rangeDays.value = days
  customStart.value = daysAgo(days - 1)
  customEnd.value = today()
  loadTrend()
}

watch([adcode, year], () => {
  loadTrend()
  loadYearly()
})

onMounted(() => {
  loadTrend()
  loadYearly()
})
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">时间分析</h2>
        <p class="page__desc">
          从日、月、年三个尺度看降水变化，并结合同期基准做<strong>距平分析</strong>。
          距平基准仅采用 <strong>2024 / 2025 两个完整年</strong>（2023 仅含 9–12 月、2026 年尚未过完，
          混入会造成严重偏差）。
        </p>
      </div>
      <div class="controls">
        <RegionSelect
          :model-value="adcode"
          label="区域"
          @update:model-value="filter.select($event)"
        />
      </div>
    </div>

    <p v-if="error" class="notice notice--error">{{ error }}</p>

    <div class="grid-3">
      <div class="mini">
        <span class="mini__label">区间累计</span>
        <span class="mini__value text-mono">{{ formatNumber(dailyTotal, 1) }}<em>mm</em></span>
      </div>
      <div class="mini">
        <span class="mini__label">单日最大</span>
        <span class="mini__value text-mono">{{ formatNumber(dailyPeak.value, 1) }}<em>mm</em></span>
        <span class="mini__hint text-mono">{{ dailyPeak.time }}</span>
      </div>
      <div class="mini">
        <span class="mini__label">最大距平</span>
        <span class="mini__value text-mono">
          {{ anomalyPeak?.anomaly_pct != null ? `${anomalyPeak.anomaly_pct > 0 ? '+' : ''}${anomalyPeak.anomaly_pct}%` : '—' }}
        </span>
        <span class="mini__hint text-mono">{{ anomalyPeak?.month ?? '—' }}</span>
      </div>
    </div>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">日降水趋势</div>
        <div class="seg">
          <button
            v-for="item in RANGES"
            :key="item.days"
            class="seg__btn"
            :class="{ 'seg__btn--active': rangeDays === item.days }"
            @click="applyRange(item.days)"
          >
            {{ item.label }}
          </button>
        </div>
      </header>
      <div class="panel__body">
        <p class="hint text-muted">
          区间 {{ rangeLabel }}
          <template v-if="!adcode">　·　柱为全区日均，线为当日最大点位</template>
        </p>
        <DailyTrendChart :points="daily" :show-max="!adcode" height="300px" />
      </div>
    </section>

    <div class="grid-2">
      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">月累计降水</div>
          <div class="seg">
            <button
              v-for="y in YEARS"
              :key="y"
              class="seg__btn"
              :class="{ 'seg__btn--active': year === y }"
              @click="year = y"
            >
              {{ y }}
            </button>
          </div>
        </header>
        <div class="panel__body">
          <MonthlyBarChart :points="monthly" height="270px" />
        </div>
      </section>

      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">降水距平</div>
          <span class="panel__subtitle">基准 = 2024 / 2025 同期均值</span>
        </header>
        <div class="panel__body">
          <AnomalyChart :items="anomaly" height="270px" />
        </div>
      </section>
    </div>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">日降水量等级分布</div>
        <span class="panel__subtitle">GB/T 28592-2012 · 24 小时口径</span>
      </header>
      <div class="panel__body">
        <LevelDonutChart :items="levels" height="280px" :unit="adcode ? '天' : '点位·天'" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.controls {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  flex-wrap: wrap;
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

.mini {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 13px 16px;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius);
}

.mini__label {
  font-size: 12px;
  color: var(--text-2);
}

.mini__value {
  font-size: 24px;
  font-weight: 650;
  color: var(--text-0);
}

.mini__value em {
  margin-left: 4px;
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  color: var(--text-2);
}

.mini__hint {
  font-size: 11px;
  color: var(--text-3);
}

.seg {
  display: inline-flex;
  padding: 2px;
  background: rgba(120, 170, 255, 0.07);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.seg__btn {
  padding: 3px 10px;
  font-size: 12px;
  color: var(--text-2);
  border-radius: 4px;
}

.seg__btn--active {
  color: var(--text-0);
  background: var(--accent-dim);
}

.hint {
  margin-bottom: 8px;
  font-size: 12px;
}
</style>
