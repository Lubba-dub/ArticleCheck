# 交互式对话工作流

本文档定义了 chat-moderator 运行时的完整工作流路径。

## 核心工作流

### 审查流程 (Review Flow)

```
用户: 帮我看看这篇论文
  ↓
Agent: 询问论文路径
  ↓
用户: paper.tex
  ↓
Agent: 
  1. 检测文件类型 → latex
  2. 自动匹配模板 → IEEE Transactions (auto-detected)
  3. 执行格式检查
     ├─ article-check format paper.tex
     └─ article-check template check --template-name "IEEE" --paper paper.tex
  4. 展示结果
  5. 询问是否需要内容审查 (需 API key)
  ↓
用户: 需要
  ↓
Agent: 
  6. python -m article-check review paper.tex
  7. 读取报告
  8. 总结呈现
```

### 修正流程 (Fix Flow)

```
用户: 帮我改成 IEEE 格式
  ↓
Agent: 
  1. 运行 template auto-detect 确认当前模板
  2. 运行 template check 获取问题列表
  3. 展示问题列表，询问用户是否确认修改
  
  对每个需要修改的问题:
    ┌─────────────────────────────────────┐
    │ 📌 问题 #1: 文档类应为 IEEEtran     │
    │    当前: \documentclass{article}    │
    │    应为: \documentclass{IEEEtran}   │
    │    应用修改? (y/n/全部应用):        │
    └─────────────────────────────────────┘
  4. 逐项应用（或全部应用）
  5. 再次运行格式检查以验证
  6. 报告修改结果
```

### 批量处理流程 (Batch Flow)

```
用户: 把这个目录里的所有论文都审了
  ↓
Agent: 
  1. 扫描目录 → 找到 5 篇论文
  2. 列出论文列表
  3. 确认是否全部审查
  4. 显示并发数和预估 token 消耗
  5. 执行 python -m article-check batch <dir>
  6. 汇总结果表格
```

### 模板创建流程 (Template Create Flow)

```
用户: 我要创建一个新的期刊模板
  ↓
Agent:
  1. 询问期刊名称
  2. 询问格式要求（引导式）
     - 纸张大小: A4/Letter?
     - 字体: Times New Roman 12pt?
     - 参考文献格式: IEEE/APA/ACM?
     - 必需章节有哪些?
     - LaTeX 文档类是什么?
     - ...更多问题
  3. 生成 FormatTemplate 代码
  4. 写入 rules/template.py
  5. 注册模板
  6. 验证: 用已有论文测试模板
```

## 用户意图识别速查

| 用户输入关键词 | 意图 | 路由 |
|--------------|------|------|
| "看看", "审", "review", "审查", "检查论文" | 审查 | paper-review |
| "改", "修", "fix", "改正", "对齐", "修正", "调整" | 修复 | paper-fix |
| "格式", "format", "版面", "样式" | 格式检查 | format-check |
| "引用", "文献", "reference", "citation", "DOI" | 文献验证 | reference-verify |
| "批量", "batch", "目录", "多个", "文件夹", "所有论文" | 批量 | batch pipe |
| "模板", "template", "新建", "自定义", "注册" | 模板管理 | template |
| "配置", "设置", "config", "key", "API" | 配置 | config |
| "报告", "report", "上次", "结果" | 查看报告 | show report |
