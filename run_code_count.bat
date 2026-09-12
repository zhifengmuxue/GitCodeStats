@echo off
setlocal enabledelayedexpansion
:: 设置编码为UTF-8
chcp 65001

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0

:: 切换到脚本目录（便于读取 config.ini）
cd /d %SCRIPT_DIR%

:: 从 config.ini 读取 conda 环境名，避免与配置不一致
set CONDA_ENV_NAME=
for /f "tokens=2 delims==" %%a in ('findstr "CONDA_ENV_NAME" config.ini') do set CONDA_ENV_NAME=%%a

:: 去除变量值前后的空格（先判空：cmd 的 %VAR: =% 在变量为空时会产生垃圾值）
if not "!CONDA_ENV_NAME!"=="" set "CONDA_ENV_NAME=!CONDA_ENV_NAME: =!"

:: 激活conda环境
call conda activate %CONDA_ENV_NAME%

:: 执行Python脚本
python codeCount.py %*

:: 暂停以查看输出
pause
