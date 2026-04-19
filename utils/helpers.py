#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数
"""

from PySide6.QtGui import QColor


def darken_color(color: str, factor: float = 0.8) -> str:
    """将颜色变暗
    
    Args:
        color: 颜色值（十六进制或颜色名称）
        factor: 变暗因子，0-1之间，越小越暗
        
    Returns:
        RGB格式的颜色字符串
    """
    qcolor = QColor(color)
    return f"rgb({int(qcolor.red() * factor)}, {int(qcolor.green() * factor)}, {int(qcolor.blue() * factor)})"


def lighten_color(color: str, factor: float = 1.2) -> str:
    """将颜色变亮
    
    Args:
        color: 颜色值（十六进制或颜色名称）
        factor: 变亮因子，大于1表示变亮
        
    Returns:
        RGB格式的颜色字符串
    """
    qcolor = QColor(color)
    r = min(255, int(qcolor.red() * factor))
    g = min(255, int(qcolor.green() * factor))
    b = min(255, int(qcolor.blue() * factor))
    return f"rgb({r}, {g}, {b})"


def format_duration(seconds: int) -> str:
    """格式化时长为 HH:MM:SS 格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串
    """
    if seconds < 0:
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f'{hours:02d}:{minutes:02d}:{secs:02d}'


def format_duration_short(seconds: int) -> str:
    """格式化时长为简短格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串，如 "2h30m" 或 "45m"
    """
    if seconds < 0:
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f'{hours}h{minutes}m'
    else:
        return f'{minutes}m'


def format_time(dt) -> str:
    """格式化时间为 HH:MM 格式
    
    Args:
        dt: datetime对象
        
    Returns:
        格式化的时间字符串
    """
    return dt.strftime('%H:%M')


def format_date(dt) -> str:
    """格式化日期为 YYYY-MM-DD 格式
    
    Args:
        dt: datetime或date对象
        
    Returns:
        格式化的日期字符串
    """
    return dt.strftime('%Y-%m-%d')


def hex_to_rgba(hex_color: str, alpha: int = 255) -> str:
    """将十六进制颜色转换为RGBA格式
    
    Args:
        hex_color: 十六进制颜色值，如 "#FF6B6B"
        alpha: 透明度，0-255
        
    Returns:
        RGBA格式的颜色字符串
    """
    qcolor = QColor(hex_color)
    return f"rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {alpha})"


def get_contrast_color(color: str) -> str:
    """获取对比色（用于文字显示）
    
    Args:
        color: 背景颜色
        
    Returns:
        "white" 或 "black"
    """
    qcolor = QColor(color)
    # 使用亮度公式判断
    brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
    return "white" if brightness < 128 else "black"
