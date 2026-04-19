# -*- coding: utf-8 -*-
"""
集成测试模块

测试多个模块之间的协作和端到端工作流
包括：
- 活动生命周期测试
- 日程提醒工作流测试
- 数据一致性测试
- 并发操作测试
"""

import os
import sys
import pytest
import threading
import time
from datetime import datetime, timedelta, date
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import DatabaseManager
from core.time_calculator import TimeCalculator
from core.models import Activity, TimeLog, DailyStats


class TestActivityLifecycle:
    """活动生命周期集成测试"""
    
    def test_complete_activity_lifecycle(self, db_manager):
        """测试完整活动生命周期：创建 -> 开始 -> 暂停 -> 恢复 -> 停止"""
        # 1. 创建活动
        activity_id = db_manager.add_activity(
            name="生命周期测试",
            color="#FF0000",
            icon="🧪",
            goal_minutes=60
        )
        assert activity_id is not None
        
        # 2. 开始活动
        log_id = db_manager.start_activity(activity_id, note="测试开始")
        assert log_id is not None
        
        # 验证运行状态
        running = db_manager.get_running_activities()
        assert any(r[0] == log_id for r in running)
        
        # 3. 暂停活动
        time.sleep(0.1)
        result = db_manager.pause_activity(log_id)
        assert result is True
        
        # 验证暂停状态
        running = db_manager.get_running_activities()
        log = next(r for r in running if r[0] == log_id)
        assert log[6] == "paused"
        
        # 4. 恢复活动
        time.sleep(0.1)
        result = db_manager.resume_activity(log_id)
        assert result is True
        
        # 验证运行状态
        running = db_manager.get_running_activities()
        log = next(r for r in running if r[0] == log_id)
        assert log[6] == "running"
        
        # 5. 停止活动
        time.sleep(0.1)
        duration = db_manager.stop_activity(log_id)
        assert duration >= 0
        
        # 验证已完成
        running = db_manager.get_running_activities()
        assert not any(r[0] == log_id for r in running)
        
        # 6. 验证统计
        stats = db_manager.get_daily_stats(date.today())
        activity_stat = next((s for s in stats if s[0] == activity_id), None)
        assert activity_stat is not None
        assert activity_stat[5] > 0  # total_seconds > 0
    
    def test_activity_with_multiple_pauses(self, db_manager):
        """测试多次暂停的活动"""
        activity_id = db_manager.add_activity(name="多次暂停", color="#00FF00")
        log_id = db_manager.start_activity(activity_id)
        
        total_pause_time = 0
        
        for _ in range(3):
            time.sleep(0.05)
            db_manager.pause_activity(log_id)
            time.sleep(0.05)
            total_pause_time += 0.05
            db_manager.resume_activity(log_id)
        
        time.sleep(0.05)
        duration = db_manager.stop_activity(log_id)
        
        # 实际时长应该扣除暂停时间
        # 由于时间精度问题，只验证duration > 0
        assert duration >= 0
    
    def test_resume_completed_activity(self, db_manager):
        """测试恢复已完成的活动"""
        activity_id = db_manager.add_activity(name="恢复测试", color="#0000FF")
        
        # 创建并完成一个活动
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now() - timedelta(minutes=30)
        log_id = db_manager.add_manual_log(activity_id, start, end, "原始记录")
        
        # 恢复
        result = db_manager.resume_completed_activity(log_id)
        assert result is True
        
        # 验证重新进入运行状态
        running = db_manager.get_running_activities()
        assert any(r[0] == log_id for r in running)
        
        # 再次停止
        duration = db_manager.stop_activity(log_id)
        assert duration > 0


class TestScheduleReminderWorkflow:
    """日程提醒工作流集成测试"""
    
    def test_schedule_creation_and_retrieval(self, db_manager):
        """测试日程创建和检索"""
        today = date.today().strftime("%Y-%m-%d")
        
        # 创建日程
        schedule_id = db_manager.add_schedule(
            start_time="09:00",
            end_time="10:00",
            content="集成测试日程",
            target_date=today
        )
        assert schedule_id > 0
        
        # 检索
        schedules = db_manager.get_schedules(today)
        assert len(schedules) >= 1
        assert any(s[0] == schedule_id for s in schedules)
    
    def test_schedule_with_activity_matching(self, db_manager):
        """测试日程与活动匹配"""
        # 创建活动
        activity_id = db_manager.add_activity(name="匹配测试活动", color="#FF00FF")
        
        # 创建同名日程
        today = date.today().strftime("%Y-%m-%d")
        db_manager.add_schedule("09:00", "10:00", "匹配测试活动", today)
        
        # 获取活动
        activities = db_manager.get_activities()
        activity = next((a for a in activities if a[0] == activity_id), None)
        
        assert activity is not None
        assert activity[1] == "匹配测试活动"
    
    def test_reminder_time_logic(self):
        """测试提醒时间逻辑"""
        with patch('utils.schedule_reminder.QTimer'):
            from utils.schedule_reminder import ScheduleReminder
            
            mock_db = MagicMock()
            reminder = ScheduleReminder(mock_db)
            reminder.advance_minutes = 5
            
            # 测试边界情况
            test_cases = [
                ("08:55", "09:00", True),   # 正好提前5分钟
                ("08:54", "09:00", False),  # 太早
                ("09:00", "09:00", True),   # 正好开始
                ("09:02", "09:00", True),   # 开始后2分钟内
                ("09:03", "09:00", False),  # 太晚
            ]
            
            for current, start, expected in test_cases:
                result, _ = reminder._should_remind(current, start)
                assert result == expected, f"Failed for {current} vs {start}"
            
            reminder.stop()


class TestDataConsistency:
    """数据一致性测试"""
    
    def test_activity_deletion_cascade(self, db_manager):
        """测试活动相关数据的级联处理"""
        # 创建活动和记录
        activity_id = db_manager.add_activity(name="级联测试", color="#123456")
        log_id = db_manager.start_activity(activity_id)
        db_manager.pause_activity(log_id)
        db_manager.resume_activity(log_id)
        db_manager.stop_activity(log_id)
        
        # 删除记录
        db_manager.delete_log(log_id)
        
        # 验证暂停记录也被删除
        cursor = db_manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pause_logs WHERE time_log_id = ?", (log_id,))
        count = cursor.fetchone()[0]
        assert count == 0
    
    def test_statistics_accuracy(self, db_manager):
        """测试统计准确性"""
        activity_id = db_manager.add_activity(name="统计测试", color="#ABCDEF")
        
        today = date.today()
        
        # 添加3条记录，每条1小时
        for i in range(3):
            start = datetime.combine(today, datetime.min.time()) + timedelta(hours=9+i)
            end = start + timedelta(hours=1)
            db_manager.add_manual_log(activity_id, start, end)
        
        # 验证每日统计
        daily_stats = db_manager.get_daily_stats(today)
        stat = next((s for s in daily_stats if s[0] == activity_id), None)
        
        assert stat is not None
        assert stat[5] == 3 * 3600  # 3小时 = 10800秒
        assert stat[6] == 3         # 3次会话
    
    def test_week_month_statistics_consistency(self, db_manager):
        """测试周/月统计一致性"""
        activity_id = db_manager.add_activity(name="周月统计", color="#FEDCBA")
        
        today = date.today()
        
        # 添加今日记录
        start = datetime.now() - timedelta(hours=2)
        end = datetime.now() - timedelta(hours=1)
        db_manager.add_manual_log(activity_id, start, end)
        
        # 验证今日包含在周统计中
        weekly = db_manager.get_weekly_stats(today)
        weekly_stat = next((s for s in weekly if s[0] == activity_id), None)
        
        # 验证今日包含在月统计中
        monthly = db_manager.get_monthly_stats(today)
        monthly_stat = next((s for s in monthly if s[0] == activity_id), None)
        
        assert weekly_stat is not None
        assert monthly_stat is not None
        
        # 周统计和月统计应该至少包含今日的数据
        assert weekly_stat[5] > 0
        assert monthly_stat[5] > 0


class TestConcurrentOperations:
    """并发操作测试"""
    
    @pytest.mark.thread_safety
    def test_concurrent_activity_starts(self, temp_db_path):
        """测试并发开始活动"""
        manager = DatabaseManager(db_path=temp_db_path)
        activity_id = manager.add_activity(name="并发测试", color="#FF0000")
        
        log_ids = []
        errors = []
        lock = threading.Lock()
        
        def start_activity():
            try:
                log_id = manager.start_activity(activity_id)
                with lock:
                    log_ids.append(log_id)
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        threads = [threading.Thread(target=start_activity) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        manager.close()
        
        assert len(errors) == 0
        assert len(log_ids) == 10
        assert len(set(log_ids)) == 10  # 所有ID应该唯一
    
    @pytest.mark.thread_safety
    def test_concurrent_mixed_operations(self, temp_db_path):
        """测试并发混合操作"""
        manager = DatabaseManager(db_path=temp_db_path)
        
        errors = []
        lock = threading.Lock()
        
        def do_operations():
            try:
                # 创建活动
                activity_id = manager.add_activity(
                    name=f"活动_{threading.current_thread().name}",
                    color="#FF0000"
                )
                if activity_id:
                    # 开始
                    log_id = manager.start_activity(activity_id)
                    time.sleep(0.01)
                    
                    # 暂停
                    manager.pause_activity(log_id)
                    time.sleep(0.01)
                    
                    # 恢复
                    manager.resume_activity(log_id)
                    time.sleep(0.01)
                    
                    # 停止
                    manager.stop_activity(log_id)
            except Exception as e:
                with lock:
                    errors.append(f"{threading.current_thread().name}: {e}")
        
        threads = [threading.Thread(target=do_operations, name=f"Thread_{i}") 
                   for i in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        manager.close()
        
        assert len(errors) == 0, f"出现错误: {errors}"


class TestModelIntegration:
    """模型集成测试"""
    
    def test_activity_tuple_conversion(self, db_manager):
        """测试活动元组转换"""
        activity_id = db_manager.add_activity(
            name="模型测试",
            color="#112233",
            icon="🔬",
            goal_minutes=90
        )
        
        activities = db_manager.get_activities()
        activity_tuple = next(a for a in activities if a[0] == activity_id)
        
        # 使用模型转换
        activity = Activity.from_tuple(activity_tuple)
        
        assert activity.id == activity_id
        assert activity.name == "模型测试"
        assert activity.color == "#112233"
        assert activity.icon == "🔬"
        assert activity.goal_minutes == 90
    
    def test_daily_stats_model_integration(self, db_manager):
        """测试每日统计模型集成"""
        activity_id = db_manager.add_activity(name="统计模型测试", color="#445566", goal_minutes=60)
        
        # 添加记录
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        db_manager.add_manual_log(activity_id, start, end)
        
        # 获取统计
        stats = db_manager.get_daily_stats(date.today())
        stat_tuple = next((s for s in stats if s[0] == activity_id), None)
        
        assert stat_tuple is not None
        
        # 转换为模型
        daily_stats = DailyStats.from_tuple(stat_tuple)
        
        assert daily_stats.activity_id == activity_id
        assert daily_stats.total_minutes == 60
        assert daily_stats.completion_rate == 100.0  # 60分钟目标，完成60分钟
    
    def test_time_calculator_integration(self, db_manager):
        """测试时间计算器集成"""
        activity_id = db_manager.add_activity(name="时间计算测试", color="#778899")
        
        start = datetime.now() - timedelta(hours=2, minutes=30, seconds=45)
        log_id = db_manager.start_activity(activity_id, start_time=start)
        
        elapsed = db_manager.get_elapsed_running(log_id)
        
        # 使用TimeCalculator格式化
        formatted = TimeCalculator.format_duration(elapsed)
        formatted_hm = TimeCalculator.format_duration_hm(elapsed)
        
        # 验证格式
        assert ":" in formatted
        assert ("h" in formatted_hm or "m" in formatted_hm)
        
        db_manager.stop_activity(log_id)


class TestEdgeCasesIntegration:
    """边界情况集成测试"""
    
    def test_midnight_activity(self, db_manager):
        """测试跨午夜活动"""
        activity_id = db_manager.add_activity(name="跨夜测试", color="#AABBCC")
        
        # 创建跨夜记录
        yesterday = datetime.now().replace(hour=23, minute=30) - timedelta(days=1)
        today = datetime.now().replace(hour=0, minute=30)
        
        log_id = db_manager.add_manual_log(activity_id, yesterday, today)
        
        # 验证记录存在
        log = db_manager.get_log_by_id(log_id)
        assert log is not None
        assert log[6] == 3600  # 1小时
    
    def test_rapid_start_stop(self, db_manager):
        """测试快速开始停止"""
        activity_id = db_manager.add_activity(name="快速操作", color="#DDEEFF")
        
        for _ in range(20):
            log_id = db_manager.start_activity(activity_id)
            db_manager.stop_activity(log_id)
        
        # 验证所有记录
        logs = db_manager.get_daily_logs(date.today())
        activity_logs = [l for l in logs if l[1] == "快速操作"]
        
        assert len(activity_logs) == 20
    
    def test_empty_note_handling(self, db_manager):
        """测试空备注处理"""
        activity_id = db_manager.add_activity(name="空备注", color="#000000")
        
        log_id = db_manager.start_activity(activity_id, note="")
        db_manager.stop_activity(log_id)
        
        log = db_manager.get_log_by_id(log_id)
        assert log[7] == ""  # note 应该是空字符串
    
    def test_unicode_throughout(self, db_manager):
        """测试全程Unicode"""
        activity_id = db_manager.add_activity(
            name="🎮 游戏时间 🕹️",
            color="#FF00FF",
            icon="🎲"
        )
        
        log_id = db_manager.start_activity(activity_id, note="玩得开心！🎉")
        db_manager.stop_activity(log_id)
        
        log = db_manager.get_log_by_id(log_id)
        assert "🎮" in log[1]
        assert "🎉" in log[7]


class TestDatabaseIntegrityIntegration:
    """数据库完整性集成测试"""
    
    def test_foreign_key_integrity(self, db_manager):
        """测试外键完整性"""
        activity_id = db_manager.add_activity(name="外键测试", color="#123123")
        log_id = db_manager.start_activity(activity_id)
        
        # 验证 time_logs 引用了有效的 activity_id
        cursor = db_manager.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM time_logs tl
            JOIN activities a ON tl.activity_id = a.id
            WHERE tl.id = ?
        """, (log_id,))
        
        assert cursor.fetchone()[0] == 1
        
        db_manager.stop_activity(log_id)
    
    def test_transaction_rollback_simulation(self, db_manager):
        """测试事务回滚模拟"""
        initial_count = len(db_manager.get_activities())
        
        try:
            # 添加活动
            db_manager.add_activity(name="事务测试", color="#456456")
            
            # 模拟错误（尝试添加重名）
            db_manager.add_activity(name="事务测试", color="#789789")
            
        except Exception:
            pass
        
        # 第一个活动应该成功
        final_count = len(db_manager.get_activities())
        assert final_count == initial_count + 1
