/** 通用格式化工具。 */

/** 今天（本地时区），返回 YYYY-MM-DD */
export function today(): string {
  return toDateString(new Date())
}

/** n 天前，返回 YYYY-MM-DD */
export function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return toDateString(d)
}

function toDateString(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 把 '2026-10-07T15:00' 显示为 '10-07 15:00' */
export function shortTime(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace(/^\d{2}(\d{2})-/, '$1-').replace('T', ' ')
}

/** 只取时刻部分：'2026-10-07T15:00' → '15:00' */
export function hhmm(value: string | null | undefined): string {
  if (!value) return '—'
  return value.slice(11, 16)
}

/** 在 'YYYY-MM-DDTHH:MM' 上加减小时（本地时区无关，纯字符串运算） */
export function shiftHours(value: string, hours: number): string {
  const [datePart, timePart] = value.split('T')
  const [y, m, d] = datePart.split('-').map(Number)
  const [hh, mm] = timePart.split(':').map(Number)
  const dt = new Date(y, m - 1, d, hh, mm)
  dt.setHours(dt.getHours() + hours)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}

/** 把 '2026-10-07 15:30:00' 显示为 '10-07 15:30' */
export function shortDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return value.slice(5, 16)
}

/** 数字格式化：大数加千分位，保留指定小数位 */
export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/** 大数缩写：12345 → 1.2万；1234567 → 123.5万 */
export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)}亿`
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(1)}万`
  return value.toLocaleString('zh-CN')
}

/** 距平百分比带符号显示 */
export function formatAnomaly(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
}

/** 相对时间：刚刚 / n 分钟前 / n 小时前 */
export function relativeTime(date: Date | null): string {
  if (!date) return '—'
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 10) return '刚刚'
  if (seconds < 60) return `${seconds} 秒前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  return `${Math.floor(seconds / 3600)} 小时前`
}
