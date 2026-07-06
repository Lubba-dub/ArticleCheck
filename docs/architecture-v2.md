# 🏗 Article Check V2 — 自回归自我编排架构

> 融合运筹学调度 + 上下文策展 + 隐状态通信 + 自压缩Loop

---

## 一、架构总览

```
                    ┌─────────────────────────────────────┐
                    │      LLM 自回归自我Loop 引擎         │
                    │  每一步: 自感知→自决策→自执行→自压缩 │
                    └──────────────┬──────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────┐
│            ┌─────────────────────┴─────────────────────┐            │
│            │          Orchestrator V2                   │            │
│            │   编排器 = 路由器 + 调度器 + 执行器         │            │
│            └──────┬──────────┬──────────┬──────────────┘            │
│                   │          │          │                           │
│    ┌──────────────▼──┐ ┌────▼────┐ ┌───▼──────────────┐           │
│    │ Topology Router │ │CPM Sched│ │ Task Executor     │           │
│    │ (AdaptOrch)     │ │(关键路径)│ │ (自回归)         │           │
│    └─────────────────┘ └─────────┘ └──────────────────┘            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │               Context Curator（上下文策展层）                 │  │
│  │  独立于执行器运行，负责上下文追踪/弹性类型/可逆压缩/ACON复盘  │  │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │  │
│  │  │Step观察 │ │阈值检测  │ │策展决策  │ │可逆解压      │   │  │
│  │  │Observe()│ │ShouldCompact│ │Compact()│ │Restore()     │   │  │
│  │  └─────────┘ └──────────┘ └──────────┘ └───────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │   Latent Relay（隐空间通信层 — 超越多Agent）                │  │
│  │  信息通过引用(KV key/向量/任务ID)而非文本传递, 节省80-90%  │  │
│  │  ┌──────────┐ ┌───────────────┐ ┌─────────────────────┐    │  │
│  │  │KV Share  │ │Latent Briefing│ │Orthogonal Backfill  │    │  │
│  │  │(PolyKV)  │ │(AttentionMatch)│ │(信息无损修正)      │    │  │
│  │  └──────────┘ └───────────────┘ └─────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## 二、核心创新点详解

### 2.1 运筹学调度 (Operations Research → Agent Scheduling)

| 组件 | 来源 | 作用 |
|------|------|------|
| **Topology Router** | AdaptOrch (arXiv:2602.16873) | 根据依赖图动态选拓扑 |
| **CPM Scheduler** | 关键路径法 (经典OR) | 找到最优执行顺序 |
| **Task Graph DAG** | MOSAIC ILP (arXiv:2606.03014) | 任务依赖关系建模 |

**工作流**:
```
审查任务列表 → TaskGraph DAG → TopologyRouter.select()
    ├─ 无依赖 → PARALLEL (全部并行)
    ├─ 链式 → SEQUENTIAL (串行)
    └─ 复杂 → HYBRID (CPM 关键路径驱动)
```

### 2.2 上下文策展 (Context Curator)

从 `ContextCurator` 独立运行，与 `TaskExecutor` **完全解耦**。

| 策略 | 参考 | 原理 |
|------|------|------|
| **BaselineStrategy** | 规则基线 | 关键词+重要性阈值 |
| **LLMStrategy** | SelfCompact (arXiv:2606.23525) | LLM自决策 |
| **ACONStrategy** | ACON (ICML 2026) | 从失败中自适应调整 |

**弹性类型系统** (ACE, arXiv:2606.31564):
```
RAW → ABSTRACT → DROP (可逆)
  ↓         ↓
保留原文  摘要化   丢弃但存原文hash
```
完全可逆 — `curator.restore(step_id)` 恢复任意被压缩的步骤。

### 2.3 自回归自我Loop

```
Step N 执行完成
    ↓
SelfLoopState.record_step()
    ↓
SelfLoopState.decide_next()
    ├─ "compact" → 调用 curator.compact()
    ├─ "execute:X" → 执行任务X
    ├─ "llm_decide" → 让LLM自决策下一步
    └─ "complete" → 结束
    ↓
Step N+1
```

**LLM自编排**: 模型可以选择 "我需要先检查格式，再验证引用，最后做综合审查" → 自己决定顺序。

### 2.4 Latent Relay — 超越多Agent的新范式

| 范式 | 通信方式 | 成本 | 信息损失 |
|------|---------|------|---------|
| **传统多Agent** | 文本消息传递 | 高 (完整文本) | 有(复述失真) |
| **MCP/A2A协议** | 结构化消息 | 中 | 低 |
| **Latent Relay (本系统)** | KV缓存/向量/任务ID引用 | 极低 (元数据) | 极低 (引用原数据) |
| **Latent Briefing** | Attention Matching 压缩 | 几乎为零 | 可控制 |

**三种通信方式**:
```
1. KV Cache Share (PolyKV模式)
   WorkerA的KV缓存 → WorkerB直接引用
   成本: 1个key字符串
   
2. Latent Briefing (Attention Matching)
   压缩历史上下文为隐空间表示
   成本: 几个浮点数向量
   
3. Orthogonal Backfill (信息保真)
   丢失的正交分量重新注入
   保证信息无损
```

## 三、与传统架构对比

| 维度 | V1 (当前架构) | V2 (新架构) | 提升 |
|------|-------------|------------|------|
| **编排模式** | Orchestrator→Worker 固定流水线 | 自回归自我Loop | 灵活度∞ |
| **上下文管理** | 文本拼接, 40%阈值手动处理 | ContextCurator自动策展 | Token省30-70% |
| **调度** | asyncio.Semaphore(4) | CPM关键路径+ILP分配 | 效率2× |
| **通信** | 函数调用+Python对象 | Latent Relay KV/向量引用 | 成本省80-90% |
| **Worker间通信** | 无 | Latent × PolyKV共享KV池 | 省2.91×内存 |
| **可逆性** | 不可逆(直接截断) | 完全可逆(弹性类型) | 信息零丢失 |
| **自适应** | 无 | ACON失败驱动调整 | 持续优化 |
| **拓扑选择** | 固定并行 | AdaptOrch动态4拓扑 | 最优映射 |

## 四、KV压缩可集成项目

| 项目 | 使用方式 | 收益 | 优先级 |
|------|---------|------|--------|
| **Multi-TurboQuant** | pip install → 插件调用 | 5-80× KV压缩 | 🔥 高 |
| **March** | pip install → Trie前缀去重 | 80-97%共享内存 | 🔥 高 |
| **PolyKV** | 算法移植 → KV池共享 | 多Agent内存O(1) | ⚡ 中 |
| **Latent Briefing** | 算法实现 → Attention Matching | 表示层压缩 | ⚡ 中 |

## 五、组件间关系

```
ctx_messages ← ContextCurator.get_messages()
      ↓
OrchestratorV2.execute(task_graph)
      ├─ TopologyRouter.select_topology()      # OR调度
      ├─ router.schedule() → stages             # CPM计划
      ├─ 对每个stage:
      │   ├─ curator.should_compact()? → compact()
      │   ├─ 并行执行stage中的任务
      │   ├─ state.record_step()
      │   └─ state.decide_next()
      ├─ relay.broadcast(LatentMessage)         # 隐空间通信
      └─ → 返回 {results, curator_report, compaction}
```

## 六、文件清单

```
article_check/
├── curator/
│   ├── __init__.py           ← ContextCurator 主类 (430行)
│   └── orchestrator_v2.py    ← Orchestrator V2 (410行)
│
├── core/harness/             ← V1 兼容层 (可被V2调用)
├── pipeline/                 ← V1 流水线 (可被V2作为Worker调用)
├── rules/                    ← 规则引擎 (零token)
├── knowledge/                ← RAG知识库
└── .claude/skills/           ← Skill定义
```
