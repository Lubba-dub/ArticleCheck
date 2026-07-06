"""
格式检查工具 — 在 Harness 工具层运行的本地格式规则引擎

零 token 成本 — 完全本地执行。
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from article_check.rules.latex.checker import LaTeXChecker
from article_check.rules.docx.checker import DocxChecker

logger = logging.getLogger(__name__)

# 全局检查器实例
_latex_checker = LaTeXChecker()
_docx_checker = DocxChecker()


def check_latex_format(
    file_path: str,
    rules_filter: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    检查 LaTeX 文件格式

    零 token 成本 — 使用本地 chktex 规则引擎。

    Args:
        file_path: LaTeX 文件路径
        rules_filter: 可选，仅检查指定规则编号

    Returns:
        格式问题列表
    """
    logger.info(f"check_latex_format: {file_path}")
    issues = _latex_checker.check(file_path)

    if rules_filter:
        issues = [i for i in issues if i.get("rule_id") in rules_filter]

    return issues


def check_docx_format(
    file_path: str,
    template_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    检查 Word 文档格式

    零 token 成本 — 使用 python-docx 规则引擎。

    Args:
        file_path: Word 文件路径
        template_path: 可选模板路径

    Returns:
        格式问题列表
    """
    logger.info(f"check_docx_format: {file_path}")
    checker = DocxChecker(template_path=template_path)
    issues = checker.check(file_path)
    return issues


def check_structure(
    file_path: str,
    file_type: str,
    expected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    检查论文结构完整性

    Args:
        file_path: 论文文件路径
        file_type: 文件类型 (latex/docx)
        expected_sections: 期望的章节列表

    Returns:
        结构检查结果
    """
    default_sections = [
        "abstract", "introduction", "related work",
        "method", "experiment", "result",
        "discussion", "conclusion", "reference",
    ]

    sections = expected_sections or default_sections
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    text_lower = text.lower()

    found = []
    missing = []
    for sec in sections:
        if sec in text_lower:
            found.append(sec)
        else:
            missing.append(sec)

    return {
        "issues": [
            {
                "type": "missing_section",
                "severity": "major" if s in ["abstract", "reference"] else "minor",
                "section": s,
                "description": f"缺少 '{s}' 章节",
                "suggestion": f"请添加 {s} 章节",
            }
            for s in missing
        ],
        "found_sections": found,
        "missing_sections": missing,
        "complete": len(missing) == 0,
    }
