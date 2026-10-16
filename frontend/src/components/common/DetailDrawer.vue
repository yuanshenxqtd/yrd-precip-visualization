<script setup lang="ts">
/**
 * 点位下钻抽屉（Details-on-demand）。
 *
 * 这是数据可视化交互任务清单里缺失的那一项：
 * 界面上看到的任何数字都应该能追问「它是怎么来的」。
 * 点地图区划、点位矩阵方块、排行柱子都会唤起它，
 * 抽屉里给出该点位的逐小时/逐日原始值与汇总口径。
 *
 * 抽屉只在 AppLayout 挂载一次，状态由 useDetailStore 持有。
 */
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'

import DailyTrendChart from '@/components/charts/DailyTrendChart.vue'
import HourlyTrendChart from '@/components/charts/HourlyTrendChart.vue'
import LevelDonutChart from '@/components/charts/LevelDonutChart.vue'
import NavIcon from '@/components/common/NavIcon.vue'
import { useDetailStore } from '@/stores/detail'
import { useFilterStore } from '@/stores/filter'
import { formatNumber, shortTime } from '@/utils/format'

const detail = useDetailStore()
const filter = useFilterStore()

const WINDOWS = [
  { hours: 24, days: 7, label: '24h / 7天' },
  { hours: 48, days: 30, label: '48h / 30天' },
  { hours: 168, days: 90, label: '7天 / 90天' },
]

const data = computed(() => detail.detail)

/** 逐日序列转成图表需要的形状（max = 当日最大小时雨强） */
const dailyPoints = computed(() =>
  (data.value?.daily ?? []).map((d) => ({ time: d.time, value: d.value, max: d.max ?? 0 })),
)

const hourlyPoints = computed(() => data.value?.hourly ?? [])

const activeWindow = computed(() =>
  WINDOWS.findIndex(
    (w) => w.hours === detail.windowHours && w.days === detail.windowDays,
  ),
)

function switchWindow(index: number): void {
  const w = WINDOWS[index]
  if (w) void detail.setWindow(w.hours, w.days)
}

/** 把该点位设为全局筛选目标（后续跨模块联动的入口） */
function focusRegion(): void {
  if (detail.adcode) filter.select(detail.adcode)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && detail.visible) detail.close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

// 打开时禁止背景滚动
watch(
  () => detail.visible,
  (visible) => {
    document.body.style.overflow = visible ? 'hidden' : ''
  },
)
onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="detail.visible" class="drawer-root">
        <div class="drawer__mask" @click="detail.close()" />

        <aside class="drawer" role="dialog" aria-modal="true" :aria-label="`${detail.name} 详情`">
          <!-- 头部 -->
          <header class="drawer__head">
            <div class="drawer__title-wrap">
              <h3 class="drawer__title">{{ detail.name || '加载中…' }}</h3>
              <div class="drawer__meta">
                <span v-if="data" class="badge">{{ data.region.province }}</span>
                <span v-if="data" class="badge badge--dim">
                  {{ data.region.level === 'district' ? '区级' : '市级' }}
                </span>
                <span v-if="data" class="text-mono text-muted">{{ data.region.adcode }}</span>
                <span v-if="data" class="text-mono text-muted">
                  {{ data.region.lon }}, {{ data.region.lat }}
                </span>
              </div>
            </div>
            <button class="icon-btn" title="关闭（Esc）" @click="detail.close()">
              <NavIcon name="close" />
            </button>
          </header>

          <div class="drawer__body">
            <p v-if="detail.error" class="notice notice--error">{{ detail.error }}</p>
            <div v-else-if="detail.loading && !data" class="drawer__loading">正在加载点位明细…</div>

            <template v-if="data">
              <!-- 汇总指标 -->
              <section class="block">
                <div class="block__title">
                  汇总指标
                  <span class="block__hint">窗口：近 {{ data.hours }} 小时 / {{ data.days }} 天</span>
                </div>
                <div class="stats">
                  <div class="stat">
                    <span class="stat__k">最新时刻降水</span>
                    <span class="stat__v text-mono">{{ formatNumber(data.summary.latest_value, 1) }}<em>mm</em></span>
                    <span class="stat__h text-mono">{{ shortTime(data.summary.latest_time) }}</span>
                  </div>
                  <div class="stat">
                    <span class="stat__k">{{ data.hours }}h 累计</span>
                    <span class="stat__v text-mono">{{ formatNumber(data.summary.sum_hours, 1) }}<em>mm</em></span>
                    <span class="stat__h">最大小时 {{ formatNumber(data.summary.peak_hour_value, 1) }}</span>
                  </div>
                  <div class="stat">
                    <span class="stat__k">{{ data.days }} 天累计</span>
                    <span class="stat__v text-mono">{{ formatNumber(data.summary.sum_days, 1) }}<em>mm</em></span>
                    <span class="stat__h">{{ data.summary.rain_days }} 天有雨</span>
                  </div>
                  <div class="stat">
                    <span class="stat__k">窗口内最大日</span>
                    <span class="stat__v text-mono">{{ formatNumber(data.summary.peak_day_value, 1) }}<em>mm</em></span>
                    <span class="stat__h text-mono">{{ data.summary.peak_day_date ?? '—' }}</span>
                  </div>
                  <div class="stat">
                    <span class="stat__k">历史最大日</span>
                    <span class="stat__v text-mono accent">{{ formatNumber(data.summary.historic_max, 1) }}<em>mm</em></span>
                    <span class="stat__h text-mono">{{ data.summary.historic_max_date ?? '—' }}</span>
                  </div>
                  <div class="stat">
                    <span class="stat__k">数据记录</span>
                    <span class="stat__v text-mono">{{ formatNumber(data.summary.total_records) }}<em>条</em></span>
                    <span class="stat__h text-mono">自 {{ shortTime(data.summary.first_time) }}</span>
                  </div>
                </div>
              </section>

              <!-- 窗口切换 -->
              <section class="block">
                <div class="block__title">
                  统计窗口
                  <div class="seg">
                    <button
                      v-for="(w, i) in WINDOWS"
                      :key="w.label"
                      class="seg__btn"
                      :class="{ 'seg__btn--active': activeWindow === i }"
                      @click="switchWindow(i)"
                    >
                      {{ w.label }}
                    </button>
                  </div>
                </div>
              </section>

              <!-- 逐小时 -->
              <section class="block">
                <div class="block__title">
                  逐小时降水
                  <span class="block__hint">{{ hourlyPoints.length }} 个整点</span>
                </div>
                <p v-if="!hourlyPoints.length" class="block__empty">该窗口无小时数据</p>
                <HourlyTrendChart v-else :points="hourlyPoints" height="180px" />
              </section>

              <!-- 逐日 -->
              <section class="block">
                <div class="block__title">
                  逐日降水
                  <span class="block__hint">柱=日累计，线=当日最大小时雨强</span>
                </div>
                <DailyTrendChart :points="dailyPoints" show-max height="200px" />
              </section>

              <!-- 等级分布 -->
              <section class="block">
                <div class="block__title">
                  历史降水等级分布
                  <span class="block__hint">GB/T 28592-2012</span>
                </div>
                <LevelDonutChart :items="data.levels" height="220px" />
              </section>

              <!-- 极值榜 -->
              <section class="block">
                <div class="block__title">
                  该点位历史极值
                  <span class="block__hint">Top {{ data.extremes.length }}</span>
                </div>
                <table class="mini-table">
                  <thead>
                    <tr>
                      <th>日期</th>
                      <th class="num">日累计</th>
                      <th class="num">最大小时</th>
                      <th>等级</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="e in data.extremes" :key="e.obs_date">
                      <td class="text-mono">{{ e.obs_date }}</td>
                      <td class="num text-mono">{{ formatNumber(e.precip_sum, 1) }}</td>
                      <td class="num text-mono">
                        {{ e.precip_max_hourly == null ? '—' : formatNumber(e.precip_max_hourly, 1) }}
                      </td>
                      <td>
                        <span class="level" :style="{ background: e.color ?? undefined }">
                          {{ e.rain_level ?? '—' }}
                        </span>
                      </td>
                    </tr>
                    <tr v-if="!data.extremes.length">
                      <td colspan="4" class="block__empty">暂无极值记录</td>
                    </tr>
                  </tbody>
                </table>
              </section>
            </template>
          </div>

          <!-- 底部 -->
          <footer v-if="data" class="drawer__foot">
            <button class="btn" @click="focusRegion">在全局筛选中聚焦该点位</button>
            <span class="drawer__foot-hint text-muted">
              数据来源：{{ data.region.name }} 采集点 · 56 个点位之一
            </span>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-root {
  position: fixed;
  inset: 0;
  z-index: 9000;
}

.drawer__mask {
  position: absolute;
  inset: 0;
  background: rgba(4, 8, 18, 0.62);
  backdrop-filter: blur(2px);
}

.drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  width: min(760px, 94vw);
  background: linear-gradient(160deg, #0d1730 0%, #0a1226 100%);
  border-left: 1px solid var(--panel-border);
  box-shadow: -16px 0 48px rgba(0, 0, 0, 0.5);
}

/* ---------- 头部 ---------- */
.drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--gap);
  padding: 16px 20px;
  border-bottom: 1px solid var(--panel-border);
}

.drawer__title {
  font-size: 17px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.drawer__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  font-size: 12px;
}

.badge {
  padding: 1px 8px;
  font-size: 11px;
  color: var(--accent-light);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
}

.badge--dim {
  color: var(--text-2);
  background: rgba(120, 170, 255, 0.06);
}

.icon-btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  color: var(--text-1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: color var(--transition), border-color var(--transition);
}

.icon-btn:hover {
  color: var(--text-0);
  border-color: var(--panel-border-hover);
}

/* ---------- 主体 ---------- */
.drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 20px;
  display: grid;
  gap: 18px;
  align-content: start;
}

.drawer__loading {
  padding: 60px 0;
  text-align: center;
  font-size: 13px;
  color: var(--text-2);
}

.block__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-0);
}

.block__hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-2);
}

.block__empty {
  padding: 14px 0;
  font-size: 12.5px;
  color: var(--text-2);
  text-align: center;
}

/* 汇总指标 */
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

@media (max-width: 640px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 9px 11px;
  background: rgba(120, 170, 255, 0.05);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.stat__k {
  font-size: 11px;
  color: var(--text-2);
}

.stat__v {
  font-size: 19px;
  font-weight: 650;
  color: var(--text-0);
}

.stat__v.accent {
  color: var(--warning);
}

.stat__v em {
  margin-left: 3px;
  font-size: 11px;
  font-style: normal;
  font-weight: 500;
  color: var(--text-2);
}

.stat__h {
  font-size: 10.5px;
  color: var(--text-3);
}

/* 分段按钮 */
.seg {
  display: inline-flex;
  padding: 2px;
  background: rgba(120, 170, 255, 0.07);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.seg__btn {
  padding: 3px 9px;
  font-size: 11.5px;
  color: var(--text-2);
  border-radius: 4px;
}

.seg__btn--active {
  color: var(--text-0);
  background: var(--accent-dim);
}

/* 迷你表格 */
.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.mini-table th,
.mini-table td {
  padding: 7px 10px;
  text-align: left;
  border-bottom: 1px solid rgba(120, 170, 255, 0.1);
}

.mini-table thead th {
  color: var(--text-2);
  font-weight: 500;
}

.mini-table .num {
  text-align: right;
}

.level {
  display: inline-block;
  padding: 1px 8px;
  font-size: 11px;
  color: #fff;
  border-radius: 999px;
}

/* ---------- 底部 ---------- */
.drawer__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  padding: 12px 20px;
  border-top: 1px solid var(--panel-border);
  background: rgba(9, 17, 34, 0.6);
}

.btn {
  padding: 7px 14px;
  font-size: 12.5px;
  color: var(--text-0);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.btn:hover {
  border-color: var(--panel-border-hover);
}

.drawer__foot-hint {
  font-size: 11.5px;
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

/* ---------- 过渡 ---------- */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 200ms ease;
}

.drawer-enter-active .drawer,
.drawer-leave-active .drawer {
  transition: transform 240ms cubic-bezier(0.22, 0.61, 0.36, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .drawer,
.drawer-leave-to .drawer {
  transform: translateX(100%);
}
</style>
