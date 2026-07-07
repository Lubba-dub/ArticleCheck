# 部署架构与平台适配说明

## 1. 当前项目的真实部署形态

当前项目不是一个原生构建在 Dify 内部的应用，而是一个以 `FastAPI + React/Vite` 为主线的独立论文审查系统：

- 后端入口：`article_check.web.server:app`
- 前端产物：`article_check/web/frontend/dist`
- 统一交付对象：`article_check.ai_review.v1`
- 报告产物：结构化 JSON、建议报告 Markdown、正式审改报告 HTML/Markdown/JSON

因此，部署上应区分两种模式：

1. **独立部署模式**
   - 直接以 Docker / Docker Compose 部署本项目
   - 本项目完整提供 Web UI、API、报告生成与文件落盘
   - 这是当前最真实、最完整、最推荐的部署方式

2. **平台接入模式**
   - 将本项目作为平台中的“专业审查服务”
   - Dify 不替代本项目 UI，而是承接对话式入口、工作流编排或门户层调用
   - Dify 通过 HTTP/API 调本项目，而不是反过来把本项目完全迁入 Dify

## 2. Docker 部署建议

### 2.1 当前仓库已经具备的能力

仓库已经包含以下容器化文件：

- `Dockerfile`
- `docker-compose.yml`
- `nginx.conf`
- `.env.docker`
- `deploy.bat`
- `deploy.sh`

这套方案当前的真实结构是：

- `nginx`
  - 对外暴露 `3000`
  - 转发 `/api/*` 到 FastAPI
  - 提供 SPA 路由回退与 SSE 代理
- `backend`
  - 实际运行 FastAPI
  - 内部端口 `8000`
  - 持久化挂载 `reports/` 与 `uploads/`
- `redis`
  - 可选，不是当前主链的强依赖

### 2.2 当前 Docker 部署的关键约束

- 必填环境变量：`DEEPSEEK_API_KEY`
- 持久化目录：
  - `/app/reports`
  - `/app/uploads`
- 健康检查接口：`/api/health`
- 必须保留 SPA fallback，否则 `/review` 等直达路由会失效
- 若使用流式批处理，Nginx 必须关闭 `/api/` 缓冲

### 2.3 推荐部署路径

对于当前项目，推荐优先采用：

```bash
cp .env.docker .env
docker compose build
docker compose up -d
```

验证：

```bash
curl http://localhost:3000/api/health
```

浏览器访问：

```text
http://localhost:3000/review
```

## 3. Dify 适配建议

### 3.1 先澄清一件事

工作区中的 `.dify-config.md` 现在已经对应到实际实现：当前项目支持由 FastAPI 后端代理 Dify Service API。

当前仓库当前状态：

- 已有直接调用 Dify API 的后端代码
- 已支持 `chat` 与 `workflow` 两类 Dify App
- 已保持论文审查主流程和正式报告工作台在本项目中

所以，**当前项目已经完成“WebDemo + 后端代理 Dify API”的集成主线**。

### 3.2 正确的 Dify 角色

对本项目来说，Dify 最合适的角色不是替代 Web UI，而是以下三种之一：

1. **门户对话入口**
   - 用户在 Dify 中通过 Chatflow 或 Agent 提问
   - Dify 通过 HTTP 请求调用本项目接口
   - 本项目返回结构化结果或报告链接

2. **轻量工作流编排层**
   - Dify 负责串起：
     - 上传文件说明
     - 审查触发
     - 报告问答
     - 结果摘要
   - 论文审查的核心逻辑仍在本项目中

3. **平台统一入口**
   - Dify 提供统一应用入口
   - Article Check 作为一个垂直专业应用挂接在平台中

### 3.3 不推荐的做法

当前阶段不建议：

- 把整个项目重写成 Dify Workflow
- 把正式报告模板、Evidence 联动和原文定位都迁移进 Dify 页面
- 让 Dify 承担论文文件管理和报告存储主责任

原因是：

- 本项目已经形成独立且较复杂的审查工作台
- 正式报告、Evidence、打印预览、原文片段联动更适合在本项目内维护
- Dify 更擅长“流程入口与对话编排”，不适合承接本项目当前的全部专业 UI

## 4. 推荐的 Dify 落地方式

### 4.1 模式 A：Dify 作为聊天入口

在 Dify 中创建一个 Chatflow / Agent：

- 输入：论文路径、论文主题、审查模式
- 中间节点：HTTP Request
- 调用目标：
  - `POST /api/review`
  - `POST /api/report/dialogue`
- 输出：
  - 审查摘要
  - 关键问题
  - 正式报告链接

适合：

- 门户侧统一接入
- 轻量对话使用
- 管理员总控台

### 4.2 模式 B：Dify 作为工作流编排层

在 Dify 中设计 Workflow：

1. 输入论文信息
2. HTTP 请求本项目 `upload/review`
3. 提取结构化结果
4. LLM 节点生成摘要说明
5. 最终返回报告链接和建议动作

这种方式下：

- Dify 负责交互和节点编排
- Article Check 负责真实审查和报告生成

### 4.3 模式 C：平台网关挂接

若存在上层门户或 Dify-demo 统一壳层，可以通过网关将本项目挂到子路径：

- `/article-check/` → 本项目前端
- `/article-check/api/` → 本项目后端 API

这时 Dify 和本项目是并列挂载，不必强制嵌套。

## 5. Dify 自托管环境的真实要求

结合当前工作区文档与外部资料，Dify 自托管通常至少包括：

- `nginx`
- `api`
- `worker`
- `web`
- `db`
- `redis`
- 向量存储（如 `weaviate` / `pgvector`）
- sandbox / plugin / ssrf 相关服务

因此，若你要在同一台机器部署：

- **Article Check**
- **Dify**

推荐资源至少：

- CPU：4 核以上
- 内存：8GB 起步，12-16GB 更稳妥
- 磁盘：至少 30GB 可写空间

原因：

- Article Check 本身要处理报告、文件和审查任务
- Dify 是一个多服务系统，不是单容器 Web 应用

## 6. 当前最可执行的部署结论

### 6.1 对本项目本身

最优先采用：

- Docker Compose 独立部署本项目
- 保持 `3000 -> nginx -> 8000 FastAPI` 的现有结构

### 6.2 对 Dify 适配

最优先采用：

- 先独立部署 Dify
- 在 Dify 中通过 HTTP 节点调用本项目 API
- 把本项目作为一个“论文审查服务”集成进平台

### 6.3 当前不应误判为已完成的事项

以下能力目前还**没有**完全完成：

- 项目方正式 Dify 应用的 workflow 导出包与变量映射模板
- 项目方正式 OAuth/SSO 配置与生产环境回调联调
- Dify 侧针对论文审查的专用 prompt / knowledge / workflow 工程化固化

## 7. 下一步建议

下一步最值得做的是两项：

1. 补一份 `docker-compose.override.yml` 或生产版 compose
   - 增加外部挂载
   - 增加日志目录
   - 增加反向代理域名说明

2. 补一份 `docs/dify-integration.md`
   - 明确 Dify 中如何创建 Chatflow
   - 给出调用 `/api/review` 和 `/api/report/dialogue` 的请求样例
   - 说明 Dify 与本项目的职责边界
