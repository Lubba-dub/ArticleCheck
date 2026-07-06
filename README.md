# 📋 Article Check — 学术论文审查与文献调研智能体

基于 **DeepSeek API** + **规则引擎** + **多源平行检索** + **自压缩上下文策展** 的学术论文全流程审查与修正系统。
支持 LaTeX / Word 格式审查、自动修正、文献检索、引文分析、综述生成、投稿就绪检查。

[![GitHub](https://img.shields.io/badge/GitHub-ArticleCheck-blue)](https://github.com/Lubba-dub/ArticleCheck)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://python.org)

---

## 🚀 一键启动

```bash
# 在项目根目录下
python run.py               # 交互式菜单
python run.py chat           # 自然语言对话模式（推荐）
python run.py paper.tex      # 快捷审查单篇
python run.py papers/        # 批量审查目录
python run.py --help         # 查看全部命令
```

对话模式下直接说话即可驱动：

```
🗣️  "帮我看看这篇论文 paper.tex"    → 审查
🗣️  "改成IEEE格式"                 → 自动修正
🗣️  "查一下这篇论文的引用"          → 文献分析+引文图谱
🗣️  "帮我写个文献综述"              → 自动综述生成
🗣️  "这篇投稿IEEE能过吗？"          → 投稿就绪检查
🗣️  "批量审这个目录"               → 流式批处理
```

---

## ✨ 核心能力

### 论文格式审查
| 能力 | 说明 |
|------|------|
| **LaTeX 格式检查** | chktex 40+ 规则（零 token）+ 正则降级 |
| **Word 格式检查** | python-docx 样式/字体/边距/标题层级 |
| **模板格式审查** | 18 条规则 × 4 内置模板（IEEE/Elsevier/ACM/LNCS） |
| **投稿就绪检查** | 目标期刊要求逐条核对，PASS/FAIL 报告 |
| **匿名化检查** | double-blind 阶段自动检测作者/致谢泄露 |
| **自动修正** | 直接修复 .docx 字体/边距/页码/标题样式 |

### 内容深度审查
| 能力 | 说明 |
|------|------|
| **分段深度分析** | 按章节分段送入 DeepSeek，避免 40% 上下文阈值 |
| **结构化输出** | JSON Schema 强制输出 → completion tokens 省 30-50% |
| **综合评分** | 格式 × 0.25 + 内容 × 0.50 + 文献 × 0.25 |
| **审查报告** | Markdown + JSON 双格式 |

### 文献调研
| 能力 | 说明 |
|------|------|
| **多源平行检索** | 5 个学术数据源并发搜索 + 去重排序 |
| **参考文献提取** | 从 BibTeX / LaTeX bibitem / Word docx 自动提取 |
| **交叉验证** | 正文引用 ↔ 参考文献一致性检查 |
| **格式生成** | IEEE / APA / ACM / Springer LNCS / Nature 输出 |
| **DOI 验证** | CrossRef API 实时元数据查询 |
| **引文网络分析** | 前向引用、后向引用、共引矩阵、领域趋势判断 |
| **遗漏文献发现** | 检索相关文献 → 对比已有引用 → 推荐补充 |
| **自动综述生成** | 多源搜索 → 论文聚类 → 趋势分析 → Markdown 综述 |
| **引文图谱** | D3.js 力导向图 + 年度分布柱状图 HTML |

### 批量并行
| 能力 | 说明 |
|------|------|
| **工作树隔离** | 每篇论文独立目录 → 并行互不干扰 |
| **流式批处理** | 审查完一篇立即返回，不等全部完成 |
| **弹性 Worker 池** | 根据 API 延迟/错误率/队列深度自适应调整并发 |
| **CPM 关键路径调度** | 关键路径优先分配资源 |
| **自适应限流** | API 错误率上升自动降并发，延迟降低自动回升 |

### V2 智能体引擎
| 能力 | 说明 |
|------|------|
| **Context Curator** | 独立上下文策展，与任务执行解耦 |
| **三层弹性类型** | RAW / ABSTRACT / DROP 完全可逆 |
| **ACON 自适应** | 从失败中学习压缩策略 |
| **运筹学调度** | AdaptOrch 四拓扑 + CPM 关键路径 |
| **LatentRelay** | 隐空间通信：KV key / 向量 / 任务ID 引用 |
| **Self-Loop** | 自回归自我编排：LLM 自决定下一步 |

---

## 📦 安装

```bash
# 1. 克隆
git clone https://github.com/Lubba-dub/ArticleCheck.git
cd ArticleCheck

# 2. 一键安装
双击 install.bat    # Windows
# 或
pip install -e .

# 3. 配置 API Key（可选，不用则跳过内容审查）
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env
```

### 可选依赖
```bash
pip install python-docx      # Word 格式检查（强烈推荐）
pip install pymupdf          # PDF 文本提取
# chktex: LaTeX 40+ 规则引擎（需要系统安装）
```

### 构建单文件 exe
```bash
pip install pyinstaller
python build_exe.py
# → dist/ArticleCheck.exe（双击即用）
```

---

## 💡 使用指南

### 自然语言对话模式
```bash
python run.py chat
```
输入自然语言即可驱动全部功能：

| 你说 | 系统做什么 |
|-----|-----------|
| "帮我看看 paper.tex" | 模板检测 + 格式检查 + 结构分析 + 文献提取 |
| "查格式 paper.docx" | 快速格式检查（零 token） |
| "改成IEEE格式" | 自动检测模板 → 修正格式 |
| "查引用" | 提取参考文献 → 交叉验证 → 格式生成 |
| "查一下这篇论文的引文网络" | DOI 验证 → 引文分析 → 生成引文图谱 |
| "写个文献综述" | 多源搜索 → 聚类 → 趋势分析 → Markdown |
| "批量审 papers/" | 流式批处理（逐篇返回结果） |
| "这篇投IEEE能过吗？" | 投稿就绪检查（PASS/FAIL 清单） |

### 格式检查（零 token）
```bash
python -m article_check format paper.tex
python -m article_check format paper.docx
```

### 模板格式审查
```bash
python -m article_check template list
python -m article_check template check --template-name "IEEE Transactions" --paper paper.tex
python -m article_check template auto-detect --paper paper.tex
```

### 嵌入式参考项目
本项目参考了以下开源项目的思想：
- [coarse](https://github.com/Davidvandijcke/coarse) — 审查流水线
- [reviewer2](https://github.com/isitcredible/reviewer2) — 对抗审稿
- [Loupe](https://github.com/AIScientists-Dev/loupe) — 数学审查
- [ScholarFlow](https://github.com/qianbkk/scholarflow) — 文献检索流水线
- [PaperSeek](https://github.com/MingfengHong/paperseek) — 文献发现
- [CitationClaw](https://pypi.org/project/citationclaw/2.0.0/) — 引文分析
- [athena-loops](https://github.com/luckeyfaraday/athena-loops) — Agent 编排

---

## 🏗 项目架构

```
article_check/
├── core/                    # 核心抽象
│   ├── harness/             # 6-layer Harness（17 个 MCP 工具）
│   ├── agent/               # Agent 注册表
│   ├── worktree/            # 工作树隔离（并行安全）
│   └── pool.py              # 弹性 Worker 池（自适应并发）
├── pipeline/                # 审查流水线
│   ├── orchestrator.py      # V1 编排器
│   ├── streaming.py         # 流式批处理（先到先出）
│   ├── worker.py            # FormatWorker / ContentWorker / ReferenceWorker
│   ├── reviewer.py          # 审阅者（评分 + 报告）
│   └── models.py            # 共享数据模型
├── curator/                 # V2 智能体引擎
│   ├── __init__.py          # Context Curator（弹性类型/可逆压缩/3策略）
│   └── orchestrator_v2.py   # V2 自编排（CPM/拓扑路由/LatentRelay）
├── rules/                   # 格式规则引擎
│   ├── template.py          # 格式模板定义（8 组约束）
│   ├── registry.py          # 模板注册表
│   └── engine.py            # 18 条模板检查规则
├── literature/              # V3 文献调研
│   ├── searcher.py          # 5 源平行检索
│   ├── citation.py          # 引文网络分析
│   ├── survey.py            # 自动综述生成
│   └── viz.py               # D3 引文图谱可视化
├── checkers/                # V3 投稿检查
│   └── submission.py        # 投稿就绪检查
├── fixers/                  # V3 自动修正
│   └── docx_fixer.py        # Word 自动修正
├── references/              # 参考文献引擎
│   └── engine.py            # 解析/生成/验证/交叉检查
├── llm/                     # LLM 交互层
│   ├── client/deepseek.py   # DeepSeek API 客户端
│   ├── schemas/             # 结构化输出 Schema
│   └── cache/               # 三层缓存
├── mcp/tools/               # 17 个 MCP 工具实现
├── chat.py                  # 自然语言对话模式
├── cli.py                   # CLI + 交互式菜单
└── config/settings.py       # 全局配置
```

---

## 🎯 Token 优化策略

```
Layer 1: 规则引擎（零 token）    → chktex / python-docx 格式检查
Layer 2: 分段审查                 → 避免 40% 上下文阈值退化
Layer 3: 结构化输出               → completion tokens 省 30-50%
Layer 4: 前缀缓存                 → provider 级自动缓存
Layer 5: Context Curator          → 弹性类型压缩 / 自适应阈值
Layer 6: LatentRelay              → 隐空间通信省 80-90%
```

---

## 📊 测试

实测论文：《基于多模态情绪识别的AI音乐疗愈系统》（8.2MB, 14 篇参考文献）
- 全流程 25+ 子项通过
- 14 篇参考文献正确提取
- 交叉验证一致性评分 0.80
- 可在 4 个阶段完成完整审查（格式→文献→综述→报告）

---

## 📄 许可证

MIT
