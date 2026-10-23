<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchRealtimeLatest, fetchTimespan } from '@/api'
import { describeError } from '@/api/client'
import FieldMap from '@/components/charts/FieldMap.vue'
import RainMap from '@/components/charts/RainMap.vue'
import TimeScrubber from '@/components/common/TimeScrubber.vue'
import { useAppStore } from '@/stores/app'
import { useDetailStore } from '@/stores/detail'
import { useFilterStore } from '@/stores/filter'
import type { MapFrame, MapPoint } from '@/types'
import { formatNumber, shiftHours, shortTime } from '@/utils/format'

const app = useAppStore()
const filter = useFilterStore()
const detail = useDetailStore()

/** 小时数据的起始时刻 —— 决定时间轴回放能往前拖多远 */
const hourlyStart = computed(() => app.meta?.hourly_start ?? null)

interface Preset {
  key: string
  label: string
  desc: string
  start: string
  end: string
}

/**
 * 预设时段。
 *
 * ⚠️ 时间轴回放依赖**小时数据**，而本项目的小时数据只回溯 1 年
 * （2025-09-07 起；更早的历史只有日数据，只能做日尺度统计）。
 * 因此这里选用的过程都落在小时数据覆盖区间内 —— 均已实测确认有帧返回。
 *
 * 第一个是库内最强的区域性过程，用于解决「答辩当日可能无降水」的问题
 * （见 docs/PLAN.md 风险 R1）。
 */
const PRESETS: Preset[] = [
  {
    key: 'event-2026-08-10',
    label: '2026-08-09~10 大暴雨过程',
    desc: '库内最强：全区单日合计 4,399.9 mm、56/56 点位有雨；台州 328.7 mm（特大暴雨）、苏州单小时 35.2 mm',
    start: '2026-08-09T00:00',
    end: '2026-08-10T23:00',
  },
  {
    key: 'event-2026-06-22',
    label: '2026-06-22 过程',
    desc: '梅雨期区域性降水：全区合计 1,622.6 mm，泰州 137.8 mm',
    start: '2026-06-21T12:00',
    end: '2026-06-22T23:00',
  },
  {
    key: 'event-2026-08-31',
    label: '2026-08-31 过程',
    desc: '局地强降水：南通 127.3 mm，最大小时 34.0 mm',
    start: '2026-08-30T12:00',
    end: '2026-08-31T23:00',
  },
  {
    key: 'recent-24h',
    label: '最近 24 小时',
    desc: '以库内最新实况时刻向前推 24 小时',
    start: '',
    end: '',
  },
]

const activeKey = ref(PRESETS[0].key)
const frames = ref<MapFrame[]>([])
const index = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const latestObs = ref<string | null>(null)
const maxFrames = ref(48)

const activePreset = computed(() => PRESETS.find((p) => p.key === activeKey.value) ?? PRESETS[0])
const currentFrame = computed<MapFrame | null>(() => frames.value[index.value] ?? null)
const frameLabel = computed(() => shortTime(currentFrame.value?.time))

const mapData = computed(() =>
  Object.entries(currentFrame.value?.values ?? {}).map(([adcode, v]) => ({
    adcode,
    name: filter.nameByAdcode[adcode] ?? adcode,
    value: Math.round((v ?? 0) * 10) / 10,
  })),
)

/**
 * 连续场模式下的站点覆盖层：用全局行政区划的经纬度补全每个站点的位置。
 * 保留站点圆点，是为了让使用者看得见「插值是从哪些实况点推出来的」——
 * 否则一片渐变会让人误以为是观测到的面状数据。
 */
const fieldMode = ref<'field' | 'region'>('field')

const fieldPoints = computed<MapPoint[]>(() => {
  const values = currentFrame.value?.values ?? {}
  return filter.monitored.map((region) => ({
    adcode: region.adcode,
    name: region.name,
    province: region.province,
    lon: region.lon,
    lat: region.lat,
    value: values[region.adcode] ?? 0,
    level: null,
    color: null,
  }))
})

const frameRanking = computed(() =>
  Object.entries(currentFrame.value?.values ?? {})
    .map(([adcode, v]) => ({
      adcode,
      name: filter.nameByAdcode[adcode] ?? adcode,
      value: Math.round((v ?? 0) * 10) / 10,
    }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 12),
)

const frameStats = computed(() => {
  const values = Object.values(currentFrame.value?.values ?? {}).filter(
    (v): v is number => (v ?? 0) > 0,
  )
  return {
    count: values.length,
    total: Math.round(values.reduce((sum, v) => sum + v, 0) * 10) / 10,
    max: values.length ? Math.max(...values) : 0,
  }
})

function resolveRange(): { start: string; end: string } {
  const preset = activePreset.value
  if (preset.key !== 'recent-24h') return { start: preset.start, end: preset.end }
  if (!latestObs.value) return { start: '', end: '' }
  return { start: shiftHours(latestObs.value, -23), end: latestObs.value }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    await filter.loadRegions()

    if (!latestObs.value) {
      const latest = await fetchRealtimeLatest()
      latestObs.value = latest.time
    }

    const { start, end } = resolveRange()
    if (!start || !end) {
      frames.value = []
      error.value = '缺少可用的实况时刻，请先采集一次数据'
      return
    }

    const data = await fetchTimespan({ start, end, max_frames: maxFrames.value })
    frames.value = data
    index.value = 0
    error.value = data.length ? null : '该时段没有实况数据'
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

async function selectPreset(key: string): Promise<void> {
  activeKey.value = key
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">空间分布</h2>
        <p class="page__desc">
          用分级设色地图呈现降水场的空间格局，并支持<strong>时间轴回放</strong>整场降水过程的演变。
          分级依据 GB/T 28592-2012（24 小时口径）。
          <br />
          <span class="text-muted">
            注：时间轴回放依赖小时数据，本项目小时数据回溯 1 年
            （{{ shortTime(hourlyStart) }} 起）；更早的历史仅有日数据，只能做日尺度统计。
          </span>
        </p>
      </div>
      <button class="btn" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <p v-if="error" class="notice notice--error">{{ error }}</p>

    <!-- 预设时段 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">选择时段</div>
        <span class="panel__subtitle">库内已确认的强降水过程可直接回放</span>
      </header>
      <div class="panel__body">
        <div class="presets">
          <button
            v-for="preset in PRESETS"
            :key="preset.key"
            class="preset"
            :class="{ 'preset--active': activeKey === preset.key }"
            @click="selectPreset(preset.key)"
          >
            <strong>{{ preset.label }}</strong>
            <em>{{ preset.desc }}</em>
          </button>
        </div>
        <p class="presets__note text-muted">
          共 {{ frames.length }} 帧，每帧间隔 1 小时。拖动时间轴或点击播放可查看降水场的移动与增强过程。
        </p>
      </div>
    </section>

    <!-- 地图 + 播放器 + 排行 -->
    <div class="spatial-main">
      <section class="panel">
        <header class="panel__header">
          <div class="panel__title">长三角降水场</div>
          <div class="controls">
            <div class="seg">
              <button
                class="seg__btn"
                :class="{ 'seg__btn--active': fieldMode === 'field' }"
                title="连续插值场：看雨带走向与区域内强中心"
                @click="fieldMode = 'field'"
              >
                连续场
              </button>
              <button
                class="seg__btn"
                :class="{ 'seg__btn--active': fieldMode === 'region' }"
                title="按行政区划整体着色：看哪个市下了多少"
                @click="fieldMode = 'region'"
              >
                区域着色
              </button>
            </div>
            <span class="panel__subtitle">{{ frameLabel }}</span>
          </div>
        </header>
        <div class="panel__body">
          <FieldMap
            v-if="fieldMode === 'field'"
            :time="currentFrame?.time ?? null"
            :points="fieldPoints"
            height="470px"
            @select="detail.open($event)"
          />
          <RainMap v-else :data="mapData" height="470px" @select="detail.open($event)" />
          <div class="player">
            <TimeScrubber
              v-model="index"
              :total="frames.length"
              :label="frameLabel"
              :autoplay="app.demoMode"
            />
          </div>
        </div>
      </section>

      <div class="spatial-side">
        <section class="panel">
          <header class="panel__header">
            <div class="panel__title">本帧统计</div>
          </header>
          <div class="panel__body">
            <dl class="kv">
              <div><dt>时刻</dt><dd class="text-mono">{{ frameLabel }}</dd></div>
              <div><dt>有雨点位</dt><dd class="text-mono">{{ frameStats.count }} / 56</dd></div>
              <div><dt>全区合计</dt><dd class="text-mono">{{ formatNumber(frameStats.total, 1) }} mm</dd></div>
              <div><dt>该帧最大</dt><dd class="text-mono">{{ formatNumber(frameStats.max, 1) }} mm</dd></div>
            </dl>
          </div>
        </section>

        <section class="panel">
          <header class="panel__header">
            <div class="panel__title">本帧降水排行</div>
            <span class="panel__subtitle">前 12 名 · 点击查看明细</span>
          </header>
          <div class="panel__body">
            <p v-if="!frameRanking.length" class="empty">该时刻全区无降水</p>
            <ol v-else class="rank">
              <li v-for="(item, i) in frameRanking" :key="item.adcode">
                <button type="button" class="rank__row" @click="detail.open(item.adcode)">
                  <span class="rank__no" :class="{ 'rank__no--top': i < 3 }">{{ i + 1 }}</span>
                  <span class="rank__name">{{ item.name }}</span>
                  <span class="rank__value text-mono">{{ formatNumber(item.value, 1) }}</span>
                </button>
              </li>
            </ol>
          </div>
        </section>
      </div>
    </div>
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

.presets {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--gap-sm);
}

.preset {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 11px 14px;
  text-align: left;
  color: var(--text-1);
  background: rgba(120, 170, 255, 0.05);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background var(--transition);
}

.preset:hover {
  border-color: var(--panel-border-hover);
}

.preset--active {
  color: var(--text-0);
  background: var(--accent-dim);
  border-color: var(--accent);
}

.preset strong {
  font-size: 13px;
  font-weight: 600;
}

.preset em {
  font-size: 11.5px;
  font-style: normal;
  line-height: 1.5;
  color: var(--text-2);
}

.presets__note {
  margin-top: var(--gap-sm);
  font-size: 12px;
}

.spatial-main {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(260px, 1fr);
  gap: var(--gap);
}

@media (max-width: 1280px) {
  .spatial-main {
    grid-template-columns: minmax(0, 1fr);
  }
}

.spatial-side {
  display: grid;
  gap: var(--gap);
  align-content: start;
}

.player {
  margin-top: var(--gap-sm);
  padding-top: var(--gap-sm);
  border-top: 1px dashed rgba(120, 170, 255, 0.14);
}

.kv {
  margin: 0;
  display: grid;
  gap: 8px;
  font-size: 13px;
}

.kv > div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding-bottom: 7px;
  border-bottom: 1px dashed rgba(120, 170, 255, 0.12);
}

.kv > div:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.kv dt {
  color: var(--text-2);
}

.kv dd {
  margin: 0;
  color: var(--text-0);
}

.rank {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 5px;
}

.rank__row {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 3px 5px;
  font-size: 12.5px;
  color: inherit;
  text-align: left;
  border-radius: var(--radius-sm);
  transition: background var(--transition);
  cursor: pointer;
}

.rank__row:hover {
  background: rgba(120, 170, 255, 0.09);
}

.rank__row:focus-visible {
  outline: 2px solid var(--accent-light);
  outline-offset: 0;
}

.rank__no {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  font-size: 10px;
  color: var(--text-2);
  background: rgba(120, 170, 255, 0.08);
  border-radius: 4px;
}

.rank__no--top {
  color: #06121f;
  font-weight: 700;
  background: linear-gradient(180deg, var(--accent-light), var(--accent));
}

.rank__value {
  text-align: right;
  color: var(--text-0);
}

.empty {
  padding: 14px 0;
  font-size: 12.5px;
  color: var(--text-2);
  text-align: center;
}
/* 连续场 / 区域着色 切换 */
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
</style>
