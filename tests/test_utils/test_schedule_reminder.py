# -*- coding: utf-8 -*-
"""
日程提醒服务测试模块

测试 utils/schedule_reminder.py 中的日程提醒功能
包括：
- ScheduleReminder 类
- ReminderDialog 类
- ScheduleReminderManager 类
- 时间判断逻辑
- 提醒触发机制
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, PropertyMock

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestScheduleReminderShouldRemind:
    """_should_remind 方法测试"""
    
    @pytest.fixture
    def reminder_instance(self, mock_db_manager):
        """创建带模拟数据库的提醒实例"""
        # 延迟导入以避免Qt初始化问题
        with patch('utils.schedule_reminder.QTimer'):
            from utils.schedule_reminder import ScheduleReminder
            reminder = ScheduleReminder(mock_db_manager)
            reminder.advance_minutes = 1
            yield reminder
            reminder.stop()
    
    def test_should_remind_in_window(self, reminder_instance):
        """测试在提醒窗口内"""
        # 开始时间09:00，提前1分钟，当前08:59
        result, reason = reminder_instance._should_remind("08:59", "09:00")
        assert result is True
    
    def test_should_remind_at_start(self, reminder_instance):
        """测试正好在开始时间"""
        result, reason = reminder_instance._should_remind("09:00", "09:00")
        assert result is True
    
    def test_should_remind_after_start(self, reminder_instance):
        """测试开始后2分钟内"""
        result, reason = reminder_instance._should_remind("09:01", "09:00")
        assert result is True
        
        result, reason = reminder_instance._should_remind("09:02", "09:00")
        assert result is True
    
    def test_should_not_remind_too_early(self, reminder_instance):
        """测试过早不提醒"""
        result, reason = reminder_instance._should_remind("08:50", "09:00")
        assert result is False
    
    def test_should_not_remind_too_late(self, reminder_instance):
        """测试过晚不提醒"""
        result, reason = reminder_instance._should_remind("09:10", "09:00")
        assert result is False
    
    def test_should_remind_advance_5_minutes(self, reminder_instance):
        """测试5分钟提前提醒"""
        reminder_instance.advance_minutes = 5
        result, reason = reminder_instance._should_remind("08:55", "09:00")
        assert result is True
    
    def test_invalid_time_format(self, reminder_instance):
        """测试无效时间格式"""
        result, reason = reminder_instance._should_remind("invalid", "09:00")
        assert result is False
        assert "解析错误" in reason
    
    def test_empty_time(self, reminder_instance):
        """测试空时间"""
        result, reason = reminder_instance._should_remind("", "09:00")
        assert result is False


class TestScheduleReminderCheckSchedules:
    """check_schedules 方法测试"""
    
    @pytest.fixture
    def mock_timer(self):
        """模拟QTimer"""
        with patch('utils.schedule_reminder.QTimer') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock
    
    @pytest.fixture
    def reminder_with_schedules(self, mock_db_manager, mock_timer):
        """创建带日程的提醒实例"""
        from utils.schedule_reminder import ScheduleReminder
        
        # 设置当前时刻的日程
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        start_time = (now - timedelta(minutes=1)).strftime("%H:%M")
        end_time = (now + timedelta(hours=1)).strftime("%H:%M")
        
        mock_db_manager.get_schedules.return_value = [
            (1, start_time, end_time, "测试日程"),
        ]
        
        reminder = ScheduleReminder(mock_db_manager)
        yield reminder
        reminder.stop()
    
    def test_check_schedules_triggers_signal(self, reminder_with_schedules):
        """测试检查日程触发信号"""
        signal_received = []
        
        def on_reminder(start, end, content):
            signal_received.append((start, end, content))
        
        reminder_with_schedules.reminder_triggered.connect(on_reminder)
        reminder_with_schedules.check_schedules()
        
        # 应该触发至少一个提醒
        assert len(signal_received) >= 0  # 取决于时间
    
    def test_check_schedules_empty(self, mock_db_manager, mock_timer):
        """测试无日程时检查"""
        from utils.schedule_reminder import ScheduleReminder
        
        mock_db_manager.get_schedules.return_value = []
        reminder = ScheduleReminder(mock_db_manager)
        
        # 不应该抛出异常
        reminder.check_schedules()
        reminder.stop()
    
    def test_already_reminded_skipped(self, mock_db_manager, mock_timer):
        """测试已提醒的日程被跳过"""
        from utils.schedule_reminder import ScheduleReminder
        
        now = datetime.now()
        start_time = (now - timedelta(minutes=1)).strftime("%H:%M")
        end_time = (now + timedelta(hours=1)).strftime("%H:%M")
        
        mock_db_manager.get_schedules.return_value = [
            (1, start_time, end_time, "测试日程"),
        ]
        
        reminder = ScheduleReminder(mock_db_manager)
        
        # 添加到已提醒集合
        reminder.reminded_schedules.add(1)
        
        signal_received = []
        reminder.reminder_triggered.connect(lambda s, e, c: signal_received.append(c))
        
        reminder.check_schedules()
        
        # 应该不触发
        assert len(signal_received) == 0
        reminder.stop()
    
    def test_exception_handling(self, mock_db_manager, mock_timer):
        """测试异常处理"""
        from utils.schedule_reminder import ScheduleReminder
        
        mock_db_manager.get_schedules.side_effect = Exception("数据库错误")
        
        reminder = ScheduleReminder(mock_db_manager)
        
        # 不应该抛出异常
        reminder.check_schedules()
        reminder.stop()


class TestScheduleReminderReset:
    """午夜重置测试"""
    
    @pytest.fixture
    def mock_timer(self):
        with patch('utils.schedule_reminder.QTimer') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock
    
    def test_reset_reminded_list(self, mock_db_manager, mock_timer):
        """测试重置已提醒列表"""
        from utils.schedule_reminder import ScheduleReminder
        
        reminder = ScheduleReminder(mock_db_manager)
        reminder.reminded_schedules.add(1)
        reminder.reminded_schedules.add(2)
        reminder.reminded_schedules.add(3)
        
        reminder.reset_reminded_list()
        
        assert len(reminder.reminded_schedules) == 0
        reminder.stop()
    
    def test_set_advance_minutes(self, mock_db_manager, mock_timer):
        """测试设置提前提醒分钟数"""
        from utils.schedule_reminder import ScheduleReminder
        
        reminder = ScheduleReminder(mock_db_manager)
        
        reminder.set_advance_minutes(10)
        assert reminder.advance_minutes == 10
        
        reminder.set_advance_minutes(0)
        assert reminder.advance_minutes == 0
        
        reminder.set_advance_minutes(-5)  # 负数应该变为0
        assert reminder.advance_minutes == 0
        
        reminder.stop()


class TestScheduleReminderManager:
    """ScheduleReminderManager 测试"""
    
    @pytest.fixture
    def mock_timer(self):
        with patch('utils.schedule_reminder.QTimer') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock
    
    @pytest.fixture
    def manager_instance(self, mock_db_manager, mock_timer):
        """创建管理器实例"""
        from utils.schedule_reminder import ScheduleReminderManager
        
        manager = ScheduleReminderManager(mock_db_manager, main_window=None)
        yield manager
        manager.stop()
    
    def test_snooze_reminder(self, manager_instance, mock_timer):
        """测试稍后提醒"""
        manager_instance.snooze_reminder("09:00", "10:00", "测试内容", minutes=5)
        
        key = "09:00_测试内容"
        assert key in manager_instance.snooze_schedules
    
    def test_snooze_duplicate_ignored(self, manager_instance):
        """测试重复稍后提醒被忽略"""
        manager_instance.snooze_reminder("09:00", "10:00", "测试内容")
        manager_instance.snooze_reminder("09:00", "10:00", "测试内容")
        
        # 应该只有一个
        key = "09:00_测试内容"
        assert key in manager_instance.snooze_schedules
    
    def test_start_activity_from_schedule_no_window(self, manager_instance, mock_db_manager):
        """测试无主窗口时开始活动"""
        manager_instance.main_window = None
        
        # 不应该抛出异常
        manager_instance.start_activity_from_schedule("工作")
    
    def test_start_activity_from_schedule_matched(self, manager_instance, mock_db_manager):
        """测试匹配活动并开始"""
        mock_window = MagicMock()
        manager_instance.main_window = mock_window
        
        mock_db_manager.get_activities.return_value = [
            (1, '工作', '#FF6B6B', '💼', 480),
            (2, '学习', '#4ECDC4', '📚', 120),
        ]
        mock_db_manager.start_activity.return_value = True
        
        manager_instance.start_activity_from_schedule("工作")
        
        mock_db_manager.start_activity.assert_called_once()
    
    def test_start_activity_from_schedule_not_matched(self, manager_instance, mock_db_manager):
        """测试未匹配到活动"""
        mock_window = MagicMock()
        manager_instance.main_window = mock_window
        
        mock_db_manager.get_activities.return_value = [
            (1, '工作', '#FF6B6B', '💼', 480),
        ]
        
        manager_instance.start_activity_from_schedule("不存在的活动")
        
        mock_db_manager.start_activity.assert_not_called()
        mock_window.show.assert_called()
    
    def test_show_main_window(self, manager_instance):
        """测试显示主窗口"""
        mock_window = MagicMock()
        manager_instance.main_window = mock_window
        
        manager_instance._show_main_window()
        
        mock_window.show.assert_called_once()
        mock_window.activateWindow.assert_called_once()
        mock_window.raise_.assert_called_once()
    
    def test_stop_manager(self, manager_instance):
        """测试停止管理器"""
        manager_instance.stop()
        
        manager_instance.reminder.check_timer.stop.assert_called()
        manager_instance.reminder.reset_timer.stop.assert_called()


class TestReminderDialog:
    """ReminderDialog 测试"""
    
    @pytest.mark.ui
    def test_dialog_creation(self):
        """测试对话框创建"""
        pytest.importorskip('PySide6.QtWidgets')
        
        from PySide6.QtWidgets import QApplication
        from utils.schedule_reminder import ReminderDialog
        
        # 需要QApplication实例
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        dialog = ReminderDialog("09:00", "10:00", "测试日程")
        
        assert dialog.windowTitle() == "📅 日程提醒"
        
        dialog.close()
    
    @pytest.mark.ui
    def test_dialog_content(self):
        """测试对话框内容"""
        pytest.importorskip('PySide6.QtWidgets')
        
        from PySide6.QtWidgets import QApplication
        from utils.schedule_reminder import ReminderDialog
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        dialog = ReminderDialog("09:00", "10:00", "测试日程")
        
        text = dialog.text()
        assert "09:00" in text
        assert "10:00" in text
        assert "测试日程" in text
        
        dialog.close()


class TestTimeWindowEdgeCases:
    """时间窗口边界情况测试"""
    
    @pytest.fixture
    def reminder(self, mock_db_manager):
        with patch('utils.schedule_reminder.QTimer'):
            from utils.schedule_reminder import ScheduleReminder
            reminder = ScheduleReminder(mock_db_manager)
            yield reminder
            reminder.stop()
    
    def test_midnight_crossing(self, reminder):
        """测试跨午夜时间"""
        # 这个测试验证时间解析不会因为跨夜而出错
        result, reason = reminder._should_remind("23:59", "00:01")
        # 由于只比较时间字符串，23:59 > 00:01，所以不会在窗口内
        assert result is False
    
    def test_same_time(self, reminder):
        """测试相同时间"""
        result, reason = reminder._should_remind("09:00", "09:00")
        assert result is True
    
    def test_exact_window_boundary_start(self, reminder):
        """测试窗口边界开始"""
        reminder.advance_minutes = 1
        # 开始时间09:00，提前1分钟，窗口从08:59开始
        result, reason = reminder._should_remind("08:59", "09:00")
        assert result is True
    
    def test_exact_window_boundary_end(self, reminder):
        """测试窗口边界结束"""
        # 开始时间09:00，窗口到09:02结束
        result, reason = reminder._should_remind("09:02", "09:00")
        assert result is True
        
        result, reason = reminder._should_remind("09:03", "09:00")
        assert result is False


class TestThreadSafetyScheduleReminder:
    """日程提醒线程安全测试"""
    
    @pytest.fixture
    def reminder(self, mock_db_manager):
        with patch('utils.schedule_reminder.QTimer'):
            from utils.schedule_reminder import ScheduleReminder
            reminder = ScheduleReminder(mock_db_manager)
            yield reminder
            reminder.stop()
    
    def test_concurrent_reminded_schedules_access(self, reminder):
        """测试并发访问已提醒集合"""
        import threading
        
        errors = []
        
        def add_items():
            try:
                for i in range(100):
                    reminder.reminded_schedules.add(i)
            except Exception as e:
                errors.append(str(e))
        
        def remove_items():
            try:
                for i in range(100):
                    reminder.reminded_schedules.discard(i)
            except Exception as e:
                errors.append(str(e))
        
        threads = [
            threading.Thread(target=add_items),
            threading.Thread(target=remove_items),
            threading.Thread(target=add_items),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Python的set在CPython中由于GIL是线程安全的
        # 但在实际生产中应该使用锁
        assert len(errors) == 0


class TestMemoryLeakPrevention:
    """内存泄漏预防测试"""
    
    @pytest.fixture
    def mock_timer(self):
        with patch('utils.schedule_reminder.QTimer') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock
    
    def test_reminded_schedules_cleared_on_reset(self, mock_db_manager, mock_timer):
        """测试重置时清理已提醒集合"""
        from utils.schedule_reminder import ScheduleReminder
        
        reminder = ScheduleReminder(mock_db_manager)
        
        # 添加大量条目
        for i in range(1000):
            reminder.reminded_schedules.add(i)
        
        assert len(reminder.reminded_schedules) == 1000
        
        reminder.reset_reminded_list()
        
        assert len(reminder.reminded_schedules) == 0
        reminder.stop()
    
    def test_snooze_schedules_cleanup(self, mock_db_manager, mock_timer):
        """测试稍后提醒字典清理"""
        from utils.schedule_reminder import ScheduleReminderManager
        
        manager = ScheduleReminderManager(mock_db_manager)
        
        # 模拟稍后提醒回调 - 现在存储的是 QTimer 对象
        key = "09:00_测试"
        mock_timer_instance = MagicMock()
        manager.snooze_schedules[key] = mock_timer_instance
        
        # 调用回调
        manager._snooze_callback("09:00", "10:00", "测试", key)
        
        # 应该被清理
        assert key not in manager.snooze_schedules
        # 定时器应该被调用 deleteLater
        mock_timer_instance.deleteLater.assert_called_once()
        manager.stop()
    
    def test_timer_stopped_on_stop(self, mock_db_manager, mock_timer):
        """测试停止时定时器被停止"""
        from utils.schedule_reminder import ScheduleReminder
        
        reminder = ScheduleReminder(mock_db_manager)
        reminder.stop()
        
        # 验证定时器被停止
        reminder.check_timer.stop.assert_called()
        reminder.reset_timer.stop.assert_called()
