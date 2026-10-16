<script setup lang="ts">
/**
 * 模块占位卡片。
 * P5 阶段用于把 7 个模块的骨架搭起来并说明各模块将要实现的内容，
 * 后续阶段用真实图表逐个替换。
 */
withDefaults(
  defineProps<{
    title: string
    summary: string
    items?: { title: string; desc: string }[]
    stage?: string
  }>(),
  { items: () => [], stage: '待实现' },
)
</script>

<template>
  <section class="panel placeholder">
    <header class="panel__header">
      <div class="panel__title">{{ title }}</div>
      <span class="placeholder__stage">{{ stage }}</span>
    </header>
    <div class="panel__body">
      <p class="placeholder__summary">{{ summary }}</p>
      <ul v-if="items.length" class="placeholder__list">
        <li v-for="item in items" :key="item.title">
          <strong>{{ item.title }}</strong>
          <span class="text-dim">{{ item.desc }}</span>
        </li>
      </ul>
      <slot />
    </div>
  </section>
</template>

<style scoped>
.placeholder__stage {
  padding: 2px 10px;
  font-size: 12px;
  color: var(--accent-light);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
}

.placeholder__summary {
  font-size: 13px;
  color: var(--text-1);
}

.placeholder__list {
  margin: var(--gap) 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: var(--gap-xs);
}

.placeholder__list li {
  display: flex;
  gap: var(--gap-sm);
  align-items: baseline;
  padding: 8px 12px;
  font-size: 13px;
  background: rgba(120, 170, 255, 0.05);
  border-left: 2px solid var(--accent);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.placeholder__list strong {
  flex: 0 0 150px;
  font-weight: 600;
  color: var(--text-0);
}
</style>
