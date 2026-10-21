# 长三角地区降水实时监测与可视化分析系统

> 课程设计项目 · 基于真实气象数据的降水监测与可视化分析平台

## 项目简介

面向长三角地区（上海市、江苏省、浙江省、安徽省）的降水实时监测与可视化分析系统，覆盖 **56 个采集点**（上海 16 个区 + 江苏 13 市 + 浙江 11 市 + 安徽 16 市），提供多模块可视化大屏与交互式分析能力。

数据来源为 **Open-Meteo** 真实气象数据（免 API Key），行政区划边界来自 **阿里 DataV GeoAtlas**。

## 技术栈

| 层 | 技术 |
|---|---|
| 采集 | Python 3.13 + requests + APScheduler |
| 后端 | FastAPI + SQLAlchemy + Uvicorn |
| 数据库 | SQLite（WAL 模式，可平滑切换 MySQL/PostgreSQL） |
| 前端 | Vue 3 + Vite + TypeScript + Vue Router + Pinia + ECharts 5 |

## 功能模块

| 模块 | 说明 |
|---|---|
| 总览大屏 | 关键指标 + 分级设色地图 + 城市排行 + 24h 趋势 |
| 实时监测 | 近 48h 逐小时降水、采集心跳、自动刷新 |
| 空间分布 | 降水场分级设色、时间轴回放、下钻 |
| 时间分析 | 日/月累计、降水距平、雨量等级分布 |
| 城市对比 | 多城市序列、排行、箱线图 |
| 预警统计 | 预警列表与极值统计 |
| 数据管理 | 采集日志、数据质量报告、CSV 导出 |

## ⚠️ 环境注意事项（本机特有，务必遵守）

**本机的系统临时目录对 Python 不可用**：`C:\Users\zhang\AppData\Local\Temp` 会让 Python 的 `tempfile` 报
`No usable temporary directory found`，导致 `pip` / `venv` **长时间空转甚至卡死**（实测单次空烧 400+ 秒 CPU 且零进展）。

**解决办法：把临时目录指向工作区内的 `.tmp`。**

```bat
set "TMP=D:\visualization\.tmp"
set "TEMP=D:\visualization\.tmp"
set "TMPDIR=D:\visualization\.tmp"
```

`scripts\setup.bat` 已内置该设置。**手动执行任何 pip 命令时也必须先设置**，否则会卡死。
另外，本机 pip 缓存（`%LOCALAPPDATA%\pip\cache`，约 458 MB）疑有损坏，安装时统一加 `--no-cache-dir`。

**前端 pnpm 必须用独立安装的那一份**：本机 PATH 里的 `pnpm` 会被 DSH Desktop 注入的
shim（`pnpm 11.8.0`，跑在 DSH 自带 Node 上）抢先，而独立安装的是
`%APPDATA%\npm\pnpm.cmd`（`pnpm 12.5.1`，跑在 `D:\Program Files\nodejs`）。
两者对「最小发布年龄」策略的默认值不同，会造成**同一份锁文件一个能装、一个报错**的迷惑现象。

`scripts\run_frontend.bat` 已显式指定独立 pnpm 路径，无需手动处理。
手动执行时请用完整路径：

```bat
"%APPDATA%\npm\pnpm.cmd" dev
```

> 在 PowerShell 里直接敲 `pnpm` 会命中被禁用的 `pnpm.ps1`（执行策略限制），
> 因此**统一用 `.cmd`**，或改用 `cmd /c pnpm ...`。

**⚠️ `scripts\*.bat` 必须保持纯 ASCII（重要，勿破坏）**

本机系统代码页是 **936（GBK）**，而 `.bat` 文件以 **UTF-8** 保存。
cmd.exe 是**按字节**解析批处理文件的：UTF-8 的中文会被从字节中间切断，
导致整份脚本解析错乱（实测报出一堆 `'xxx' is not recognized`，脚本完全不能运行）。

因此约定：

- **`.bat` 里不写中文**，提示信息用英文；需要中文界面时由 **Python 输出**（配 `chcp 65001` 显示正常）
- 新增/修改 `.bat` 后，用这条命令自查（三个数字都应为 0）：

```powershell
Get-ChildItem scripts\*.bat | ForEach-Object {
  $n = ([System.IO.File]::ReadAllBytes($_.FullName) | Where-Object { $_ -gt 127 }).Count
  "{0,-24} 非ASCII字节 {1}" -f $_.Name, $n
}
```

- 另外：`echo` 里**不要出现英文圆括号**（如 `(1-2 minutes)`），
  若该行位于 `if (...)` 块内，`)` 会提前闭合代码块导致语法错误；需要时写成 `^( ... ^)` 转义

**自动化运行脚本时**：设置环境变量 `YRD_NO_PAUSE=1` 可跳过结尾的「按任意键继续」，
这样脚本不会阻塞在 `pause`：

```powershell
$env:YRD_NO_PAUSE = '1'; & cmd /c "scripts\stop_all.bat"
```

---

## 快速开始

### 日常使用：一键启动（推荐）

**双击 `scripts\start.bat`** 即可 —— 它会按顺序完成：

```
环境自检 → 后端(8000) → 等就绪 → 前端(5173) → 等就绪
        → 自动打开浏览器 → 定时采集器(每 30 分钟) → 打印访问地址
```

特点：

- **等就绪再继续**：后台轮询 `/api/health` 与前端首页，真的起来了才走下一步，不会出现"页面打开但后端还没起"
- **可重复运行**：已启动的部分会自动跳过（后端/前端按端口判断，采集器按 PID 锁判断），不会重复启动
- **采集器防重复**：`collector/scheduler.py` 内置单实例锁（`.tmp/scheduler.pid`），误开两个也不会把 API 额度翻倍
- 每个服务各自一个窗口，**关掉哪个窗口就停哪个服务**

可选参数：

| 命令 | 作用 |
|---|---|
| `scripts\start.bat` | 全部启动（含浏览器与采集器） |
| `scripts\start.bat --no-collect` | 不启动定时采集 |
| `scripts\start.bat --no-browser` | 不自动打开浏览器 |
| `scripts\start.bat lan` | 监听 `0.0.0.0`，同 WiFi 的手机可直接访问 |

停止：`scripts\stop_all.bat`（停后端与前端），采集器窗口单独关掉。

### 首次部署：按顺序执行

前三步已完成，可重复运行：

| 步骤 | 命令 | 说明 |
|---|---|---|
| 1 | `scripts\setup.bat` | 安装 Python 依赖到 `.venv` |
| 2 | `scripts\init_db.bat` | 建表 + 下载合并地图 + 56 点位入库 |
| 3 | `scripts\backfill.bat` | 回填 3 年日数据 + 1 年小时数据（约 4 分钟） |
| 4 | `scripts\collect_once.bat` | 采集一次实时数据（约 3 秒） |
| 5 | **`scripts\start.bat`** | **一键启动整套系统（推荐）** |
| — | `scripts\run_backend.bat` | 只启动后端 → <http://127.0.0.1:8000/docs> |
| — | `scripts\run_frontend.bat` | 只启动前端 → <http://127.0.0.1:5173> |
| — | `scripts\status.bat` | 查看 8000 / 5173 端口是否在监听、被哪个进程占用 |
| — | `scripts\stop_all.bat` | **按端口停止服务**（无论谁启动的都能停，含子进程） |
| — | `scripts\start_autocollect.bat` | 单独启动前台定时采集（关窗口即停） |
| — | `scripts\git-push.bat` | 提交并推送到 GitHub（双击 → 输入说明 → 自动 add / commit / push） |

### 关不掉服务怎么办

服务有时是由工具以后台任务方式启动的，**没有可见的命令行窗口**，此时关窗口这条路走不通。
双击 **`scripts\stop_all.bat`** 即可 —— 它按「谁在监听端口」定位进程，
不管是谁启动的都能停掉：

```bat
scripts\status.bat      :: 先看谁在占用
scripts\stop_all.bat    :: 再一键停止
```

也可以用一条命令直接停：

```powershell
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**局域网访问**（同 WiFi 的手机/电脑可看大屏）：

```bat
scripts\run_backend.bat 0.0.0.0 8000
scripts\run_frontend.bat lan
```

## 运行模式

| 模式 | 启动方式 | 行为 |
|---|---|---|
| **A · 按需采集**（默认） | 双击 `scripts\collect_once.bat` | 立即采集一次（约 3 秒）后退出 |
| **B · 定时采集** | 双击 `scripts\start_autocollect.bat` | 立即采一次，之后**每 30 分钟**采一次；**关闭窗口或关机即停止** |
| **C · 一键启动**（推荐） | 双击 `scripts\start.bat` | 后端 + 前端 + 浏览器 + **B 模式采集器** 一起起来；重复运行会自动跳过已启动的部分 |

> `start.bat` 内部调用的就是 A/B 两个脚本，所以行为完全一致；
> 它只是把「起服务」和「起采集」这两件事合并成一次点击。
> 单独启动时，采集器同样受单实例锁保护，误开两个不会重复消耗 API 额度。

### 关于 B 模式的几点说明

- **不做任何开机自启注册** —— 不写注册表、不放启动文件夹、不建计划任务，因此**下次开机（含 Windows 快速启动）默认是关闭的**，需要再次双击启动。
- **前台运行** —— 它与你打开的那个命令行窗口绑定，想停就 Ctrl+C 或直接关窗口。
- **资源占用很小** —— 一次采集约 3 秒、峰值内存 74 MB、1 个网络请求；平均 CPU 占用约 0.17%。
- **需要时也可以定时跑一次**：`.venv\Scripts\python -m collector.scheduler --once`

> **自愈补采**：每轮固定回拉过去 3 天数据并幂等写入（重复运行不会产生重复数据），
> 所以**电脑关机、程序崩溃、断网都不影响数据完整性** —— 下次运行会自动补齐缺口。

## 项目文档

- [项目规划文档](docs/PLAN.md) —— 架构、数据库设计、接口设计、里程碑、风险登记
- [数据源核实记录](docs/DATA_SOURCE.md) —— API 额度核算与实测证据

## 数据来源与许可

- 气象数据：[Open-Meteo](https://open-meteo.com/)，数据基于 ECMWF ERA5 / ERA5-Land 再分析资料，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可，**非商业用途免费**，使用时须署名。
- 行政区划边界：[阿里云 DataV GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector)

## 目录结构

```
visualization/
├── docs/          项目文档
├── backend/       FastAPI 后端
├── collector/     Python 采集器
├── frontend/      Vue 3 前端
├── data/          SQLite 数据库与 GeoJSON
└── scripts/       启动与运维脚本
```
