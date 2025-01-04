@echo off
:: 设置默认配置
set DEFAULT_PATH=D:/project
set DEFAULT_DAYS=1
set CONDA_ENV_NAME=code_count

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
python codeCount.py -p "%DEFAULT_PATH%" -d %DEFAULT_DAYS%

:: 等待用户确认
pause 