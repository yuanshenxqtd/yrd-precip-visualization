<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { exportCsvUrl, fetchCollectLogs, triggerCollect } from '@/api'
import { describeError } from '@/api/client'
import NavIcon from '@/components/common/NavIcon.vue'
import { useAppStore } from '@/stores/app'
import type { CollectLog } from '@/types'
import { formatNumber, shortDateTime } from '@/utils/format'

const app = useAppStore()
const logs = ref<CollectLog[]>([])
const loading = ref(false)
const collecting = ref(false)
const message = ref<string | null>(null)
const error = ref<string | null>(null)

const quality = computed(() => app.quality)

const collectRate = computed(() => {
  const q = quality.value
  if (!q || !q.collect_total) return 0
  return Math.round((q.collect_success / q.collect_total) * 1000) / 10
})

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    logs.value = await fetchCollectLogs({ limit: 30 })
    error.value = null
  } catch (err) {
    error.value = describeError(err)
  } finally {
    loading.value = false
  }
}

async function refreshAll(): Promise<void> {
  await Promise.all([app.refresh(), loadLogs()])
}

async function collectNow(): Promise<void> {
  collecting.value = true
  message.value = null
  error.value = null
  try {
    const result = await triggerCollect(3)
    if (result.status === 'success') {
      message.value = `采集成功：写入 ${formatNumber(result.rows_written)} 行（新增 ${formatNumber(result.rows_inserted)}），耗时 ${result.elapsed_seconds}s。${result.message ?? ''}`
    } else {
      error.value = `采集失败：${result.message ?? '未知原因'}`
    }
    await refreshAll()
  } catch (err) {
    error.value = describeError(err)
  } finally {
    collecting.value = false
  }
}

function statusTone(status: string): string {
  if (status === 'success') return 'ok'
  if (status === 'failed') return 'bad'
  return 'run'
}

onMounted(refreshAll)
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">数据管理</h2>
        <p class="page__desc">
          数据源状态、采集审计日志、数据质量报告与 CSV 导出。
          质量指标（缺测率、时间覆盖率、采集成功率）是论文「数据真实性与可用性」一节的直接证据。
        </p>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="refreshAll">刷新</button>
        <button class="btn btn--primary" :disabled="collecting" @click="collectNow">
          <NavIcon name="play" />
          {{ collecting ? '采集中…' : '立即采集一次' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="notice notice--error">{{ error }}</p>
    <p v-if="message" class="notice notice--ok">{{ message }}</p>

    <!-- 数据质量 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">数据质量报告</div>
        <span class="panel__subtitle">来自 /api/admin/quality</span>
      </header>
      <div class="panel__body">
        <div class="quality">
          <div class="quality__item">
            <span class="quality__label">时间覆盖率</span>
            <span class="quality__value text-mono quality__value--ok">{{ quality?.coverage_pct ?? '—' }}%</span>
            <span class="quality__hint">
              {{ quality?.distinct_hours ?? '—' }} / {{ quality?.expected_hours ?? '—' }} 个整点
            </span>
          </div>
          <div class="quality__item">
            <span class="quality__label">缺测率</span>
            <span class="quality__value text-mono quality__value--ok">{{ quality?.hourly_null_pct ?? '—' }}%</span>
            <span class="quality__hint">{{ quality?.hourly_null ?? '—' }} 条 NULL</span>
          </div>
          <div class="quality__item">
            <span class="quality__label">缺失整点数</span>
            <span class="quality__value text-mono">{{ quality?.missing_hours ?? '—' }}</span>
            <span class="quality__hint">0 表示无缺口</span>
          </div>
          <div class="quality__item">
            <span class="quality__label">采集成功率</span>
            <span class="quality__value text-mono">{{ collectRate }}%</span>
            <span class="quality__hint">
              {{ quality?.collect_success ?? '—' }} 成功 / {{ quality?.collect_failed ?? '—' }} 失败
            </span>
          </div>
          <div class="quality__item">
            <span class="quality__label">实况 / 预报</span>
            <span class="quality__value text-mono">
              {{ quality ? formatNumber(quality.hourly_observed_rows) : '—' }}
            </span>
            <span class="quality__hint">预报 {{ quality ? formatNumber(quality.hourly_forecast_rows) : '—' }} 条</span>
          </div>
          <div class="quality__item">
            <span class="quality__label">日汇总明细</span>
            <span class="quality__value text-mono">{{ quality ? formatNumber(quality.daily_with_detail) : '—' }}</span>
            <span class="quality__hint">
              另有 {{ quality ? formatNumber(quality.daily_without_detail) : '—' }} 天仅有日值（历史回填）
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据源状态 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">数据源状态</div>
        <span class="panel__subtitle">来自 /api/meta</span>
      </header>
      <div class="panel__body">
        <dl class="kv">
          <div><dt>数据源</dt><dd>Open-Meteo（ECMWF ERA5 / ERA5-Land，CC BY 4.0）</dd></div>
          <div><dt>采集点 / 行政区划</dt><dd class="text-mono">{{ app.meta?.points_total ?? '—' }} / {{ app.meta?.regions_total ?? '—' }}</dd></div>
          <div><dt>小时记录</dt><dd class="text-mono">{{ app.meta ? formatNumber(app.meta.hourly_rows) : '—' }}</dd></div>
          <div><dt>日汇总记录</dt><dd class="text-mono">{{ app.meta ? formatNumber(app.meta.daily_rows) : '—' }}</dd></div>
          <div><dt>小时数据范围</dt><dd class="text-mono">{{ app.meta?.hourly_start ?? '—' }} ~ {{ app.meta?.hourly_end ?? '—' }}</dd></div>
          <div><dt>日数据范围</dt><dd class="text-mono">{{ app.meta?.daily_start ?? '—' }} ~ {{ app.meta?.daily_end ?? '—' }}</dd></div>
          <div><dt>最近采集</dt><dd class="text-mono">{{ app.meta?.last_collect_at ?? '—' }} · {{ app.meta?.last_collect_status ?? '—' }}</dd></div>
          <div><dt>数据库初始化</dt><dd class="text-mono">{{ app.meta?.db_initialized_at ?? '—' }}</dd></div>
        </dl>
      </div>
    </section>

    <!-- 采集日志 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">采集审计日志</div>
        <span class="panel__subtitle">最近 30 条 · 失败也会留痕</span>
      </header>
      <div class="panel__body panel__body--flush">
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>#</th>
                <th>模式</th>
                <th>状态</th>
                <th class="num">点位数</th>
                <th class="num">写入</th>
                <th class="num">新增</th>
                <th>开始</th>
                <th>结束</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in logs" :key="log.id">
                <td class="text-mono">{{ log.id }}</td>
                <td>{{ log.mode }}</td>
                <td><span class="tag" :class="`tag--${statusTone(log.status)}`">{{ log.status }}</span></td>
                <td class="num text-mono">{{ log.points_total }}</td>
                <td class="num text-mono">{{ formatNumber(log.rows_upserted) }}</td>
                <td class="num text-mono">{{ formatNumber(log.gap_filled_hours) }}</td>
                <td class="text-mono">{{ shortDateTime(log.started_at) }}</td>
                <td class="text-mono">{{ shortDateTime(log.finished_at) }}</td>
              </tr>
              <tr v-if="!logs.length">
                <td colspan="8" class="empty">暂无采集记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 导出 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">数据导出</div>
        <span class="panel__subtitle">流式导出，避免大结果集占用内存</span>
      </header>
      <div class="panel__body">
        <div class="exports">
          <a class="btn" :href="exportCsvUrl({ kind: 'daily' })" download>
            <NavIcon name="download" /> 导出日数据 CSV
          </a>
          <a class="btn" :href="exportCsvUrl({ kind: 'hourly', start: '2026-09-01T00:00' })" download>
            <NavIcon name="download" /> 导出小时数据 CSV（9 月起）
          </a>
          <a class="btn" :href="exportCsvUrl({ kind: 'daily', adcode: '320500' })" download>
            <NavIcon name="download" /> 导出苏州市日数据
          </a>
        </div>
        <p class="export-hint text-muted">
          CSV 带 UTF-8 BOM，可直接用 Excel 打开；字段包含行政区划代码、名称、省份、时间、降水量、等级。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  gap: var(--gap-sm);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  font-size: 13px;
  color: var(--text-0);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background var(--transition);
}

.btn:hover:not(:disabled) {
  border-color: var(--panel-border-hover);
  background: rgba(58, 160, 224, 0.2);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--primary {
  color: #04121e;
  font-weight: 600;
  background: linear-gradient(180deg, var(--accent-light), var(--accent));
  border-color: transparent;
}

.btn--primary:hover:not(:disabled) {
  background: linear-gradient(180deg, #9adcfb, var(--accent));
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

.notice--ok {
  color: #b6f5cf;
  background: rgba(46, 204, 113, 0.12);
  border: 1px solid rgba(46, 204, 113, 0.3);
}

.quality {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: var(--gap);
}

.quality__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  background: rgba(120, 170, 255, 0.05);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.quality__label {
  font-size: 12px;
  color: var(--text-2);
}

.quality__value {
  font-size: 22px;
  font-weight: 650;
}

.quality__value--ok {
  color: var(--success);
}

.quality__hint {
  font-size: 11px;
  color: var(--text-3);
}

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
  color: var(--text-2);
  flex: 0 0 auto;
}

.kv dd {
  margin: 0;
  text-align: right;
  color: var(--text-0);
  word-break: break-all;
}

.panel__body--flush {
  padding: 0;
}

.table-wrap {
  max-height: 420px;
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
  z-index: 1;
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

.empty {
  padding: 24px;
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

.tag--run {
  color: var(--warning);
  background: rgba(245, 215, 110, 0.14);
}

.exports {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.export-hint {
  margin-top: var(--gap-sm);
  font-size: 12px;
}
</style>
