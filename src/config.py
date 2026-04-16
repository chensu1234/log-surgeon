#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log-surgeon 配置管理模块
支持 INI 格式配置文件
"""
import os
import configparser
from typing import Any, Optional


class Config:
    """
    配置文件管理器

    支持从 INI 格式配置文件读取配置，
    同时支持环境变量覆盖（格式: SURGEON_KEY）
    """

    def __init__(self, config_path: str = './config/surgeon.conf'):
        self.config_path = config_path
        self.parser = configparser.ConfigParser()
        self._load()

    def _load(self):
        """加载配置文件"""
        # 尝试多个可能的位置
        paths = [
            self.config_path,
            os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'surgeon.conf'),
            '/etc/log-surgeon/surgeon.conf',
            os.path.expanduser('~/.config/log-surgeon/surgeon.conf'),
        ]

        for path in paths:
            if path and os.path.exists(path):
                try:
                    self.parser.read(path, encoding='utf-8')
                    return
                except configparser.Error:
                    continue

        # 使用默认配置
        self._set_defaults()

    def _set_defaults(self):
        """设置默认配置"""
        self.parser['default'] = {
            'format': 'auto',
            'time_format': '%Y-%m-%d %H:%M:%S',
            'timeout': '5',
            'color': 'true',
        }
        self.parser['parser'] = {}
        self.parser['output'] = {
            'export_format': 'text',
            'limit': '1000',
        }

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        获取配置值

        Args:
            section: 配置段落
            key: 配置键
            fallback: 默认值

        Returns:
            配置值
        """
        # 优先从环境变量读取
        env_key = f"SURGEON_{section.upper()}_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val

        # 从配置文件读取
        try:
            return self.parser.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置"""
        val = self.get(section, key, fallback)
        try:
            return int(val)
        except (ValueError, TypeError):
            return fallback

    def getbool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置"""
        val = self.get(section, key, fallback)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', 'yes', '1', 'on')
        return bool(val)

    def sections(self):
        """返回所有段落"""
        return self.parser.sections()

    def items(self, section: str):
        """返回段落中的所有项"""
        try:
            return self.parser.items(section)
        except configparser.NoSectionError:
            return []
