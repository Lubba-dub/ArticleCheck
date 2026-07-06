"""投稿就绪检查 — 对标期刊投稿系统

核心功能:
1. 从目标期刊官网/模板拉取投稿要求
2. 按投稿阶段 (initial/double-blind/camera-ready) 检查
3. 输出 PASS/FAIL 清单式报告

参考: submit-check (SkillsMP), IEEE Compliance Framework
"""
from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from article_check.rules.registry import template_registry
from article_check.rules.engine import TemplateRuleEngine
from article_check.mcp.tools.format_tools import check_docx_format, check_latex_format

logger = logging.getLogger(__name__)


@dataclass
class SubmissionRequirement:
    """一条投稿要求"""
    name: str
    category: str  # format / structure / reference / figure / ethics
    description: str
    required: bool = True
    stage: str = "initial"  # initial / double-blind / camera-ready
    check_fn: str = ""       # 对应的检查函数名


@dataclass
class SubmissionCheckItem:
    """单条检查结果"""
    name: str
    category: str
    status: str  # pass / fail / warn / skip
    detail: str = ""
    suggestion: str = ""


@dataclass
class SubmissionReport:
    """投稿检查报告"""
    journal: str
    stage: str
    items: List[SubmissionCheckItem] = field(default_factory=list)
    paper_path: str = ""

    @property
    def passed(self) -> int:
        return sum(1 for i in self.items if i.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for i in self.items if i.status == "fail")

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def ready(self) -> bool:
        return self.failed == 0

    def to_markdown(self) -> str:
        lines = [
            f"## 📋 投稿就绪检查报告",
            f"",
            f"**目标期刊**: {self.journal} | **投稿阶段**: {self.stage}",
            f"**结果**: {'✅ 可投稿' if self.ready else '❌ 需修改'} ({self.passed}/{self.total} 通过)",
            f"",
        ]
        for item in self.items:
            emoji = {"pass": "✅", "fail": "❌", "warn": "⚠️", "skip": "⏭️"}
            lines.append(f"{emoji.get(item.status, '•')} **{item.name}**")
            lines.append(f"   {item.detail}")
            if item.suggestion:
                lines.append(f"   💡 {item.suggestion}")
            lines.append("")
        return "\n".join(lines)


class JournalGuidelineFetcher:
    """目标期刊投稿指南获取器"""

    # 内置期刊投稿要求
    JOURNALS: Dict[str, Dict[str, Any]] = {
        "IEEE Transactions": {
            "stage_rules": {
                "double-blind": [
                    {"name": "匿名化作者", "check": r"\author\{", "expect_missing": True},
                    {"name": "删除致谢", "check": r"\acknowledgment|\thanks", "expect_missing": True},
                ],
                "camera_ready": [
                    {"name": "版权声明", "check": r"\IEEEpeerreviewmaketitle", "expect_missing": False},
                ],
            },
            "requirements": [
                {"name": "正文字体 Times New Roman 10pt", "category": "format"},
                {"name": "参考文献 ≥ 10 篇", "category": "reference"},
                {"name": "摘要 ≤ 200 词", "category": "structure"},
                {"name": "图表编号连续", "category": "figure"},
            ],
        },
        "Elsevier": {
            "requirements": [
                {"name": "正文字体 Times New Roman 12pt", "category": "format"},
                {"name": "参考文献 ≥ 15 篇", "category": "reference"},
                {"name": "行距 1.5 倍", "category": "format"},
                {"name": "图表标题在上(表)/在下(图)", "category": "figure"},
            ],
        },
    }

    def fetch(self, journal_name: str) -> Dict[str, Any]:
        """获取期刊投稿要求"""
        journal_name_lower = journal_name.lower()
        # 模糊匹配
        for key, spec in self.JOURNALS.items():
            if key.lower() in journal_name_lower or journal_name_lower in key.lower():
                return spec
        # 尝试从模板系统获取
        tpl = template_registry.get(journal_name)
        if tpl:
            spec = {"requirements": [], "stage_rules": {}}
            if tpl.references:
                spec["requirements"].append({
                    "name": f"参考文献 ≥ {tpl.references.min_refs} 篇",
                    "category": "reference",
                })
            if tpl.font:
                spec["requirements"].append({
                    "name": f"正文 {tpl.font.body_font} {tpl.font.body_size_pt}pt",
                    "category": "format",
                })
            if tpl.section:
                spec["requirements"].append({
                    "name": f"摘要 ≤ {tpl.section.max_abstract_words} 词",
                    "category": "structure",
                })
            if tpl.title_page:
                spec["requirements"].append({
                    "name": f"需有关键词 (≤ {tpl.title_page.keywords_max} 个)",
                    "category": "structure",
                })
            return spec
        return {"requirements": [], "stage_rules": {}}


class SubmissionChecker:
    """投稿检查器 — 逐条检查投稿要求"""

    def __init__(self, journal: str, stage: str = "initial"):
        self.journal = journal
        self.stage = stage
        self.fetcher = JournalGuidelineFetcher()
        self.guidelines = self.fetcher.fetch(journal)
        self.engine = TemplateRuleEngine()
        logger.info(f"SubmissionChecker: {journal} ({stage})")

    def check(self, paper_path: str) -> SubmissionReport:
        """执行投稿检查"""
        report = SubmissionReport(
            journal=self.journal,
            stage=self.stage,
            paper_path=paper_path,
        )
        path = Path(paper_path)
        if not path.exists():
            report.items.append(SubmissionCheckItem(
                name="文件存在", category="format",
                status="fail", detail="文件不存在",
            ))
            return report

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""

        # 1. 模板格式检查
        from article_check.utils.file_utils import detect_file_type
        ft = detect_file_type(path)
        tpl_issues = self.engine.check(self.journal, path, ft) if template_registry.get(self.journal) else []

        for req in self.guidelines.get("requirements", []):
            item = SubmissionCheckItem(
                name=req["name"], category=req["category"], status="pass",
            )
            # 匹配对应的 template engine 检查结果
            matched = [i for i in tpl_issues if req["name"][:10].lower() in i.get("description", "").lower()]
            if matched:
                item.status = "fail"
                item.detail = matched[0].get("description", "")
                item.suggestion = matched[0].get("suggestion", "")
            report.items.append(item)

        # 2. 投稿阶段特定检查
        stage_rules = self.guidelines.get("stage_rules", {}).get(self.stage, [])
        for rule in stage_rules:
            item = SubmissionCheckItem(
                name=rule["name"], category="format", status="fail",
            )
            found = re.search(rule["check"], text) if text else None
            if rule.get("expect_missing"):
                item.status = "pass" if not found else "fail"
                item.detail = "未检测到（符合要求）" if not found else f"检测到: {found.group()[:50]}"
            else:
                item.status = "pass" if found else "fail"
                item.detail = f"已找到: {found.group()[:50]}" if found else "未找到"
            report.items.append(item)

        logger.info(f"投稿检查完成: {report.passed}/{report.total} 通过")
        return report
