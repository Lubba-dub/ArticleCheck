# 论文审查智能体设计与 PRD

## 0. 文档信息

- 文档名称：论文审查智能体设计与 PRD
- 项目名称：Article Check
- 文档版本：v1.0
- 文档定位：产品需求文档 + 系统设计文档 + 平台化落地说明
- 适用范围：
  - 独立 Web 部署
  - VSCode 插件工作台
  - 平台 WebDemo 托管
  - Dify 作为 AI 工作流与问答后端

## 1. 执行摘要

### 1.1 项目要解决的核心问题

当前高校论文送审、课程论文检查、毕业论文预审存在几个长期痛点：

1. 格式审核依赖人工逐项核对，效率低且一致性差。
2. 参考文献容易出现缺失、错引、DOI 缺失、正文引用不一致，甚至出现 AI 生成的“文献幻觉”。
3. 大多数“AI 论文助手”停留在泛化聊天层，不能输出可归档、可定位、可复核的正式审查报告。
4. 批量论文处理场景中，缺少面向教师、教务、平台方可运营的统一工作台。
5. 审查结果通常只有一段自然语言总结，缺乏证据链、问题定位、严重度分层与修订路径。

### 1.2 本项目的产品定位

Article Check 不是一个通用聊天机器人，而是一个围绕“论文提交前质量治理”的垂直智能体系统。它的核心目标是：

- 对学术论文执行批量化、结构化、可追踪的审查；
- 在格式规范、参考文献有效性、内容风险、审改建议之间形成统一证据链；
- 以正式报告、工作台、问题定位、问答解释四种可消费形态交付结果；
- 同时支持独立部署与平台接入，尤其适配 WebDemo 与 Dify 平台集成。

### 1.3 一句话定义

> 一个面向论文格式审查、参考文献核验、文献幻觉预警与正式审改报告生成的证据优先型论文审查智能体系统。

## 2. 背景与机会

### 2.1 业务背景

在毕业论文、课程论文、项目报告、学术预审等场景中，组织方真正需要的不是“能聊论文”的 AI，而是“能稳定发现问题、解释依据、输出正式报告、支持批量处理和平台部署”的系统。

这意味着产品必须同时满足四类约束：

1. **规则性约束**
   - 学校模板、期刊模板、章节结构、页边距、图表标题、参考文献规范等需要稳定、可重复地检查。

2. **事实性约束**
   - 文献条目必须能被外部元数据源交叉验证，避免“看起来像真的但实际不存在”的虚假引用。

3. **可消费性约束**
   - 审查结果不能只是模型输出文本，而必须变成可定位、可归档、可打印、可问答的报告对象。

4. **工程性约束**
   - 要适配 Web 页面、批量处理、Dify 平台、Docker 托管和项目方平台认证。

### 2.2 当前机会窗口

大模型使“内容性审查”成为可能，但实际落地中的决定性竞争优势不在于是否接入某个模型，而在于：

- 是否有足够稳定的文档结构解析能力；
- 是否能进行参考文献真实性验证；
- 是否将问题转换为 Evidence、Diagnostic、Report Fragment 等可操作对象；
- 是否能在批量处理、平台部署和正式报告上形成闭环。

因此，本项目的价值主线应从“AI 会不会审论文”转为“如何把论文审查系统产品化、平台化、证据化”。

## 3. 用户、角色与场景

### 3.1 核心角色

#### 3.1.1 学生 / 作者

目标：

- 在提交前快速发现格式错误和引用问题；
- 获得清晰的修改优先级；
- 能追溯到原文位置并快速修订。

典型诉求：

- 哪些问题最影响提交？
- 哪些引用可能是幻觉或不完整？
- 具体要改哪一页、哪一行、哪一段？

#### 3.1.2 导师 / 审阅教师

目标：

- 在有限时间内批量把握论文质量；
- 通过正式报告快速判断风险等级；
- 对问题有证据、有定位、有摘要，而不是长文本堆砌。

典型诉求：

- 哪些论文需要优先退回修改？
- 哪些是格式性问题，哪些是引用真实性问题？
- 是否能快速查看证据链和报告摘要？

#### 3.1.3 教务 / 学院管理员 / 平台方

目标：

- 统一部署、统一接入、统一管理；
- 批量导入和批量审查；
- 满足平台托管和权限体系要求。

典型诉求：

- 能否在平台上以 WebDemo 方式托管？
- 能否通过 Dify 平台统一调度 AI 能力？
- 是否支持批量任务和结构化结果输出？

### 3.2 核心使用场景

#### 场景 A：单篇论文预审

用户上传一篇论文，系统返回：

- 总体风险等级
- 格式问题列表
- 文献预警列表
- Evidence 明细
- 正式审改报告
- 报告问答入口

#### 场景 B：批量论文筛查

教师或管理员上传一个文件夹或多篇论文，系统输出：

- 每篇论文总体评分与风险等级
- 按严重度排序的问题数
- 适合优先复核的论文列表
- 可逐篇下钻查看报告详情

#### 场景 C：文献幻觉预警

系统从正文与参考文献区提取引用条目，执行 DOI、OpenAlex、Crossref 等多源核验，识别：

- DOI 不存在
- 题名与作者、年份不匹配
- 正文有引用但文末缺失
- 文末有条目但正文未使用
- 可能为 AI 编造的“似真文献”

#### 场景 D：平台型服务接入

项目方平台通过 Docker 托管本项目，通过 `auth.js` 做认证接入，通过 Dify 为智能体节点提供能力，本项目保留页面与报告系统，平台获得稳定可运行的专业审查服务。

## 4. 需求重述与边界

### 4.1 必须覆盖的需求

结合当前项目状态与用户多轮确认，本项目必须覆盖以下一级能力：

1. 论文批量处理
2. 论文格式审查
3. 参考文献真实性核验
4. 文献幻觉预警
5. 内容性审查与建议生成
6. 统一证据记录与问题定位
7. 正式审改报告生成
8. Web 工作台与报告工作流
9. VSCode 工作台联动
10. Docker 平台部署
11. Dify AI 工作流接入

### 4.2 本期不做的事

为了保证产品聚焦，当前阶段明确不作为主目标的内容包括：

- 端到端自动改写整篇论文
- 替代人工进行最终学术评价或学位评定
- 做通用研究助手平台
- 做引用管理器或文献库管理器
- 在 Dify 中重建全部专业 UI

### 4.3 为什么不应泛化为“通用 Agent”

因为论文审查的关键价值不在开放式对话，而在：

- 规则性
- 证据链
- 报告规范
- 定位能力
- 可批量处理
- 可归档交付

因此，系统应该以“任务图 + 结构化结果 + 正式报告”为核心，而不是以“自由对话”作为主入口。

## 5. 调研结论

### 5.1 文档结构解析

GROBID 长期专注于将 PDF 学术文献解析为结构化 TEI/XML，支持参考文献抽取、正文结构抽取、引用上下文识别与 PDF 坐标信息输出，这说明“将论文先变成结构化对象，再做下游审查”是成熟路线，而不是临时技巧。[GROBID Documentation](https://grobid.readthedocs.io/en/latest/) [How GROBID works](https://grobid.readthedocs.io/en/latest/Principles/) [GROBID Introduction](https://github.com/grobidOrg/grobid/blob/master/doc/Introduction.md)

对本项目的直接启发：

- PDF 不应只做纯文本 OCR，而应逐步收束为统一中间表示；
- Evidence 定位最终应支持 page / line / section / bbox 多层坐标；
- 对 LaTeX、Word、PDF 的处理应共享一套“统一审查中间层”。

### 5.2 参考文献真实性验证

Crossref 的 REST API 提供公开可检索的 DOI 元数据，OpenAlex 则支持通过 DOI、PMID、PMCID 等外部 ID 查询 works，并返回 `referenced_works`、`authorships`、`topics`、`open_access` 等更丰富的结构化字段。[Crossref community note on REST API availability](https://community.crossref.org/t/ticket-of-the-month-february-2026-if-google-can-t-find-it-is-my-doi-registered/15390) [Crossref REST API docs repo](https://github.com/CrossRef/rest-api-doc) [OpenAlex single work API](https://developers.openalex.org/api-reference/works/get-a-single-work) [OpenAlex works overview](https://developers.openalex.org/api-reference/works)

对本项目的直接启发：

- “文献幻觉预警”必须建立在外部权威元数据源上，而不是只看格式；
- DOI、标题、作者、年份应采用多字段匹配，不应只用单字段命中；
- 参考文献模块应同时输出“存在性、匹配度、可访问性、正文映射关系”四类信号。

### 5.3 智能体编排与平台化

Dify 的 Service API 明确区分 `Workflow API` 和 `Chat API`：前者适合无状态、结构化、固定流程任务，后者适合带会话的问答场景。[Dify API backend services](https://deepwiki.com/langgenius/dify-docs/11.3-contributing-to-documentation) [Dify API integration and access](https://deepwiki.com/langgenius/dify-docs/7-governance-and-community)

对本项目的直接启发：

- 内容审查与建议生成更适合挂到 Workflow；
- 报告问答更适合挂到 Chat；
- 专业 UI、文件处理、报告生成不应被搬进 Dify，而应由本项目后端保留。

### 5.4 产品工作台模式

虽然当前需求不是做代码审查工具，但问题治理产品的一般规律是一致的：高效工作台通常采用“摘要卡片 + 严重度分层 + 问题列表 + 证据定位 + 下钻详情”的模式，而不是线性长文。当前项目 Web 工作台已经朝这个方向收束，这是正确的。

对本项目的直接启发：

- 报告必须兼容“正式文档视图”和“工作台视图”；
- 问题对象应支持跳转、过滤、聚类、打印、问答；
- 问题与证据应成为系统中的一级对象，而不是报告中的附带文本。

## 6. 产品目标

### 6.1 北极星目标

让论文作者、导师和平台管理员能够在同一套系统中，以可批量、可解释、可定位、可归档的方式完成论文质量审查。

### 6.2 本期核心目标

1. 建立统一论文审查报告对象 `article_check.ai_review.v1`
2. 建立格式审查 + 文献核验 + 内容审查三条主链
3. 建立 Evidence-first 的工作台和正式报告
4. 建立单篇与批量两种主操作路径
5. 建立 Dify 可接入的 AI 智能体工作流
6. 建立平台可托管的 WebDemo 部署方案

### 6.3 成功标准

- 单篇论文审查能稳定输出正式报告和结构化结果
- 批量审查能对多篇论文给出统一汇总
- 文献幻觉预警能发现 DOI 缺失、元数据不一致、引用映射异常
- Web 工作台支持 Evidence 详情与报告片段联动
- Dify 可作为内容审查和报告问答的 AI 后端
- Docker 可完成平台托管部署

## 7. 产品信息架构

### 7.1 一级对象

系统内部最重要的不是“页面”，而是以下对象：

1. `PaperTask`
   - 单篇论文任务
2. `PipelineResult`
   - 单篇审查结果
3. `Finding`
   - 问题项
4. `EvidenceRecord`
   - 证据项
5. `AdviceReport`
   - 修订优先级报告
6. `FormalReport`
   - 正式审改报告
7. `WorkflowGraph`
   - 智能体执行图

### 7.2 统一输出对象

当前系统已经收束到统一报告格式 `article_check.ai_review.v1`，在 [build_review_payload](file:///e:/cocoon/projects/article_check/article_check/runtime.py#L374-L453) 中构建。该对象包含：

- `meta`
- `summary`
- `sections`
- `findings`
- `evidence_records`
- `advice_report`
- `formal_report`
- `workflow`
- `errors`

这一步极其关键，因为它决定了 CLI、Web、VSCode、平台 API 可以围绕同一份数据工作。

## 8. 功能设计

### 8.1 论文接入与预处理

#### 输入格式

- `.tex`
- `.ltx`
- `.doc`
- `.docx`
- `.pdf`

#### 核心动作

- 识别文件类型
- 建立任务 ID
- 提取标题、章节、正文、参考文献区
- 构建统一上下文

#### 设计要求

- 多格式输入应尽量收敛为统一的中间表示；
- 原始文件路径需保留，供报告回跳与 Evidence 溯源；
- 批量模式下要支持队列去重与并发控制。

### 8.2 格式审查

#### 审查维度

- 题名页与封面
- 字体、字号、行距
- 标题层级
- 页边距、页眉页脚
- 图表标题与编号
- 章节缺失或顺序异常
- 模板一致性

#### 输出要求

每个格式问题至少要输出：

- `category = format`
- `severity`
- `description`
- `suggestion`
- `location`

#### 产品要求

- 对用户应显示为“格式预警与定位”；
- 对 VSCode 应能映射为 Problems / Diagnostics；
- 对报告应能映射到正式审改报告章节。

### 8.3 参考文献核验与文献幻觉预警

#### 核心能力

- 引用条目提取
- 正文引用与文末参考文献映射
- DOI、URL、PMID、OpenAlex 外部检索
- 题名、作者、年份一致性比对
- 未匹配、疑似伪造、缺字段、失效链接标记

#### 输出问题类型建议

- `reference_missing`
- `doi_missing`
- `doi_not_resolvable`
- `metadata_mismatch`
- `citation_unmapped`
- `reference_unused`
- `hallucination_suspected`

#### 文献幻觉预警判定逻辑

建议采用分层判定，而不是二元真假：

1. **存在性失败**
   - DOI 无法解析
   - 标题/作者/年份完全无匹配

2. **一致性失败**
   - DOI 存在，但元数据与论文中的条目不匹配

3. **映射性失败**
   - 正文引用与文末条目不能建立关系

4. **可访问性失败**
   - 有标识但落地链接不可达或元数据缺失

这四类信号组合后再输出风险等级，比简单“真/假文献”更适合产品落地。

### 8.4 内容审查

#### 当前定位

内容审查不是为了替代导师，而是补充“结构是否完整、论证是否清晰、方法和结果表述是否合理”的智能建议。

#### 建议维度

- 研究问题是否清晰
- 摘要是否覆盖问题、方法、结果、贡献
- 相关工作是否充分
- 方法部分是否缺关键步骤
- 实验/结果是否支撑结论
- 语言与结构是否冗余或跳跃

#### 输出要求

- 必须为结构化 JSON
- 必须按 section 输出问题
- 必须有 severity 与 suggestion
- 必须能与现有 findings / advice report 融合

### 8.5 审改建议报告

#### 核心目标

从几十条问题中提炼“先改什么”的路线图。

#### 输出结构

- `priority`
- `title`
- `actions[]`

#### 使用方式

- 作者优先查看
- 导师快速复核
- 报告问答的摘要输入

### 8.6 正式审改报告

#### 目标

输出可提交、可打印、可归档、可展示的正式报告。

#### 当前形态

系统已支持：

- Markdown
- HTML
- JSON

并已做成送审风格页面、打印版、签批区和报告工作台联动。

#### 理想章节

1. 报告封面
2. 执行摘要
3. 风险矩阵
4. 格式问题详表
5. 参考文献问题详表
6. 内容审查摘要
7. Evidence 记录区
8. 修订优先级建议
9. 工作流与审查说明
10. 签批与归档区

### 8.7 报告问答

#### 目标

允许作者或导师基于已有结构化报告继续提问。

#### 典型问题

- 我应该先修哪些问题？
- 哪些是影响提交的硬伤？
- 哪些参考文献最可疑？
- 哪些问题只是规范性小问题？

#### 设计要求

- 必须严格基于 `report_payload`
- 不得脱离报告自由发挥
- 回答要偏修改动作，不做泛化空话

### 8.8 批量审查工作台

#### 目标

让管理员或导师能一次处理多篇论文，并迅速识别高风险论文。

#### 关键能力

- 批量上传或批量路径输入
- 并发执行
- 每篇论文产出独立结果
- 汇总评分、风险等级、问题数
- 支持逐篇下钻

#### 关键页面组件

- 任务列表
- 风险排序
- 单篇报告切换
- 批量汇总指标

## 9. 页面与交互设计

### 9.1 总体页面原则

产品层不应以“聊天”作为主视觉，而应以“报告与治理工作台”作为主视觉。

因此页面设计遵循：

1. 摘要优先
2. 风险分层
3. 证据优先
4. 问题可跳转
5. 报告与工作台双视图统一

### 9.2 Web 工作台

当前 Web 主页面 [ReviewPage](file:///e:/cocoon/projects/article_check/article_check/web/frontend/src/pages/ReviewPage.jsx) 已形成以下结构：

- 上传区
- 单篇/流式批量触发
- 结果集合
- 统一报告工作台
- Evidence 详情联动
- 原文片段预览
- 报告问答

### 9.3 报告工作台

当前报告主视图 [ReviewStudio](file:///e:/cocoon/projects/article_check/article_check/web/frontend/src/components/ReviewStudio.jsx) 已具备以下结构：

- Report Hero
- 执行摘要卡片
- 格式预警
- 文献预警
- Evidence 记录
- 工作流状态
- 打印与正式报告入口
- 统一详情面板

### 9.4 VSCode 工作台

VSCode 侧应继续强调三类对象：

- 工作流节点
- Evidence 列表
- Problems / Diagnostics

这样编辑器就不仅是“看报告”，而是“边看问题边回到原文修复”。

## 10. 智能体系统设计

### 10.1 设计原则

1. 规则优先，模型补充
2. 证据优先，结论其次
3. 工作流可追踪
4. 输出统一结构化对象
5. UI 与运行时解耦

### 10.2 为什么采用多阶段智能体

论文审查不是一个单轮 prompt 可以稳定完成的任务，因为它同时包含：

- 确定性规则检查
- 结构性解析
- 外部事实检索
- 模型审查
- 报告生成

因此正确做法是多 worker / 多 stage 串联，而不是把原文整篇扔给模型。

### 10.3 推荐的执行图

```text
ingest
  -> normalize
  -> format_check
  -> reference_extract
  -> reference_validate
  -> content_review
  -> evidence_aggregate
  -> advice_generate
  -> formal_report_generate
  -> publish_artifacts
```

### 10.4 Worker 设计

#### `ingest`

职责：

- 读取文件
- 识别格式
- 建立任务元信息

#### `normalize`

职责：

- 将 Word / LaTeX / PDF 收束为统一中间表示
- 提取章节、段落、引用、候选位置

#### `format_check`

职责：

- 执行模板规则
- 输出格式类 findings

#### `reference_extract`

职责：

- 提取参考文献条目
- 提取正文引用 callout

#### `reference_validate`

职责：

- Crossref / OpenAlex / 其他源匹配
- 生成文献幻觉预警

#### `content_review`

职责：

- 以结构化 prompt 调用 AI
- 输出内容性 findings

#### `evidence_aggregate`

职责：

- 将 findings 转换成 EvidenceRecord
- 构建 severity、location、claim、suggestion

#### `advice_generate`

职责：

- 聚合高优先级修复动作

#### `formal_report_generate`

职责：

- 生成 Markdown / HTML / JSON 正式报告

### 10.5 Dify 作为智能体后端的最佳位置

建议采用“双 Dify 应用”模式：

1. `Review Workflow`
   - 输入论文上下文、格式结果、参考文献结果
   - 输出结构化内容审查与修订建议

2. `Report Chat`
   - 输入统一报告对象
   - 输出针对报告的问答

这样做可以兼顾：

- 工作流可控
- 会话问答自然
- 后端职责清晰

## 11. 数据与证据模型

### 11.1 `Finding`

产品上所有问题项都应归一为统一结构：

- `category`
- `severity`
- `type`
- `description`
- `suggestion`
- `location`

### 11.2 `EvidenceRecord`

Evidence 是系统的核心对象，应具备：

- `evidence_id`
- `stage`
- `source_type`
- `claim`
- `severity`
- `location`
- `suggestion`
- `raw_payload`

当前系统已在 [runtime.py](file:///e:/cocoon/projects/article_check/article_check/runtime.py#L374-L453) 与 [models.py](file:///e:/cocoon/projects/article_check/article_check/pipeline/models.py#L32-L54) 上形成这条主线。

### 11.3 `location`

位置对象建议逐步标准化为：

- `line`
- `column`
- `page`
- `section`
- `paragraph_id`
- `bbox`（后续）

### 11.4 为什么要把问题映射成 Evidence / Diagnostic

因为只有这样，系统才能支持：

- Web 报告片段跳转
- 原文片段回溯
- VSCode Problems 面板
- 正式报告中的证据区
- 批量工作台的问题聚合

## 12. 部署设计

### 12.1 独立部署

当前推荐形态：

- `nginx`
- `FastAPI`
- `frontend dist`
- `reports/`
- `uploads/`

### 12.2 平台部署

当前已完成的适配主线：

- 当前页面作为 WebDemo 托管
- 后端代理 Dify API
- 平台 `auth.js` 脚本可注入
- Docker 可作为交付方式

### 12.3 平台职责边界

平台方负责：

- 认证入口
- 托管环境
- 域名与网关
- Dify 应用配置

本项目负责：

- 页面和专业工作台
- 论文文件处理
- 格式与文献规则审查
- Evidence 与报告生成
- Dify 调用编排

## 13. 非功能需求

### 13.1 性能

- 单篇论文预审：目标在可接受时间内返回报告
- 批量处理：支持并发数可配置
- 报告页面：首屏先展示摘要，再异步载入细节

### 13.2 可解释性

- 每条关键结论必须尽量附带 Evidence
- 每条 Evidence 必须尽量附带定位
- 问答必须严格基于报告，而非任意生成

### 13.3 可维护性

- 规则引擎与 AI 节点解耦
- 统一报告对象保持稳定
- 页面与后端契约明确

### 13.4 可部署性

- 支持 Docker
- 支持 WebDemo 模式
- 支持 Dify 后端代理
- 支持环境变量切换 provider

## 14. 指标体系

### 14.1 业务指标

- 单篇审查完成率
- 批量审查成功率
- 正式报告生成成功率
- 高风险论文识别命中率
- 用户对“问题优先级建议”的采纳率

### 14.2 质量指标

- 格式问题定位准确率
- 参考文献匹配成功率
- DOI 可解析率
- 文献幻觉误报率 / 漏报率
- 报告问答事实一致性

### 14.3 工程指标

- API 成功率
- 批量任务平均耗时
- 页面关键交互耗时
- Dify 节点失败率

## 15. 路线图建议

### Phase 1：可用主线

- 单篇审查
- 批量审查
- 统一报告
- Web 工作台
- Dify 问答

### Phase 2：证据强化

- 更稳健的 PDF 坐标
- 更细粒度的原文定位
- 更强的文献幻觉评分模型

### Phase 3：平台化运营

- 平台租户化接入
- 任务队列与批处理调度
- 教师/管理员汇总看板
- 审查策略配置化

### Phase 4：领域深化

- 不同学校模板包
- 不同期刊模板包
- 相关工作覆盖度分析
- 可选自动修订建议草稿

## 16. 主要风险与应对

### 风险 1：PDF / Word / LaTeX 结构不一致

应对：

- 统一中间层
- 分格式解析器
- 先保证位置粗粒度可用，再逐步细化

### 风险 2：文献幻觉判定误伤

应对：

- 采用分层风险而非真假二元判断
- 保留原始匹配依据
- 允许人工复核

### 风险 3：模型输出不稳定

应对：

- 强制结构化 JSON
- 增加 normalize / repair 层
- 将模型输出限制在内容审查与建议层

### 风险 4：Dify 编排和本地工作流耦合过深

应对：

- 后端持有主契约
- Dify 只负责 AI 节点
- 不把报告 UI 迁移进 Dify

### 风险 5：平台部署环境不稳定

应对：

- Docker 化
- 健康检查
- 环境变量模板化
- `auth.js` 作为独立替换层

## 17. 结论

本项目最正确的方向，不是把“论文助手”做成一个会聊天的通用 Agent，而是把它建设为一个：

- 面向论文提交前质量治理的垂直系统
- 以格式审查、文献核验、文献幻觉预警为确定性基础
- 以 Dify 提供内容审查和报告问答等 AI 能力
- 以 Evidence 和正式报告为最终交付对象
- 以 Web 工作台、VSCode 工作台和平台部署为交付形态

如果按这个方向持续推进，Article Check 的核心壁垒将不是“换了哪个模型”，而是：

- 统一中间表示
- 结构化证据链
- 审查对象模型
- 论文场景专用工作流
- 平台级可运营交付

这也是本项目从研究型原型走向产品化系统的关键收束路径。

## 18. 参考资料

### 外部调研

- GROBID 官方文档：[https://grobid.readthedocs.io/en/latest/](https://grobid.readthedocs.io/en/latest/)
- GROBID 原理说明：[https://grobid.readthedocs.io/en/latest/Principles/](https://grobid.readthedocs.io/en/latest/Principles/)
- GROBID 项目介绍：[https://github.com/grobidOrg/grobid/blob/master/doc/Introduction.md](https://github.com/grobidOrg/grobid/blob/master/doc/Introduction.md)
- Crossref REST API 文档仓库：[https://github.com/CrossRef/rest-api-doc](https://github.com/CrossRef/rest-api-doc)
- Crossref 关于 DOI 与 REST API 的说明：[https://community.crossref.org/t/ticket-of-the-month-february-2026-if-google-can-t-find-it-is-my-doi-registered/15390](https://community.crossref.org/t/ticket-of-the-month-february-2026-if-google-can-t-find-it-is-my-doi-registered/15390)
- OpenAlex Works API：[https://developers.openalex.org/api-reference/works](https://developers.openalex.org/api-reference/works)
- OpenAlex 单篇 Work API：[https://developers.openalex.org/api-reference/works/get-a-single-work](https://developers.openalex.org/api-reference/works/get-a-single-work)
- Dify Service API 总览：[https://deepwiki.com/langgenius/dify-docs/11.3-contributing-to-documentation](https://deepwiki.com/langgenius/dify-docs/11.3-contributing-to-documentation)
- Dify API 分类与接入说明：[https://deepwiki.com/langgenius/dify-docs/7-governance-and-community](https://deepwiki.com/langgenius/dify-docs/7-governance-and-community)

### 项目内文档

- [README.md](file:///e:/cocoon/projects/article_check/README.md)
- [deployment-architecture.md](file:///e:/cocoon/projects/article_check/docs/deployment-architecture.md)
- [dify-workflow-text-architecture.md](file:///e:/cocoon/projects/article_check/ArticleCheck_platform/docs/dify-workflow-text-architecture.md)
