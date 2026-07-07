#!/usr/bin/env bash
# ==========================================================
# Article Check — Docker 部署脚本 (Linux / Mac)
# ==========================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*" >&2; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}  🐳 Article Check Docker 部署脚本${NC}"
echo -e "${CYAN}  论文审查智能体 —— Web 服务容器化部署${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# 1. 检查 Docker
if ! command -v docker &>/dev/null; then
    err "Docker 未安装！"
    echo "  安装: https://docs.docker.com/engine/install/"
    exit 1
fi
ok "Docker $(docker --version | cut -d' ' -f3 | tr -d ',')"

# 2. 检查 docker compose
if ! docker compose version &>/dev/null; then
    err "Docker Compose 不可用"
    exit 1
fi

# 3. 检查 .env
if [ ! -f .env ]; then
    if [ -f .env.docker ]; then
        warn "未找到 .env 文件，从模板复制..."
        cp .env.docker .env
        info "已创建 .env 文件，请编辑填入 DIFY_BASE_URL 与 DIFY_API_KEY"
        ${EDITOR:-vi} .env
    else
        err "缺少 .env 和 .env.docker 文件"
        exit 1
    fi
fi

# 4. 检查 Dify 配置
if grep -q "DIFY_API_KEY=app-your" .env 2>/dev/null || grep -q "DIFY_BASE_URL=http://host.docker.internal/v1" .env 2>/dev/null; then
    warn "Dify 配置看起来仍是模板值，请编辑 .env 文件"
    ${EDITOR:-vi} .env
    exit 1
fi

# 5. 构建
info "构建 Docker 镜像（首次约 5-10 分钟）..."
docker compose build

# 6. 启动
info "启动服务..."
docker compose up -d

echo ""
ok "✅ 部署完成！"
echo ""
echo -e "  ${CYAN}🌐  Web UI:${NC}      http://localhost:${NGINX_PORT:-3000}"
echo -e "  ${CYAN}📚  API 文档:${NC}    http://localhost:${NGINX_PORT:-3000}/docs"
echo -e "  ${CYAN}🔍 健康检查:${NC}    http://localhost:${NGINX_PORT:-3000}/api/health"
echo ""
echo -e "  ${YELLOW}停止:${NC} docker compose down"
echo -e "  ${YELLOW}日志:${NC} docker compose logs -f"
echo -e "  ${YELLOW}重启:${NC} docker compose restart"
echo ""
