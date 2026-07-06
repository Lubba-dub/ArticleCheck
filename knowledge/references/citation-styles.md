# 学术引用与参考文献格式指南

## 常见引用风格

### IEEE 风格 (数字编号)
```
正文: ...as shown in [1]...
参考文献: 
[1] J. Clerk Maxwell, "A Treatise on Electricity and Magnetism", 
    3rd ed., vol. 2. Oxford: Clarendon, 1892, pp.68-73.
[2] I. S. Jacobs and C. P. Bean, "Fine particles, thin films and 
    exchange anisotropy," in Magnetism, vol. III, G. T. Rado and 
    H. Suhl, Eds. New York: Academic, 1963, pp. 271-350.
```
- 引用: `\cite{ref_id}` → [1]
- 排序: 按引用顺序编号
- 作者: 首字母. 姓

### APA 风格 (作者-年份)
```
正文: (Smith, 2020) 或 Smith (2020) states...
参考文献:
Smith, J. A. (2020). Title of the article. *Journal Name*, 12(3), 45-67.
https://doi.org/10.xxxx/xxxxx
```
- 引用: `\citep{ref_id}` → (Author, Year)
- 排序: 按作者姓名字母序
- DOI: 通常要求

### ACM 风格
```
正文: ...as shown by Smith et al. [2020]...
参考文献:
Smith, J. and Jones, M. 2020. Title. *Journal Name*. 12, 3 (2020), 45-67.
```
- 引用: `\cite{ref_id}` → [Author Year]
- 作者: 名 姓
- 年份: 在方括号中

### Nature 风格
```
正文: ...as previously reported¹...
参考文献:
1. Smith, J. et al. Nature 123, 45-67 (2020).
```
- 引用: 上标数字
- 作者: 姓 名(缩写)
- 期刊: 斜体 (Nature)

### Springer LNCS 风格
```
正文: ...as shown in [1]...
参考文献:
[1] Smith, J., Jones, M.: Title of the Paper. In: Conference 
    Proceedings, pp. 45-67. Springer (2020).
```
- 引用: `\cite{ref_id}` → [1]
- 作者: 姓, 名(缩写)
- 标题: 斜体

## 引用工具使用建议

| 工具 | 用途 | 输出格式 |
|------|------|---------|
| BibTeX | LaTeX 文献管理 | .bib 文件 |
| BibLaTeX | 灵活的 LaTeX 文献 | .bib + 样式 |
| Zotero | 通用引用管理 | Word/LibreOffice 插件 |
| Mendeley | 引用管理+PDF | Word 插件 |

## DOI 验证

DOI (Digital Object Identifier) 是文献的唯一标识符:
- 格式: `10.xxxx/xxxxx`
- 验证: `https://doi.org/10.xxxx/xxxxx` → 302 跳转到文献主页
- API: `https://api.crossref.org/works/10.xxxx/xxxxx` → JSON 元数据
- 学术搜索: `https://api.semanticscholar.org/graph/v1/paper/DOI:10.xxxx/xxxxx`

## 引用准确性的检查方法

1. **存在性**: DOI/标题是否真实存在
2. **元数据匹配**: 作者/年份/期刊是否与数据库一致
3. **引用上下文**: 论文声称的内容是否与原文一致（需要人工核查）
4. **时效性**: 引用是否过时，是否有更新的版本
5. **相关性**: 引用是否真的支持论文的论点

## BibTeX 常见条目类型

```bibtex
@article{ref_id,
  author    = {Author, A. and Author, B.},
  title     = {Title of the Article},
  journal   = {Journal Name},
  volume    = {12},
  number    = {3},
  pages     = {45-67},
  year      = {2020},
  doi       = {10.xxxx/xxxxx},
}

@inproceedings{ref_id,
  author    = {Author, A.},
  title     = {Title of the Paper},
  booktitle = {Conference Proceedings},
  pages     = {45-67},
  year      = {2020},
  publisher = {IEEE},
}

@book{ref_id,
  author    = {Author, A.},
  title     = {Book Title},
  publisher = {Publisher},
  year      = {2020},
  edition   = {3rd},
}
```
