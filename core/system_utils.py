#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统级适配工具 (跨平台支持)
处理免打扰模式 (DND) 切换
"""

import os
import sys
import subprocess

class SystemUtils:
    """操作系统相关工具类"""
    
    @staticmethod
    def set_dnd_mode(enabled: bool):
        """
        切换系统免打扰模式
        Args:
            enabled: True = 开启免打扰 (禁止弹窗), False = 恢复正常 (允许弹窗)
        """
        platform = sys.platform
        
        if platform == "win32":
            SystemUtils._set_windows_dnd(enabled)
        elif platform == "darwin":
            SystemUtils._set_macos_dnd(enabled)
        elif platform == "linux":
            SystemUtils._set_linux_dnd(enabled)

    @staticmethod
    def _set_windows_dnd(enabled: bool):
        """Windows 实现: 修改注册表控制通知开关"""
        try:
            import winreg
            path = r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
            # 0 = 禁用通知 (DND 开), 1 = 启用通知 (DND 关)
            val = 0 if enabled else 1
            winreg.SetValueEx(key, "NOC_GLOBAL_SETTING_TOASTS_ENABLED", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Windows DND Error: {e}")

    @staticmethod
    def _set_macos_dnd(enabled: bool):
        """macOS 实现: 通过 AppleScript 或 Shortcuts 切换专注模式"""
        try:
            # 常见方案: 模拟快捷键或使用命令行
            # 这里的方案是使用 AppleScript 控制通知中心 (Monterey+)
            state = "true" if enabled else "false"
            script = f'tell application "System Events" to set do not disturb to {state}'
            subprocess.run(['osascript', '-e', script], capture_output=True)
        except Exception as e:
            print(f"macOS DND Error: {e}")

    @staticmethod
    def _set_linux_dnd(enabled: bool):
        """Linux 实现: 仅支持 GNOME 桌面环境"""
        try:
            state = "false" if enabled else "true"
            subprocess.run([
                'gsettings', 'set', 'org.gnome.desktop.notifications', 
                'show-banners', state
            ], capture_output=True)
        except Exception as e:
            print(f"Linux/GNOME DND Error: {e}")
