"""统一文档层 — 读写 DOCX / LaTeX / PDF / Markdown"""
from article_check.documents.core import (
    InternalDoc, DocReader, DocWriter,
    DocumentFormat,
    read_document, write_document, convert_document,
)
