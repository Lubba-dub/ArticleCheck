"""
🏁 一键启动入口 — 项目根目录双击或运行

用法:
    python run.py                  # 交互式菜单
    python run.py path/to/paper    # 直接审查论文
    python run.py path/to/dir/     # 直接批量审查目录
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from article_check.cli import main as cli_main

if __name__ == "__main__":
    if len(sys.argv) > 1:
        first = Path(sys.argv[1])
        if first.exists():
            if first.is_dir():
                sys.argv = [sys.argv[0], "batch", str(first)]
            else:
                sys.argv = [sys.argv[0], "review", str(first)]
        else:
            sys.argv = [sys.argv[0]] + sys.argv[1:]
    else:
        sys.argv = [sys.argv[0], "start"]
    cli_main()
