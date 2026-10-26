# ==============================================================================
# 长三角降水监测系统 —— 生产镜像
#
# 两个构建目标（target）：
#   backend : FastAPI 后端 + 采集器（同一镜像，用不同启动命令）
#   web     : Caddy，托管前端静态产物并反代 /api
#
# 对应 docker-compose.yml 里的 api / collector / web 三个服务。
# 使用说明见 deploy/README.md。
#
# 架构无关：python:3.13-slim / node:22-alpine / caddy:2-alpine 都有
# amd64 与 arm64 版本，因此本文件在 Oracle A1（arm64）上同样适用，
# 直接在该机器上 `docker compose build` 即可出对应架构的镜像。
# ==============================================================================

# ------------------------------------------------------------------ 前端构建
FROM node:22-alpine AS web-build

WORKDIR /app/frontend

# 固定 pnpm 版本：lockfileVersion 为 9，与本机 12.5.1 一致，
# 避免 corepack 装到不同大版本导致锁文件解析不一致。
RUN corepack enable && corepack prepare pnpm@12.5.1 --activate

# 先只拷依赖清单：改源码不会触发重新安装依赖（层缓存）
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# 再拷源码并构建（.env.production 已把 VITE_API_BASE 设为 /api，同源部署）
COPY frontend/ ./
RUN pnpm build

# ------------------------------------------------------------------ 后端运行时
FROM python:3.13-slim AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 以非 root 用户运行
RUN useradd --create-home --uid 10001 appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY collector/ ./collector/

# 静态边界数据（5 个 JSON，已入库）。
# 命名数据卷首次创建时，Docker 会把镜像里 /app/data 的内容播种进卷，
# 所以挂载卷之后 geojson 不会丢。
COPY data/geojson/ ./data/geojson/

RUN mkdir -p data/snapshots .tmp && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 默认启动 API；采集器在 compose 里覆盖 command 为 python -m collector.scheduler
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------------ Web 运行时
FROM caddy:2-alpine AS web

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=web-build /app/frontend/dist /srv

EXPOSE 80 443
