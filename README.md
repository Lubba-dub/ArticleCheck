# ArticleCheck

面向高校论文送审前审改场景的审计型论文审查系统。当前版本以 `FastAPI + React WebDemo + Dify Workflow` 为主线，强调两类能力：

- **确定性审查**：本地规则引擎负责 `DOCX/PDF/TEX` 的结构与版式检查、参考文献元数据核验、证据落点。
- **Dify 编排审查**：Dify 负责文档归一化、弱格式判断、风险归纳、正式报告生成和报告问答。

## 当前能力

- 单篇与批量论文上传、审查、流式结果推送
- 本科 / 硕士论文显式分类审查
- `DOCX` 版式检查：页边距、字号、行距、图表标题位置、封面关键元素
- 参考文献核验：DOI 校验、Crossref / OpenAlex 题名检索、可疑条目标记
- 报告问答、原文证据联动、打印版报告 HTML 预览
- Docker / Docker Compose 一键部署

## 架构概览

```text
WebDemo (React)
    -> FastAPI Gateway
        -> Local Rule Engine (format / reference / evidence)
        -> Dify Workflows (document read / format review / reference verify / hallucination review / report generation / report qa)
        -> Report Renderer (HTML report / source snippet / Q&A)
```

主设计文档：

- `docs/dify-driven-review-architecture.md`
- `docs/dify-driven-format-hallucination-redesign.md`
- `docs/dify-workflow-optimization-architecture.md`

## 仓库结构

```text
article_check/
├── article_check/                 # 后端主代码
│   ├── web/                       # FastAPI + React 前端
│   ├── pipeline/                  # 审查主流程与 worker
│   ├── rules/                     # 本地格式规则与 DOCX 检查器
│   ├── references/                # 参考文献抽取与核验
│   ├── mcp/tools/                 # Harness / MCP 工具封装
│   ├── runtime.py                 # 审查运行时聚合层
│   └── dify_review.py             # Dify 主链编排
├── dify_dsl/                      # 项目使用的 Dify 工作流 DSL
├── docs/                          # 架构与设计文档
├── test_fixtures/                 # 本地调试样例（默认不进 Docker）
├── 北师大论文格式要求/              # 本科 / 研究生规则资产与结构化 JSON
├── Dockerfile
├── docker-compose.yml
├── dify_api.example.md            # Dify 工作流绑定模板（请复制为本地 dify_api.md）
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
cd article_check/web/frontend
npm install
```

### 2. 配置环境

复制环境变量模板：

```bash
cp .env.example .env
```

复制 Dify 绑定模板：

```bash
cp dify_api.example.md dify_api.md
```

然后在本地填写：

- `DIFY_BASE_URL`
- 各工作流 `API Key`
- 各工作流 `Workflow ID / URL`

`dify_api.md` 已加入 `.gitignore`，不会提交到仓库。

### 3. 启动后端与前端

后端：

```bash
python -m article_check.web.server
```

前端：

```bash
cd article_check/web/frontend
npm run dev
```

默认访问：

- `http://127.0.0.1:8765` 后端
- `http://127.0.0.1:5173` 前端开发环境

## Docker 部署

```bash
docker compose --env-file .env.docker build
docker compose --env-file .env.docker up -d
```

验证接口：

```bash
curl http://127.0.0.1:3000/api/health
curl http://127.0.0.1:3000/api/status
```

说明：

- Docker 镜像内默认复制 `dify_api.example.md`
- 生产环境请通过挂载或镜像外注入真实 `dify_api.md`
- `reports/`、`uploads/` 通过 volume 持久化

## Dify 工作流

当前仓库保留的项目工作流 DSL：

- `articlecheck_document_read_workflow.yml`
- `articlecheck_format_review_workflow.yml`
- `articlecheck_reference_verify_workflow.yml`
- `articlecheck_hallucination_review_workflow.yml`
- `articlecheck_report_generation_workflow.yml`
- `articlecheck_report_qa_workflow.yml`
- `文本情感分析工作流.yml`（当前实例导出的母版样例）

这些 DSL 只保留项目主线资产；社区调研样例与临时实验文件已从仓库主结构中移出。

## 当前边界

- `PDF` 版式检查仍弱于 `DOCX`，后续建议接入更强的结构化解析器
- “文献幻觉”当前已经支持 DOI / 题名 / 作者 / 年份核验，但尚未做到全文级 claim-to-source 对齐
- Dify 工作流导入前仍需按你的实例模型、变量名和插件配置做最终绑定

## 建议的下一步

- 引入统一 `Evidence Bundle`，把解析结果、规则证据和 Dify 上下文收束到一套 JSON 契约
- 为 `PDF` 接入更强的版面结构解析
- 将参考文献快诊断升级为本地缓存 + 离线索引 + 在线补查的级联核验

## 许可证

MIT
