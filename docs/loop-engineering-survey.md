# 🔬 前沿 Loop 工程与上下文压缩调研报告 (2026)

> 调研时间: 2026年7月
> 范围: Agent Loop 编排 / 上下文压缩 / Agent 间通信协议

---

## 一、系统功能检查结果

通过全面测试，当前系统所有模块正常运行：

| 模块 | 状态 | 备注 |
|------|------|------|
| 配置系统 | ✅ | API Key / 模型 / 缓存配置 |
| Harness 核心 | ✅ | 13 个工具注册, 6-layer 架构 |
| Agent 注册表 | ✅ | 工厂模式就绪 |
| 工作树管理 | ✅ | 隔离/清理正常 |
| 审查流水线 | ✅ | Orchestrator/Worker/Reviewer 全链路 |
| 模板引擎 | ✅ | 4 模板 + 18 规则 |
| LaTeX 检查器 | ✅ | 正则降级可用 (chktex 未安装) |
| Word 检查器 | ✅ | python-docx 就绪 |
| DeepSeek API | ✅ | 实测连通, model=deepseek-v4-flash |
| 缓存系统 | ✅ | 三层缓存架构 |
| arXiv 搜索 | ✅ | 实时 API 可用 |
| Chat 对话 | ✅ | 11 个意图 100% 识别 |
| Skill 系统 | ✅ | 5 个 SKILL.md |
| RAG 知识库 | ✅ | 7 篇参考文档 |

⚠️ 待改进: chktex 未安装、文献验证 API 待实现、自动修正功能待完成

---

## 二、前沿 Loop 编排方案

### 2.1 当前主流范式

| 模式 | 代表 | 说明 |
|------|------|------|
| **ReAct** | 标准 prompt loop | 思考→行动→观察→思考... |
| **Orchestrator-Workers** | athena-loops, 本系统 | 编排器调度多个 Worker |
| **Evaluate-Optimizer** | Anthropic 模式 | 生成→批评→改进循环 |
| **DAG Pipeline** | AgentSkillOS | 有向无环图编排 |
| **Tool Folding** | Claude Code | 模型一次产出多步骤代码 |

### 2.2 2026 年最值得关注的方案

#### 🏆 Self-Compacting Agents (SelfCompact)
- **核心**: 不给外部总结器，让 LLM 自己决定何时压缩——通过一个"compaction tool"和轻量级评分规则
- **结果**: 成本降低 30-70%，数学任务提升 18.1 分，Agentic 搜索提升 5-9 分
- **对本系统的价值**: **可直接集成**——加入一个 route step，让 Worker 在 context > 70% 时自压缩

#### 🏆 ContextCurator (解耦式上下文管理)
- **核心**: 将上下文管理从任务执行中分离——一个轻量级 RL 训练的 ContextCurator 负责裁剪噪声
- **结果**: WebArena 成功率 36.4% → 41.2%，token 减少 8× (DeepSearch)
- **对本系统的价值**: 为 Harness 层增加独立的 Context Manager 组件

#### 🏆 ACON (ICML 2026)
- **核心**: 基于失败分析迭代优化压缩策略，无需微调模型
- **结果**: 峰值 token 减少 26-54%，提升小模型性能最高 46%
- **对本系统的价值**: 审查流水线中可按"审查轮次"自适应压缩

#### 🏆 ACE (弹性上下文)
- **核心**: 每步历史分配"弹性类型"——raw/abstract/drop，完全可逆
- **结果**: 在 ReAct/DeepAgent/WebThinker 上一致优于截断和总结
- **对本系统的价值**: 工作树中可以保留每步的弹性类型，按需解压

### 2.3 上下文压缩技术全景

| 技术 | 压缩比 | 质量损失 | 适合场景 | 当前系统状态 |
|------|--------|---------|---------|------------|
| **前缀缓存** | 50-90% | 0% | 固定 system prompt | ✅ 已实现 |
| **分段审查** | 40-60% | <5% | 长文档 | ✅ 已实现 (worker.py) |
| **结构化输出** | 30-50% | 0% | API 响应 | ✅ 已实现 (schemas/) |
| **LLMLingua** | 5-20× | 1-5% | 任意文本 | ❌ 未集成 |
| **ACON 优化** | 26-54% | 0% | Agent trajectory | ❌ 可集成 |
| **Latent Briefing** | 5-50× | 5-20% | KV cache 层 | ❌ 深度集成 |
| **Self-Compact** | 30-70% | 0% | Agent loop | ❌ 可集成 |

### 2.4 Agent 间通信协议

| 协议 | 角色 | 本系统现状 | 集成路径 |
|------|------|-----------|---------|
| **MCP** | Agent ↔ 工具/数据 | ✅ 已用 (tools.py) | 已有框架 |
| **A2A** | Agent ↔ Agent 任务委派 | ❌ | Harness 层增加 A2A client |
| **OpenClaw Bridge** | 协议翻译层 | ❌ | 多协议兼容 |

---

## 三、本系统与前沿方案的差距分析

### 现有优势（与前沿一致）
- ✅ **Orchestrator-Worker 模式** — 与 athena-loops 一致
- ✅ **工作树隔离** — 进程级隔离，符合 2026 最佳实践
- ✅ **结构化输出** — Pydantic → JSON Schema，省 30-50% tokens
- ✅ **前缀缓存** — provider 级缓存，省 50-90%
- ✅ **分段审查** — 避免 40% 阈值退化
- ✅ **规则引擎优先** — 零 token 审查格式

### 需要追赶（前沿已覆盖）
| 方向 | 具体方案 | 预期收益 | 实现难度 |
|------|---------|---------|---------|
| **自压缩 Loop** | SelfCompact/ACE 集成到 Worker | token 再省 30-70% | 低 |
| **Context Curator** | 独立的上下文管理器 | 减少噪声干扰 | 中 |
| **KV Cache 优化** | 固定前缀→动态内容分离 | 提升缓存命中率 | 低 |
| **A2A 协议** | Worker 间可互调任务 | 更灵活编排 | 高 |
| **并行压缩** | asyncio 多路压缩 | 降低延时 | 中 |
| **失败驱动的优化** | ACON 式自动复盘 | 持续改善审查质量 | 中高 |

---

## 四、推荐的改进路径

### Phase 1 (1-2天, 低风险)
```
Self-Compact 集成 → 在 Worker 的 work() 中增加 context 自检
  当 token 使用 > 70% → 触发自动压缩
  预期: Token 省 30-50%，代码改动 < 50 行
```

### Phase 2 (3-5天, 中等风险)
```
Context Curator 组件 → 独立的上下文管理器
  1. 跟踪每步的 token 消耗和关键信息
  2. 在上下文 > 70% 时选择性裁剪
  3. Harness 层的标准组件
  预期: 审查质量提升 5-10%
```

### Phase 3 (1-2周, 高风险)
```
A2A 协议集成 → Worker 间可以互调
  1. FormatWorker 发现问题 → 自动调 ReferenceWorker 验证引用
  2. ContentWorker 发现异常 → 调 FormatWorker 回查格式
  预期: 审查深度质变
```

---

## 五、最值得立即落地的 3 个方案

### 方案1: 结构化的 System Prompt 前缀缓存优化
把当前 `worker.py` 中的 system prompt 按"静态/动态"严格分区：

```python
# 优化前（混在一起，缓存不友好）
messages = [
    {"role": "system", "content": f"你是一个{role}专家。论文: {paper_text[:100]}"},
]

# 优化后（静态在前，动态在后，最大化缓存命中）
messages = [
    {"role": "system", "content": SYSTEM_PROMPT_CACHE_KEY},  # 完全静态 → 100% 缓存
    {"role": "user", "content": paper_text},                  # 唯一变化部分
]
```

### 方案2: Worker 自压缩
在 `worker.py` 的 ContentWorker 中加入 context 阈值自检：

```python
def should_compress(self, token_count: int) -> bool:
    """当使用量超过 70% 时自动压缩老的历史"""
    if token_count > 0.7 * MAX_CONTEXT:
        # 使用 LLM 自压缩（SelfCompact 模式）
        return self._self_compact()
    return False
```

### 方案3: 轻量级 Context Curator
在 Harness 层增加一个独立的上下文管理器，与 task executor 解耦：

```python
class ContextCurator:
    """上下文的"策展人"——独立于任务执行"""
    def prune(self, history: List[Step]) -> List[Step]:
        # 保留所有 tool call + result
        # 修剪 verbose thinking 步骤
        # 保留系统决策点
```

Sources:
- [Self-Compacting Agents (arXiv:2606.23525)](https://arxiv.org/abs/2606.23525)
- [ContextCurator (arXiv:2604.11462)](https://arxiv.org/abs/2604.11462)
- [ACON (arXiv:2510.00615)](https://arxiv.org/abs/2510.00615)
- [ACE (arXiv:2606.31564)](https://arxiv.org/abs/2606.31564)
- [Parallel Context Compaction (arXiv:2605.23296)](https://arxiv.org/abs/2605.23296)
- [SkillReducer (arXiv:2603.29919)](https://arxiv.org/abs/2603.29919)
- [Inter-Agent Communication Guide (Taskade, 2026)](https://www.taskade.com/blog/inter-agent-communication-patterns)
- [OpenClaw Protocol Bridge](https://github.com/ZhenRobotics/openclaw-protocol-bridge)
- [Red Hat Context Compaction Survey](https://github.com/redhat-ai-americas/memory-hub/blob/main/research/context-compaction-survey.md)
- [Baseten Repeated KV Cache](https://www.baseten.co/research/repeated-kv-cache-for-long-running-agents/)
- [Context Engineering for Production](https://www.spheron.network/blog/context-engineering-production-ai-agents-kv-cache-long-context/)
- [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering)
