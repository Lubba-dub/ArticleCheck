# 📋 Article Check — 学术论文审查智能体

基于 **DeepSeek API** + **规则引擎** + **工作树隔离** 的学术论文格式审查与文献审查系统。

## 核心特性

| 特性 | 说明 |
|------|------|
| **双格式支持** | LaTeX (chktex 规则引擎) + Word (python-docx 样式检查) |
| **混合审查模式** | 规则引擎（零 token）+ AI 深度审查（DeepSeek API） |
| **工作树隔离** | 每篇论文独立工作区，并行互不干扰 |
| **批量并行** | 异步并发控制，一篇失败不影响其他 |
| **结构化输出** | 强制 JSON Schema，减少 30-50% completion tokens |
| **缓存优化** | 上下文缓存 + 语义缓存，大幅降低 API 成本 |
| **文献验证** | DOI 核实 / Semantic Scholar / arXiv 交叉验证 |
| **审查报告** | Markdown + JSON 双格式，机器可读 |

## 快速开始

```bash
# 安装
pip install -e .

# 单篇审查（格式 + 内容 + 文献）
article-check review paper.tex
article-check review paper.docx --api-key sk-xxx

# 仅格式检查（无需 API key）
article-check format paper.tex

# 批量审查目录
article-check batch ./papers/
article-check batch ./papers/ --concurrent 8

# 查看工具
article-check tools
```

## 项目架构

```
article_check/
├── core/            # Harness + Agent + Worktree 核心抽象
│   ├── harness/     # 6-layer Harness 架构（工具/上下文/约束）
│   ├── agent/       # Agent 注册表与基类
│   └── worktree/    # 工作树隔离（并行安全）
├── pipeline/        # 审查流水线
│   ├── orchestrator # 编排器（审查策略决策）
│   ├── worker/      # 审查 Worker（维度化）
│   └── reviewer     # 审阅者（综合评分+报告生成）
├── rules/           # 格式规则引擎
│   ├── latex/       # LaTeX chktex 规则
│   └── docx/        # Word python-docx 规则
├── llm/             # LLM 交互层
│   ├── client/      # DeepSeek API 客户端
│   ├── schemas/     # 结构化输出 Schema
│   └── cache/       # Token 缓存优化
├── mcp/             # MCP 工具（可被 LLM 调用）
│   └── tools/       # 格式/文献/搜索/报告工具
├── utils/           # 文件工具
└── config/          # 配置管理
```

## 设计原则

### 1. 分层 Token 优化

```
本地规则引擎 (零token) → 本地小模型 (低成本) → DeepSeek API (精准深度审查)
     ↓                    ↓                         ↓
  chktex/python-docx   规则聚类+初筛           结构化输出审查
```

### 2. 工作树隔离

每篇论文的运行互不干扰：
- 隔离工作目录 → 文件互不干扰
- 异步并发控制 → 一个失败不影响其他
- 报告自动保存 → 工作树可安全清理

### 3. 参考项目

本项目参考了以下开源项目：
- [coarse](https://github.com/Davidvandijcke/coarse) — 审稿流水线
- [reviewer2](https://github.com/isitcredible/reviewer2) — 对抗审稿
- [Loupe](https://github.com/AIScientists-Dev/loupe) — 数学审查
- [athena-loops](https://github.com/luckeyfaraday/athena-loops) — Agent 编排
- [OpenJudge](https://github.com/agentscope-ai/OpenJudge) — 多维度评分
- [validocx](https://github.com/tivaliy/validocx) — Word 格式验证

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | — |
| `ARTICLE_CHECK_ROOT` | 项目根路径 | 当前目录 |

## 许可证

MIT
