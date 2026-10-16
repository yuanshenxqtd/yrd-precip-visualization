<script setup lang="ts">
/** 行政区划选择器：按省市分组的下拉框，数据来自全局 filter store。 */
import { computed } from 'vue'

import { useFilterStore } from '@/stores/filter'

withDefaults(
  defineProps<{
    modelValue: string | null
    label?: string
    allowAll?: boolean
    allLabel?: string
  }>(),
  { label: '', allowAll: true, allLabel: '长三角全区' },
)

const emit = defineEmits<{ 'update:modelValue': [string | null] }>()

const filter = useFilterStore()
const groups = computed(() => filter.groupedByProvince)

function onChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  emit('update:modelValue', value === '' ? null : value)
}
</script>

<template>
  <label class="region-select">
    <span v-if="label" class="region-select__label">{{ label }}</span>
    <select class="region-select__input" :value="modelValue ?? ''" @change="onChange">
      <option v-if="allowAll" value="">{{ allLabel }}</option>
      <optgroup v-for="group in groups" :key="group.province" :label="group.province">
        <option v-for="item in group.items" :key="item.adcode" :value="item.adcode">
          {{ item.name }}
        </option>
      </optgroup>
    </select>
  </label>
</template>

<style scoped>
.region-select {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.region-select__label {
  color: var(--text-2);
  white-space: nowrap;
}

.region-select__input {
  min-width: 132px;
  padding: 5px 10px;
  font-family: inherit;
  font-size: 13px;
  color: var(--text-0);
  background: rgba(16, 29, 56, 0.9);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  outline: none;
  cursor: pointer;
  transition: border-color var(--transition);
}

.region-select__input:hover,
.region-select__input:focus {
  border-color: var(--panel-border-hover);
}

.region-select__input option,
.region-select__input optgroup {
  color: var(--text-0);
  background: #101d38;
}
</style>
