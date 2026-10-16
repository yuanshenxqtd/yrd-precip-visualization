import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchMeta, fetchQuality } from '@/api'
import { describeError } from '@/api/client'
import type { MetaInfo, QualityReport } from '@/types'

/**
 * 应用级状态：后端连通性、数据规模、采集状态、侧边栏折叠。
 * 所有模块页共用，避免各自重复请求 /meta 与 /admin/quality。
 */
export const useAppStore = defineStore('app', () => {
  const meta = ref<MetaInfo | null>(null)
  const quality = ref<QualityReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastSyncAt = ref<Date | null>(null)
  const sidebarCollapsed = ref(false)

  /** 是否已成功连上后端 */
  const online = computed(() => meta.value !== null && error.value === null)

  /** 最近一次采集是否成功 */
  const collectHealthy = computed(() => meta.value?.last_collect_status === 'success')

  /** 页面底部/页头显示的数据时间 */
  const latestObsTime = computed(() => meta.value?.hourly_end ?? null)

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      const [metaData, qualityData] = await Promise.all([fetchMeta(), fetchQuality()])
      meta.value = metaData
      quality.value = qualityData
      lastSyncAt.value = new Date()
      error.value = null
    } catch (err) {
      error.value = describeError(err)
    } finally {
      loading.value = false
    }
  }

  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    meta,
    quality,
    loading,
    error,
    lastSyncAt,
    sidebarCollapsed,
    online,
    collectHealthy,
    latestObsTime,
    refresh,
    toggleSidebar,
  }
})
