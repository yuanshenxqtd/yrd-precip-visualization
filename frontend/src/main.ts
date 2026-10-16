import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/global.css'

const app = createApp(App)

/**
 * 全局错误提示。
 *
 * 组件内部抛错时 Vue 默认只往控制台打日志，页面上什么都看不到，极难排查。
 * 这里把错误以一个**可关闭的浮层**显示出来，并写进 document.title。
 *
 * 注意：只做覆盖层，**不清空 #app** —— 单个子组件出错不应该让整个界面消失。
 */
let fatalShown = false

function showErrorOverlay(message: string, stack?: string): void {
  document.title = `出错了 · ${message.slice(0, 50)}`
  if (fatalShown) return
  fatalShown = true

  const overlay = document.createElement('div')
  overlay.id = 'error-overlay'
  overlay.style.cssText = [
    'position:fixed', 'left:50%', 'top:24px', 'transform:translateX(-50%)',
    'z-index:99999', 'max-width:min(900px, 92vw)', 'max-height:80vh', 'overflow:auto',
    'padding:18px 22px', 'font-family:system-ui,sans-serif', 'line-height:1.65',
    'color:#ffd9d4', 'background:rgba(24,10,10,.96)',
    'border:1px solid rgba(231,76,60,.5)', 'border-radius:10px',
    'box-shadow:0 12px 40px rgba(0,0,0,.5)',
  ].join(';')

  const stackBlock = stack
    ? `<pre style="margin-top:12px;padding:10px;font-size:11px;line-height:1.5;white-space:pre-wrap;
                  color:#a8bcd8;background:rgba(0,0,0,.35);border-radius:6px;max-height:40vh;overflow:auto">${stack}</pre>`
    : ''

  overlay.innerHTML = `
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
      <div style="font-size:15px;font-weight:600">页面出现错误</div>
      <button id="error-overlay-close"
              style="flex:0 0 auto;padding:2px 10px;font-size:12px;color:#ffd9d4;cursor:pointer;
                     background:transparent;border:1px solid rgba(231,76,60,.5);border-radius:5px">关闭</button>
    </div>
    <div style="margin-top:6px;font-size:13px;word-break:break-all;color:#eaf2ff">${message}</div>
    ${stackBlock}
    <div style="margin-top:12px;font-size:12px;color:#a8bcd8">
      若后端未启动，请先运行 scripts\\run_backend.bat；完整堆栈见浏览器控制台。
    </div>`

  document.body.appendChild(overlay)
  document.getElementById('error-overlay-close')?.addEventListener('click', () => {
    overlay.remove()
    fatalShown = false
  })
}

app.config.errorHandler = (err, _instance, info) => {
  const error = err as Error
  // eslint-disable-next-line no-console
  console.error('[vue error]', err, info)
  showErrorOverlay(`${error?.message ?? String(err)}　(${info})`, error?.stack)
}

window.addEventListener('error', (event) => {
  showErrorOverlay(event.message || String(event.error), (event.error as Error)?.stack)
})

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason as Error | string | undefined
  showErrorOverlay(
    reason instanceof Error ? reason.message : String(reason),
    reason instanceof Error ? reason.stack : undefined,
  )
})

app.use(createPinia())
app.use(router)
app.mount('#app')
