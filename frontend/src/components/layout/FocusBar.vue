<script setup lang="ts">
/**
 * 全局聚焦条。
 *
 * 图表联动最容易出的问题是「点了地图，别的图表悄悄变了，用户不知道」。
 * 所以联动必须有三个要素：**看得见、说得清、撤得掉** ——
 * 这条 bar 就是这三件事的载体：
 *
 *   · 看得见：聚焦时出现在页头下方，带强调色
 *   · 说得清：写明聚焦到哪个点位
 *   · 撤得掉：一个「取消聚焦」直接回到全区
 */
import { computed } from 'vue'

import NavIcon from '@/components/common/NavIcon.vue'
import { useDetailStore } from '@/stores/detail'
import { useFilterStore } from '@/stores/filter'

const filter = useFilterStore()
const detail = useDetailStore()

const levelLabel = computed(() =>
  filter.focusLevel === 'district' ? '区级' : filter.focusLevel === 'city' ? '市级' : '',
)

function openDetail(): void {
  if (filter.selectedAdcode) void detail.open(filter.selectedAdcode)
}
</script>

<template>
  <Transition name="focusbar">
    <div v-if="filter.hasFocus" class="focusbar">
      <span class="focusbar__icon" aria-hidden="true">
        <NavIcon name="focus" />
      </span>

      <span class="focusbar__text">
        已聚焦
        <strong>{{ filter.focusName }}</strong>
        <span v-if="filter.focusProvince" class="focusbar__meta">
          {{ filter.focusProvince }}<template v-if="levelLabel"> · {{ levelLabel }}</template>
        </span>
        <span class="focusbar__hint">各页图表已同步到该点位</span>
      </span>

      <span class="focusbar__actions">
        <button class="focusbar__btn" @click="openDetail">查看详情</button>
        <button class="focusbar__btn focusbar__btn--clear" title="回到全区" @click="filter.clearFocus()">
          取消聚焦
        </button>
      </span>
    </div>
  </Transition>
</template>

<style scoped>
.focusbar {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  padding: 7px var(--gap);
  font-size: 12.5px;
  color: var(--text-0);
  background: linear-gradient(
    90deg,
    rgba(58, 160, 224, 0.16),
    rgba(58, 160, 224, 0.06) 60%,
    transparent
  );
  border-bottom: 1px solid rgba(58, 160, 224, 0.28);
  border-left: 3px solid var(--accent);
}

.focusbar__icon {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  color: var(--accent-light);
}

.focusbar__text {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.focusbar__text strong {
  font-size: 13px;
  font-weight: 650;
  color: var(--accent-light);
}

.focusbar__meta {
  color: var(--text-2);
}

.focusbar__hint {
  margin-left: 4px;
  color: var(--text-3);
}

.focusbar__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.focusbar__btn {
  padding: 3px 10px;
  font-size: 12px;
  color: var(--text-0);
  background: rgba(120, 170, 255, 0.1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background var(--transition);
}

.focusbar__btn:hover {
  border-color: var(--panel-border-hover);
  background: rgba(120, 170, 255, 0.18);
}

.focusbar__btn--clear {
  color: var(--text-1);
}

.focusbar__btn--clear:hover {
  color: #ffd9d4;
  background: rgba(231, 76, 60, 0.16);
  border-color: rgba(231, 76, 60, 0.35);
}

.focusbar-enter-active,
.focusbar-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.focusbar-enter-from,
.focusbar-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
