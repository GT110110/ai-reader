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
    echo   deploy all      - 上传所有代码 + .env 并重启
    echo   deploy app      - 只更新 app.py
    echo   deploy status   - 查看运行状态
    echo   deploy log      - 查看最近日志
    echo   deploy stop     - 停止服务
    echo   deploy start    - 启动服务
    echo   deploy pull     - 从 GitHub 拉取最新代码并重启
    echo   deploy init     - 首次部署（拉取 + 装依赖）
    echo.
    pause
    exit /b
)

if "%1"=="all" (
    echo [1/2] 上传所有文件...
    scp -i "%PEM%" app.py styles.py shelf.py reader.py book_parser.py prompt.py notes.py reading_log.py requirements.txt .env %HOST%:%APP_DIR%/
    echo [2/2] 重启服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo 完成！
    goto :done
)

if "%1"=="app" (
    echo [1/2] 上传 app.py...
    scp -i "%PEM%" app.py %HOST%:%APP_DIR%/
    echo [2/2] 重启服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo 完成！
    goto :done
)

if "%1"=="pull" (
    echo [1/2] 从 GitHub 拉取最新代码...
    ssh -i "%PEM%" %HOST% "cd %APP_DIR% && git pull"
    echo [2/2] 重启服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo 完成！
    goto :done
)

if "%1"=="init" (
    echo [1/4] 拉取代码...
    ssh -i "%PEM%" "git clone git@github.com:GT110110/ai-reader.git %APP_DIR%"
    echo [2/4] 创建 .env...
    set /p KEY="请输入 DeepSeek API Key: "
    ssh -i "%PEM%" "echo DEEPSEEK_API_KEY=%KEY% > %APP_DIR%/.env"
    ssh -i "%PEM%" "echo DEEPSEEK_BASE_URL=https://api.deepseek.com >> %APP_DIR%/.env"
    echo [3/4] 安装依赖...
    ssh -i "%PEM%" "cd %APP_DIR% && pip install -r requirements.txt"
    echo [4/4] 创建 systemd 服务...
    ssh -i "%PEM%" "cat > /etc/systemd/system/ai-reader.service << 'SERVICEEOF'
[Unit]
Description=AI Reader
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=%APP_DIR%
ExecStart=streamlit run app.py --server.port 8501 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF
systemctl daemon-reload && systemctl enable ai-reader && systemctl restart ai-reader"
    echo 首次部署完成！
    goto :done
)

if "%1"=="status" (
    echo 服务状态：
    ssh -i "%PEM%" %HOST% "systemctl status ai-reader --no-pager -l"
    goto :done
)

if "%1"=="log" (
    echo 最近日志：
    ssh -i "%PEM%" %HOST% "journalctl -u ai-reader --no-pager -n 50"
    goto :done
)

if "%1"=="stop" (
    echo 停止服务...
    ssh -i "%PEM%" %HOST% "systemctl stop ai-reader"
    echo 已停止
    goto :done
)

if "%1"=="start" (
    echo 启动服务...
    ssh -i "%PEM%" %HOST% "systemctl restart ai-reader"
    echo 已启动
    goto :done
)

:done
echo.
pause
