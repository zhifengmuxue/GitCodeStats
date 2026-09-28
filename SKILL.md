---
name: git-code-stats
description: Use when the user wants to count git commit lines (added/removed) across repositories, asks about code contribution stats, or wants a visual contribution report with charts (Contributor-style / bar / pie, exportable as PNG)
---

# Git Code Stats

## Overview

扫描目录下所有 Git 仓库，统计指定作者（或全部作者）在指定时间范围内的代码增删行数，基于 `git log --numstat`。除文本统计外，还可生成单文件 HTML 可视化报告：人员 / 仓库 / 语言 / 提交时间分布四类视图，图表可一键导出 PNG。

## When to Use

- "统计代码量"、"看看我这周写了多少行"、"git 贡献统计"
- 按作者、时间范围汇总多个仓库的增删行数
- "生成代码贡献报告/图表"、"把统计导出成图片"（使用 `--report`）
- 按语言看代码增删、看提交时间分布（在报告内）

## When NOT to Use

- 只查单个仓库 → `git log --stat`
- 统计非 Git 目录（没有提交历史）的文件行数 → 用 cloc/tokei
- GitHub/GitLab 平台上的贡献图 → 用平台 API

## Usage

```bash
python <skill-dir>/codeCount.py -p "项目根目录" -d 7 -u "用户名"
```

生成可视化报告（HTML 图表，浏览器打开，可导出 PNG）：

```bash
python <skill-dir>/codeCount.py -p "项目根目录" -d 30 --report report.html
python <skill-dir>/codeCount.py -p "项目根目录" -d 30 --report report.html --all-users
```

## Parameters

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p` | 项目根目录（扫描其下所有 Git 仓库） | config.ini `DEFAULT_PATH` |
| `-d` | 统计天数（从今天往前推） | `1` |
| `-u` | Git 用户名（支持逗号分隔多个） | `git config user.name` |
| `--report` | 生成 HTML 可视化报告到指定文件 | 不生成 |
| `--all-users` | 报告中统计全部贡献者 | 只统计自己 |

## Config

编辑 `<skill-dir>/config.ini` 设置默认路径、天数、用户名、进度条开关。

## Requirements

Python 3.8+、`tqdm`、Git 在 PATH 中。报告为纯静态单文件，导出 PNG 在浏览器端完成，无额外依赖。

## Common Mistakes

| 问题 | 原因 | 解决 |
|------|------|------|
| `python` 打开应用商店 | Windows Store 空壳 stub | 用 `conda run -n <env> python` 或指定完整路径 |
| 结果为 0 | 用户名不匹配 | `git log --format='%an'` 确认作者名 |
| 结果为 0 | 时间范围内无提交 | 扩大 `-d` 天数 |
| `FileNotFoundError` | 路径错误 | 检查 `-p` 参数 |
| 中文乱码 | Windows 编码 | 脚本已自动处理 UTF-8 |
| 报告"仅自己"为空 | 提交署名与 `-u`/git 配置不一致 | `git log --format='%an'` 看实际署名，再用 `-u "署名1,署名2"` 指定 |
| 导出 PNG 无反应 | 在编辑器里预览而不是用浏览器 | 用浏览器打开报告，点图表右上角"导出 PNG" |
