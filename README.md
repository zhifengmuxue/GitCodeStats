# Git代码统计工具

一个简单但功能强大的Git代码统计工具，可以帮助你统计指定时间范围内的代码增删行数。

## 功能特点

- 🔍 支持扫描多个Git仓库
- 📅 自定义统计时间范围
- 👥 支持指定Git用户名
- 📊 实时显示统计进度
- ⚙️ 支持配置文件自定义设置
- 🖥️ 跨平台支持（Windows/Linux/Mac）

## 使用前提

在使用本工具前，请确保你的系统已安装：

1. [Anaconda](https://www.anaconda.com/download) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
2. [Git](https://git-scm.com/downloads)

## 快速开始

### 1. 下载项目

```bash
git clone https://github.com/zhifengmuxue/GitCodeStats.git
cd GitCodeStats
```

### 2. 配置设置

打开 `config.ini` 文件，根据需要修改以下配置：

```ini
[DEFAULT]
# 设置要扫描的项目根目录
DEFAULT_PATH = D:/project

# 设置默认统计天数
DEFAULT_DAYS = 1

# 设置conda环境名称
CONDA_ENV_NAME = code_count

# 是否显示进度条
SHOW_PROGRESS = True

# Git用户名（可选）
GIT_USERNAME = 

# 是否配置环境变量（True/False）
SETUP_ENV_PATH = True

# conda安装路径（可选，留空则自动检测）
CONDA_INSTALL_PATH = 
```

### 3. 运行工具

#### Windows用户：

1. 双击运行 `run_windows.bat`
2. 等待环境配置完成
3. 查看统计结果

#### Linux/Mac用户：

1. 打开终端，进入项目目录
2. 执行以下命令：
```bash
chmod +x run_unix.sh
./run_unix.sh
```

### 4. 命令行高级用法

如果你需要更灵活的控制，可以直接使用命令行参数：

```bash
# 基本用法
python codeCount.py

# 指定项目路径和统计天数
python codeCount.py -p "D:/你的项目路径" -d 7

# 指定Git用户名
python codeCount.py -u "你的Git用户名"

# 组合使用
python codeCount.py -p "D:/项目路径" -d 30 -u "用户名"
```

参数说明：
- `-p` 或 `--path`：指定要统计的项目根目录
- `-d` 或 `--days`：指定要统计的天数
- `-u` 或 `--user`：指定Git用户名

## 常见问题

### 1. 找不到conda命令
确保已正确安装Anaconda或Miniconda，并将其添加到系统环境变量中。

### 2. 统计结果为0
可能的原因：
- Git用户名配置不正确
- 指定的时间范围内没有提交记录
- 项目路径设置错误

### 3. 权限不足
在Linux/Mac上运行时，确保已经给予运行脚本的执行权限：
```bash
chmod +x run_unix.sh
```

## 工作原理

1. 工具会递归扫描指定目录下的所有Git仓库
2. 使用git log命令获取指定用户在指定时间范围内的代码变更
3. 统计每个仓库的代码增删行数
4. 汇总显示最终结果

## 目录结构

```
project/
├── codeCount.py      # 主程序
├── config.ini        # 配置文件
├── requirements.txt  # Python依赖
├── run_windows.bat   # Windows启动脚本
├── run_unix.sh      # Linux/Mac启动脚本
└── README.md        # 说明文档
```

## 注意事项

1. 首次运行时会自动创建conda环境并安装依赖，可能需要一些时间
2. 确保有足够的磁盘空间用于创建conda环境
3. 统计大型项目或多个仓库时可能需要较长时间
4. 建议定期更新工具以获取最新功能

## 贡献指南

欢迎提交Issue和Pull Request来帮助改进这个工具！

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 更新日志

### v1.0.0 (2025-01-03)
- 首次发布
- 支持多仓库统计
- 添加配置文件支持
- 提供跨平台运行脚本
- 添加环境变量配置

### 环境变量配置

在`config.ini`中，你可以设置是否自动配置环境变量：

- `SETUP_ENV_PATH`: 设置为True时会自动配置conda环境变量
- `CONDA_INSTALL_PATH`: 可以手动指定conda的安装路径（可选）

注意：
- 首次配置环境变量可能需要重启终端才能生效
- Windows用户可能需要以管理员权限运行脚本才能设置环境变量
- 如果conda已在PATH中，可以将`SETUP_ENV_PATH`设置为False
