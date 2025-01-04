@echo off
:: 设置编码为UTF-8
chcp 65001

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0

:: 激活conda环境（替换为你的conda环境名）
call conda activate daily

:: 切换到脚本目录并执行Python脚本
cd /d %SCRIPT_DIR%
python codeCount.py %*

:: 暂停以查看输出
pause 