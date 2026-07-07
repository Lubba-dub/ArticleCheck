# ArticleCheck Platform Package

## 1. 包说明

`ArticleCheck_platform` 是面向项目方平台托管整理出的轻量化交付包。

目标形态：

- 前端继续以 WebDemo 页面运行
- 后端以 FastAPI 方式提供 `/api/*`
- AI 能力默认由后端代理到 Dify Service API
- 支持项目方 `auth.js` 认证脚本接入
- 支持 Docker / Docker Compose 托管部署

## 2. 目录说明

- `article_check/`
  - 核心后端与前端源码
- `knowledge/`
  - 规则与知识文本
- `scripts/`
  - 辅助运行脚本
- `docs/`
  - 平台部署说明、Dify 工作流文本架构设计、项目方要求 PPT
- `项目方相关配置/`
  - 项目方给出的参考认证脚本、示例 Dockerfile、Dify yml 示例
- `Dockerfile`
  - Docker 镜像构建文件
- `docker-compose.yml`
  - 平台托管编排文件
- `.env.docker`
  - Docker 环境变量模板
- `.dify-config.md`
  - Dify 接入配置说明
- `nginx.conf`
  - Nginx 反代与 SPA 路由配置
- `deploy.bat` / `deploy.sh`
  - 一键部署脚本

## 3. 推荐部署方式

1. 复制环境变量模板：

```bash
cp .env.docker .env
```

2. 至少填写以下项：

```env
ARTICLE_CHECK_AI_PROVIDER=dify
DIFY_BASE_URL=http://your-dify-host/v1
DIFY_API_KEY=app-your-key
DIFY_APP_TYPE=chat
```

3. 启动：

```bash
docker compose build
docker compose up -d
```

4. 验证：

```bash
curl http://localhost:3000/api/health
curl http://localhost:3000/api/status
```

## 4. Dify 侧建议

建议拆成两个应用：

1. `ArticleCheck_Review_Workflow`
   - 用于结构化内容审查与建议生成
   - 后端可通过 `DIFY_APP_TYPE=workflow` 调用

2. `ArticleCheck_Report_Chat`
   - 用于报告问答
   - 后端可通过 `DIFY_APP_TYPE=chat` 调用

当前包内已经附带面向 Dify 线上编排的文本架构设计，见：

- `docs/dify-workflow-text-architecture.md`

## 5. 平台认证说明

前端已在 `article_check/web/frontend/index.html` 中引入：

```html
<script src="/auth.js"></script>
```

当前运行逻辑：

- 本地 `localhost/127.0.0.1` 默认不启用认证
- 部署到平台域名时自动启用
- 若项目方提供正式版脚本，可直接替换：

```text
article_check/web/frontend/public/auth.js
```

## 6. 交付边界

本交付包已经满足：

- WebDemo 页面托管
- 后端代理 Dify API
- Docker 化部署
- 平台认证脚本接入

仍需项目方联调的内容：

- 真实 Dify 应用的 API Key 与地址
- 真实 Dify workflow/chat 的变量映射
- 真实 OAuth / SSO 回调参数
