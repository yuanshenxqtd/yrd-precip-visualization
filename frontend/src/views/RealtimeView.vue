<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchCollectLogs, fetchRealtimeLatest, fetchTimeseries } from '@/api'
import { describeError } from '@/api/client'
import HourlyTrendChart from '@/components/charts/HourlyTrendChart.vue'
import PointMatrix from '@/components/charts/PointMatrix.vue'
import RegionSelect from '@/components/common/RegionSelect.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useAppStore } from '@/stores/app'
import { useDetailStore } from '@/stores/detail'
import { useFilterStore } from '@/stores/filter'
import type { CollectLog, RealtimeLatest, TrendPoint } from '@/types'
import { formatNumber, shortDateTime, shortTime } from '@/utils/format'

const app = useAppStore()
const filter = useFilterStore()
const detail = useDetailStore()

const latest = ref<RealtimeLatest | null>(null)
const series = ref<TrendPoint[]>([])
const logs = ref<CollectLog[]>([])
const adcode = ref<string | null>(null)
const hours = ref(48)
const loading = ref(false)
const error = ref<string | null>(null)

const WINDOWS = [24, 48, 72]

const lastLog = computed(() => logs.value[0] ?? null)

const pointsWithRain = computed(
  () => (latest.value?.points ?? []).filter((p) => (p.value ?? 0) > 0),
)

const peak = computed(() => {
  let best: { name: string; value: number } | null = null
  for (const p of latest.value?.points ?? []) {
    const v = p.value ?? 0
    if (v > 0 && (!best || v > best.value)) best = { name: p.name, value: v }
  }
  return best
})

const seriesTotal = computed(() =>
  Math.round(series.value.reduce((sum, p) => sum + p.value, 0) * 10) / 10,
)

async function loadAll(): Promise<void> {
  loading.value = true
  try {
    await filter.loadRegions()
    const [latestData, seriesData, logData] = await Promise.all([
      fetchRealtimeLatest(),
      fetchTimeseries({ adcode: adcode.value ?? undefined, hours: hours.value }),
      fetchCollectLogs({ limit: 6 }),
    ])
    latest.value = latestData
    series.value = seriesData.points
    logs.value = logData
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

async function loadSeries(): Promise<void> {
  try {
    const data = await fetchTimeseries({ adcode: adcode.value ?? undefined, hours: hours.value })
    series.value = data.points
  } catch (err) {
    error.value = describeError(err)
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">实时监测</h2>
        <p class="page__desc">
          最新实况时刻
          <span class="text-mono">{{ shortTime(latest?.time) }}</span>
          ，逐小时序列与 56 个点位的降水分布。采集心跳取自 <code>/api/admin/collect-logs</code>。
        </p>
      </div>
      <button class="btn" :disabled="loading" @click="loadAll">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <p v-if="error" class="notice notice--error">{{ error }}</p>

    <div class="grid-4">
      <StatCard
        label="该时刻有降水点位"
        :value="pointsWithRain.length"
        unit="/ 56"
        :tone="pointsWithRain.length ? 'accent' : 'default'"
        :muted="!pointsWithRain.length"
        :hint="pointsWithRain.length ? '存在降水' : '当前全区无降水'"
      />
      <StatCard
        label="该时刻最大雨强"
        :value="peak ? formatNumber(peak.value, 1) : '—'"
        unit="mm/h"
        :muted="!peak"
        :hint="peak ? peak.name : '无降水'"
      />
      <StatCard
        label="近窗口累计"
        :value="formatNumber(seriesTotal, 1)"
        unit="mm"
        :muted="seriesTotal === 0"
        :hint="`近 ${hours} 小时 · ${adcode ? '单点位' : '全区合计'}`"
      />
      <StatCard
        label="最近一次采集"
        :value="lastLog ? lastLog.mode : '—'"
        :tone="lastLog?.status === 'success' ? 'accent' : 'warning'"
        :hint="lastLog ? `${shortDateTime(lastLog.started_at)} · ${lastLog.status}` : '无记录'"
      />
    </div>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">逐小时降水序列</div>
        <div class="controls">
          <RegionSelect v-model="adcode" label="区域" @update:model-value="loadSeries" />
          <div class="seg">
            <button
              v-for="w in WINDOWS"
              :key="w"
              class="seg__btn"
              :class="{ 'seg__btn--active': hours === w }"
              @click="((hours = w), loadSeries())"
            >
              {{ w }}h
            </button>
          </div>
        </div>
      </header>
      <div class="panel__body">
        <p class="hint text-muted">
          柱为逐小时降水（mm）。当前全区无降水时柱高为 0 —— 这是真实天气状态，不是故障。
        </p>
        <HourlyTrendChart :points="series" height="240px" />
      </div>
    </section>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">点位降水矩阵</div>
        <span class="panel__subtitle">按省市分组 · 色阶为相对强度</span>
      </header>
      <div class="panel__body">
        <PointMatrix :points="latest?.points ?? []" @select="detail.open($event)" />
      </div>
    </section>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">采集心跳</div>
        <span class="panel__subtitle">最近 6 次采集记录</span>
      </header>
      <div class="panel__body panel__body--flush">
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>模式</th>
                <th>状态</th>
                <th class="num">写入行数</th>
                <th class="num">新增</th>
                <th>开始</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in logs" :key="log.id">
                <td class="text-mono">{{ log.id }}</td>
                <td>{{ log.mode }}</td>
                <td>
                  <span class="tag" :class="log.status === 'success' ? 'tag--ok' : 'tag--bad'">
                    {{ log.status }}
                  </span>
                </td>
                <td class="num text-mono">{{ formatNumber(log.rows_upserted) }}</td>
                <td class="num text-mono">{{ formatNumber(log.gap_filled_hours) }}</td>
                <td class="text-mono">{{ shortDateTime(log.started_at) }}</td>
              </tr>
              <tr v-if="!logs.length">
                <td colspan="6" class="empty">暂无采集记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.btn {
  padding: 7px 16px;
  font-size: 13px;
  color: var(--text-0);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.btn:hover:not(:disabled) {
  border-color: var(--panel-border-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.controls {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  flex-wrap: wrap;
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

.panel__body--flush {
  padding: 0;
}

.table-wrap {
  max-height: 260px;
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

.tag {
  display: inline-block;
  padding: 1px 8px;
  font-size: 11px;
  border-radius: 999px;
}

.tag--ok {
  color: #8ff0b5;
  background: rgba(46, 204, 113, 0.14);
}

.tag--bad {
  color: #ff9d94;
  background: rgba(231, 76, 60, 0.16);
}

code {
  padding: 1px 5px;
  font-family: var(--font-mono);
  font-size: 11px;
  background: rgba(120, 170, 255, 0.1);
  border-radius: 4px;
}
</style>
