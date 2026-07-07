# ==========================================================
# Article Check — Make 命令
# ==========================================================

# 默认目标
.DEFAULT_GOAL := help

# 变量
PORT ?= 3000

help: ## 显示帮助信息
	@echo "Article Check — 部署命令"
	@echo ""
	@echo "用法: make [目标]"
	@echo ""
	@echo "🐳 Docker 部署"
	@echo "  build       构建 Docker 镜像"
	@echo "  up          启动所有服务 (docker compose up -d)"
	@echo "  down        停止所有服务"
	@echo "  restart     重启所有服务"
	@echo "  logs        查看日志 (tail)"
	@echo "  ps          查看服务状态"
	@echo ""
	@echo "💻 本地开发"
	@echo "  install     安装 Python 依赖"
	@echo "  dev-backend 启动后端 (uvicorn, 热重载)"
	@echo "  dev-frontend启动前端 (Vite dev server)"
	@echo "  build-front 构建前端 (Vite build)"
	@echo ""
	@echo "🧪 测试"
	@echo "  test        运行测试"
	@echo "  lint        代码检查"
	@echo ""
	@echo "📦 工具"
	@echo "  clean       清理 __pycache__ 等"
	@echo "  help        显示此帮助"

# ─── Docker 部署 ──────────────────────────────────────────

build: ## 构建 Docker 镜像
	docker compose build

up: ## 启动所有服务（后台）
	docker compose up -d

down: ## 停止所有服务
	docker compose down

restart: down up ## 重启所有服务

logs: ## 查看日志
	docker compose logs -f

ps: ## 查看服务状态
	docker compose ps

# ─── 本地开发 ────────────────────────────────────────────

install: ## 安装 Python 依赖
	pip install -e .
	pip install fastapi uvicorn python-multipart python-docx pymupdf pdfplumber

dev-backend: ## 启动后端（热重载）
	uvicorn article_check.web.server:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## 启动前端开发服务器
	cd article_check/web/frontend && npm run dev

build-front: ## 构建前端
	cd article_check/web/frontend && npm run build

# ─── 测试 ────────────────────────────────────────────────

test: ## 运行测试
	python -m pytest tests/ -v

lint: ## 代码检查
	ruff check article_check/
	black --check article_check/

# ─── 工具 ────────────────────────────────────────────────

clean: ## 清理缓存文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name *.pyc -delete 2>/dev/null || true
	@echo "✅ 已清理"
