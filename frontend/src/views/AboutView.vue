<script setup lang="ts">
/**
 * 关于本系统：把「数据哪来的、怎么算的、有什么局限」一次讲清楚。
 *
 * 这一页的目的不是好看，而是**经得起追问**：
 * 评审/答辩最常问的三件事 —— 数据来源与许可、统计口径、已知限制 —— 都集中在这里，
 * 而不是散落在各页脚注里让人自己拼。
 */
import { computed } from 'vue'

import { useAppStore } from '@/stores/app'
import { formatNumber, shortTime } from '@/utils/format'

const app = useAppStore()

const meta = computed(() => app.meta)

interface Row {
  k: string
  v: string
  mono?: boolean
}

const sources: Row[] = [
  { k: '气象数据', v: 'Open-Meteo（免 API Key，基于 ECMWF ERA5 / ERA5-Land 再分析资料）' },
  { k: '数据许可', v: 'CC BY 4.0 —— 非商业免费，使用须署名', mono: false },
  { k: '行政区划边界', v: '阿里云 DataV GeoAtlas（按省级 adcode 下载后合并为 56 个要素）' },
  { k: '降水分级标准', v: 'GB/T 28592-2012《降水量等级》（已逐条核对气象局原文）' },
]

const pipeline: Row[] = [
  { k: '采集点位', v: '上海 16 个区 + 江苏 13 市 + 浙江 11 市 + 安徽 16 市，合计 56 个' },
  { k: '采集方式', v: '单次批量 HTTP 请求覆盖全部点位（约 4 秒），按点位计量计入免费额度（10000 次/天）' },
  { k: '采集间隔', v: '30 分钟（由用户手动启动的前台进程执行，关闭窗口即停止，不做任何开机自启注册）' },
  { k: '自愈补采', v: '每轮回拉最近 3 天并做幂等 UPSERT —— 停机造成的时间缺口会在下次启动时自动补齐' },
  { k: '采集审计', v: '每次采集（含失败）都写入 collect_log，界面上的「采集心跳」即来自该表' },
  { k: '历史回填', v: '日数据回溯 3 年；小时数据回溯 1 年；再分析资料有延迟，最近一个月另行补齐' },
]

const caliber: Row[] = [
  { k: '降水等级', v: '严格按 GB/T 28592-2012 的 24 小时口径划分 7 个等级' },
  { k: '实况 / 预报', v: '分开存储与展示（is_forecast 标记）；「数据时刻」一律取实况最新时刻，取预报会显示成未来时间' },
  { k: '日累计', v: '该点位当日 24 个小时值之和；「当日最大小时雨强」单独统计' },
  { k: '距平基准', v: '只采用 2024 / 2025 两个完整年份的同期均值（2023 仅 9–12 月、2026 未过完，混入会造成严重偏差）' },
  { k: '小时雨强', v: '国标未定义小时尺度等级，因此小时维度只显示真实数值 + 相对强度色阶，不套用等级名称' },
]

const limits: { title: string; detail: string }[] = [
  {
    title: '小时数据仅回溯 1 年',
    detail:
      '2025-09-07 起才有逐小时数据；更早只有日数据。因此「时间轴回放」「小时雨强分析」只能覆盖近一年，日/月/年尺度统计则可用完整 3 年。',
  },
  {
    title: '数据为再分析产品，非地面雨量站实测',
    detail:
      'ERA5 是数值模式同化后的网格再分析资料，与雨量站的点观测存在系统性差异（尤其山区与强对流局地降水）。本项目把它当作"区域性降水态势"使用，不应用于单点精确定量。',
  },
  {
    title: '气象预警数据源未接入',
    detail:
      'Open-Meteo 不提供中国气象预警，weather_alert 表为空、/api/alerts 返回空数组 —— 这是预期行为。界面上的「预警统计」展示的是按国标阈值从历史数据中筛出的统计型极端事件，不是官方发布的预警信号。',
  },
  {
    title: '采集器需要手动启动',
    detail:
      '系统不做任何开机自启注册（这是刻意的设计）。采集器未运行时数据不会更新，界面会用黄/红提示条告知数据已多久未更新；停机期间的缺口会在下次采集时自动补齐。',
  },
  {
    title: '单一数据源，未做多源交叉验证',
    detail:
      '目前只对接 Open-Meteo 一家。若需更强可信度，可接入第二个数据源对同一时段做交叉核对 —— 数据库结构已支持（precip_hourly 带 source 字段）。',
  },
  {
    title: '距平与"历史最强"的边界',
    detail:
      '受 1 年小时数据限制，"历史最强"类表述只限定在近 30 天窗口内；跨年比较只用完整的 2024 / 2025 两年。摘要里刻意不使用"罕见""破纪录"等超出数据支撑的说法。',
  },
]

const stack: Row[] = [
  { k: '数据层', v: 'SQLite（WAL 并发）+ 7 张表；逐小时与日汇总分离；唯一约束保证幂等' },
  { k: '采集层', v: 'Python 3.13 + requests + APScheduler；批量请求、幂等 UPSERT、缺口自愈、采集审计' },
  { k: '后端', v: 'FastAPI + SQLAlchemy 2；25 个接口；聚合结果 TTL 缓存' },
  { k: '前端', v: 'Vue 3 + TypeScript + Vite + Pinia + ECharts；10 余个图表组件，按路由分包' },
  { k: '工程', v: '脚本化启动与运维（纯 ASCII 批处理）、Git 版本管理、文档与实测记录' },
]
</script>

<template>
  <div class="page">
    <div class="page__intro">
      <div>
        <h2 class="page__title">关于本系统</h2>
        <p class="page__desc">
          长三角地区降水实时监测与可视化分析系统。下面把<strong>数据来源与许可</strong>、<strong>采集机制</strong>、<strong>统计口径</strong>、<strong>已知限制</strong>与<strong>技术架构</strong>一次说清。
        </p>
      </div>
    </div>

    <!-- 一句话定位 + 实时规模 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">一句话说明</div>
        <span class="panel__subtitle">数据规模为实时读取</span>
      </header>
      <div class="panel__body">
        <p class="lead">
          把长三角 56 个点位的真实降水数据采集入库，再用地图与图表呈现，并支持
          <strong>下钻到原始小时值</strong>、<strong>时间轴回放</strong>、<strong>跨模块联动</strong>与
          <strong>自动生成读图要点</strong>。
        </p>

        <dl class="kv">
          <div><dt>采集点位 / 行政区划</dt><dd class="text-mono">{{ meta?.points_total ?? '—' }} / {{ meta?.regions_total ?? '—' }}</dd></div>
          <div><dt>逐小时记录</dt><dd class="text-mono">{{ meta ? formatNumber(meta.hourly_rows) : '—' }}</dd></div>
          <div><dt>日汇总记录</dt><dd class="text-mono">{{ meta ? formatNumber(meta.daily_rows) : '—' }}</dd></div>
          <div><dt>实况数据范围</dt><dd class="text-mono">{{ shortTime(meta?.observed_start) }} ~ {{ shortTime(meta?.observed_end) }}</dd></div>
          <div><dt>日数据范围</dt><dd class="text-mono">{{ meta?.daily_start ?? '—' }} ~ {{ meta?.daily_end ?? '—' }}</dd></div>
          <div><dt>最近一次采集</dt><dd class="text-mono">{{ meta?.last_collect_at ?? '—' }} · {{ meta?.last_collect_status ?? '—' }}</dd></div>
        </dl>
      </div>
    </section>

    <!-- 数据来源与许可 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">数据来源与许可</div>
        <span class="panel__subtitle">使用前请确认署名要求</span>
      </header>
      <div class="panel__body">
        <dl class="kv kv--wide">
          <div v-for="row in sources" :key="row.k">
            <dt>{{ row.k }}</dt>
            <dd>{{ row.v }}</dd>
          </div>
        </dl>
        <p class="footnote">
          气象数据与行政区划边界均为公开数据，本项目仅作教学与课程设计用途。
        </p>
      </div>
    </section>

    <!-- 采集机制 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">采集机制</div>
        <span class="panel__subtitle">手动启动 · 自愈补采 · 幂等写入</span>
      </header>
      <div class="panel__body">
        <dl class="kv kv--wide">
          <div v-for="row in pipeline" :key="row.k">
            <dt>{{ row.k }}</dt>
            <dd>{{ row.v }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- 统计口径 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">统计口径</div>
        <span class="panel__subtitle">同一个数字，口径不同结论会差很多</span>
      </header>
      <div class="panel__body">
        <dl class="kv kv--wide">
          <div v-for="row in caliber" :key="row.k">
            <dt>{{ row.k }}</dt>
            <dd>{{ row.v }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- 已知限制 -->
    <section class="panel panel--warn">
      <header class="panel__header">
        <div class="panel__title">已知限制</div>
        <span class="panel__subtitle">主动说明，避免误用</span>
      </header>
      <div class="panel__body">
        <div class="limits">
          <article v-for="item in limits" :key="item.title" class="limit">
            <h4 class="limit__title">{{ item.title }}</h4>
            <p class="limit__detail">{{ item.detail }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- 架构 -->
    <section class="panel">
      <header class="panel__header">
        <div class="panel__title">技术架构</div>
        <span class="panel__subtitle">数据层 → 采集层 → 后端 → 前端</span>
      </header>
      <div class="panel__body">
        <dl class="kv kv--wide">
          <div v-for="row in stack" :key="row.k">
            <dt>{{ row.k }}</dt>
            <dd>{{ row.v }}</dd>
          </div>
        </dl>
        <p class="footnote">
          更详细的规划与逐阶段实测记录见仓库中的
          <code>docs/PLAN.md</code>，数据源核实过程见 <code>docs/DATA_SOURCE.md</code>。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.lead {
  margin-bottom: var(--gap-sm);
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--text-1);
}

.lead strong {
  color: var(--accent-light);
  font-weight: 600;
}

.kv {
  margin: 0;
  display: grid;
  gap: 7px;
  font-size: 13px;
}

.kv > div {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
  gap: var(--gap-sm);
  align-items: baseline;
  padding-bottom: 7px;
  border-bottom: 1px dashed rgba(120, 170, 255, 0.12);
}

.kv > div:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.kv dt {
  color: var(--text-2);
  white-space: nowrap;
}

.kv dd {
  margin: 0;
  color: var(--text-0);
  line-height: 1.7;
}

.kv--wide > div {
  grid-template-columns: 132px minmax(0, 1fr);
}

/* 已知限制 */
.panel--warn {
  border-color: rgba(245, 215, 110, 0.28);
}

.panel--warn .panel__title::before {
  background: linear-gradient(180deg, #f5d76e, #f39c12);
}

.limits {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: var(--gap-sm);
}

.limit {
  padding: 11px 13px;
  background: rgba(245, 215, 110, 0.05);
  border: 1px solid rgba(245, 215, 110, 0.2);
  border-radius: var(--radius-sm);
}

.limit__title {
  margin-bottom: 5px;
  font-size: 12.5px;
  font-weight: 620;
  color: #ffe6a8;
}

.limit__detail {
  font-size: 12.5px;
  line-height: 1.75;
  color: var(--text-1);
}

.footnote {
  margin-top: var(--gap-sm);
  font-size: 12px;
  color: var(--text-2);
}

code {
  padding: 1px 5px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  background: rgba(120, 170, 255, 0.12);
  border-radius: 4px;
}

@media (max-width: 720px) {
  .kv > div,
  .kv--wide > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .kv dt {
    white-space: normal;
  }
}
</style>
