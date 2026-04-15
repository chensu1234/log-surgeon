# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-26

### Added
- 多格式自动检测 (Apache/Nginx 访问日志, Syslog, JSON, 纯文本)
- `stats` 命令: 完整统计报告 (总行数, 错误/警告/信息/调试分类, Top-IP, Top-路径, HTTP 状态码分布)
- `tail` 命令: 实时日志追踪, 带彩色输出和解析
- `anomaly` 命令: 异常检测 (5xx 错误, 日志风暴, 高频请求, 可疑路径扫描)
- `filter` 命令: 灵活过滤 (按级别/IP/状态码/正则/时间)
- `top` 命令: 多维度 Top-N 排行 (IP/路径/状态码/级别)
- `watch` 命令: 持续监控模式, 带自动告警 (错误率 > 10%, IP 访问激增)
- `parse` 命令: 快速解析单文件预览
- `patterns.conf`: 自定义检测规则配置
- 纯 Bash 实现, 零外部依赖
- 彩色终端输出
- 完整帮助文档
