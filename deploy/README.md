# 部署说明（Docker Compose）

本目录外的三个文件构成本项目的生产部署形态：

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 多阶段构建：`web-build`（前端）→ `backend`（API/采集器）→ `web`（Caddy） |
| `docker-compose.yml` | 三个服务 + 三个数据卷 |
| `Caddyfile` | 静态托管 + `/api` 反代 + 可选自动 HTTPS |

---

## 1. 架构

```
浏览器
  │
  ▼
Caddy（web，对外 80/443）
  ├── /           → /srv 里的前端静态产物（SPA 回退到 index.html）
  └── /api/*      → 反代 api:8000
                     │
                     ▼
                  FastAPI（api，仅内网 8000）──┐
                                               ├── appdata 卷（SQLite）
                  采集器（collector）───────┘   （WAL 模式，同机双进程安全）
```

**同源部署**：前端构建时 `VITE_API_BASE=/api`（`frontend/.env.production` 已设好），
所以不需要配置 CORS，也不需要把后端地址写进构建产物。

---

## 2. 首次部署（关键一步：别让数据库是空的）

镜像**不含数据库**（`data/weather.db` 在 `.gitignore` 里）。
空库启动会没有数据，重新回填要跑很久还消耗 API 额度 ——
**正确做法是把本机已有的数据库放进去。**

> ⚠️ 下面这套步骤是**实测通过**的。三个坑必须同时避开，
> 否则会出现「文件明明在卷里、查询却是 0 行」或「容器启动即崩」：
>
> 1. **不要用 `docker compose cp`** —— 实测对已停止的容器不生效，文件根本没进去。
> 2. **必须先清掉卷里残留的 `weather.db-wal` / `-shm`** —— 旧 WAL 与新库不匹配时
>    SQLite 会把数据库**重置为空**。这是本项目踩过最隐蔽的坑。
> 3. **必须把文件属主改成 `10001:10001`** —— 容器以非 root 用户运行，
>    root 所有的文件会让启动时报 `attempt to write a readonly database`
>    （应用启动时要执行 `PRAGMA journal_mode=WAL`，需要写权限）。

```bash
# ① 本机导出干净副本（自包含、无 WAL 依赖），并核对行数
python deploy/vacuum_db.py
#    target : data/weather-clean.db  (89.1 MB)
#      precip_hourly    src=  561792  dst=  561792  OK
#      precip_daily     src=   64008  dst=   64008  OK
#      region           src=      60  dst=      60  OK

# ② 先起一次后端，让 Docker 创建数据卷并播种 geojson
docker compose up -d api

# ③ 停后端，清空卷里的数据库文件（保留 geojson）
docker compose stop api
docker run --rm -v yrd-precip_appdata:/v alpine:3.20 \
  sh -c "rm -f /v/weather.db /v/weather.db-wal /v/weather.db-shm"

# ④ 把干净副本写进卷，并修正属主（容器内以 uid 10001 运行）
docker run --rm \
  -v yrd-precip_appdata:/v \
  -v "$PWD/data:/src:ro" \
  alpine:3.20 \
  sh -c "cp /src/weather-clean.db /v/weather.db && chown 10001:10001 /v/weather.db && chmod 644 /v/weather.db"

# ⑤ 起全部服务
docker compose up -d
```

验证：

```bash
curl -s http://localhost/api/health          # {"status":"ok",...}
curl -s http://localhost/api/meta            # points_total / hourly_rows 应非空
docker compose exec -T api python -c "import sqlite3;c=sqlite3.connect('/app/data/weather.db');print(c.execute('select count(*) from precip_hourly').fetchone()[0])"
docker compose ps                            # 三个服务都应为 running / healthy
```

浏览器打开 `http://<服务器IP>/` 即可。

> Windows + Docker Desktop 时，第 ④ 步的 `$PWD` 换成绝对路径并用正斜杠，
> 例如 `-v "D:/visualization/data:/src:ro"`。已在本机实测通过。

浏览器打开 `http://<服务器IP>/` 即可。

---

## 3. 绑定域名与 HTTPS

```bash
# 域名已解析到本机 IP 后：
SITE_ADDRESS=yrd.example.com docker compose up -d
```

Caddy 会自动申请并续期 Let's Encrypt 证书，结果持久化在 `caddy_data` 卷里。

> 国内服务器绑域名需 ICP 备案；海外服务器（如 Oracle 日本/新加坡区）不需要。

---

## 4. 更新代码

```bash
git pull
docker compose up -d --build
```

- **数据卷不会被动**，数据库和 geojson 都保留。
- 如果只改了前端或后端其中一个，也可以 `docker compose up -d --build web` 单独重建。

---

## 5. 常用运维

```bash
docker compose logs -f api          # 后端日志
docker compose logs -f collector    # 采集日志（看有没有报错/额度问题）
docker compose ps                   # 状态与健康检查
docker compose restart collector    # 只重启采集器
docker compose down                 # 停止（保留数据卷）
docker compose down -v              # 危险：连数据卷一起删
```

手动触发一次采集（不依赖定时器）：

```bash
docker compose exec collector python -m collector.pipeline --once
```

---

## 6. 排错

| 现象 | 原因与处理 |
|---|---|
| 页面能开但所有图表空白 | 后端没起来或 `/api` 反代失败。`curl http://localhost/api/health` 自查 |
| `no such table` / 空数据 | 数据卷里没有数据库。回到第 2 步把 `weather.db` 拷进去 |
| `database is locked` | SQLite 并发写冲突。本项目采集为串行、读为主，正常不会出现；若频繁出现，把 `collector` 的 `command` 合并进 `api` 容器串行执行，或迁移到 Postgres |
| 页头一直显示「数据偏旧」 | 采集器没跑或额度问题。`docker compose logs -f collector` 看原因 |
| 时间显示差 8 小时 | 已设 `TZ=Asia/Shanghai`；若仍有偏差，检查宿主机时区 |
| 证书申请失败 | 域名未解析到本机、或 80 端口被占用。`docker compose logs web` 看 ACME 报错 |

---

## 7. 在 Oracle Cloud Always Free 上部署的注意事项

1. **架构**：Always Free 的 ARM 实例是 `arm64`。三个基础镜像（`python:3.13-slim`、`node:22-alpine`、`caddy:2-alpine`）都有 arm64 版本，**直接在目标机器上 `docker compose build` 即可**，不需要交叉编译。
2. **内存**：这套栈常驻约 **400–600 MB**（FastAPI ~300 MB + Caddy ~50 MB + SQLite 页缓存）。
3. **闲置回收**：Oracle 的判定是「7 天内 CPU 95 分位 < 20% **且** 网络 < 20% **且** 内存 < 20%（仅 ARM）」**三条同时成立**。本应用流量小、CPU 几乎空转，会落在闲置定义里 —— 具体应对方案见项目文档讨论（减小实例规格到 1 OCPU / 6 GB 可把内存阈值降到 1.2 GB，或升级 Pay As You Go 后不再受该政策约束）。
4. **端口**：OCI 的安全列表（Security List / NSG）默认只放行 22，**必须手动放行 80 和 443**，否则 Caddy 起得来但访问不到。
