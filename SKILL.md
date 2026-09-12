---
name: git-code-stats
description: Use when the user wants to count git commit lines (added/removed) across repositories, or asks about code contribution stats
---

# Git Code Stats

## Overview

扫描目录下所有 Git 仓库，统计指定作者在指定时间范围内的代码增删行数。基于 `git log --numstat`。

## When to Use

- "统计代码量"、"看看我这周写了多少行"、"git 贡献统计"
- 按作者、时间范围汇总多个仓库的增删行数

## When NOT to Use

- 只查单个仓库 → `git log --stat`
- 按文件类型/语言分类 → 用 cloc/tokei
- GitHub/GitLab 贡献图 → 用平台 API

## Usage

```bash
python <skill-dir>/codeCount.py -p "项目根目录" -d 7 -u "用户名"
```

## Parameters

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p` | 项目根目录（扫描其下所有 Git 仓库） | config.ini `DEFAULT_PATH` |
| `-d` | 统计天数（从今天往前推） | `1` |
| `-u` | Git 用户名 | `git config user.name` |

## Config

编辑 `<skill-dir>/config.ini` 设置默认路径、天数、用户名、进度条开关。

## Requirements

Python 3.8+、`tqdm`、Git 在 PATH 中。

## Common Mistakes

| 问题 | 原因 | 解决 |
|------|------|------|
| `python` 打开应用商店 | Windows Store 空壳 stub | 用 `conda run -n <env> python` 或指定完整路径 |
| 结果为 0 | 用户名不匹配 | `git log --format='%an'` 确认作者名 |
| 结果为 0 | 时间范围内无提交 | 扩大 `-d` 天数 |
| `FileNotFoundError` | 路径错误 | 检查 `-p` 参数 |
| 中文乱码 | Windows 编码 | 脚本已自动处理 UTF-8 |
