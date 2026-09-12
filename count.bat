@echo off
:: 设置编码为UTF-8
chcp 65001

:: 执行同目录下的脚本（使用脚本自身位置，避免硬编码绝对路径）
call "%~dp0run_code_count.bat" %*
