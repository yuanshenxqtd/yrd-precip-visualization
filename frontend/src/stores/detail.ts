import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchRegionDetail } from '@/api'
import { describeError } from '@/api/client'
import type { RegionDetail } from '@/types'

import { useFilterStore } from './filter'

/**
 * 点位下钻抽屉的全局状态。
 *
 * 抽屉在 AppLayout 里只挂载一次，任何页面/任何图表只要调用
 * `open(adcode)` 就能唤起它 —— 这样「看到数字 → 追问明细」在
 * 全站都是一致的交互，不需要每个页面各写一套。
 */
export const useDetailStore = defineStore('detail', () => {
  const visible = ref(false)
  const adcode = ref<string | null>(null)
  const detail = ref<RegionDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const windowHours = ref(48)
  const windowDays = ref(30)

  const name = computed(() => detail.value?.region.name ?? '')
  const province = computed(() => detail.value?.region.province ?? '')

  async function load(): Promise<void> {
    if (!adcode.value) return
    loading.value = true
    try {
      detail.value = await fetchRegionDetail(adcode.value, {
        hours: windowHours.value,
        days: windowDays.value,
      })
      error.value = null
    } catch (err) {
      detail.value = null
      error.value = describeError(err)
    } finally {
      loading.value = false
    }
  }

  /** 打开抽屉并载入指定点位（同一 adcode 且已有数据时不重复请求） */
  async function open(code: string): Promise<void> {
    visible.value = true

    // 联动：打开详情的同时把全局筛选切到该点位。
    // 关掉抽屉后，各页图表已经切到这个点位上了，不会「点完什么都没变」。
    useFilterStore().select(code)

    if (adcode.value === code && detail.value) return
    adcode.value = code
    detail.value = null
    await load()
  }

  function close(): void {
    visible.value = false
  }

  /** 切换统计窗口后重新拉取 */
  async function setWindow(hours: number, days: number): Promise<void> {
    windowHours.value = hours
    windowDays.value = days
    await load()
  }

  return {
    visible,
    adcode,
    detail,
    loading,
    error,
    windowHours,
    windowDays,
    name,
    province,
    open,
    close,
    load,
    setWindow,
  }
})
