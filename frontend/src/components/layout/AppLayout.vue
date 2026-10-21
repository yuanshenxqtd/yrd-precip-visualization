<script setup lang="ts">
import { onMounted } from 'vue'

import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
import DetailDrawer from '@/components/common/DetailDrawer.vue'
import { useAppStore } from '@/stores/app'
import { useFilterStore } from '@/stores/filter'

const app = useAppStore()
const filter = useFilterStore()

onMounted(async () => {
  await app.refresh()
  // 行政区划是各模块共用的基础数据，连上后端后立即拉一次
  if (app.online) {
    try {
      await filter.loadRegions()
    } catch {
      /* 行政区划拉取失败不阻塞页面，后续模块自行重试 */
    }
  }
})
</script>

<template>
  <div class="layout">
    <AppSidebar />

    <div class="layout__main">
      <AppHeader />

      <div v-if="app.error" class="layout__banner">
        <strong>无法连接后端：</strong>
        <span>{{ app.error }}</span>
        <span class="layout__banner-hint">
          请先运行
          <code>scripts\run_backend.bat</code>
          启动接口服务，然后点击右上角刷新。
        </span>
      </div>

      <!-- 数据时效警示：偏旧 / 过期时出现，避免用户把旧数据当成最新 -->
      <div
        v-else-if="app.freshnessWarned"
        class="layout__banner"
        :class="`layout__banner--${app.freshness}`"
      >
        <strong>{{ app.freshnessLabel }}：</strong>
        <span>{{ app.freshnessHint }}</span>
        <span class="layout__banner-hint">
          采集器未运行时数据不会更新；停机期间的数据缺口会在下次采集时自动补齐。
        </span>
      </div>

      <main class="layout__content">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <!-- 下钻抽屉：全站唯一实例，任何图表调用 detail.open(adcode) 即可唤起 -->
    <DetailDrawer />
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.layout__main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.layout__content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.layout__banner {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  padding: 10px var(--gap);
  font-size: 13px;
  color: #ffd9d4;
  background: rgba(231, 76, 60, 0.14);
  border-bottom: 1px solid rgba(231, 76, 60, 0.3);
}

/* 偏旧：黄色提示；过期：红色（与后端断连同色但文案不同） */
.layout__banner--stale {
  color: #ffe6a8;
  background: rgba(245, 215, 110, 0.12);
  border-bottom-color: rgba(245, 215, 110, 0.3);
}

.layout__banner--expired {
  color: #ffd9d4;
  background: rgba(231, 76, 60, 0.14);
  border-bottom-color: rgba(231, 76, 60, 0.3);
}

.layout__banner-hint {
  color: var(--text-1);
}

.layout__banner code {
  padding: 1px 6px;
  font-family: var(--font-mono);
  font-size: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 180ms ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
