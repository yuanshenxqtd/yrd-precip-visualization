import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

/**
 * 7 个功能模块 —— 导航即路由，每个模块一个独立页面。
 * meta.title  显示在侧边栏与页头
 * meta.icon   侧边栏图标（内联 SVG 的 path，见 AppSidebar.vue）
 * meta.module 模块代号
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/overview',
  },
  {
    path: '/overview',
    name: 'overview',
    component: () => import('@/views/OverviewView.vue'),
    meta: { title: '总览大屏', icon: 'grid', module: 'overview' },
  },
  {
    path: '/realtime',
    name: 'realtime',
    component: () => import('@/views/RealtimeView.vue'),
    meta: { title: '实时监测', icon: 'pulse', module: 'realtime' },
  },
  {
    path: '/spatial',
    name: 'spatial',
    component: () => import('@/views/SpatialView.vue'),
    meta: { title: '空间分布', icon: 'map', module: 'spatial' },
  },
  {
    path: '/trend',
    name: 'trend',
    component: () => import('@/views/TrendView.vue'),
    meta: { title: '时间分析', icon: 'chart', module: 'trend' },
  },
  {
    path: '/compare',
    name: 'compare',
    component: () => import('@/views/CompareView.vue'),
    meta: { title: '城市对比', icon: 'bars', module: 'compare' },
  },
  {
    path: '/alerts',
    name: 'alerts',
    component: () => import('@/views/AlertsView.vue'),
    meta: { title: '预警统计', icon: 'alert', module: 'alerts' },
  },
  {
    path: '/data',
    name: 'data',
    component: () => import('@/views/DataManageView.vue'),
    meta: { title: '数据管理', icon: 'database', module: 'data' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/overview',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = (to.meta.title as string) ?? ''
  document.title = title ? `${title} · 长三角降水监测` : '长三角降水实时监测与可视化分析系统'
})

export default router
