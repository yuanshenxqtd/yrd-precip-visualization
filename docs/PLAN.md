# 长三角地区降水实时监测与可视化分析系统 · 项目规划

> 课程设计项目规划文档
> 最后更新：2026-10-04
> 状态：**方案已确认，进入实施阶段**

---

## 1. 项目概述

### 1.1 目标

构建一个面向长三角地区（上海市、江苏省、浙江省、安徽省）的**降水实时监测与可视化分析系统**，实现：

- 从真实气象数据源**定时采集**逐小时降水数据并持久化入库
- 提供**多模块可视化大屏**与**交互式分析界面**
- 支持空间分布、时间趋势、城市对比、历史回放等分析能力

### 1.2 范围边界

| 包含 | 不包含 |
|---|---|
| 长三角 41 个地级及以上城市（上海细化到 16 个区，共 **56 个采集点**） | 全国范围、区县级全覆盖 |
| 逐小时降水实况与预报数据 | 分钟级雷达外推降水 |
| 历史 3 年日数据 + 1 年小时数据 | 30 年气候态长序列 |
| 降水相关的可视化与统计分析 | 温度、风、气压等多要素综合分析 |

### 1.3 硬性要求对照

| 要求 | 落实方式 |
|---|---|
| 可视化界面 | ECharts 地图/折线/柱状/箱线/饼图等，7 个专题模块 |
| 交互界面 | 时间轴回放、图表联动、下钻、自动刷新、数据导出 |
| 导航 + 模块化 | Vue Router 驱动 7 个路由模块，前后端均为分层模块化结构 |
| 数据库 | SQLite（SQLAlchemy ORM，7 张表，含唯一索引与幂等写入） |
| 数据真实 | Open-Meteo 真实气象再分析数据 + 官方行政区划 GeoJSON |

---

## 2. 已锁定的决策

| 项目 | 决策 |
|---|---|
| 数据源（实时+历史） | **Open-Meteo** 免费层（免 API Key） |
| 数据源（地图边界） | **阿里 DataV GeoAtlas** 行政区划 GeoJSON |
| 采集频率 | **30 分钟/次**（每轮拉取 `past_days=3`，自愈补缺） |
| 采集点位 | **56 个**：上海 16 区 + 江苏 13 市 + 浙江 11 市 + 安徽 16 市 |
| 运行模式 | **A + B**。A = 按需手动采集（双击即跑，约 3 秒）；B = **用户手动启动的前台定时采集会话**（立即采一次，之后每 30 分钟一次，关闭窗口或关机即停止；**不做任何开机自启注册，重启后默认关闭**） |
| 数据库 | **SQLite**（SQLAlchemy 抽象，可平滑切换 MySQL/PostgreSQL） |
| 历史数据 | 日数据 **3 年** + 小时数据 **1 年** |
| 后端 | Python 3.13 + FastAPI + SQLAlchemy + APScheduler |
| 前端 | Vue 3 + Vite + TypeScript + Vue Router + Pinia + ECharts 5 |
| 部署 | **暂缓决策**；架构按"可部署"标准编写，三种方案均可平滑切换 |

---

## 3. 数据源与可行性验证

> 以下全部为**实测结论**，非推断。

### 3.1 Open-Meteo（主数据源）

| 项目 | 实测结果 |
|---|---|
| 是否需要 API Key | ❌ 不需要 |
| 免费额度 | 10,000 次/天、5,000 次/小时、600 次/分钟 |
| Python 直连 | ✅ 成功（返回真实逐小时降水序列） |
| 批量请求 | ✅ 56 个坐标合并为 **1 次 HTTP 请求**，耗时 **4.4 秒**，URL 长 1299 字符 |
| `past_days` 上限 | **92 天**（实测 92 成功、100 返回 HTTP 400） |
| 历史回溯 | ✅ archive 接口正常，可回溯至 1940 年 |
| 3 年日数据回填 | 单点 **1.2 秒**、1096 天、20.8 KB；56 点串行约 **1.1 分钟** |
| 许可 | CC BY 4.0，**非商业使用免费，须署名** |

**额度核算（按最坏情况：每点位各计一次调用）**

| 维度 | 消耗 | 占额度 | 余量 |
|---|---|---|---|
| 每日（30 分钟一轮） | 56 × 48 = **2,688 次** | 26.9% | **3.7 倍** |
| 每小时 | 56 × 2 = **112 次** | 2.2% | 44 倍 |

> 结论：**30 分钟采集频率安全可行**。若官方按"请求数"计费，则仅 48 次/天（0.48%）。

### 3.2 DataV GeoAtlas（地图边界）

| 项目 | 实测结果 |
|---|---|
| 接口 | `https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json` |
| 上海 `310000` | 16 个 `level=district` 要素 |
| 江苏 `320000` | 13 个 `level=city` 要素 |
| 浙江 `330000` | 11 个 `level=city` 要素 |
| 安徽 `340000` | 16 个 `level=city` 要素 |
| 要素字段 | `adcode / name / center / centroid / level / parent` |

### 3.3 ⚠️ 关键实测发现：答辩当日大概率无降水

对 56 个点位的 72 小时真实降水统计：

```
total_values=4032   nonzero=74 (1.8%)   total_mm=29.4
wettest_point_72h = 温州市  8.8mm
```

**仅 1.8% 的"小时×点位"记录存在降水。** 这不是缺陷，是天气本身。因此系统**必须**具备：

1. **历史回放模式** —— 可指定历史时段（如梅雨季暴雨日）回放，保证演示始终有内容
2. **空态设计** —— 无降水时展示"当前长三角无降水 + 最近一次降水时间 + 采集心跳"，而非空白

### 3.4 本机环境

| 项 | 状态 |
|---|---|
| Node.js | v24.18.0 ✅ |
| pnpm / npm | 11.8.0 / 可用 ✅ |
| Python | 3.13.5 ✅ |
| 虚拟环境 | `.venv`（项目内）✅ |
| 已装依赖 | pandas 2.3.3、numpy 2.3.3、requests 2.34.2、httpx 0.28.1 |
| 本项目新增依赖 | fastapi、uvicorn、sqlalchemy、apscheduler（装在 `.venv`） |
| MySQL / PostgreSQL / Docker | ❌ 均未安装（故选用 SQLite） |
| PowerShell 直连 HTTPS | ❌ TLS 中断（本机 PS 网络栈问题）；**Python 直连正常**，采集器用 Python 编写 |
| **系统临时目录** | ❌ **不可用**：Python `tempfile` 报 `No usable temporary directory found`，会导致 pip/venv 空转卡死。**必须把 `TMP`/`TEMP`/`TMPDIR` 指向工作区 `.tmp`**（已在 `scripts\setup.bat` 内置） |
| pip 缓存 | ⚠️ 疑有损坏（458 MB），安装统一加 `--no-cache-dir` |

### 3.5 依赖安装结果（已完成）

`.venv` 虚拟环境（Python 3.13.5）中已验证的版本：

| 包 | 版本 |
|---|---|
| fastapi | 0.142.2 |
| uvicorn | 0.54.0 |
| sqlalchemy | 2.1.3 |
| apscheduler | 3.11.3 |

> ⚠️ **待确认**：采集器还需要 HTTP 客户端与统计库。全局 Python 已有 `requests 2.34.2`、`pandas 2.3.3`、`numpy 2.3.3`，但 `.venv` 是隔离环境**取不到**。三个可选方案见 `requirements.txt` 末尾注释。

---

## 4. 系统架构

```
┌──────────────────────┐        ┌──────────────────────┐
│  Open-Meteo API      │        │  DataV GeoAtlas      │
│  (实时 + 历史降水)    │        │  (行政区划 GeoJSON)   │
└──────────┬───────────┘        └──────────┬───────────┘
           │ 30 分钟定时 / 历史回填          │ 一次性下载
           ▼                               ▼
   ┌────────────────────┐          ┌─────────────────┐
   │  Collector 采集器   │          │  data/geojson/  │
   │  APScheduler 调度   │          │  长三角合并地图  │
   │  自愈补采 + 幂等写入 │          └────────┬────────┘
   └─────────┬──────────┘                   │
             ▼                              │
   ┌────────────────────────────┐           │
   │   SQLite  weather.db        │           │
   │   region / grid_point       │           │
   │   precip_hourly / _daily    │           │
   │   collect_log / alert / meta│           │
   └─────────┬──────────────────┘           │
             ▼                              │
   ┌────────────────────────────┐           │
   │  FastAPI 后端（REST API）    │           │
   │  分层：router → crud → model │           │
   └─────────┬──────────────────┘           │
             ▼ REST/JSON                    ▼
   ┌────────────────────────────────────────────────┐
   │  Vue 3 前端（Vite + TS + Router + Pinia）        │
   │  总览大屏│实时监测│空间分布│时间分析│城市对比      │
   │  预警统计│数据管理                              │
   └────────────────────────────────────────────────┘
```

---

## 5. 数据库设计

### 5.1 E-R 关系

```
region (60 行：4 省级 + 40 市级 + 16 区级)
   │ 1
   │
   │ N
grid_point (56 行：被监测的点位)
   │ 1                    │ 1
   ├──────────┐           │
   │ N        │ N         │ N
precip_hourly  precip_daily
   │
collect_log（独立采集审计表）
weather_alert（独立预警表，预留）
meta（键值配置表）
```

### 5.2 DDL（SQLite）

```sql
-- ============ 1. 行政区划表 ============
CREATE TABLE region (
    adcode        TEXT PRIMARY KEY,             -- 行政区划代码，如 310101
    name          TEXT NOT NULL,                -- 名称，如 黄浦区
    level         TEXT NOT NULL,                -- province / city / district
    parent_adcode TEXT,                         -- 父级 adcode
    province      TEXT NOT NULL,                -- 所属省市：上海 / 江苏 / 浙江 / 安徽
    lon           REAL NOT NULL,                -- 中心经度
    lat           REAL NOT NULL,                -- 中心纬度
    is_monitored  INTEGER NOT NULL DEFAULT 1,   -- 是否为采集点 (0/1)
    FOREIGN KEY (parent_adcode) REFERENCES region(adcode)
);
CREATE INDEX idx_region_parent ON region(parent_adcode);
CREATE INDEX idx_region_level  ON region(level);

-- ============ 2. 采集点表 ============
CREATE TABLE grid_point (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    region_adcode TEXT NOT NULL UNIQUE,         -- 一个区域一个采集点
    lon           REAL NOT NULL,
    lat           REAL NOT NULL,
    source        TEXT NOT NULL DEFAULT 'open-meteo',
    label         TEXT,                         -- 显示名
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (region_adcode) REFERENCES region(adcode)
);

-- ============ 3. 逐小时降水事实表（核心） ============
CREATE TABLE precip_hourly (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    point_id    INTEGER NOT NULL,
    obs_time    TEXT NOT NULL,                  -- ISO8601 'YYYY-MM-DDTHH:MM'
    precip_mm   REAL,                           -- 降水量 (mm)
    source      TEXT NOT NULL DEFAULT 'open-meteo',
    is_forecast INTEGER NOT NULL DEFAULT 0,     -- 0=实况/分析场 1=预报
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(point_id, obs_time, source),         -- ★ 幂等写入的关键
    FOREIGN KEY (point_id) REFERENCES grid_point(id)
);
CREATE INDEX idx_hourly_time        ON precip_hourly(obs_time);
CREATE INDEX idx_hourly_point_time  ON precip_hourly(point_id, obs_time);

-- ============ 4. 日降水汇总表 ============
CREATE TABLE precip_daily (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    point_id          INTEGER NOT NULL,
    obs_date          TEXT NOT NULL,            -- 'YYYY-MM-DD'
    precip_sum        REAL NOT NULL DEFAULT 0,  -- 日累计 (mm)
    precip_max_hourly REAL,                     -- 最大小时雨强 (mm)
    rain_hours        INTEGER NOT NULL DEFAULT 0, -- 有降水的小时数
    rain_level        TEXT,                     -- 按 GB/T 28592-2012 分级
    source            TEXT NOT NULL DEFAULT 'open-meteo',
    created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(point_id, obs_date, source),
    FOREIGN KEY (point_id) REFERENCES grid_point(id)
);
CREATE INDEX idx_daily_date ON precip_daily(obs_date);

-- ============ 5. 采集日志表（审计 / 数据质量） ============
CREATE TABLE collect_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source           TEXT NOT NULL,
    mode             TEXT NOT NULL,             -- realtime / backfill / manual
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    status           TEXT NOT NULL,             -- running / success / partial / failed
    points_total     INTEGER NOT NULL DEFAULT 0,
    rows_upserted    INTEGER NOT NULL DEFAULT 0,
    gap_filled_hours INTEGER NOT NULL DEFAULT 0,
    error_msg        TEXT
);
CREATE INDEX idx_log_started ON collect_log(started_at);

-- ============ 6. 气象预警表（预留，可选数据源） ============
CREATE TABLE weather_alert (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    region_adcode TEXT NOT NULL,
    alert_type    TEXT NOT NULL,                -- 暴雨 / 雷电 / 大风
    alert_level   TEXT,                         -- 蓝 / 黄 / 橙 / 红
    title         TEXT,
    published_at  TEXT,
    source        TEXT,
    raw_json      TEXT,
    UNIQUE(region_adcode, alert_type, published_at, source)
);

-- ============ 7. 元数据表（键值配置与状态） ============
CREATE TABLE meta (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

### 5.3 幂等写入策略

采集器统一使用 SQLite 的 UPSERT：

```sql
INSERT INTO precip_hourly (point_id, obs_time, precip_mm, source, is_forecast)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(point_id, obs_time, source)
DO UPDATE SET precip_mm = excluded.precip_mm;
```

**效果**：采集器可以任意重复运行、中途崩溃后重跑、关机数天后补采，**都不会产生重复数据，也不会丢数据**。

### 5.4 数据量估算

| 表 | 行数估算 | 说明 |
|---|---|---|
| `region` | 60 | 静态 |
| `grid_point` | 56 | 静态 |
| `precip_hourly` | 56 × 8,760 ≈ **49 万** | 1 年小时数据 |
| `precip_daily` | 56 × 1,095 ≈ **6.1 万** | 3 年日数据 |
| `collect_log` | 约 1.7 万/年 | 30 分钟一次 |
| **合计** | **约 57 万行** | SQLite 约 40–70 MB，压力极小 |

---

## 6. 业务规则

### 6.1 降水量等级（GB/T 28592-2012）

依据中国气象局公布的国家标准（[官方页面](https://www.cma.gov.cn/2011xzt/2013zhuant/20130620_3/2013062002/201308/t20130816_223400.html)）：

| 等级 | 12 小时降水量 (mm) | 24 小时降水量 (mm) |
|---|---|---|
| 微量降雨（零星小雨） | — | < 0.1 |
| 小雨 | 0.1 – 4.9 | 0.1 – 9.9 |
| 中雨 | 5.0 – 14.9 | 10.0 – 24.9 |
| 大雨 | 15.0 – 29.9 | 25.0 – 49.9 |
| 暴雨 | 30.0 – 69.9 | 50.0 – 99.9 |
| 大暴雨 | 70.0 – 139.9 | 100.0 – 249.9 |
| 特大暴雨 | ≥ 140.0 | ≥ 250.0 |

> 本项目日数据按 **24 小时**口径分级；如需 12 小时口径，另加 `rain_level_12h` 字段。

### 6.2 统计口径

| 指标 | 定义 |
|---|---|
| 日累计降水 | 当日 00:00–23:59 逐小时降水之和 |
| 最大小时雨强 | 当日逐小时降水的最大值 |
| 有雨小时数 | 当日 `precip_mm > 0` 的小时数 |
| 降水距平 | (当期实测值 − 同期 3 年平均值) / 同期 3 年平均值 × 100% |
| 区域降水覆盖率 | 当前时刻有降水的点位数 / 总点位数 |

> ⚠️ **论文中必须如实说明**：距平基准为 3 年样本，样本期偏短，结论仅作趋势示意，不作气候结论。

---

## 7. 采集器设计

### 7.1 采集流程

```
启动 → 读取 region/grid_point → 构造 56 点坐标列表
     → 单次批量请求 forecast API (past_days=3, hourly=precipitation)
     → 解析 56 个返回对象
     → 拆分为 实况小时(is_forecast=0) / 预报小时(is_forecast=1)
     → UPSERT 写入 precip_hourly
     → 重算受影响日期的 precip_daily
     → 写 collect_log
```

### 7.2 三种采集模式

| 模式 | 触发 | 数据范围 | 用途 |
|---|---|---|---|
| `realtime` | APScheduler 每 30 分钟 | 过去 3 天 + 未来 7 天 | 日常实时监测 |
| `backfill` | 手动执行一次 | 3 年日数据 + 1 年小时数据 | 初始化历史库 |
| `manual` | 前端"数据管理"按钮 | 同 realtime | 演示 / 补数 |

### 7.3 自愈补采机制

- 每轮固定回拉 `past_days=3`，任何一轮失败都不影响后续补齐
- 超过 3 天的空缺由 `backfill` 模式的 **92 天上限** 覆盖
- 超过 92 天由 archive 历史接口覆盖（可回溯至 1940 年）

**这是本项目的核心工程亮点**：即使采集器只在电脑开机时运行，数据库仍保持完整无缺口。

### 7.4 B 方案：前台定时采集会话（2026-10-07 重新设计）

**设计目标（用户要求）**：由用户自己控制开始，启动后每 30 分钟写一次库，直到关机；
**下一次开机（含快速启动）默认是关着的**。

| 特性 | 实现方式 |
|---|---|
| 用户控制开始 | 双击 `scripts\start_autocollect.bat`，或运行 `python -m collector.scheduler` |
| 每 30 分钟写库 | APScheduler `BlockingScheduler` + `IntervalTrigger(minutes=30)` |
| 前台常驻 | 进程与命令行窗口绑定，窗口关闭即结束 |
| **重启后默认关闭** | **不做任何系统注册**：不写注册表 Run 键、不放启动文件夹、不建计划任务。因此正常重启与「快速启动」（仅内核会话休眠、不保留用户进程）都不会恢复它 |
| 随时可停 | Ctrl+C，或直接关窗口 |
| 数据完整性 | 每轮仍回拉 `past_days=3` 并幂等 UPSERT，停机缺口下次启动自动补齐 |
| 单次失败不中断 | 采集异常被捕获并记入 `collect_log`，下一轮自动重试 |
| 休眠/漏触发 | `coalesce=True` + `misfire_grace_time=300`：错过多次只补跑一次，其余由自愈补采覆盖 |

**资源占用实测**（一次采集）：持续 **3.1 秒**、峰值内存 **74 MB**、**1 个 HTTP 请求约 116 KB**、平均 CPU ≈ **0.17%**、磁盘 **+209 KB/天**。

> 与「开机自启」的关键区别：本方案把控制权完全交给用户，**不存在"装了一次就永远在跑"的情况**。

---

## 8. 后端 API 设计

### 8.1 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/meta` | 系统与数据源状态、最后采集时间、点位数 |
| GET | `/api/regions` | 区域树（省→市/区），含中心坐标 |
| GET | `/api/overview/summary` | 总览指标卡：24h 累计、最大雨强、有雨点位数、覆盖率 |
| GET | `/api/overview/ranking` | 城市降水排行 |
| GET | `/api/realtime/latest` | 各点最新观测小时与降水值（地图 + 卡片数据源） |
| GET | `/api/realtime/timeseries` | 指定区域近 N 小时序列 |
| GET | `/api/spatial/map` | 指定时刻全区分级设色数据 |
| GET | `/api/spatial/timespan` | 时间区间内的降水场（供时间轴回放） |
| GET | `/api/trend/daily` | 日降水序列 |
| GET | `/api/trend/monthly` | 月累计序列 |
| GET | `/api/trend/anomaly` | 降水距平 |
| GET | `/api/trend/level-distribution` | 雨量等级分布 |
| GET | `/api/compare/ranking` | 多指标排行 |
| GET | `/api/compare/multi` | 多城市序列对比 |
| GET | `/api/compare/boxplot` | 城市降水分布箱线数据 |
| GET | `/api/alerts` | 预警列表（预留） |
| GET | `/api/admin/collect-logs` | 采集日志 |
| POST | `/api/admin/collect-now` | 手动触发采集 |
| GET | `/api/admin/quality` | 数据质量报告（缺测率、覆盖小时数） |
| GET | `/api/export/csv` | 导出 CSV |

### 8.2 分层结构

```
routers/    路由层：参数校验、HTTP 语义
crud.py     数据访问层：SQL 查询与聚合
models.py   ORM 模型：表结构定义
schemas.py  Pydantic 模型：请求/响应契约
config.py   配置：数据库路径、CORS、采集参数（支持 .env）
```

### 8.3 缓存策略

聚合类接口（overview / ranking / map）使用**进程内 TTL 缓存**（默认 60 秒），避免大屏自动刷新时反复全表聚合。

---

## 9. 前端模块与路由

| 路由 | 模块 | 核心可视化 | 主要交互 |
|---|---|---|---|
| `/overview` | **总览大屏** | 指标卡 + 分级设色地图 + Top10 排行 + 24h 趋势 | 自动刷新、点击城市联动 |
| `/realtime` | **实时监测** | 近 48h 逐小时柱线图、点位热力、采集心跳 | 刷新间隔可调、暂停、最新时刻高亮 |
| `/spatial` | **空间分布** | 长三角合并地图（分级设色/散点/热力） | 时间轴回放、省→市下钻、图层切换 |
| `/trend` | **时间分析** | 日/月累计柱线组合、距平、雨量等级饼图 | 时间范围选择、区域切换 |
| `/compare` | **城市对比** | 多城市折线、排行榜、箱线图、雷达图 | 勾选对比城市、指标切换 |
| `/alerts` | **预警与统计** | 预警列表、极值统计、分级表 | 按等级/时间筛选 |
| `/data` | **数据管理** | 采集日志时间线、数据质量报告 | 手动采集、CSV 导出、数据源状态 |

### 9.1 交互设计（评分"感知性"的得分点）

1. **时间轴回放** —— 拖动滑条看降水场逐小时演变，答辩保命功能
2. **图表联动** —— 点击地图某城市，其余图表全部切换到该城市
3. **下钻** —— 省级 → 市级/区级
4. **自动刷新** —— 30s / 1min / 5min 可调 + 暂停
5. **数据导出** —— 当前视图导出 CSV
6. **空态设计** —— 无降水时展示最近降水时间与采集心跳

### 9.2 视觉规范

- 统一暗色主题（深蓝渐变底 + 高对比数据色）
- 降水配色遵循气象习惯：浅蓝（小）→ 蓝 → 黄 → 橙 → 红（特大暴雨）
- 大屏布局用 `transform: scale()` 等比缩放，避免多分辨率错位
- 统一字体、间距、圆角、卡片阴影变量（CSS Variables）

---

## 10. 目录结构

```
D:\visualization\
├── README.md
├── .gitignore
├── .venv/                          # 项目虚拟环境（不提交）
├── docs/
│   ├── PLAN.md                     # ← 本文件
│   └── DATA_SOURCE.md              # 数据源与额度核实记录
├── backend/                        # FastAPI 后端
│   ├── app/
│   │   ├── main.py                 # 应用入口、CORS、路由挂载
│   │   ├── config.py               # 配置（.env 支持）
│   │   ├── db.py                   # 引擎与会话
│   │   ├── models.py               # ORM 模型（7 张表）
│   │   ├── schemas.py              # Pydantic 契约
│   │   ├── crud.py                 # 数据访问与聚合
│   │   └── routers/                # 7 个模块化路由
│   └── tests/
├── collector/                      # 采集器
│   ├── regions.py                  # 56 点位构建
│   ├── geojson.py                  # GeoJSON 下载与合并
│   ├── openmeteo.py                # Open-Meteo 客户端
│   ├── pipeline.py                 # 采集主流程（自愈 + 幂等）
│   ├── backfill.py                 # 历史回填
│   ├── scheduler.py                # 30 分钟调度
│   └── sources/
├── frontend/                       # Vue 3 前端
│   ├── src/
│   │   ├── main.ts
│   │   ├── router/                 # 导航路由
│   │   ├── stores/                 # Pinia 状态
│   │   ├── api/                    # 接口封装
│   │   ├── components/             # 通用组件（图表、卡片、筛选器）
│   │   ├── views/                  # 7 个模块页面
│   │   └── styles/                 # 视觉规范变量
│   └── .env                        # API 地址（可切换本机/局域网/公网）
├── data/
│   ├── weather.db                  # SQLite 数据库
│   ├── geojson/                    # 行政区划 GeoJSON
│   └── snapshots/                  # 数据快照（¥0 部署方案用）
└── scripts/
    ├── setup.bat                   # 一键安装依赖（含临时目录修正）
    ├── init_db.bat                 # 建表 + 地图合并 + 56 点位入库
    ├── backfill.bat                # 历史回填（3 年日 + 1 年小时 + 补齐最近月）
    ├── collect_once.bat            # A 模式：手动采集一次
    ├── start_autocollect.bat       # B 模式：前台定时采集会话（关闭窗口即停）
    ├── run_backend.bat             # 启动后端 API（可传 host/port 切局域网）
    ├── run_frontend.bat            # 启动前端（可传 lan 切局域网）
    └── export_snapshot.bat         # 导出静态快照（P10 阶段生成，¥0 部署方案用）
```

---

## 11. 里程碑与任务清单

| 阶段 | 任务 | 产出 | 预估 |
|---|---|---|---|
| **P0 骨架** | 目录结构、虚拟环境、依赖安装、规划文档 | ✅ 已完成 | 0.5 天 |
| **P1 数据层** | 建表、GeoJSON 下载合并、56 点位入库 | ✅ 已完成（`weather.db` 已可用） | 1 天 |
| **P2 采集器** | Open-Meteo 客户端、自愈采集、幂等写入、采集日志 | ✅ 已完成（已跑通真实采集） | 1 天 |
| **P3 历史回填** | 3 年日数据 + 1 年小时数据回填 | ✅ 已完成（55 万行入库） | 0.5 天 |
| **P4 后端** | 9 组路由 + 聚合查询 + 缓存 + 质量报告 | ✅ 已完成（21 个接口全部通过冒烟测试） | 1.5 天 |
| **P5 前端骨架** | 项目初始化、路由导航、布局、视觉规范、API 封装 | ✅ 已完成（7 个模块可点通；总览、数据管理已接真实数据） | 1.5 天 |
| **P6 总览大屏** | 指标卡、合并地图、排行、趋势 | ✅ 已完成（分级设色地图 + 趋势 + 等级分布 + 时间轴） | 1.5 天 |
| **P7 分析模块** | 实时监测、空间分布、时间分析、城市对比（+ 预警统计） | ✅ 已完成（5 个模块全部接真实数据） | 2.5 天 |
| **P8 面向用户优化** | 按数据可视化流水线补齐「感知层」与「知识层」，打通三条交互反馈（详见第 24 节） | ⏳ 进行中（3/9 完成：下钻抽屉、时效警示、一键启动+演示模式） | 1~1.5 天 |
| **P9 数据管理** | 采集日志、质量报告、导出 | ✅ 已完成（P5 阶段一并落地） | 0.5 天 |
| **P10 收尾** | 测试、论文/报告、答辩材料、演示录屏、Git 版本管理 | 交付物齐备 | 2 天 |
| | | **合计** | **约 16 天** |

---

## 12. 部署方案（暂缓决策）

架构上已保证三种方案均可平滑切换：

| 方案 | 成本 | 前置条件 |
|---|---|---|
| **本机运行** | ¥0 | 无 |
| **本机 + 局域网** | ¥0 | 同 WiFi，改两个 `--host` 参数 |
| **公网：静态快照** | ¥0 | 前端静态托管（Vercel/GitHub Pages 免费）+ 导出快照 |
| **公网：完整后端** | ≈¥17/月 | Fly.io 最小实例（$2.19/月 + $0.15/GB 卷），SQLite 直接跑 |
| **公网：国内学生机** | 首年 ¥38–99 | 阿里云/腾讯云；域名 + 80/443 需 ICP 备案（用 IP:端口可规避） |

> 关键设计：前端 API 地址走 `.env`，后端提供快照导出命令，因此**部署决策可以推迟到最后**。

---

## 13. 风险登记册

| # | 风险 | 影响 | 对策 | 状态 |
|---|---|---|---|---|
| R1 | 答辩当日无降水，大屏全 0 | 演示失败 | 时间轴回放 + 空态设计 | 已设计 |
| R2 | API 额度超限 | 采集中断 | 30 分钟频率仅用 26.9%，余量 3.7 倍；批量请求 | 已核算 |
| R3 | 采集器停机造成数据缺口 | 数据不完整 | `past_days=3` 自愈 + 92 天补采 + archive 兜底 | 已设计 |
| R4 | 距平样本期仅 3 年，统计意义弱 | 论文被质疑 | 论文如实标注"趋势示意，不作气候结论" | 已声明 |
| R5 | 本机 PowerShell 无法直连 HTTPS | 脚本用 PS 写会失败 | 采集统一用 Python；PS 脚本只做调度 | 已规避 |
| R6 | 数据源许可 | 合规风险 | Open-Meteo 为 CC BY 4.0，非商业免费；页面与论文均署名 | 已确认 |
| R7 | SQLite 并发写入（采集器 + 后端） | 锁冲突 | 开启 WAL 模式；采集写入短暂，读写分离 | 待实施 |
| R8 | 系统临时目录不可用 + pip 缓存损坏 | 依赖装不上、脚本卡死 | 所有脚本内置 `TMP/TEMP/TMPDIR` 重定向 + `--no-cache-dir` | **已定位并绕过** |
| R9 | `.venv` 取不到全局的 requests/pandas/numpy | 采集器无法运行 | 装进 `.venv`（推荐）或重建时加 `--system-site-packages`，或改用标准库 urllib | 待确认 |

---

## 14. 论文/报告写作要点（对齐评分标准）

| 评分项 | 论文对应章节 | 可写的实证材料 |
|---|---|---|
| ① **真实性、可用性** | 数据源与数据处理 | Open-Meteo 官方数据、56 点位真实坐标、幂等采集不重不漏、采集日志与缺测率质量报告、CC BY 4.0 署名 |
| ② **感知性、可行性** | 可视化设计 | 每张图的选型理由（为什么用分级设色而非热力图）、时间轴回放揭示降水移动规律、图表联动支持下钻 |
| ③ **艺术性、设计性** | 界面与交互设计 | 统一视觉规范（配色/字号/间距）、大屏栅格布局、气象惯用降水配色 |
| ④ **创新性、有价值** | 系统亮点 | 自愈式采集机制、历史回放引擎、GB/T 28592 国标分级、距平分析 |

### 建议纳入论文的"硬证据"

- 额度核算表（56 点 × 48 轮 = 2,688 次/天，占免费额度 26.9%）
- 批量请求实测数据（56 坐标单请求，4.4 秒）
- 72 小时降水覆盖率统计（1.8%），佐证回放功能的必要性
- 数据完整性校验结果（停机 T 天后补采行数 = 理论值）

---

## 15. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-04 | 初版：方案确认，P0 骨架完成 |
| 2026-10-07 | P1 完成：7 张表建立、GeoJSON 下载并合并为 56 要素地图、60 条行政区划与 56 个采集点入库；幂等性验证通过（二次运行 0 新增 / 60+56 更新） |
| 2026-10-07 | P2 完成：采集器跑通真实采集，三次运行验证幂等；修复 SQLite 临时目录依赖问题（`temp_store=MEMORY` + 配置层临时目录自愈） |
| 2026-10-07 | P3 完成：回填 3 年日数据（61,432 行）+ 1 年小时数据（491,904 行），补桥最近 30 天；库内共 54 万小时行 + 6.3 万日行，缺测率 0%，覆盖率 100% |
| 2026-10-07 | **B 方案重新设计**（用户要求）：由「注册开机自启的计划任务」改为「**用户手动启动的前台定时采集会话**」—— 立即采一次，之后每 30 分钟一次，关窗口/关机即停，不做任何系统注册，**重启后默认关闭**；自愈补采机制不变 |
| 2026-10-07 | P4 完成：后端 21 个接口全部通过冒烟测试（均 200，响应 < 300ms），内容正确性抽查通过；修复「无降水时误报极值点位」的语义瑕疵 |
| 2026-10-07 | P5 完成：Vue 3 前端骨架搭建，7 个模块路由可点通，总览与数据管理接真实数据；类型检查 0 错误，生产构建 861ms |
| 2026-10-07 | **前端运行时去 DSH 化**：改用独立安装的 pnpm 12.5.1（`%APPDATA%\npm\pnpm.cmd`，基于独立 Node）；在 `pnpm-workspace.yaml` 显式设置 `minimumReleaseAge: 0` 以统一 pnpm 11/12 行为；脚本显式指定 pnpm 路径，不再受 PATH 注入影响 |
| 2026-10-07 | P6 完成：总览大屏落地分级设色地图（56 要素）、24h 趋势柱状图、降水等级环形图、时间轴切换；修复两个真实缺陷（ECharts 地图注册时序、Vite 监听临时文件崩溃） |
| 2026-10-09 | P7 完成：5 个分析模块全部接入真实数据（实时监测 / 空间分布含时间轴回放 / 时间分析 / 城市对比 / 预警统计），新增 8 个图表组件与 1 个后端接口；修复「时间轴回放预设时段超出小时数据范围」的缺陷 |
| 2026-10-09 | **修复全部 9 个 `.bat` 脚本无法运行的问题**（严重）：系统代码页 936 与 UTF-8 脚本冲突导致 cmd 按字节切断中文、整份脚本解析错乱；改为纯 ASCII 脚本 + Python 输出中文。新增 `status.bat`（端口状态）与 `stop_all.bat`（按端口停止服务） |
| 2026-10-09 | **新增 P8 面向用户优化计划**（第 24 节）：以数据可视化流水线（含三条人机交互反馈）为标尺逐段评估 —— ②采集 85% / ③处理 75% / ④映射 80% / ⑤感知 55% / ⑥知识 35%；按 Shneiderman 任务清单发现 Details-on-demand、Relate、Extract 三项缺失；排出 9 项优化清单与实施顺序 |
| 2026-10-09 | **初始化 Git 仓库**并完成首次提交，开始版本化管理 |
| 2026-10-16 | **P8-1 完成：点位下钻抽屉（Details-on-demand）**。新增 `GET /api/regions/{adcode}/detail`（一次取全逐小时+逐日+等级+极值+汇总，OpenAPI 增至 24 条）；前端新增 `stores/detail.ts` 与 `DetailDrawer.vue`，并让 `BaseChart`/`RainMap`/`PointMatrix`/`RankingBarChart` 支持点击下钻；4 个页面的 6 个入口已接入。实测：接口 21~89 ms，与已有接口一致性校验全部吻合，地图与排行两条触发路径经浏览器截图确认可用 |
| 2026-10-21 | **P8-2 完成：数据时效三态警示**。修复一个会误导用户的真实缺陷 —— `meta.hourly_end` 未过滤 `is_forecast`，导致页头「数据时刻」显示的是**未来 157 小时**的预报时刻，且数据已陈旧 123.9 小时仍亮绿色「采集正常」。后端 `/api/meta` 新增 `observed_start`/`observed_end`/`forecast_end`/`server_now`；前端按 <2h 绿 / 2–24h 黄 / >24h 红三态显示，并增加颜色提示条与处置建议。三态均经浏览器截图验证；顺带用 30 天窗口采集补齐了 6,720 行真实缺口 |
| 2026-10-21 | **P8-3（部分）：一键启动 `scripts\start.bat`**。把「起后端 + 起前端 + 开浏览器 + 起定时采集」合并为一次点击：环境自检 → 后端 → 轮询 `/api/health` 等就绪 → 前端 → 轮询首页等就绪 → 浏览器 → 采集器 → 打印地址。已启动的部分按端口/PID 锁自动 `[SKIP]`，可安全重复运行。配套给 `collector/scheduler.py` 增加**单实例锁**（`.tmp/scheduler.pid` + PID 存活检查），防止误开两个采集器翻倍消耗 API 额度。实测：后端 2 秒、前端 1 秒就绪，重复运行零新增进程 |
| 2026-10-21 | **P8-3 完成：演示模式**。新增 `stores/app` 演示态与 `PresentationBar.vue`（底部浮动条：时效灯 + 7 模块切换 + 全屏 + 退出）；`?demo=1` 或页头图标进入，侧边栏与页头隐藏、内容整屏；`TimeScrubber` 新增 `autoplay`，演示时时间轴自动播放；`start.bat demo` 直达 2026-08-09~10 大暴雨回放。踩到并解决两个浏览器限制：`requestFullscreen` 需用户手势、全屏时 `Esc` 不派发给网页（改用 `fullscreenchange` + 抑制时间窗兜底） |

---

## 16. P1 完成情况（实测记录）

```
[1/4] 建表 ...            数据库文件: D:\visualization\data\weather.db
[2/4] 下载并合并 GeoJSON
      310000: 16 个要素   320000: 13 个要素
      330000: 11 个要素   340000: 16 个要素
      合并地图: yrd_merged.json（56 个要素）
[3/4] 写入行政区划与采集点
      行政区划: 新增 60 条，更新 0 条
      采集点:   新增 56 个，更新 0 个
[4/4] 校验
      region 总数: 60（其中参与监测 56）    grid_point 总数: 56
      上海 district 16 | 安徽 city 16 | 江苏 city 13 | 浙江 city 11
      [OK] 校验通过
```

**二次运行（幂等性验证）**：`新增 0 条，更新 60 条` / `新增 0 个，更新 56 个` —— 确认可重复执行不产生重复数据。

**数据库实测状态**：7 张表、6 个索引、`journal_mode=wal`、`region` 60 行、`grid_point` 56 行。

**产出文件**：

| 文件 | 大小 |
|---|---|
| `data/weather.db` | 88 KB |
| `data/geojson/yrd_merged.json`（长三角合并地图，56 要素） | 458 KB |
| `data/geojson/{310000,320000,330000,340000}.json` | 89–135 KB |

---

## 17. P2 完成情况（采集器，实测记录）

### 17.1 首次真实采集

```
点位数=56  past_days=3  forecast_days=7
Open-Meteo 单次批量请求返回 56 个点位

写入 13440 行（新增 13440，更新 0）
实况 4928 行 / 预报 8512 行
日汇总重算 224 组（点位×日期）
库内累计：小时 13440 行，日 224 行

有降水的小时数：675，累计 588.1 mm
最湿点位：宁波市（50.5 mm）
耗时 3.3 秒
```

- 13,440 = 56 点 × 240 小时（past_days 3 天 + forecast_days 7 天 = 72 + 168）
- 实况 4,928 = 56 × 88 小时（过去 3 天整 + 当日已过小时）；预报 8,512 = 56 × 152 小时
- **单次 HTTP 请求拉取 56 个点位，全程 3.3 秒**

### 17.2 幂等性验证（连续运行三次）

| 运行 | 写入行数 | 新增 | 更新 | 库内小时总数 |
|---|---|---|---|---|
| 第 1 次 | 13,440 | 13,440 | 0 | 13,440 |
| 第 2 次 | 13,440 | **0** | 13,440 | **13,440**（未翻倍） |
| 第 3 次（quiet） | 13,440 | **0** | 13,440 | **13,440** |

**结论：重复运行不产生重复数据，幂等成立。**

### 17.3 采集审计（collect_log）

| id | 模式 | 状态 | 点位数 | 写入 | 新增 | 时间 |
|---|---|---|---|---|---|---|
| 1 | manual | **failed** | 56 | 0 | 0 | 15:24:08→15:24:10 |
| 2 | manual | success | 56 | 13,440 | 13,440 | 15:24:28→15:24:31 |
| 3 | manual | success | 56 | 13,440 | 0 | 15:24:38→15:24:43 |
| 4 | manual | success | 56 | 13,440 | 0 | 15:24:43→15:24:46 |

> 第 1 条 `failed` 是真实发生的故障记录（SQLite 临时目录缺失），
> **恰好证明了审计链路有效**：失败也会留痕，这正是论文「数据质量与完整性」一节的实证材料。

### 17.4 国标分级的实际输出（GB/T 28592-2012）

| 点位 | 日期 | 日累计 (mm) | 最大小时 (mm) | 有雨小时 | 等级 |
|---|---|---|---|---|---|
| 宁波市 | 2026-10-04 | 50.3 | 6.6 | 23 | **暴雨** (50.0–99.9) ✓ |
| 舟山市 | 2026-10-04 | 38.1 | 6.0 | 24 | **大雨** (25.0–49.9) ✓ |
| 嘉兴市 | 2026-10-04 | 28.6 | 4.5 | 19 | 大雨 ✓ |
| 绍兴市 | 2026-10-04 | 26.3 | 3.9 | 24 | 大雨 ✓ |
| 金山区 | 2026-10-04 | 24.6 | 3.8 | 19 | **中雨** (10.0–24.9) ✓ |
| 杭州市 | 2026-10-04 | 23.6 | 3.2 | 22 | 中雨 ✓ |

等级分布：无降水 168 / 小雨 32 / 中雨 20 / 大雨 3 / 暴雨 1

**分级边界与国标一致**，可直接用于论文的等级分布图。

### 17.5 本轮修复的缺陷

| 问题 | 现象 | 根因 | 修复 |
|---|---|---|---|
| SQLite 写入失败 | `sqlite3.OperationalError: unable to open database file` | `TMP` 指向的 `.tmp` 被清理掉，SQLite 建临时文件失败 | ① `config.py` 导入时**自愈**：自动创建 `.tmp` 并设置 `TMP/TEMP/TMPDIR`；② `db.py` 增加 `PRAGMA temp_store=MEMORY`，不再依赖磁盘临时目录 |

**自愈验证**：在 `.tmp` 不存在、且不设置任何环境变量的干净环境下执行采集，成功。

### 17.6 新增源码

| 文件 | 作用 |
|---|---|
| `collector/openmeteo.py` | Open-Meteo 客户端：56 点单次批量请求、3 次重试、点位数量校验 |
| `collector/pipeline.py` | 采集主流程：自愈补采 + 分块 UPSERT + 日汇总重算 + 采集审计 |
| `backend/app/levels.py` | GB/T 28592-2012 降水等级判定（12h/24h 双口径）+ 前端配色 |
| `scripts/collect_once.bat` | 双击采集一次 |

---

## 18. P3 完成情况（历史回填，实测记录）

### 18.1 回填执行

```
采集点: 56
日数据:   2023-09-07 ~ 2026-09-07（3 年，约 61,376 行）
小时数据: 2025-09-07 ~ 2026-09-07（365 天，约 490,560 行）

[1/3] 回填日数据 ...     日数据完成：61,432 行     （7 个批次）
[2/3] 回填小时数据 ...   小时数据完成：491,904 行   （14 个批次）
[3/3] 重算日汇总 ...     重算 20,720 组（点位×日期）

回填完成：日数据 61,432 行 + 小时数据 491,904 行
耗时 3.4 分钟
```

随后补齐再分析延迟造成的最近一个月缺口：

```
python -m collector.pipeline --mode backfill --past-days 30
写入 49728 行（新增 34944，更新 14784）
耗时 11.5 秒
```

### 18.2 库内规模

| 表 | 行数 |
|---|---|
| `region` | 60 |
| `grid_point` | 56 |
| `precip_hourly` | **540,288** |
| `precip_daily` | **63,112** |
| `collect_log` | 6 |

**时间覆盖**

| 数据 | 范围 | 行数 |
|---|---|---|
| 小时·实况 | 2025-09-07T00:00 ~ 2026-10-07T15:00 | 531,776 |
| 小时·预报 | 2026-10-07T16:00 ~ 2026-10-13T23:00 | 8,512 |
| 日数据 | 2023-09-07 ~ 2026-10-07 | 63,112 |

### 18.3 数据质量（论文核心实证）

| 指标 | 结果 |
|---|---|
| 小时降水 `NULL` | **0 / 540,288（缺测率 0.00%）** |
| 小时降水负值 | 0 |
| 小时覆盖率 | 2025-09-07T00:00 ~ 2026-10-07T15:00 = 每点 **9,496 小时** × 56 = **531,776 行，精确吻合，零缺口** |
| 日覆盖率 | 2023-09-07 ~ 2026-10-07 = **1,127 天** × 56 = **63,112 行，精确吻合** |

> 覆盖率核对方法：`(结束时刻 − 起始时刻)` 的全部整点 × 点位数 = 理论行数，
> 与实际行数逐位比对，而非按整天粗算（最后一天只到当前整点）。

**关于 `rain_hours` 为空**：40,936 行（前两年）为 `NULL`，表示**日值接口不提供小时明细**；
22,176 行（最近 396 天）有值，由小时数据重算得到。前端需把 `NULL` 显示为「无小时数据」，
不能显示为「0 小时有雨」。

### 18.4 日降水等级分布（3 年全量，GB/T 28592-2012）

| 等级 | 天数 |
|---|---|
| 无降水 | 31,374 |
| 小雨 | 24,620 |
| 中雨 | 5,021 |
| 大雨 | 1,614 |
| 暴雨 | 427 |
| 大暴雨 | 55 |
| 特大暴雨 | 1 |

### 18.5 历史极值 Top10（单日单点）

| 日期 | 点位 | 日累计 | 最大小时 | 雨时 | 等级 |
|---|---|---|---|---|---|
| 2026-08-09 | 台州市 | **328.7 mm** | 37.8 | 24 | **特大暴雨** (≥250) ✓ |
| 2026-08-10 | 苏州市 | 231.4 mm | 35.2 | 24 | 大暴雨 |
| 2026-08-10 | 台州市 | 168.1 mm | 39.0 | 24 | 大暴雨 |
| 2026-08-10 | 奉贤区 | 165.7 mm | 27.9 | 24 | 大暴雨 |
| 2026-08-10 | 常州市 | 165.6 mm | 29.4 | 24 | 大暴雨 |
| 2024-10-26 | 台州市 | 160.9 mm | — | — | 大暴雨 |
| 2024-10-26 | 温州市 | 158.0 mm | — | — | 大暴雨 |
| 2026-08-10 | 无锡市 | 154.5 mm | 26.4 | 24 | 大暴雨 |
| 2024-11-01 | 嘉兴市 | 152.9 mm | — | — | 大暴雨 |
| 2026-08-10 | 金山区 | 148.0 mm | 20.0 | 24 | 大暴雨 |

> **发现一个绝佳的演示素材**：**2026-08-10** 长三角出现区域性大暴雨过程，
> 苏州、台州、奉贤、常州、无锡、金山等地同日超 140mm。
> 这正是「时间轴回放」功能的最佳演示案例（对应风险 R1：答辩当日无降水）。
> 另一个可用案例是 2024-10-26（台州、温州）。

### 18.6 年度降水总量（趋势分析基准）

| 年份 | 全区平均 | 最少点位 | 最多点位 | 备注 |
|---|---|---|---|---|
| 2023 | 231.5 mm | 170.5 | 296.0 | **仅 9–12 月**（不完整） |
| 2024 | 1,452.0 mm | 920.9 | 2,188.0 | 完整年 |
| 2025 | 1,152.7 mm | 897.1 | 1,719.7 | 完整年 |
| 2026 | 1,265.2 mm | 688.3 | 1,987.7 | 截至 10 月 |

> 量级与长三角实际年降水量（约 1,000–1,500 mm）吻合，佐证数据真实合理。
> **距平分析只能用 2024 / 2025 两个完整年作基准**，2023 与 2026 为不完整年份，
> 论文中必须注明，不可混入气候态均值。

### 18.7 采集日志（全量审计）

| id | 模式 | 状态 | 写入 | 新增 | 时间 |
|---|---|---|---|---|---|
| 1 | manual | **failed** | 0 | 0 | 15:24:08 |
| 2 | manual | success | 13,440 | 13,440 | 15:24:28 |
| 3 | manual | success | 13,440 | 0 | 15:24:38 |
| 4 | manual | success | 13,440 | 0 | 15:24:43 |
| 5 | backfill | success | 553,336 | 491,904 | 15:26:55 |
| 6 | backfill | success | 49,728 | 34,944 | 15:30:22 |

### 18.8 本轮修复的问题

| 问题 | 现象 | 根因 | 处理 |
|---|---|---|---|
| 裸 `sqlite3` 连接的大表 GROUP BY 失败 | `unable to open database file` | 未走项目 db 层，SQLite 用系统临时目录建 B-tree | 验证/运维脚本一律加 `PRAGMA temp_store=MEMORY`；应用层已由 `db.py` 统一设置 |
| 历史日数据无法表达「无小时明细」 | `rain_hours` 非空，被迫填 0，与「确实 0 小时有雨」混淆 | 表结构设计缺陷 | 改为**可为空**：`NULL` = 无小时数据；表为派生数据，直接重建 |

### 18.9 新增源码

| 文件 | 作用 |
|---|---|
| `collector/backfill.py` | 历史回填：分块调用 archive-api、日/小时分离写入、重叠时段重算 |
| `collector/openmeteo.py`（扩展） | 新增 `fetch_archive()`：archive-api 客户端，支持 daily/hourly 与分批 |
| `scripts/backfill.bat` | 一键回填（回填 + 补齐最近一个月） |

---

## 19. P4 完成情况（后端 API，实测记录）

### 19.1 接口清单与冒烟测试结果

**21 个业务接口全部返回 200**，响应时间均 < 300 ms：

| 分组 | 接口 | 耗时 | 返回体 |
|---|---|---|---|
| 系统 | `GET /api/meta` | 62 ms | 367 B |
| 行政区划 | `GET /api/regions` | 4 ms | 9.0 KB |
| 行政区划 | `GET /api/regions/geojson` | 30 ms | **431 KB**（56 要素合并地图） |
| 总览 | `GET /api/overview/summary` | 41 ms | 406 B |
| 总览 | `GET /api/overview/ranking` | 20 ms | 411 B |
| 实时 | `GET /api/realtime/latest` | 16 ms | 10.9 KB |
| 实时 | `GET /api/realtime/timeseries` | 5 ms | 1.0 KB |
| 空间 | `GET /api/spatial/map` | 4 ms | 8.0 KB |
| 空间 | `GET /api/spatial/timespan` | 28 ms | 9.2 KB |
| 时间 | `GET /api/trend/daily` | 20 ms | 1.5 KB |
| 时间 | `GET /api/trend/monthly` | 14 ms | 446 B |
| 时间 | `GET /api/trend/anomaly` | 49 ms | 741 B |
| 时间 | `GET /api/trend/level-distribution` | 33 ms | 394 B |
| 对比 | `GET /api/compare/ranking` | 22 ms | 426 B |
| 对比 | `GET /api/compare/multi` | 21 ms | 1.7 KB |
| 对比 | `GET /api/compare/boxplot` | 4 ms | 637 B |
| 预警 | `GET /api/alerts` | 3 ms | 2 B（空，符合预期） |
| 管理 | `GET /api/admin/collect-logs` | 2 ms | 647 B |
| 管理 | `GET /api/admin/quality` | 256 ms | 443 B |
| 管理 | `POST /api/admin/collect-now` | **2.3 s** | 采集成功，幂等（新增 0） |
| 导出 | `GET /api/export/csv` | 4 ms | 240 B |

> 接口总数核对：以 **OpenAPI schema** 为准（FastAPI 0.142 的 `include_router`
> 不再把子路由摊平进 `app.routes`，故不能用 `len(app.routes)` 计数）。
> schema 中含 22 条路径 = 21 个业务接口 + `/api/health`。

### 19.2 数据质量接口的输出（论文直接可用）

```
hourly_rows          540288      hourly_null          0      hourly_null_pct   0.0
hourly_observed_rows 531776      hourly_forecast_rows 8512
observed_start       2025-09-07T00:00     observed_end  2026-10-07T15:00
distinct_hours       9496         expected_hours       9496
missing_hours        0            coverage_pct         100.0
daily_rows           63112        daily_with_detail    22176   daily_without_detail 40936
collect_total        10           collect_success      9       collect_failed    1
```

### 19.3 时间轴回放接口的实际输出（2026-08-10 大暴雨过程）

对 `GET /api/spatial/timespan?start=2026-08-09T20:00&end=2026-08-10T20:00` 的实测：

| 时刻 | 有雨点位 | 全区合计 | 前三位 |
|---|---|---|---|
| 08-09 20:00 | 44 / 56 | 124.9 mm | 台州 15.8、丽水 7.6 |
| 08-10 00:00 | 44 / 56 | 136.0 mm | 台州 17.8 |
| 08-10 04:00 | 50 / 56 | 208.8 mm | 奉贤 15.2、青浦 12.2 |
| 08-10 08:00 | 53 / 56 | 238.6 mm | 青浦 13.9、金山 11.4 |
| **08-10 12:00** | **56 / 56** | **272.3 mm** | **苏州 35.2、无锡 26.4、常州 18.0** |
| 08-10 16:00 | 56 / 56 | 192.5 mm | 台州 11.0 |

**降水场从"浙南局地"→"苏南上海全域暴雨"→"减弱"的完整演变清晰可见**，
这正是前端时间轴回放要播放的内容，也是风险 R1（答辩当日无降水）的解决方案。

### 19.4 距平接口输出（基准 = 2024/2025 完整年）

| 月份 | 实际 | 基准 | 距平 |
|---|---|---|---|
| 2026-06 | 10,037.4 mm | 15,893.2 mm | −36.8% |
| 2026-07 | 12,442.6 mm | 10,788.3 mm | +15.3% |
| **2026-08** | **17,722.2 mm** | **5,892.4 mm** | **+200.8%** |
| 2026-09 | 5,331.7 mm | 9,396.9 mm | −43.3% |

**2026 年 8 月距平 +200.8%**，与 18.5 节发现的历史极值（台州 328.7 mm）完全对应，
两条独立统计口径互相印证。

### 19.5 本轮修复的语义瑕疵

| 问题 | 现象 | 修复 |
|---|---|---|
| 无降水时误报极值点位 | 全区 0 降水时，`max_hourly_point` 仍返回「黄浦区」（值为 0.0），会误导用户以为该点位有降水 | 极值点位名仅在数值 **> 0** 时返回；否则为 `null`，前端显示「全区无降水」空态 |

**验证**：修复后全区无降水时段，`max_hourly_mm` / `max_hourly_point` / `max_hourly_time` /
`wettest_point` / `today_wettest_point` 全部为 `null`。

### 19.6 新增源码

| 文件 | 作用 |
|---|---|
| `backend/app/main.py` | 应用入口：CORS、9 个路由挂载、lifespan 建表、根路径跳转 `/docs` |
| `backend/app/schemas.py` | 13 个 Pydantic 契约（Swagger 文档即论文「接口设计」截图素材） |
| `backend/app/cache.py` | 进程内 TTL 缓存（summary 60s / map 120s / trend 300s） |
| `backend/app/crud.py` | 数据访问层：全部 SQL 聚合集中于此 |
| `backend/app/routers/` | 9 个模块化路由：meta / regions / overview / realtime / spatial / trend / compare / alerts / admin |
| `collector/scheduler.py` | **B 方案**：前台定时采集会话 |
| `scripts/start_autocollect.bat` | 双击启动 B 方案 |
| `scripts/run_backend.bat` | 启动后端（可传 host/port 切换本机/局域网） |

---

## 20. P5 完成情况（前端骨架，实测记录）

### 20.1 技术栈与版本（实际安装）

| 包 | 版本 |
|---|---|
| vue | 3.5.43 |
| vue-router | 4.6.4 |
| pinia | 2.3.1 |
| echarts | 5.6.0 |
| axios | 1.20.0 |
| vite | 6.4.4 |
| typescript | 5.6.3 |
| vue-tsc | 2.2.12 |

共安装 88 个包。

### 20.2 验证结果

**类型检查**：`pnpm typecheck` 退出码 **0**（0 错误）
**生产构建**：`pnpm build` 成功，**861 ms**，126 个模块

```
dist/index.html                          0.62 kB │ gzip:  0.38 kB
dist/assets/index-*.css                  8.27 kB │ gzip:  2.41 kB
dist/assets/OverviewView-*.js            7.32 kB │ gzip:  3.05 kB
dist/assets/DataManageView-*.js          8.37 kB │ gzip:  3.17 kB
dist/assets/vendor-*.js                153.68 kB │ gzip: 58.84 kB
```

**端到端联调**（后端 8000 + 前端 5173 同时运行）：

| 检查项 | 结果 |
|---|---|
| SPA 入口 | HTTP 200，含 `<div id="app">` 与 `/src/main.ts` |
| Vite 代理 `/api` → 后端 | HTTP 200，857 ms，返回真实数据（点位数 56、小时行 540,288） |
| 7 个模块路由 | `/overview` `/realtime` `/spatial` `/trend` `/compare` `/alerts` `/data` **全部 200** |
| 经代理的业务数据 | 回放帧 2026-08-10T13:00 有雨点位 56/56，合计 264.9 mm |
| 质量报告 | 覆盖率 100.0%，缺测率 0.0%，缺失整点 0 |

**浏览器实际渲染**：已用 Edge 打开并截图确认，侧边栏 7 个模块、指标卡、
排行表、数据源状态、模块进度均正常渲染，页头显示「采集正常」绿色状态灯。

> 排查记录：首次用 `PrintWindow` 截取 Edge 窗口时，图片出现「地址栏显示 /realtime、
> 主内容显示总览大屏」的矛盾状态。改用屏幕抓取后四处（URL / 标签页标题 / 侧边栏高亮 /
> 主内容）完全一致 —— 确认是 **Edge 硬件加速窗口在 PrintWindow 下的跨帧残影**，
> 不是应用缺陷（当时 UIA 树报的窗口标题也是「总览大屏」，与图像矛盾，已印证此结论）。

### 20.3 目录结构

```
frontend/
├── package.json / pnpm-workspace.yaml / tsconfig*.json / vite.config.ts
├── index.html / env.d.ts
├── .env.development / .env.production      # API 地址（可切本机/局域网/公网）
└── src/
    ├── main.ts / App.vue
    ├── router/index.ts                     # 7 个模块路由 + 导航元数据
    ├── api/client.ts                       # axios 实例 + 中文错误提示
    ├── api/index.ts                        # 21 个接口的封装
    ├── types/index.ts                       # 与后端 schemas.py 一一对应
    ├── stores/app.ts                       # 连通性、数据规模、采集状态
    ├── stores/filter.ts                    # 选中区域、对比城市、时间窗口
    ├── utils/format.ts                     # 数字/时间/距平格式化
    ├── styles/tokens.css                   # 设计令牌（含降水等级配色）
    ├── styles/global.css                   # 重置 + 通用面板/栅格
    ├── components/layout/                  # AppLayout / AppSidebar / AppHeader
    ├── components/common/                  # BaseChart / StatCard / NavIcon / ModulePlaceholder
    └── views/                              # 7 个模块页面
```

### 20.4 已实现 / 待实现

| 模块 | 状态 |
|---|---|
| 总览大屏 | ✅ 已接真实数据（指标卡、Top10 排行、数据源状态、模块导航） |
| 数据管理 | ✅ 已接真实数据（质量报告、采集审计表、手动采集、CSV 导出） |
| 实时监测 | 骨架 + 规划说明（P7 填充图表） |
| 空间分布 | 骨架 + 规划说明（P7 填充地图与回放） |
| 时间分析 | 骨架 + 规划说明（P7 填充趋势与距平） |
| 城市对比 | 骨架 + 规划说明（P7 填充对比图表） |
| 预警统计 | 骨架 + 数据源说明（当前无预警数据源，接口与表已就绪） |

### 20.5 两个踩坑记录

| 问题 | 现象 | 解决 |
|---|---|---|
| pnpm 11 拦截构建脚本 | `ERR_PNPM_IGNORED_BUILDS: esbuild, vue-demi`，esbuild 平台二进制缺失 | pnpm 11 已不从 package.json 读 `pnpm` 字段，配置迁移到 **`pnpm-workspace.yaml`**，键名为 **`allowBuilds`**（不是 `onlyBuiltDependencies`） |
| composite 项目禁用 emit | `tsc` 报 `TS6310: Referenced project may not disable emit` | `tsconfig.node.json` 去掉 `noEmit`，改为 `outDir` 指向 `node_modules/.tmp` |

### 20.6 新增文件

| 文件 | 作用 |
|---|---|
| `frontend/`（24 个源文件） | Vue 3 前端骨架 |
| `scripts/run_frontend.bat` | 启动前端（可传 `lan` 切换局域网监听） |
| `frontend/pnpm-workspace.yaml` | pnpm 配置：放行 esbuild / vue-demi 构建脚本、关闭供应链发布年龄门限 |

---

## 21. 前端运行时去 DSH 化（实测记录）

### 21.1 问题

排查端口归属时发现 **5173 的持有进程映像是 `DSH Desktop.exe` 而不是 `node.exe`**。
追进程链后确认：`pnpm` 解析到了 DSH 注入 PATH 的 shim
（`%APPDATA%\DSH Desktop\runtime-commands\generations\...\bin\pnpm.cmd`），
于是 Vite 跑在 DSH 自带的 Node 运行时上。

进程链（修复前）：

```
DSH Desktop(31768) → powershell → cmd → DSH Desktop(3888) → cmd /c vite
                                                        → DSH Desktop(34668)  ← 监听 5173
                                                            → esbuild.exe
```

风险：卸载 / 移动 DSH Desktop 后 `pnpm` 失效，前端将无法启动。

### 21.2 关键发现：独立 pnpm 其实早就装好了

| 项 | 实际情况 |
|---|---|
| `node` | **独立安装**：`D:\Program Files\nodejs\node.exe`（v24.18.0） |
| `%APPDATA%\npm\pnpm.cmd` | **已存在**，自带 `pnpm.exe`，版本 **12.5.1**，使用的是独立 Node |
| DSH 的 shim | 版本 11.8.0，仅在 **DSH 启动的进程**里因 PATH 注入而抢占优先级 |
| 持久化 PATH | **不含任何 DSH 目录**（用户级、系统级均无） |

即：从资源管理器双击 `.bat` 时本来就用的是独立 pnpm；只有经由 DSH 终端/工具执行时才被抢。

### 21.3 真正的障碍：供应链发布年龄门限

独立 pnpm 12.5.1 拒绝读取由 pnpm 11 生成的锁文件：

```
ERR_PNPM_LOCKFILE_SUPPLY_CHAIN_VIOLATION
  @rollup/rollup-*@4.64.3 was published at 2026-10-08T18:13:50Z,
  within the minimumReleaseAge cutoff (2026-10-08T02:11:56Z)
```

配置对比（`pnpm config get minimumReleaseAge`）：

| pnpm | 值 | 效果 |
|---|---|---|
| 独立 12.5.1 | `undefined` | 走 pnpm 12 的默认门限 → 拒绝锁文件 |
| DSH 11.8.0 | `0` | DSH 显式关闭该门限 → 通过 |

### 21.4 处理

1. `frontend/pnpm-workspace.yaml` 显式加入 **`minimumReleaseAge: 0`** ——
   让 pnpm 11 与 12 行为一致（本项目锁文件已精确固定版本与完整性哈希，此设置合理且透明）
2. `scripts/run_frontend.bat` 显式使用 `%APPDATA%\npm\pnpm.cmd`，找不到才回退到 PATH
   —— 彻底摆脱 PATH 注入的不确定性

### 21.5 验证结果

```
独立 pnpm 12.5.1：
  install --frozen-lockfile  退出码 0，14 ms，"Lockfile passes supply-chain policies (136 entries)"
  typecheck                  退出码 0
  build                      退出码 0，13.4 s
  锁文件被改写               否（SHA256 前后一致）

端口归属：
  端口 5173  PID 8876  进程 node  映像 D:\Program Files\nodejs\node.exe   ← 已脱离 DSH
  进程树     node.exe ← cmd.exe ← pnpm.exe                              ← 全程无 DSH Desktop.exe
```

---

## 22. P6 完成情况（总览大屏图表，实测记录）

### 22.1 交付内容

| 组件 | 说明 |
|---|---|
| `RainMap.vue` | 长三角分级设色地图：56 要素、国标等级分段配色、tooltip 显示数量+等级、可缩放 |
| `HourlyTrendChart.vue` | 近 24 小时全区逐小时降水柱状图 |
| `LevelDonutChart.vue` | 日降水量等级分布环形图（3 年 63,112 天） |
| `useYrdMap.ts` | GeoJSON 获取与 `echarts.registerMap` 单例注册 |
| `rainLevels.ts` | 降水等级与配色（与后端 `levels.py`、`tokens.css` 三处一致） |
| `chartTheme.ts` | ECharts 统一主题常量 |
| `OverviewView.vue` | 组装：4 指标卡 + 地图/排行 + 趋势/等级 + 数据源状态 + 模块导航 |

地图支持两种口径切换：**近 24h 累计**（各帧逐小时累加）与**逐小时**（拖动滑块回放 24 帧）。

### 22.2 端到端验证

| 检查项 | 结果 |
|---|---|
| 类型检查 | **0 错误** |
| 生产构建 | 成功，13.4 s；`echarts` 单独分包 1,035 kB（gzip 343 kB） |
| 接口可用性 | timespan 24 帧、timeseries 24 点、等级分布 7 项 63,112 天 |
| **地图名称匹配** | 56 个监测点名称与 GeoJSON 要素名称 **100% 匹配**（0 个不匹配） |
| 浏览器实际渲染 | 已 OCR 确认：指标卡、地图（含图例 10/25/50）、排行 Top10、空态提示全部呈现 |

### 22.3 本轮修复的两个真实缺陷

**缺陷一：ECharts 地图注册时序错误（导致整页空白）**

```
TypeError: Cannot read properties of undefined (reading 'regions')
    at MapSeries.getInitialData (echarts.js)
```

*根因*：**Vue 中子组件的 `mounted` 先于父组件执行**。原实现把 `ensureYrdMap()`
放在父组件 `OverviewView` 的 `onMounted` 里，于是 `RainMap → BaseChart` 的
`onMounted` 先跑，`echarts.init` + `setOption` 时地图 `yrd` 尚未注册，
ECharts 在 `MapSeries.getInitialData` 中读到 `undefined`。

*修复*：把「注册完成后再渲染」的责任下沉到 `RainMap` 自身 ——
组件挂载即 `await ensureYrdMap()`，完成前渲染占位提示；加载失败显示错误原因。
这样任何页面使用该组件都不会再踩时序问题。

**缺陷二：Vite 文件监听器被临时文件搞崩（导致 dev server 退出）**

```
Error: EBUSY: resource busy or locked, watch
  'src/stores/.filter.ts.<pid>.<rand>.tmpdir/filter.ts.tmp'
```

*根因*：DSH 的写文件实现采用「先写临时文件再原子重命名」，会在源码目录
产生临时目录；Vite 的 chokidar 监听器一旦盯上它就抛 `EBUSY` 并让进程退出。
这会在**每次改代码时复发**。

*修复*：`vite.config.ts` 增加 `server.watch.ignored`，忽略 `.tmpdir/`、`.tmp` 等临时文件。

### 22.4 附带改进：全局错误浮层

排查缺陷一时，为看到浏览器端真实错误，在 `main.ts` 增加了全局错误兜底：
捕获 Vue 组件错误、`window.onerror`、`unhandledrejection`，
以**可关闭的浮层**展示错误信息与堆栈，并写入 `document.title`。

设计要点：**只做覆盖层，不清空 `#app`** —— 单个子组件出错不应该让整个界面消失
（第一版实现会清空应用，已修正）。这既是排查手段，也是交付物的健壮性改进。

### 22.5 新增文件

| 文件 | 作用 |
|---|---|
| `frontend/src/components/charts/` | RainMap / HourlyTrendChart / LevelDonutChart |
| `frontend/src/composables/useYrdMap.ts` | 地图注册单例 |
| `frontend/src/utils/rainLevels.ts`、`chartTheme.ts` | 等级配色与图表主题 |
| `frontend/src/main.ts`（改） | 全局错误浮层 |
| `frontend/vite.config.ts`（改） | 忽略临时文件的监听规则 |

---

## 23. P7 完成情况（5 个分析模块，实测记录）

### 23.1 交付内容

| 模块 | 路由 | 实际内容 |
|---|---|---|
| **实时监测** | `/realtime` | 4 指标卡（有雨点位/最大雨强/窗口累计/最近采集）、逐小时序列（24/48/72h 切换 + 区域选择）、**56 点位降水矩阵**（按省市分组）、采集心跳表 |
| **空间分布** | `/spatial` | **时间轴回放**（播放/暂停/倍速/拖动）、分级设色地图、本帧统计、本帧 Top12 排行、4 个预设时段 |
| **时间分析** | `/trend` | 日趋势柱线组合（30/90/365/全部）、月累计柱状图（按年切换）、**距平图**、等级分布环形图 |
| **城市对比** | `/compare` | 城市多选（最多 8 个，按省分组）、多城折线对比、区间排行横向条、箱线图 + 五数概括明细表 |
| **预警统计** | `/alerts` | 数据源说明、**极端降水事件榜**（按国标阈值筛选）、3 个汇总指标、等级分布 |

### 23.2 新增图表组件（8 个）

| 组件 | 用途 |
|---|---|
| `TimeScrubber.vue` | 时间轴播放器（播放/暂停/回放/0.5×–4× 倍速） |
| `PointMatrix.vue` | 56 点位色块矩阵（按省市分组，连续色阶） |
| `DailyTrendChart.vue` | 日降水柱线组合 |
| `MonthlyBarChart.vue` | 月累计柱状图 |
| `AnomalyChart.vue` | 距平图（正负分色 + 零基线） |
| `MultiLineChart.vue` | 多城市折线对比 |
| `RankingBarChart.vue` | 横向排行条形图 |
| `BoxplotChart.vue` | 箱线图 + 均值散点 |

另有 `RegionSelect.vue`（按省市分组的区域选择器）。

### 23.3 新增后端接口

`GET /api/trend/extremes` —— 极端降水事件榜，支持 `min_mm` 按国标阈值筛选。
OpenAPI 路径数由 22 增至 **23**。

### 23.4 端到端验证

| 检查项 | 结果 |
|---|---|
| 类型检查 | **0 错误** |
| 生产构建 | 成功，12.6 s；7 个视图各自分包 |
| 5 个页面所需接口 | 经 Vite 代理全部 200 |

**时间轴回放预设（已实测有帧返回）**

| 预设 | 帧数 | 帧合计范围 | 峰值帧 |
|---|---|---|---|
| 2026-08-09~10 大暴雨过程 | 48 | 38.4 ~ 340.7 mm | 08-10 07:00 |
| 2026-06-22 过程 | 36 | 18.2 ~ 129.8 mm | 06-22 07:00 |
| 2026-08-31 过程 | 36 | 17.4 ~ 135.4 mm | 08-31 21:00 |

**浏览器实际渲染**（OCR 确认 `/spatial`）：

```
空间分布
注：时间轴回放依赖小时数据，本项目小时数据回溯 1 年（25-09-07 00:00 起）
选择时段：2026-08-09~10 大暴雨过程 | 2026-06-22 过程 | 2026-08-31 过程 | 最近 24 小时
共 48 帧，每帧间隔 1 小时。拖动时间轴或点击播放可查看降水场的移动与增强过程
长三角降水场  26-08-09 00:00   ← 地图已渲染（图例 25/50）
本帧统计：有雨点位 36/56
本帧降水排行：舟山市、宁波市、绍兴市…
```

### 23.5 本轮修复的缺陷

| 问题 | 现象 | 根因 | 处理 |
|---|---|---|---|
| 时间轴回放预设时段返回空 | 选「2024-10-26 过程」时帧数为 0，页面无内容 | **小时数据只回溯 1 年**（2025-09-07 起），2024 年只有日数据，无法做小时级回放 | 改为三个**在小时数据覆盖区间内、且实测有帧返回**的预设（2026-08-09~10 / 2026-06-22 / 2026-08-31）；并在页面显著位置说明小时数据的回溯范围 |
| ECharts `label.formatter` 类型不匹配 | `vue-tsc` 报 `TS2769`（2 处） | 内联回调参数类型过窄 | 统一改为 `(raw: unknown)` 后内部收窄（与 P6 的 tooltip 处理一致） |

### 23.6 一个重要的数据边界（论文需注明）

**小时数据仅回溯 1 年，日数据回溯 3 年。** 因此：

- **时间轴回放**、**小时雨强分析** 仅适用于 2025-09 之后
- **日/月/年尺度统计**、**距平**、**等级分布** 可用完整 3 年
- 论文中若展示「2024-10-26 台州大暴雨」，只能给日尺度数据，不能给小时演变

### 23.7 当前前端模块完成度

| 模块 | 状态 |
|---|---|
| 总览大屏 | ✅ 图表完整 |
| 实时监测 | ✅ 图表完整 |
| 空间分布 | ✅ 含时间轴回放 |
| 时间分析 | ✅ 含距平 |
| 城市对比 | ✅ 含箱线图 |
| 预警统计 | ✅ 含极值榜（真实预警数据源未接入，已如实说明） |
| 数据管理 | ✅ 质量报告 / 审计 / 采集 / 导出 |

**7 个模块全部可用，无占位页。**

---

## 24. P8 面向用户的优化计划（基于数据可视化流水线）

### 24.1 分析框架

以数据可视化经典流水线为标尺（含**三条人机交互反馈**）：

```
社会自然现象 → 数据采集 → 数据处理和变换 → 可视化映射 → 用户感知 → 知识、灵感
                    ↑            ↑              ↑
                    └────────────┴──────────────┘
                          人机交互（反馈）
```

这条流水线的关键不只在前向的六段，更在**三条反馈回路**：
交互可以反作用于「可视化映射」（改变视觉编码）、「数据处理」（改变计算口径）、
「数据采集」（触发新的数据获取）。

### 24.2 逐段完成度评估

| 流水线段 | 完成度 | 已具备 | 主要缺口 |
|---|---|---|---|
| ① 社会自然现象 | 100% | 真实气象数据源（ECMWF 再分析），非模拟 | — |
| ② 数据采集 | **85%** | 56 点位批量采集、自愈补采、幂等写入、采集审计、3 年回填、额度核算 | 单一数据源无交叉验证；无推送式更新；**交互反馈到采集层几乎为零** |
| ③ 数据处理和变换 | **75%** | 清洗（缺测率 0%）、日汇总、国标分级、距平、五数概括、极值榜、质量校验 | **无空间插值**（现为 56 离散点着色，非连续降水场）；无预聚合分层；无质量控制标记；交互反馈到处理层弱 |
| ④ 可视化映射 | **80%** | 10 个图表组件、位置/颜色/长度/角度/面积多通道、时间轴动画、统一设计令牌 | 无网格热力图/等值线/流场；**映射选型未显式表达**；图例不统一；动画无插值过渡；**无多视图协调（联动）** |
| ⑤ 用户感知 | **55%** | tooltip 精确读数、空态设计、数据时刻显示、分级图例、响应式布局 | **加载时无反馈**；**无数据时效警示**；无叙事引导；**数字不可追溯**；无导出；首屏 echarts 全量 1,035 KB |
| ⑥ 知识、灵感 | **35%** | 距平、极值榜、排行、箱线可支撑人工发现 | **系统不给结论**（无自动文字摘要）；无自动极值标注；无报告导出；视图无法固化/分享 |

**结论：数据侧（②③）与视觉侧（④）扎实，人这一侧（⑤⑥）与交互反馈明显偏薄。**

### 24.3 三条交互反馈的缺口

| 反馈方向 | 现状 | 评价 |
|---|---|---|
| → 可视化映射 | 时间轴拖动、区域切换、图层切换、地图缩放 | ✅ 中等 |
| → 数据处理和变换 | 仅能选区域/时间范围，统计口径写死 | ⚠️ 不足 |
| → 数据采集 | 仅一个「立即采集一次」按钮 | ❌ 基本缺失 |

### 24.4 Shneiderman 任务清单对照

| 任务 | 现状 |
|---|---|
| 1 Overview 总览 | ✅ 总览大屏 |
| 2 Zoom 缩放 | ✅ 地图 roam、时间范围切换 |
| 3 Filter 筛选 | ✅ 区域/时间/阈值筛选 |
| 4 **Details-on-demand 按需细节** | ✅ **已实现**（点位下钻抽屉，P8-1） |
| 5 **Relate 关联** | ❌ **缺失** |
| 6 History 历史/撤销 | ❌ 无 |
| 7 **Extract 提取** | ⚠️ 仅 3 种固定导出 |

**7 项做全 4 项** —— 缺的 Relate / Extract 仍是「能不能用起来」的关键。

### 24.5 优化清单（按价值 ÷ 成本排序）

| 档位 | # | 优化项 | 补在哪一层 | 对应评分 |
|---|---|---|---|---|
| 🥇 一 | **1** | **按需细节：点位下钻抽屉** —— 点任意点位弹出该点近 48h 逐小时 + 近 30 天逐日 + 等级统计 + 极值榜 | ⑤ 感知 + 交互反馈 | 真实性、可用性 | ✅ **已完成**（见第 25 节） |
| 🥇 一 | **2** | **数据时效三态警示** —— <2h 绿 / 2–24h 黄 / >24h 红；采集失败另标 | ⑤ 感知 | 真实性 | ✅ **已完成**（见第 26 节） |
| 🥇 一 | **3** | **一键启动 `start.bat` + 演示模式** —— 起服务、等就绪、自动开浏览器；演示模式隐藏导航、全屏、直达回放 | 工程可用性 | 答辩不翻车 | ✅ **已完成**（见第 27、28 节） |
| 🥈 二 | **4** | **图表联动（Relate）** —— 打通 `selectedAdcode`，点地图各页同步切换 | 交互 → 映射 | 感知性 |
| 🥈 二 | **5** | **自动文字摘要 + 极值自动标注** —— 把"知识"从用户脑中搬到界面上 | ⑥ 知识 | **创新性** |
| 🥈 二 | **6** | **关于/数据说明页** —— 数据源、口径、已知限制、架构集中呈现 | 全局 | 论文可复用 |
| 🥉 三 | **7** | 空间插值生成连续降水场（IDW + 等值线） | ③ → ④ | 技术含量 |
| 🥉 三 | **8** | 加载态骨架、导出 PNG、CSV 自定义范围、echarts 按需引入 | ⑤ 感知 | 艺术性、性能 |
| 🥉 三 | **9** | 图表选型说明（每图一句"为什么用这种编码"） | ④ 映射 | 论文必需 |

### 24.6 实施顺序与验收标准

**逐个实施，每项完成即验证并单独提交。**

| 顺序 | 优化项 | 验收标准 |
|---|---|---|
| 1 | 点位下钻抽屉 | 在总览地图、点位矩阵、排行、空间分布帧排行上点任意点位，右侧滑出抽屉；抽屉内 4 组内容全部为真实数据；可从抽屉一键"聚焦该点位"联动全局筛选 |
| 2 | 数据时效警示 | 页头状态灯随数据新鲜度变色；构造"数据超过 24 小时"场景验证变红 |
| 3 | 一键启动 + 演示模式 | 双击 `start.bat` 后自动打开浏览器且页面可用；演示模式一键隐藏导航并进入全屏 |

### 24.7 关联的交互反馈补齐说明

本计划完成后，三条反馈回路的覆盖情况将变为：

| 反馈方向 | 计划完成后 |
|---|---|
| → 可视化映射 | 增强：新增点位聚焦、联动切换 |
| → 数据处理和变换 | 增强：下钻抽屉按点位重算口径（逐小时/逐日/等级/极值四套口径） |
| → 数据采集 | 仍偏弱：仅保留「立即采集」（后续可扩展为"圈选区域补采"） |

---

## 25. P8-1 完成情况：点位下钻抽屉（实测记录）

### 25.1 补的是哪一项

对应 Shneiderman 任务清单里缺失的 **Details-on-demand（按需细节）**，
也就是流水线中「人机交互 → 数据处理和变换」这条反馈回路的实体化。

**要解决的问题**：界面上显示「宁波市 50.3 mm」时，用户无法核对这个数字是怎么来的。
下钻抽屉让任何一个数字都可以被追问到原始小时值。

### 25.2 新增后端接口

`GET /api/regions/{adcode}/detail?hours=48&days=30`

把「近 N 小时逐小时 + 近 N 天逐日 + 历史等级分布 + 历史极值 + 汇总指标」
合并为**一个响应**（下钻时只打 1 个请求，而不是 4~5 个）。

| 字段 | 内容 |
|---|---|
| `region` | 点位基本信息（名称、层级、省市、经纬度、是否参与监测） |
| `hourly` | 近 N 小时逐小时降水 |
| `daily` | 近 N 天逐日（含当日最大小时雨强与等级） |
| `levels` | 该点位全部历史的降水等级分布 |
| `extremes` | 该点位历史极值榜 Top 5 |
| `summary` | 13 项汇总指标（累计、极值、有雨日数、记录总数、数据起始时刻等） |

参数边界：`hours` 限 6~168、`days` 限 7~365，越界返回 422；
省级区划（无采集点）返回 404 并给出解释。

**OpenAPI 路径数：23 → 24。**

### 25.3 新增前端

| 文件 | 作用 |
|---|---|
| `stores/detail.ts` | 抽屉全局状态（打开/关闭/换窗口/加载） |
| `components/common/DetailDrawer.vue` | 抽屉本体（右侧滑入，含遮罩、Esc 关闭、锁定背景滚动） |
| `BaseChart.vue`（改） | 新增 `chartClick` 事件，把 ECharts 的点击透传给上层 |
| `RainMap.vue`（改） | data 项携带 `adcode`，点击区划抛出 `select` |
| `PointMatrix.vue`（改） | 色块改为可聚焦按钮，点击抛出 `select` |
| `RankingBarChart.vue`（改） | 点击柱子按城市名反查 adcode 并抛出 `select` |
| `NavIcon.vue`（改） | 补充 `close` / `focus` 图标 |

**抽屉只在 AppLayout 挂载一次**，任何页面/图表调用 `detail.open(adcode)` 即可唤起 ——
保证「看到数字 → 追问明细」在全站是一致的交互。

### 25.4 已接入的下钻入口

| 页面 | 入口 |
|---|---|
| 总览大屏 | 点击地图任意区划、点击降水排行任意一行 |
| 实时监测 | 点击 56 点位矩阵的任意色块 |
| 空间分布 | 点击地图任意区划、点击本帧降水排行任意一行 |
| 城市对比 | 点击区间排行横向条 |

### 25.5 实测数据

**接口性能**（5 个不同点位、含区级）：

| 点位 | 层级 | 响应时间 | 30 天累计 | 历史最大日 | 记录数 |
|---|---|---|---|---|---|
| 淮安市 | city | 65 ms | 52.9 mm | 101.6 mm | 9,540 |
| 宿迁市 | city | 21 ms | 51.4 mm | 79.4 mm | 9,540 |
| 宁波市 | city | 28 ms | 107.0 mm | 141.1 mm | 9,540 |
| 黄浦区 | district | 89 ms | 90.1 mm | 106.8 mm | 9,540 |
| 合肥市 | city | 63 ms | 163.5 mm | 76.0 mm | 9,540 |

**一致性校验**（抽屉数字 vs 已有接口，全部吻合）：

| 校验项 | 已有接口 | 抽屉 | 结果 |
|---|---|---|---|
| 当前值 `latest_value` | 0.0 | 0.0 | 一致 |
| 48h 小时点数 | 48 | 48 | 一致 |
| 30 天日点数 | 30 | 30 | 一致 |
| 48h 累计 | 0.0 | 0.0 | 一致 |

**参数边界**：`hours=5` / `hours=200` / `days=400` 均被 422 正确拒绝。

### 25.6 浏览器实测（截图确认）

| 路径 | 触发方式 | 结果 |
|---|---|---|
| 排行下钻 | 点击「宿迁市」 | ✅ 抽屉显示：江苏 / 市级 / 321300 / 118.275162, 33.963008；48h 累计 0.1 mm、30 天累计 51.4 mm、历史最大日 **79.4 mm（2024-07-20）**、记录 9,540 条；逐小时图 48 个整点；逐日图；底部「在全局筛选中聚焦该点位」 |
| 地图下钻 | 点击地图「淮安市」区划 | ✅ 抽屉显示：江苏 / 市级 / 320800 / 119.021265, 33.597506；历史降水等级分布环形图（无降水/小雨/中雨/大雨四段） |
| Esc 关闭 | 按键 | ✅ 抽屉关闭、背景恢复 |
| 提示文案 | 视觉确认 | ✅ 总览页出现「点击任意区划可查看该点位明细」「近 24 小时累计 · 点击查看明细」 |

### 25.7 本轮修复的缺陷

| 问题 | 现象 | 根因 | 处理 |
|---|---|---|---|
| 下钻接口返回 500 | `GET /api/regions/330200/detail` 报 `ResponseValidationError` | `region` 字典漏了 `is_monitored`，与 `RegionOut` 校验规则不符 | 补上该字段；并确立一条经验：**crud 返回的字典必须与 response_model 字段完全对齐**，直接调用 crud 不会暴露这类问题，只有走 HTTP 才触发 |

### 25.8 待办（本项未覆盖的部分）

- 抽屉内的图表尚未参与跨模块联动（属 P8-4「图表联动」范畴）
- 底部「在全局筛选中聚焦该点位」按钮目前只写入 `filter.selectedAdcode`，
  尚无页面消费该状态 —— 需要等 P8-4 打通后才有可见效果

---

## 26. P8-2 完成情况：数据时效三态警示（实测记录）

### 26.1 为什么这一项重要

采集器是**手动启动的前台进程**（见第 7 节 B 模式），用户完全可能几天不启动它。
在此之前，界面会在数据已经陈旧 5 天的情况下，依然亮着绿色「采集正常」，
并且显示一个**未来的**「数据时刻」—— 用户没有任何线索判断眼前的图是不是最新的。

这是数据可视化里最伤信任的一类问题：**图很漂亮，但它是旧的，而界面没说。**

### 26.2 本轮修复的核心缺陷（比功能本身更关键）

| 问题 | 现象 | 根因 |
|---|---|---|
| 「数据时刻」显示未来时间 | 页头显示 `2026-10-22 23:00`，而最新**实况**只有 `2026-10-16 10:00` | `meta.hourly_end` 取的是 `max(obs_time)` **不加 `is_forecast` 过滤**，而预报有 7 天，实测领先实况 **157 小时（6.5 天）** |
| 数据陈旧却报「采集正常」 | 数据已 123.9 小时未更新，页头仍为绿色 | 状态只看「最近一次采集是否 success」，**不看数据有多旧** |
| 两处「小时数据范围」同样误导 | 显示 `2025-09-07 ~ 2026-10-22`，让人以为已有到 10-22 的观测 | 同一个字段被复用 |

### 26.3 后端改动

`GET /api/meta` 新增 4 个字段（保留原字段但明确其含义）：

| 字段 | 含义 |
|---|---|
| `observed_start` / `observed_end` | **实况**数据边界（`is_forecast = 0`）—— 判断时效只能用这个 |
| `forecast_end` | 预报数据最远时刻 |
| `server_now` | 服务器当前时间，供前端抵消客户端时钟偏差 |
| `hourly_end`（保留） | 全部小时数据（含预报）的最大值，说明中已标注「可能在未来」 |

### 26.4 前端改动

| 文件 | 改动 |
|---|---|
| `stores/app.ts` | 新增 `dataAgeHours`、`freshness`、`freshnessLabel`、`freshnessHint`、`ageText`；用 `server_now` 计算并保存时钟偏差；每 30 秒推进本地时钟让"多久以前"自动增长 |
| `components/layout/AppHeader.vue` | 状态灯改由 `freshness` 驱动（绿/黄/红）；副行显示「数据时刻 · 多久以前」，偏旧时"多久以前"标黄 |
| `components/layout/AppLayout.vue` | 新增时效提示条（偏旧=黄、过期=红），给出具体处置建议 |
| `views/OverviewView.vue`、`views/DataManageView.vue` | 「小时数据范围」改为「实况数据范围」+ 单独一行「预报数据至」 |

### 26.5 阈值设计

| 阈值 | 值 | 依据 |
|---|---|---|
| 新鲜 | `< 2 小时` | 采集间隔是 30 分钟，2 小时 = 允许连续 4 次采集未运行，仍属"正常但该看看了" |
| 偏旧 | `2 ~ 24 小时` | 已明显落后，但用户看到的仍是同一天的数据，不至于误判为实时 |
| 过期 | `> 24 小时` | 跨天，界面呈现的"近 24 小时"已不是真正的近 24 小时，必须明确告知 |

采集失败（`last_collect_status = failed`）**优先于时效判断**，单独标为红色「采集失败」。

### 26.6 实测（三态逐一验证）

| 状态 | 构造方式 | 页头 | 提示条 |
|---|---|---|---|
| **过期**（真实场景） | 数据实际已 123.9 小时（5.2 天）未更新 | 红色「数据过期」；`数据时刻 26-10-16 10:00 · 5.2 天前` | 红色：「数据已过期 —— 请启动 scripts\start_autocollect.bat 或手动采集一次」 |
| **新鲜** | 执行一次采集（`observed_end` 推进到 `2026-10-21T13:00`，年龄 0.93 小时） | 绿色「数据新鲜」；`数据时刻 26-10-21 13:00 · 55 分钟前` | **消失** |
| **偏旧** | 临时把 `FRESH_HOURS` 调到 0.5（年龄 0.92 小时落入该档），验证后已改回 2 | 黄色 | 黄色：「数据可能不是最新 —— 请检查定时采集是否在运行」 |

三态均经浏览器截图/OCR 确认。

### 26.7 顺带修复的数据缺口

验证「新鲜」状态时发现数据实际已停 5 天，于是执行了一次 30 天窗口的采集：

- 写入 49,728 行（新增 0，更新 49,728，幂等）
- 小时总行数 552,384 → **559,104**（+6,720 行，补齐 10-16 至 10-21 的缺口）
- 观察时刻推进到 `2026-10-21T13:00`

说明：默认 `past_days=3` 只够补 3 天；**停机超过 3 天时需要 `--past-days 30`（或跑 `backfill.bat` 的桥接步骤）才能完全补齐**。
这一条与第 7 节的自愈机制配套，应写入运行须知。

---

## 27. P8-3 完成情况：一键启动 `start.bat`（实测记录）

### 27.1 背景

在此之前启动整套系统需要：双击 `run_backend.bat` → 双击 `run_frontend.bat` → 手动开浏览器输网址 → 再双击 `start_autocollect.bat` 起采集。
**四步、三个窗口、还要手打网址** —— 答辩现场最容易翻车的一环。

### 27.2 交付内容：`scripts\start.bat`

一次点击，按固定顺序完成：

```
环境自检 → 前端依赖检查 → 后端(8000) → 轮询 /api/health 等就绪
        → 前端(5173) → 轮询首页等就绪 → 打开浏览器
        → 定时采集器（每 30 分钟） → 打印访问地址
```

关键设计：

| 设计点 | 说明 |
|---|---|
| **等就绪而非等固定秒数** | 用 `curl` 轮询 `/api/health` 与前端首页，拿到 HTTP 200 才继续；后端 90 秒、前端 120 秒超时 |
| **可重复运行** | 后端/前端按**端口是否监听**判断，采集器按 **PID 锁**判断；已启动的一律 `[SKIP]` |
| **环境自检** | 缺 `.venv` 或缺 `data/weather.db` 时直接报错并给出该先跑哪个脚本 |
| **自动补依赖** | `frontend/node_modules` 不存在时先跑 `pnpm install`，避免前端窗口闪退 |
| **不重复造轮子** | 内部仍是 `call` 现有的 `run_backend.bat` / `run_frontend.bat` / `start_autocollect.bat`，逻辑只有一份 |

参数：

| 命令 | 作用 |
|---|---|
| `start.bat` | 全部启动（含浏览器与采集器） |
| `start.bat --no-collect` | 不启动定时采集 |
| `start.bat --no-browser` | 不自动打开浏览器 |
| `start.bat lan` | 监听 `0.0.0.0`，同 WiFi 设备可访问 |

### 27.3 配套改动：采集器单实例锁

把采集合并进一键启动后，多了一个风险：**重复点击会启动两个采集器，API 额度翻倍消耗**
（数据本身安全，因为写入是幂等 UPSERT，但会白白浪费额度）。

因此在 `collector/scheduler.py` 增加了单实例锁：

- 锁文件 `.tmp/scheduler.pid`，内容为持有者 PID
- 启动时若锁存在且该 PID **仍存活**（用 `OpenProcess` + `GetExitCodeProcess` 判断，仅标准库），则打印提示并退出
- 进程正常结束时由 `atexit` 删除锁；被强杀留下的陈旧锁会在下次启动时被 PID 存活检查识别并覆盖
- `--once` 模式**不占用锁**，便于随时做一次性采集

### 27.4 实测

**从零启动**（先 `stop_all.bat` 清空，锁文件不存在）：

| 阶段 | 实测 |
|---|---|
| 后端 | 约 **2 秒**就绪 |
| 前端 | 约 **1 秒**就绪 |
| 浏览器 | 已打开 `http://127.0.0.1:5173` |
| 采集器 | 已启动，首次采集 `collect_log #22 realtime success 14:10:21` |
| 三处连通性 | 后端 `/api/health` 200、前端 `/` 200、代理 `/api/meta` 200（56 点位） |

**重复运行**（服务已在跑）：

```
[SKIP]  Backend is already listening on port 8000
[SKIP]  Frontend is already listening on port 5173
[SKIP]  Collector already running (PID 27732)
```

进程数核对：`uvicorn` 2 个、`collector.scheduler` 2 个、`vite` 1 个 —— **与首次运行后完全相同，没有多启动任何东西**；
采集日志在 5 分钟内也只有 1 条记录（即采集器自己的周期任务），**没有重复采集**。

> 说明：`uvicorn` 与 `scheduler` 各显示 2 个同名进程，是虚拟环境启动器「父→子」再执行造成的正常现象
> （后端 `--reload` 也会有同样的一对），并非两个实例。判据是 `collect_log` 的新增条数。

### 27.5 一条排查记录（不是脚本缺陷）

测试过程中曾出现「前端被启动后又消失」，一度怀疑是 `start.bat` 的问题。
最终定位为：**在 DSH 后台任务里运行时，`start` 派生的子进程仍归属于同一个 Windows 作业对象**，
作业被终止时子进程被连坐；而正常双击运行时不存在这层作业对象，子窗口是独立的。

改用「输出重定向到文件」而非管道复测后，三个服务全部存活且连通性正常，确认脚本本身无问题。
这条记录保留下来，避免以后误判。

---

## 28. P8-3 完成情况：演示模式（实测记录）

### 28.1 要解决的问题

答辩/汇报时投屏，侧边栏（约 130px）+ 页头（约 56px）会吃掉近 200px 宽度，而且屏幕上还留着浏览器地址栏、时钟、刷新按钮等与内容无关的东西。手动按 F11、再想办法藏导航，既麻烦又容易在手忙脚乱时出错。

### 28.2 交付内容

| 能力 | 实现 |
|---|---|
| **进入方式** | ① `scripts\start.bat demo`（打开 `/spatial?demo=1`）② 页头右上角的「演示模式」图标（会同时请求全屏） |
| **布局变化** | 侧边栏与页头整体隐藏，内容占满整屏 |
| **导航替代** | 新增 `PresentationBar.vue`：底部居中的细窄浮动条，含 **数据时效指示灯 + 7 个模块切换 + 全屏开关 + 退出** |
| **自动播放** | `TimeScrubber` 新增 `autoplay` 属性；演示模式下进入空间分布页，时间轴自动开始播放 |
| **退出** | 「退出演示」按钮；`Esc`；全屏状态下由 `fullscreenchange` 兜底一并退出 |
| **状态记忆** | `sessionStorage` 记住演示模式，刷新仍保持，关标签页即失效 |

### 28.3 两个实现上的坑

**① `requestFullscreen` 必须由用户手势触发**

带 `?demo=1` 打开页面时没有用户手势，强行调用会被浏览器拒绝。因此 `enterDemo(forceFullscreen)` 加了参数：
从 URL 进入时只切布局、不请求全屏；从按钮进入时才请求全屏。`start.bat demo` 走的正是前者。

**② 全屏时浏览器会吞掉 `Esc`，不派发给网页**

首次实测发现：全屏下按 `Esc` 只退出了全屏，页面仍停在演示态 —— 变成"按一次 Esc 只退了一半"。
由于浏览器不把该按键传给页面，只能靠 `fullscreenchange` 兜底：

- 监听 `fullscreenchange`，若全屏结束且仍处于演示模式 → 一并退出演示
- 但「全屏」按钮是**主动**退全屏、只想保留演示布局，用一个 1 秒的抑制时间窗把它排除在外

### 28.4 实测（截图确认）

| 路径 | 结果 |
|---|---|
| `?demo=1` 进入 | ✅ 侧边栏与页头消失，底部浮动条出现，7 个模块与当前高亮正常 |
| 自动播放 | ✅ 预设首帧为 `26-08-09 00:00`，数秒后截图已在第 8 帧（`08:00`），继续推进到 `08-10 13:00` 时 **56/56 点位有雨、全区合计 264.9 mm、苏州 29.4 mm** |
| 页头图标进入 | ✅ 演示布局 + **浏览器全屏**（窗口尺寸变为整屏，并出现 Edge 的全屏提示条） |
| 「退出演示」按钮 | ✅ 侧边栏与页头恢复，浮动条消失 |
| `Esc`（非全屏） | ✅ 退出演示模式 |

> 说明：全屏→`Esc` 的兜底逻辑是在最后一次实测之后才补上的，未再单独复测
> （合成点击在这套环境下不能稳定触发全屏）。主路径均已验证。

### 28.5 一个已知限制

演示模式下**数据时效提示条仍然保留**。这是有意的：数据过期时不提示，等于在答辩场合隐瞒数据新鲜度。
如果希望演示时更"干净"，正确做法是演示前先跑一次 `start.bat`（含采集器）把数据更新到最新。
