<script setup lang="ts">
/**
 * 时间轴播放器：拖动 + 播放/暂停 + 倍速。
 *
 * 受控组件：索引由父组件持有（v-model），播放状态由组件内部管理。
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: number
    total: number
    label?: string
    /** 单步基准间隔（毫秒），实际间隔 = baseInterval / speed */
    baseInterval?: number
    /** 帧加载完成后自动开始播放（演示模式用） */
    autoplay?: boolean
  }>(),
  { label: '', baseInterval: 900, autoplay: false },
)

const emit = defineEmits<{ 'update:modelValue': [number] }>()

const SPEEDS = [0.5, 1, 2, 4]
const playing = ref(false)
const speed = ref(1)
let timer: number | undefined

function clearTimer(): void {
  if (timer !== undefined) {
    window.clearInterval(timer)
    timer = undefined
  }
}

function step(delta: number): void {
  if (props.total <= 0) return
  let next = props.modelValue + delta
  if (next >= props.total) next = 0
  if (next < 0) next = props.total - 1
  emit('update:modelValue', next)
}

function start(): void {
  if (props.total <= 1) return
  clearTimer()
  playing.value = true
  timer = window.setInterval(() => step(1), props.baseInterval / speed.value)
}

function stop(): void {
  clearTimer()
  playing.value = false
}

function toggle(): void {
  if (playing.value) stop()
  else start()
}

function restart(): void {
  stop()
  emit('update:modelValue', 0)
}

watch(speed, () => {
  if (playing.value) start()
})

watch(
  () => props.total,
  (total) => {
    if (total <= 1) {
      stop()
      return
    }
    // 帧数变为可用时按需自动播放（演示模式）
    if (props.autoplay && !playing.value) start()
  },
)

onMounted(() => {
  if (props.autoplay && props.total > 1) start()
})

onBeforeUnmount(clearTimer)
</script>

<template>
  <div class="scrubber">
    <button class="scrubber__btn" :disabled="total <= 1" :title="playing ? '暂停' : '播放'" @click="toggle">
      {{ playing ? '❚❚' : '▶' }}
    </button>
    <button class="scrubber__btn scrubber__btn--sm" :disabled="total <= 1" title="回到起点" @click="restart">
      ⟲
    </button>

    <input
      class="scrubber__range"
      type="range"
      min="0"
      :max="Math.max(total - 1, 0)"
      :value="modelValue"
      :disabled="total <= 1"
      @input="emit('update:modelValue', Number(($event.target as HTMLInputElement).value))"
    />

    <span class="scrubber__label text-mono">{{ label || '—' }}</span>
    <span class="scrubber__count text-muted">{{ total ? modelValue + 1 : 0 }} / {{ total }}</span>

    <span class="scrubber__speeds">
      <button
        v-for="item in SPEEDS"
        :key="item"
        class="scrubber__speed"
        :class="{ 'scrubber__speed--active': speed === item }"
        @click="speed = item"
      >
        {{ item }}×
      </button>
    </span>
  </div>
</template>

<style scoped>
.scrubber {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.scrubber__btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--text-0);
  background: var(--accent-dim);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background var(--transition);
}

.scrubber__btn:hover:not(:disabled) {
  border-color: var(--panel-border-hover);
  background: rgba(58, 160, 224, 0.22);
}

.scrubber__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.scrubber__btn--sm {
  width: 26px;
  height: 26px;
  font-size: 12px;
}

.scrubber__range {
  flex: 1 1 200px;
  min-width: 160px;
  height: 4px;
  accent-color: var(--accent);
  cursor: pointer;
}

.scrubber__label {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--accent-light);
  min-width: 96px;
}

.scrubber__count {
  flex: 0 0 auto;
  font-size: 12px;
}

.scrubber__speeds {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  background: rgba(120, 170, 255, 0.07);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-sm);
}

.scrubber__speed {
  padding: 2px 7px;
  font-size: 11px;
  color: var(--text-2);
  border-radius: 4px;
  transition: color var(--transition), background var(--transition);
}

.scrubber__speed--active {
  color: var(--text-0);
  background: var(--accent-dim);
}
</style>
