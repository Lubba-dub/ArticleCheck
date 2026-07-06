# Article Check — 论文审查与修正智能体

## 项目简介
基于 DeepSeek API + 规则引擎的学术论文审查与修正系统。支持 LaTeX/Word 格式，
单篇或批量并行审查，出具结构化报告，并支持交互式修正。

## Skill 系统
本项目配置了以下 Claude Code Skills，可通过自然语言调用：

| Skill | 功能 | 调用方式 |
|-------|------|---------|
| `paper-review` | 全方位论文审稿 | "审这篇论文" |
| `paper-fix` | 交互式自动修正格式 | "改成IEEE格式" |
| `format-check` | 快速格式检查（零 token） | "查格式" |
| `reference-verify` | 文献引用验证 | "检查引用" |
| `chat-moderator` | 自然语言对话交互（主入口） | 直接说话 |

## 知识库
`knowledge/` 目录包含可供参考的格式规则和引用规范：
- `knowledge/formats/` — LaTeX/Word 规则、模板指南、常见错误
- `knowledge/references/` — 引用格式、DOI 验证
- `knowledge/workflows/` — 工作流模板

## 工作方式
1. 用户通过自然语言输入需求
2. chat-moderator 识别意图并路由到对应 skill
3. skill 调用 `article-check` CLI 执行具体审查/修正
4. 结果以对话形式呈现给用户

## 常用命令
```bash
python run.py                  # 交互式菜单
python run.py paper.tex        # 快捷审查
python -m article-check chat   # 对话模式
```
