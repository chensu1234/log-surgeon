#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon 单元测试
测试日志解析器核心功能
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parser import LogParser
from src.query import QueryEngine
from src.stats import StatsEngine
from src.config import Config
from src.formatter import OutputFormatter


class TestLogParser(unittest.TestCase):
    """测试日志解析器"""

    def setUp(self):
        self.config = Config()

    def test_parse_simple_format(self):
        """测试简化格式解析"""
        parser = LogParser(self.config, fmt='simple')
        line = '2026-04-16 08:00:00  [INFO]    Application started'
        result = parser.parse_line(line)

        self.assertIsNotNone(result)
        self.assertEqual(result['level'], 'info')
        self.assertIn('Application started', result['message'])

    def test_parse_level_detection(self):
        """测试级别检测"""
        parser = LogParser(self.config)

        cases = [
            ('2026-04-16 08:00:00  [ERROR]   Failed', 'error'),
            ('2026-04-16 08:00:00  [WARN]    Warning', 'warn'),
            ('2026-04-16 08:00:00  [DEBUG]   Debug', 'debug'),
            ('2026-04-16 08:00:00  [FATAL]   Fatal', 'fatal'),
        ]

        for line, expected_level in cases:
            parser = LogParser(self.config, fmt='simple')
            result = parser.parse_line(line)
            self.assertEqual(result['level'], expected_level, f"Line: {line}")

    def test_parse_json_format(self):
        """测试 JSON 格式解析"""
        parser = LogParser(self.config, fmt='json')
        line = '{"timestamp": "2026-04-16T08:00:00Z", "level": "error", "message": "Test error"}'
        result = parser.parse_line(line)

        self.assertIsNotNone(result)
        self.assertEqual(result['level'], 'error')
        self.assertEqual(result['message'], 'Test error')

    def test_parse_multiple_lines(self):
        """测试批量解析"""
        parser = LogParser(self.config, fmt='simple')
        lines = [
            '2026-04-16 08:00:00  [INFO]    Line 1',
            '2026-04-16 08:00:01  [ERROR]  Line 2',
            '2026-04-16 08:00:02  [WARN]   Line 3',
        ]
        results = parser.parse_lines(lines)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['level'], 'info')
        self.assertEqual(results[1]['level'], 'error')
        self.assertEqual(results[2]['level'], 'warn')

    def test_parse_invalid_line(self):
        """测试无效行"""
        parser = LogParser(self.config, fmt='json')
        result = parser.parse_line('not a valid log line')

        # JSON 解析器对无效行返回 None
        self.assertIsNone(result)

    def test_parse_empty_line(self):
        """测试空行"""
        parser = LogParser(self.config)
        result = parser.parse_line('')
        self.assertIsNone(result)

        result = parser.parse_line('   \n  ')
        self.assertIsNone(result)


class TestQueryEngine(unittest.TestCase):
    """测试查询引擎"""

    def setUp(self):
        self.config = Config()
        self.lines = [
            '2026-04-16 08:00:00  [INFO]    Application started',
            '2026-04-16 08:00:01  [ERROR]  Database connection failed',
            '2026-04-16 08:00:02  [WARN]   High memory usage',
            '2026-04-16 08:00:03  [DEBUG]  Loading config file',
            '2026-04-16 08:00:04  [ERROR]  SMTP send failed',
        ]

    def test_filter_by_level(self):
        """测试级别过滤"""
        engine = QueryEngine(self.config)
        engine.add_filter('level', 'error')
        results = engine.filter(self.lines)

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertEqual(r['level'], 'error')

    def test_filter_by_regex(self):
        """测试正则过滤"""
        engine = QueryEngine(self.config)
        engine.set_regex(r'database|SMTP')
        results = engine.filter(self.lines)

        self.assertEqual(len(results), 2)

    def test_combined_filters(self):
        """测试组合过滤"""
        engine = QueryEngine(self.config)
        engine.add_filter('level', 'error')
        engine.set_regex(r'database')
        results = engine.filter(self.lines)

        self.assertEqual(len(results), 1)

    def test_filter_no_match(self):
        """测试无匹配"""
        engine = QueryEngine(self.config)
        engine.add_filter('level', 'fatal')
        results = engine.filter(self.lines)

        self.assertEqual(len(results), 0)


class TestStatsEngine(unittest.TestCase):
    """测试统计引擎"""

    def setUp(self):
        self.config = Config()
        self.parser = LogParser(self.config, fmt='simple')

        self.entries = self.parser.parse_lines([
            '2026-04-16 08:00:00  [INFO]    Line 1',
            '2026-04-16 08:00:01  [ERROR]  Line 2',
            '2026-04-16 08:00:02  [INFO]   Line 3',
            '2026-04-16 08:00:03  [ERROR]  Line 4',
            '2026-04-16 08:00:04  [WARN]   Line 5',
        ])

    def test_top_values(self):
        """测试 Top N 统计"""
        engine = StatsEngine(self.config)
        result = engine.top_values(self.entries, field='level', top_n=5)

        self.assertEqual(result['type'], 'top_values')
        self.assertEqual(result['total_entries'], 5)

        # INFO 应该出现2次
        top = {item['value']: item['count'] for item in result['items']}
        self.assertEqual(top.get('info', 0), 2)
        self.assertEqual(top.get('error', 0), 2)

    def test_level_distribution(self):
        """测试级别分布"""
        engine = StatsEngine(self.config)
        result = engine.level_distribution(self.entries)

        self.assertEqual(result['type'], 'level_distribution')
        self.assertEqual(result['total'], 5)

        dist = {item['level']: item['count'] for item in result['distribution']}
        self.assertEqual(dist['info'], 2)
        self.assertEqual(dist['error'], 2)
        self.assertEqual(dist['warn'], 1)

    def test_summary(self):
        """测试摘要统计"""
        engine = StatsEngine(self.config)
        result = engine.summary(self.entries)

        self.assertEqual(result['type'], 'summary')
        self.assertEqual(result['total'], 5)
        self.assertIn('level_distribution', result)


class TestFormatter(unittest.TestCase):
    """测试输出格式化"""

    def setUp(self):
        self.config = Config()

    def test_format_text(self):
        """测试文本格式输出"""
        formatter = OutputFormatter(self.config, fmt='text')
        entries = [
            {'timestamp': None, 'level': 'info', 'message': 'Test message', 'raw': 'raw'}
        ]
        output = formatter.format_lines(entries)
        self.assertIn('Test message', output)

    def test_format_json(self):
        """测试 JSON 格式输出"""
        formatter = OutputFormatter(self.config, fmt='json')
        entries = [
            {'level': 'error', 'message': 'Test error'}
        ]
        output = formatter.format_lines(entries)
        self.assertIn('error', output)
        self.assertIn('Test error', output)

    def test_format_csv(self):
        """测试 CSV 格式输出"""
        formatter = OutputFormatter(self.config, fmt='csv')
        entries = [
            {'level': 'info', 'message': 'Test1'},
            {'level': 'error', 'message': 'Test2'},
        ]
        output = formatter.format_lines(entries)
        self.assertIn('level,message', output)
        self.assertIn('info,Test1', output)
        self.assertIn('error,Test2', output)


if __name__ == '__main__':
    unittest.main()
