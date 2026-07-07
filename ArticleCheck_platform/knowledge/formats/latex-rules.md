# LaTeX 格式规则知识库

本文档包含学术论文 LaTeX 格式的核心规则，供审查智能体在格式检查时参考。

## 文档类 (documentclass)

| 模板 | 文档类 | 适用 |
|------|--------|------|
| IEEE Transactions | `\documentclass[10pt,conference]{IEEEtran}` | IEEE 系列 |
| ACM Conference | `\documentclass[sigconf]{acmart}` | ACM 会议 |
| Springer LNCS | `\documentclass{llncs}` | LNCS 论文集 |
| Elsevier | `\documentclass[5p]{elsarticle}` | Elsevier 期刊 |
| 中文论文 (通用) | `\documentclass[12pt]{article}` | 一般中文投稿 |

**字号规范：**
- IEEE: 10pt
- ACM: 9pt
- Elsevier: 12pt (双倍行距) / 10pt (单倍)
- LNCS: 10pt
- 中文国标: 小四号 (12pt)

## 字体要求

| 模板 | 正文 | 标题 | 等宽 |
|------|------|------|------|
| IEEE | Times New Roman 10pt | Times New Roman 10pt bold | Courier 9pt |
| Elsevier | Times New Roman 12pt | Times New Roman 12pt bold | — |
| ACM | Times New Roman 9pt | Times New Roman 9pt bold | Courier New 8pt |
| LNCS | Times New Roman 10pt | Times New Roman 10pt | — |

**LaTeX 实现：**
```latex
\usepackage{mathptmx}        % Times New Roman 正文
\usepackage[scaled]{helvet}  % 无衬线字体
\usepackage{courier}         % 等宽字体
```

## 页面布局

| 模板 | 纸张 | 页边距 (mm) | 行距 |
|------|------|-------------|------|
| IEEE | Letter | 上19.05 下19.05 左17.78 右17.78 | 单倍 |
| Elsevier | A4 | 各20mm | 1.5倍 |
| ACM | Letter | 各19.05mm | 单倍 |
| LNCS | A4 | 上45 下56 左28 右28 | 单倍 |
| 中文标准 | A4 | 上25.4 下25.4 左31.7 右31.7 | 1.5-2.0倍 |

## 章节结构检查

### 必需章节

| 模板 | 必需章节 |
|------|---------|
| IEEE | abstract, introduction, conclusion, references |
| Elsevier | abstract, introduction, method, results, discussion, conclusion, references |
| ACM | abstract, introduction, conclusion, references |
| LNCS | abstract, introduction, conclusion, references |

**章节编号：** IEEE/ACM 使用编号，LNCS 使用编号，部分期刊要求无编号。

### 摘要字数限制

| 模板 | 最多字数 |
|------|---------|
| IEEE | 200 words |
| ACM | 150 words |
| Elsevier | 300 words |
| LNCS | 200 words |

## 图表规范

- **标题位置：** IEEE — 图题在下、表题在上；ACM — 图题在下、表题在上
- **编号：** 必须按出现顺序编号 (Figure 1, Figure 2; Table I, Table II)
- **引用：** 正文中必须引用所有图表，"as shown in Figure 1"
- **分辨率：** 一般要求至少 300 DPI
- **格式：** EPS/PDF (LaTeX), TIFF/JPEG (Word)

## 数学公式

| 正确方式 | 错误方式 |
|---------|---------|
| `\[ ... \]` | `$$ ... $$` (AMS 不推荐) |
| `\begin{equation}...\end{equation}` | 手动编号 |
| `\text{}` 在数学模式内 | `\rm` (已弃用) |
| `\label{...}` / `\ref{...}` | 硬编码编号 |

## 常见 LaTeX 错误

1. **命令后缺空格** — `\LaTeX` 后应加 `{}` 或空格
2. **引号错误** — 应使用 `` `` '' '' 而非 " " 
3. **破折号** — `-` 连字符, `--` 数字范围, `---` 破折号
4. **省略号** — 使用 `\dots` 而非 `...`
5. **非断行空格** — 使用 `~` 而非空格
6. **花括号不匹配** — 确保 `{...}` 成对
7. **数学模式外使用数学命令** — `\sin`, `\log` 等只能在数学模式
8. **无效的字体大小** — `\tiny`, `\small` 等不能在 `\documentclass` 外随意使用
