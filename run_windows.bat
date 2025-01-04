@echo off
:: 读取配置文件中的设置
for /f "tokens=2 delims==" %%a in ('findstr "CONDA_ENV_NAME" config.ini') do set CONDA_ENV_NAME=%%a
for /f "tokens=2 delims==" %%a in ('findstr "SETUP_ENV_PATH" config.ini') do set SETUP_ENV_PATH=%%a
for /f "tokens=2 delims==" %%a in ('findstr "CONDA_INSTALL_PATH" config.ini') do set CONDA_INSTALL_PATH=%%a

:: 去除变量值前后的空格
set CONDA_ENV_NAME=%CONDA_ENV_NAME: =%
set SETUP_ENV_PATH=%SETUP_ENV_PATH: =%
set CONDA_INSTALL_PATH=%CONDA_INSTALL_PATH: =%

:: 如果需要配置环境变量
if /i "%SETUP_ENV_PATH%"=="True" (
    echo 正在配置环境变量...
    
    :: 如果未指定conda安装路径，尝试自动检测
    if "%CONDA_INSTALL_PATH%"=="" (
        where conda >nul 2>nul
        if %ERRORLEVEL% NEQ 0 (
            :: 检查常见的Anaconda安装位置
            if exist "%USERPROFILE%\Anaconda3" (
                set CONDA_INSTALL_PATH=%USERPROFILE%\Anaconda3
            ) else if exist "%USERPROFILE%\miniconda3" (
                set CONDA_INSTALL_PATH=%USERPROFILE%\miniconda3
            ) else (
                echo 错误：未能找到conda安装路径，请在config.ini中手动指定CONDA_INSTALL_PATH
                pause
                exit /b 1
            )
        )
    )

    :: 设置环境变量
    setx PATH "%CONDA_INSTALL_PATH%;%CONDA_INSTALL_PATH%\Scripts;%CONDA_INSTALL_PATH%\Library\bin;%PATH%"
    echo 环境变量配置完成
)

:: 检查是否已安装conda
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误：未找到conda，请先安装Anaconda或Miniconda
    pause
    exit /b 1
)

:: 创建并激活conda环境
call conda create -n %CONDA_ENV_NAME% python=3.8 -y
call conda activate %CONDA_ENV_NAME%

:: 安装依赖
pip install -r requirements.txt

:: 运行Python脚本
python codeCount.py

:: 等待用户确认
pause 