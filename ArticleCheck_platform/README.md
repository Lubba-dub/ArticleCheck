# Article Check

面向论文格式审查、参考文献有效性验证、审改建议生成与批量审查的研究型系统。

当前仓库已经从“多入口分叉原型”收束到一条统一主线：
- `CLI / Web / VSCode 插件` 共享统一 runtime
- 输出统一结构化报告 `article_check.ai_review.v1`
- 支持正式审改报告导出、证据记录、节点状态与报告问答

## 核心定位

当前最重要的业务目标是：
- 本科毕业论文格式核查
- 参考文献有效性验证
- 支持单篇检测
- 支持批量检测
- 输出问题清单、审改建议报告和正式审改报告

这不是一个“通用聊天式智能体平台”，而是一个正在 V4 路线上持续收束的论文审改系统。

## 当前能力

### 论文审查
- LaTeX 格式检查：`chktex` + 规则检查
- Word 格式检查：`python-docx` 样式、字体、页边距等
- 模板检查：支持内置模板规则与自动检测
- 参考文献引擎：提取、正文引用一致性检查、DOI 缺失检查
- 内容深审：按章节切分，调用 DeepSeek 输出结构化问题
- 审改建议报告：按严重度聚合修正建议
- 正式审改报告：导出 Markdown / HTML / JSON

### V4 执行核
- 统一 `build_runtime()` 装配入口
- `TaskGraph` / `WorkflowEvent` / `CheckpointStore`
- `ContextCurator` 适配层
- `ContextCacheBus` + `PolyKVEngine` 逻辑级接入
- 单篇工作流 checkpoint / 事件日志
- 批量结果的最小工作流图推断

### Web 与插件
- FastAPI Web API
- React Web 前端
- VSCode 插件：
  - 审改工作台
  - 节点状态 TreeView
  - Evidence TreeView
  - 当前文件审查
  - 工作区批量审查
  - 正式审改报告打开
  - 基于结构化报告的问答

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install -e .
```

建议额外安装：

```bash
pip install python-docx pymupdf
```

如需更强的 LaTeX 规则检查，请在系统中安装 `chktex`。

### 2. 配置 DeepSeek

如果希望启用内容深审和报告问答：

```bash
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env
```

未配置时，系统仍可执行格式与参考文献相关检查。

### 3. 运行 CLI

```bash
python run.py
python run.py chat
python -m article_check review tests/fixtures/sample.tex
python -m article_check batch temp_batch --concurrent 2
```

### 4. 启动 Web

```bash
python -m article_check web
```

默认地址：
- Web UI: `http://127.0.0.1:8765`
- API Docs: `http://127.0.0.1:8765/docs`
- Health: `http://127.0.0.1:8765/api/health`

### 5. 构建 VSCode 插件

在 `vscode-extension/` 下执行：

```bash
npm install
npm run compile
npm run package
```

产物为 `.vsix` 扩展包，可在 VSCode 中安装测试。

## 常用命令

### 单篇审查

```bash
python -m article_check review paper.tex --json-output report.json
```

### 批量审查

```bash
python -m article_check batch papers/ --concurrent 2 --json-output batch_report.json
```

### 报告问答

```bash
python -m article_check assist-report report.json --question "我应该先修改哪些问题？"
```

### 模板检查

```bash
python -m article_check template list
python -m article_check template check --template-name "IEEE Transactions" --paper paper.tex
```

## 报告产物

当前系统会输出以下几类产物：

### 结构化报告
- 格式：`article_check.ai_review.v1`
- 内容：
  - `meta`
  - `summary`
  - `findings`
  - `evidence_records`
  - `workflow`
  - `advice_report`
  - `formal_report`

### 审改建议报告
- 路径示例：`reports/sample/sample_advice_report.md`
- 用途：给学生或导师快速看“先改什么”

### 正式审改报告
- 路径示例：
  - `reports/sample/sample_formal_review_report.md`
  - `reports/sample/sample_formal_review_report.html`
  - `reports/sample/sample_formal_review_report.json`
- 用途：归档、提交、展示或后续二次处理

## VSCode 插件使用

扩展安装后，VSCode 左侧会出现 `Article Check` 工作台。

当前包含三个视图：
- 审改工作台
- 节点状态
- Evidence

支持以下交互：
- 审查当前论文
- 批量审查当前工作区论文
- 打开最近报告
- 打开正式审改报告
- 针对当前报告提问

## 当前架构

```text
article_check/
├── runtime.py                # 统一 runtime、结构化报告、建议报告、正式报告
├── orchestrator_v4/          # V4 TaskGraph / EventLog / Checkpoint / Workflow
├── context/                  # Curator 适配层与 ContextCacheBus
├── pipeline/                 # 当前生产主链：Orchestrator / Worker / Reviewer
├── references/               # 参考文献引擎
├── literature/               # 文献检索与综述
├── web/                      # FastAPI + React
└── llm/client/deepseek.py    # DeepSeek 客户端与结构化容错

vscode-extension/
├── src/extension.ts          # VSCode 工作台 / TreeView / 命令
├── media/                    # 图标
└── package.json              # 扩展声明
```

## 已验证的部署与使用效果

以下链路已在当前仓库中完成验证：

### CLI
- 单篇审查：

```bash
python -m article_check review tests/fixtures/sample.tex --json-output temp_report.json
```

- 批量审查：

```bash
python -m article_check batch temp_batch --concurrent 2 --json-output temp_batch_report.json
```

- 报告问答：

```bash
python -m article_check assist-report temp_report.json --question "我应该先修改哪些问题？" --json-output
```

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
