#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon 查询引擎
支持级别过滤、正则匹配、时间范围过滤、字段过滤
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable


class QueryEngine:
    """
    日志查询引擎

    支持的过滤方式:
    - 级别过滤 (level)
    - 正则匹配 (regex)
    - 时间范围 (before/after)
    - 字段匹配 (field)
    """

    def __init__(self, config):
        self.config = config
        self.filters: List[Callable[[Dict], bool]] = []
        self._regex: Optional[re.Pattern] = None
        self._time_start: Optional[datetime] = None
        self._time_end: Optional[datetime] = None
        self._field_filters: Dict[str, Any] = {}

    def add_filter(self, field: str, value: Any) -> 'QueryEngine':
        """
        添加字段过滤

        Args:
            field: 字段名 (level, status, ip, url 等)
            value: 过滤值
        """
        v_normalized = value.lower() if isinstance(value, str) else value

        def make_filter(f, v):
            def filter_fn(entry: Dict) -> bool:
                entry_val = entry.get(f, '')
                if isinstance(entry_val, str):
                    entry_val = entry_val.lower()
                return entry_val == v
            return filter_fn

        self.filters.append(make_filter(field, v_normalized))
        return self

    def set_regex(self, pattern: str) -> 'QueryEngine':
        """
        设置正则表达式过滤

        Args:
            pattern: 正则表达式
        """
        try:
            self._regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"无效的正则表达式: {e}")
        return self

    def set_time_range(self, start: Optional[str] = None, end: Optional[str] = None) -> 'QueryEngine':
        """
        设置时间范围过滤

        Args:
            start: 起始时间（格式: YYYY-MM-DD HH:MM:SS）
            end: 结束时间
        """
        if start:
            self._time_start = self._parse_time(start)
        if end:
            self._time_end = self._parse_time(end)
        return self

    def add_field_filter(self, field: str, value: Any, op: str = 'eq') -> 'QueryEngine':
        """
        添加字段过滤（支持操作符）

        Args:
            field: 字段名
            value: 值
            op: 操作符 (eq, ne, contains, regex)
        """
        def make_op_filter(f, v, o):
            def filter_fn(entry: Dict) -> bool:
                entry_val = entry.get(f, '')

                if o == 'eq':
                    return str(entry_val) == str(v)
                elif o == 'ne':
                    return str(entry_val) != str(v)
                elif o == 'contains':
                    return str(v) in str(entry_val)
                elif o == 'regex':
                    try:
                        return bool(re.search(str(v), str(entry_val)))
                    except re.error:
                        return False

                return False
            return filter_fn

        self.filters.append(make_op_filter(field, value, op))
        return self

    def filter(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        过滤日志行

        Args:
            lines: 原始日志行列表

        Returns:
            匹配过滤条件的字典列表
        """
        from src.parser import LogParser

        parser = LogParser(self.config)
        results = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parsed = parser.parse_line(line)
            if not parsed:
                # 解析失败，保留原始行
                parsed = {'raw': line, 'message': line, 'level': 'info', 'timestamp': None}

            # 应用过滤器
            if self._match_entry(parsed):
                results.append(parsed)

        return results

    def _match_entry(self, entry: Dict[str, Any]) -> bool:
        """检查单条日志是否匹配所有过滤条件"""
        # 级别过滤
        for filter_fn in self.filters:
            if not filter_fn(entry):
                return False

        # 正则过滤
        if self._regex:
            # 在多个字段中匹配
            match_fields = [
                entry.get('message', ''),
                entry.get('raw', ''),
                entry.get('url', ''),
            ]
            if not any(self._regex.search(str(f)) for f in match_fields if f):
                return False

        # 时间范围过滤
        ts = entry.get('timestamp')
        if ts:
            if self._time_start and ts < self._time_start:
                return False
            if self._time_end and ts > self._time_end:
                return False

        return True

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def count(self) -> int:
        """返回匹配数量"""
        return len(self._matched_entries)

    def clear(self) -> 'QueryEngine':
        """清空所有过滤条件"""
        self.filters = []
        self._regex = None
        self._time_start = None
        self._time_end = None
        self._field_filters = {}
        return self
