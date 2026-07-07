# 常见格式错误与修复示例

## LaTeX 常见错误及修复

### 1. 文档类错误
```
错误: \documentclass{article}
正确: \documentclass[10pt,conference]{IEEEtran}
```
**影响严重度**: major
**修复**: 直接替换 documentclass 行

### 2. 使用 $$ 代替 \[...\]
```
错误: $$ E = mc^2 $$
正确: \[ E = mc^2 \]
```
**影响严重度**: minor (不影响编译，但 AMS 不推荐)
**修复**: 全局替换 `$$...$$` 为 `\[...\]`

### 3. 缺少必需的宏包
```
错误: 未加载 graphicx
正确: \usepackage{graphicx}
```
**影响严重度**: minor
**修复**: 在 documentclass 后添加 `\usepackage` 行

### 4. 字体设置不正确
```
错误: 无字体设置
正确: \usepackage{mathptmx}  % Times New Roman
```
**影响严重度**: minor
**修复**: 添加字体包

### 5. 缺少摘要
```
错误: 没有 abstract 环境
正确: \begin{abstract} ... \end{abstract}
```
**影响严重度**: critical
**修复**: 在 `\maketitle` 后添加 abstract 环境

### 6. 缺少关键词
```
错误: 没有 keywords
正确: \keywords{...} 或 \begin{keywords}...\end{keywords}
```
**影响严重度**: minor
**修复**: 在摘要后添加关键词

### 7. 参考文献数量不足
```
错误: 只有 3 篇引用
要求: IEEE 最少 10 篇
```
**影响严重度**: major
**修复**: 补充文献至模板最低要求

### 8. 页码缺失
```
错误: 没有页码设置
正确: \pagestyle{plain}
```
**影响严重度**: minor
**修复**: 在 document 环境中添加

### 9. 字号错误
```
错误: \documentclass[12pt]{article}
要求: 10pt (IEEE)
```
**影响严重度**: minor
**修复**: 修改 documentclass 选项

### 10. 标题层级跳跃
```
错误: 直接 Heading 1 → Heading 3
正确: Heading 1 → Heading 2 → Heading 3
```
**影响严重度**: major
**修复**: 在跳级处插入中间级别标题

## Word 常见错误及修复

### 1. 正文样式不统一
部分段落使用 "Normal"，部分使用其他样式。修复：选中全文 → 重置为 Normal 样式。

### 2. 图表编号不连续
检查编号序列中是否有遗漏。修复：重新编号（右键 → 更新域）。

### 3. 目录未更新
论文修改后目录未刷新。修复：右键目录 → 更新域。

### 4. 页眉页脚不一致
节的断开设置导致页眉显示错误。修复：取消"链接到前一节"后修正。
