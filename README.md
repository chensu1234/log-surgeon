# log-surgeon 🔍

> Structured Log Parser & Analyzer — 将原始日志转换为结构化格式，支持字段提取、过滤与统计

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Shell](https://img.shields.io/badge/Shell-Bash-green.svg)](https://www.gnu.org/software/bash/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Linux-blue.svg)](https://www.gnu.org/software/bash/)

**log-surgeon** 是一个轻量级、结构化的日志解析与分析工具，可将 Nginx、Apache、Syslog、JSON 等格式的原始日志转换为结构化数据，支持字段过滤、实时监控与统计分析。

## ✨ 特性

- 🚀 **轻量级** — 纯 Bash 脚本，无外部依赖（仅需 `python3` 做 JSON 处理）
- 📦 **多格式支持** — Nginx、Apache、Syslog (RFC 3164/5424)、JSON、CSV
- 🔧 **自定义格式** — 通过配置文件定义任意正则解析规则
- 🎯 **精确过滤** — 按字段名 + 正则表达式过滤，或按 HTTP 状态码筛选
- 📊 **统计分析** — 按任意字段分组计数，输出 TopN 排名
- 🖥️ **实时监控** — 支持 `tail -f` 风格实时解析日志流
- 📤 **多格式输出** — JSON / CSV / Table / Raw
- 🎨 **彩色输出** — 终端友好的彩色格式化

## 🏃 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/chensu1234/log-surgeon.git
cd log-surgeon

# 添加执行权限
chmod +x bin/log-surgeon.sh
```

### 基本用法

```bash
# 解析 Nginx 日志，输出 JSON
./bin/log-surgeon.sh -f log/access.log -F nginx

# 解析 JSON 日志文件
./bin/log-surgeon.sh -f log/app.json -F json

# 实时监控 Nginx 访问日志
tail -f /var/log/nginx/access.log | ./bin/log-surgeon.sh -F nginx --tail-mode

# 统计 Top 10 请求路径
./bin/log-surgeon.sh -f log/access.log -F nginx --stats request --stats-limit 10

# 过滤 500 错误
./bin/log-surgeon.sh -f log/access.log -F nginx --filter-field status --filter-value "5[0-9]{2}"

# 输出为 CSV
./bin/log-surgeon.sh -f log/access.log -F nginx -O csv
```

### 管道输入

```bash
# 从其他命令管道输入
cat access.log | ./bin/log-surgeon.sh -F nginx -n 20

# 与 grep 配合使用
grep "ERROR" app.log | ./bin/log-surgeon.sh -F json
```

## ⚙️ 配置

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FORMAT` | 默认日志格式 | `nginx` |
| `OUTPUT_FORMAT` | 默认输出格式 | `json` |
| `CONFIG_FILE` | 自定义格式配置文件路径 | - |

### 自定义格式配置

创建 `config/myformat.conf`:

```bash
name: my-app-format
regex: ^\[([^\]]+)\] \[([^\]]+)\] \[([^\]]+)\] (.*)$
field: timestamp
field: level
field: component
field: message
```

使用自定义格式:

```bash
./bin/log-surgeon.sh -f app.log -c config/myformat.conf
```

## 📋 命令行选项

### 输入相关

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-f, --file FILE` | 输入日志文件（为空则读取 stdin） | stdin |
| `-c, --config FILE` | 自定义格式配置文件 | - |

### 格式相关

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-F, --format FMT` | 输入日志格式 | `nginx` |
| `-O, --output FMT` | 输出格式: json, csv, table, raw | `json` |

### 过滤相关

| 选项 | 说明 |
|------|------|
| `--filter-field FIELD` | 按字段名过滤 |
| `--filter-value REGEX` | 过滤值（支持正则） |
| `-s, --status CODE` | 仅显示指定 HTTP 状态码 |

### 统计相关

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--stats FIELD` | 启用统计模式，按字段分组计数 | - |
| `--stats-limit N` | 统计 TopN | `10` |

### 限制相关

| 选项 | 说明 |
|------|------|
| `-n, --head N` | 仅显示前 N 行 |
| `-t, --tail N` | 仅显示后 N 行 |
| `--tail-mode` | 实时 tail -f 模式 |

### 输出相关

| 选项 | 说明 |
|------|------|
| `-q, --quiet` | 静默模式，不输出元信息 |
| `--no-color` | 禁用颜色输出 |

## 📁 项目结构

```
log-surgeon/
├── bin/
│   └── log-surgeon.sh          # 主脚本
├── config/
│   └── app-format.conf        # 自定义格式示例
├── log/
│   ├── access.log             # Nginx 示例日志
│   ├── syslog.sample          # Syslog 示例日志
│   └── app.json               # JSON 日志示例
├── README.md
└── LICENSE
```

## 🧩 支持的日志格式

### Nginx / Apache Combined

输入:
```
192.168.1.100 - - [15/Apr/2026:10:30:00 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
```

输出 (JSON):
```json
{"remote_addr": "192.168.1.100", "remote_user": "", "time_local": "15/Apr/2026:10:30:00 +0800", "request": "GET /api/users HTTP/1.1", "status": "200", "body_bytes_sent": "1234", "http_referer": "", "http_user_agent": "Mozilla/5.0"}
```

### Syslog (RFC 3164)

输入:
```
Apr 15 10:30:00 web01 sshd[1234]: Accepted publickey for deploy from 10.0.0.50
```

输出 (JSON):
```json
{"timestamp": "Apr 15 10:30:00", "hostname": "web01", "program": "sshd[1234]", "message": "Accepted publickey for deploy from 10.0.0.50"}
```

### JSON Lines

输入:
```json
{"level":"info","ts":"2026-04-15T10:30:00Z","msg":"Server started","port":8080}
```

输出: 保持原样（已是 JSON 格式）

## 📝 CHANGELOG

### [v1.0.0] - 2026-04-15

- ✨ 初始版本
- 🚀 支持 Nginx、Apache、Syslog、JSON、CSV 格式解析
- 🔧 支持自定义正则格式配置
- 🎯 字段过滤与正则匹配
- 📊 统计分析模式（TopN 分组计数）
- 🖥️ 实时 tail 模式
- 📤 多格式输出（JSON、CSV、Table、Raw）
- 🎨 彩色终端输出

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
