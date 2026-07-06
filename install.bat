@echo off
chcp 65001 >nul
title Article Check — 论文审查智能体 一键安装
echo ================================================
echo   📋 Article Check v0.1.0 一键安装
echo   学术论文格式审查与文献审查系统
echo ================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python，请先安装 Python 3.10+
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set pyver=%%i
echo ✅ Python 版本: %pyver%

:: 检查 pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 pip
    pause
    exit /b 1
)
echo ✅ pip 就绪

echo.
echo ⏳ 正在安装依赖（首次可能需要 2-5 分钟）...
echo.

:: 安装项目及其依赖
pip install -e . 2>&1 | findstr /V "already satisfied"
if %errorlevel% neq 0 (
    echo ⚠️  安装过程有警告，继续...
)

:: 安装可选依赖
echo.
echo ⏳ 安装可选依赖（Word/PDF 支持）...
pip install python-docx pymupdf pdfplumber 2>&1 | findstr /V "already satisfied"

:: 创建 .env 文件（如不存在）
if not exist .env (
    echo.
    echo ⚠️  未检测到 .env 文件
    echo 是否配置 DeepSeek API Key？（可跳过，但内容审查需要）
    set /p apikey="输入 API Key（回车跳过）: "
    if not "!apikey!"=="" (
        echo DEEPSEEK_API_KEY=!apikey!> .env
        echo ✅ API Key 已保存
    ) else (
        echo ⚠️  已跳过，内容审查仅在配置 API Key 后可用
    )
)

echo.
echo ✅ 安装完成！
echo.
echo 🚀 快速启动：
echo    python run.py          — 交互式菜单
echo    python run.py chat     — 对话模式（推荐）
echo    python run.py help     — 帮助
echo.
echo 📖 查看完整文档: https://github.com/Lubba-dub/ArticleCheck
echo.
pause
