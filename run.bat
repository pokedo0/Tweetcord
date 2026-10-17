@echo off
setlocal
title Tweetcord Local Management Tool
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

if /i "%~1"=="test" goto RUN_TESTS
if /i "%~1"=="bot" goto RUN_BOT
if /i "%~1"=="install" goto INSTALL_DEPS

:MENU
cls
echo =======================================================
echo          Tweetcord Windows 本机管理工具
echo =======================================================
echo 当前 Python 环境:
python --version 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 并添加到 PATH！
    pause
    exit /b 1
)
echo.
echo [1] 运行单元测试 (pytest)
echo [2] 本机启动 Bot (python bot.py)
echo [3] 安装 / 更新依赖 (requirements.txt)
echo [4] 初始化虚拟环境 (.venv)
echo [0] 退出
echo =======================================================
set "choice="
set /p choice="请输入选项 [0-4]: "

if "%choice%"=="1" goto RUN_TESTS
if "%choice%"=="2" goto RUN_BOT
if "%choice%"=="3" goto INSTALL_DEPS
if "%choice%"=="4" goto INIT_VENV
if "%choice%"=="0" exit /b 0
goto MENU

:RUN_TESTS
echo.
echo [INFO] 正在运行测试套件 (pytest)...
echo.
python -m pytest test
if errorlevel 1 (
    echo.
    echo [WARNING] 部分测试未通过，请检查上方日志。
) else (
    echo.
    echo [SUCCESS] 所有测试全部通过！
)
echo.
if not "%~1"=="" exit /b %errorlevel%
pause
goto MENU

:RUN_BOT
echo.
echo [INFO] 正在检查环境与数据目录...
if not exist ".env" (
    echo [ERROR] 未找到 .env 文件！请先配置 .env
    pause
    goto MENU
)
if not exist "configs.yml" (
    if exist "configs.example.yml" (
        echo [INFO] 未找到 configs.yml，正在从 configs.example.yml 复制...
        copy "configs.example.yml" "configs.yml" >nul
    )
)
if not exist "data" (
    mkdir "data"
)

set "DATA_PATH=./data"
echo [INFO] 本地数据目录: DATA_PATH=%DATA_PATH%
echo [INFO] 正在启动 Tweetcord Bot (按 Ctrl+C 可停止)...
echo.
python bot.py
echo.
if not "%~1"=="" exit /b %errorlevel%
pause
goto MENU

:INSTALL_DEPS
echo.
echo [INFO] 正在安装 / 更新项目依赖...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if exist "requirements-dev.txt" (
    python -m pip install -r requirements-dev.txt
)
echo.
echo [SUCCESS] 依赖安装完成！
echo.
if not "%~1"=="" exit /b 0
pause
goto MENU

:INIT_VENV
echo.
echo [INFO] 正在创建虚拟环境 .venv ...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] 虚拟环境创建失败。
    pause
    goto MENU
)
echo [INFO] 激活虚拟环境并安装依赖...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if exist "requirements-dev.txt" (
    python -m pip install -r requirements-dev.txt
)
echo.
echo [SUCCESS] 虚拟环境创建并安装完成！
echo.
pause
goto MENU
