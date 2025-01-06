import os
import subprocess
from tqdm import tqdm
from datetime import datetime, timedelta
import argparse
import configparser

# 版本号
VERSION = "1.0.1"

def load_config():
    """
    加载配置文件
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if os.path.exists(config_path):
        config.read(config_path)
        return config['DEFAULT']
    else:
        # 返回默认配置
        return {
            'DEFAULT_PATH': 'D:/project',
            'DEFAULT_DAYS': '1',
            'CONDA_ENV_NAME': 'code_count',
            'SHOW_PROGRESS': 'True',
            'GIT_USERNAME': ''
        }


def find_git_repos(start_path):
    """
    查找指定路径下的所有 Git 仓库
    :param start_path: 根目录
    :return: Git 仓库列表
    """
    if not os.path.exists(start_path):
        raise FileNotFoundError(f"路径不存在: {start_path}")
    if not os.path.isdir(start_path):
        raise NotADirectoryError(f"指定路径不是目录: {start_path}")

    git_repos = []
    try:
        for root, dirs, _ in os.walk(start_path):
            if '.git' in dirs:
                git_repos.append(root)
                dirs.remove('.git')
    except PermissionError as e:
        print(f"警告: 无法访问部分目录，权限不足: {e}")
    except Exception as e:
        print(f"警告: 遍历目录时出现错误: {e}")
    
    return git_repos


def get_modifications_in_one(auth, path, days=1):
    """
    获取指定作者在指定时间段内的代码增删行数
    :param auth: 作者名
    :param path: 仓库路径
    :param days: 统计的天数，默认为1天
    :return: added_lines, removed_lines 代码增删行数
    """
    # 获取日期
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # 今天0:00
    tomorrow = today + timedelta(days=1)  # 明天0:00
    start_date = today - timedelta(days=days-1)  # 统计起始日的0:00

    # 定义要执行的命令
    command = [
        "git", "log",
        f"--author={auth}",
        f"--since={start_date.strftime('%Y-%m-%d %H:%M:%S')}",
        f"--until={tomorrow.strftime('%Y-%m-%d %H:%M:%S')}",
        "--pretty=tformat:",
        "--numstat"
    ]

    # 使用 subprocess 执行命令，并指定仓库路径
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path)
    stdout, _ = process.communicate()

    # 处理输出
    if process.returncode == 0:
        added_lines = 0
        removed_lines = 0

        for line in stdout.decode('utf-8').strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != '-' else 0
                    removed = int(parts[1]) if parts[1] != '-' else 0
                    added_lines += added
                    removed_lines += removed
                except ValueError:
                    # 如果转换失败，跳过这行
                    continue

        return added_lines, removed_lines
    else:
        return 0, 0  # 返回零行数以防止后续处理错误


def get_today_modifications(auth, start_path, days=1):
    """
    获取指定作者在指定时间段内的代码增删行数
    :param auth:  作者名
    :param start_path:  仓库根目录
    :param days: 统计的天数，默认为1天
    :return:  tuple(int, int) 返回代码增加行数和删除行数
    """
    # 查找所有 Git 仓库
    git_repos = find_git_repos(start_path)

    # 统计今天的总增改量
    total_added = 0
    total_removed = 0

    for repo in tqdm(git_repos):
        added, removed = get_modifications_in_one(auth, repo, days)
        total_added += added
        total_removed += removed

    return total_added, total_removed


def get_git_username(path):
    command = ["git", "config", "--get", "user.name"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path)
    stdout, _ = process.communicate()

    if process.returncode == 0:
        return stdout.decode('utf-8').strip()
    else:
        return None


if __name__ == '__main__':
    # 加载配置
    config = load_config()
    default_path = config.get('DEFAULT_PATH')
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='统计Git仓库代码修改行数')
    parser.add_argument('-p', '--path', default=default_path,
                       help=f'指定要统计的根目录路径，默认为 {default_path}')
    parser.add_argument('-d', '--days', type=int, default=int(config.get('DEFAULT_DAYS')),
                       help='指定要统计的天数，默认为1天')
    parser.add_argument('-u', '--user', default=config.get('GIT_USERNAME'),
                       help='指定Git用户名，如果不指定则使用仓库配置的用户名')
    
    args = parser.parse_args()
    
    try:
        # 处理路径格式
        repo_path = args.path.replace("\\", "/")
        
        # 获取用户名
        auth = args.user if args.user else get_git_username(repo_path)
        if not auth:
            print("错误：未能获取Git用户名，请使用 -u 参数指定用户名")
            exit(1)
            
        # 获取统计结果
        added, removed = get_today_modifications(auth, repo_path, args.days)
        print("用户: ", auth)
        print(f"总代码增加量: {added}, 总代码删除量: {removed}")
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        exit(1)
    except NotADirectoryError as e:
        print(f"错误: {e}")
        exit(1)
    except Exception as e:
        print(f"发生未知错误: {e}")
        exit(1)
