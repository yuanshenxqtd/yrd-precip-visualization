<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import NavIcon from '@/components/common/NavIcon.vue'
import { useAppStore } from '@/stores/app'
import { relativeTime, shortTime } from '@/utils/format'

const app = useAppStore()
const route = useRoute()

const moduleTitle = computed(() => (route.meta.title as string) ?? '总览大屏')

/** 页面时钟：大屏类界面需要实时感 */
const now = ref(new Date())
let timer: number | undefined
onMounted(() => {
  timer = window.setInterval(() => (now.value = new Date()), 1000)
})
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})

const clock = computed(() => {
  const d = now.value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})

const statusText = computed(() => app.freshnessLabel)

const statusTone = computed(() => {
  switch (app.freshness) {
    case 'ok':
      return 'ok'
    case 'stale':
      return 'warning'
    case 'expired':
    case 'failed':
    case 'offline':
      return 'danger'
    default:
      return 'idle'
  }
})
</script>

<template>
  <header class="header">
    <div class="header__left">
      <button class="icon-btn" title="折叠 / 展开导航" @click="app.toggleSidebar()">
        <NavIcon name="menu" />
      </button>
      <div>
        <div class="header__title">{{ moduleTitle }}</div>
        <div class="header__sub" :title="app.freshnessHint">
          数据时刻
          <span class="text-mono">{{ shortTime(app.latestObsTime) }}</span>
          <span class="header__dot">·</span>
          <span :class="{ 'header__age--warn': app.freshnessWarned }">{{ app.ageText }}</span>
          <span class="header__dot">·</span>
          同步于 {{ relativeTime(app.lastSyncAt) }}
        </div>
      </div>
    </div>

    <div class="header__right">
      <span class="pill" :class="`pill--${statusTone}`" :title="app.freshnessHint">
        <i class="pill__dot"></i>{{ statusText }}
      </span>
      <span class="header__clock text-mono">{{ clock }}</span>
      <button class="icon-btn" title="切换演示模式（隐藏导航、进入全屏）" @click="app.toggleDemo()">
        <NavIcon name="present" />
      </button>
      <button class="icon-btn" :disabled="app.loading" title="刷新数据" @click="app.refresh()">
        <NavIcon name="refresh" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap);
  height: var(--header-height);
  padding: 0 var(--gap);
  flex: 0 0 var(--header-height);
  background: rgba(9, 17, 34, 0.72);
  border-bottom: 1px solid var(--panel-border);
  backdrop-filter: blur(10px);
}

.header__left,
.header__right {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.header__title {
  font-size: 15px;
  font-weight: 640;
  letter-spacing: 0.02em;
}

.header__sub {
  font-size: 12px;
  color: var(--text-2);
}

.header__dot {
  margin: 0 6px;
  color: var(--text-3);
}

/* 数据偏旧/过期时，把「多久以前」标成警告色 */
.header__age--warn {
  color: var(--warning);
  font-weight: 600;
}

.header__clock {
  font-size: 13px;
  color: var(--text-1);
  letter-spacing: 0.04em;
}

.icon-btn {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  color: var(--text-1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: color var(--transition), border-color var(--transition);
}

.icon-btn:hover:not(:disabled) {
  color: var(--text-0);
  border-color: var(--panel-border-hover);
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  font-size: 12px;
  border-radius: 999px;
  border: 1px solid var(--panel-border);
  color: var(--text-1);
}

.pill__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-2);
}

.pill--ok {
  color: #8ff0b5;
  border-color: rgba(46, 204, 113, 0.35);
  background: rgba(46, 204, 113, 0.1);
}

.pill--ok .pill__dot {
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
}

.pill--warning {
  color: var(--warning);
  border-color: rgba(245, 215, 110, 0.35);
  background: rgba(245, 215, 110, 0.1);
}

.pill--warning .pill__dot {
  background: var(--warning);
}

.pill--danger {
  color: #ff9d94;
  border-color: rgba(231, 76, 60, 0.4);
  background: rgba(231, 76, 60, 0.12);
}

.pill--danger .pill__dot {
  background: var(--danger);
}

@media (max-width: 900px) {
  .header__clock {
    display: none;
  }
}
</style>
