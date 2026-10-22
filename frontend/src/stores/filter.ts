import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchRegions } from '@/api'
import type { Region } from '@/types'

/**
 * 全局筛选状态：选中的行政区、对比城市、时间窗口。
 * 各模块共享同一份选择，实现「点地图 → 其他图表跟着切」的联动效果。
 */
export const useFilterStore = defineStore('filter', () => {
  const regions = ref<Region[]>([])
  const loaded = ref(false)
  const selectedAdcode = ref<string | null>(null)
  const compareAdcodes = ref<string[]>([])
  const rangeDays = ref(30)
  /** 进行中的加载请求，避免并发重复拉取 */
  let pending: Promise<void> | null = null

  /** 参与采集的 56 个点位 */
  const monitored = computed(() => regions.value.filter((r) => r.is_monitored === 1))

  /** 省级 → 下辖点位，用于选择器的分组显示 */
  const groupedByProvince = computed(() => {
    const groups = new Map<string, Region[]>()
    for (const region of regions.value) {
      if (region.level === 'province') continue
      const list = groups.get(region.province) ?? []
      list.push(region)
      groups.set(region.province, list)
    }
    return [...groups.entries()].map(([province, items]) => ({ province, items }))
  })

  /** adcode → 名称。地图按名称匹配 GeoJSON 要素，需要这个映射 */
  const nameByAdcode = computed<Record<string, string>>(() =>
    Object.fromEntries(regions.value.map((r) => [r.adcode, r.name])),
  )

  const selected = computed(
    () => regions.value.find((r) => r.adcode === selectedAdcode.value) ?? null,
  )

  const selectedName = computed(() => selected.value?.name ?? '长三角全区')

  /** 是否处于「聚焦某个点位」状态（全区时为 false） */
  const hasFocus = computed(() => selectedAdcode.value !== null)

  /** 聚焦点位名称；未聚焦时为空串（与 selectedName 的「全区」兜底区分开） */
  const focusName = computed(() => (hasFocus.value ? (selected.value?.name ?? '') : ''))

  const focusProvince = computed(() => (hasFocus.value ? (selected.value?.province ?? '') : ''))

  const focusLevel = computed(() => (hasFocus.value ? (selected.value?.level ?? '') : ''))

  async function loadRegions(): Promise<void> {
    if (loaded.value) return
    if (pending) return pending
    pending = fetchRegions()
      .then((data) => {
        regions.value = data
        loaded.value = true
        // 默认对比城市：上海(黄浦)、苏州、杭州
        if (!compareAdcodes.value.length) {
          const prefer = ['310101', '320500', '330100']
          const available = new Set(monitored.value.map((r) => r.adcode))
          compareAdcodes.value = prefer.filter((code) => available.has(code))
        }
      })
      .finally(() => {
        pending = null
      })
    return pending
  }

  function select(adcode: string | null): void {
    selectedAdcode.value = adcode
  }

  /** 手动清空聚焦，回到全区 */
  function clearFocus(): void {
    selectedAdcode.value = null
  }

  function toggleCompare(adcode: string): void {
    const list = compareAdcodes.value
    const index = list.indexOf(adcode)
    if (index >= 0) list.splice(index, 1)
    else if (list.length < 8) list.push(adcode)
  }

  return {
    regions,
    loaded,
    selectedAdcode,
    compareAdcodes,
    rangeDays,
    monitored,
    groupedByProvince,
    nameByAdcode,
    selected,
    selectedName,
    hasFocus,
    focusName,
    focusProvince,
    focusLevel,
    loadRegions,
    select,
    clearFocus,
    toggleCompare,
  }
})
