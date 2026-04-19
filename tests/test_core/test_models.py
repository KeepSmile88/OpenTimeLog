# -*- coding: utf-8 -*-
"""
数据模型测试模块

测试 core/models.py 中的数据模型类
包括：
- Activity 活动数据模型
- TimeLog 时间记录数据模型
- PauseLog 暂停记录数据模型
- DailyStats 每日统计数据模型
"""

import os
import sys
import pytest
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.models import Activity, TimeLog, PauseLog, DailyStats


class TestActivityModel:
    """Activity 模型测试"""
    
    def test_from_tuple_full_data(self):
        """测试完整数据元组创建Activity"""
        data = (1, "工作", "#FF6B6B", "💼", 480, 0, "2026-01-28T10:00:00")
        
        activity = Activity.from_tuple(data)
        
        assert activity.id == 1
        assert activity.name == "工作"
        assert activity.color == "#FF6B6B"
        assert activity.icon == "💼"
        assert activity.goal_minutes == 480
        assert activity.is_archived is False
        assert activity.created_at == datetime(2026, 1, 28, 10, 0, 0)
    
    def test_from_tuple_minimal_data(self):
        """测试最小数据元组创建Activity"""
        data = (1, "工作", "#FF6B6B")
        
        activity = Activity.from_tuple(data)
        
        assert activity.id == 1
        assert activity.name == "工作"
        assert activity.color == "#FF6B6B"
        assert activity.icon == '⭕'  # 默认值
        assert activity.goal_minutes == 0  # 默认值
        assert activity.is_archived is False  # 默认值
        assert activity.created_at is None  # 默认值
    
    def test_from_tuple_with_none_datetime(self):
        """测试空日期时间"""
        data = (1, "工作", "#FF6B6B", "💼", 480, 0, None)
        
        activity = Activity.from_tuple(data)
        
        assert activity.created_at is None
    
    def test_from_tuple_archived_true(self):
        """测试已归档的活动"""
        data = (1, "工作", "#FF6B6B", "💼", 480, 1, None)
        
        activity = Activity.from_tuple(data)
        
        assert activity.is_archived is True
    
    def test_default_values(self):
        """测试默认值"""
        activity = Activity(id=1, name="测试", color="#FF0000")
        
        assert activity.icon == '⭕'
        assert activity.goal_minutes == 0
        assert activity.is_archived is False
        assert activity.created_at is None
    
    def test_equality(self):
        """测试对象相等性"""
        activity1 = Activity(id=1, name="测试", color="#FF0000")
        activity2 = Activity(id=1, name="测试", color="#FF0000")
        
        assert activity1 == activity2
    
    def test_unicode_content(self):
        """测试Unicode内容"""
        data = (1, "🎮 游戏", "#FF0000", "🎲", 0, False, None)
        
        activity = Activity.from_tuple(data)
        
        assert "🎮" in activity.name
        assert activity.icon == "🎲"


class TestTimeLogModel:
    """TimeLog 模型测试"""
    
    def test_from_tuple_basic(self):
        """测试基本元组创建TimeLog"""
        data = (
            1,                          # id
            2,                          # activity_id
            "2026-01-28T10:00:00",     # start_time
            "2026-01-28T11:00:00",     # end_time
            3600,                       # duration_seconds
            "completed",                # status
            "测试备注",                 # note
            0,                          # is_manual
            0                           # paused_duration
        )
        
        log = TimeLog.from_tuple(data)
        
        assert log.id == 1
        assert log.activity_id == 2
        assert log.start_time == datetime(2026, 1, 28, 10, 0, 0)
        assert log.end_time == datetime(2026, 1, 28, 11, 0, 0)
        assert log.duration_seconds == 3600
        assert log.status == "completed"
        assert log.note == "测试备注"
        assert log.is_manual is False
        assert log.paused_duration == 0
    
    def test_from_tuple_with_activity(self):
        """测试带活动信息的元组"""
        data = (
            1,                          # id
            "工作",                     # activity name
            "#FF6B6B",                  # activity color
            "💼",                       # activity icon
            "2026-01-28T10:00:00",     # start_time
            "测试备注",                 # note
            "running"                   # status
        )
        
        log = TimeLog.from_tuple(data, include_activity=True)
        
        assert log.id == 1
        assert log.activity_name == "工作"
        assert log.activity_color == "#FF6B6B"
        assert log.activity_icon == "💼"
        assert log.start_time == datetime(2026, 1, 28, 10, 0, 0)
        assert log.note == "测试备注"
        assert log.status == "running"
    
    def test_from_tuple_null_end_time(self):
        """测试空结束时间"""
        data = (1, 2, "2026-01-28T10:00:00", None, None, "running", "")
        
        log = TimeLog.from_tuple(data)
        
        assert log.end_time is None
        assert log.duration_seconds is None
    
    def test_from_tuple_minimal(self):
        """测试最小数据"""
        data = (1, 2, "2026-01-28T10:00:00")
        
        log = TimeLog.from_tuple(data)
        
        assert log.id == 1
        assert log.activity_id == 2
        assert log.start_time == datetime(2026, 1, 28, 10, 0, 0)
        assert log.status == "running"  # 默认值
    
    def test_default_values(self):
        """测试默认值"""
        log = TimeLog(
            id=1,
            activity_id=1,
            start_time=datetime.now()
        )
        
        assert log.end_time is None
        assert log.duration_seconds is None
        assert log.status == 'running'
        assert log.note == ''
        assert log.is_manual is False
        assert log.paused_duration == 0
        assert log.activity_name == ''
        assert log.activity_color == ''
        assert log.activity_icon == ''
    
    def test_datetime_string_parsing(self):
        """测试日期时间字符串解析"""
        data = (1, 2, "2026-01-28T10:30:45", "2026-01-28T11:30:45", 3600, "completed", "")
        
        log = TimeLog.from_tuple(data)
        
        assert log.start_time.hour == 10
        assert log.start_time.minute == 30
        assert log.start_time.second == 45
        assert log.end_time.hour == 11


class TestPauseLogModel:
    """PauseLog 模型测试"""
    
    def test_from_tuple_complete(self):
        """测试完整暂停记录"""
        data = (
            1,                          # id
            10,                         # time_log_id
            "2026-01-28T10:30:00",     # pause_start
            "2026-01-28T10:45:00",     # pause_end
            "2026-01-28T10:30:00"      # created_at
        )
        
        pause = PauseLog.from_tuple(data)
        
        assert pause.id == 1
        assert pause.time_log_id == 10
        assert pause.pause_start == datetime(2026, 1, 28, 10, 30, 0)
        assert pause.pause_end == datetime(2026, 1, 28, 10, 45, 0)
        assert pause.created_at == datetime(2026, 1, 28, 10, 30, 0)
    
    def test_from_tuple_ongoing_pause(self):
        """测试进行中的暂停（无结束时间）"""
        data = (1, 10, "2026-01-28T10:30:00", None)
        
        pause = PauseLog.from_tuple(data)
        
        assert pause.pause_end is None
    
    def test_from_tuple_minimal(self):
        """测试最小数据"""
        data = (1, 10, "2026-01-28T10:30:00")
        
        pause = PauseLog.from_tuple(data)
        
        assert pause.id == 1
        assert pause.time_log_id == 10
        assert pause.pause_start == datetime(2026, 1, 28, 10, 30, 0)
        assert pause.pause_end is None
        assert pause.created_at is None
    
    def test_default_values(self):
        """测试默认值"""
        pause = PauseLog(
            id=1,
            time_log_id=10,
            pause_start=datetime.now()
        )
        
        assert pause.pause_end is None
        assert pause.created_at is None


class TestDailyStatsModel:
    """DailyStats 模型测试"""
    
    def test_from_tuple(self):
        """测试元组创建DailyStats"""
        data = (1, "工作", "#FF6B6B", "💼", 480, 7200, 3)
        
        stats = DailyStats.from_tuple(data)
        
        assert stats.activity_id == 1
        assert stats.activity_name == "工作"
        assert stats.activity_color == "#FF6B6B"
        assert stats.activity_icon == "💼"
        assert stats.goal_minutes == 480
        assert stats.total_seconds == 7200
        assert stats.session_count == 3
    
    def test_total_minutes_property(self):
        """测试总分钟数计算"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=3600,  # 1小时
            session_count=1
        )
        
        assert stats.total_minutes == 60
    
    def test_total_minutes_with_partial_seconds(self):
        """测试带余数的秒数转分钟"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=3661,  # 61分钟1秒 -> 应该是61分钟（整除）
            session_count=1
        )
        
        assert stats.total_minutes == 61  # 3661 // 60 = 61
    
    def test_completion_rate_normal(self):
        """测试正常完成率计算"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=3600,  # 正好60分钟
            session_count=1
        )
        
        assert stats.completion_rate == 100.0
    
    def test_completion_rate_over_100(self):
        """测试超过100%的完成率"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=7200,  # 120分钟，目标60分钟
            session_count=2
        )
        
        assert stats.completion_rate == 200.0
    
    def test_completion_rate_zero_goal(self):
        """测试目标为0时的完成率"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=0,
            total_seconds=3600,
            session_count=1
        )
        
        assert stats.completion_rate == 0.0
    
    def test_completion_rate_negative_goal(self):
        """测试负数目标时的完成率"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=-60,  # 负数目标
            total_seconds=3600,
            session_count=1
        )
        
        assert stats.completion_rate == 0.0
    
    def test_completion_rate_partial(self):
        """测试部分完成率"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=1800,  # 30分钟
            session_count=1
        )
        
        assert stats.completion_rate == 50.0


class TestModelIntegrity:
    """模型完整性测试"""
    
    def test_activity_fields_exist(self):
        """验证Activity所有字段存在"""
        activity = Activity(
            id=1,
            name="测试",
            color="#FF0000"
        )
        
        # 检查所有字段可访问
        assert hasattr(activity, 'id')
        assert hasattr(activity, 'name')
        assert hasattr(activity, 'color')
        assert hasattr(activity, 'icon')
        assert hasattr(activity, 'goal_minutes')
        assert hasattr(activity, 'is_archived')
        assert hasattr(activity, 'created_at')
    
    def test_timelog_fields_exist(self):
        """验证TimeLog所有字段存在"""
        log = TimeLog(
            id=1,
            activity_id=1,
            start_time=datetime.now()
        )
        
        assert hasattr(log, 'id')
        assert hasattr(log, 'activity_id')
        assert hasattr(log, 'start_time')
        assert hasattr(log, 'end_time')
        assert hasattr(log, 'duration_seconds')
        assert hasattr(log, 'status')
        assert hasattr(log, 'note')
        assert hasattr(log, 'is_manual')
        assert hasattr(log, 'paused_duration')
        assert hasattr(log, 'activity_name')
        assert hasattr(log, 'activity_color')
        assert hasattr(log, 'activity_icon')
    
    def test_pauselog_fields_exist(self):
        """验证PauseLog所有字段存在"""
        pause = PauseLog(
            id=1,
            time_log_id=1,
            pause_start=datetime.now()
        )
        
        assert hasattr(pause, 'id')
        assert hasattr(pause, 'time_log_id')
        assert hasattr(pause, 'pause_start')
        assert hasattr(pause, 'pause_end')
        assert hasattr(pause, 'created_at')
    
    def test_dailystats_fields_exist(self):
        """验证DailyStats所有字段存在"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=3600,
            session_count=1
        )
        
        assert hasattr(stats, 'activity_id')
        assert hasattr(stats, 'activity_name')
        assert hasattr(stats, 'activity_color')
        assert hasattr(stats, 'activity_icon')
        assert hasattr(stats, 'goal_minutes')
        assert hasattr(stats, 'total_seconds')
        assert hasattr(stats, 'session_count')
        assert hasattr(stats, 'total_minutes')
        assert hasattr(stats, 'completion_rate')


class TestModelEdgeCases:
    """模型边界情况测试"""
    
    def test_activity_empty_strings(self):
        """测试空字符串"""
        data = (1, "", "", "", 0, False, None)
        
        activity = Activity.from_tuple(data)
        
        assert activity.name == ""
        assert activity.color == ""
    
    def test_timelog_zero_duration(self):
        """测试零时长"""
        data = (1, 1, "2026-01-28T10:00:00", "2026-01-28T10:00:00", 0, "completed", "")
        
        log = TimeLog.from_tuple(data)
        
        assert log.duration_seconds == 0
    
    def test_dailystats_zero_sessions(self):
        """测试零会话数"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=60,
            total_seconds=0,
            session_count=0
        )
        
        assert stats.session_count == 0
        assert stats.total_minutes == 0
        assert stats.completion_rate == 0.0
    
    def test_large_numbers(self):
        """测试大数值"""
        stats = DailyStats(
            activity_id=1,
            activity_name="测试",
            activity_color="#FF0000",
            activity_icon="🧪",
            goal_minutes=1440,  # 24小时
            total_seconds=86400,  # 24小时
            session_count=100
        )
        
        assert stats.total_minutes == 1440
        assert stats.completion_rate == 100.0
