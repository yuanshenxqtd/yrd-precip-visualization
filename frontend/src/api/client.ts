import axios, { AxiosError } from 'axios'

/**
 * 统一的 HTTP 客户端。
 *
 * baseURL 取自 VITE_API_BASE：
 *   - 开发期 = /api，由 Vite 代理转发到 http://127.0.0.1:8000（无跨域问题）
 *   - 部署期可改为后端完整地址
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 60000,
  headers: { Accept: 'application/json' },
})

/** 把后端/网络错误转成可读中文提示。 */
export function describeError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.code === 'ECONNABORTED') return '请求超时：后端可能未启动或响应过慢'
    if (!error.response) return '无法连接后端（请确认已运行 scripts\\run_backend.bat）'
    const detail = (error.response.data as { detail?: string } | undefined)?.detail
    return detail || `后端返回 ${error.response.status}`
  }
  if (error instanceof Error) return error.message
  return '未知错误'
}

http.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const message = describeError(error)
    console.warn('[api]', message)
    return Promise.reject(new Error(message))
  },
)
