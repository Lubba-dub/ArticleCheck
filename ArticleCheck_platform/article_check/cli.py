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
from article_check.core.harness.tools import ToolRegistry
from article_check.core.worktree.manager import WorktreeManager
from article_check.pipeline.orchestrator import Orchestrator
from article_check.mcp.tools.format_tools import (
    check_latex_format,
    check_docx_format,
    check_structure,
)
from article_check.runtime import (
    answer_report_question,
    build_batch_payload,
    build_review_payload,
    build_runtime,
    create_paper_task,
    execute_review_batch,
    execute_review_task,
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
    runtime = build_runtime(mode="cli", enable_deep_review=False)
    return runtime.orchestrator


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

    runtime = build_runtime(
        mode="cli",
        enable_deep_review=bool(config.deepseek.api_key),
        api_key=args.api_key,
        paper_paths=[str(paper_path)],
    )
    task = create_paper_task(
        paper_path,
        depth=args.depth or "auto",
    )

    print(f"🔍 开始审查: {paper_path.name}")
    print(f"   文件类型: {task.file_type}")
    print(f"   审查深度: {task.review_depth}")
    print()

    result = asyncio.run(
        execute_review_task(
            runtime,
            task,
            enable_deep_review=bool(config.deepseek.api_key),
        )
    )

    _print_result(result)
    if getattr(args, "json_output", None):
        payload = build_review_payload(result, plan_id=runtime.plan.plan_id)
        Path(args.json_output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


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

    if args.api_key:
        config.deepseek.api_key = args.api_key
    if not config.deepseek.api_key:
        print("⚠️  无 API key，将跳过内容审查")

    runtime = build_runtime(
        mode="batch",
        enable_deep_review=bool(config.deepseek.api_key),
        api_key=args.api_key,
        paper_paths=[p["path"] for p in papers],
    )

    tasks = [
        create_paper_task(
            p["path"],
            depth="auto",
        )
        for p in papers
    ]

    max_c = args.concurrent or config.pipeline.max_concurrent
    print(f"🚀 开始批量审查 (并发={max_c})...")
    print()

    results = asyncio.run(execute_review_batch(runtime, tasks, max_concurrent=max_c))

    for r in results:
        _print_result(r)
        print()

    if getattr(args, "json_output", None):
        payload = build_batch_payload(results, plan_id=runtime.plan.plan_id)
        Path(args.json_output).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 打印汇总
    print("=" * 50)
    print("📊 批量审查汇总")
    print("=" * 50)
    for r in results:
        score = r.overall_score or 0
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {r.paper_title:30s} [{bar}] {score:.2f}")
    print(f"  完成: {sum(1 for r in results if not r.errors)}/{len(results)}")


def cmd_template(args):
    """模板管理命令"""
    from article_check.rules.template import FormatTemplate, PageConstraint, \
        FontConstraint, SectionConstraint, ReferenceConstraint, \
        FigureTableConstraint, TitlePageConstraint
    from article_check.rules.registry import template_registry

    if args.action == "list":
        templates = template_registry.list_all()
        if not templates:
            print("暂无注册的模板")
            return
        print(f"已注册模板 ({len(templates)}):")
        print()
        for tpl in templates:
            print(f"  📌 {tpl.name}")
            print(f"     类别: {tpl.category} | 描述: {tpl.description}")
            if tpl.latex_class:
                print(f"     LaTeX: \\documentclass{{{tpl.latex_class}}}")
            print()

    elif args.action == "show":
        tpl = template_registry.get(args.name)
        if not tpl:
            print(f"未找到模板: {args.name}")
            return
        import dataclasses
        d = dataclasses.asdict(tpl)
        import json
        print(json.dumps(d, ensure_ascii=False, indent=2))

    elif args.action == "search":
        results = template_registry.search(args.query)
        if not results:
            print(f"未找到匹配 '{args.query}' 的模板")
            return
        print(f"匹配 '{args.query}' 的模板:")
        for tpl in results:
            print(f"  📌 {tpl.name} [{tpl.category}]")

    elif args.action == "check":
        """用指定模板检查论文格式"""
        setup_logging(args.verbose)
        paper_path = Path(args.paper)
        if not paper_path.exists():
            print(f"文件不存在: {paper_path}")
            return

        from article_check.rules.engine import TemplateRuleEngine
        from article_check.utils.file_utils import detect_file_type

        engine = TemplateRuleEngine()
        file_type = detect_file_type(paper_path)

        print(f"检查论文: {paper_path.name}")
        print(f"使用模板: {args.template_name}")
        print(f"文件类型: {file_type}")
        print()

        issues = engine.check(args.template_name, paper_path, file_type)

        if not issues:
            print("✅ 格式符合模板规范")
            return

        print(f"发现 {len(issues)} 个格式问题:")
        for i, issue in enumerate(issues, 1):
            sev = issue.get("severity", "info")
            emoji = {"critical": "🔴", "major": "🟡", "minor": "🟢", "info": "ℹ️"}
            print(f"\n{emoji.get(sev, '•')} #{i} [{sev.upper()}] {issue.get('description', '')}")
            if issue.get("suggestion"):
                print(f"   💡 建议: {issue['suggestion']}")

    elif args.action == "auto-detect":
        """自动检测论文匹配哪类模板"""
        paper_path = Path(args.paper)
        if not paper_path.exists():
            print(f"文件不存在: {paper_path}")
            return

        text = paper_path.read_text(encoding="utf-8", errors="replace")

        # LaTeX 文档类检测
        import re
        m = re.search(r'\\documentclass(?:\[[^\]]*\])?\{(.+?)\}', text)
        latex_class = m.group(1) if m else None

        # 检测宏包
        packages = re.findall(r'\\usepackage(?:\[[^\]]*\])?\{(.+?)\}', text)

        # 自动匹配
        tpl = template_registry.detect_matching_template(
            latex_class=latex_class,
            packages=packages,
            text_sample=text[:500],
        )

        print(f"论文: {paper_path.name}")
        if latex_class:
            print(f"文档类: \\documentclass{{{latex_class}}}")
        if packages:
            print(f"宏包: {', '.join(packages[:10])}")
        print()

        if tpl:
            print(f"✅ 自动匹配: {tpl.name} ({tpl.category})")
            print(f"   描述: {tpl.description}")
        else:
            print("⚠️  未能自动匹配模板")
            print("   可尝试: article-check template list")


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


def cmd_start(args):
    """🎯 交互式一键启动 — 智能体主菜单"""
    import shutil

    setup_logging(args.verbose)
    width = shutil.get_terminal_size().columns

    def banner():
        print()
        print("=" * width)
        title = "  📋 Article Check — 学术论文审查智能体  "
        print(f"  \033[1;36m{title:^{width-4}}\033[0m")
        print(f"  \033[2mv{__version__} | DeepSeek API | 格式+文献+内容审查\033[0m")
        print("=" * width)
        print()

    def check_env():
        """环境检查"""
        status = []
        # API Key
        if config.deepseek.api_key:
            status.append(("✅ DeepSeek API", f"已配置 ({config.deepseek.api_key[:8]}...)"))
        else:
            status.append(("⚠️  DeepSeek API", "未配置 → 仅格式+文献检查"))

        # 模板
        from article_check.rules.registry import template_registry
        n = template_registry.count
        status.append(("📌 格式模板", f"{n} 个内置 ({', '.join(t.name for t in template_registry.list_all()[:3])}...)"))

        # chktex
        try:
            import subprocess
            r = subprocess.run(["chktex", "--version"], capture_output=True, timeout=3)
            chk = "✅ 可用" if r.returncode == 0 else "⚠️  未安装"
        except Exception:
            chk = "⚠️  未安装（使用正则降级）"
        status.append(("🔧 LaTeX chktex", chk))

        # git
        try:
            import subprocess
            r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=3)
            git = f"✅ {r.stdout.strip()}" if r.returncode == 0 else "⚠️  not a repo"
        except Exception:
            git = "⚠️  git not found"
        status.append(("🔖 Git", git))

        for label, val in status:
            print(f"   {label:20s}  {val}")
        print()

    def show_menu() -> str:
        print(f"  ┌────────────────────────────────────────────┐")
        print(f"  │  \033[1m请选择操作\033[0m                                   │")
        print(f"  ├────────────────────────────────────────────┤")
        print(f"  │  \033[1;36m1\033[0m  审查单篇论文                              │")
        print(f"  │  \033[1;36m2\033[0m  批量审查目录                              │")
        print(f"  │  \033[1;36m3\033[0m  格式检查（仅本地规则，零token）            │")
        print(f"  │  \033[1;36m4\033[0m  模板管理                                   │")
        print(f"  │  \033[1;36m5\033[0m  查看配置与环境检查                         │")
        print(f"  │  \033[1;36m6\033[0m  自动检测论文模板                           │")
        print(f"  │  \033[1;31mq\033[0m  退出                                       │")
        print(f"  └────────────────────────────────────────────┘")
        return input("  \033[1m请输入 [1-6/q]:\033[0m ").strip()

    while True:
        banner()
        check_env()
        choice = show_menu()

        if choice == "1":
            path = input("  📄 论文路径: ").strip().strip('"').strip("'")
            if path:
                from pathlib import Path
                p = Path(path)
                if p.exists():
                    print()
                    cmd_review(argparse.Namespace(
                        paper=path, api_key=None, depth="auto", verbose=args.verbose
                    ))
                else:
                    print(f"  ❌ 文件不存在: {p}")
            input("  \n  按回车继续...")

        elif choice == "2":
            path = input("  📁 论文目录: ").strip().strip('"').strip("'")
            if path:
                p = Path(path)
                if p.is_dir():
                    print()
                    cmd_batch(argparse.Namespace(
                        directory=path, api_key=None, concurrent=None,
                        types=["latex", "docx", "pdf"], verbose=args.verbose
                    ))
                else:
                    print(f"  ❌ 目录不存在: {p}")
            input("  \n  按回车继续...")

        elif choice == "3":
            path = input("  📄 论文路径: ").strip().strip('"').strip("'")
            if path:
                p = Path(path)
                if p.exists():
                    print()
                    cmd_format(argparse.Namespace(paper=path, verbose=args.verbose))
                else:
                    print(f"  ❌ 文件不存在: {p}")
            input("  \n  按回车继续...")

        elif choice == "4":
            print()
            from article_check.rules.registry import template_registry
            tpls = template_registry.list_all()
            print(f"  已注册模板 ({len(tpls)}):")
            for i, tpl in enumerate(tpls, 1):
                print(f"    {i}. {tpl.name} [{tpl.category}]")
            sel = input("  \n  查看详情（输入编号，回车返回）: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(tpls):
                import dataclasses, json
                d = dataclasses.asdict(tpls[int(sel) - 1])
                print(json.dumps(d, ensure_ascii=False, indent=2))
            input("  \n  按回车继续...")

        elif choice == "5":
            print()
            cmd_config(None)
            input("  \n  按回车继续...")

        elif choice == "6":
            path = input("  📄 论文路径: ").strip().strip('"').strip("'")
            if path:
                p = Path(path)
                if p.exists():
                    print()
                    cmd_template(argparse.Namespace(
                        action="auto-detect", paper=path, name=None,
                        query=None, template_name=None, verbose=args.verbose
                    ))
                else:
                    print(f"  ❌ 文件不存在: {p}")
            input("  \n  按回车继续...")

        elif choice.lower() == "q":
            print("\n  👋 再见！")
            break

        else:
            print("  ⚠️  无效输入，请输入 1-6 或 q")
            input("  按回车继续...")


def cmd_chat(args):
    """
    💬 自然语言对话模式 — 像聊天一样驱动论文审查与修正
    """
    from article_check.chat import ChatSession
    session = ChatSession(verbose=args.verbose)
    session.run()


def cmd_web(args):
    """启动 Web 图形界面"""
    setup_logging(args.verbose)
    from article_check.web import run_server
    run_server(host=args.host, port=args.port)


def cmd_assist_report(args):
    """基于结构化报告回答追问。"""
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"❌ 报告不存在: {report_path}")
        sys.exit(1)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    answer = answer_report_question(payload, args.question)
    if getattr(args, "json_output", False):
        print(json.dumps({"answer": answer}, ensure_ascii=False, indent=2))
    else:
        print(answer)


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
        description=f"学术论文审查智能体 v{__version__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py                            # 🎯 交互式一键启动
  python run.py paper.tex                  # 直接审查单篇
  python run.py papers/                    # 直接批量审查目录
  python -m article_check start            # 交互式菜单
  python -m article_check review paper.tex # 审查单篇
  python -m article_check batch papers/    # 批量审查
  python -m article_check format paper.tex # 仅格式检查
  python -m article_check template list    # 列出模板
  python -m article_check template check --template-name "IEEE Transactions" --paper paper.tex
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
    p_review.add_argument("--json-output", help="将结构化审查结果输出到 JSON 文件")
    p_review.add_argument("-v", "--verbose", action="store_true")

    # batch
    p_batch = subparsers.add_parser("batch", help="批量审查论文")
    p_batch.add_argument("directory", help="论文目录")
    p_batch.add_argument("--api-key", help="DeepSeek API Key")
    p_batch.add_argument("-c", "--concurrent", type=int, default=None)
    p_batch.add_argument("-t", "--types", nargs="+", default=["latex", "docx", "pdf"])
    p_batch.add_argument("--json-output", help="将批量结构化审查结果输出到 JSON 文件")
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

    # template
    p_template = subparsers.add_parser("template", help="模板管理：list/show/search/check/auto-detect")
    p_template.add_argument("action", choices=["list", "show", "search", "check", "auto-detect"],
                           help="模板操作")
    p_template.add_argument("--name", help="模板名称（show/check 用）")
    p_template.add_argument("--query", help="搜索关键词（search 用）")
    p_template.add_argument("--paper", help="论文路径（check/auto-detect 用）")
    p_template.add_argument("--template-name", help="模板名称（check 用）")
    p_template.add_argument("-v", "--verbose", action="store_true")

    # start — 交互式一键启动
    p_start = subparsers.add_parser("start", help="交互式一键启动 — 智能体主菜单")
    p_start.add_argument("-v", "--verbose", action="store_true")

    # chat — 自然语言对话模式
    p_chat = subparsers.add_parser("chat", help="💬 自然语言对话模式 — 像聊天一样审查/修正论文")
    p_chat.add_argument("-v", "--verbose", action="store_true")

    # web — 图形化界面
    p_web = subparsers.add_parser("web", help="🌐 启动 Web 图形界面 (FastAPI + React)")
    p_web.add_argument("--host", default="127.0.0.1", help="监听地址")
    p_web.add_argument("--port", type=int, default=8765, help="监听端口")
    p_web.add_argument("-v", "--verbose", action="store_true")

    # assist-report — 基于结构化报告回答问题
    p_assist = subparsers.add_parser("assist-report", help="基于结构化审查报告回答追问")
    p_assist.add_argument("report", help="结构化报告 JSON 路径")
    p_assist.add_argument("--question", required=True, help="用户问题")
    p_assist.add_argument("--json-output", action="store_true", help="以 JSON 输出回答")

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
        "template": cmd_template,
        "start": cmd_start,
        "chat": cmd_chat,
        "web": cmd_web,
        "assist-report": cmd_assist_report,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)


if __name__ == "__main__":
    main()
