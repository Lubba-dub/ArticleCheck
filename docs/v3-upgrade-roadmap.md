# 🚀 Article Check V3 — 升级方案白皮书

> 基于 2026 年 7 月前沿调研，覆盖格式审改、文献调研、批量并行三大方向

---

## 一、论文格式审改升级方案

### 1.1 投稿就绪检查（Submission-Ready Check）

对标 [submit-check](https://skillsmp.com/skills/grind-lab-core-night-owl-research-agent-skills-submit-check-skill-md) 和 [IEEE Compliance Framework](https://ieeexplore.ieee.org/document/11454060)：

**当前缺失 → 需要新增：**

| 功能 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| 目标期刊实时指南拉取 | ❌ 无 | 从期刊官网/API 拉取最新投稿要求 | 🔥 P0 |
| 投稿阶段感知 | ❌ 无 | double-blind / camera-ready / initial 不同阶段不同规则 | 🔥 P0 |
| 图表布局验证 | ❌ 无 | 图表尺寸、分辨率、字体嵌入检查 | 🔥 P0 |
| 报告格式规范 | ✅ 有 | 增加 PASS/FAIL 清单式报告 | P1 |
| AI 写作模式检测 | ❌ 无 | 标记 AI 生成嫌疑段落（期刊政策合规） | P1 |
| 跨语言一致性 | ❌ 无 | 中英文摘要对照翻译检查 | P2 |

**代码实现路径（~3 天）：**

```python
# 新增: journal_guideline_fetcher.py
from article_check.journals.guidelines import JournalGuidelineFetcher

fetcher = JournalGuidelineFetcher()
guidelines = fetcher.fetch("IEEE Transactions on Pattern Analysis")
# 返回: {word_limit, figure_count_max, ref_format, ...}

# 新增: submission_check.py
from article_check.checkers.submission import SubmissionChecker
checker = SubmissionChecker(guidelines)
report = checker.check(paper_path, stage="double-blind")
# PASS/FAIL 清单 + 具体修改建议
```

### 1.2 文档自动修正（Auto-Format Repair）

对标 [Paper Format Agent](https://github.com/zxyasfas/paper_format_agent)：

**当前缺失 → 需要新增：**

| 功能 | 当前状态 | 目标 |
|------|---------|------|
| Word 自动修正 | ❌ 无 | 直接修改 .docx 样式/字体/边距 |
| LaTeX 自动修正 | ⚠️ 手动 Edit | 代码级自动替换 |
| 格式指纹保护 | ❌ 无 | 哈希校验 → 防止修正时误改内容 |
| 修正日志 | ❌ 无 | modify_log.json 跟踪每步修改 |

**代码实现路径（~2 天）：**

```python
# DocxAutoFixer: 直接操作 python-docx 修改样式
from article_check.fixers.docx_fixer import DocxAutoFixer
fixer = DocxAutoFixer(template="IEEE")
fixes = fixer.apply(paper_path, issues)
# "已将字体从 Calibri 改为 Times New Roman"
# "已将上边距从 2.54cm 改为 1.905cm"
```

### 1.3 多粒度分段检测

**当前：** 整个文档一次读取 → 简单分段 → 格式检查
**升级后：**

```
输入 .docx/.tex
    │
    ├─ 布局分析层 (PubLayNet 或规则)
    │   ├─ 识别: 标题区 / 摘要 / 正文 / 图表 / 公式 / 参考文献
    │   └─ 每个区域独立检测
    │
    ├─ 规则引擎层
    │   ├─ 标题 → 大小写/编号/字体
    │   ├─ 正文 → 行距/缩进/字体一致性
    │   ├─ 图表 → 标题位置/编号连续性/分辨率
    │   ├─ 公式 → 编号/引用/字体
    │   └─ 参考文献 → 格式/DOI/引用匹配
    │
    └─ 语义一致性层 (SciBERT → cosine similarity)
        ├─ 章节标题与内容是否匹配
        └─ 图表引用是否在正文中出现
```

---

## 二、文献调研升级方案

### 2.1 多源平行检索

对标 [ScholarFlow](https://github.com/qianbkk/scholarflow) 的 8 节点流水线：

**当前：** 仅 arXiv 搜索（`search_tools.py`）
**升级后：**

```python
from article_check.literature.searcher import LiteratureSearcher

searcher = LiteratureSearcher()
results = searcher.parallel_search(
    query="music emotion recognition multimodal",
    sources=["semantic_scholar", "openalex", "arxiv", "crossref", "pubmed"],
    max_per_source=20,
    timeout=30,
)
# 返回: 100 篇去重排序论文
```

| 数据源 | API | 免费额度 | 状态 |
|--------|-----|---------|------|
| **Semantic Scholar** | graph/v1 | 100 req/s | 🔥 待接入 |
| **OpenAlex** | REST | 100k req/day | 🔥 待接入 |
| **CrossRef** | REST | 50 req/s | 🔥 待接入 |
| **arXiv** | API | 无限制 | ✅ 已接入 |
| **PubMed** | E-utilities | 10 req/s | P2 |

### 2.2 引文网络分析

对标 [CitationClaw](https://pypi.org/project/citationclaw/2.0.0/) 和 [Biblio Infinity](https://zenodo.org/records/20648811)：

```
输入论文的参考文献列表
    │
    ├─ 前向引用: 有哪些后续论文引用了这篇？
    │   └─ Semantic Scholar API → citation_count + citing_papers
    │
    ├─ 后向引用: 这篇引用的文献是什么？
    │   └─ OpenAlex API → referenced_works
    │
    ├─ 共引网络: 哪些论文和这篇被同一批论文引用？
    │   └─ 共引强度矩阵 → 社区发现(Louvain)
    │
    └─ 文献时序分析:
        ├─ 引用年份分布 → 新兴/成熟/衰退领域判断
        ├─ 关键文献识别 → betweenness centrality
        └─ 推荐补充文献 → 高共引但未被引用的论文
```

**核心收益：** 不止检查"引用格式是否正确"，更能回答"这篇论文遗漏了哪些关键文献？"

### 2.3 自动综述生成

对标 [ResearchPilot](https://arxiv.org/abs/2603.14629) 和 ScholarFlow：

```
用户: "帮我看看这个领域的研究现状"
    │
    ├─ 提取论文关键词和方法
    ├─ Semantic Scholar 搜索相关论文
    ├─ 引文链扩展 (forward + backward)
    ├─ LLM 分析 → 归纳出 3-5 个研究方向
    └─ 生成结构化综述 + D3 引文图谱
```

**技术路径：** LangGraph 编排 5 个 Agent 节点（Search → Expand → Analyze → Structure → Render）

### 2.4 文献质量评估

**当前：** DOI 验证、一致性检查
**升级后（新增指标）：**

| 指标 | 方法 | 说明 |
|------|------|------|
| **引用影响力** | Semantic Scholar citation count | 高被引 = 影响力大 |
| **期刊可信度** | 期刊 IF / 是否被 DOAJ 收录 | 预测审稿通过率 |
| **时效性** | 发表年份 + 被引年份分布 | 是否过时或前沿 |
| **复现性** | 是否有开源代码/数据集 | 论文可信度 |
| **引用准确性** | 引文上下文匹配 | 是否断章取义 |

---

## 三、批量并行性能提升方案

### 3.1 当前瓶颈分析

```
现状: asyncio.Semaphore(N) + 顺序审查
瓶颈:
  [1] 每篇论文独立调用 DeepSeek API → API 成为瓶颈
  [2] 没有 KV 缓存共享 → 相同内容重复编码
  [3] 串行报告生成 → 最后一个报告拖慢整体
  [4] 全部审查完才出结果 → 用户等待时间长
```

### 3.2 流式批处理（Streaming Batch）

**核心思想：审查完一篇立刻返回一篇，不等全部完成：**

```python
# 当前 (阻塞)
results = await orchestrator.review_batch(tasks)
# 全部完成后才返回

# 升级后 (流式)
async for partial_result in orchestrator.review_batch_stream(tasks):
    # 一篇完成立即显示
    display_result(partial_result)
    # UI 实时更新: "5/10 篇完成，以下为前5篇结果..."
```

**收益：** 用户体验从"等 5 分钟看结果"变为"30 秒开始陆续出结果"

### 3.3 共享 KV 缓存池

对标 [PolyKV](https://arxiv.org/abs/2604.24971)：

```
场景: 同一期刊批量审 20 篇论文
当前: 每篇调用 DeepSeek API → 20 次 → 20 倍 system prompt 传输
升级后:
  [1] system prompt 一次传入 → KV 缓存
  [2] 20 篇论文共享同一个 KV 缓存池
  [3] 只需要传输论文特有内容

收益: 多   → system prompt 传输从 N 倍降到 1 倍
实现: Multi-TurboQuant 插件 + 缓存键管理
```

### 3.4 Worker 池化与弹性伸缩

对标 [Hermes Concurrent Agents](https://github.com/r0b0tlab/hermes-concurrent-agents) 和 [MOSAIC](https://arxiv.org/abs/2606.03014)：

```python
class WorkerPool:
    """工作池 — 自适应并发"""
    
    async def acquire(self, task) -> Worker:
        # 自适应并发控制
        while self.active >= self.limit:
            # 如果队列>阈值, 提升 limit
            if len(self.queue) > 10:
                self.limit = min(self.limit + 1, self.max_limit)
            await asyncio.sleep(0.1)
        return Worker(task)
    
    def adjust(self, metrics: PoolMetrics):
        """根据实时指标动态调整"""
        # API 延迟低 → 加大并发
        if metrics.avg_latency < 1.0:
            self.limit += 1
        # 错误率上升 → 降低并发
        if metrics.error_rate > 0.05:
            self.limit -= 1
```

**弹性策略：**
| 信号 | 响应 |
|------|------|
| API 延迟 < 1s + 无错误 | ↑ 并发 +1 |
| API 延迟 > 5s | ↓ 并发 -2 |
| 错误率 > 5% | ↓ 并发 -1，等待 10s |
| 队列积压 > 20 | ↑ 最大并发 +2 |

### 3.5 关键路径感知调度

**当前：** 所有 Worker 同等优先级
**升级后：** CPM 关键路径决定优先级

```
任务 DAG:
    [格式检查] ─┬─→ [内容审查] ─→ [综合评分] ─→ [报告生成]
               └─→ [文献审查] ─→─↑
    
关键路径: 格式检查 → 内容审查 → 综合评分 → 报告生成 (8.5s)
非关键: 文献审查 (可并行, 不影响整体时间)

策略: 优先分配资源给关键路径任务
      "文献审查"可以先等 → 腾出 API 并发给"内容审查"
```

### 3.6 预估性能提升

| 优化手段 | 预期提升 | 实现难度 |
|---------|---------|---------|
| 流式批处理 | 体验提升（先到先出） | 低 |
| 共享 KV 缓存 | 30-50% token 节省 | 低 |
| Worker 池弹性伸缩 | 2-3× 吞吐量（高负载场景） | 中 |
| CPM 感知调度 | 15-25% 端到端延时降低 | 中 |
| PolyKV 集成 | 多 Agent 内存 O(N) → O(1) | 高 |

**综合预计**：批量审查 50 篇论文从当前约 10 分钟压缩到 **3-4 分钟**。

---

## 四、推荐实施路线

### Phase 1（1 周）— 立竿见影
```
□ 文献多源平行搜索 (Semantic Scholar + OpenAlex + CrossRef)
□ 投稿就绪检查 (journal guideline fetch + PASS/FAIL 报告)
□ 流式批处理 (先到先出)
```

### Phase 2（2 周）— 核心竞争力
```
□ Worker 池弹性伸缩 (自适应并发)
□ 引文网络分析 (前向/后向/共引)
□ 文档自动修正 (docx auto-repair)
□ CPM 关键路径调度
```

### Phase 3（1 月）— 质的飞跃
```
□ 自动综述生成 (LangGraph 多 Agent)
□ PolyKV 共享 KV 缓存集成
□ 多粒度分段检测 (布局分析+语义一致性)
□ 引文图谱可视化 (D3.js / NetworkX)
```

---

## 五、可合并的开源项目清单

| 领域 | 项目 | 集成方式 | 优先度 |
|------|------|---------|--------|
| **文献检索** | [ScholarFlow](https://github.com/qianbkk/scholarflow) | 算法移植 | 🔥 P0 |
| **文献检索** | [PaperSeek](https://github.com/MingfengHong/paperseek) | pip install | 🔥 P0 |
| **引文分析** | [CitationClaw](https://pypi.org/project/citationclaw/2.0.0/) | pip install | 🔥 P0 |
| **文献计量** | [Biblio Infinity](https://zenodo.org/records/20648811) | 直接引入前端 | P1 |
| **文献综述** | [ResearchPilot](https://arxiv.org/abs/2603.14629) | 代码参考 | P1 |
| **投稿检查** | [submit-check](https://skillsmp.com/skills/grind-lab-core-night-owl-research-agent-skills-submit-check-skill-md) | SKILL 移植 | P1 |
| **格式修正** | [Paper Format Agent](https://github.com/zxyasfas/paper_format_agent) | 代码参考 | P2 |
| **KV 共享** | [PolyKV](https://arxiv.org/abs/2604.24971) | pip + 改造 | P2 |
| **KV 压缩** | [Multi-TurboQuant](https://github.com/aivrar/multi-turboquant) | pip install | P2 |
| **并行调度** | [Hermes Concurrent](https://github.com/r0b0tlab/hermes-concurrent-agents) | 架构参考 | P3 |

Sources:
- [submit-check](https://skillsmp.com/skills/grind-lab-core-night-owl-research-agent-skills-submit-check-skill-md) — 投稿检查 Agent Skill
- [Paper Format Agent](https://github.com/zxyasfas/paper_format_agent) — 文档自动修正
- [IEEE Compliance Framework](https://ieeexplore.ieee.org/document/11454060) — 多阶段合规检查
- [ScholarFlow](https://github.com/qianbkk/scholarflow) — 多源文献检索流水线
- [PaperSeek](https://github.com/MingfengHong/paperseek) — 文献发现工具
- [CitationClaw](https://pypi.org/project/citationclaw/2.0.0/) — 引文影响分析
- [Biblio Infinity](https://zenodo.org/records/20648811) — 文献计量可视化
- [ResearchPilot](https://arxiv.org/abs/2603.14629) — 自动综述生成
- [PolyKV](https://arxiv.org/abs/2604.24971) — 共享 KV 缓存池
- [MOSAIC](https://arxiv.org/abs/2606.03014) — MoA 调度优化
- [Hermes Concurrent Agents](https://github.com/r0b0tlab/hermes-concurrent-agents) — 并发 Agent 部署
- [Scepsy](https://arxiv.org/abs/2604.15186) — Agentic 工作流调度
