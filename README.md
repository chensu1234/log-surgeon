# log-surgeon 🔍

> 结构化日志分析与查询工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-green.svg)](https://github.com/)

一个强大且实用的日志分析工具，支持多格式解析、灵活过滤和统计分析。

## ✨ 特性

- 🚀 支持多种日志格式：Syslog、JSON、Nginx、Apache、GLIBC、Custom
- 🔍 强大的查询表达式（支持正则、字段提取、时间范围）
- 📊 统计分析：Top N、频率分析、分布图
- 🏃 交互式尾部模式，实时过滤新日志
- 📤 导出为 CSV / JSON / Text
- 🎯 零配置智能格式检测
- 🔧 可配置、可扩展

## 🏃 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/chensu1234/log-surgeon.git
cd log-surgeon

# 安装依赖
pip install -r requirements.txt

# 添加执行权限
chmod +x bin/log-surgeon
```

### 基本用法

```bash
# 分析单个日志文件
./bin/log-surgeon analyze access.log

# 从标准输入读取
cat app.log | ./bin/log-surgeon parse --format json

# 过滤 error 级别日志
./bin/log-surgeon query app.log --level error

# 正则过滤
./bin/log-surgeon query app.log --regex "timeout|failed"

# 实时跟踪并过滤
./bin/log-surgeon tail app.log --level warning

# 统计 Top N
./bin/log-surgeon stats app.log --top 10 --field ip

# 组合过滤：时间范围 + 级别 + 关键词
./bin/log-surgeon query app.log --level error --after "2026-04-01 00:00:00" --regex "database"
```

## ⚙️ 配置

编辑 `config/surgeon.conf` 文件：

```ini
[default]
# 默认日志格式
format = auto          # auto, syslog, json, nginx, apache, glibc, custom

# 时间格式（用于解析时间戳）
time_format = %Y-%m-%d %H:%M:%S

# 超时时间（秒）
timeout = 5

# 输出颜色
color = true

[parser]
# 自定义正则（用于 custom 格式）
pattern = ^(?P<timestamp>\S+\s+\S+)\s+(?P<level>\w+)\s+(?P<message>.*)$

[output]
# 默认导出格式
export_format = text   # text, json, csv

# 日志行数限制（0 = 无限制）
limit = 1000
```

## 📋 命令行选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `analyze` | 分析日志文件结构 | - |
| `parse` | 解析日志（使用指定格式） | - |
| `query` | 查询/过滤日志 | - |
| `tail` | 实时跟踪日志（带过滤） | - |
| `stats` | 统计分析 | - |
| `-f, --file` | 日志文件路径 | stdin |
| `--format` | 日志格式 | auto |
| `--level` | 按级别过滤 | - |
| `--regex` | 正则表达式过滤 | - |
| `--after` | 起始时间 | - |
| `--before` | 结束时间 | - |
| `--top` | Top N 统计数 | 10 |
| `--field` | 统计字段 | - |
| `--export` | 导出格式 | text |
| `--output` | 输出文件路径 | stdout |
| `--config` | 配置文件路径 | ./config/surgeon.conf |
| `-h, --help` | 显示帮助 | - |

## 📁 项目结构

```
log-surgeon/
├── bin/
│   └── log-surgeon              # 主入口脚本
├── config/
│   ├── surgeon.conf             # 主配置文件
│   └── formats/                 # 格式定义
│       └── patterns.conf
├── log/                         # 日志目录（默认）
│   └── .gitkeep
├── samples/                     # 示例日志
│   └── sample.log
├── src/
│   ├── __init__.py
│   ├── cli.py                   # 命令行接口
│   ├── parser.py                # 日志解析器
│   ├── query.py                 # 查询引擎
│   ├── stats.py                 # 统计分析
│   ├── formatter.py             # 输出格式化
│   └── config.py                # 配置管理
├── tests/
│   └── test_parser.py           # 单元测试
├── README.md
├── LICENSE
└── requirements.txt
```

## 📝 示例日志

`samples/sample.log` 包含用于测试的示例数据。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 👤 作者

Chen Su
