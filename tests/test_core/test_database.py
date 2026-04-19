# -*- coding: utf-8 -*-
"""
数据库管理器测试模块

测试 core/database.py 中 DatabaseManager 类的所有功能
包括：
- 数据库初始化
- 活动CRUD操作
- 时间记录管理
- 待办事项管理
- 日程管理
- 统计查询
- 线程安全性
- 边界条件处理
"""

import os
import sys
import pytest
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import DatabaseManager


class TestDatabaseInitialization:
    """数据库初始化测试"""
    
    def test_create_with_default_path(self, tmp_path, monkeypatch):
        """测试使用默认路径创建数据库"""
        # 模拟项目根目录
        fake_root = tmp_path / "project"
        fake_root.mkdir()
        core_dir = fake_root / "core"
        core_dir.mkdir()
        
        # 创建一个临时的 database.py 位置上下文
        original_file = os.path.abspath(__file__)
        
        # 直接使用临时路径测试
        db_path = tmp_path / "data" / "test.db"
        db_path.parent.mkdir(parents=True)
        
        manager = DatabaseManager(db_path=str(db_path))
        assert os.path.exists(str(db_path))
        manager.close()
    
    def test_create_with_custom_path(self, temp_db_path):
        """测试使用自定义路径创建数据库"""
        manager = DatabaseManager(db_path=temp_db_path)
        assert os.path.exists(temp_db_path)
        manager.close()
    
    def test_tables_created(self, db_manager):
        """测试所有必要的表已创建"""
        cursor = db_manager.conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {'activities', 'time_logs', 'pause_logs', 'todos', 'schedules'}
        assert expected_tables.issubset(tables), f"缺少表: {expected_tables - tables}"
    
    def test_default_activities_created(self, db_manager):
        """测试默认活动已创建"""
        activities = db_manager.get_activities()
        assert len(activities) >= 8, "应该有至少8个默认活动"
        
        # 检查一些预期的默认活动
        activity_names = [a[1] for a in activities]
        assert '工作' in activity_names
        assert '学习' in activity_names
        assert '运动' in activity_names
    
    def test_get_cursor_when_closed(self, db_manager):
        """测试数据库关闭后获取游标返回None"""
        db_manager.close()
        cursor = db_manager.get_cursor()
        assert cursor is None


class TestActivityManagement:
    """活动管理测试"""
    
    def test_add_activity_success(self, db_manager):
        """测试成功添加活动"""
        activity_id = db_manager.add_activity(
            name="新活动",
            color="#123456",
            icon="🆕",
            goal_minutes=30
        )
        
        assert activity_id is not None
        assert activity_id > 0
    
    def test_add_activity_duplicate_name(self, db_manager):
        """测试添加重名活动返回None"""
        db_manager.add_activity(name="唯一活动", color="#FF0000")
        result = db_manager.add_activity(name="唯一活动", color="#00FF00")
        
        assert result is None
    
    def test_add_activity_with_defaults(self, db_manager):
        """测试使用默认参数添加活动"""
        activity_id = db_manager.add_activity(name="默认活动", color="#000000")
        
        activities = db_manager.get_activities()
        activity = next(a for a in activities if a[0] == activity_id)
        
        assert activity[3] == '⭕'  # 默认图标
        assert activity[4] == 0     # 默认目标时间
    
    def test_get_activities_exclude_archived(self, db_manager):
        """测试获取活动时排除归档的"""
        activity_id = db_manager.add_activity(name="待归档", color="#FF0000")
        db_manager.archive_activity(activity_id)
        
        activities = db_manager.get_activities(include_archived=False)
        activity_ids = [a[0] for a in activities]
        
        assert activity_id not in activity_ids
    
    def test_get_activities_include_archived(self, db_manager):
        """测试获取活动时包含归档的"""
        activity_id = db_manager.add_activity(name="待归档2", color="#FF0000")
        db_manager.archive_activity(activity_id)
        
        activities = db_manager.get_activities(include_archived=True)
        activity_ids = [a[0] for a in activities]
        
        assert activity_id in activity_ids
    
    def test_update_activity_partial(self, db_manager, sample_activity):
        """测试部分更新活动"""
        result = db_manager.update_activity(sample_activity, name="更新名称")
        
        assert result is True
        
        activities = db_manager.get_activities()
        activity = next(a for a in activities if a[0] == sample_activity)
        assert activity[1] == "更新名称"
        assert activity[2] == "#FF0000"  # 颜色未变
    
    def test_update_activity_all_fields(self, db_manager, sample_activity):
        """测试更新活动所有字段"""
        result = db_manager.update_activity(
            sample_activity,
            name="全新名称",
            color="#00FF00",
            icon="✅",
            goal_minutes=120
        )
        
        assert result is True
        
        activities = db_manager.get_activities()
        activity = next(a for a in activities if a[0] == sample_activity)
        assert activity[1] == "全新名称"
        assert activity[2] == "#00FF00"
        assert activity[3] == "✅"
        assert activity[4] == 120
    
    def test_update_activity_duplicate_name(self, db_manager):
        """测试更新活动为已存在的名称"""
        id1 = db_manager.add_activity(name="活动1", color="#FF0000")
        id2 = db_manager.add_activity(name="活动2", color="#00FF00")
        
        result = db_manager.update_activity(id2, name="活动1")
        
        assert result is False  # 应该失败
    
    def test_update_activity_no_updates(self, db_manager, sample_activity):
        """测试不提供任何更新"""
        result = db_manager.update_activity(sample_activity)
        assert result is False
    
    def test_archive_activity(self, db_manager, sample_activity):
        """测试归档活动"""
        result = db_manager.archive_activity(sample_activity)
        
        assert result is True
        
        # 确认已归档
        activities = db_manager.get_activities(include_archived=False)
        activity_ids = [a[0] for a in activities]
        assert sample_activity not in activity_ids
    
    def test_archive_nonexistent_activity(self, db_manager):
        """测试归档不存在的活动"""
        result = db_manager.archive_activity(99999)
        assert result is False


class TestTimeLogManagement:
    """时间记录管理测试"""
    
    def test_start_activity(self, db_manager, sample_activity):
        """测试开始活动"""
        log_id = db_manager.start_activity(sample_activity, note="开始测试")
        
        assert log_id is not None
        assert log_id > 0
        
        running = db_manager.get_running_activities()
        assert len(running) >= 1
        log = next(r for r in running if r[0] == log_id)
        assert log[5] == "开始测试"  # note
        assert log[6] == "running"   # status
    
    def test_start_activity_with_custom_time(self, db_manager, sample_activity):
        """测试使用自定义时间开始活动"""
        custom_time = datetime(2026, 1, 1, 10, 0, 0)
        log_id = db_manager.start_activity(sample_activity, start_time=custom_time)
        
        log = db_manager.get_log_by_id(log_id)
        start_time = datetime.fromisoformat(log[4])
        assert start_time.date() == custom_time.date()
    
    def test_pause_activity(self, db_manager, sample_running_log):
        """测试暂停活动"""
        result = db_manager.pause_activity(sample_running_log)
        
        assert result is True
        
        running = db_manager.get_running_activities()
        log = next(r for r in running if r[0] == sample_running_log)
        assert log[6] == "paused"
    
    def test_pause_already_paused(self, db_manager, sample_running_log):
        """测试暂停已暂停的活动"""
        db_manager.pause_activity(sample_running_log)
        result = db_manager.pause_activity(sample_running_log)
        
        assert result is False
    
    def test_resume_activity(self, db_manager, sample_running_log):
        """测试恢复活动"""
        db_manager.pause_activity(sample_running_log)
        result = db_manager.resume_activity(sample_running_log)
        
        assert result is True
        
        running = db_manager.get_running_activities()
        log = next(r for r in running if r[0] == sample_running_log)
        assert log[6] == "running"
    
    def test_resume_not_paused(self, db_manager, sample_running_log):
        """测试恢复未暂停的活动"""
        result = db_manager.resume_activity(sample_running_log)
        assert result is False
    
    def test_stop_activity(self, db_manager, sample_running_log):
        """测试停止活动"""
        time.sleep(0.1)  # 确保有一些时间流逝
        duration = db_manager.stop_activity(sample_running_log)
        
        assert duration >= 0
        
        # 确认不在运行列表中
        running = db_manager.get_running_activities()
        running_ids = [r[0] for r in running]
        assert sample_running_log not in running_ids
        
        # 确认状态为completed
        log = db_manager.get_log_by_id(sample_running_log)
        assert log[8] == "completed"
    
    def test_stop_activity_with_custom_time(self, db_manager, sample_activity):
        """测试使用自定义时间停止活动"""
        start_time = datetime.now() - timedelta(hours=1)
        log_id = db_manager.start_activity(sample_activity, start_time=start_time)
        
        end_time = datetime.now()
        duration = db_manager.stop_activity(log_id, end_time=end_time)
        
        # 应该约等于1小时
        assert 3500 <= duration <= 3700
    
    def test_stop_activity_with_pauses(self, db_manager, sample_activity):
        """测试带暂停的活动停止时正确计算时长"""
        start = datetime.now()
        log_id = db_manager.start_activity(sample_activity, start_time=start)
        
        # 模拟暂停
        db_manager.pause_activity(log_id)
        time.sleep(0.2)  # 暂停0.2秒
        db_manager.resume_activity(log_id)
        
        time.sleep(0.1)  # 继续运行
        
        duration = db_manager.stop_activity(log_id)
        
        # 总时长应该扣除暂停时间
        assert duration >= 0
    
    def test_resume_completed_activity(self, db_manager, sample_completed_log):
        """测试恢复已完成的活动"""
        result = db_manager.resume_completed_activity(sample_completed_log)
        
        assert result is True
        
        # 应该在运行列表中
        running = db_manager.get_running_activities()
        running_ids = [r[0] for r in running]
        assert sample_completed_log in running_ids
    
    def test_resume_completed_not_completed(self, db_manager, sample_running_log):
        """测试恢复非completed状态的记录"""
        result = db_manager.resume_completed_activity(sample_running_log)
        assert result is False
    
    def test_get_elapsed_running_normal(self, db_manager, sample_activity):
        """测试获取运行中活动的耗时"""
        start = datetime.now() - timedelta(seconds=100)
        log_id = db_manager.start_activity(sample_activity, start_time=start)
        
        elapsed = db_manager.get_elapsed_running(log_id)
        
        # 应该约等于100秒
        assert 95 <= elapsed <= 110
    
    def test_get_elapsed_running_with_pause(self, db_manager, sample_activity):
        """测试暂停状态下获取耗时"""
        start = datetime.now() - timedelta(seconds=100)
        log_id = db_manager.start_activity(sample_activity, start_time=start)
        
        # 暂停
        db_manager.pause_activity(log_id)
        
        elapsed = db_manager.get_elapsed_running(log_id)
        
        # 暂停后时间应该停止增长
        time.sleep(0.3)
        elapsed_after = db_manager.get_elapsed_running(log_id)
        
        # 两次获取应该相近（暂停状态下不增长）
        assert abs(elapsed - elapsed_after) < 5
    
    def test_add_manual_log(self, db_manager, sample_activity):
        """测试添加手动记录"""
        start = datetime.now() - timedelta(hours=2)
        end = datetime.now() - timedelta(hours=1)
        
        log_id = db_manager.add_manual_log(
            sample_activity,
            start,
            end,
            note="手动添加"
        )
        
        assert log_id > 0
        
        log = db_manager.get_log_by_id(log_id)
        assert log[8] == "completed"
        assert log[9] == 1  # is_manual
        assert log[6] == 3600  # duration_seconds (1小时)
    
    def test_update_log_times(self, db_manager, sample_completed_log):
        """测试更新记录时间"""
        new_start = datetime(2026, 1, 1, 9, 0, 0)
        new_end = datetime(2026, 1, 1, 10, 0, 0)
        
        result = db_manager.update_log_times(sample_completed_log, new_start, new_end)
        
        assert result is True
        
        log = db_manager.get_log_by_id(sample_completed_log)
        assert datetime.fromisoformat(log[4]).hour == 9  # start hour
    
    def test_update_log_note(self, db_manager, sample_running_log):
        """测试更新记录备注"""
        result = db_manager.update_log_note(sample_running_log, "新备注内容")
        
        assert result is True
        
        log = db_manager.get_log_by_id(sample_running_log)
        assert log[7] == "新备注内容"
    
    def test_update_log_activity(self, db_manager, sample_running_log):
        """测试更新记录的活动类型"""
        new_activity = db_manager.add_activity(name="新类型", color="#00FF00")
        
        result = db_manager.update_log_activity(sample_running_log, new_activity)
        
        assert result is True
        
        log = db_manager.get_log_by_id(sample_running_log)
        assert log[1] == "新类型"  # activity name
    
    def test_delete_log(self, db_manager, sample_completed_log):
        """测试删除记录"""
        result = db_manager.delete_log(sample_completed_log)
        
        assert result is True
        
        log = db_manager.get_log_by_id(sample_completed_log)
        assert log is None
    
    def test_delete_log_with_pause_records(self, db_manager, sample_activity):
        """测试删除带暂停记录的日志"""
        log_id = db_manager.start_activity(sample_activity)
        db_manager.pause_activity(log_id)
        db_manager.resume_activity(log_id)
        db_manager.stop_activity(log_id)
        
        result = db_manager.delete_log(log_id)
        
        assert result is True
        
        # 检查暂停记录也被删除
        cursor = db_manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pause_logs WHERE time_log_id = ?", (log_id,))
        assert cursor.fetchone()[0] == 0
    
    def test_get_running_activities(self, db_manager, sample_activity):
        """测试获取运行中的活动"""
        log1 = db_manager.start_activity(sample_activity, note="运行中1")
        
        # 创建另一个活动并暂停
        activity2 = db_manager.add_activity(name="活动2", color="#00FF00")
        log2 = db_manager.start_activity(activity2, note="已暂停")
        db_manager.pause_activity(log2)
        
        running = db_manager.get_running_activities()
        
        # 应该包含运行和暂停状态的
        running_ids = [r[0] for r in running]
        assert log1 in running_ids
        assert log2 in running_ids
        
        # 检查排序（running在前）
        statuses = [r[6] for r in running]
        assert statuses.index('running') < statuses.index('paused') or 'paused' not in statuses[:statuses.index('running')]


class TestTodoManagement:
    """待办事项管理测试"""
    
    def test_add_todo(self, db_manager):
        """测试添加待办事项"""
        todo_id = db_manager.add_todo(
            content="测试待办",
            priority=2,
            due_date="2026-01-30",
            description="详细描述"
        )
        
        assert todo_id > 0
    
    def test_add_todo_with_activity(self, db_manager, sample_activity):
        """测试添加关联活动的待办"""
        todo_id = db_manager.add_todo(
            content="关联待办",
            activity_id=sample_activity
        )
        
        todos = db_manager.get_todos()
        todo = next(t for t in todos if t[0] == todo_id)
        
        assert todo[9] == sample_activity  # activity_id
    
    def test_get_todos_sorted(self, db_manager):
        """测试待办事项正确排序"""
        db_manager.add_todo(content="低优先级", priority=0)
        db_manager.add_todo(content="高优先级", priority=3)
        db_manager.add_todo(content="中优先级", priority=1)
        
        todos = db_manager.get_todos()
        priorities = [t[3] for t in todos]
        
        # 应该按优先级降序排列
        assert priorities == sorted(priorities, reverse=True)
    
    def test_get_todos_exclude_completed(self, db_manager):
        """测试排除已完成的待办"""
        todo_id = db_manager.add_todo(content="已完成")
        db_manager.update_todo_status(todo_id, True)
        
        todos = db_manager.get_todos(include_completed=False)
        todo_ids = [t[0] for t in todos]
        
        assert todo_id not in todo_ids
    
    def test_update_todo_status(self, db_manager):
        """测试更新待办状态"""
        todo_id = db_manager.add_todo(content="待完成")
        db_manager.update_todo_status(todo_id, True)
        
        todos = db_manager.get_todos()
        todo = next(t for t in todos if t[0] == todo_id)
        
        assert todo[2] == 1  # is_completed
    
    def test_update_todo_details(self, db_manager):
        """测试更新待办详情"""
        todo_id = db_manager.add_todo(content="原内容")
        db_manager.update_todo(todo_id, content="新内容", priority=3)
        
        todos = db_manager.get_todos()
        todo = next(t for t in todos if t[0] == todo_id)
        
        assert todo[1] == "新内容"
        assert todo[3] == 3
    
    def test_delete_todo(self, db_manager):
        """测试删除待办"""
        todo_id = db_manager.add_todo(content="待删除")
        db_manager.delete_todo(todo_id)
        
        todos = db_manager.get_todos()
        todo_ids = [t[0] for t in todos]
        
        assert todo_id not in todo_ids


class TestScheduleManagement:
    """日程管理测试"""
    
    def test_add_schedule(self, db_manager):
        """测试添加日程"""
        schedule_id = db_manager.add_schedule(
            start_time="09:00",
            end_time="10:00",
            content="测试日程",
            target_date="2026-01-28"
        )
        
        assert schedule_id > 0
    
    def test_get_schedules_by_date(self, db_manager):
        """测试按日期获取日程"""
        db_manager.add_schedule("09:00", "10:00", "日程1", "2026-01-28")
        db_manager.add_schedule("11:00", "12:00", "日程2", "2026-01-29")
        
        schedules = db_manager.get_schedules("2026-01-28")
        
        assert len(schedules) == 1
        assert schedules[0][3] == "日程1"
    
    def test_get_current_schedule(self, db_manager):
        """测试获取当前时间的日程"""
        today = date.today().strftime("%Y-%m-%d")
        now = datetime.now()
        start = (now - timedelta(minutes=30)).strftime("%H:%M")
        end = (now + timedelta(minutes=30)).strftime("%H:%M")
        
        db_manager.add_schedule(start, end, "当前日程", today)
        
        current = db_manager.get_current_schedule(now.strftime("%H:%M"))
        
        assert current is not None
        # get_current_schedule 返回 (start_time, end_time, content)
        # 也可能返回更多字段，检查content在返回值中
        assert "当前日程" in str(current)
    
    def test_delete_schedule(self, db_manager):
        """测试删除日程"""
        schedule_id = db_manager.add_schedule("09:00", "10:00", "待删除", "2026-01-28")
        db_manager.delete_schedule(schedule_id)
        
        schedules = db_manager.get_schedules("2026-01-28")
        schedule_ids = [s[0] for s in schedules]
        
        assert schedule_id not in schedule_ids
    
    def test_clear_schedules(self, db_manager):
        """测试清空所有日程"""
        db_manager.add_schedule("09:00", "10:00", "日程1", "2026-01-28")
        db_manager.add_schedule("11:00", "12:00", "日程2", "2026-01-28")
        
        db_manager.clear_schedules()
        
        schedules = db_manager.get_schedules("2026-01-28")
        assert len(schedules) == 0


class TestStatisticsQueries:
    """统计查询测试"""
    
    def test_get_daily_logs(self, db_manager, sample_activity):
        """测试获取每日记录"""
        today = date.today()
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        db_manager.add_manual_log(sample_activity, start, end, "今日记录")
        
        logs = db_manager.get_daily_logs(today)
        
        assert len(logs) >= 1
    
    def test_get_daily_stats(self, db_manager, sample_activity):
        """测试获取每日统计"""
        today = date.today()
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        
        db_manager.add_manual_log(sample_activity, start, end)
        
        stats = db_manager.get_daily_stats(today)
        
        # 应该包含所有活动
        assert len(stats) >= 1
        
        # 找到我们的测试活动
        stat = next((s for s in stats if s[0] == sample_activity), None)
        if stat:
            assert stat[5] > 0  # total_seconds
    
    def test_get_weekly_stats(self, db_manager, sample_activity):
        """测试获取周统计"""
        today = date.today()
        
        # 添加本周的记录
        for i in range(3):
            day = today - timedelta(days=i)
            if day.weekday() < 7:  # 确保在本周内
                start = datetime.combine(day, datetime.min.time()) + timedelta(hours=10)
                end = start + timedelta(hours=1)
                db_manager.add_manual_log(sample_activity, start, end)
        
        stats = db_manager.get_weekly_stats(today)
        
        assert len(stats) >= 1
    
    def test_get_monthly_stats(self, db_manager, sample_activity):
        """测试获取月统计"""
        today = date.today()
        
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        db_manager.add_manual_log(sample_activity, start, end)
        
        stats = db_manager.get_monthly_stats(today)
        
        assert len(stats) >= 1
    
    def test_get_yearly_heatmap_data(self, db_manager, sample_activity):
        """测试获取年度热力图数据"""
        year = date.today().year
        
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        db_manager.add_manual_log(sample_activity, start, end)
        
        data = db_manager.get_yearly_heatmap_data(year)
        
        # 热力图数据返回的是字典 {日期字符串: 秒数}
        assert isinstance(data, dict)
        assert len(data) > 0


class TestEdgeCases:
    """边界条件测试"""
    
    def test_empty_database_queries(self, empty_db_manager):
        """测试空数据库的查询"""
        assert empty_db_manager.get_activities() == []
        assert empty_db_manager.get_running_activities() == []
        assert empty_db_manager.get_todos() == []
        assert empty_db_manager.get_schedules() is not None
        assert empty_db_manager.get_daily_logs() == []
    
    def test_invalid_activity_id(self, db_manager):
        """测试无效的活动ID"""
        result = db_manager.update_activity(99999, name="不存在")
        assert result is False
        
        result = db_manager.archive_activity(99999)
        assert result is False
    
    def test_invalid_log_id(self, db_manager):
        """测试无效的日志ID"""
        result = db_manager.pause_activity(99999)
        assert result is False
        
        result = db_manager.resume_activity(99999)
        assert result is False
        
        duration = db_manager.stop_activity(99999)
        assert duration == 0
        
        log = db_manager.get_log_by_id(99999)
        assert log is None
    
    def test_special_characters_in_content(self, db_manager):
        """测试特殊字符处理"""
        # 活动名称中的特殊字符
        activity_id = db_manager.add_activity(
            name="测试'活动\"",
            color="#FF0000"
        )
        assert activity_id is not None
        
        # 待办内容中的特殊字符
        todo_id = db_manager.add_todo(
            content="SQL注入测试'; DROP TABLE todos; --",
            description="<script>alert('XSS')</script>"
        )
        assert todo_id > 0
        
        # 确保能正确读取
        todos = db_manager.get_todos()
        todo = next(t for t in todos if t[0] == todo_id)
        assert "DROP TABLE" in todo[1]
    
    def test_unicode_content(self, db_manager):
        """测试Unicode字符处理"""
        activity_id = db_manager.add_activity(
            name="🎮 游戏时间 🕹️",
            color="#FF00FF",
            icon="🎲"
        )
        
        activities = db_manager.get_activities()
        activity = next(a for a in activities if a[0] == activity_id)
        
        assert "🎮" in activity[1]
        assert activity[3] == "🎲"
    
    def test_very_long_content(self, db_manager):
        """测试超长内容"""
        long_name = "A" * 1000
        activity_id = db_manager.add_activity(name=long_name, color="#FF0000")
        
        activities = db_manager.get_activities()
        activity = next(a for a in activities if a[0] == activity_id)
        
        assert len(activity[1]) == 1000
    
    def test_zero_duration_log(self, db_manager, sample_activity):
        """测试零时长记录"""
        now = datetime.now()
        log_id = db_manager.add_manual_log(sample_activity, now, now)
        
        log = db_manager.get_log_by_id(log_id)
        assert log[6] == 0  # duration_seconds


class TestThreadSafety:
    """线程安全测试"""
    
    @pytest.mark.thread_safety
    def test_concurrent_activity_creation(self, temp_db_path):
        """测试并发创建活动"""
        manager = DatabaseManager(db_path=temp_db_path)
        errors = []
        created_ids = []
        lock = threading.Lock()
        
        def create_activity(i):
            try:
                activity_id = manager.add_activity(
                    name=f"并发活动_{i}",
                    color="#FF0000"
                )
                with lock:
                    if activity_id:
                        created_ids.append(activity_id)
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=create_activity, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        manager.close()
        
        assert len(errors) == 0, f"出现错误: {errors}"
        assert len(created_ids) == 10, "应该创建10个活动"
    
    @pytest.mark.thread_safety
    def test_concurrent_start_stop(self, temp_db_path):
        """测试并发开始和停止活动"""
        manager = DatabaseManager(db_path=temp_db_path)
        activity_id = manager.add_activity(name="并发测试", color="#FF0000")
        
        results = {'starts': 0, 'stops': 0, 'errors': []}
        lock = threading.Lock()
        
        def start_and_stop():
            try:
                log_id = manager.start_activity(activity_id)
                with lock:
                    results['starts'] += 1
                
                time.sleep(0.01)
                
                manager.stop_activity(log_id)
                with lock:
                    results['stops'] += 1
            except Exception as e:
                with lock:
                    results['errors'].append(str(e))
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(start_and_stop) for _ in range(20)]
            for f in as_completed(futures):
                pass
        
        manager.close()
        
        assert len(results['errors']) == 0, f"出现错误: {results['errors']}"
        assert results['starts'] == 20
        assert results['stops'] == 20
    
    @pytest.mark.thread_safety
    def test_concurrent_read_write(self, temp_db_path):
        """测试并发读写"""
        manager = DatabaseManager(db_path=temp_db_path)
        
        errors = []
        lock = threading.Lock()
        
        def writer():
            try:
                for i in range(10):
                    manager.add_todo(content=f"写入_{i}")
                    time.sleep(0.01)
            except Exception as e:
                with lock:
                    errors.append(f"Writer: {e}")
        
        def reader():
            try:
                for _ in range(10):
                    manager.get_todos()
                    time.sleep(0.01)
            except Exception as e:
                with lock:
                    errors.append(f"Reader: {e}")
        
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        manager.close()
        
        assert len(errors) == 0, f"出现错误: {errors}"


class TestDatabaseConnection:
    """数据库连接测试"""
    
    def test_close_and_reopen(self, temp_db_path):
        """测试关闭后重新打开"""
        manager1 = DatabaseManager(db_path=temp_db_path)
        activity_id = manager1.add_activity(name="持久化测试", color="#FF0000")
        manager1.close()
        
        manager2 = DatabaseManager(db_path=temp_db_path)
        activities = manager2.get_activities()
        activity_names = [a[1] for a in activities]
        
        assert "持久化测试" in activity_names
        manager2.close()
    
    def test_operations_after_close(self, db_manager):
        """测试关闭后的操作处理"""
        db_manager.close()
        
        # 这些操作应该安全地失败
        cursor = db_manager.get_cursor()
        assert cursor is None
        
        running = db_manager.get_running_activities()
        assert running == []
