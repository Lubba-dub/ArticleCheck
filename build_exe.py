"""
构建单文件 .exe 包

用法:
    python build_exe.py

依赖:
    pip install pyinstaller

输出:
    dist/ArticleCheck.exe — 双击即用的单文件应用
"""
import os
import sys
import shutil
from pathlib import Path

def main():
    # 检查 PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("❌ 需要 PyInstaller: pip install pyinstaller")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent
    os.chdir(str(project_root))

    # 清理旧构建
    for d in ["build", "dist"]:
        if Path(d).exists():
            shutil.rmtree(d)

    # 构建命令
    cmd = [
        "pyinstaller",
        "--onefile",                    # 单文件
        "--name", "ArticleCheck",       # 输出文件名
        "--console",                    # 窗口模式
        "--add-data", f"knowledge{os.pathsep}knowledge",
        "--add-data", f".claude{os.pathsep}.claude",
        "--add-data", f".env.example{os.pathsep}.",
        "--add-data", f"requirements.txt{os.pathsep}.",
        "--hidden-import", "docx",
        "--hidden-import", "httpx",
        "--hidden-import", "pydantic",
        "--hidden-import", "dotenv",
        "run.py"
    ]

    print("🔨 构建 exe 中...")
    os.system(" ".join(cmd))
    print(f"\n✅ 构建完成: {project_root / 'dist' / 'ArticleCheck.exe'}")
    print(f"   大小: {os.path.getsize(project_root / 'dist' / 'ArticleCheck.exe') / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
