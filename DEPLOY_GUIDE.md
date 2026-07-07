# 🐳 Article Check — Docker 部署指南

根据《中小学教育教学支撑平台》技术架构要求，Article Check 需要作为 **WebDemo** 案例以 Docker 容器化方式部署，并由 **后端代理 Dify API** 提供 AI 能力。

---

## 📦 已创建的文件

| 文件 | 用途 |
|------|------|
| `Dockerfile` | 多阶段构建（前端 Node.js → Python 运行镜像） |
| `docker-compose.yml` | Nginx + FastAPI + Redis(可选) 编排 |
| `nginx.conf` | 反向代理、前端托管、API 路由 |
| `.dockerignore` | 优化构建上下文 |
| `.env.docker` | 环境变量模板（API Key + 端口配置） |
| `deploy.bat` | Windows 一键部署脚本 |
| `deploy.sh` | Linux/Mac 一键部署脚本 |
| `Makefile` | 常用命令快捷入口 |
| `.dify-config.md` | Dify 平台集成配置说明 |
| `article_check/web/frontend/public/auth.js` | WebDemo 平台认证脚本 |

---

## 📋 部署步骤

### Step 1: 安装 Docker Desktop

下载地址：https://www.docker.com/products/docker-desktop/

```bash
# 或使用 winget（管理员 PowerShell）:
winget install --id Docker.DockerDesktop
```

安装后：
1. 启动 Docker Desktop（任务栏图标绿色表示运行中）
2. 设置确认：Settings → General → ✅ Use WSL 2 based engine

### Step 2: 配置 Dify API Key 与 Provider

```bash
# 从模板创建 .env
cp .env.docker .env

# 编辑 .env，至少填写以下变量
# ARTICLE_CHECK_AI_PROVIDER=dify
# DIFY_BASE_URL=http://你的-dify-地址/v1
# DIFY_API_KEY=app-你的真实key
# DIFY_APP_TYPE=chat   # 或 workflow
```

### Step 3: 构建并启动

**Windows:**
```bash
# 双击 或
deploy.bat
```

**Mac/Linux:**
```bash
chmod +x deploy.sh && ./deploy.sh
```

**或手动:**
```bash
docker compose build
docker compose up -d
```

### Step 4: 验证

```bash
# 健康检查
curl http://localhost:3000/api/health

# 查看当前 AI provider 状态
curl http://localhost:3000/api/status

# 查看日志
docker compose logs -f
```

---

## 🔗 平台集成

### 方式一: 作为独立 WebDemo
- 访问 `http://localhost:3000`
- 可直接使用全部审查功能

### 方式二: 接入平台门户（PPT 第 28 页）
平台通过 Nginx 统一入口，Article Check 可作为子路径路由：
```
平台网关 → /article-check/* → http://article-check:3000/*
```
在平台网关配置：
```nginx
location /article-check/ {
    proxy_pass http://article-check-host:3000/;
}
```

### 方式三: 平台托管 + Dify 代理模式（当前推荐）
- 前端仍然作为 WebDemo 页面运行
- FastAPI 后端代理 Dify Service API
- 支持 `chat` 与 `workflow` 两种 Dify 应用

```text
浏览器 WebDemo -> /api/* -> FastAPI -> Dify API -> 返回内容 -> 生成报告
```

Docker 中推荐设置：

```env
ARTICLE_CHECK_AI_PROVIDER=dify
DIFY_BASE_URL=http://host.docker.internal/v1
DIFY_API_KEY=app-your-dify-api-key-here
DIFY_APP_TYPE=chat
```

说明：
- `DIFY_APP_TYPE=chat` 时，后端调用 `/chat-messages`
- `DIFY_APP_TYPE=workflow` 时，后端调用 `/workflows/run`
- 当前 WebDemo 前端无需暴露 Dify API Key，密钥仅保存在服务端容器环境变量中

### 方式四: 平台认证脚本接入
- 前端已在 `index.html` 中引入 `/auth.js`
- 平台域名环境下自动启用认证
- 本地 `localhost/127.0.0.1` 默认不触发认证

---

## 🛠 运维命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 更新（代码变更后）
git pull
docker compose build
docker compose up -d
```

---

## 📐 PPT 规范对照

| PPT 要求 | 实现 | 文件 |
|----------|------|------|
| ✅ 容器化部署 | Docker 多阶段构建 | `Dockerfile` |
| ✅ Nginx 反向代理 | 前端托管 + API 转发 | `nginx.conf` |
| ✅ API Key 环境变量 | 不硬编码，`-e` 注入 | `.env.docker` |
| ✅ 轻量化无状态 | Python slim 镜像 | `Dockerfile` |
| ✅ SSE 流式支持 | proxy_buffering off | `nginx.conf` |
| ✅ 健康检查 | /api/health + Docker HEALTHCHECK | `server.py`, `Dockerfile` |
| ✅ 可扩展 | Redis 可选 profile | `docker-compose.yml` |
