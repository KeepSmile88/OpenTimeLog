#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间计算工具类
提供统一的时间计算和格式化方法
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple


class TimeCalculator:
    """时间计算工具类"""
    
    @staticmethod
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
    
    @staticmethod
    def format_duration_hm(seconds: int) -> str:
        """格式化时长为 Xh Xm 格式
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串，如 "2h 30m"
        """
        if seconds < 0:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f'{hours}h {minutes}m'
        else:
            return f'{minutes}m'
    
    @staticmethod
    def format_time(dt: datetime) -> str:
        """格式化时间为 HH:MM 格式
        
        Args:
            dt: datetime对象
            
        Returns:
            格式化的时间字符串
        """
        return dt.strftime('%H:%M')
    
    @staticmethod
    def format_datetime(dt: datetime) -> str:
        """格式化日期时间为完整格式
        
        Args:
            dt: datetime对象
            
        Returns:
            格式化的日期时间字符串
        """
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def calculate_duration(start_time: datetime, end_time: Optional[datetime] = None) -> int:
        """计算时间间隔（秒）
        
        Args:
            start_time: 开始时间
            end_time: 结束时间，默认为当前时间
            
        Returns:
            时间间隔（秒）
        """
        if end_time is None:
            end_time = datetime.now()
        
        duration = end_time - start_time
        return max(0, int(duration.total_seconds()))
    
    @staticmethod
    def parse_time_string(time_str: str) -> Optional[datetime]:
        """解析时间字符串
        
        Args:
            time_str: ISO格式的时间字符串
            
        Returns:
            datetime对象，解析失败返回None
        """
        try:
            return datetime.fromisoformat(time_str)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_week_range(target_date: datetime.date) -> Tuple[datetime.date, datetime.date]:
        """获取指定日期所在周的起止日期
        
        Args:
            target_date: 目标日期
            
        Returns:
            (周一日期, 周日日期) 元组
        """
        start_of_week = target_date - timedelta(days=target_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week, end_of_week
    
    @staticmethod
    def get_month_range(target_date: datetime.date) -> Tuple[datetime.date, datetime.date]:
        """获取指定日期所在月的起止日期
        
        Args:
            target_date: 目标日期
            
        Returns:
            (月初日期, 月末日期) 元组
        """
        start_of_month = target_date.replace(day=1)
        
        # 计算月末日期
        if start_of_month.month == 12:
            next_month = start_of_month.replace(year=start_of_month.year + 1, month=1, day=1)
        else:
            next_month = start_of_month.replace(month=start_of_month.month + 1, day=1)
        
        end_of_month = next_month - timedelta(days=1)
        return start_of_month, end_of_month
    
    @staticmethod
    def seconds_to_hms(seconds: int) -> Tuple[int, int, int]:
        """将秒数转换为时分秒元组
        
        Args:
            seconds: 秒数
            
        Returns:
            (小时, 分钟, 秒) 元组
        """
        if seconds < 0:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return hours, minutes, secs
    
    @staticmethod
    def hms_to_seconds(hours: int, minutes: int, seconds: int = 0) -> int:
        """将时分秒转换为秒数
        
        Args:
            hours: 小时
            minutes: 分钟
            seconds: 秒
            
        Returns:
            总秒数
        """
        return hours * 3600 + minutes * 60 + seconds
