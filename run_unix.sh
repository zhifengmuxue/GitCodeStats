#!/bin/bash

# 读取配置文件
get_config_value() {
    local key=$1
    grep "^$key = " config.ini | cut -d "=" -f2 | tr -d " "
}

CONDA_ENV_NAME=$(get_config_value "CONDA_ENV_NAME")
SETUP_ENV_PATH=$(get_config_value "SETUP_ENV_PATH")
CONDA_INSTALL_PATH=$(get_config_value "CONDA_INSTALL_PATH")

# 如果需要配置环境变量
if [ "$SETUP_ENV_PATH" = "True" ]; then
    echo "正在配置环境变量..."
    
    # 如果未指定conda安装路径，尝试自动检测
    if [ -z "$CONDA_INSTALL_PATH" ]; then
        if [ -d "$HOME/anaconda3" ]; then
            CONDA_INSTALL_PATH="$HOME/anaconda3"
        elif [ -d "$HOME/miniconda3" ]; then
            CONDA_INSTALL_PATH="$HOME/miniconda3"
        else
            echo "错误：未能找到conda安装路径，请在config.ini中手动指定CONDA_INSTALL_PATH"
            exit 1
        fi
    fi

    # 配置环境变量
    echo "export PATH=\"$CONDA_INSTALL_PATH/bin:\$PATH\"" >> ~/.bashrc
    source ~/.bashrc
    echo "环境变量配置完成"
fi

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
python codeCount.py

# 等待用户输入
read -p "按回车键继续..." 