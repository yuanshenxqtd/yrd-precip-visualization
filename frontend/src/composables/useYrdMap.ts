import * as echarts from 'echarts/core'

import { fetchGeoJSON } from '@/api'

/**
 * 长三角合并地图的注册（模块级单例，全局只注册一次）。
 *
 * GeoJSON 来自 /api/regions/geojson，是沪苏浙皖四份数据合并后的
 * 56 要素 FeatureCollection；每个要素的 properties.name 与后端返回的
 * 点位名称一致，ECharts 才能按 name 匹配上数据。
 */

export const YRD_MAP_NAME = 'yrd'

let pending: Promise<void> | null = null
let done = false

export function ensureYrdMap(): Promise<void> {
  if (done) return Promise.resolve()
  if (pending) return pending

  pending = fetchGeoJSON()
    .then((geo) => {
      echarts.registerMap(YRD_MAP_NAME, geo as never)
      done = true
    })
    .catch((err) => {
      pending = null
      throw err
    })

  return pending
}

export function isYrdMapReady(): boolean {
  return done
}
