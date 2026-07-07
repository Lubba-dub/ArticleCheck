# 学术搜索与 DOI 验证指南

## 免费学术 API

| API | 速率限制 | 需要密钥 | 用途 |
|-----|---------|---------|------|
| Semantic Scholar | 100 req/s | 否 (推荐免费 key) | 论文搜索、引用图谱 |
| CrossRef | 50 req/s | 否 | DOI 元数据 |
| OpenAlex | 100k req/d | 否 | 学术图谱 |
| arXiv | 无限制 | 否 | 预印本全文 |
| DBLP | 无限制 | 否 | 计算机科学文献 |

## Semantic Scholar API 使用

搜索论文:
```
GET https://api.semanticscholar.org/graph/v1/paper/search?query=transformer&limit=10
```

按 DOI 获取:
```
GET https://api.semanticscholar.org/graph/v1/paper/DOI:10.xxxx/xxxxx?fields=title,authors,year,citationCount
```

## CrossRef API 使用

DOI 元数据:
```
GET https://api.crossref.org/works/10.xxxx/xxxxx
```

返回 JSON 包含: title, author, publisher, type, DOI, URL, issued (date-parts)

## arXiv API 使用

搜索:
```
http://export.arxiv.org/api/query?search_query=all:transformer&start=0&max_results=10
```

返回 Atom XML，解析 entry/title, entry/summary, entry/id, entry/author

## 引用验证流程

```
发现的引用 → 提取 DOI/标题/作者
    ↓
调用 CrossRef API 验证 DOI 存在性
    ↓
调用 Semantic Scholar API 获取引用元数据
    ↓
对比: 标题是否匹配? 作者是否匹配? 年份是否一致?
    ↓
不匹配 → 标记为可疑引用
    ↓
出具文献验证报告
```
