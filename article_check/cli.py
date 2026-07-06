"""
命令行入口 — 论文审查 CLI

支持:
- 单篇审查: python -m article_check review path/to/paper.tex
- 批量审查: python -m article_check batch path/to/dir
- 格式检查: python -m article_check format path/to/paper.tex
- 文献审查: python -m article_check refs path/to/paper.tex
- 列出工具: python -m article_check tools
"""
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from article_check import __version__
from article_check.config.settings import config
from article_check.core.harness.base import Harness
from article_check.core.harness.tools import (
    get_default_tools,
    ToolRegistry,
)
from article_check.core.worktree.manager import WorktreeManager
from article_check.pipeline.orchestrator import Orchestrator, PaperTask
from article_check.pipeline.worker import FormatWorker, ContentWorker, ReferenceWorker
from article_check.pipeline.reviewer import Reviewer
from article_check.llm.client.deepseek import DeepSeekClient
from article_check.mcp.tools.format_tools import (
    check_latex_format,
    check_docx_format,
    check_structure,
)
from article_check.utils.file_utils import find_papers, detect_file_type

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def create_orchestrator() -> Orchestrator:
    """创建配置好的审查编排器"""
    harness = Harness()

    # 注册默认工具
    tool_specs = get_default_tools()
    for spec in tool_specs.values():
        harness.register_tool(spec)

    # 绑定实际工具函数
    harness.get_tool("check_latex_format").fn = check_latex_format
    harness.get_tool("check_docx_format").fn = check_docx_format
    harness.get_tool("check_structure").fn = check_structure

    # 创建编排器
    orchestrator = Orchestrator(harness=harness)

    # 注册 Worker
    orchestrator.register_worker(FormatWorker(harness))
    orchestrator.register_worker(ReferenceWorker(harness))

    # 注册 Reviewer
    orchestrator.register_reviewer(Reviewer())

    return orchestrator


def cmd_review(args):
    """单篇审查命令"""
    setup_logging(args.verbose)

    paper_path = Path(args.paper)
    if not paper_path.exists():
        print(f"❌ 文件不存在: {paper_path}")
        sys.exit(1)

    # 配置 DeepSeek
    if args.api_key:
        config.deepseek.api_key = args.api_key
    if not config.deepseek.api_key:
        print("⚠️  未设置 DEEPSEEK_API_KEY。只在无 API 模式运行（格式检查+文献验证）")
        print("   设置: export DEEPSEEK_API_KEY=sk-xxx")
        print("       或: python -m article_check review paper.tex --api-key sk-xxx")

    orchestrator = create_orchestrator()

    # 如果有 API key，添加内容审查 Worker
    if config.deepseek.api_key:
        llm = DeepSeekClient()
        orchestrator.register_worker(ContentWorker(orchestrator.harness, llm))

    task = PaperTask(
        task_id=paper_path.stem,
        paper_path=paper_path,
        title=paper_path.stem,
        file_type=detect_file_type(paper_path),
        review_depth=args.depth or "auto",
    )

    print(f"🔍 开始审查: {paper_path.name}")
    print(f"   文件类型: {task.file_type}")
    print(f"   审查深度: {task.review_depth}")
    print()

    result = asyncio.run(orchestrator.review_single(task))

    _print_result(result)


def cmd_batch(args):
    """批量审查命令"""
    setup_logging(args.verbose)

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"❌ 目录不存在: {directory}")
        sys.exit(1)

    papers = find_papers(str(directory), file_types=args.types)
    if not papers:
        print(f"⚠️  在 {directory} 中没有找到论文文件")
        print(f"   支持格式: .tex, .docx, .pdf")
        sys.exit(0)

    print(f"📚 找到 {len(papers)} 篇论文:")
    for p in papers:
        print(f"   - [{p['type']}] {p['name']} ({p['size']/1024:.1f} KB)")
    print()

    if config.deepseek.api_key:
        llm = DeepSeekClient()
    else:
        llm = None
        print("⚠️  无 API key，将跳过内容审查")

    orchestrator = create_orchestrator()
    if llm:
        orchestrator.register_worker(ContentWorker(orchestrator.harness, llm))

    tasks = [
        PaperTask(
            task_id=p["name"],
            paper_path=Path(p["path"]),
            title=p["name"],
            file_type=p["type"],
        )
        for p in papers
    ]

    max_c = args.concurrent or config.pipeline.max_concurrent
    print(f"🚀 开始批量审查 (并发={max_c})...")
    print()

    results = asyncio.run(
        orchestrator.review_batch(tasks, max_concurrent=max_c)
    )

    for r in results:
        _print_result(r)
        print()

    # 打印汇总
    print("=" * 50)
    print("📊 批量审查汇总")
    print("=" * 50)
    for r in results:
        score = r.overall_score or 0
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {r.paper_title:30s} [{bar}] {score:.2f}")
    print(f"  完成: {sum(1 for r in results if not r.errors)}/{len(results)}")


def cmd_format(args):
    """格式检查命令（无需 LLM）"""
    setup_logging(args.verbose)

    paper_path = Path(args.paper)
    if not paper_path.exists():
        print(f"❌ 文件不存在: {paper_path}")
        sys.exit(1)

    file_type = detect_file_type(paper_path)
    print(f"🔍 格式检查: {paper_path.name}")
    print(f"   文件类型: {file_type}")
    print()

    if file_type == "latex":
        issues = check_latex_format(str(paper_path))
    elif file_type == "docx":
        issues = check_docx_format(str(paper_path))
    else:
        print(f"⚠️  不支持的文件类型: {file_type}")
        sys.exit(1)

    if not issues:
        print("✅ 未发现格式问题")
        return

    print(f"📋 发现 {len(issues)} 个格式问题:")
    for i, issue in enumerate(issues, 1):
        sev = issue.get("severity", "info")
        emoji = {"critical": "🔴", "major": "🟡", "minor": "🟢", "info": "ℹ️"}
        print(f"\n{emoji.get(sev, '•')} #{i} [{sev.upper()}] {issue.get('description', '')}")
        if issue.get("suggestion"):
            print(f"   💡 建议: {issue['suggestion']}")
        if issue.get("line"):
            print(f"   📍 行 {issue['line']}")


def cmd_refs(args):
    """文献审查命令"""
    setup_logging(args.verbose)
    print("📚 文献审查（待实现 — 需要配置学术数据库 API）")
    print("   计划接入: Semantic Scholar / CrossRef / OpenAlex")


def cmd_tools(args):
    """列出所有可用工具"""
    print("[Tools] 已注册的工具:")
    registry = ToolRegistry()
    tools = get_default_tools()

    for name, spec in tools.items():
        print(f"\n  📌 {name}")
        print(f"     {spec.description}")
        params = list(spec.parameters.keys())
        if params:
            print(f"     参数: {', '.join(params)}")
        if spec.required:
            print(f"     必填: {', '.join(spec.required)}")


def cmd_config(args):
    """显示当前配置"""
    print("[Config] 当前配置:")
    d = config.to_dict()
    print(json.dumps(d, ensure_ascii=False, indent=2))


def _print_result(result):
    """打印审查结果到控制台"""
    score = result.overall_score or 0
    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))

    print(f"📋 {result.paper_title}")
    print(f"   评分: [{bar}] {score:.2f}")
    print(f"   耗时: {result.duration:.1f}s")

    if result.errors:
        for err in result.errors:
            print(f"   ❌ 错误: {err}")

    if result.report_path:
        print(f"   📄 报告: {result.report_path}")

    # 格式问题摘要
    if result.format_check:
        fmt_issues = result.format_check.get("issues", [])
        if isinstance(fmt_issues, list):
            crits = sum(1 for i in fmt_issues if isinstance(i, dict) and i.get("severity") == "critical")
            majors = sum(1 for i in fmt_issues if isinstance(i, dict) and i.get("severity") == "major")
            if fmt_issues:
                print(f"   📐 格式: {len(fmt_issues)} 个问题 (严重={crits}, 重要={majors})")

    # 内容问题摘要
    if result.content_review:
        total = 0
        for v in result.content_review.values():
            if isinstance(v, dict):
                total += len(v.get("issues", []))
        if total:
            print(f"   📝 内容: {total} 个问题")


def main():
    parser = argparse.ArgumentParser(
        description=f"📋 论文审查智能体 v{__version__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m article_check review paper.tex              # 审查单篇 LaTeX
  python -m article_check review paper.docx --api-key sk-xxx  # 审查 Word
  python -m article_check batch ./papers/                # 批量审查目录
  python -m article_check batch ./papers/ --concurrent 8  # 8 并发
  python -m article_check format paper.tex               # 仅格式检查
  python -m article_check tools                          # 列出工具
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"article-check v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # review
    p_review = subparsers.add_parser("review", help="审查单篇论文")
    p_review.add_argument("paper", help="论文文件路径")
    p_review.add_argument("--api-key", help="DeepSeek API Key")
    p_review.add_argument("--depth", choices=["quick", "auto", "full"], default="auto")
    p_review.add_argument("-v", "--verbose", action="store_true")

    # batch
    p_batch = subparsers.add_parser("batch", help="批量审查论文")
    p_batch.add_argument("directory", help="论文目录")
    p_batch.add_argument("--api-key", help="DeepSeek API Key")
    p_batch.add_argument("-c", "--concurrent", type=int, default=None)
    p_batch.add_argument("-t", "--types", nargs="+", default=["latex", "docx", "pdf"])
    p_batch.add_argument("-v", "--verbose", action="store_true")

    # format
    p_format = subparsers.add_parser("format", help="格式检查（无需 LLM）")
    p_format.add_argument("paper", help="论文文件路径")
    p_format.add_argument("-v", "--verbose", action="store_true")

    # refs
    p_refs = subparsers.add_parser("refs", help="文献审查")
    p_refs.add_argument("paper", help="论文文件路径")

    # tools
    subparsers.add_parser("tools", help="列出所有可用工具")

    # config
    subparsers.add_parser("config", help="显示当前配置")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # 命令分发
    commands = {
        "review": cmd_review,
        "batch": cmd_batch,
        "format": cmd_format,
        "refs": cmd_refs,
        "tools": cmd_tools,
        "config": cmd_config,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)


if __name__ == "__main__":
    main()
