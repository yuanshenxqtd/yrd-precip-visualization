<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import NavIcon from '@/components/common/NavIcon.vue'
import { routes } from '@/router'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const route = useRoute()

interface NavItem {
  path: string
  title: string
  icon: string
}

const navItems = computed<NavItem[]>(() =>
  routes
    .filter((r) => r.meta?.title && typeof r.path === 'string' && r.path.startsWith('/'))
    .map((r) => ({
      path: r.path,
      title: r.meta!.title as string,
      icon: (r.meta!.icon as string) ?? 'grid',
    })),
)

const currentPath = computed(() => route.path)
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar--collapsed': app.sidebarCollapsed }">
    <div class="sidebar__brand">
      <div class="sidebar__logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
          <path d="M6 14.5a4 4 0 0 1 .6-7.95 5.5 5.5 0 0 1 10.5 1.2A3.6 3.6 0 0 1 17 14.5" />
          <path d="M8.5 17.5l-1 2.5M12 17.5l-1 2.5M15.5 17.5l-1 2.5" />
        </svg>
      </div>
      <div v-show="!app.sidebarCollapsed" class="sidebar__titles">
        <div class="sidebar__title">长三角降水监测</div>
        <div class="sidebar__subtitle">实时监测与可视化分析</div>
      </div>
    </div>

    <nav class="sidebar__nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'nav-item--active': currentPath === item.path }"
        :title="item.title"
      >
        <NavIcon :name="item.icon" />
        <span v-show="!app.sidebarCollapsed" class="nav-item__label">{{ item.title }}</span>
      </RouterLink>
    </nav>

    <div v-show="!app.sidebarCollapsed" class="sidebar__footer">
      <div class="sidebar__stat">
        <span class="text-muted">采集点</span>
        <span class="text-mono">{{ app.meta?.points_total ?? '—' }}</span>
      </div>
      <div class="sidebar__stat">
        <span class="text-muted">小时记录</span>
        <span class="text-mono">{{ app.meta ? app.meta.hourly_rows.toLocaleString('zh-CN') : '—' }}</span>
      </div>
      <div class="sidebar__source">
        数据源 {{ app.meta?.data_source ?? '—' }} · CC BY 4.0
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  flex: 0 0 var(--sidebar-width);
  height: 100vh;
  padding: var(--gap-sm);
  background: linear-gradient(180deg, rgba(16, 29, 56, 0.9), rgba(9, 17, 34, 0.92));
  border-right: 1px solid var(--panel-border);
  transition: width var(--transition), flex-basis var(--transition);
}

.sidebar--collapsed {
  width: var(--sidebar-width-collapsed);
  flex-basis: var(--sidebar-width-collapsed);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 8px 8px 16px;
}

.sidebar__logo {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  color: var(--accent-light);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.sidebar__logo svg {
  width: 20px;
  height: 20px;
}

.sidebar__title {
  font-size: 13px;
  font-weight: 650;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.sidebar__subtitle {
  font-size: 11px;
  color: var(--text-2);
  white-space: nowrap;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  color: var(--text-1);
  border-radius: var(--radius-sm);
  transition: background var(--transition), color var(--transition);
  white-space: nowrap;
}

.nav-item:hover {
  color: var(--text-0);
  background: rgba(120, 170, 255, 0.08);
}

.nav-item--active {
  color: var(--text-0);
  background: var(--accent-dim);
  box-shadow: inset 2px 0 0 var(--accent);
}

.nav-item__label {
  font-size: 13px;
}

.sidebar__footer {
  padding: 12px 8px 4px;
  border-top: 1px solid var(--panel-border);
  display: grid;
  gap: 4px;
}

.sidebar__stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.sidebar__source {
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-3);
}
</style>
