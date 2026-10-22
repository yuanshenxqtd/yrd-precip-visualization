<script setup lang="ts">
/**
 * 读图要点（自动摘要）。
 *
 * 数据可视化流水线的最后一环是「知识、灵感」—— 但这一步现在仍要用户自己从图里读。
 * 这个组件把已经算好的**结构化事实**组织成几句话，直接告诉用户：
 * 现在什么情况、最极端的是谁、跟之前比如何、历史上算不算强。
 *
 * 措辞上刻意避免"评价性"用词（如"严重""罕见"），只用可核对的事实与相对比较，
 * 因为数据规模有限（小时数据仅 1 年），过度定性会让结论失去依据。
 */
import { computed } from 'vue'

import type { OverviewHighlights } from '@/types'
import { formatNumber, hhmm } from '@/utils/format'

const props = defineProps<{ data: OverviewHighlights | null }>()
const emit = defineEmits<{ select: [string] }>()

interface Line {
  key: string
  label: string
  /** 主句 */
  text: string
  /** 次要说明（弱化显示） */
  note?: string
  /** 可跳转的点位（点击后聚焦并下钻） */
  action?: { adcode: string; name: string }
}

const lines = computed<Line[]>(() => {
  const d = props.data
  if (!d || !d.current) return []

  const cur = d.current
  const out: Line[] = []

  // ① 当前态势
  if (cur.dry) {
    out.push({
      key: 'current',
      label: '当前',
      text: `近 ${d.hours} 小时全区无降水`,
      note: `${cur.points_total} 个点位累计均为 0`,
    })
  } else {
    out.push({
      key: 'current',
      label: '当前',
      text: `近 ${d.hours} 小时全区累计 ${formatNumber(cur.total_mm, 1)} mm`,
      note: `${cur.wet_points} / ${cur.points_total} 个点位出现降水`,
    })
  }

  // ② 极值
  if (cur.wettest) {
    const w = cur.wettest
    const peakNote = cur.peak
      ? `最强单小时 ${formatNumber(cur.peak.value, 1)} mm（${cur.peak.name ?? ''} ${hhmm(cur.peak.time)}）`
      : undefined
    out.push({
      key: 'peak',
      label: '极值',
      text: `累计最多 ${w.name ?? ''} ${formatNumber(w.value, 1)} mm`,
      note: peakNote,
      action: w.adcode && w.name ? { adcode: w.adcode, name: w.name } : undefined,
    })
  }

  // ③ 与前一窗口比较
  const prev = d.previous
  if (prev) {
    if (prev.change_pct === null) {
      out.push({
        key: 'change',
        label: '对比',
        text: `前 ${d.hours} 小时全区无降水，本次无可比基数`,
      })
    } else {
      const up = prev.change_pct > 0
      out.push({
        key: 'change',
        label: '对比',
        text: `较前 ${d.hours} 小时${up ? '偏多' : '偏少'} ${Math.abs(prev.change_pct).toFixed(1)}%`,
        note: `前值 ${formatNumber(prev.total_mm, 1)} mm`,
      })
    }
  }

  // ④ 历史定位
  const best = d.strongest_day
  if (best) {
    const peak = best.peak
    out.push({
      key: 'strongest',
      label: '历史',
      text: `近 ${d.window_days} 天最强的一天是 ${best.date}`,
      note: peak
        ? `全区合计 ${formatNumber(best.total_mm, 1)} mm；${peak.name ?? ''} ${formatNumber(peak.value, 1)} mm${peak.level ? `（${peak.level}）` : ''}`
        : `全区合计 ${formatNumber(best.total_mm, 1)} mm`,
      action: peak?.adcode && peak.name ? { adcode: peak.adcode, name: peak.name } : undefined,
    })
  }

  return out
})

const rainDayNote = computed(() => {
  const d = props.data
  if (!d || !d.rain_days) return ''
  return `其中 ${d.rain_days} 天出现降水`
})
</script>

<template>
  <section class="insight">
    <header class="insight__head">
      <span class="insight__title">
        <i class="insight__spark" aria-hidden="true">✦</i>
        读图要点
      </span>
      <span class="insight__sub text-muted">
        由当前数据自动生成 · <span class="text-mono">{{ rainDayNote || '仅供参考' }}</span>
      </span>
    </header>

    <p v-if="!lines.length" class="insight__empty">正在生成要点…</p>

    <ul v-else class="insight__list">
      <li v-for="line in lines" :key="line.key" class="insight__row">
        <span class="insight__label">{{ line.label }}</span>
        <span class="insight__body">
          <span class="insight__text">{{ line.text }}</span>
          <span v-if="line.note" class="insight__note">{{ line.note }}</span>
        </span>
        <button
          v-if="line.action"
          class="insight__action"
          :title="`聚焦并查看 ${line.action.name} 详情`"
          @click="emit('select', line.action.adcode)"
        >
          {{ line.action.name }} ›
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.insight {
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(58, 160, 224, 0.1), rgba(58, 160, 224, 0.03));
  border: 1px solid rgba(58, 160, 224, 0.24);
  border-radius: var(--radius);
}

.insight__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  margin-bottom: 9px;
}

.insight__title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 650;
  color: var(--accent-light);
  letter-spacing: 0.02em;
}

.insight__spark {
  font-style: normal;
  font-size: 12px;
}

.insight__sub {
  font-size: 11px;
}

.insight__empty {
  font-size: 12.5px;
  color: var(--text-2);
}

.insight__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}

.insight__row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 10px;
  font-size: 13px;
  line-height: 1.55;
}

.insight__label {
  padding: 1px 0;
  font-size: 11px;
  color: var(--text-2);
  text-align: center;
  background: rgba(120, 170, 255, 0.1);
  border-radius: 4px;
}

.insight__body {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.insight__text {
  color: var(--text-0);
}

.insight__note {
  font-size: 12px;
  color: var(--text-2);
}

.insight__action {
  padding: 2px 9px;
  font-size: 11.5px;
  color: var(--accent-light);
  white-space: nowrap;
  background: rgba(58, 160, 224, 0.14);
  border: 1px solid rgba(58, 160, 224, 0.3);
  border-radius: 999px;
  transition: background var(--transition), border-color var(--transition);
}

.insight__action:hover {
  background: rgba(58, 160, 224, 0.26);
  border-color: var(--accent);
}

@media (max-width: 720px) {
  .insight__row {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .insight__action {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
