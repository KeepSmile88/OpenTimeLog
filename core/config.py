#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置管理
"""

import os
import json


class ConfigManager:
    """管理应用程序配置的持久化"""
    
    DEFAULT_CONFIG = {
        "theme": "default",
        "geometry": None, # [x, y, w, h]
        "minimize_to_tray": True,
        "close_to_tray": True,
        "pomodoro_duration": 25,
        "break_duration": 5,
        "hotkey_show_hide": "Alt+Shift+S"
    }

    def __init__(self, config_file="config.json"):
        self.config_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(os.path.dirname(self.config_dir), config_file)
        self.data = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """从文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
