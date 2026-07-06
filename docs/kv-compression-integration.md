# 🔬 并行KV压缩开源项目评估报告

> 评估日期: 2026-07-06 | 评估目标: 能否并入 article-check 系统

---

## 项目评估矩阵

| 项目 | 可并入性 | 集成难度 | 预期收益 | 备注 |
|------|---------|---------|---------|------|
| **PolyKV** | ⚠️ 部分可 | 中 | 多Agent共享KV池省2.91×内存 | 需要改造接口 |
| **Multi-TurboQuant** | ✅ 可 | 低 | 5-80×压缩, agents预设 | 插件式API, 直接pip |
| **March** | ✅ 可 | 低 | 80-97%前缀去重 | Trie结构, pip安装 |
| **Latent Briefing** | ✅ 可直接借鉴 | 低 | 表示层共享, Task-Guided Query | 纯算法, 无需依赖 |
| **STAR-KV** | ❌ 过重 | 高 | 75%压缩 | 需要Triton CUDA内核 |
| **Tangram** | ❌ vLLM绑定 | 高 | 只能用于vLLM部署 | 架构不匹配 |

## 推荐集成策略

### Phase 1: Multi-TurboQuant (立即)
```bash
pip install multi-turboquant
```
通过插件API直接在Context Curator中调用, 5行代码集成。

### Phase 2: March (1天)
```bash
pip install march-kv
```
Trie前缀去重, 适合批量审查场景——多篇论文共享相同的前缀(system prompt)。

### Phase 3: Latent Briefing 算法移植 (2天)
不引入外部依赖, 直接实现Attention Matching算法：
- 任务引导的Query向量构建
- 共享Token Mask聚合
- MAD自适应阈值
