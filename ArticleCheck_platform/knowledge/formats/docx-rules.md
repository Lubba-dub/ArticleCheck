# Microsoft Word (DOCX) 格式规则知识库

本文档包含 Word 文档格式的核心检查规则，供审查智能体在格式检查时参考。

## 常用中文学位论文/期刊模板规范

| 项目 | 本科毕业论文 | 硕士/博士论文 | 期刊投稿 |
|------|-------------|-------------|---------|
| 页面 | A4 | A4 | 按期刊要求 |
| 上边距 | 25mm | 25mm | 20mm |
| 下边距 | 25mm | 25mm | 20mm |
| 左边距 | 30mm | 30mm | 25mm |
| 右边距 | 25mm | 25mm | 20mm |
| 行距 | 1.5倍 | 1.5-2倍 | 单倍/1.5倍 |
| 正文 | 宋体/小四 (12pt) | 宋体/小四 (12pt) | Times New Roman 10-12pt |

## Word 样式检查要点

### 标题样式层次
```
Heading 1 → 章 (第1章, 第一章)
Heading 2 → 节 (1.1, 1.2)
Heading 3 → 小节 (1.1.1, 1.1.2)
Heading 4 → 条 (1.1.1.1)
```

**检查项：**
- 标题样式连续（不许 H1 → H3 跳级）
- 标题编号格式一致
- 所有正文使用 "Normal" 样式

### 字体一致性
- 全文正文字体统一（中文宋体/英文 Times New Roman）
- 中英文混排时中文字体不改变
- 公式符号统一用 Italic 表示变量
- 图表标题字体统一（通常小五号/9pt）

### 段落格式
- 首行缩进 2 字符（中文）/ 0（英文）
- 段前段后间距一致（通常 0pt/6pt）
- 对齐方式：正文两端对齐，标题居中/左对齐
- 行距统一

### 图表编号
- `图 1-1`, `图 1-2`（第1章第1/2图）
- `表 1-1`（第1章第1表）
- 编号必须连续，不能跳号
- 正文必须引用所有图表

### 页码
- 封面：无页码
- 摘要/目录：罗马数字 (i, ii, iii)
- 正文：阿拉伯数字 (1, 2, 3)
- 页面底端居中或右对齐

### 页眉页脚
- 页眉：一般奇数页显示章名，偶数页显示论文标题
- 页脚：页码
- 学位论文：页眉通常有"XX大学硕士学位论文"

## python-docx 检查方法

```python
from docx import Document
doc = Document('paper.docx')

# 检查标题样式
for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        level = para.style.name.replace('Heading ', '')
        # 检查级别连续性

# 检查字体
for para in doc.paragraphs:
    for run in para.runs:
        if run.font.name != 'Times New Roman' and run.font.name != '宋体':
            # 记录不一致字体

# 检查段落间距
from docx.shared import Pt
for para in doc.paragraphs:
    pf = para.paragraph_format
    if pf.line_spacing and pf.line_spacing != 1.5:
        # 行距异常
```
