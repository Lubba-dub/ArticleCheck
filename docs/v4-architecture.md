# Article Check V4 详细架构文档

> 面向“本科毕业论文格式核查与参考文献有效性验证”的统一审改与文献分析系统

---

## 1. 文档目标

本文档定义 `Article Check V4` 的目标定位、核心需求、总体架构、关键数据模型、执行主线、缓存与并发策略、领域子系统设计，以及分阶段敏捷迭代方案。

V4 的目标不是继续叠加一套新的并行架构，而是在当前项目已有的 `pipeline / curator / agents / web / polykv / pool` 基础上，收敛出一条可长期演进、适合高并发场景、并面向论文审改领域的统一主线。

---

## 2. 核心需求

### 2.1 业务问题定义

根据当前项目目标与需求输入，V4 必须首先服务以下核心场景：

**场景名称：本科毕业论文格式核查**

- 学院要求本科毕业论文遵循固定格式。
- 学生存在不按格式提交论文的情况。
- 在 AIGC 背景下，论文中可能出现虚假参考文献、错误引文、失效 DOI、与正文不一致的文献项等问题。
- 系统必须同时解决“格式核查”和“参考文献有效性验证”这两个核心问题。

### 2.2 一级需求

V4 的一级需求必须明确且不可发散，具体如下：

1. 对学生毕业论文进行批量检测。
2. 支持单篇论文检测。
3. 核查参考文献有效性，并对异常期刊、异常来源、失效引用做预警。
4. 输出格式核查报告，明确指出不符合规范的位置与原因。
5. 在以上核心功能稳定落地后，再承接可扩展特色能力。

### 2.3 产品北极星

V4 的北极星不是“做一个通用智能体平台”，而是：

**做一个适用于高校毕业论文与学术论文场景的、可批量运行、可追溯、可扩展的格式审改与文献分析系统。**

### 2.4 核心约束

V4 必须遵循以下约束：

- 以论文审改领域为中心，不以通用对话式 Agent 为中心。
- 以确定性工作流为主，以局部 Agent 自治为辅。
- 以证据链、规则链、引用链为核心，而不是仅输出自然语言建议。
- 以批量处理和单篇处理同时兼容为基本前提。
- 以高并发下的稳定性、成本控制、状态可恢复为系统级目标。

### 2.5 非目标

以下内容不属于 V4 当前阶段的主目标：

- 通用开放式多智能体聊天平台
- 通用代码智能体平台
- 先做复杂 LoRA/模型训练体系，再倒推业务需求
- 优先追求“完全自治”，而牺牲审计性与可解释性

---

## 3. V4 总体定位

### 3.1 V4 的一句话定义

V4 是一个面向论文格式审查、参考文献核验、文献调研与自动修正的**统一审改工作流系统**，其核心采用：

- `Review DAG` 作为确定性主流程
- `Context Curator` 作为统一上下文治理器
- `ContextCacheBus` 作为共享上下文与 PolyKV/ForkKV 承载总线
- `Elastic Worker Pool` 作为批量并发与流式执行底座
- `Evidence Store` 作为证据与审计中枢

### 3.2 V4 与现有版本关系

| 版本 | 主特点 | 主要问题 |
|------|--------|----------|
| V1 | `pipeline` 流水线可运行 | 文献阶段 stub，多入口不统一 |
| V2 | `curator` + 自回归编排实验 | 研究味重，未成为生产主线 |
| V3 | 提出并发、KV、综述等升级方向 | 路线较全，但未统一落地 |
| V4 | 统一 runtime + 统一执行核 + 统一缓存总线 | 目标是收敛和工程化 |

---

## 4. V4 架构原则

### 4.1 原则一：主线收敛

CLI、Web、Chat、批量流式接口都必须通过同一个 `build_runtime()` 组装出的运行时执行。

### 4.2 原则二：领域优先

系统首先服务以下核心对象：

- 论文文件
- 论文结构
- 模板规则
- 正文引用
- 参考文献条目
- 外部文献来源
- 审查证据
- 修正建议与补丁

### 4.3 原则三：证据优先

每条结论都必须可追溯到：

- 文档片段
- 规则命中
- 引用记录
- 外部文献元数据
- 执行步骤与时间

### 4.4 原则四：高并发优先

设计必须支持：

- 单篇同步运行
- 批量异步运行
- 流式先到先出
- 共享上下文复用
- 批次聚类与资源调度

### 4.5 原则五：可恢复执行

长流程必须支持：

- 事件日志
- checkpoint
- 中断恢复
- 人工介入
- 重试与回滚

---

## 5. V4 总体架构

### 5.1 分层架构

```text
+--------------------------------------------------------------+
|                        Entry Layer                           |
|          CLI / Web / Chat / Batch API / Admin UI            |
+------------------------------+-------------------------------+
                               |
                               v
+--------------------------------------------------------------+
|                      Runtime Assembly                        |
| build_runtime() -> config + tools + workers + cache + pool  |
+------------------------------+-------------------------------+
                               |
                               v
+--------------------------------------------------------------+
|                    Orchestrator V4 Layer                     |
|      ReviewIntent -> ReviewPlan -> TaskGraph -> Workflow     |
+------------------------------+-------------------------------+
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
+----------------+   +--------------------+  +------------------+
| Context Layer  |   | Execution Layer    |  | Resource Layer   |
| ContextCurator |   | Typed Workers      |  | Pool + CacheBus  |
+----------------+   +--------------------+  +------------------+
          |                    |                    |
          +--------------------+--------------------+
                               |
                               v
+--------------------------------------------------------------+
|                  Evidence & Report Layer                     |
| EvidenceStore / ReportAssembler / PatchPlan / ReviewReport   |
+--------------------------------------------------------------+
```

### 5.2 五大核心内核

V4 的执行内核由五部分组成：

1. `Runtime Kernel`：统一构造器，解决多入口装配不一致。
2. `Workflow Kernel`：Review DAG 和 loop 规则，解决执行收敛问题。
3. `Context Kernel`：上下文裁剪、摘要、打包、恢复。
4. `Resource Kernel`：共享缓存、弹性并发、批次复用。
5. `Evidence Kernel`：证据、审计、报告、修正闭环。

---

## 6. 关键模块设计

### 6.1 build_runtime()

#### 目标

统一 CLI、Web、Chat 三种入口的运行时构造逻辑，消除同一篇论文在不同入口下得到不同结果的问题。

#### 设计

```python
runtime = build_runtime(
    mode="web",                # cli / web / chat / batch
    enable_deep_review=True,
    enable_streaming=True,
    enable_cache=True,
    enable_checkpoint=True,
)
```

#### build_runtime() 输出对象

- `config`
- `tool_registry`
- `worker_registry`
- `context_curator`
- `context_cache_bus`
- `elastic_worker_pool`
- `evidence_store`
- `report_assembler`
- `orchestrator_v4`

#### 收益

- 单一运行主线
- 可统一测试
- 可统一观测
- 可统一注入缓存、上下文、调度、日志能力

---

### 6.2 ReviewIntent / ReviewPlan / EvidenceRecord

#### ReviewIntent

统一入口意图对象，用于表达“用户到底要做什么”。

```python
ReviewIntent(
    mode="batch_review",
    paper_paths=[...],
    template_name="undergraduate_thesis",
    institution="School of XXX",
    goals=[
        "检查格式规范",
        "验证参考文献有效性",
        "输出问题报告",
    ],
)
```

#### ReviewPlan

将意图映射为可执行计划。

```python
ReviewPlan(
    plan_id="plan_xxx",
    stages=["ingest", "format", "reference", "report"],
    strategy="deterministic_dag",
    budget={"max_tokens": 120000, "max_minutes": 20},
)
```

#### EvidenceRecord

统一证据记录结构，是 V4 的核心数据资产。

```python
EvidenceRecord(
    evidence_id="ev_xxx",
    paper_id="paper_xxx",
    stage="reference_validation",
    source_type="crossref",
    source_ref="10.xxxx/xxxx",
    location={"section": "参考文献", "index": 18},
    claim="该参考文献 DOI 无效",
    confidence=0.92,
    raw_payload={...},
)
```

#### 价值

- 统一数据边界
- 统一报告装配
- 统一缓存复用
- 统一审计日志

---

### 6.3 TaskGraph -> Stage Plan -> Worker Binding

#### 目标

把当前分散在 `pipeline`、`streaming`、`agents` 中的隐式执行顺序，收敛成显式任务图。

#### 标准阶段

V4 推荐的标准阶段如下：

1. `ingest`
2. `normalize`
3. `format_check`
4. `structure_check`
5. `reference_extract`
6. `reference_validate`
7. `literature_expand`
8. `coverage_gap`
9. `submission_check`
10. `auto_fix_plan`
11. `patch_apply`
12. `recheck`
13. `meta_review`
14. `report`

#### TaskGraph 设计原则

- 图结构显式化
- 节点职责单一
- 节点输入输出结构化
- 节点绑定明确 worker
- 节点具备预算、重试、优先级、证据要求

#### 示例图

```text
ingest
 -> normalize
 -> format_check ------+
 -> structure_check ---+--> meta_review -> report
 -> reference_extract -> reference_validate --+
 -> literature_expand -> coverage_gap --------+
 -> submission_check -------------------------+
 -> auto_fix_plan -> patch_apply -> recheck --+
```

#### Worker Binding

每个节点只允许绑定一类主 worker：

| 节点 | Worker |
|------|--------|
| format_check | `FormatWorker` |
| structure_check | `StructureWorker` |
| reference_extract | `ReferenceExtractWorker` |
| reference_validate | `ReferenceValidateWorker` |
| literature_expand | `LiteratureSearchWorker` |
| coverage_gap | `CoverageGapWorker` |
| submission_check | `SubmissionWorker` |
| auto_fix_plan | `AutoFixPlannerWorker` |
| patch_apply | `PatchExecutorWorker` |
| meta_review | `MetaReviewerWorker` |

---

### 6.4 ContextCurator 全量接入

#### 当前问题

目前只有部分路径使用上下文压缩思想，未成为全部 LLM worker 的统一入口。

#### V4 方案

所有 LLM worker 都通过 `ContextCurator` 生成活跃上下文：

```python
messages = context_curator.get_messages()
result = llm_worker.run(messages=messages, task=task)
```

#### 上下文层级

V4 采用四层上下文：

| 层级 | 名称 | 内容 |
|------|------|------|
| L0 | Scratch | 单步推理临时内容 |
| L1 | Run State | 当前论文执行态 |
| L2 | Shared Packs | 模板、期刊规则、结构包、章节包 |
| L3 | Long-Term Memory | 历史论文、常见错误、规则演化 |

#### 接入策略

- Phase B 先完成逻辑接入
- Phase C 再对共享上下文做 pack 化和 PolyKV/Fork 化

---

### 6.5 ContextCacheBus

#### 目标

统一当前 `SharedKVPool` 与 `PolyKVEngine` 两套逻辑，构建一个真正为批量审查服务的上下文缓存总线。

#### 职责

- 存储共享 prompt、规则包、章节包、检索结果包
- 统一 `put/get/acquire/release/fork/diff/evict`
- 管理 TTL、LRU、引用计数、压缩级别
- 提供命中率、复用率、节省 token 量等指标

#### 核心对象

| 类型 | 说明 |
|------|------|
| `TemplatePack` | 模板规则与说明 |
| `SubmissionPack` | 投稿阶段与期刊要求 |
| `StructurePack` | 文档结构树与分区结果 |
| `SectionPack` | 章节摘要与片段索引 |
| `ReferencePack` | 规范化参考文献集合 |
| `LiteraturePack` | 检索结果、引文图扩展结果 |
| `EvidencePack` | 某阶段产生的证据集合 |

#### API 草案

```python
pack_id = cache_bus.put_pack(pack, level="standard")
cache_bus.acquire(pack_id, run_id)
fork_id = cache_bus.fork_from(pack_id, run_id, mode="copy_on_write")
diff_id = cache_bus.put_diff(base_id=pack_id, content=delta)
pack = cache_bus.get(pack_id)
cache_bus.release(pack_id, run_id)
```

---

### 6.6 ElasticWorkerPool 统一调度

#### 当前问题

当前批量并发主要依赖 `Semaphore`，流式与批量分离，不能做细粒度调度和资源优先级控制。

#### V4 方案

所有批量、流式、后台任务统一使用 `ElasticWorkerPool`：

- 支持动态并发调整
- 支持按任务类型分池
- 支持优先级队列
- 支持关键路径优先
- 支持故障降级

#### 资源池划分

| 池类型 | 主要任务 |
|--------|----------|
| `llm_pool` | 内容评审、综述、meta review |
| `search_pool` | Semantic Scholar / OpenAlex / CrossRef 等 |
| `io_pool` | 读写文件、报告输出、缓存落盘 |
| `patch_pool` | 自动修正与回滚 |
| `cpu_pool` | 本地规则、PDF/Docx 解析、结构分析 |

#### 调度原则

- 关键路径优先
- 高价值缓存命中优先
- 批次聚类优先
- 失败率上升则降并发
- API 延迟降低则升并发

---

### 6.7 事件日志与 Checkpoint

#### 目标

将 V4 从“能跑的流程”提升为“可恢复的系统”。

#### 事件类型

- `run_started`
- `intent_parsed`
- `plan_compiled`
- `node_scheduled`
- `node_started`
- `node_completed`
- `node_failed`
- `checkpoint_saved`
- `checkpoint_restored`
- `human_override`
- `patch_applied`
- `run_finished`

#### Checkpoint 内容

- 当前 `ReviewPlan`
- `TaskGraph` 执行位置
- 已完成节点结果
- 活跃 Pack 引用关系
- 当前上下文压缩状态
- 当前 Evidence 累积状态
- 当前预算消耗

#### 收益

- 批量任务可恢复
- 流式任务可断点续跑
- Web 端可展示节点状态
- 审查链路可审计

---

## 7. 面向论文审改领域的子系统设计

### 7.1 格式审查子系统

#### 核心目标

检查学生毕业论文是否符合固定模板与学院格式要求。

#### 范围

- 页面布局
- 字体字号
- 行距缩进
- 标题层级
- 封面与摘要
- 图表标题
- 公式编号
- 参考文献格式

#### 输出

- 规则命中列表
- 问题位置
- 严重程度
- 可自动修正项

---

### 7.2 参考文献有效性验证子系统

#### 核心目标

这是 V4 的一级核心需求，必须与格式核查并列，而不是附属功能。

#### 检查范围

- 引文与参考文献是否一致
- DOI 是否存在
- 文献信息是否完整
- 期刊/会议是否可识别
- 是否存在异常来源或虚假引用
- 是否存在可疑期刊、掠夺性期刊或低可信来源

#### 风险输出

- `invalid_doi`
- `missing_metadata`
- `title_author_mismatch`
- `suspicious_journal`
- `citation_not_in_text`
- `text_citation_missing_ref`

#### 领域价值

该模块直接回应 AIGC 场景下“虚假参考文献”的现实问题，因此在优先级上不低于格式检查。

---

### 7.3 文献分析与相关工作覆盖子系统

#### 核心目标

在完成参考文献真实性验证之后，进一步分析：

- 是否遗漏关键文献
- 相关工作覆盖是否充分
- 是否引用了低质量或过时文献

#### 执行图

```text
query_plan
 -> multi_source_search
 -> dedup
 -> rerank
 -> citation_neighborhood_expand
 -> coverage_gap_analysis
 -> novelty_gap_summary
```

#### 适用位置

- 本科论文抽检
- 研究生论文审查
- 教师审稿辅助
- 文献综述自动生成

---

### 7.4 自动修正闭环

#### 目标

自动修正不能只是一段“建议文本”，而必须形成闭环：

1. 发现问题
2. 生成修正计划
3. 生成 patch
4. 干跑验证
5. 应用 patch
6. 再次复检
7. 记录修改日志

#### Patch 协议

V4 统一 Word 与 LaTeX 的修正协议：

- `PatchDraft`
- `PatchApplyResult`
- `PatchRollbackPoint`

#### Web 支持

- 修正前后对比
- 单项采纳或拒绝
- 人工改判
- 回滚

---

## 8. 高并发与 PolyKV/Fork 化设计

### 8.1 为什么论文审改场景特别适合共享缓存

在高校论文场景中，经常出现：

- 同一学院、同一模板、同一批次的大量论文
- 相同的 system prompt、规则集、模板说明反复注入
- 相似的参考文献校验流程反复运行
- 多个 worker 对同一篇论文的相同结构信息重复处理

这使得论文审改成为非常适合 `shared pack + fork diff` 的场景。

### 8.2 V4 的缓存层次

| 层次 | 说明 |
|------|------|
| `Pack Cache` | 结构化共享数据包 |
| `Prompt Cache` | 共享 prompt 与模板说明 |
| `KV Cache` | 真实模型 KV 或逻辑 KV 代理 |
| `Diff Cache` | 子任务增量差异 |
| `Artifact Cache` | 中间产物与报告草稿 |

### 8.3 Shared Pack + Fork Diff

#### 基本模型

```text
Base TemplatePack
    ├─ Fork: Paper A FormatWorker
    ├─ Fork: Paper A ReferenceWorker
    ├─ Fork: Paper B FormatWorker
    └─ Fork: Paper B SubmissionWorker
```

#### 规则

- 基础 pack 不可变
- 子任务只写 diff
- 合并时按 evidence 或 patch 策略汇总
- 引用计数归零后再淘汰

### 8.4 批次聚类执行

V4 在批量执行前先聚类：

- 按模板聚类
- 按学院规则聚类
- 按期刊/投稿目标聚类
- 按学科关键词聚类

#### 目的

- 提高 pack 复用率
- 降低 prompt 传输与重复解析成本
- 让文献检索与规则检查更稳定

### 8.5 reuse-aware 调度

调度不只看依赖关系，还看缓存复用价值：

- 高复用 pack 的任务优先成批执行
- 共享 prompt 命中率高的任务优先编排
- 文献检索结果可复用的论文优先打包处理

---

## 9. Web 与交互工作台设计

### 9.1 Web 不再只是 API 面板

V4 的 Web 前端应升级成“审改工作台”，而不是简单页面壳。

### 9.2 核心界面

1. 批量任务总览
2. 单篇论文审查详情
3. 节点执行状态面板
4. 证据面板
5. 引用风险面板
6. 自动修正面板
7. 人工改判面板
8. 报告导出面板

### 9.3 核心交互

- 审查中流式展示
- 节点失败后可重试
- 单条 evidence 可人工改判
- patch 可逐项应用
- 支持下载学院汇总报告

---

## 10. 目录重构建议

### 10.1 新目录结构

```text
article_check/
├── runtime/
│   ├── build.py
│   ├── registry.py
│   └── services.py
│
├── orchestrator_v4/
│   ├── intent.py
│   ├── plan.py
│   ├── dag.py
│   ├── workflow.py
│   ├── events.py
│   └── checkpoint.py
│
├── context/
│   ├── curator.py
│   ├── packs.py
│   ├── memory.py
│   └── evidence.py
│
├── cache/
│   ├── bus.py
│   ├── polykv_adapter.py
│   ├── fork_store.py
│   └── reuse_policy.py
│
├── review/
│   ├── workers/
│   │   ├── format.py
│   │   ├── structure.py
│   │   ├── reference.py
│   │   ├── literature.py
│   │   ├── submission.py
│   │   ├── writing.py
│   │   ├── autofix.py
│   │   └── meta.py
│   └── report.py
│
├── batch/
│   ├── dispatcher.py
│   ├── grouping.py
│   ├── streaming.py
│   └── quota.py
│
└── web/
    ├── api/
    ├── views/
    └── presenters/
```

### 10.2 旧模块迁移原则

- `pipeline` 中稳定 DTO 保留并迁移
- `curator` 核心能力保留并提升为公共层
- `agents` 保留为入口层，不再作为主执行层
- `web/server.py` 只做 API 汇聚，不再手工拼装工作流

---

## 11. 敏捷迭代总览

### 11.1 迭代原则

每个阶段都必须形成：

- 明确目标
- 用户价值
- 代码边界
- 验收标准
- 风险与回退策略

### 11.2 Phase 总览

| 阶段 | 周期 | 主题 |
|------|------|------|
| Phase A | 2 周 | 收敛主线 |
| Phase B | 3-4 周 | 引入 V4 执行核 |
| Phase C | 4-6 周 | PolyKV / Fork 化 |
| Phase D | 4 周 | 领域强化 |
| Phase E | 后续 | 真实系统级优化 |

---

## 12. 各阶段敏捷迭代沉淀

### 12.1 Phase A：收敛主线（2 周）

#### 目标

把当前多入口、多装配、多并发实现收敛成统一 runtime 与统一批量执行入口。

#### 范围

- 新建 `build_runtime()`
- 统一 CLI / Web / Chat 到同一 runtime
- `review_batch` 与 `review_batch_stream` 改由统一 pool 调度
- `ReferenceWorker` 真正打通到底层文献引擎
- 引入 `ReviewIntent / ReviewPlan / EvidenceRecord`

#### 产出

- `runtime/build.py`
- `runtime/registry.py`
- `review/reference.py`
- `batch/dispatcher.py`
- `orchestrator_v4/intent.py`
- `orchestrator_v4/plan.py`
- `context/evidence.py`

#### Sprint 建议

**Sprint A1**

- 建 `build_runtime()` 和运行时注册器
- 统一入口层调用
- 加 smoke test

**Sprint A2**

- 接入统一 pool
- 打通 `ReferenceWorker`
- 补 `ReviewIntent / ReviewPlan / EvidenceRecord`
- 做 CLI/Web 一致性验证

#### 验收标准

- 同一篇论文从 CLI/Web/Chat 得到一致主结果
- `review_batch` 与 `review_batch_stream` 共用一套调度底座
- `ReferenceWorker` 不再是 stub
- evidence 可在报告中落地

#### 风险

- 多入口迁移引发接口不兼容
- 旧 API 依赖强耦合

#### 回退策略

- 保留 V1 兼容入口
- build_runtime 引入 feature flag

---

### 12.2 Phase B：引入 V4 执行核（3-4 周）

#### 目标

建立统一的 DAG 工作流和状态执行内核。

#### 范围

- 落地 `TaskGraph -> stage plan -> worker binding`
- 把 `ContextCurator` 接入全部 LLM workers
- 实现 `ContextCacheBus`，先逻辑复用，再压缩
- 实现事件日志与 checkpoint

#### 产出

- `orchestrator_v4/dag.py`
- `orchestrator_v4/workflow.py`
- `orchestrator_v4/events.py`
- `orchestrator_v4/checkpoint.py`
- `cache/bus.py`
- `context/curator.py`

#### Sprint 建议

**Sprint B1**

- 建 DAG 与 worker binding
- 将阶段逻辑显式化

**Sprint B2**

- 接 ContextCurator 到全部 LLM worker
- 引入 ContextCacheBus 的逻辑级版本

**Sprint B3**

- 事件日志
- checkpoint
- Web 节点状态展示初版

#### 验收标准

- 核心工作流由 DAG 定义，不再散落在多个入口文件
- 所有 LLM worker 使用统一上下文接口
- checkpoint 可恢复中断任务
- 节点状态可查询

---

### 12.3 Phase C：PolyKV / Fork 化（4-6 周）

#### 目标

把共享上下文从“逻辑复用”升级为“共享 pack + fork diff + reuse-aware 调度”。

#### 范围

- 模板包、投稿包、结构包、章节包、文献包统一 pack 化
- 实现 `shared pack + fork diff`
- 批次聚类执行
- 关键路径优先 + reuse-aware 调度

#### 产出

- `context/packs.py`
- `cache/polykv_adapter.py`
- `cache/fork_store.py`
- `cache/reuse_policy.py`
- `batch/grouping.py`

#### Sprint 建议

**Sprint C1**

- pack 结构定义
- pack 生命周期管理

**Sprint C2**

- fork/diff 机制
- reuse-aware 指标

**Sprint C3**

- 聚类批处理
- 关键路径 + 复用联合调度

#### 验收标准

- 同模板批量运行时可观测到 pack 复用
- 批次执行具备聚类能力
- 缓存命中率与节省 token 量可度量

#### 注意

Phase C 先做逻辑 Pack/Fork，不强依赖真实 GPU KV 注入。

---

### 12.4 Phase D：领域强化（4 周）

#### 目标

围绕论文审改的核心价值，做真正拉开差异化的领域能力。

#### 范围

- 新颖性 / 遗漏引用 / 相关工作覆盖子图
- 自动修正闭环
- Web 证据面板、节点状态、人工改判

#### 产出

- `review/workers/literature.py`
- `review/workers/meta.py`
- `review/workers/autofix.py`
- Web evidence panel
- Human review actions

#### Sprint 建议

**Sprint D1**

- coverage gap 子图
- 缺失文献推荐

**Sprint D2**

- 自动修正计划与 patch 闭环

**Sprint D3**

- Web 证据面板
- 人工改判与二次生成

#### 验收标准

- 能输出“格式问题 + 参考文献风险 + 相关工作覆盖不足”三类综合报告
- 自动修正形成闭环
- Web 支持证据查看与人工修订

---

### 12.5 Phase E：真实系统级优化（后续）

#### 目标

在本地 GPU 或推理服务部署场景下，进一步推进底层缓存与性能优化。

#### 范围

- 真实 KV 注入
- 分层缓存
- `RoPE-aware prefetch`
- `copy-on-write cache pages`
- 更底层的 PolyKV/ForkKV 风格接入

#### 前提

只有在以下条件满足后再进入：

- V4 工作流稳定
- cache bus 已经形成统一抽象
- batch clustering 与 reuse-aware scheduling 已经落地

#### 验收方向

- 更高吞吐
- 更低内存开销
- 更短 TTFT
- 更强批量处理能力

---

## 13. 敏捷管理机制

### 13.1 每阶段必须沉淀的工件

每个阶段都必须输出以下工件：

1. `phase-goals.md`
2. `backlog.md`
3. `acceptance-checklist.md`
4. `risk-log.md`
5. `demo-script.md`
6. `metrics-report.md`

### 13.2 建议指标

| 指标 | 说明 |
|------|------|
| 单篇审查平均耗时 | 核心性能指标 |
| 批量 20 篇吞吐量 | 并发能力指标 |
| CLI/Web 一致性 | 主线收敛指标 |
| 缓存命中率 | 复用指标 |
| token 节省率 | 成本指标 |
| reference 风险发现率 | 领域有效性指标 |
| 自动修正成功率 | 闭环能力指标 |
| 人工改判后复审收敛率 | HITL 有效性指标 |

### 13.3 Definition of Done

每阶段只有满足以下条件才算完成：

- 功能跑通
- 有自动化验证
- 有文档更新
- 有验收脚本
- 有指标结果
- 能回滚

---

## 14. 风险与取舍

### 14.1 最大风险

- 架构过度前沿化，业务主线反而变弱
- PolyKV 提前下沉到底层模型，引入过多工程复杂度
- 文献分析路线过重，影响格式与引用核查主价值
- Web 交互提前做太多，主执行核未稳定

### 14.2 核心取舍

- 先统一 runtime，再谈高阶 Agent
- 先逻辑 pack/fork，再谈真实 KV 注入
- 先把参考文献有效性打实，再扩展到 novelty gap
- 先让系统“可靠”，再让系统“更聪明”

---

## 15. V4 最终目标图

```text
用户上传论文 / 批量目录
        |
        v
ReviewIntent
        |
        v
build_runtime()
        |
        v
ReviewPlan -> TaskGraph -> ElasticWorkerPool
        |
        +--> Format / Structure / Reference / Literature / Submission
        |          |            |            |            |
        |          +------------+------------+------------+
        |                       |
        |                 EvidenceStore
        |                       |
        +--> AutoFixPlan -> Patch -> Recheck
        |                       |
        +-----------------------+
                                |
                                v
                         Meta Review / Report
                                |
                                v
                 Web 面板 / 批量汇总报告 / 单篇审查报告
```

---

## 16. 结论

V4 的核心不是新造一个更复杂的“通用多智能体平台”，而是明确回到最重要的业务问题：

- 本科毕业论文格式核查
- 参考文献有效性验证
- 批量检测与单篇检测并行支持
- 输出可执行、可定位、可追溯的审查报告

在这个前提下，V4 通过：

- 统一 runtime
- 统一执行核
- 统一上下文治理
- 统一共享缓存总线
- 统一证据与报告系统

把当前项目从“多方向探索中的研究原型”，收敛为“高并发场景下可持续演进的论文审改系统”。

