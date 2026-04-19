# -*- coding: utf-8 -*-
"""
时间计算器测试模块

测试 core/time_calculator.py 中的 TimeCalculator 类
包括：
- 时长格式化
- 日期范围计算
- 时间解析
- 单位转换
"""

import os
import sys
import pytest
from datetime import datetime, timedelta, date

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.time_calculator import TimeCalculator


class TestFormatDuration:
    """format_duration 方法测试"""
    
    def test_zero_seconds(self):
        """测试0秒"""
        result = TimeCalculator.format_duration(0)
        assert result == "00:00:00"
    
    def test_negative_seconds(self):
        """测试负数秒"""
        result = TimeCalculator.format_duration(-10)
        assert result == "00:00:00"
    
    def test_one_second(self):
        """测试1秒"""
        result = TimeCalculator.format_duration(1)
        assert result == "00:00:01"
    
    def test_one_minute(self):
        """测试1分钟"""
        result = TimeCalculator.format_duration(60)
        assert result == "00:01:00"
    
    def test_one_hour(self):
        """测试1小时"""
        result = TimeCalculator.format_duration(3600)
        assert result == "01:00:00"
    
    def test_mixed_time(self):
        """测试混合时间"""
        result = TimeCalculator.format_duration(3661)  # 1小时1分钟1秒
        assert result == "01:01:01"
    
    def test_large_hours(self):
        """测试大小时数"""
        result = TimeCalculator.format_duration(100 * 3600)  # 100小时
        assert result == "100:00:00"
    
    def test_max_within_day(self):
        """测试一天内的最大值"""
        result = TimeCalculator.format_duration(86399)  # 23:59:59
        assert result == "23:59:59"


class TestFormatDurationHM:
    """format_duration_hm 方法测试"""
    
    def test_zero_seconds(self):
        """测试0秒"""
        result = TimeCalculator.format_duration_hm(0)
        assert result == "0m"
    
    def test_negative_seconds(self):
        """测试负数秒"""
        result = TimeCalculator.format_duration_hm(-60)
        assert result == "0m"
    
    def test_less_than_one_minute(self):
        """测试不足1分钟"""
        result = TimeCalculator.format_duration_hm(30)
        assert result == "0m"
    
    def test_one_minute(self):
        """测试1分钟"""
        result = TimeCalculator.format_duration_hm(60)
        assert result == "1m"
    
    def test_30_minutes(self):
        """测试30分钟"""
        result = TimeCalculator.format_duration_hm(1800)
        assert result == "30m"
    
    def test_one_hour(self):
        """测试1小时"""
        result = TimeCalculator.format_duration_hm(3600)
        assert result == "1h 0m"
    
    def test_one_hour_30_minutes(self):
        """测试1小时30分钟"""
        result = TimeCalculator.format_duration_hm(5400)
        assert result == "1h 30m"
    
    def test_two_hours_45_minutes(self):
        """测试2小时45分钟"""
        result = TimeCalculator.format_duration_hm(9900)
        assert result == "2h 45m"


class TestFormatTime:
    """format_time 方法测试"""
    
    def test_midnight(self):
        """测试午夜"""
        dt = datetime(2026, 1, 28, 0, 0, 0)
        result = TimeCalculator.format_time(dt)
        assert result == "00:00"
    
    def test_noon(self):
        """测试中午"""
        dt = datetime(2026, 1, 28, 12, 0, 0)
        result = TimeCalculator.format_time(dt)
        assert result == "12:00"
    
    def test_with_seconds(self):
        """测试有秒数的时间（秒数应被忽略）"""
        dt = datetime(2026, 1, 28, 10, 30, 45)
        result = TimeCalculator.format_time(dt)
        assert result == "10:30"
    
    def test_late_night(self):
        """测试深夜"""
        dt = datetime(2026, 1, 28, 23, 59, 0)
        result = TimeCalculator.format_time(dt)
        assert result == "23:59"


class TestFormatDatetime:
    """format_datetime 方法测试"""
    
    def test_full_format(self):
        """测试完整格式"""
        dt = datetime(2026, 1, 28, 10, 30, 45)
        result = TimeCalculator.format_datetime(dt)
        assert result == "2026-01-28 10:30:45"
    
    def test_with_zeros(self):
        """测试零填充"""
        dt = datetime(2026, 1, 1, 1, 1, 1)
        result = TimeCalculator.format_datetime(dt)
        assert result == "2026-01-01 01:01:01"


class TestCalculateDuration:
    """calculate_duration 方法测试"""
    
    def test_normal_duration(self):
        """测试正常时间间隔"""
        start = datetime(2026, 1, 28, 10, 0, 0)
        end = datetime(2026, 1, 28, 11, 0, 0)
        
        result = TimeCalculator.calculate_duration(start, end)
        
        assert result == 3600  # 1小时
    
    def test_with_current_time(self):
        """测试使用当前时间"""
        start = datetime.now() - timedelta(seconds=100)
        
        result = TimeCalculator.calculate_duration(start)
        
        # 应该约等于100秒
        assert 95 <= result <= 110
    
    def test_zero_duration(self):
        """测试零时长"""
        now = datetime.now()
        result = TimeCalculator.calculate_duration(now, now)
        assert result == 0
    
    def test_negative_duration(self):
        """测试负时长（结束时间早于开始时间）"""
        start = datetime(2026, 1, 28, 11, 0, 0)
        end = datetime(2026, 1, 28, 10, 0, 0)
        
        result = TimeCalculator.calculate_duration(start, end)
        
        assert result == 0  # 应该返回0，不是负数
    
    def test_cross_day_duration(self):
        """测试跨天时长"""
        start = datetime(2026, 1, 27, 23, 0, 0)
        end = datetime(2026, 1, 28, 1, 0, 0)
        
        result = TimeCalculator.calculate_duration(start, end)
        
        assert result == 7200  # 2小时


class TestParseTimeString:
    """parse_time_string 方法测试"""
    
    def test_valid_iso_format(self):
        """测试有效的ISO格式"""
        result = TimeCalculator.parse_time_string("2026-01-28T10:30:45")
        
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 28
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45
    
    def test_date_only(self):
        """测试仅日期"""
        result = TimeCalculator.parse_time_string("2026-01-28")
        
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 28
    
    def test_invalid_format(self):
        """测试无效格式"""
        result = TimeCalculator.parse_time_string("invalid")
        assert result is None
    
    def test_empty_string(self):
        """测试空字符串"""
        result = TimeCalculator.parse_time_string("")
        assert result is None
    
    def test_none_input(self):
        """测试None输入"""
        result = TimeCalculator.parse_time_string(None)
        assert result is None
    
    def test_space_format(self):
        """测试空格分隔格式"""
        result = TimeCalculator.parse_time_string("2026-01-28 10:30:45")
        
        assert result is not None
        assert result.hour == 10


class TestGetWeekRange:
    """get_week_range 方法测试"""
    
    def test_monday(self):
        """测试周一"""
        target = date(2026, 1, 26)  # 周一
        start, end = TimeCalculator.get_week_range(target)
        
        assert start == date(2026, 1, 26)  # 周一
        assert end == date(2026, 2, 1)     # 周日
    
    def test_wednesday(self):
        """测试周三"""
        target = date(2026, 1, 28)  # 周三
        start, end = TimeCalculator.get_week_range(target)
        
        assert start == date(2026, 1, 26)  # 周一
        assert end == date(2026, 2, 1)     # 周日
    
    def test_sunday(self):
        """测试周日"""
        target = date(2026, 2, 1)  # 周日
        start, end = TimeCalculator.get_week_range(target)
        
        assert start == date(2026, 1, 26)  # 周一
        assert end == date(2026, 2, 1)     # 周日
    
    def test_cross_month(self):
        """测试跨月周"""
        target = date(2026, 1, 31)  # 周六
        start, end = TimeCalculator.get_week_range(target)
        
        assert start.month == 1
        assert end.month == 2
    
    def test_cross_year(self):
        """测试跨年周"""
        target = date(2026, 1, 1)  # 周四
        start, end = TimeCalculator.get_week_range(target)
        
        assert start.year == 2025
        assert end.year == 2026


class TestGetMonthRange:
    """get_month_range 方法测试"""
    
    def test_january(self):
        """测试1月"""
        target = date(2026, 1, 15)
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 31)
    
    def test_february_non_leap(self):
        """测试非闰年2月"""
        target = date(2026, 2, 15)
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 28)
    
    def test_february_leap(self):
        """测试闰年2月"""
        target = date(2024, 2, 15)  # 2024是闰年
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)
    
    def test_december(self):
        """测试12月（跨年）"""
        target = date(2026, 12, 15)
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2026, 12, 1)
        assert end == date(2026, 12, 31)
    
    def test_30_day_month(self):
        """测试30天的月份"""
        target = date(2026, 4, 15)  # 4月
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 30)
    
    def test_first_day_of_month(self):
        """测试月初"""
        target = date(2026, 3, 1)
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2026, 3, 1)
        assert end == date(2026, 3, 31)
    
    def test_last_day_of_month(self):
        """测试月末"""
        target = date(2026, 3, 31)
        start, end = TimeCalculator.get_month_range(target)
        
        assert start == date(2026, 3, 1)
        assert end == date(2026, 3, 31)


class TestSecondsToHMS:
    """seconds_to_hms 方法测试"""
    
    def test_zero(self):
        """测试0秒"""
        h, m, s = TimeCalculator.seconds_to_hms(0)
        assert (h, m, s) == (0, 0, 0)
    
    def test_negative(self):
        """测试负数"""
        h, m, s = TimeCalculator.seconds_to_hms(-100)
        assert (h, m, s) == (0, 0, 0)
    
    def test_seconds_only(self):
        """测试仅秒"""
        h, m, s = TimeCalculator.seconds_to_hms(45)
        assert (h, m, s) == (0, 0, 45)
    
    def test_minutes_and_seconds(self):
        """测试分钟和秒"""
        h, m, s = TimeCalculator.seconds_to_hms(125)  # 2分5秒
        assert (h, m, s) == (0, 2, 5)
    
    def test_hours_minutes_seconds(self):
        """测试时分秒"""
        h, m, s = TimeCalculator.seconds_to_hms(3661)  # 1小时1分1秒
        assert (h, m, s) == (1, 1, 1)
    
    def test_large_value(self):
        """测试大数值"""
        h, m, s = TimeCalculator.seconds_to_hms(100000)
        assert h == 27
        assert m == 46
        assert s == 40


class TestHMSToSeconds:
    """hms_to_seconds 方法测试"""
    
    def test_all_zeros(self):
        """测试全零"""
        result = TimeCalculator.hms_to_seconds(0, 0, 0)
        assert result == 0
    
    def test_hours_only(self):
        """测试仅小时"""
        result = TimeCalculator.hms_to_seconds(2, 0, 0)
        assert result == 7200
    
    def test_minutes_only(self):
        """测试仅分钟"""
        result = TimeCalculator.hms_to_seconds(0, 30, 0)
        assert result == 1800
    
    def test_seconds_only(self):
        """测试仅秒"""
        result = TimeCalculator.hms_to_seconds(0, 0, 45)
        assert result == 45
    
    def test_mixed(self):
        """测试混合"""
        result = TimeCalculator.hms_to_seconds(1, 30, 45)
        assert result == 5445
    
    def test_default_seconds(self):
        """测试默认秒数"""
        result = TimeCalculator.hms_to_seconds(1, 30)
        assert result == 5400


class TestRoundTripConversion:
    """往返转换测试"""
    
    def test_seconds_hms_roundtrip(self):
        """测试秒数往返转换"""
        original = 12345
        h, m, s = TimeCalculator.seconds_to_hms(original)
        result = TimeCalculator.hms_to_seconds(h, m, s)
        
        assert result == original
    
    def test_hms_seconds_roundtrip(self):
        """测试时分秒往返转换"""
        h, m, s = 5, 30, 15
        seconds = TimeCalculator.hms_to_seconds(h, m, s)
        h2, m2, s2 = TimeCalculator.seconds_to_hms(seconds)
        
        assert (h2, m2, s2) == (h, m, s)
    
    def test_format_parse_consistency(self):
        """测试格式化和解析的一致性"""
        original = datetime.now().replace(microsecond=0)
        formatted = TimeCalculator.format_datetime(original)
        parsed = datetime.strptime(formatted, '%Y-%m-%d %H:%M:%S')
        
        assert parsed == original
