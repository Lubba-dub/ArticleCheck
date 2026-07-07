@echo off
chcp 65001 >nul
title Article Check — Docker 部署助手
echo ================================================
echo   🐳 Article Check Docker 部署助手
echo   论文审查智能体 —— Web 服务容器化部署
echo ================================================
echo.

:: 检查 Docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未运行或未安装！
    echo.
    echo 请先安装 Docker Desktop for Windows:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    echo 安装后确保:
    echo   1. Docker Desktop 正在运行（任务栏图标绿色）
    echo   2. 已启用 WSL2 后端
    echo.
    pause
    exit /b 1
)
echo ✅ Docker 运行中

:: 检查 .env
if not exist .env (
    echo ⚠️  未找到 .env 文件
    if exist .env.docker (
        echo 从 .env.docker 复制模板...
        copy .env.docker .env >nul
        echo ✅ 已创建 .env 文件，请编辑填入 Dify API 配置！
        echo.
        echo 📝 编辑 .env 文件后重新运行此脚本。
        notepad .env
        pause
        exit /b 0
    ) else (
        echo ❌ 缺少 .env 和 .env.docker 文件
        pause
        exit /b 1
    )
)

:: 检查 Dify 配置
findstr /C:"DIFY_API_KEY=app-your" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  DIFY_API_KEY 尚未配置！
    echo 请编辑 .env 文件填入真实 Dify API Key
    notepad .env
    pause
    exit /b 1
)

findstr /C:"DIFY_BASE_URL=http://host.docker.internal/v1" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  DIFY_BASE_URL 仍是模板值！
    echo 请编辑 .env 文件填入真实 Dify 地址
    notepad .env
    pause
    exit /b 1
)

echo.
echo ⏳ 正在构建 Docker 镜像（首次约 5-10 分钟）...
echo.

:: 构建并启动
docker compose build
if %errorlevel% neq 0 (
    echo ❌ 镜像构建失败
    pause
    exit /b 1
)

echo.
echo ⏳ 正在启动服务...
echo.

docker compose up -d
if %errorlevel% neq 0 (
    echo ❌ 服务启动失败
    pause
    exit /b 1
)

echo.
echo ✅ 部署完成！
echo.
echo ================================================
echo   🌐 http://localhost:3000
echo   📚 API 文档: http://localhost:3000/docs
echo   🔍 健康检查: http://localhost:3000/api/health
echo ================================================
echo.
echo 🛑 停止服务: docker compose down
echo 📋 查看日志: docker compose logs -f
echo 🔄 重启: docker compose restart
echo.
pause
