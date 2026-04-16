#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon 日志解析器
支持多种日志格式的自动检测与解析
"""
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class LogParser:
    """
    日志解析器基类

    支持的格式:
    - auto:   自动检测
    - syslog: 标准 syslog 格式
    - json:   JSON 格式日志
    - nginx:  Nginx 访问日志
    - apache: Apache 访问日志
    - glibc:  GNU C Library 日志格式
    - custom: 用户自定义正则（在配置中定义）
    """

    # 各格式的正则模式
    FORMAT_PATTERNS = {
        'syslog': re.compile(
            r'^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d+:\d+:\d+)\s+'
            r'(?P<host>\S+)\s+(?P<prog>\S+?)(?:\[(?P<pid>\d+)\])?:\s+'
            r'(?P<message>.*)$'
        ),
        'json': None,  # 特殊处理
        'nginx': re.compile(
            r'^(?P<ip>\S+)\s+-\s+\S+\s+'
            r'\[(?P<time>[^\]]+)\]\s+'
            r'"(?P<method>\S+)\s+(?P<url>\S+)\s+(?P<proto>\S+)"\s+'
            r'(?P<status>\d+)\s+(?P<size>\d+)\s+'
            r'"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"'
        ),
        'apache': re.compile(
            r'^(?P<ip>\S+)\s+\S+\s+\S+\s+'
            r'\[(?P<time>[^\]]+)\]\s+'
            r'"(?P<method>\S+)\s+(?P<url>\S+)\s+(?P<proto>\S+)"\s+'
            r'(?P<status>\d+)\s+(?P<size>\d+)'
        ),
        'glibc': re.compile(
            r'^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d+:\d+:\d+)\s+'
            r'(?P<host>\S+)\s+(?P<prog>\S+):\s+(?P<message>.*)$'
        ),
        'iso8601': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
            r'(?P<level>\w+)\s+(?P<message>.*)$'
        ),
        'simple': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'\[(?P<level>\w+)\]\s+(?P<message>.*)$'
        ),
    }

    # 级别关键词映射
    LEVEL_KEYWORDS = {
        'debug': ['debug', 'dbg', 'trace', 'verbose'],
        'info':  ['info', 'information', 'notice'],
        'warn':  ['warn', 'warning', 'wrn'],
        'error': ['error', 'err', 'fail', 'failed', 'failure'],
        'fatal': ['fatal', 'critical', 'crit', 'emergency', 'emerg'],
    }

    def __init__(self, config, fmt='auto'):
        self.config = config
        self.format = fmt
        self.custom_pattern = None

        # 尝试加载自定义正则
        custom_pat = config.get('parser', 'pattern', fallback=None)
        if custom_pat:
            try:
                self.custom_pattern = re.compile(custom_pat)
            except re.error:
                pass

    def detect_format(self, file_path: str) -> Dict[str, Any]:
        """
        自动检测日志格式

        Returns:
            dict: {'format': str, 'confidence': float}
        """
        # 读取样本行
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = [f.readline() for _ in range(100) if f.readline()]
        except Exception:
            return {'format': 'unknown', 'confidence': 0.0}

        if not lines:
            return {'format': 'unknown', 'confidence': 0.0}

        # 检测各格式
        scores = {}
        for fmt, pattern in self.FORMAT_PATTERNS.items():
            if fmt == 'json':
                # JSON 格式检测
                try:
                    json_count = sum(1 for line in lines if line.strip().startswith('{'))
                    scores[fmt] = json_count / len(lines)
                except Exception:
                    scores[fmt] = 0
            elif pattern:
                try:
                    match_count = sum(1 for line in lines if pattern.match(line.strip()))
                    scores[fmt] = match_count / len(lines)
                except Exception:
                    scores[fmt] = 0

        # 找最高分
        best_fmt = max(scores, key=scores.get)
        best_score = scores[best_fmt]

        # 如果最高分很低，尝试其他启发式方法
        if best_score < 0.5:
            # 检查是否有明确的级别标识
            for line in lines[:10]:
                line_lower = line.lower()
                for level, keywords in self.LEVEL_KEYWORDS.items():
                    if any(kw in line_lower for kw in keywords):
                        return {'format': 'simple', 'confidence': 0.6}

            return {'format': 'unknown', 'confidence': best_score}

        return {'format': best_fmt, 'confidence': best_score}

    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        解析单行日志

        Args:
            line: 日志行

        Returns:
            dict: 解析后的字段，解析失败返回 None
        """
        line = line.strip()
        if not line:
            return None

        fmt = self.format
        if fmt == 'auto':
            detected = self.detect_format_from_line(line)
            fmt = detected['format']

        # 根据格式解析
        if fmt == 'json':
            return self._parse_json(line)
        elif fmt in self.FORMAT_PATTERNS and self.FORMAT_PATTERNS[fmt]:
            return self._parse_regex(line, self.FORMAT_PATTERNS[fmt])
        elif fmt == 'custom' and self.custom_pattern:
            return self._parse_regex(line, self.custom_pattern)
        else:
            # 默认：整行作为 message
            return {
                'raw': line,
                'message': line,
                'level': self._detect_level(line),
                'timestamp': None,
            }

    def _parse_json(self, line: str) -> Optional[Dict[str, Any]]:
        """解析 JSON 格式日志"""
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                # 标准化字段名
                result = {
                    'raw': line,
                    'message': data.get('message', data.get('msg', data.get('log', ''))),
                    'level': self._normalize_level(
                        data.get('level', data.get('severity', data.get('loglevel', '')))
                    ),
                    'timestamp': self._parse_timestamp(
                        data.get('timestamp', data.get('time', data.get('@timestamp', '')))
                    ),
                }
                # 复制其他字段
                for k, v in data.items():
                    if k not in result:
                        result[k] = v
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _parse_regex(self, line: str, pattern: re.Pattern) -> Optional[Dict[str, Any]]:
        """使用正则表达式解析日志"""
        match = pattern.match(line)
        if not match:
            return None

        groups = match.groupdict()

        # 标准化时间戳
        timestamp = None
        if 'timestamp' in groups:
            timestamp = self._parse_timestamp(groups['timestamp'])
        elif 'time' in groups:
            timestamp = self._parse_timestamp(groups['time'])
        elif 'month' in groups and 'day' in groups and 'time' in groups:
            # 构造完整时间戳（缺少年份，用当前年份）
            year = datetime.now().year
            try:
                ts_str = f"{year} {groups['month']} {groups['day']} {groups['time']}"
                timestamp = datetime.strptime(ts_str, '%Y %b %d %H:%M:%S')
            except ValueError:
                pass

        # 标准化级别
        level = self._normalize_level(groups.get('level', ''))

        # 组装结果
        result = {
            'raw': line,
            'timestamp': timestamp,
            'level': level,
        }

        for k, v in groups.items():
            if v and k not in ('timestamp', 'time', 'month', 'day', 'level'):
                result[k] = v

        # 合并 message
        if 'message' not in result or not result['message']:
            result['message'] = groups.get('message', line)

        return result

    def parse_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """批量解析多行日志"""
        results = []
        for line in lines:
            parsed = self.parse_line(line)
            if parsed:
                results.append(parsed)
        return results

    def _detect_level(self, text: str) -> str:
        """从文本中检测日志级别"""
        text_lower = text.lower()
        for level, keywords in self.LEVEL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return level
        return 'info'

    def _normalize_level(self, level: str) -> str:
        """标准化日志级别"""
        if not level:
            return 'info'
        level_lower = str(level).lower()
        for std_level, keywords in self.LEVEL_KEYWORDS.items():
            if level_lower in keywords or level_lower == std_level:
                return std_level
        return 'info'

    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """解析时间戳字符串"""
        if not ts_str:
            return None

        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%d/%b/%Y:%H:%M:%S',
            '%b %d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
        ]

        # 清理时区
        ts_str = re.sub(r'[+-]\d{2}:?\d{2}$', '', ts_str)
        ts_str = ts_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue

        return None

    def detect_format_from_line(self, line: str) -> Dict[str, Any]:
        """从单行检测格式（用于 parse_line）"""
        line = line.strip()

        # JSON 检测
        if line.startswith('{'):
            try:
                json.loads(line)
                return {'format': 'json', 'confidence': 1.0}
            except Exception:
                pass

        # 各格式检测
        for fmt, pattern in self.FORMAT_PATTERNS.items():
            if fmt == 'json' or not pattern:
                continue
            if pattern.match(line):
                return {'format': fmt, 'confidence': 0.8}

        # 简单级别检测
        for level, keywords in self.LEVEL_KEYWORDS.items():
            if any(kw in line.lower() for kw in keywords):
                return {'format': 'simple', 'confidence': 0.5}

        return {'format': 'raw', 'confidence': 0.1}
