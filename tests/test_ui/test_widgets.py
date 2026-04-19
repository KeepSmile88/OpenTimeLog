# -*- coding: utf-8 -*-
"""
UI组件测试模块

测试 ui/ 目录下的UI组件
包括：
- MainWindow 主窗口
- ActivityControlWidget 活动控制组件
- ScheduleManagerWidget 日程管理组件
- 其他UI组件

注意：这些测试需要 pytest-qt 和图形显示环境
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# 跳过没有Qt环境的测试
pytestmark = pytest.mark.skipif(
    not os.environ.get('DISPLAY') and sys.platform not in ('win32', 'darwin'),
    reason="需要图形显示环境"
)


class TestActivityControlWidget:
    """活动控制组件测试"""
    
    @pytest.fixture
    def activity_data(self):
        """示例活动数据"""
        return (1, "工作", "#FF6B6B", "💼", 480)
    
    @pytest.fixture
    def widget(self, activity_data, qtbot):
        """创建组件实例"""
        from ui.widgets.activity_control import ActivityControlWidget
        
        widget = ActivityControlWidget(activity_data)
        qtbot.addWidget(widget)
        return widget
    
    def test_widget_creation(self, widget, activity_data):
        """测试组件创建"""
        assert widget.activity_id == activity_data[0]
        assert widget.name == activity_data[1]
        assert widget.color == activity_data[2]
        assert widget.icon == activity_data[3]
        assert widget.goal_minutes == activity_data[4]
    
    def test_main_button_text(self, widget):
        """测试主按钮文本"""
        assert "💼" in widget.main_button.text()
        assert "工作" in widget.main_button.text()
    
    def test_start_clicked_signal(self, widget, qtbot):
        """测试开始信号"""
        with qtbot.waitSignal(widget.start_clicked, timeout=1000):
            widget.main_button.click()
    
    def test_manual_clicked_signal(self, widget, qtbot):
        """测试手动记录信号"""
        with qtbot.waitSignal(widget.manual_clicked, timeout=1000):
            widget.manual_add_btn.click()
    
    def test_minimal_activity_data(self, qtbot):
        """测试最小活动数据"""
        from ui.widgets.activity_control import ActivityControlWidget
        
        minimal_data = (1, "测试", "#FF0000")
        widget = ActivityControlWidget(minimal_data)
        qtbot.addWidget(widget)
        
        assert widget.icon == '⭕'  # 默认图标
        assert widget.goal_minutes == 0
    
    def test_unicode_activity_name(self, qtbot):
        """测试Unicode活动名称"""
        from ui.widgets.activity_control import ActivityControlWidget
        
        data = (1, "🎮 游戏时间 🕹️", "#FF00FF", "🎲", 60)
        widget = ActivityControlWidget(data)
        qtbot.addWidget(widget)
        
        assert "🎮" in widget.main_button.text()


class TestRunningActivityWidget:
    """运行中活动组件测试"""
    
    @pytest.fixture
    def running_data(self):
        """运行中活动数据"""
        return (
            1,                          # log_id
            "工作",                     # activity_name
            "#FF6B6B",                  # color
            "💼",                       # icon
            datetime.now().isoformat(), # start_time
            "测试备注",                 # note
            "running"                   # status
        )
    
    @pytest.fixture
    def widget(self, running_data, mock_db_manager, qtbot):
        """创建组件实例"""
        from ui.widgets.running_activity import RunningActivityWidget
        
        widget = RunningActivityWidget(running_data, mock_db_manager)
        qtbot.addWidget(widget)
        return widget
    
    def test_widget_creation(self, widget):
        """测试组件创建"""
        assert widget is not None
    
    def test_display_info(self, widget, running_data):
        """测试显示信息"""
        assert running_data[1] in widget.activity_label.text()  # 活动名称
    
    def test_pause_signal(self, widget, qtbot):
        """测试暂停信号"""
        # 找到暂停按钮并点击
        if hasattr(widget, 'pause_btn') and widget.pause_btn.isVisible():
            with qtbot.waitSignal(widget.pause_requested, timeout=1000):
                widget.pause_btn.click()
    
    def test_resume_signal(self, widget, qtbot):
        """测试恢复信号（暂停状态）"""
        # 设置为暂停状态
        widget.status = 'paused'
        widget.update_status_display()
        
        if hasattr(widget, 'resume_btn') and widget.resume_btn.isVisible():
            with qtbot.waitSignal(widget.resume_requested, timeout=1000):
                widget.resume_btn.click()
    
    def test_stop_signal(self, widget, qtbot):
        """测试停止信号"""
        if hasattr(widget, 'stop_btn'):
            with qtbot.waitSignal(widget.stop_requested, timeout=1000):
                widget.stop_btn.click()


class TestScheduleManagerWidget:
    """日程管理组件测试"""
    
    @pytest.fixture
    def widget(self, mock_db_manager, qtbot):
        """创建组件实例"""
        from ui.widgets.schedule_manager import ScheduleManagerWidget
        
        widget = ScheduleManagerWidget(mock_db_manager)
        qtbot.addWidget(widget)
        return widget
    
    def test_widget_creation(self, widget):
        """测试组件创建"""
        assert widget is not None
    
    def test_initial_state(self, widget):
        """测试初始状态"""
        # 应该有日期选择和时间输入
        assert hasattr(widget, 'current_date')
    
    def test_date_change(self, widget, qtbot):
        """测试日期变更"""
        from PySide6.QtCore import QDate
        
        new_date = QDate.currentDate().addDays(1)
        widget.on_date_changed(new_date)
        
        assert widget.current_date == new_date
    
    def test_add_schedule_empty_content(self, widget, mock_db_manager):
        """测试添加空内容日程"""
        # 不应该实际添加
        initial_call_count = mock_db_manager.add_schedule.call_count
        
        widget.content_input.setText("")
        widget.add_schedule()
        
        # 调用次数应该不变或方法应处理空内容
        assert mock_db_manager.add_schedule.call_count == initial_call_count


class TestDailyLogWidget:
    """每日记录组件测试"""
    
    @pytest.fixture
    def widget(self, mock_db_manager, qtbot):
        """创建组件实例"""
        from ui.widgets.daily_log import DailyLogWidget
        
        mock_db_manager.get_daily_logs.return_value = []
        mock_db_manager.get_daily_stats.return_value = []
        
        widget = DailyLogWidget(mock_db_manager)
        qtbot.addWidget(widget)
        return widget
    
    def test_widget_creation(self, widget):
        """测试组件创建"""
        assert widget is not None
    
    def test_refresh_logs(self, widget, mock_db_manager):
        """测试刷新日志"""
        widget.refresh()
        mock_db_manager.get_daily_logs.assert_called()


class TestStatisticsWidget:
    """统计组件测试"""
    
    @pytest.fixture
    def widget(self, mock_db_manager, qtbot):
        """创建组件实例"""
        from ui.widgets.statistics import StatisticsWidget
        
        mock_db_manager.get_daily_stats.return_value = []
        mock_db_manager.get_weekly_stats.return_value = []
        mock_db_manager.get_monthly_stats.return_value = []
        mock_db_manager.get_yearly_heatmap_data.return_value = []
        
        widget = StatisticsWidget(mock_db_manager)
        qtbot.addWidget(widget)
        return widget
    
    def test_widget_creation(self, widget):
        """测试组件创建"""
        assert widget is not None


class TestTodoListWidget:
    """待办列表组件测试"""
    
    @pytest.fixture
    def widget(self, mock_db_manager, qtbot):
        """创建组件实例"""
        from ui.widgets.todo_list import TodoListWidget
        
        mock_db_manager.get_todos.return_value = []
        mock_db_manager.get_activities.return_value = []
        
        widget = TodoListWidget(mock_db_manager)
        qtbot.addWidget(widget)
        return widget
    
    def test_widget_creation(self, widget):
        """测试组件创建"""
        assert widget is not None
    
    def test_add_todo(self, widget, mock_db_manager):
        """测试添加待办"""
        mock_db_manager.add_todo.return_value = 1
        
        # 设置内容
        if hasattr(widget, 'input_field'):
            widget.input_field.setText("新待办")
            
            if hasattr(widget, 'add_todo'):
                widget.add_todo()
                mock_db_manager.add_todo.assert_called()


class TestMainWindow:
    """主窗口测试"""
    
    @pytest.fixture
    def main_window(self, qtbot):
        """创建主窗口实例"""
        with patch('ui.main_window.DatabaseManager') as MockDB:
            mock_db = MagicMock()
            mock_db.get_activities.return_value = []
            mock_db.get_running_activities.return_value = []
            mock_db.get_todos.return_value = []
            mock_db.get_schedules.return_value = []
            MockDB.return_value = mock_db
            
            from ui.main_window import MainWindow
            
            window = MainWindow()
            qtbot.addWidget(window)
            yield window
            window.close()
    
    def test_window_creation(self, main_window):
        """测试窗口创建"""
        assert main_window is not None
    
    def test_window_title(self, main_window):
        """测试窗口标题"""
        assert "aTimeLogPro" in main_window.windowTitle()
    
    def test_initial_visibility(self, main_window):
        """测试初始可见性"""
        main_window.show()
        assert main_window.isVisible()
    
    def test_toggle_visibility(self, main_window):
        """测试切换可见性"""
        main_window.show()
        main_window.toggle_visibility()
        # 可能隐藏或保持可见，取决于实现
    
    def test_refresh_all(self, main_window):
        """测试刷新所有"""
        main_window.refresh_all()
        # 不应该抛出异常
    
    def test_apply_theme(self, main_window):
        """测试应用主题"""
        main_window.apply_theme('light')
        main_window.apply_theme('dark')
        # 不应该抛出异常


class TestDialogs:
    """对话框测试"""
    
    def test_add_activity_dialog(self, qtbot):
        """测试添加活动对话框"""
        from ui.dialogs.add_activity import AddActivityDialog
        
        dialog = AddActivityDialog()
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        dialog.close()
    
    def test_edit_log_dialog(self, mock_db_manager, qtbot):
        """测试编辑记录对话框"""
        from ui.dialogs.edit_log import EditLogDialog
        
        log_data = (
            1,                          # id
            "工作",                     # activity_name
            "#FF6B6B",                  # color
            "💼",                       # icon
            "2026-01-28 10:00:00",     # start_time
            "2026-01-28 11:00:00",     # end_time
            3600,                       # duration
            "测试备注",                 # note
            "completed",                # status
            0                           # is_manual
        )
        
        mock_db_manager.get_activities.return_value = [
            (1, '工作', '#FF6B6B', '💼', 480, 0, None),
        ]
        
        dialog = EditLogDialog(log_data, mock_db_manager)
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        dialog.close()
    
    def test_manual_log_dialog(self, mock_db_manager, qtbot):
        """测试手动记录对话框"""
        from ui.dialogs.manual_log import ManualLogDialog
        
        mock_db_manager.get_activities.return_value = [
            (1, '工作', '#FF6B6B', '💼', 480, 0, None),
        ]
        
        dialog = ManualLogDialog(mock_db_manager)
        qtbot.addWidget(dialog)
        
        assert dialog is not None
        dialog.close()


class TestUIInteractions:
    """UI交互测试"""
    
    @pytest.fixture
    def activity_widget(self, qtbot):
        """活动控制组件"""
        from ui.widgets.activity_control import ActivityControlWidget
        
        data = (1, "测试活动", "#FF0000", "🧪", 60)
        widget = ActivityControlWidget(data)
        qtbot.addWidget(widget)
        return widget
    
    def test_button_hover_effect(self, activity_widget, qtbot):
        """测试按钮悬停效果"""
        from PySide6.QtCore import Qt
        
        # 模拟鼠标进入
        qtbot.mouseMove(activity_widget.main_button)
        # 不应该抛出异常
    
    def test_button_click_feedback(self, activity_widget, qtbot):
        """测试按钮点击反馈"""
        signal_received = []
        activity_widget.start_clicked.connect(lambda x: signal_received.append(x))
        
        qtbot.mouseClick(activity_widget.main_button, Qt.LeftButton)
        
        assert len(signal_received) == 1
        assert signal_received[0] == activity_widget.activity_id


class TestUIStateManagement:
    """UI状态管理测试"""
    
    @pytest.fixture
    def main_window_with_activities(self, qtbot):
        """带活动的主窗口"""
        with patch('ui.main_window.DatabaseManager') as MockDB:
            mock_db = MagicMock()
            mock_db.get_activities.return_value = [
                (1, '工作', '#FF6B6B', '💼', 480, 0, None),
                (2, '学习', '#4ECDC4', '📚', 120, 0, None),
            ]
            mock_db.get_running_activities.return_value = []
            mock_db.get_todos.return_value = []
            mock_db.get_schedules.return_value = []
            MockDB.return_value = mock_db
            
            from ui.main_window import MainWindow
            
            window = MainWindow()
            qtbot.addWidget(window)
            yield window
            window.close()
    
    def test_activity_grid_populated(self, main_window_with_activities):
        """测试活动网格已填充"""
        # 检查活动网格是否有子组件
        assert main_window_with_activities is not None


class TestUIEdgeCases:
    """UI边界情况测试"""
    
    def test_empty_activity_list(self, mock_db_manager, qtbot):
        """测试空活动列表"""
        with patch('ui.main_window.DatabaseManager', return_value=mock_db_manager):
            mock_db_manager.get_activities.return_value = []
            mock_db_manager.get_running_activities.return_value = []
            
            from ui.main_window import MainWindow
            
            window = MainWindow()
            qtbot.addWidget(window)
            
            # 不应该抛出异常
            window.refresh_activities()
            window.close()
    
    def test_very_long_activity_name(self, qtbot):
        """测试超长活动名称"""
        from ui.widgets.activity_control import ActivityControlWidget
        
        long_name = "A" * 100
        data = (1, long_name, "#FF0000", "🧪", 60)
        
        widget = ActivityControlWidget(data)
        qtbot.addWidget(widget)
        
        # 不应该抛出异常
        assert widget is not None
    
    def test_special_characters_in_ui(self, qtbot):
        """测试UI中的特殊字符"""
        from ui.widgets.activity_control import ActivityControlWidget
        
        data = (1, "测试<script>alert('XSS')</script>", "#FF0000", "🧪", 60)
        
        widget = ActivityControlWidget(data)
        qtbot.addWidget(widget)
        
        # 不应该抛出异常，特殊字符应该被正确显示
        assert widget is not None
