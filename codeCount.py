import os
import sys
import io
import re
import json
import subprocess
from tqdm import tqdm
from datetime import datetime, timedelta
import argparse
import configparser

# 修复 Windows 控制台中文输出乱码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 版本号
VERSION = "1.0.2"

def load_config():
    """
    加载配置文件
    """
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if os.path.exists(config_path):
        # 必须显式指定 UTF-8：Windows 中文环境的默认编码是 GBK(cp936)，
        # 而本项目的 config.ini 以 UTF-8 保存（含中文注释），
        # 不指定编码会直接抛出 UnicodeDecodeError 导致程序无法启动
        config.read(config_path, encoding='utf-8')
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


def parse_authors(value):
    """
    解析 -u/--user 参数：支持逗号分隔的多个用户名
    :param value: 用户名字符串，如 "张三" 或 "张三,张三_work"
    :return: 用户名列表
    """
    if not value:
        return []
    return [part.strip() for part in str(value).split(',') if part.strip()]


def get_modifications_in_one(auths, path, days=1):
    """
    获取指定作者在指定时间段内的代码增删行数
    :param auths: 作者名列表（多人时任一匹配即统计）
    :param path: 仓库路径
    :param days: 统计的天数，默认为1天
    :return: added_lines, removed_lines 代码增删行数
    """
    # 获取日期
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)  # 今天0:00
    tomorrow = today + timedelta(days=1)  # 明天0:00
    start_date = today - timedelta(days=days-1)  # 统计起始日的0:00

    # 定义要执行的命令（多个 --author 之间是 OR 关系）
    command = ["git", "log"]
    for auth in auths:
        command.append(f"--author={auth}")
    command += [
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

        # errors='replace'：文件名等非 UTF-8 字节不应导致整个统计崩溃
        for line in stdout.decode('utf-8', errors='replace').strip().split('\n'):
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


def get_today_modifications(auths, start_path, days=1, show_progress=True):
    """
    获取指定作者在指定时间段内的代码增删行数
    :param auths:  作者名列表
    :param start_path:  仓库根目录
    :param days: 统计的天数，默认为1天
    :param show_progress: 是否显示进度条，默认为True
    :return:  tuple(int, int) 返回代码增加行数和删除行数
    """
    # 查找所有 Git 仓库
    git_repos = find_git_repos(start_path)

    # 统计今天的总增改量
    total_added = 0
    total_removed = 0

    for repo in tqdm(git_repos, disable=not show_progress):
        added, removed = get_modifications_in_one(auths, repo, days)
        total_added += added
        total_removed += removed

    return total_added, total_removed


def get_git_username(path):
    command = ["git", "config", "--get", "user.name"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path)
    stdout, _ = process.communicate()

    if process.returncode == 0:
        return stdout.decode('utf-8', errors='replace').strip()
    else:
        return None


def get_git_identity(path):
    """
    读取 Git 身份（user.name + user.email），用于报告中自动识别"自己"
    :param path: 执行 git config 的目录（一般传扫描根目录，可读到全局配置）
    :return: (name, email)，读取失败时为 (None, None)
    """
    def _read(key):
        command = ["git", "config", "--get", key]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path)
        stdout, _ = process.communicate()
        if process.returncode == 0:
            return stdout.decode('utf-8', errors='replace').strip()
        return None

    return _read("user.name"), _read("user.email")


# ============================================================
# 以下为可视化报告相关功能：
#   - 采集所有仓库的提交明细（作者/邮箱/日期/增删行数）
#   - 身份合并（同邮箱、同 GitHub 数字 ID、名字归一化）
#   - 生成单文件 HTML 报告（Contributor 风格 / 柱状图 / 饼图，可导出 PNG）
# ============================================================

# 形近字符归一化表：把常见替代写法（Sh1Zuku -> shizuku）折叠为同一形式，
# 用于把同一个人的多个提交身份合并到一起
_AUTHOR_CHAR_MAP = str.maketrans({
    '1': 'i', '0': 'o', '3': 'e', '4': 'a', '5': 's', '7': 't',
})


def norm_author_name(name):
    """
    归一化作者名：小写、形近字符折叠、去掉常见分隔符
    """
    return (name or '').lower().translate(_AUTHOR_CHAR_MAP)\
        .replace(' ', '').replace('_', '').replace('.', '').replace('-', '')


def github_noreply_id(email):
    """
    从 GitHub noreply 邮箱中提取用户数字 ID
    例：125943630+someuser@users.noreply.github.com -> '125943630'
    """
    m = re.match(r'^(\d+)\+', (email or '').strip())
    return m.group(1) if m else None


# 常用文件扩展名 -> 语言名映射（用于报告的"语言视图"）。
# 只收录常见语言；未收录的扩展名统一归入"其他"，无扩展名文件不参与统计。
LANG_EXT_MAP = {
    'py': 'Python', 'pyw': 'Python', 'pyi': 'Python',
    'js': 'JavaScript', 'mjs': 'JavaScript', 'cjs': 'JavaScript', 'jsx': 'JavaScript',
    'ts': 'TypeScript', 'tsx': 'TypeScript', 'mts': 'TypeScript',
    'vue': 'Vue', 'svelte': 'Svelte', 'astro': 'Astro',
    'java': 'Java', 'kt': 'Kotlin', 'kts': 'Kotlin', 'scala': 'Scala', 'groovy': 'Groovy',
    'c': 'C', 'cpp': 'C++', 'cc': 'C++', 'cxx': 'C++', 'hpp': 'C++', 'hh': 'C++',
    'h': 'C/C++ Header',
    'cs': 'C#', 'go': 'Go', 'rs': 'Rust', 'rb': 'Ruby', 'php': 'PHP', 'swift': 'Swift',
    'dart': 'Dart', 'lua': 'Lua', 'r': 'R', 'pl': 'Perl', 'pm': 'Perl',
    'sh': 'Shell', 'bash': 'Shell', 'zsh': 'Shell', 'bat': 'Batchfile', 'cmd': 'Batchfile',
    'ps1': 'PowerShell', 'psm1': 'PowerShell',
    'html': 'HTML', 'htm': 'HTML', 'css': 'CSS', 'scss': 'SCSS', 'sass': 'Sass', 'less': 'Less',
    'sql': 'SQL', 'json': 'JSON', 'json5': 'JSON', 'yaml': 'YAML', 'yml': 'YAML',
    'toml': 'TOML', 'ini': 'INI', 'cfg': 'INI', 'conf': 'INI', 'properties': 'INI', 'xml': 'XML',
    'md': 'Markdown', 'markdown': 'Markdown', 'rst': 'reStructuredText', 'txt': 'Text',
    'ipynb': 'Jupyter Notebook',
    'ex': 'Elixir', 'exs': 'Elixir', 'erl': 'Erlang', 'hs': 'Haskell', 'clj': 'Clojure',
    'fs': 'F#', 'vb': 'Visual Basic', 'asm': 'Assembly', 's': 'Assembly',
    'tex': 'TeX', 'proto': 'Protocol Buffers', 'gradle': 'Gradle', 'cmake': 'CMake',
    'jl': 'Julia', 'nim': 'Nim', 'zig': 'Zig', 'sol': 'Solidity', 'pas': 'Pascal',
}

# 无扩展名但常见的特殊文件名
LANG_FILE_MAP = {
    'makefile': 'Makefile', 'gnumakefile': 'Makefile', 'dockerfile': 'Dockerfile',
    'cmakelists.txt': 'CMake', 'rakefile': 'Ruby', 'gemfile': 'Ruby',
    'cargo.lock': 'TOML',
}


def file_language(path):
    """
    根据文件路径判断语言；无法判断时返回 None
    （numstat 中的路径可能带引号转义或 "old => new" 重命名形式，这里做尽力解析）
    """
    if not path:
        return None
    p = path.strip()
    if p.startswith('"') and p.endswith('"'):
        p = p[1:-1]
    if '=>' in p:
        # 重命名：取新路径一侧
        p = p.split('=>')[-1]
    p = p.replace('{', '').replace('}', '').strip()
    base = os.path.basename(p).lower()
    ext = os.path.splitext(base)[1].lstrip('.')
    if not ext:
        return LANG_FILE_MAP.get(base)
    return LANG_EXT_MAP.get(ext, '其他')


def collect_commits(repo_paths, days=1, show_progress=True):
    """
    采集所有仓库在统计时间段内的提交明细（所有作者）
    :param repo_paths: 仓库路径列表
    :param days: 统计天数
    :param show_progress: 是否显示进度条
    :return: dict[(repo_name, author_name, author_email)] = {
                 'add': 新增行数, 'del': 删除行数,
                 'weekly': {周一日期: [新增, 删除], ...},
                 'commits': 提交数,
             }
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    start_date = today - timedelta(days=days-1)

    sep = '\x01'
    raw = {}

    for repo_path in tqdm(repo_paths, disable=not show_progress):
        repo_name = os.path.basename(repo_path.rstrip('/\\')) or repo_path
        command = [
            "git", "log",
            f"--since={start_date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"--until={tomorrow.strftime('%Y-%m-%d %H:%M:%S')}",
            "--numstat",
            f"--pretty=format:{sep}%an{sep}%ae{sep}%aI",
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=repo_path)
        stdout, _ = process.communicate()
        if process.returncode != 0:
            continue

        current = None
        commit_dt = today
        for line in stdout.decode('utf-8', errors='replace').split('\n'):
            if line.startswith(sep):
                parts = line.split(sep)
                if len(parts) >= 4:
                    current = (repo_name, parts[1], parts[2])
                    try:
                        commit_dt = datetime.fromisoformat(parts[3])
                    except ValueError:
                        commit_dt = today
                    rec = raw.get(current)
                    if rec is None:
                        rec = raw[current] = {
                            'add': 0, 'del': 0,
                            'weekly': {},
                            'langs': {},
                            'hours': [[0, 0, 0] for _ in range(24)],
                            'commits': 0,
                        }
                    rec['commits'] += 1
                    # 小时分布：按提交者本地时间的整点，[提交数, 新增, 删除]
                    if 0 <= commit_dt.hour < 24:
                        rec['hours'][commit_dt.hour][0] += 1
            elif line.strip() and current:
                cols = line.split('\t')
                if len(cols) >= 2 and cols[0].lstrip('-').isdigit():
                    added = int(cols[0]) if cols[0] != '-' else 0
                    removed = int(cols[1]) if cols[1] != '-' else 0
                    rec = raw[current]
                    rec['add'] += added
                    rec['del'] += removed
                    monday = commit_dt - timedelta(days=commit_dt.weekday())
                    week = monday.date().isoformat()
                    week_pair = rec['weekly'].setdefault(week, [0, 0])
                    week_pair[0] += added
                    week_pair[1] += removed
                    if 0 <= commit_dt.hour < 24:
                        rec['hours'][commit_dt.hour][1] += added
                        rec['hours'][commit_dt.hour][2] += removed
                    lang = file_language(cols[2] if len(cols) > 2 else '')
                    if lang:
                        lang_rec = rec['langs'].setdefault(lang, {'add': 0, 'del': 0, 'weekly': {}})
                        lang_rec['add'] += added
                        lang_rec['del'] += removed
                        lang_week = lang_rec['weekly'].setdefault(week, [0, 0])
                        lang_week[0] += added
                        lang_week[1] += removed

    return raw


def merge_identities(raw):
    """
    把同一个人的多个提交身份（不同名字/邮箱）合并成组。
    合并规则（尽量合并）：
      1. 邮箱完全相同
      2. GitHub noreply 邮箱中的数字 ID 相同
      3. 作者名归一化后相同（如 Shizuku / Sh1Zuku）
    :param raw: collect_commits 的返回值
    :return: (find, names_by_root)
        find(identity) -> 组根；names_by_root[根] = {作者名: 提交数}
    """
    identities = list({(name, email) for (_, name, email) in raw.keys()})
    parent = {ident: ident for ident in identities}

    def find(ident):
        while parent[ident] != ident:
            parent[ident] = parent[parent[ident]]
            ident = parent[ident]
        return ident

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_email, by_gid, by_norm = {}, {}, {}
    for name, email in identities:
        by_email.setdefault((email or '').strip().lower(), []).append((name, email))
        gid = github_noreply_id(email)
        if gid:
            by_gid.setdefault(gid, []).append((name, email))
        by_norm.setdefault(norm_author_name(name), []).append((name, email))

    for bucket in (by_email, by_gid, by_norm):
        for group in bucket.values():
            for i in range(1, len(group)):
                union(group[0], group[i])

    names_by_root = {}
    for (_, name, email), rec in raw.items():
        root = find((name, email))
        names = names_by_root.setdefault(root, {})
        names[name] = names.get(name, 0) + rec['commits']

    return find, names_by_root


def match_self_identities(identities, hints, find):
    """
    找出"自己"的身份组。
    :param identities: 所有 (作者名, 邮箱)
    :param hints: 判定线索列表 [(名字, 邮箱或None)]，如 [('Shizuku', 'xx@qq.com')]
                  邮箱为空时只按名字匹配
    :param find: merge_identities 返回的 find 函数
    :return: (self_roots 集合, 匹配到的身份名列表)
    """
    roots = set()
    matched_names = []
    for name, email in identities:
        for hint_name, hint_email in hints:
            hit = norm_author_name(name) == norm_author_name(hint_name)
            if not hit and hint_email and email:
                if email.strip().lower() == hint_email.strip().lower():
                    hit = True
                else:
                    gid_a, gid_b = github_noreply_id(email), github_noreply_id(hint_email)
                    if gid_a and gid_b and gid_a == gid_b:
                        hit = True
            if hit:
                roots.add(find((name, email)))
                matched_names.append(name)
                break
    return roots, sorted(set(matched_names))


def _accumulate(dst, key, rec):
    """把单条提交记录累加进聚合表"""
    d = dst.get(key)
    if d is None:
        d = dst[key] = {'add': 0, 'del': 0, 'commits': 0, 'weekly': {}}
    d['add'] += rec['add']
    d['del'] += rec['del']
    d['commits'] += rec['commits']
    for week, pair in rec['weekly'].items():
        w = d['weekly'].setdefault(week, [0, 0])
        w[0] += pair[0]
        w[1] += pair[1]


def _accumulate_langs(dst, langs):
    """把单条记录的“按语言”数据累加进语言聚合表"""
    for lang, d in langs.items():
        entry = dst.get(lang)
        if entry is None:
            entry = dst[lang] = {'add': 0, 'del': 0, 'weekly': {}}
        entry['add'] += d['add']
        entry['del'] += d['del']
        for week, pair in d['weekly'].items():
            w = entry['weekly'].setdefault(week, [0, 0])
            w[0] += pair[0]
            w[1] += pair[1]


def _new_hours():
    """24 小时分布容器：每小时 [提交数, 新增行数, 删除行数]"""
    return [[0, 0, 0] for _ in range(24)]


def _accumulate_hours(dst, hours):
    """把单条记录的小时分布累加进聚合表"""
    for h in range(24):
        if h < len(hours):
            dst[h][0] += hours[h][0]
            dst[h][1] += hours[h][1]
            dst[h][2] += hours[h][2]


def build_report_payload(raw, find, names_by_root, self_roots, weeks, top_n=15):
    """
    生成报告数据：人员视图（byUser）、仓库视图（byRepo）、语言视图（byLang）、
    时间分布（hours），各含全部/仅自己两组
    """
    agg_users, agg_repos, agg_langs = {}, {}, {}
    agg_hours = _new_hours()
    agg_users_self, agg_repos_self, agg_langs_self = {}, {}, {}
    agg_hours_self = _new_hours()
    for (repo, name, email), rec in raw.items():
        root = find((name, email))
        _accumulate(agg_users, root, rec)
        _accumulate(agg_repos, repo, rec)
        _accumulate_langs(agg_langs, rec.get('langs', {}))
        _accumulate_hours(agg_hours, rec.get('hours', []))
        if root in self_roots:
            _accumulate(agg_users_self, root, rec)
            _accumulate(agg_repos_self, repo, rec)
            _accumulate_langs(agg_langs_self, rec.get('langs', {}))
            _accumulate_hours(agg_hours_self, rec.get('hours', []))

    def to_week_list(weekly):
        return [[weekly.get(week, (0, 0))[0], weekly.get(week, (0, 0))[1]] for week in weeks]

    def user_rows(agg, top=None):
        rows = []
        for root, d in agg.items():
            names = names_by_root.get(root, {})
            rep = max(names.items(), key=lambda kv: kv[1])[0] if names else '(未知)'
            rows.append({
                'name': rep,
                'add': d['add'], 'del': d['del'], 'commits': d['commits'],
                'sources': sorted(names.keys()),
                'w': to_week_list(d['weekly']),
            })
        rows.sort(key=lambda r: r['add'] + r['del'], reverse=True)
        return rows[:top] if top else rows

    def repo_rows(agg):
        rows = []
        for repo_name, d in agg.items():
            rows.append({
                'name': repo_name,
                'add': d['add'], 'del': d['del'], 'commits': d['commits'],
                'w': to_week_list(d['weekly']),
            })
        rows.sort(key=lambda r: r['add'] + r['del'], reverse=True)
        return rows

    def lang_rows(agg):
        rows = []
        for lang, d in agg.items():
            rows.append({
                'name': lang,
                'add': d['add'], 'del': d['del'],
                'w': to_week_list(d['weekly']),
            })
        rows.sort(key=lambda r: r['add'] + r['del'], reverse=True)
        return rows

    return {
        'all': {
            'byUser': user_rows(agg_users, top_n),
            'byRepo': repo_rows(agg_repos),
            'byLang': lang_rows(agg_langs),
            'hours': agg_hours,
        },
        'self': {
            'byUser': user_rows(agg_users_self),
            'byRepo': repo_rows(agg_repos_self),
            'byLang': lang_rows(agg_langs_self),
            'hours': agg_hours_self,
        },
    }


REPORT_TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>代码贡献统计</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #f6f8fa; margin: 0; padding: 24px 16px; color: #1f2328; }
  .wrap { max-width: 1320px; margin: 0 auto; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .meta { color: #656d76; font-size: 12px; margin: 0 0 14px; }
  .controls { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; font-size: 13px; }
  button { font-family: inherit; font-size: 12px; padding: 4px 10px; border: 1px solid #d0d7de; background: #fff; border-radius: 6px; cursor: pointer; color: #1f2328; }
  button:hover { background: #f3f4f6; }
  button.on { background: #1f883d; border-color: #1f883d; color: #fff; }
  button.png { background: #0969da; border-color: #0969da; color: #fff; }
  button.png:hover { background: #0860c4; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  @media (max-width: 1100px) { .cols { grid-template-columns: 1fr; } }
  .panel { background: #fff; border: 1px solid #d0d7de; border-radius: 8px; padding: 14px 16px 16px; }
  .panel-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  .panel-head h2 { font-size: 15px; margin: 0; flex: none; }
  .views { display: flex; gap: 4px; margin-left: auto; }
  .chart svg { display: block; width: 100%; height: auto; }
  .empty { color: #656d76; font-size: 13px; padding: 30px 0; text-align: center; }
  .hint { color: #9a6700; font-size: 12px; margin: 0 0 12px; }
</style></head><body>
<div class="wrap">
  <h1>代码贡献统计</h1>
  <p class="meta" id="meta-line"></p>
  <p class="hint" id="hint-line" style="display:none"></p>
  <div class="controls">
    <span>统计范围：</span>
    <button class="scope-btn" data-scope="all">全部人</button>
    <button class="scope-btn" data-scope="self">仅自己（已合并身份）</button>
  </div>
  <div class="cols">
    <section class="panel">
      <div class="panel-head">
        <h2>人员视图</h2>
        <div class="views" data-dim="user">
          <button data-view="contributor" class="on">Contributor 风格</button>
          <button data-view="bar">柱状图</button>
          <button data-view="pie">饼图</button>
        </div>
        <button class="png" data-dim="user">导出 PNG</button>
      </div>
      <div class="chart" id="chart-user"></div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <h2>仓库视图</h2>
        <div class="views" data-dim="repo">
          <button data-view="contributor" class="on">Contributor 风格</button>
          <button data-view="bar">柱状图</button>
          <button data-view="pie">饼图</button>
        </div>
        <button class="png" data-dim="repo">导出 PNG</button>
      </div>
      <div class="chart" id="chart-repo"></div>
    </section>
  </div>
  <div class="cols" style="margin-top:18px">
    <section class="panel">
      <div class="panel-head">
        <h2>语言视图</h2>
        <button class="png" data-dim="lang" style="margin-left:auto">导出 PNG</button>
      </div>
      <div class="chart" id="chart-lang"></div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <h2>时间分布（按小时）</h2>
        <button class="png" data-dim="hours">导出 PNG</button>
      </div>
      <div class="chart" id="chart-hours"></div>
    </section>
  </div>
</div>
<script>
const NS = 'http://www.w3.org/2000/svg';
const META = __META__;
const DATA = __DATA__;
const FONT = "'Segoe UI', 'Microsoft YaHei', -apple-system, sans-serif";
const MONO = "Consolas, 'Courier New', monospace";
const ADD_COLORS = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'];
const DEL_COLORS = ['#ebedf0', '#ffd7d5', '#ff8182', '#fa4549', '#cf222e'];
const PALETTE = ['#2ea44f', '#3572A5', '#e34c26', '#6f42c1', '#bf8700', '#1b7c83', '#8250df', '#953800', '#116329', '#a40e26', '#0550ae', '#7d4e00'];

const state = { scope: META.defaultScope, user: 'contributor', repo: 'contributor' };

function el(tag, attrs, text) {
  const e = document.createElementNS(NS, tag);
  if (attrs) { for (const k in attrs) { e.setAttribute(k, attrs[k]); } }
  if (text !== undefined && text !== null) { e.textContent = text; }
  return e;
}

function fmt(n) { return Number(n).toLocaleString('en-US'); }

function clip(s, n) { return s.length > n ? s.slice(0, n - 1) + '…' : s; }

function clipW(s, maxUnits) {
  // 按显示宽度裁剪：中日韩等全角字符按 2 个宽度单位计，避免中文名溢出到图表区域
  let units = 0, out = '';
  for (const ch of s) {
    const w = (ch.charCodeAt(0) > 0x2E7F) ? 2 : 1;
    if (units + w > maxUnits) { return out + '…'; }
    units += w; out += ch;
  }
  return out;
}

function levelOf(t) {
  if (t <= 0) return 0;
  if (t < 50) return 1;
  if (t < 200) return 2;
  if (t < 1000) return 3;
  return 4;
}

function baseTitle(svg, title, subtitle) {
  svg.appendChild(el('text', { x: 0, y: 16, 'font-size': 15, 'font-weight': 600, fill: '#1f2328', 'font-family': FONT }, title));
  svg.appendChild(el('text', { x: 0, y: 34, 'font-size': 11, fill: '#656d76', 'font-family': FONT }, subtitle));
}

function renderContributor(chart, rows, opts) {
  const W = 620, rowH = 22, headH = 50;
  const H = headH + rows.length * rowH + 8;
  const svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'font-family': FONT });
  baseTitle(svg, opts.title, opts.subtitle);
  const cellW = 15, cellH = 15, gap = 3, x0 = 150;
  rows.forEach(function (row, i) {
    const y = headH + i * rowH;
    let nameTxt = clipW(row.name, 22);
    if (row.sources && row.sources.length > 1) { nameTxt += ' *'; }
    const t = el('text', { x: 0, y: y + 14, 'font-size': 12, fill: '#1f2328', 'font-family': FONT }, nameTxt);
    if (row.sources && row.sources.length > 1) {
      t.appendChild(el('title', {}, '合并身份: ' + row.sources.join('、')));
    }
    svg.appendChild(t);
    for (let wi = 0; wi < row.w.length; wi++) {
      const pair = row.w[wi];
      const v = pair[0] + pair[1];
      let fill = '#ebedf0';
      if (v > 0) { fill = (pair[0] >= pair[1] ? ADD_COLORS : DEL_COLORS)[levelOf(v)]; }
      const rect = el('rect', { x: x0 + wi * (cellW + gap), y: y, width: cellW, height: cellH, rx: 2, fill: fill });
      rect.appendChild(el('title', {}, '周 ' + META.weeks[wi] + ': +' + pair[0] + ' / -' + pair[1]));
      svg.appendChild(rect);
    }
    svg.appendChild(el('text', { x: W - 80, y: y + 14, 'font-size': 11.5, fill: '#1a7f37', 'text-anchor': 'end', 'font-family': MONO }, '+' + fmt(row.add)));
    svg.appendChild(el('text', { x: W - 4, y: y + 14, 'font-size': 11.5, fill: '#cf222e', 'text-anchor': 'end', 'font-family': MONO }, '-' + fmt(row.del)));
  });
  chart.innerHTML = '';
  chart.appendChild(svg);
}

function renderBar(chart, rows, opts) {
  const W = 620, rowH = 26, headH = 50;
  const H = headH + rows.length * rowH + 8;
  const svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'font-family': FONT });
  baseTitle(svg, opts.title, opts.subtitle);
  const x0 = 150, barW = 300;
  let maxV = 1;
  rows.forEach(function (r) { maxV = Math.max(maxV, r.add, r.del); });
  rows.forEach(function (row, i) {
    const y = headH + i * rowH;
    svg.appendChild(el('text', { x: 0, y: y + 15, 'font-size': 12, fill: '#1f2328', 'font-family': FONT }, clipW(row.name, 22)));
    const wa = Math.max(2, row.add / maxV * barW);
    const wd = Math.max(2, row.del / maxV * barW);
    svg.appendChild(el('rect', { x: x0, y: y + 2, width: wa.toFixed(1), height: 10, rx: 2, fill: '#40c463' }));
    svg.appendChild(el('rect', { x: x0, y: y + 14, width: wd.toFixed(1), height: 10, rx: 2, fill: '#fa4549' }));
    svg.appendChild(el('text', { x: W - 80, y: y + 15, 'font-size': 11.5, fill: '#1a7f37', 'text-anchor': 'end', 'font-family': MONO }, '+' + fmt(row.add)));
    svg.appendChild(el('text', { x: W - 4, y: y + 15, 'font-size': 11.5, fill: '#cf222e', 'text-anchor': 'end', 'font-family': MONO }, '-' + fmt(row.del)));
  });
  chart.innerHTML = '';
  chart.appendChild(svg);
}

function renderPie(chart, rows, opts) {
  const W = 620, headH = 50;
  const CX = 155, CY = headH + 130, R = 115;
  let items = rows.slice();
  if (items.length > 10) {
    const rest = items.slice(9);
    const other = { name: '其他 ' + rest.length + ' 项', add: 0, del: 0 };
    rest.forEach(function (r) { other.add += r.add; other.del += r.del; });
    items = items.slice(0, 9).concat([other]);
  }
  let total = 0;
  items.forEach(function (r) { total += r.add + r.del; });
  if (total <= 0) { chart.innerHTML = '<div class="empty">无数据</div>'; return; }
  const H = Math.max(headH + 300, headH + 20 + items.length * 22) + 8;
  const svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'font-family': FONT });
  baseTitle(svg, opts.title, opts.subtitle);
  let angle = -Math.PI / 2;
  items.forEach(function (row, i) {
    const v = row.add + row.del;
    const frac = v / total;
    const color = PALETTE[i % PALETTE.length];
    if (frac > 0.9999) {
      const c = el('circle', { cx: CX, cy: CY, r: R, fill: color, stroke: '#ffffff', 'stroke-width': 1 });
      c.appendChild(el('title', {}, row.name + ': 100%'));
      svg.appendChild(c);
    } else {
      const a2 = angle + frac * Math.PI * 2;
      const big = (frac > 0.5) ? 1 : 0;
      const x1 = CX + R * Math.cos(angle), y1 = CY + R * Math.sin(angle);
      const x2 = CX + R * Math.cos(a2), y2 = CY + R * Math.sin(a2);
      const d = 'M ' + CX + ' ' + CY + ' L ' + x1.toFixed(2) + ' ' + y1.toFixed(2) +
                ' A ' + R + ' ' + R + ' 0 ' + big + ' 1 ' + x2.toFixed(2) + ' ' + y2.toFixed(2) + ' Z';
      const p = el('path', { d: d, fill: color, stroke: '#ffffff', 'stroke-width': 1 });
      p.appendChild(el('title', {}, row.name + ': ' + (frac * 100).toFixed(1) + '%'));
      svg.appendChild(p);
      angle = a2;
    }
    const ly = headH + 10 + i * 22;
    const lx = 312;
    svg.appendChild(el('rect', { x: lx, y: ly, width: 11, height: 11, rx: 2, fill: color }));
    svg.appendChild(el('text', { x: lx + 17, y: ly + 10, 'font-size': 12, fill: '#1f2328', 'font-family': FONT }, clipW(row.name, 18)));
    svg.appendChild(el('text', { x: W - 4, y: ly + 10, 'font-size': 11, fill: '#656d76', 'text-anchor': 'end', 'font-family': MONO },
      (frac * 100).toFixed(1) + '%  +' + fmt(row.add) + ' / -' + fmt(row.del)));
  });
  chart.innerHTML = '';
  chart.appendChild(svg);
}

function renderHours(chart, hours, opts) {
  const W = 620, headH = 50, plotH = 200;
  const H = headH + plotH + 48;
  let totalC = 0, maxC = 0, peak = 0;
  hours.forEach(function (h, i) {
    totalC += h[0];
    if (h[0] > maxC) { maxC = h[0]; peak = i; }
  });
  if (totalC === 0) { chart.innerHTML = '<div class="empty">无数据</div>'; return; }
  const svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'font-family': FONT });
  baseTitle(svg, opts.title, opts.subtitle);
  const x0 = 24, bw = 17, gap = 7, baseY = headH + plotH;
  svg.appendChild(el('line', { x1: 14, y1: baseY, x2: W - 14, y2: baseY, stroke: '#d0d7de', 'stroke-width': 1 }));
  hours.forEach(function (h, i) {
    const x = x0 + i * (bw + gap);
    const bh = h[0] > 0 ? Math.max(3, Math.round(h[0] / maxC * (plotH - 14))) : 2;
    const rect = el('rect', {
      x: x, y: baseY - bh, width: bw, height: bh, rx: 2,
      fill: h[0] > 0 ? '#40c463' : '#ebedf0'
    });
    rect.appendChild(el('title', {}, i + ' 点: ' + h[0] + ' 次提交, +' + fmt(h[1]) + ' / -' + fmt(h[2])));
    svg.appendChild(rect);
    if (i % 2 === 0) {
      svg.appendChild(el('text', { x: x + bw / 2, y: baseY + 15, 'font-size': 10, fill: '#656d76', 'text-anchor': 'middle', 'font-family': MONO }, String(i)));
    }
  });
  svg.appendChild(el('text', { x: W - 14, y: baseY + 32, 'font-size': 10, fill: '#656d76', 'text-anchor': 'end', 'font-family': FONT },
    '峰值 ' + peak + ' 点 · ' + hours[peak][0] + ' 次提交 · 共 ' + totalC + ' 次'));
  chart.innerHTML = '';
  chart.appendChild(svg);
}

function exportPNG(dim) {
  const chart = document.getElementById('chart-' + dim);
  const svg = chart.querySelector('svg');
  if (!svg) { return; }
  const vb = svg.viewBox.baseVal;
  const W = vb.width, H = vb.height;
  const clone = svg.cloneNode(true);
  clone.setAttribute('xmlns', NS);
  clone.setAttribute('width', W);
  clone.setAttribute('height', H);
  const svgText = new XMLSerializer().serializeToString(clone);
  const blob = new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n' + svgText], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const img = new Image();
  img.onload = function () {
    const scale = 2;
    const canvas = document.createElement('canvas');
    canvas.width = W * scale;
    canvas.height = H * scale;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);
    canvas.toBlob(function (b) {
      const a = document.createElement('a');
      const dl = URL.createObjectURL(b);
      a.href = dl;
      const FILE_NAMES = { user: '人员贡献视图', repo: '仓库贡献视图', lang: '语言贡献视图', hours: '提交时间分布' };
      a.download = (FILE_NAMES[dim] || dim) + '-' + META.stamp + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(dl); }, 3000);
    }, 'image/png');
  };
  img.src = url;
}

function currentRows(dim) {
  const scope = DATA[state.scope];
  if (dim === 'user') { return scope.byUser; }
  if (dim === 'repo') { return scope.byRepo; }
  return scope.byLang;
}

function scopeText() {
  if (state.scope === 'all') { return '全部贡献者'; }
  const names = (META.selfNames && META.selfNames.length) ? META.selfNames.join('、') : '未匹配到身份';
  return '仅自己（' + names + '）';
}

function subtitleFor(dim) {
  if (dim === 'hours') {
    return META.range + ' · ' + scopeText() + ' · 按提交者本地时间统计';
  }
  const n = currentRows(dim).length;
  let unit;
  if (dim === 'user') {
    const total = META.allUserCount || n;
    unit = (total > n) ? ('展示前 ' + n + ' 位（共 ' + total + ' 位）') : ('共 ' + n + ' 位贡献者');
  } else if (dim === 'repo') {
    unit = '共 ' + n + ' 个仓库';
  } else {
    unit = '共 ' + n + ' 种语言/文件类型';
  }
  return META.range + ' · ' + scopeText() + ' · ' + unit;
}

function renderDim(dim) {
  const chart = document.getElementById('chart-' + dim);
  if (dim === 'hours') {
    renderHours(chart, DATA[state.scope].hours, { title: '提交时间分布', subtitle: subtitleFor('hours') });
    return;
  }
  const rows = currentRows(dim);
  if (!rows.length) { chart.innerHTML = '<div class="empty">该范围下无数据</div>'; return; }
  const titles = { user: '人员贡献视图', repo: '仓库贡献视图', lang: '语言贡献视图' };
  const opts = { title: titles[dim] || dim, subtitle: subtitleFor(dim) };
  if (dim === 'lang') { renderPie(chart, rows, opts); return; }  // 语言视图固定使用饼图
  const view = state[dim];
  if (view === 'contributor') { renderContributor(chart, rows, opts); }
  else if (view === 'bar') { renderBar(chart, rows, opts); }
  else { renderPie(chart, rows, opts); }
}

function renderAll() { renderDim('user'); renderDim('repo'); renderDim('lang'); renderDim('hours'); }

document.querySelectorAll('.views').forEach(function (group) {
  const dim = group.dataset.dim;
  group.querySelectorAll('button').forEach(function (btn) {
    btn.addEventListener('click', function () {
      state[dim] = btn.dataset.view;
      group.querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b === btn); });
      renderDim(dim);
    });
  });
});

document.querySelectorAll('.png').forEach(function (btn) {
  btn.addEventListener('click', function () { exportPNG(btn.dataset.dim); });
});

document.querySelectorAll('.scope-btn').forEach(function (btn) {
  if (btn.dataset.scope === state.scope) { btn.classList.add('on'); }
  btn.addEventListener('click', function () {
    state.scope = btn.dataset.scope;
    document.querySelectorAll('.scope-btn').forEach(function (b) { b.classList.toggle('on', b === state.scope); });
    renderAll();
  });
});

document.getElementById('meta-line').textContent =
  '统计范围 ' + META.range + '（' + META.days + ' 天） · 扫描 ' + META.repoCount + ' 个仓库 · 生成于 ' + META.generated;

if (META.hint) {
  const hintEl = document.getElementById('hint-line');
  hintEl.textContent = META.hint;
  hintEl.style.display = '';
}

renderAll();
</script>
</body></html>'''


def render_report_html(payload, meta):
    """把数据与元信息填入 HTML 模板"""
    data_js = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    meta_js = json.dumps(meta, ensure_ascii=False).replace('</', '<\\/')
    return REPORT_TEMPLATE.replace('__DATA__', data_js).replace('__META__', meta_js)


def generate_report(repo_path, days, user_value, all_users, output_file, show_progress=True):
    """
    生成 HTML 可视化报告
    :return: 报告统计结果 dict（供命令行输出）
    """
    repo_paths = find_git_repos(repo_path)
    if not repo_paths:
        print(f"错误: 在 {repo_path} 下没有找到任何 Git 仓库")
        return None

    print(f"共找到 {len(repo_paths)} 个 Git 仓库，正在采集提交数据……")
    raw = collect_commits(repo_paths, days=days, show_progress=show_progress)
    if not raw:
        print("警告: 统计范围内没有任何提交记录")

    find, names_by_root = merge_identities(raw)
    identities = list({(name, email) for (_, name, email) in raw.keys()})

    # 确定"自己"的身份线索：-u 参数优先，其次读取 git 配置
    hints = []
    hint_desc = ""
    author_list = parse_authors(user_value)
    if author_list:
        hints = [(name, None) for name in author_list]
        hint_desc = "、".join(author_list) + "（来自 -u 参数）"
    else:
        git_name, git_email = get_git_identity(repo_path)
        if git_name:
            hints = [(git_name, git_email)]
            hint_desc = git_name + (f" <{git_email}>" if git_email else "") + "（来自 git 配置）"

    self_roots, matched_names = match_self_identities(identities, hints, find) if hints else (set(), [])

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=days-1)

    weeks = []
    monday = start_date - timedelta(days=start_date.weekday())
    while monday.date() <= now.date():
        weeks.append(monday.date().isoformat())
        monday += timedelta(days=7)
    # 时间轴最多显示最近 104 周（两年），避免超长统计范围下图表过密；
    # 仅影响 Contributor 视图的周格子显示，不影响任何总量统计
    MAX_WEEKS = 104
    if len(weeks) > MAX_WEEKS:
        weeks = weeks[-MAX_WEEKS:]

    payload = build_report_payload(raw, find, names_by_root, self_roots, weeks)

    hint = ""
    if not hints:
        hint = "提示: 未指定用户名（-u），且未能从 git 配置读取身份，\"仅自己\"视图为空。可用 -u 参数指定用户名。"
    elif not matched_names:
        hint = f"提示: 未能在提交记录中匹配到身份（{hint_desc}），\"仅自己\"视图为空。可用 -u 参数指定实际使用的提交用户名。"

    meta = {
        'weeks': weeks,
        'days': days,
        'range': f'{start_date.date()} ~ {now.date()}',
        'stamp': now.strftime('%Y%m%d'),
        'generated': now.strftime('%Y-%m-%d %H:%M'),
        'repoCount': len(repo_paths),
        'selfNames': matched_names,
        'defaultScope': 'all' if all_users else 'self',
        'allUserCount': len(names_by_root),
        'hint': hint,
    }

    html = render_report_html(payload, meta)
    out_path = os.path.abspath(output_file)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    user_rows_all = payload['all']['byUser']
    self_total = {'add': 0, 'del': 0, 'commits': 0}
    for row in payload['self']['byUser']:
        self_total['add'] += row['add']
        self_total['del'] += row['del']
        self_total['commits'] += row['commits']

    return {
        'report_path': out_path,
        'repo_count': len(repo_paths),
        'user_count': len(user_rows_all),
        'self_names': matched_names,
        'hint_desc': hint_desc,
        'self_total': self_total,
        'hint': hint,
    }


if __name__ == '__main__':
    # 加载配置
    config = load_config()
    default_path = (config.get('DEFAULT_PATH') or '').strip()

    # 读取是否显示进度条（兼容大小写与多余空格）
    show_progress = str(config.get('SHOW_PROGRESS', 'True')).strip().lower() in ('true', '1', 'yes', 'on')

    # 读取默认天数（配置非法或为空时回退为 1）
    default_days = str(config.get('DEFAULT_DAYS', '1')).strip()
    if not default_days or not default_days.isdigit():
        default_days = '1'
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='统计Git仓库代码修改行数')
    parser.add_argument('-p', '--path', default=default_path,
                       help='指定要统计的根目录路径，未指定时读取 config.ini 中的 DEFAULT_PATH')
    parser.add_argument('-d', '--days', type=int, default=int(default_days),
                       help='指定要统计的天数，默认为1天')
    parser.add_argument('-u', '--user', default=config.get('GIT_USERNAME'),
                       help='指定Git用户名，支持逗号分隔多个；不指定则使用仓库配置的用户名')
    parser.add_argument('--report', default=None, metavar='FILE',
                       help='生成 HTML 可视化报告到指定文件（浏览器打开，图表可导出 PNG）')
    parser.add_argument('--all-users', action='store_true',
                       help='报告中统计全部贡献者（默认只统计自己或 -u 指定的用户）')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}',
                       help='显示版本号并退出')
    
    args = parser.parse_args()
    
    try:
        # 处理路径格式
        repo_path = (args.path or '').strip().replace("\\", "/")
        if not repo_path:
            print("错误：未指定统计路径，请使用 -p 参数指定，或在 config.ini 中设置 DEFAULT_PATH")
            exit(1)

        if args.all_users and not args.report:
            print("提示：--all-users 仅在配合 --report 生成报告时生效，本次将按普通模式统计。")

        if args.report:
            # ---------- 可视化报告模式 ----------
            result = generate_report(repo_path, args.days, args.user, args.all_users,
                                     args.report, show_progress)
            if result is None:
                exit(1)

            print(f"统计范围: 最近 {args.days} 天")
            if result['self_names']:
                print(f"自己: {result['hint_desc']}")
                print(f"  匹配到 {len(result['self_names'])} 个身份: {'、'.join(result['self_names'])}")
                print(f"  总代码增加量: {result['self_total']['add']}, 总代码删除量: {result['self_total']['del']}")
            print(f"共 {result['user_count']} 位贡献者、{result['repo_count']} 个仓库")
            if result['hint']:
                print(result['hint'])
            print(f"HTML 报告已生成: {result['report_path']}")
            print("用浏览器打开报告查看图表，图表右上角可导出 PNG。")
        else:
            # ---------- 普通统计模式（与原有行为一致）----------
            # 获取用户名
            author_list = parse_authors(args.user)
            if not author_list:
                git_name = get_git_username(repo_path)
                if git_name:
                    author_list = [git_name]
            if not author_list:
                print("错误：未能获取Git用户名，请使用 -u 参数指定用户名")
                exit(1)

            # 获取统计结果
            added, removed = get_today_modifications(author_list, repo_path, args.days, show_progress)
            print("用户: ", "、".join(author_list))
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
