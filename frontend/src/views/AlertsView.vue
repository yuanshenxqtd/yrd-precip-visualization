<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { fetchExtremes, fetchLevelDistribution } from '@/api'
import { describeError } from '@/api/client'
import LevelDonutChart from '@/components/charts/LevelDonutChart.vue'
import type { ExtremeEvent, LevelCount } from '@/types'
import { formatNumber } from '@/utils/format'

/** 国标阈值：暴雨 ≥50、大暴雨 ≥100、特大暴雨 ≥250（24 小时口径） */
const THRESHOLDS = [
  { value: 0, label: '全部降水日', desc: '日累计 > 0' },
  { value: 50, label: '暴雨及以上', desc: '≥ 50 mm' },
  { value: 100, label: '大暴雨及以上', desc: '≥ 100 mm' },
  { value: 250, label: '特大暴雨', desc: '≥ 250 mm' },
]

const minMm = ref(50)
const limit = ref(30)
const events = ref<ExtremeEvent[]>([])
const levels = ref<LevelCount[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const activeThreshold = computed(
  () => THRESHOLDS.find((t) => t.value === minMm.value) ?? THRESHOLDS[1],
)

const summary = computed(() => {
  const list = events.value
  if (!list.length) return { max: 0, top: null as ExtremeEvent | null, wettestHour: 0 }
  const top = list[0]
  const wettestHour = list.reduce(
    (max, e) => Math.max(max, e.precip_max_hourly ?? 0),
    0,
  )
  return { max: top.precip_sum, top, wettestHour }
})

/** 事件涉及的日期数（同一次过程往往跨多个点位） */
const distinctDates = computed(() => new Set(events.value.map((e) => e.obs_date)).size)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [eventData, levelData] = await Promise.all([
      fetchExtremes({ min_mm: minMm.value > 0 ? minMm.value : undefined, limit: limit.value }),
      fetchLevelDistribution(),
    ])
    events.value = eventData
    levels.value = levelData
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

watch([minMm, limit], load)
onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">预警统计</h2>
        <p class="page__desc">
          从 3 年历史数据中提取<strong>极端降水事件</strong>并按国标阈值分级，
          用于识别需要重点关注的强降水过程。
        </p>
      </div>
      <button class="btn" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <p v-if="error" class="notice notice--error">{{ error }}</p>

    <!-- 数据源说明（诚实标注） -->
    <section class="panel panel--info">
      <header class="panel__header">
        <div class="panel__title">关于「气象预警」数据源</div>
        <span class="panel__subtitle">重要说明</span>
      </header>
      <div class="panel__body">
        <p class="note">
          本项目使用的 <strong>Open-Meteo 不提供中国气象预警数据</strong>，因此数据库中的
          <code>weather_alert</code> 表当前为空，接口 <code>GET /api/alerts</code> 返回空数组
          —— 这是<strong>预期行为，不是故障</strong>。
        </p>
        <p class="note">
          本页展示的是<strong>由降水数据按国标阈值自动判定</strong>的「统计型预警」，
          即以 GB/T 28592-2012 的等级划分代替人工发布的预警信号。
          若需真实预警，可接入和风天气的预警接口（表结构与接口已就绪）。
        </p>
      </div>
    </section>

    <div class="grid-3">
      <div class="mini">
        <span class="mini__label">最大单日单点</span>
        <span class="mini__value text-mono">{{ formatNumber(summary.max, 1) }}<em>mm</em></span>
        <span class="mini__hint text-mono">
          {{ summary.top ? `${summary.top.obs_date} · ${summary.top.name}` : '—' }}
        </span>
      </div>
      <div class="mini">
        <span class="mini__label">最大小时雨强</span>
        <span class="mini__value text-mono">{{ formatNumber(summary.wettestHour, 1) }}<em>mm/h</em></span>
        <span class="mini__hint text-muted">在筛选结果中出现过的最强小时</span>
      </div>
      <div class="mini">
        <span class="mini__label">事件数 / 涉及日期</span>
        <span class="mini__value text-mono">
          {{ events.length }}<em>/ {{ distinctDates }} 天</em>
        </span>
        <span class="mini__hint text-muted">当前筛选：{{ activeThreshold.label }}</span>
      </div>
    </div>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">极端降水事件榜</div>
        <div class="seg">
          <button
            v-for="item in THRESHOLDS"
            :key="item.value"
            class="seg__btn"
            :class="{ 'seg__btn--active': minMm === item.value }"
            :title="item.desc"
            @click="minMm = item.value"
          >
            {{ item.label }}
          </button>
        </div>
      </header>
      <div class="panel__body panel__body--flush">
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th class="rank-col">#</th>
                <th>日期</th>
                <th>点位</th>
                <th>省份</th>
                <th class="num">日累计 (mm)</th>
                <th class="num">最大小时 (mm/h)</th>
                <th class="num">有雨小时</th>
                <th>等级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, i) in events" :key="`${item.adcode}-${item.obs_date}`">
                <td class="rank-col text-mono">{{ i + 1 }}</td>
                <td class="text-mono">{{ item.obs_date }}</td>
                <td>{{ item.name }}</td>
                <td class="text-dim">{{ item.province }}</td>
                <td class="num text-mono strong">{{ formatNumber(item.precip_sum, 1) }}</td>
                <td class="num text-mono">
                  {{ item.precip_max_hourly == null ? '—' : formatNumber(item.precip_max_hourly, 1) }}
                </td>
                <td class="num text-mono" :title="item.rain_hours == null ? '该日期由日值接口回填，无小时明细' : ''">
                  {{ item.rain_hours == null ? '—' : item.rain_hours }}
                </td>
                <td>
                  <span class="level" :style="{ background: item.color ?? undefined }">
                    {{ item.rain_level ?? '—' }}
                  </span>
                </td>
              </tr>
              <tr v-if="!events.length">
                <td colspan="8" class="empty">当前阈值下没有事件</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="table-note text-muted">
          「—」表示该日期由日值接口回填，原始数据不含小时明细（详见 docs/PLAN.md 第 18.3 节）。
          建议重点回放 <strong>2026-08-10</strong> 过程：可到
          <RouterLink to="/spatial">空间分布</RouterLink> 模块用时间轴查看其演变。
        </p>
      </div>
    </section>

    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">全部日降水等级分布</div>
        <span class="panel__subtitle">3 年全量 · GB/T 28592-2012</span>
      </header>
      <div class="panel__body">
        <LevelDonutChart :items="levels" height="280px" />
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

.panel--info {
  border-color: rgba(245, 215, 110, 0.3);
}

.panel--info .panel__title::before {
  background: linear-gradient(180deg, #f5d76e, #f39c12);
}

.note {
  font-size: 13px;
  line-height: 1.75;
  color: var(--text-1);
}

.note + .note {
  margin-top: 8px;
}

code {
  padding: 1px 5px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  background: rgba(120, 170, 255, 0.12);
  border-radius: 4px;
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

.panel__body--flush {
  padding: 0;
}

.table-wrap {
  max-height: 480px;
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

.table tbody tr:hover {
  background: rgba(120, 170, 255, 0.05);
}

.table .num {
  text-align: right;
}

.table .strong {
  color: var(--accent-light);
  font-weight: 650;
}

.rank-col {
  width: 40px;
  color: var(--text-3);
}

.level {
  display: inline-block;
  padding: 1px 8px;
  font-size: 11px;
  color: #fff;
  border-radius: 999px;
}

.empty {
  padding: 24px;
  text-align: center;
  color: var(--text-2);
}

.table-note {
  padding: 10px 14px 14px;
  font-size: 12px;
  line-height: 1.7;
}
</style>
