#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon CLI 模块
处理命令行参数解析与命令路由
"""
import argparse
import sys
import os
from datetime import datetime

from src.parser import LogParser
from src.query import QueryEngine
from src.stats import StatsEngine
from src.formatter import OutputFormatter
from src.config import Config


# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'  # No Color

USE_COLOR = True


def color(text, c):
    """为文本添加颜色"""
    return f"{c}{text}{NC}" if USE_COLOR else text


def show_banner():
    """显示横幅"""
    banner = f"""
{color('╔═══════════════════════════════════════╗', CYAN)}
{color('║       log-surgeon  🔍  v1.0.0          ║', CYAN)}
{color('║   结构化日志分析与查询工具            ║', CYAN)}
{color('╚═══════════════════════════════════════╝', CYAN)}
"""
    print(banner)


def show_help():
    """显示帮助信息"""
    show_banner()
    print(f"""
{color('用法:', BOLD)} log-surgeon <命令> [选项]

{color('命令:', BOLD)}
  {color('analyze', GREEN)}   分析日志文件结构（自动检测格式）
  {color('parse', GREEN)}    解析日志（指定格式）
  {color('query', GREEN)}    查询/过滤日志
  {color('tail', GREEN)}     实时跟踪日志（带过滤）
  {color('stats', GREEN)}    统计分析

{color('通用选项:', BOLD)}
  -f, --file <path>      日志文件路径（默认: stdin）
  --format <fmt>         日志格式: auto, syslog, json, nginx, apache, glibc, custom
  --config <path>        配置文件路径
  --output <path>        输出文件路径（默认: stdout）
  -h, --help             显示帮助

{color('查询选项 (query/tail):', BOLD)}
  --level <level>        按级别过滤: debug, info, warn, error, fatal
  --regex <pattern>      正则表达式过滤
  --after <time>         起始时间（格式: YYYY-MM-DD HH:MM:SS）
  --before <time>        结束时间（格式: YYYY-MM-DD HH:MM:SS）
  --field <name> <val>   字段过滤（格式: field=value 或 field~=regex）

{color('统计选项 (stats):', BOLD)}
  --top <N>              显示 Top N（默认: 10）
  --field <name>         统计字段（ip, url, status, level 等）
  --group-by <field>     分组字段

{color('导出选项:', BOLD)}
  --export <fmt>         导出格式: text, json, csv

{color('示例:', BOLD)}
  log-surgeon analyze access.log
  log-surgeon query app.log --level error --regex "timeout|database"
  log-surgeon tail /var/log/syslog --level warning
  log-surgeon stats nginx.log --top 20 --field ip
  cat app.log | log-surgeon parse --format json

{color('配置文件:', BOLD)}
  默认读取 ./config/surgeon.conf
  可用 --config 指定其他路径
""")
    print(f"{color('详细文档: https://github.com/chensu1234/log-surgeon', BLUE)}")
    return 0


def cmd_analyze(args, config):
    """分析日志文件结构"""
    if not args.file:
        print(color("[ERROR] 请指定日志文件路径（-f 或 --file）", RED))
        return 1

    if not os.path.exists(args.file):
        print(color(f"[ERROR] 文件不存在: {args.file}", RED))
        return 1

    print(color(f"[*] 分析文件: {args.file}\n", BLUE))

    parser = LogParser(config)
    with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
        all_lines = f.readlines()

    # 总行数
    total_lines = len(all_lines)
    sample_lines = all_lines[:50]

    # 检测格式
    detected = parser.detect_format(args.file)
    print(color("[+] 检测到的格式:", GREEN), detected['format'])
    if detected.get('confidence', 0) < 1.0:
        print(color(f"    可信度: {detected['confidence']:.0%}", YELLOW))
    print()

    # 显示样本行
    print(color("[-] 样本日志行（前10行）:", YELLOW))
    for i, line in enumerate(sample_lines[:10], 1):
        line = line.rstrip('\n')
        print(f"  {i:2d}. {line[:120]}")

    # 尝试解析
    print()
    print(color("[-] 尝试解析（前5行）:", YELLOW))
    parser = LogParser(config, fmt=detected['format'])
    for i, line in enumerate(sample_lines[:5], 1):
        result = parser.parse_line(line.rstrip('\n'))
        if result:
            print(f"  {i:2d}. {result}")
        else:
            print(f"  {i:2d}. {color('[解析失败]', RED)} {line[:80]}")

    # 文件统计
    print()
    print(color(f"[+] 总行数: {total_lines:,}", GREEN))
    print(color(f"[+] 文件大小: {os.path.getsize(args.file):,} bytes", GREEN))

    return 0


def cmd_parse(args, config):
    """解析日志"""
    parser = LogParser(config, fmt=args.format)
    formatter = OutputFormatter(config, fmt=args.export)

    lines = []
    if args.file:
        if not os.path.exists(args.file):
            print(color(f"[ERROR] 文件不存在: {args.file}", RED))
            return 1
        with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    output = formatter.format_lines(parser.parse_lines(lines))
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(color(f"[+] 已导出到: {args.output}", GREEN))
    else:
        print(output)

    return 0


def cmd_query(args, config):
    """查询过滤日志"""
    if not args.file and sys.stdin.isatty():
        print(color("[ERROR] 请指定日志文件（-f）或使用管道输入", RED))
        return 1

    query = QueryEngine(config)

    # 设置查询条件
    if args.level:
        query.add_filter('level', args.level.upper())
    if args.regex:
        query.set_regex(args.regex)
    if args.after:
        query.set_time_range(start=args.after)
    if args.before:
        query.set_time_range(end=args.before)

    # 读取日志
    lines = []
    if args.file:
        if not os.path.exists(args.file):
            print(color(f"[ERROR] 文件不存在: {args.file}", RED))
            return 1
        with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    # 执行查询
    results = query.filter(lines)

    # 格式化输出
    formatter = OutputFormatter(config, fmt=args.export)
    output = formatter.format_lines(results)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(color(f"[+] 找到 {len(results)} 条匹配记录，已导出到: {args.output}", GREEN))
    else:
        if results:
            print(output)
        print(color(f"\n[+] 共匹配 {len(results)} 条记录", GREEN))

    return 0


def cmd_tail(args, config):
    """实时跟踪日志"""
    if not args.file:
        print(color("[ERROR] 请指定日志文件（-f）", RED))
        return 1

    if not os.path.exists(args.file):
        print(color(f"[ERROR] 文件不存在: {args.file}", RED))
        return 1

    print(color(f"[*] 跟踪文件: {args.file}  (Ctrl+C 退出)\n", BLUE))

    query = QueryEngine(config)

    # 设置过滤条件
    if args.level:
        query.add_filter('level', args.level.upper())
    if args.regex:
        query.set_regex(args.regex)

    # 记录初始文件大小
    last_size = os.path.getsize(args.file)

    formatter = OutputFormatter(config, fmt='text')

    try:
        while True:
            current_size = os.path.getsize(args.file)

            if current_size > last_size:
                # 文件有增长，读取新内容
                with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(last_size)
                    new_lines = f.readlines()
                    last_size = current_size

                # 过滤并输出
                results = query.filter(new_lines)
                if results:
                    output = formatter.format_lines(results)
                    print(output, end='')

            import time
            time.sleep(0.5)

    except KeyboardInterrupt:
        print(color("\n[+] 已停止跟踪", GREEN))

    return 0


def cmd_stats(args, config):
    """统计分析"""
    if not args.file:
        if sys.stdin.isatty():
            print(color("[ERROR] 请指定日志文件（-f）或使用管道输入", RED))
            return 1

    lines = []
    if args.file:
        if not os.path.exists(args.file):
            print(color(f"[ERROR] 文件不存在: {args.file}", RED))
            return 1
        with open(args.file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    stats = StatsEngine(config)
    parser = LogParser(config)

    # 解析所有行
    parsed = parser.parse_lines(lines)

    # 执行统计
    if args.field:
        result = stats.top_values(parsed, field=args.field, top_n=args.top)
    else:
        result = stats.summary(parsed)

    # 输出
    formatter = OutputFormatter(config, fmt='text')
    output = formatter.format_stats(result)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(color(f"[+] 统计结果已导出到: {args.output}", GREEN))
    else:
        print(output)

    return 0


def main():
    """主入口"""
    global USE_COLOR

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--config', default='./config/surgeon.conf')
    parser.add_argument('--no-color', action='store_true')

    # 解析已知的顶层参数
    known, remaining = parser.parse_known_args()

    # 加载配置
    config = Config(known.config)

    # 颜色控制
    if known.no_color or not sys.stdout.isatty():
        USE_COLOR = False

    # 子命令解析
    subparsers = argparse.ArgumentParser(add_help=False)
    subparsers.add_argument('command', nargs='?', choices=['analyze', 'parse', 'query', 'tail', 'stats'])
    subparsers.add_argument('-f', '--file', dest='file_path')
    subparsers.add_argument('file_positional', nargs='?', help='Log file ( positional alias for -f )')
    subparsers.add_argument('--format', default='auto')
    subparsers.add_argument('--output')
    subparsers.add_argument('--export', default='text')
    subparsers.add_argument('--config', default=known.config)
    subparsers.add_argument('--level')
    subparsers.add_argument('--regex')
    subparsers.add_argument('--after')
    subparsers.add_argument('--before')
    subparsers.add_argument('--top', type=int, default=10)
    subparsers.add_argument('--field')
    subparsers.add_argument('--group-by')
    subparsers.add_argument('-h', '--help', action='store_true')

    try:
        args = subparsers.parse_args(remaining)
    except SystemExit:
        if '-h' in remaining or '--help' in remaining:
            show_help()
            return 0
        return 1

    # 显示帮助
    if args.help:
        show_help()
        return 0

    # 无命令时显示帮助
    if not args.command:
        show_help()
        return 0

    # 支持 positional 文件参数
    args.file = args.file_path or args.file_positional

    # 加载配置
    config = Config(args.config)

    # 命令路由
    commands = {
        'analyze': cmd_analyze,
        'parse': cmd_parse,
        'query': cmd_query,
        'tail': cmd_tail,
        'stats': cmd_stats,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args, config)

    return 0


if __name__ == '__main__':
    sys.exit(main())
