# ==========================================================
# Article Check — Docker 多阶段构建
# 根据 PPT WebDemo 规范: 容器化 + 环境变量管理Key + 轻量化
# ==========================================================

# ─── Stage 1: 前端构建 (Node.js) ─────────────────────────
FROM node:20 AS frontend-builder

WORKDIR /build/frontend

# 依赖层缓存
COPY article_check/web/frontend/package.json \
     article_check/web/frontend/package-lock.json* ./
RUN npm ci --include=dev 2>/dev/null || npm install --include=dev

# 源码 + 构建
COPY article_check/web/frontend/ .
RUN npm run build
# 产物: dist/   (Vite 默认输出)

# ─── Stage 2: 后端运行环境 (Python) ──────────────────────
FROM python:3.12-slim

LABEL maintainer="ShaoPaodiao <18519101256@163.com>"
LABEL description="Article Check — 学术论文审查智能体 Web 服务"
LABEL version="0.3.0"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 工作目录
WORKDIR /app

# Python 依赖层缓存
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e . 2>/dev/null || \
    pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# 复制前端产物
COPY --from=frontend-builder /build/frontend/dist /app/article_check/web/frontend/dist

# 复制源码
COPY article_check/ /app/article_check/

# 运行时目录
RUN mkdir -p /app/reports /app/uploads /app/.worktrees

# 暴露端口 (内部 8000, Nginx 对外暴露 80/3000)
EXPOSE 8000

# 环境变量 (运行时通过 -e 注入)
ENV ARTICLE_CHECK_ROOT=/app
ENV PYTHONPATH=/app

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

# 入口
CMD ["uvicorn", "article_check.web.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
