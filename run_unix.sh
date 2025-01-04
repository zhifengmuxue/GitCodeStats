#!/bin/bash

# 设置默认配置
DEFAULT_PATH="$HOME/project"
DEFAULT_DAYS=1
CONDA_ENV_NAME="code_count"

# 检查是否已安装conda
if ! command -v conda &> /dev/null; then
    echo "错误：未找到conda，请先安装Anaconda或Miniconda"
    exit 1
fi

# 创建并激活conda环境
conda create -n $CONDA_ENV_NAME python=3.8 -y
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $CONDA_ENV_NAME

# 安装依赖
pip install -r requirements.txt

# 运行Python脚本
python codeCount.py -p "$DEFAULT_PATH" -d $DEFAULT_DAYS

# 等待用户输入
read -p "按回车键继续..." 