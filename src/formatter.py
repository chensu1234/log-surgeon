#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon 输出格式化模块
支持 text、json、csv 三种输出格式
"""
import json
import csv
import io
from datetime import datetime
from typing import Dict, List, Any


# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'

USE_COLOR = True


def set_color(enabled: bool):
    """设置是否使用颜色"""
    global USE_COLOR
    USE_COLOR = enabled


def color(text: str, c: str) -> str:
    """为文本添加颜色"""
    return f"{c}{text}{NC}" if USE_COLOR else text


class OutputFormatter:
    """
    日志输出格式化器

    支持的格式:
    - text: 人类可读的文本格式
    - json: JSON 数组
    - csv:  CSV 格式
    """

    # 级别颜色映射
    LEVEL_COLORS = {
        'debug': CYAN,
        'info':  GREEN,
        'warn':  YELLOW,
        'error': RED,
        'fatal': f"{RED}{BOLD}",
    }

    def __init__(self, config, fmt: str = 'text'):
        self.config = config
        self.fmt = fmt

    def format_lines(self, entries: List[Dict[str, Any]]) -> str:
        """批量格式化日志条目"""
        if self.fmt == 'json':
            return self._format_json(entries)
        elif self.fmt == 'csv':
            return self._format_csv(entries)
        else:
            return self._format_text(entries)

    def _format_text(self, entries: List[Dict[str, Any]]) -> str:
        """文本格式输出"""
        lines = []

        for entry in entries:
            # 时间戳
            ts = entry.get('timestamp')
            if ts:
                ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
            else:
                ts_str = '-'

            # 级别
            level = entry.get('level', 'info')
            level_color = self.LEVEL_COLORS.get(level, '')
            level_str = color(f"[{level.upper():>5}]", level_color)

            # 消息
            message = entry.get('message', entry.get('raw', ''))

            # 组装行
            line = f"{ts_str}  {level_str}  {message}"
            lines.append(line)

        return '\n'.join(lines)

    def _format_json(self, entries: List[Dict[str, Any]]) -> str:
        """JSON 格式输出"""
        # 序列化 datetime
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        # 过滤不可序列化的字段
        serializable = []
        for entry in entries:
            obj = {}
            for k, v in entry.items():
                if isinstance(v, datetime):
                    obj[k] = v.isoformat()
                elif isinstance(v, (str, int, float, bool, type(None))):
                    obj[k] = v
                else:
                    obj[k] = str(v)
            serializable.append(obj)

        return json.dumps(serializable, ensure_ascii=False, indent=2)

    def _format_csv(self, entries: List[Dict[str, Any]]) -> str:
        """CSV 格式输出"""
        if not entries:
            return ""

        output = io.StringIO()
        # 使用第一个条目的键作为列名
        fieldnames = list(entries[0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            # 序列化 datetime
            row = {}
            for k, v in entry.items():
                if isinstance(v, datetime):
                    row[k] = v.isoformat()
                else:
                    row[k] = v
            writer.writerow(row)

        return output.getvalue()

    def format_stats(self, result: Dict[str, Any]) -> str:
        """格式化统计结果"""
        if self.fmt == 'json':
            return json.dumps(result, ensure_ascii=False, indent=2)

        return self._format_stats_text(result)

    def _format_stats_text(self, result: Dict[str, Any]) -> str:
        """文本格式统计输出"""
        lines = []
        t = result.get('type', '')

        if t == 'summary':
            lines.append(color("\n═══════ 日志统计摘要 ═══════\n", BOLD + CYAN))
            lines.append(f"  总记录数: {color(str(result.get('total', 0)), GREEN)}")

            # 级别分布
            level_dist = result.get('level_distribution', [])
            if level_dist:
                lines.append(color("\n  ── 级别分布 ──", BOLD))
                for item in level_dist:
                    level = item['level']
                    level_color = self.LEVEL_COLORS.get(level, '')
                    bar = item['bar']
                    pct = item['percentage']
                    cnt = item['count']
                    lines.append(
                        f"  {color(f'[{level.upper():>5}]', level_color)}  "
                        f"{bar}  {cnt:>6} ({pct:>5.1f}%)"
                    )

            # 字段统计
            field_stats = result.get('field_stats', {})
            if field_stats:
                lines.append(color("\n  ── 字段统计 ──", BOLD))
                for field, stats in field_stats.items():
                    lines.append(f"\n  [{field}]  (唯一值: {stats.get('unique', 0)})")
                    for item in stats.get('top', []):
                        lines.append(f"    {item['value']:>30}  {item['count']:>6}")

            # 时间范围
            time_range = result.get('time_range', {})
            if time_range:
                lines.append(color("\n  ── 时间范围 ──", BOLD))
                if time_range.get('earliest'):
                    lines.append(f"  最早: {time_range['earliest']}")
                if time_range.get('latest'):
                    lines.append(f"  最晚: {time_range['latest']}")

            lines.append(color("\n" + "═" * 40, BOLD + CYAN))

        elif t == 'top_values':
            lines.append(color(f"\n═══════ Top {result.get('top_n', 10)} {result.get('field', '')} ═══════\n", BOLD + CYAN))
            total = result.get('total_entries', 0)
            lines.append(f"  总记录数: {total}  |  唯一值: {result.get('total_unique', 0)}\n")

            for item in result.get('items', []):
                value = item['value']
                count = item['count']
                pct = item['percentage']
                bar = self._make_bar(pct / 100)
                lines.append(f"  {value:>30}  {bar}  {count:>6} ({pct:>5.1f}%)")

            lines.append(color("\n" + "═" * 40, BOLD + CYAN))

        elif t == 'level_distribution':
            lines.append(color("\n═══════ 级别分布 ═══════\n", BOLD + CYAN))
            total = result.get('total', 0)
            lines.append(f"  总记录数: {total}\n")

            for item in result.get('distribution', []):
                level = item['level']
                level_color = self.LEVEL_COLORS.get(level, '')
                bar = item['bar']
                pct = item['percentage']
                cnt = item['count']
                lines.append(
                    f"  {color(f'[{level.upper():>5}]', level_color)}  "
                    f"{bar}  {cnt:>6} ({pct:>5.1f}%)"
                )

            lines.append(color("\n" + "═" * 40, BOLD + CYAN))

        elif t == 'time_distribution':
            lines.append(color(f"\n═══════ 时间分布 ({result.get('bucket', 'hour')}) ═══════\n", BOLD + CYAN))
            for bucket in result.get('buckets', []):
                time = bucket['time']
                count = bucket['count']
                bar = self._make_bar(count / result.get('total', 1))
                lines.append(f"  {time}  {bar}  {count:>6}")

            lines.append(color("\n" + "═" * 40, BOLD + CYAN))

        else:
            lines.append(json.dumps(result, ensure_ascii=False, indent=2))

        return '\n'.join(lines)

    def _make_bar(self, percentage: float, width: int = 20) -> str:
        """生成 ASCII 条形图"""
        filled = int(max(0, min(1, percentage)) * width)
        return '█' * filled + '░' * (width - filled)
