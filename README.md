# 📋 Article Check — 学术论文审查智能体

基于 **DeepSeek API** + **规则引擎** + **工作树隔离** 的学术论文格式审查与文献审查系统。
支持 LaTeX / Word 格式，单篇或批量并行，出具结构化审查报告。

---

## 🚀 一键启动

```bash
# 在项目根目录下，一行命令启动交互式菜单
python run.py
```

或者直接传参跳过菜单：

```bash
python run.py paper.tex         # 审查单篇论文
python run.py papers/           # 批量审查目录
```

> 也支持模块名启动：`python -m article_check start`

### 交互式菜单

启动后显示：

```
================================================================================
               📋 Article Check — 学术论文审查智能体
               v0.1.0 | DeepSeek API | 格式+文献+内容审查
================================================================================

   ✅ DeepSeek API     已配置 (sk-86164...)
   📌 格式模板         4 个内置 (IEEE, Elsevier, ACM, Springer LNCS)
   🔧 LaTeX chktex     未安装（使用正则降级）
   🔖 Git              ✅ d2376fe

  ┌────────────────────────────────────────────┐
  │  请选择操作                                 │
  ├────────────────────────────────────────────┤
  │  1  审查单篇论文                            │
  │  2  批量审查目录                            │
  │  3  格式检查（仅本地规则，零token）          │
  │  4  模板管理                               │
  │  5  查看配置与环境检查                       │
  │  6  自动检测论文模板                        │
  │  q  退出                                   │
  └────────────────────────────────────────────┘
  请输入 [1-6/q]:
```

---

## 📦 安装

```bash
# 1. 克隆仓库
git clone https://github.com/Lubba-dub/ArticleCheck.git
cd ArticleCheck

# 2. 安装依赖
pip install -e .

# 3. 配置 API Key（可选，不用则跳过内容审查）
#     方式 A：创建 .env 文件
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env
#     方式 B：环境变量
export DEEPSEEK_API_KEY=sk-your-key-here
```

### 可选依赖

```bash
pip install python-docx    # Word 格式检查（强烈推荐）
pip install pymupdf        # PDF 文本提取
choco install chktex       # LaTeX 40+规则引擎（Windows, 需要管理员）
```

---

## 💡 使用指南

### 单篇审查

```bash
# 一键交互式
python run.py

# 快捷模式（跳过菜单）
python run.py paper.tex
python run.py paper.docx

# CLI 模式
python -m article_check review paper.tex
python -m article_check review paper.docx
```

审查内容：
1. **格式检查** — 规则引擎（零 token）扫描格式问题
2. **内容审查** — DeepSeek API 分段深度分析（需 API key）
3. **文献审查** — 文献数量与格式校验
4. **报告生成** — Markdown + JSON 双格式

### 批量审查

```bash
# 一键批量
python run.py ./papers/

# CLI 模式（并发控制）
python -m article_check batch ./papers/
python -m article_check batch ./papers/ --concurrent 8
```

批量特点：
- 异步并发，默认 4 篇同时审查
- 每篇论文在独立工作树中运行，互不干扰
- 一篇失败不影响其他
- 汇总表格显示所有论文评分

### 格式检查（零 token）

```bash
python -m article_check format paper.tex
python -m article_check format paper.docx
```

仅使用本地规则引擎：
- LaTeX → chktex（40+ 规则）或正则降级
- Word → python-docx 样式检查
- **完全不消耗 API token**

### 模板格式审查

```bash
# 查看所有内置模板
python -m article_check template list

# 用 IEEE 模板检查论文格式
python -m article_check template check --template-name "IEEE Transactions" --paper paper.tex

# 自动检测论文匹配哪类模板
python -m article_check template auto-detect --paper paper.tex

# 搜索模板
python -m article_check template search --query conference
```

### 内置模板（4 个）

| 模板名称 | 类别 | LaTeX 文档类 | 适用场景 |
|---------|------|-------------|---------|
| IEEE Transactions | journal | `IEEEtran` | IEEE 系列期刊 |
| Elsevier | journal | — | Elsevier 旗下期刊 |
| ACM Conference | conference | `acmart` | ACM 会议论文 |
| Springer LNCS | conference | `llncs` | Springer 计算机科学 |

### 环境检查与配置

```bash
# 查看完整配置
python -m article_check config

# 列出已注册的 MCP 工具
python -m article_check tools

# 交互式菜单中选 5 也显示配置
python run.py
```

---

## 🏗 项目架构

```
article_check/
├── core/                    # 核心抽象层
│   ├── harness/             # 6-layer Harness（工具/上下文/约束/并发）
│   │   ├── base.py          # Harness 基类：工具管理、并发、Token 监控
│   │   └── tools.py         # 13 个 MCP 工具定义（格式/文献/搜索/报告）
│   ├── agent/               # Agent 注册表（工厂模式）
│   └── worktree/            # 工作树隔离（并行安全）
│       ├── manager.py       # 创建/管理/清理隔离工作区
│       └── isolation.py     # 隔离执行 + 产物保存工具
├── pipeline/                # 审查流水线
│   ├── orchestrator.py      # 编排器：审查策略、并行控制、批量调度
│   ├── worker.py            # FormatWorker / ContentWorker / ReferenceWorker
│   ├── reviewer.py          # 审阅者：综合评分 + Markdown/JSON 报告
│   └── models.py            # 共享数据模型（PaperTask, PipelineResult）
├── rules/                   # 格式规则引擎
│   ├── template.py          # 格式模板定义（8 组约束类）+ 4 个内置模板
│   ├── registry.py          # 模板注册表（搜索/注册/自动匹配）
│   ├── engine.py            # 模板规则引擎（18 条检查规则）
│   ├── latex/checker.py     # LaTeX chktex 包装器 + 正则降级
│   └── docx/checker.py      # Word python-docx 样式检查器
├── llm/                     # LLM 交互层
│   ├── client/deepseek.py   # DeepSeek API 客户端（结构化输出/Tool Calling）
│   ├── schemas/             # Pydantic Schema → JSON Schema（Token 优化）
│   └── cache/               # 三层缓存（精确命中/语义缓存/前缀缓存）
├── mcp/tools/               # MCP 工具实现
│   ├── format_tools.py      # 格式检查工具（零 token）
│   ├── reference_tools.py   # DOI 验证/文献核查（API 调用）
│   ├── search_tools.py      # arXiv 搜索（免费 API）
│   └── report_tools.py      # 报告生成工具
├── config/settings.py       # 全局配置（6 组：DeepSeek/Cache/Pipeline/格式/文献/报告）
├── cli.py                   # CLI + 交互式 start 菜单
└── utils/                   # 文件检测/读取/PDF 提取工具
```

---

## 🎯 核心设计：Token 优化"三明治"策略

```
审查一个问题 → 哪个层解决最划算？

Layer 1: 规则引擎（零 token）   → chktex 判断 "$$ 比 \[...\]"
Layer 2: 本地检查（零 token）   → "标题从 H1 跳到 H3"
Layer 3: DeepSeek（消耗 token） → "这个论证逻辑有问题吗？"
```

**为什么有效？** 论文中 80% 的格式问题可以用规则引擎解决，只有 20% 的语义问题需要 LLM。相比纯 LLM 方案，token 成本降低 **60-80%**。

---

## 🔧 Token 优化四层策略

| 策略 | 效果 | 实现位置 |
|------|------|---------|
| 规则引擎优先 | 省 60-80% token | `rules/latex/`, `rules/docx/`, `rules/engine.py` |
| 分段审查 | 避免 40% 上下文阈值退化 | `worker.py` ContentWorker._split_sections |
| 结构化输出 | completion tokens 省 30-50% | `llm/schemas/` → JSON Schema |
| 前缀缓存 | provider 自动缓存系统提示词 | `llm/cache/prompt_cache.py` |

---

## 🧪 审查流水线执行流程

```
                 PaperTask(论文路径)
                        │
   Orchestrator 创建 HarnessContext + WorktreeContext
                        │
   ┌────────────────────┼────────────────────┐
   │            Phase 1（并行，零 token）      │
   │  FormatWorker      │  ReferenceWorker    │
   │  chktex/docx规则   │  文献数/格式校验    │
   └────────────────────┼────────────────────┘
                        │
              Phase 2（DeepSeek API）
            ContentWorker 分段深度分析
                        │
              Phase 3（综合评估）
              Reviewer 汇总 → 报告
                        │
               Markdown + JSON 输出
```

---

## 🌐 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `.env` 文件或环境变量 |
| `ARTICLE_CHECK_ROOT` | 项目根路径 | 当前目录 |

---

## 📚 参考项目

本项目参考了以下开源项目：

| 项目 | 参考组件 | 用途 |
|------|---------|------|
| [coarse](https://github.com/Davidvandijcke/coarse) | 审查流水线 | orchestrator→worker→reviewer 范式 |
| [reviewer2](https://github.com/isitcredible/reviewer2) | 对抗审稿 | 幻觉过滤级联架构 |
| [Loupe](https://github.com/AIScientists-Dev/loupe) | 数学审查 | triage→deep 双阶段 |
| [athena-loops](https://github.com/luckeyfaraday/athena-loops) | Agent 编排 | 确定性流水线 Python 控制 |
| [OpenJudge](https://github.com/agentscope-ai/OpenJudge) | 多维评分 | 质量/正确性评分维度 |
| [validocx](https://github.com/tivaliy/validocx) | Word 验证 | docx 模板样式校验 |

---

## 📄 许可证

MIT
