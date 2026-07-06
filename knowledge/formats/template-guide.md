# 格式模板使用指南

本文档说明如何创建、注册和使用格式模板。

## 什么是格式模板

格式模板是对一种期刊/论文类别的完整格式描述，包含 8 个约束组：

| 约束组 | 内容 |
|--------|------|
| `PageConstraint` | 纸张、页边距、行距、页码 |
| `FontConstraint` | 正文字体/大小、标题字体、等宽字体 |
| `SectionConstraint` | 必需章节、摘要字数、章节编号 |
| `FigureTableConstraint` | 图表最大数、标题位置、编号 |
| `ReferenceConstraint` | 引用格式、最少/最多参考文献数 |
| `TitlePageConstraint` | 标题字数、作者单位、关键词 |

## 如何创建一个新模板

用户提供格式规范后，只需在 `rules/template.py` 中新增一个：

```python
MY_JOURNAL_TEMPLATE = FormatTemplate(
    name="My Journal Name",
    version="1.0",
    description="My Journal 标准投稿格式",
    category="journal",
    
    # 页面布局
    page=PageConstraint(
        paper_size="A4",
        margin_top_mm=25.4,
        margin_bottom_mm=25.4,
        margin_left_mm=30.0,
        margin_right_mm=25.0,
        line_spacing=2.0,
        page_numbers=True,
    ),
    
    # 字体
    font=FontConstraint(
        body_font="Times New Roman",
        body_size_pt=12,
        heading_font="Times New Roman",
        heading_sizes={1: 14, 2: 12, 3: 12},
    ),
    
    # 章节
    section=SectionConstraint(
        required_sections=["abstract", "introduction", 
                          "method", "result", "discussion",
                          "conclusion", "reference"],
        max_abstract_words=250,
        section_numbering=True,
    ),
    
    # 文献
    references=ReferenceConstraint(
        ref_format="apa",
        citation_style="author_year",
        min_refs=20,
        max_refs=60,
    ),
    
    # LaTeX 约束
    latex_class="myjournal",
    latex_packages=["amsmath", "graphicx", "natbib"],
)
```

然后在 `rules/registry.py` 的 `_init_builtin_templates` 中注册：
```python
self.register(MY_JOURNAL_TEMPLATE)
```

## 模板自动检测逻辑

当运行 `template auto-detect` 时，系统按以下顺序匹配：

1. **LaTeX 文档类匹配** — 比较 `\documentclass{...}` 与模板的 `latex_class`
2. **宏包匹配** — 比较 `\usepackage{...}` 列表，重叠 ≥2 个则匹配
3. **文本关键词匹配** — 在论文前 500 字符中搜索模板名称关键词

## 检查规则对照表 (18 条内置规则)

| 规则 | 作用 | 依赖 |
|------|------|------|
| `_check_line_spacing` | 检查 `\linespread` / `\setstretch` | LaTeX 正则 |
| `_check_margins` | 检查 geometry 页边距设置 | LaTeX 正则 |
| `_check_page_numbers` | 检查 `\pagestyle`, `\thepage` | LaTeX 正则 |
| `_check_body_font` | 检查 mathptmx/times/setmainfont | LaTeX 正则 |
| `_check_font_sizes` | 检查 documentclass 字号参数 | LaTeX 正则 |
| `_check_required_sections` | 检查必需章节是否存在 | LaTeX 正则 |
| `_check_abstract_word_count` | 统计 abstract 环境中的词数 | LaTeX 正则 |
| `_check_section_numbering` | 检查是否使用编号或星号 | LaTeX 正则 |
| `_check_figure_captions` | 检查 figure 环境是否有 caption | LaTeX 正则 |
| `_check_table_captions` | 检查 table 环境是否有 caption | LaTeX 正则 |
| `_check_reference_count` | 统计 bibitem 条目数 | LaTeX 正则 |
| `_check_latex_class` | 检查 documentclass 是否匹配 | LaTeX 正则 |
| `_check_latex_packages` | 检查必需宏包是否加载 | LaTeX 正则 |
| `_check_abstract_presence` | 检查 abstract 环境存在性 | LaTeX 正则 |
| `_check_keywords_presence` | 检查 keywords 命令存在性 | LaTeX 正则 |
| `_check_heading_styles` | 检查 Word 标题样式层次 | python-docx |
