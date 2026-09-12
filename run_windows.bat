@echo off
setlocal enabledelayedexpansion
:: 读取配置文件中的设置
:: 先初始化为空：for /f 对取不到第 2 个字段的行会跳过（例如 "CONDA_INSTALL_PATH ="），
:: 此时变量未定义，随后的 "%VAR: =%" 去空格会得到垃圾值而不是空字符串
set CONDA_ENV_NAME=
set SETUP_ENV_PATH=
set CONDA_INSTALL_PATH=

for /f "tokens=2 delims==" %%a in ('findstr "CONDA_ENV_NAME" config.ini') do set CONDA_ENV_NAME=%%a
for /f "tokens=2 delims==" %%a in ('findstr "SETUP_ENV_PATH" config.ini') do set SETUP_ENV_PATH=%%a
for /f "tokens=2 delims==" %%a in ('findstr "CONDA_INSTALL_PATH" config.ini') do set CONDA_INSTALL_PATH=%%a

:: 去除变量值前后的空格。
:: 必须先判空：cmd 的 %VAR: =% 替换在变量为空时会产生垃圾值 " =" 而不是空字符串
if not "!CONDA_ENV_NAME!"=="" set "CONDA_ENV_NAME=!CONDA_ENV_NAME: =!"
if not "!SETUP_ENV_PATH!"=="" set "SETUP_ENV_PATH=!SETUP_ENV_PATH: =!"
if not "!CONDA_INSTALL_PATH!"=="" set "CONDA_INSTALL_PATH=!CONDA_INSTALL_PATH: =!"

:: 如果需要配置环境变量
if /i "%SETUP_ENV_PATH%"=="True" (
    echo 正在检查conda环境变量...

    rem 注意：括号块内必须使用 rem 而不是 :: 注释，:: 在块内会被当作标签导致解析错误
    rem 如果未指定conda安装路径，尝试自动检测
    if "!CONDA_INSTALL_PATH!"=="" (
        where conda >nul 2>nul
        if !ERRORLEVEL! NEQ 0 (
            rem 检查常见的Anaconda安装位置
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

    rem 不再自动写入用户环境变量：
    rem 原实现为 setx PATH "%CONDA_INSTALL_PATH%;...;%PATH%"，
    rem 这会把当前会话的整个 PATH 固化进用户环境变量，既可能因 setx 的 1024 字符限制被截断，
    rem 也会让用户之后对 PATH 的修改难以生效。此处改为仅提示，由用户自行决定是否添加。
    echo 提示：为避免覆盖或截断现有 PATH，本脚本不再自动配置环境变量。
    echo       如需在任意目录使用 conda，请手动将以下目录添加到 PATH：
    echo         !CONDA_INSTALL_PATH!
    echo         !CONDA_INSTALL_PATH!\Scripts
    echo         !CONDA_INSTALL_PATH!\Library\bin
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
