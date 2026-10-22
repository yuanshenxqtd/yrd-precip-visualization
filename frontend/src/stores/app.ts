import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchMeta, fetchQuality } from '@/api'
import { describeError } from '@/api/client'
import type { MetaInfo, QualityReport } from '@/types'

/** 数据时效阈值（小时） */
export const FRESH_HOURS = 2
export const EXPIRED_HOURS = 24

/**
 * 数据时效状态。
 *
 * - `ok`      数据新鲜（距最新实况 < 2 小时）
 * - `stale`   偏旧（2 ~ 24 小时）—— 提醒用户采集器可能没在跑
 * - `expired` 过期（> 24 小时）—— 明确告知数据不是最新的
 * - `failed`  最近一次采集失败（与时效无关，优先提示）
 * - `offline` 连不上后端
 * - `idle`    尚未取到数据
 */
export type Freshness = 'ok' | 'stale' | 'expired' | 'failed' | 'offline' | 'idle'

const LABELS: Record<Freshness, string> = {
  ok: '数据新鲜',
  stale: '数据偏旧',
  expired: '数据过期',
  failed: '采集失败',
  offline: '后端未连接',
  idle: '连接中',
}

/**
 * 解析后端的本地时间字符串（形如 2026-10-16T10:00 或 2026-10-16T10:00:00）。
 * 手写解析而不依赖 Date 字符串解析，避免不同浏览器对无时区字符串的歧义。
 */
function parseLocal(value: string | null): number | null {
  if (!value) return null
  const [datePart, timePart = '00:00'] = value.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  if (!y || !mo || !d) return null
  const [h = 0, mi = 0] = timePart.split(':').map(Number)
  return new Date(y, mo - 1, d, h, mi, 0, 0).getTime()
}

/* ------------------------------------------------------------ 演示模式存储 */

const DEMO_STORAGE_KEY = 'yrd-demo-mode'

/** 用 sessionStorage 记住演示模式，刷新页面后仍保持（关标签页即失效） */
function readStoredDemo(): boolean {
  try {
    return window.sessionStorage.getItem(DEMO_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function writeStoredDemo(on: boolean): void {
  try {
    if (on) window.sessionStorage.setItem(DEMO_STORAGE_KEY, '1')
    else window.sessionStorage.removeItem(DEMO_STORAGE_KEY)
  } catch {
    /* 隐私模式等场景忽略 */
  }
}

/**
 * 应用级状态：后端连通性、数据规模、采集状态、侧边栏折叠、**数据时效**。
 * 所有模块页共用，避免各自重复请求 /meta 与 /admin/quality。
 */
export const useAppStore = defineStore('app', () => {
  const meta = ref<MetaInfo | null>(null)
  const quality = ref<QualityReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastSyncAt = ref<Date | null>(null)
  const sidebarCollapsed = ref(false)

  /** 服务器时间与本地时间的差值（毫秒）—— 用于抵消客户端时钟偏差 */
  const skewMs = ref(0)
  /** 用于让数据时效随时间自动推进的本地时钟 */
  const tickNow = ref(Date.now())
  let ticker: number | undefined

  /** 是否已成功连上后端 */
  const online = computed(() => meta.value !== null && error.value === null)

  /** 最近一次采集是否成功 */
  const collectHealthy = computed(() => meta.value?.last_collect_status === 'success')

  /**
   * 最新**实况**时刻。
   *
   * 注意：不能用 `hourly_end` —— 它包含预报，实测可能落在 6 天之后，
   * 用作「数据时刻」会让界面显示一个未来时间。
   */
  const latestObsTime = computed(() => meta.value?.observed_end ?? null)

  /** 按服务器口径的当前时间 */
  const currentMs = computed(() => tickNow.value + skewMs.value)

  /** 数据已过去多少小时（无法判断时为 null） */
  const dataAgeHours = computed<number | null>(() => {
    const end = parseLocal(latestObsTime.value)
    if (end === null) return null
    return (currentMs.value - end) / 3_600_000
  })

  /** 数据时效状态 */
  const freshness = computed<Freshness>(() => {
    if (error.value) return 'offline'
    const info = meta.value
    if (!info) return 'idle'
    if (info.last_collect_status === 'failed') return 'failed'
    const age = dataAgeHours.value
    if (age === null) return 'idle'
    if (age < FRESH_HOURS) return 'ok'
    if (age < EXPIRED_HOURS) return 'stale'
    return 'expired'
  })

  const freshnessLabel = computed(() => LABELS[freshness.value])

  /** 是否需要向用户提示数据不是最新的 */
  const freshnessWarned = computed(
    () => freshness.value === 'stale' || freshness.value === 'expired',
  )

  /** 把时效换算成人话，例如「5.2 天前」 */
  const ageText = computed(() => {
    const age = dataAgeHours.value
    if (age === null) return '未知'
    if (age < 1) return `${Math.round(age * 60)} 分钟前`
    if (age < 48) return `${age.toFixed(1)} 小时前`
    return `${(age / 24).toFixed(1)} 天前`
  })

  /** 顶栏与提示条共用的说明文字 */
  const freshnessHint = computed(() => {
    switch (freshness.value) {
      case 'ok':
        return `最新实况 ${ageText.value}，数据正常`
      case 'stale':
        return `最新实况 ${ageText.value}，数据可能不是最新的 —— 请检查定时采集是否在运行`
      case 'expired':
        return `最新实况 ${ageText.value}，数据已过期 —— 请启动 scripts\\start_autocollect.bat 或手动采集一次`
      case 'failed':
        return `最近一次采集失败，界面展示的是 ${ageText.value}的实况数据`
      case 'offline':
        return '无法连接后端，当前页面没有可用数据'
      default:
        return '正在获取数据状态…'
    }
  })

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      const clientNow = Date.now()
      const [metaData, qualityData] = await Promise.all([fetchMeta(), fetchQuality()])
      meta.value = metaData
      quality.value = qualityData
      lastSyncAt.value = new Date()

      // 记录服务器与本地的时间差，后续时效计算以服务器口径为准
      const serverNow = parseLocal(metaData.server_now)
      skewMs.value = serverNow === null ? 0 : serverNow - clientNow
      tickNow.value = Date.now()

      error.value = null
    } catch (err) {
      error.value = describeError(err)
    } finally {
      loading.value = false
    }
    startTicker()
  }

  /** 每 30 秒推进一次本机时钟，让「数据已过去多久」自动增长 */
  function startTicker(): void {
    if (ticker !== undefined) return
    ticker = window.setInterval(() => {
      tickNow.value = Date.now()
    }, 30_000)
  }

  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  /* ------------------------------------------------------------ 演示模式 */

  const demoMode = ref(readStoredDemo())
  const isFullscreen = ref(false)

  /**
   * 主动退出全屏时的时间窗，用于区分「用户点全屏按钮退出」与「浏览器吞掉 Esc 退出」。
   *
   * 全屏状态下浏览器会自己消费 Esc 来退全屏、**不把按键派发给网页**，
   * 所以只能靠 fullscreenchange 兜底：若不是我们主动退的，就一并退出演示模式，
   * 避免出现「按一次 Esc 只退出了一半」的尴尬。
   */
  let suppressDemoExitUntil = 0

  function syncFullscreen(): void {
    const on = typeof document !== 'undefined' && document.fullscreenElement !== null
    isFullscreen.value = on
    if (!on && demoMode.value && Date.now() > suppressDemoExitUntil) {
      demoMode.value = false
      writeStoredDemo(false)
    }
    suppressDemoExitUntil = 0
  }

  /**
   * 进入演示模式：隐藏侧边栏与页头，让内容占满整屏。
   *
   * `forceFullscreen` 为 false 时不主动请求全屏 —— 浏览器要求 requestFullscreen
   * 必须由用户手势触发，带 ?demo=1 打开页面时无法满足，强行调用会被拒绝。
   */
  async function enterDemo(forceFullscreen = true): Promise<void> {
    demoMode.value = true
    writeStoredDemo(true)
    if (!forceFullscreen) {
      syncFullscreen()
      return
    }
    try {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen()
    } catch {
      /* 非用户手势或浏览器不支持：布局仍是演示态，只是没有全屏 */
    }
    syncFullscreen()
  }

  async function exitDemo(): Promise<void> {
    demoMode.value = false
    writeStoredDemo(false)
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
    } catch {
      /* ignore */
    }
    syncFullscreen()
  }

  function toggleDemo(): void {
    if (demoMode.value) void exitDemo()
    else void enterDemo()
  }

  async function toggleFullscreen(): Promise<void> {
    try {
      if (document.fullscreenElement) {
        // 只退全屏、保留演示布局
        suppressDemoExitUntil = Date.now() + 1000
        await document.exitFullscreen()
      } else {
        await document.documentElement.requestFullscreen()
      }
    } catch {
      /* ignore */
    }
    syncFullscreen()
  }

  /** 解析 URL 上的 ?demo=1 / ?demo=0 */
  function applyQueryDemo(value: unknown): void {
    const flag = Array.isArray(value) ? value[value.length - 1] : value
    if (flag === '1' || flag === 'true') {
      if (!demoMode.value) void enterDemo(false)
    } else if (flag === '0' || flag === 'false') {
      if (demoMode.value) void exitDemo()
    }
  }

  function initDemo(): void {
    syncFullscreen()
    document.addEventListener('fullscreenchange', syncFullscreen)
  }

  function disposeDemo(): void {
    document.removeEventListener('fullscreenchange', syncFullscreen)
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
    dataAgeHours,
    freshness,
    freshnessLabel,
    freshnessWarned,
    freshnessHint,
    ageText,
    demoMode,
    isFullscreen,
    refresh,
    toggleSidebar,
    enterDemo,
    exitDemo,
    toggleDemo,
    toggleFullscreen,
    applyQueryDemo,
    initDemo,
    disposeDemo,
  }
})
