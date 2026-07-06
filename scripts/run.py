"""
一键启动入口 — 项目根目录双击/运行即可

用法:
    python scripts/run.py                  # 交互式菜单
    python scripts/run.py --auto papers/   # 直接批量审查目录
    python scripts/run.py paper.tex        # 直接审查单篇
"""
import sys
from pathlib import Path

# 确保项目在 sys.path 中
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from article_check.cli import main as cli_main

if __name__ == "__main__":
    # 如果传了参数，映射到 CLI
    if len(sys.argv) > 1:
        args = sys.argv[1:]

        # 如果参数是目录或文件，自动判断
        first_arg = Path(args[0])
        if first_arg.exists():
            if first_arg.is_dir():
                # 批量审查
                sys.argv = [sys.argv[0], "batch", str(first_arg)]
            elif first_arg.is_file():
                # 单篇审查
                sys.argv = [sys.argv[0], "review", str(first_arg)]
            else:
                sys.argv = [sys.argv[0]] + args
        else:
            sys.argv = [sys.argv[0]] + args
    else:
        # 无参数 → 启动交互式菜单
        sys.argv = [sys.argv[0], "start"]

    cli_main()
