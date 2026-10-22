<script setup lang="ts">
/**
 * 演示模式浮动导航条。
 *
 * 演示模式会隐藏侧边栏与页头，把整屏让给内容 —— 但那样就没有导航了。
 * 这条细窄的浮动条补回三件事：
 *   1. 模块切换（复用路由表，与侧边栏同一份数据）
 *   2. 数据时效指示（页头被隐藏了，这里保留一个圆点）
 *   3. 全屏 / 退出
 *
 * 放在底部居中，尽量不遮挡图表标题与图例。
 */
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import { routes } from '@/router'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const route = useRoute()

const items = computed(() =>
  routes
    .filter((r) => r.meta?.title && typeof r.path === 'string' && r.path.startsWith('/'))
    .map((r) => ({ path: r.path, title: r.meta!.title as string })),
)

const currentPath = computed(() => route.path)

const tone = computed(() => {
  switch (app.freshness) {
    case 'ok':
      return 'ok'
    case 'stale':
      return 'warn'
    case 'expired':
    case 'failed':
    case 'offline':
      return 'danger'
    default:
      return 'idle'
  }
})

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') void app.exitDemo()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <nav class="pbar" aria-label="演示模式导航">
    <span class="pbar__status" :class="`pbar__status--${tone}`" :title="app.freshnessHint">
      <i class="pbar__dot"></i>
      <span class="pbar__status-text">{{ app.freshnessLabel }}</span>
    </span>

    <span class="pbar__sep"></span>

    <RouterLink
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      class="pbar__link"
      :class="{ 'pbar__link--active': currentPath === item.path }"
    >
      {{ item.title }}
    </RouterLink>

    <span class="pbar__sep"></span>

    <button class="pbar__btn" :title="app.isFullscreen ? '退出全屏' : '进入全屏'" @click="app.toggleFullscreen()">
      {{ app.isFullscreen ? '⤡' : '⤢' }}
    </button>
    <button class="pbar__btn pbar__btn--exit" title="退出演示模式（Esc）" @click="app.exitDemo()">
      退出演示
    </button>
  </nav>
</template>

<style scoped>
.pbar {
  position: fixed;
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
  z-index: 8000;
  display: flex;
  align-items: center;
  gap: 2px;
  max-width: calc(100vw - 24px);
  padding: 6px 10px;
  overflow-x: auto;
  font-size: 12.5px;
  background: rgba(9, 17, 34, 0.92);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(12px);
  scrollbar-width: none;
}

.pbar::-webkit-scrollbar {
  display: none;
}

/* ---------- 时效指示灯 ---------- */
.pbar__status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  color: var(--text-2);
  white-space: nowrap;
}

.pbar__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-2);
}

.pbar__status--ok .pbar__dot {
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
}

.pbar__status--warn .pbar__dot {
  background: var(--warning);
}

.pbar__status--danger .pbar__dot {
  background: var(--danger);
}

.pbar__status--warn .pbar__status-text {
  color: var(--warning);
}

.pbar__status--danger .pbar__status-text {
  color: #ff9d94;
}

/* ---------- 分隔 ---------- */
.pbar__sep {
  width: 1px;
  height: 16px;
  margin: 0 5px;
  flex: 0 0 auto;
  background: var(--panel-border);
}

/* ---------- 模块切换 ---------- */
.pbar__link {
  padding: 4px 11px;
  color: var(--text-1);
  white-space: nowrap;
  border-radius: 999px;
  transition: color var(--transition), background var(--transition);
}

.pbar__link:hover {
  color: var(--text-0);
  background: rgba(120, 170, 255, 0.1);
}

.pbar__link--active {
  color: #04121e;
  font-weight: 600;
  background: linear-gradient(180deg, var(--accent-light), var(--accent));
}

/* ---------- 按钮 ---------- */
.pbar__btn {
  display: grid;
  place-items: center;
  min-width: 28px;
  height: 26px;
  padding: 0 8px;
  font-size: 12px;
  color: var(--text-1);
  border-radius: 999px;
  transition: color var(--transition), background var(--transition);
}

.pbar__btn:hover {
  color: var(--text-0);
  background: rgba(120, 170, 255, 0.1);
}

.pbar__btn--exit {
  color: #ff9d94;
  border: 1px solid rgba(231, 76, 60, 0.35);
  background: rgba(231, 76, 60, 0.1);
}

.pbar__btn--exit:hover {
  color: #ffd9d4;
  background: rgba(231, 76, 60, 0.2);
}

@media (max-width: 720px) {
  .pbar__status-text {
    display: none;
  }
}
</style>
