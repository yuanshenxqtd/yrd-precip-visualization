<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import {
  fetchHighlights,
  fetchLevelDistribution,
  fetchRanking,
  fetchSummary,
  fetchTimeseries,
  fetchTimespan,
} from '@/api'
import { describeError } from '@/api/client'
import HourlyTrendChart from '@/components/charts/HourlyTrendChart.vue'
import LevelDonutChart from '@/components/charts/LevelDonutChart.vue'
import RainMap from '@/components/charts/RainMap.vue'
import InsightPanel from '@/components/common/InsightPanel.vue'
import StatCard from '@/components/common/StatCard.vue'
import { ensureYrdMap } from '@/composables/useYrdMap'
import { useAppStore } from '@/stores/app'
import { useDetailStore } from '@/stores/detail'
import { useFilterStore } from '@/stores/filter'
import type {
  LevelCount,
  MapFrame,
  OverviewHighlights,
  OverviewSummary,
  RankingItem,
  TrendPoint,
} from '@/types'
import { formatNumber, shiftHours, shortTime } from '@/utils/format'

const app = useAppStore()
const filter = useFilterStore()
const detail = useDetailStore()

const summary = ref<OverviewSummary | null>(null)
const ranking = ref<RankingItem[]>([])
const frames = ref<MapFrame[]>([])
const series = ref<TrendPoint[]>([])
const levels = ref<LevelCount[]>([])
const highlights = ref<OverviewHighlights | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

/** 地图两种口径：近 24h 逐小时累加 / 某单个整点 */
const mapMode = ref<'cumulative' | 'instant'>('cumulative')
const frameIndex = ref(0)

const cumulative = computed<Record<string, number>>(() => {
  const acc: Record<string, number> = {}
  for (const frame of frames.value) {
    for (const [adcode, mm] of Object.entries(frame.values)) {
      acc[adcode] = (acc[adcode] ?? 0) + (mm ?? 0)
    }
  }
  for (const key of Object.keys(acc)) acc[key] = Math.round(acc[key] * 10) / 10
  return acc
})

const currentFrame = computed<MapFrame | null>(() => frames.value[frameIndex.value] ?? null)

const mapValues = computed<Record<string, number>>(() => {
  if (mapMode.value === 'cumulative') return cumulative.value
  const values = currentFrame.value?.values ?? {}
  return Object.fromEntries(
    Object.entries(values).map(([adcode, mm]) => [adcode, mm ?? 0]),
  ) as Record<string, number>
})

const mapData = computed(() =>
  Object.entries(mapValues.value).map(([adcode, value]) => ({
    adcode,
    name: filter.nameByAdcode[adcode] ?? adcode,
    value: Math.round((value ?? 0) * 10) / 10,
  })),
)

/** 该区间全区无降水（值全为 0）—— 用于显示解释性提示 */
const mapDry = computed(() => mapData.value.length > 0 && mapData.value.every((d) => d.value === 0))

const mapRangeText = computed(() => {
  if (!frames.value.length) return '—'
  return `${shortTime(frames.value[0].time)} ~ ${shortTime(frames.value[frames.value.length - 1].time)}`
})

const maxRankingTotal = computed(() => ranking.value.reduce((max, item) => Math.max(max, item.total), 0))
const dry = computed(() => (summary.value?.sum_24h_mm ?? 0) === 0)

/**
 * 聚焦点位后，把「近 24 小时全区降水」这张图切成该点位的序列。
 *
 * 这是联动在总览页上的可见反馈 —— 否则用户点了地图只会看到一条提示条，
 * 会觉得「点了但什么都没变」。
 */
async function loadSeries(): Promise<void> {
  try {
    const data = await fetchTimeseries({
      hours: 24,
      adcode: filter.selectedAdcode ?? undefined,
    })
    series.value = data.points
  } catch (err) {
    error.value = describeError(err)
  }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    await ensureYrdMap()
    await filter.loadRegions()

    const summaryData = await fetchSummary()
    summary.value = summaryData

    const latest = summaryData.latest_obs_time
    const tasks: Promise<unknown>[] = [
      fetchRanking({ limit: 10, hours: 24 }).then((data) => {
        ranking.value = data
      }),
      loadSeries(),
      fetchLevelDistribution().then((data) => {
        levels.value = data
      }),
      fetchHighlights({ hours: 24, window_days: 30 }).then((data) => {
        highlights.value = data
      }),
    ]

    if (latest) {
      const start = shiftHours(latest, -23)
      tasks.push(
        fetchTimespan({ start, end: latest, max_frames: 24 }).then((data) => {
          frames.value = data
          frameIndex.value = Math.max(data.length - 1, 0)
        }),
      )
    }

    await Promise.all(tasks)
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

// 聚焦变化时只重拉趋势（其余图表看全区数据，不必整页重载）
watch(
  () => filter.selectedAdcode,
  () => {
    void loadSeries()
  },
)

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">总览大屏</h2>
        <p class="page__desc">
          长三角地区（沪苏浙皖）56 个采集点的降水实况概览。数据时刻
          <span class="text-mono">{{ shortTime(summary?.latest_obs_time) }}</span>
          ，统计窗口为最近 24 个整点。分级依据国家标准 GB/T 28592-2012。
        </p>
      </div>
      <button class="btn" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <!-- 读图要点：把「从图里读结论」搬到界面上 -->
    <InsightPanel :data="highlights" @select="detail.open($event)" />

    <p v-if="error" class="notice notice--error">{{ error }}</p>

    <!-- 指标卡 -->
    <div class="grid-4">
      <StatCard
        label="近 24h 全区累计"
        :value="formatNumber(summary?.sum_24h_mm, 1)"
        unit="mm"
        :muted="dry"
        :hint="dry ? '当前全区无降水' : `覆盖 ${summary?.points_with_rain ?? 0} 个点位`"
      />
      <StatCard
        label="降水覆盖率"
        :value="formatNumber(summary?.rain_coverage_pct, 1)"
        unit="%"
        :tone="(summary?.rain_coverage_pct ?? 0) > 0 ? 'accent' : 'default'"
        :hint="`${summary?.points_with_rain ?? 0} / ${summary?.points_total ?? 56} 个点位有降水`"
      />
      <StatCard
        label="最大小时雨强"
        :value="summary?.max_hourly_mm === null ? '—' : formatNumber(summary?.max_hourly_mm, 1)"
        unit="mm/h"
        :muted="summary?.max_hourly_mm === null"
        :hint="
          summary?.max_hourly_point
            ? `${summary.max_hourly_point} · ${shortTime(summary.max_hourly_time)}`
            : '无降水'
        "
      />
      <StatCard
        label="24h 累计最多"
        :value="summary?.wettest_point ? formatNumber(summary?.wettest_24h_mm, 1) : '—'"
        unit="mm"
        tone="accent"
        :muted="!summary?.wettest_point"
        :hint="summary?.wettest_point ?? '无降水'"
      />
    </div>

    <!-- 地图 + 排行 -->
    <div class="overview-main">
      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">长三角降水分布</div>
          <div class="seg">
            <button
              class="seg__btn"
              :class="{ 'seg__btn--active': mapMode === 'cumulative' }"
              @click="mapMode = 'cumulative'"
            >
              近 24h 累计
            </button>
            <button
              class="seg__btn"
              :class="{ 'seg__btn--active': mapMode === 'instant' }"
              @click="mapMode = 'instant'"
            >
              逐小时
            </button>
          </div>
        </header>
        <div class="panel__body">
          <RainMap :data="mapData" height="452px" @select="detail.open($event)" />
          <div v-if="mapMode === 'instant' && frames.length > 1" class="scrubber">
            <input
              v-model.number="frameIndex"
              class="scrubber__range"
              type="range"
              min="0"
              :max="frames.length - 1"
            />
            <span class="scrubber__time text-mono">{{ shortTime(currentFrame?.time) }}</span>
          </div>
          <p class="caption">
            <template v-if="mapMode === 'cumulative'">
              统计区间 <span class="text-mono">{{ mapRangeText }}</span>，逐小时累加
            </template>
            <template v-else>
              当前帧 <span class="text-mono">{{ shortTime(currentFrame?.time) }}</span>
              <span class="text-muted">（拖动滑块回放过去 24 小时）</span>
            </template>
            <span class="caption__hint">· 点击任意区划可查看该点位明细</span>
            <span v-if="mapDry" class="caption__dry">
              · 该区间全区无降水，地图呈中性色属正常现象
            </span>
          </p>
        </div>
      </section>

      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">降水排行 Top 10</div>
          <span class="panel__subtitle">近 24 小时累计 · 点击查看明细</span>
        </header>
        <div class="panel__body">
          <p v-if="!ranking.length" class="empty">暂无数据</p>
          <ol v-else class="rank">
            <li v-for="(item, index) in ranking" :key="item.adcode">
              <button
                type="button"
                class="rank__row"
                :class="{ 'rank__row--active': filter.selectedAdcode === item.adcode }"
                @click="detail.open(item.adcode)"
              >
                <span class="rank__no" :class="{ 'rank__no--top': index < 3 }">{{ index + 1 }}</span>
                <span class="rank__name">
                  {{ item.name }}
                  <em class="rank__province">{{ item.province }}</em>
                </span>
                <span class="rank__bar">
                  <i :style="{ width: `${maxRankingTotal ? (item.total / maxRankingTotal) * 100 : 0}%` }"></i>
                </span>
                <span class="rank__value text-mono">{{ formatNumber(item.total, 1) }}</span>
              </button>
            </li>
          </ol>
        </div>
      </section>
    </div>

    <!-- 趋势 + 等级 -->
    <div class="grid-2">
      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">
            近 24 小时{{ filter.hasFocus ? filter.focusName : '全区' }}降水
          </div>
          <span class="panel__subtitle">
            {{ filter.hasFocus ? '该点位逐小时降水 · mm' : '逐小时合计 · mm' }}
          </span>
        </header>
        <div class="panel__body">
          <HourlyTrendChart :points="series" height="248px" />
        </div>
      </section>

      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">日降水量等级分布</div>
          <span class="panel__subtitle">3 年全量 · GB/T 28592-2012</span>
        </header>
        <div class="panel__body">
          <LevelDonutChart :items="levels" height="248px" />
        </div>
      </section>
    </div>

    <!-- 数据源状态 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">数据源与系统状态</div>
        <span class="panel__subtitle">来自 /api/meta</span>
      </header>
      <div class="panel__body">
        <dl class="kv">
          <div><dt>数据源</dt><dd>{{ app.meta?.data_source ?? '—' }}（ECMWF ERA5 / ERA5-Land）</dd></div>
          <div><dt>采集点 / 行政区划</dt><dd class="text-mono">{{ app.meta?.points_total ?? '—' }} / {{ app.meta?.regions_total ?? '—' }}</dd></div>
          <div><dt>小时记录</dt><dd class="text-mono">{{ app.meta ? formatNumber(app.meta.hourly_rows) : '—' }}</dd></div>
          <div><dt>日汇总记录</dt><dd class="text-mono">{{ app.meta ? formatNumber(app.meta.daily_rows) : '—' }}</dd></div>
          <div><dt>实况数据范围</dt><dd class="text-mono">{{ shortTime(app.meta?.observed_start) }} ~ {{ shortTime(app.meta?.observed_end) }}</dd></div>
          <div><dt>预报数据至</dt><dd class="text-mono">{{ shortTime(app.meta?.forecast_end) }}</dd></div>
          <div><dt>日数据范围</dt><dd class="text-mono">{{ app.meta?.daily_start ?? '—' }} ~ {{ app.meta?.daily_end ?? '—' }}</dd></div>
          <div><dt>最近采集</dt><dd class="text-mono">{{ app.meta?.last_collect_at ?? '—' }} · {{ app.meta?.last_collect_status ?? '—' }}</dd></div>
          <div><dt>采集间隔</dt><dd class="text-mono">每 {{ app.meta?.collect_interval_minutes ?? 30 }} 分钟</dd></div>
        </dl>
      </div>
    </section>

    <!-- 模块导航 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">模块导航</div>
        <span class="panel__subtitle">P6 已完成总览图表；其余模块在 P7 填充</span>
      </header>
      <div class="panel__body">
        <div class="modules">
          <RouterLink to="/realtime" class="module">实时监测 <em>近 48h 序列与采集心跳</em></RouterLink>
          <RouterLink to="/spatial" class="module">空间分布 <em>分级设色地图 + 时间轴回放</em></RouterLink>
          <RouterLink to="/trend" class="module">时间分析 <em>日/月趋势、距平、等级分布</em></RouterLink>
          <RouterLink to="/compare" class="module">城市对比 <em>多城序列、排行、箱线图</em></RouterLink>
          <RouterLink to="/alerts" class="module">预警统计 <em>预警列表与极值统计</em></RouterLink>
          <RouterLink to="/data" class="module">数据管理 <em>采集日志、质量报告、导出</em></RouterLink>
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
  transition: border-color var(--transition);
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

.overview-main {
  display: grid;
  grid-template-columns: minmax(0, 2.1fr) minmax(300px, 1fr);
  gap: var(--gap);
}

@media (max-width: 1280px) {
  .overview-main {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* 分段切换器 */
.seg {
  display: inline-flex;
  padding: 2px;
  background: rgba(120, 170, 255, 0.07);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.seg__btn {
  padding: 3px 12px;
  font-size: 12px;
  color: var(--text-2);
  border-radius: 4px;
  transition: color var(--transition), background var(--transition);
}

.seg__btn--active {
  color: var(--text-0);
  background: var(--accent-dim);
}

/* 时间轴 */
.scrubber {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  margin-top: var(--gap-sm);
}

.scrubber__range {
  flex: 1;
  height: 4px;
  accent-color: var(--accent);
  cursor: pointer;
}

.scrubber__time {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--accent-light);
}

.caption {
  margin-top: var(--gap-sm);
  font-size: 12px;
  color: var(--text-2);
}

.caption__hint {
  color: var(--accent-light);
  opacity: 0.8;
}

.caption__dry {
  margin-left: 6px;
  color: var(--warning);
}

.empty {
  padding: 18px 4px;
  font-size: 13px;
  color: var(--text-2);
  text-align: center;
}

/* 排行榜 */
.rank {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}

.rank__row {
  display: grid;
  grid-template-columns: 22px 1fr 74px 52px;
  align-items: center;
  gap: var(--gap-sm);
  width: 100%;
  padding: 3px 6px;
  font-size: 13px;
  color: inherit;
  text-align: left;
  border-radius: var(--radius-sm);
  transition: background var(--transition);
  cursor: pointer;
}

.rank__row:hover {
  background: rgba(120, 170, 255, 0.09);
}

/* 当前聚焦的行：让「联动到了哪个点位」在列表里也看得出来 */
.rank__row--active {
  background: rgba(58, 160, 224, 0.16);
  box-shadow: inset 2px 0 0 var(--accent);
}

.rank__row:focus-visible {
  outline: 2px solid var(--accent-light);
  outline-offset: 0;
}

.rank__no {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  font-size: 11px;
  color: var(--text-2);
  background: rgba(120, 170, 255, 0.08);
  border-radius: 4px;
}

.rank__no--top {
  color: #06121f;
  font-weight: 700;
  background: linear-gradient(180deg, var(--accent-light), var(--accent));
}

.rank__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank__province {
  margin-left: 6px;
  font-size: 11px;
  font-style: normal;
  color: var(--text-3);
}

.rank__bar {
  height: 6px;
  overflow: hidden;
  background: rgba(120, 170, 255, 0.1);
  border-radius: 3px;
}

.rank__bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-light));
  border-radius: 3px;
}

.rank__value {
  text-align: right;
  color: var(--text-0);
}

/* 键值表 */
.kv {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 8px var(--gap);
  font-size: 13px;
}

.kv > div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding-bottom: 6px;
  border-bottom: 1px dashed rgba(120, 170, 255, 0.12);
}

.kv dt {
  flex: 0 0 auto;
  color: var(--text-2);
}

.kv dd {
  margin: 0;
  text-align: right;
  color: var(--text-0);
}

/* 模块导航 */
.modules {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--gap-sm);
}

.module {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-0);
  background: rgba(120, 170, 255, 0.05);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background var(--transition);
}

.module:hover {
  background: var(--accent-dim);
  border-color: var(--panel-border-hover);
}

.module em {
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  color: var(--text-2);
}
</style>
