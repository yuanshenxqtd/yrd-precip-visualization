<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    unit?: string
    hint?: string
    tone?: 'default' | 'accent' | 'warning' | 'danger'
    /** 值为空（如全区无降水）时以弱化样式呈现 */
    muted?: boolean
  }>(),
  { tone: 'default', muted: false, unit: '', hint: '' },
)

const classes = computed(() => ['stat', `stat--${props.tone}`, { 'stat--muted': props.muted }])
</script>

<template>
  <div :class="classes">
    <div class="stat__label">{{ label }}</div>
    <div class="stat__value">
      <span class="text-mono">{{ value }}</span>
      <span v-if="unit" class="stat__unit">{{ unit }}</span>
    </div>
    <div v-if="hint" class="stat__hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.stat {
  padding: 14px 16px;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius);
  box-shadow: var(--panel-shadow);
  transition: border-color var(--transition), transform var(--transition);
}

.stat:hover {
  border-color: var(--panel-border-hover);
  transform: translateY(-1px);
}

.stat__label {
  font-size: 12px;
  color: var(--text-2);
  letter-spacing: 0.04em;
}

.stat__value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 6px;
  font-size: 26px;
  font-weight: 650;
  line-height: 1.15;
  color: var(--text-0);
}

.stat__unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
}

.stat__hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-2);
  min-height: 18px;
}

.stat--accent .stat__value {
  color: var(--accent-light);
}

.stat--warning .stat__value {
  color: var(--warning);
}

.stat--danger .stat__value {
  color: var(--danger);
}

.stat--muted .stat__value {
  color: var(--text-2);
}
</style>
