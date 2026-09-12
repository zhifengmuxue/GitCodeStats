# 更新日志

## [Unreleased]

### 修复
- 修复 Windows 中文环境（系统默认编码 GBK/cp936）下读取 UTF-8 的 `config.ini` 抛出 `UnicodeDecodeError`、工具完全无法启动的问题；`config.read()` 显式指定 `encoding='utf-8'`
- 修复 `run_windows.bat` 使用 `setx PATH "...;%PATH%"` 覆盖并固化用户 PATH 的问题（可能触发 setx 的 1024 字符截断），改为提示用户手动配置
- 修复 `run_windows.bat` 在括号块内使用 `::` 注释导致的批处理解析错误（运行时会输出 `The system cannot find the drive specified.`，并造成 if/else 分支错乱）
- 修复 `run_windows.bat` 与 `run_code_count.bat` 中去空格语句在变量为空时产生垃圾值 `" ="`、导致空值判断失效的问题；改为先判空再去空格
- 修复 `run_windows.bat` 在括号块内提前展开 `%ERRORLEVEL%`、导致 conda 检测与自动定位分支判断失效的问题；改用延迟展开
- 修复 `count.bat` 硬编码作者本机绝对路径（`E:\tools\script\run_code_count.bat`）导致其他用户无法使用的问题
- 修复 `run_code_count.bat` 硬编码 conda 环境名（`daily`）与 `config.ini` 中 `CONDA_ENV_NAME` 不一致的问题
- 修复 `SHOW_PROGRESS` 配置项被定义但从未生效的问题
- 修复未指定统计路径时抛出 `AttributeError`、只显示“发生未知错误”的问题，改为给出明确提示

### 变更
- `config.ini` 移除作者本机私有默认值（扫描路径、Git 用户名、conda 安装路径），改为留空或中性默认值
- `codeCount.py` 中未被使用且与文档不一致的 `VERSION` 常量对齐为 1.0.2，并新增 `-v/--version` 参数
- README 补充不使用 conda 的最小运行方式

## [v1.0.1] - 2024-03-xx

### 新增
- 添加环境变量自动配置功能
- 支持通过配置文件设置是否配置环境变量
- 添加.gitignore文件

### 修复
- 修复Windows系统下路径处理问题
- 修复配置文件读取时的空格处理问题

### 变更
- 优化启动脚本
- 改进README文档

## [v1.0.0] - 2024-03-xx

### 新增
- 支持多Git仓库代码统计
- 支持自定义统计时间范围
- 添加配置文件支持
- 提供Windows和Unix系统启动脚本
- 自动环境配置功能

### 修复
- 无

### 变更
- 首次发布
