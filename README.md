# Article Check Platform Minimal

面向项目方平台交付的最小版本，当前只保留以下主线：

- `WebDemo` 前端工作台
- `FastAPI` 网关与报告接口
- `Dify Service API` 多应用编排
- 项目方官方认证接入
- `Docker / Docker Compose` 托管部署

## 当前定位

本仓库不再保留历史性的多入口形态，只服务于线上平台部署目标：

- 论文上传与批量审查
- 格式核查与参考文献核验
- 审改建议与正式报告生成
- 报告问答与证据定位
- 官方认证接入

## 目录

```text
article_check/
├── web/                      # FastAPI + React WebDemo
├── runtime.py                # 审查运行时聚合层
├── pipeline/                 # 审查主流程
├── references/               # 参考文献审查
├── rules/                    # 模板与格式规则
├── llm/client/dify.py        # Dify API 客户端
└── config/settings.py        # 平台配置

docs/
└── dify-driven-review-architecture.md

Dockerfile
docker-compose.yml
nginx.conf
.env.docker
```

## 快速启动

1. 复制环境变量模板

```bash
cp .env.docker .env
```

2. 至少配置以下变量

```env
ARTICLE_CHECK_AI_PROVIDER=dify
DIFY_BASE_URL=https://your-dify-host/v1
DIFY_API_KEY=app-your-key
DIFY_APP_TYPE=workflow
```

3. 启动 Docker

```bash
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up -d
```

4. 验证

```bash
curl http://127.0.0.1:3000/api/health
curl http://127.0.0.1:3000/api/status
```

## 官方认证

- 前端已在 `article_check/web/frontend/index.html` 注入 `auth.js`
- Nginx 已代理 `/prod-api/*` 到项目方认证链路
- 本地 Docker 可用于触发认证流程验证
- 完整登录闭环需部署在项目方平台域名或同一网关下

## Dify 主线

建议采用以下 Dify 分层：

- `Document Read Workflow`
- `Format Review Workflow`
- `Reference Review Workflow`
- `Report Generation Workflow`
- `Report Chat`

详细方案见：

- `docs/dify-driven-review-architecture.md`
- `docs/dify-migration-implementation.md`

## 当前交付边界

当前最小版本已覆盖：

- WebDemo 页面托管
- FastAPI 网关
- Dify 代理接入
- 官方认证脚本接入
- Docker 化部署

仍需线上联调的内容：

- 真实 Dify App Key 与变量映射
- 项目方平台域名下的 OAuth/SSO 回调
- 最终上线环境的网关策略

### Web
- 已启动并验证 `/api/health`
- 已验证 `/api/review`
- 已验证 `/api/review/deep`
- 已验证 `/api/report/dialogue`

### VSCode 插件
- 已验证 `npm run compile`
- 已补齐 `npm run package`
- 已配置 `.vscodeignore`
- 已具备打包 `.vsix` 所需脚本

## 当前边界与注意事项

- `ContentWorker` 的深审依赖 DeepSeek API，如未配置 API Key 会跳过内容审查
- 批量任务当前的 `workflow.graph` 在没有逐篇 checkpoint 时使用推断图兜底
- VSCode 插件目前已具备工作台和树视图，但还没有接入 Problems/Diagnostics 面板
- 自动修正当前主要覆盖 Word，LaTeX 自动修正仍未形成完整 patch 闭环

## 下一步建议

如果继续推进，建议优先做：
- 批量任务逐论文 checkpoint / 事件流
- Evidence 到 VSCode Diagnostics / Problems 的映射
- 正式报告模板向高校论文审查公文格式继续靠拢
- 自动修正闭环：建议 -> patch -> re-check -> 复验

## 参考项目

本项目在设计上参考过以下开源项目或方向：
- coarse
- reviewer2
- Loupe
- ScholarFlow
- PaperSeek
- CitationClaw
- athena-loops
- LangGraph / Durable Workflow 类模式

## 许可证

MIT
