# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-04-15

### Added
- 初始版本
- 支持 Nginx、Apache Combined、Syslog (RFC 3164/5424)、JSON Lines、CSV 格式解析
- 自定义正则格式配置支持 (`--config`)
- 字段过滤 (`--filter-field`, `--filter-value`) 与 HTTP 状态码筛选 (`-s`)
- 统计分析模式 (`--stats`)：按任意字段分组计数，输出 TopN 排名
- 实时 tail 监控模式 (`--tail-mode`)
- 多格式输出：JSON、CSV、Table、Raw
- 纯 Bash 实现，零外部依赖（仅需 `python3` 处理 JSON）
- 彩色终端输出与静默模式
