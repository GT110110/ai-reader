@echo off
chcp 65001 >nul
title AI Reader 部署

set PEM=E:\桌面文件\aireader.pem
set HOST=root@47.97.6.154
set APP_DIR=/opt/ai-reader

echo ========================================
echo   AI Reader - 部署脚本
echo ========================================
echo.

if "%1"=="" (
    echo 用法:
    echo   deploy all    - 上传所有代码并重启
    echo   deploy app     - 只更新 app.py
    echo   deploy status  - 查看运行状态
    echo   deploy log     - 查看最近日志
    echo   deploy stop    - 停止服务
    echo   deploy start   - 启动服务
    echo   deploy pull    - 从 GitHub 拉取并重启
    echo.
    pause
    exit /b
)

if "%1"=="all" (
    echo 📤 上传所有文件...
    scp -i "%PEM%" app.py shelf.py reader.py book_parser.py prompt.py notes.py reading_log.py requirements.txt .env %HOST%:%APP_DIR%/
    echo 🔄 重启服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo ✅ 完成！
)

if "%1"=="app" (
    echo 📤 上传 app.py...
    scp -i "%PEM%" app.py %HOST%:%APP_DIR%/
    echo 🔄 重启服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo ✅ 完成！
)

if "%1"=="status" (
    echo 🔍 服务状态：
    ssh -i "%PEM%" %HOST% "systemctl status ai-reader --no-pager -l"
)

if "%1"=="log" (
    echo 📋 最近日志：
    ssh -i "%PEM%" %HOST% "journalctl -u ai-reader --no-pager -n 30"
)

if "%1"=="stop" (
    echo ⏹ 停止服务...
    ssh -i "%PEM%" %HOST% "systemctl stop ai-reader"
    echo ✅ 已停止
)

if "%1"=="start" (
    echo ▶ 启动服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo ✅ 已启动
)

if "%1"=="pull" (
    echo 📥 从 GitHub 拉取...
    ssh -i "%PEM%" %HOST% "cd %APP_DIR% && git pull && systemctl restart ai-reader"
    echo ✅ 完成！
)

echo.
pause
