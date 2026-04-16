#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon 统计分析引擎
提供 Top N、频率分析、分布统计等功能
"""
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any


class StatsEngine:
    """
    日志统计分析引擎
    """

    def __init__(self, config):
        self.config = config

    def top_values(
        self,
        entries: List[Dict[str, Any]],
        field: str = 'level',
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        统计字段 Top N 值

        Args:
            entries: 解析后的日志条目列表
            field: 统计字段
            top_n: 返回前 N 条

        Returns:
            dict: 统计结果
        """
        counter = Counter()

        for entry in entries:
            value = entry.get(field, '')
            if value:
                counter[value] += 1

        total = sum(counter.values())
        top_items = counter.most_common(top_n)

        return {
            'type': 'top_values',
            'field': field,
            'top_n': top_n,
            'total_entries': len(entries),
            'total_unique': len(counter),
            'items': [
                {
                    'value': value,
                    'count': count,
                    'percentage': round(count / total * 100, 2) if total > 0 else 0
                }
                for value, count in top_items
            ]
        }

    def level_distribution(
        self,
        entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        统计日志级别分布

        Args:
            entries: 解析后的日志条目列表

        Returns:
            dict: 级别分布统计
        """
        levels = ['debug', 'info', 'warn', 'error', 'fatal']
        counter = Counter(entry.get('level', 'unknown') for entry in entries)

        total = sum(counter.values())
        distribution = []

        for level in levels:
            count = counter.get(level, 0)
            distribution.append({
                'level': level,
                'count': count,
                'percentage': round(count / total * 100, 2) if total > 0 else 0,
                'bar': self._make_bar(count / total if total > 0 else 0)
            })

        return {
            'type': 'level_distribution',
            'total': total,
            'distribution': distribution
        }

    def time_distribution(
        self,
        entries: List[Dict[str, Any]],
        bucket: str = 'hour'
    ) -> Dict[str, Any]:
        """
        按时间分桶统计

        Args:
            entries: 解析后的日志条目列表
            bucket: 分桶方式 (minute, hour, day)

        Returns:
            dict: 时间分布统计
        """
        buckets = defaultdict(int)

        for entry in entries:
            ts = entry.get('timestamp')
            if not ts:
                continue

            if bucket == 'minute':
                key = ts.strftime('%Y-%m-%d %H:%M')
            elif bucket == 'hour':
                key = ts.strftime('%Y-%m-%d %H:00')
            elif bucket == 'day':
                key = ts.strftime('%Y-%m-%d')
            else:
                key = ts.strftime('%Y-%m-%d %H:00')

            buckets[key] += 1

        # 排序
        sorted_buckets = sorted(buckets.items())

        return {
            'type': 'time_distribution',
            'bucket': bucket,
            'total': sum(buckets.values()),
            'buckets': [
                {'time': k, 'count': v}
                for k, v in sorted_buckets
            ]
        }

    def summary(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成综合统计摘要

        Args:
            entries: 解析后的日志条目列表

        Returns:
            dict: 综合统计结果
        """
        if not entries:
            return {'type': 'summary', 'total': 0}

        # 级别分布
        level_dist = self.level_distribution(entries)

        # 统计常见字段
        field_stats = {}

        # 尝试统计常见字段
        for field in ['ip', 'status', 'method', 'url', 'host', 'prog']:
            counter = Counter(entry.get(field, '') for entry in entries if entry.get(field))
            if counter:
                top = counter.most_common(5)
                field_stats[field] = {
                    'unique': len(counter),
                    'top': [{'value': v, 'count': c} for v, c in top]
                }

        # 时间范围
        timestamps = [e.get('timestamp') for e in entries if e.get('timestamp')]
        time_range = {}
        if timestamps:
            time_range = {
                'earliest': min(timestamps).isoformat() if timestamps else None,
                'latest': max(timestamps).isoformat() if timestamps else None,
            }

        return {
            'type': 'summary',
            'total': len(entries),
            'level_distribution': level_dist['distribution'],
            'field_stats': field_stats,
            'time_range': time_range,
        }

    def error_rate(
        self,
        entries: List[Dict[str, Any]],
        window_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        计算错误率时间序列

        Args:
            entries: 解析后的日志条目列表
            window_minutes: 窗口大小（分钟）

        Returns:
            dict: 错误率统计
        """
        # 按时间窗口分组
        buckets = defaultdict(lambda: {'total': 0, 'errors': 0})

        for entry in entries:
            ts = entry.get('timestamp')
            if not ts:
                continue

            # 计算窗口 key
            minute = ts.minute // window_minutes * window_minutes
            key = ts.replace(minute=minute, second=0, microsecond=0)

            buckets[key]['total'] += 1
            if entry.get('level') in ('error', 'fatal'):
                buckets[key]['errors'] += 1

        # 计算错误率
        sorted_keys = sorted(buckets.keys())
        series = []

        for key in sorted_keys:
            data = buckets[key]
            rate = data['errors'] / data['total'] if data['total'] > 0 else 0
            series.append({
                'time': key.isoformat(),
                'total': data['total'],
                'errors': data['errors'],
                'error_rate': round(rate * 100, 2)
            })

        return {
            'type': 'error_rate',
            'window_minutes': window_minutes,
            'series': series
        }

    def _make_bar(self, percentage: float, width: int = 20) -> str:
        """
        生成 ASCII 条形图

        Args:
            percentage: 百分比 (0-1)
            width: 条形宽度

        Returns:
            str: ASCII 条形图
        """
        filled = int(percentage * width)
        return '█' * filled + '░' * (width - filled)
