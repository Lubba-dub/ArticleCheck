# ArticleCheck Dify 工作流文本架构设计

## 1. 设计目标

当前项目不建议把全部业务逻辑直接搬进 Dify，而建议采用“轻量化运营”的拆分方式：

- WebDemo 页面继续由 `Article Check` 承载
- 文件上传、格式检查、参考文献核验、报告生成继续留在本项目后端
- Dify 负责 AI 强相关节点：
  - 内容审查
  - 审改建议生成
  - 报告问答

这样做的好处是：

- 迁移成本低
- 平台接入简单
- Dify 线上编排更轻
- 当前 Web 端和报告能力不需要推倒重来

## 2. 推荐拆分

建议在线上 Dify 平台中至少准备两个应用：

### 2.1 Workflow 应用

名称建议：

`ArticleCheck_Review_Workflow`

作用：

- 接收后端整理后的论文上下文
- 输出结构化审查结果
- 重点覆盖内容审查和建议生成

适配场景：

- 后端 `/api/review`
- 后端批量审查中的 AI 内容节点

### 2.2 Chat 应用

名称建议：

`ArticleCheck_Report_Chat`

作用：

- 基于结构化报告做问答
- 输出面向作者或导师的修改建议

适配场景：

- 后端 `/api/report/dialogue`

## 3. 轻量化工作流主线

### 3.1 当前系统真实分工

本项目后端负责：

1. 接收论文文件
2. 提取文本与基础结构
3. 执行格式规则检查
4. 执行参考文献提取与交叉核验
5. 拼装统一审查上下文
6. 调用 Dify
7. 生成结构化审查报告与正式报告

Dify 负责：

1. 根据论文片段做内容审查
2. 输出结构化问题列表
3. 生成修订建议摘要
4. 基于报告继续问答

### 3.2 这样拆的原因

因为格式检查、参考文献核验、报告渲染、Evidence 联动，本质上都更适合留在本项目：

- 这些逻辑确定性更强
- 与文件系统和报告落盘绑定较深
- 若完全迁到 Dify，工作流会变重且维护成本更高

## 4. Workflow 文本架构

下面给出适合在 Dify 上线平台中直接手工编排的工作流文本设计。

### 4.1 Workflow 名称

`ArticleCheck_Review_Workflow`

### 4.2 App 类型

`Workflow`

### 4.3 输入变量

- `paper_title`
  - 论文标题
- `paper_excerpt`
  - 后端切好的论文核心文本片段
- `format_findings_json`
  - 格式检查结果 JSON 字符串
- `reference_findings_json`
  - 参考文献检查结果 JSON 字符串
- `review_goal`
  - 当前审查目标，如“本科论文送审前复核”
- `template_name`
  - 模板名称，可为空

### 4.4 节点设计

#### 节点 1：Start

输入上述变量。

#### 节点 2：Template / Prompt Assemble

将输入变量整理为统一提示词上下文：

- 论文标题
- 审查目标
- 模板信息
- 关键文本片段
- 已知格式问题
- 已知参考文献问题

输出变量建议：

- `review_context`

#### 节点 3：LLM - Content Review

角色：

你是学术论文审查专家，必须基于输入上下文输出结构化 JSON，只关注：

- 逻辑性
- 清晰性
- 完整性
- 方法合理性
- 结果表达

输出 JSON 结构建议：

```json
{
  "score": 0.0,
  "summary": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "issues": [
    {
      "section": "string",
      "type": "logic|clarity|completeness|methodology|result",
      "severity": "minor|major|critical",
      "description": "string",
      "suggestion": "string"
    }
  ]
}
```

#### 节点 4：Code / JSON Normalize

作用：

- 校验 LLM 返回结构
- 修补空字段
- 保证输出是合法 JSON

输出变量建议：

- `normalized_review_json`

#### 节点 5：LLM - Revision Priorities

输入：

- `normalized_review_json`
- `format_findings_json`
- `reference_findings_json`

输出：

- 三到五条优先级建议
- 每条建议包含：
  - `priority`
  - `title`
  - `actions`

输出变量建议：

- `priority_actions_json`

#### 节点 6：Output

Output 节点建议输出：

- `review_result`
  - `normalized_review_json`
- `priority_actions`
  - `priority_actions_json`
- `executive_summary`
  - 简短执行摘要

## 5. Chat 文本架构

### 5.1 Chat 名称

`ArticleCheck_Report_Chat`

### 5.2 App 类型

`Chat`

### 5.3 输入变量

- `report_payload`
  - 结构化审查报告 JSON 字符串
- `user_question`
  - 用户问题

### 5.4 System Prompt 建议

你是论文审改助手。必须严格基于 `report_payload` 回答，不得编造报告中不存在的事实。你的回答必须：

- 面向论文修改
- 优先指出高严重度问题
- 给出可执行建议
- 不重复无意义套话

### 5.5 Chat 输出风格

- 简洁
- 专业
- 聚焦修改动作

## 6. 后端映射关系

### 6.1 `/api/review`

后端流程建议映射为：

1. 本地格式检查
2. 本地参考文献核验
3. 聚合 `paper_excerpt + findings`
4. 调用 `ArticleCheck_Review_Workflow`
5. 合并为统一 `article_check.ai_review.v1`
6. 生成 HTML / Markdown / JSON 报告

### 6.2 `/api/report/dialogue`

后端流程建议映射为：

1. 传入 `report_payload`
2. 调用 `ArticleCheck_Report_Chat`
3. 返回回答文本

## 7. Dify 变量映射建议

如果你在线上 Dify 平台手工编排，建议固定以下命名，便于后端长期稳定接入：

### 7.1 Workflow 输入命名

- `paper_title`
- `paper_excerpt`
- `format_findings_json`
- `reference_findings_json`
- `review_goal`
- `template_name`

### 7.2 Workflow 输出命名

- `review_result`
- `priority_actions`
- `executive_summary`

### 7.3 Chat 输入命名

- `report_payload`
- `user_question`

## 8. 最小上线版本

如果你现在要尽快把线上 Dify 工作流搭起来，建议先做：

### 第一版

- 只上线 `ArticleCheck_Report_Chat`
- 用于报告问答
- 改造成本最低

### 第二版

- 再上线 `ArticleCheck_Review_Workflow`
- 用于内容审查与建议生成

### 第三版

- 再把 workflow 输出和后端报告生成做正式联调

## 9. 不建议在线上 Dify 一次性做的事

- 不建议把格式检查规则全部迁进 Dify
- 不建议把参考文献校验 API 编排全部迁进 Dify
- 不建议把正式报告页面渲染迁进 Dify

原因是：

- 这三类逻辑更偏“工程与规则系统”
- 留在本项目里更稳，也更好维护

## 10. 最终建议

面向项目方平台的最佳落地不是“Dify 托管全部系统”，而是：

- `Article Check WebDemo` 负责页面和报告
- `FastAPI` 负责业务编排和文件处理
- `Dify` 负责 AI 审查与问答节点

这就是当前项目最适合的平台化、轻量化、可运营的迁移方式。
