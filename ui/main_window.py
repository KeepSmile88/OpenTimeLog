#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口和应用程序类
"""

import os
import sys

from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QScrollArea, QGridLayout, QTabWidget, QLineEdit,
    QInputDialog, QMessageBox, QDialog, QLabel, QSizePolicy, QSpacerItem,
    QSplitter, QSystemTrayIcon, QMenu, QPushButton
)
from PySide6.QtCore import QTimer, Qt, QTime, QEvent
from PySide6.QtGui import QIcon, QAction

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseManager
from core.config import ConfigManager
from ui.widgets.activity_control import ActivityControlWidget
from ui.widgets.running_activity import RunningActivityWidget
from ui.widgets.daily_log import DailyLogWidget
from ui.widgets.statistics import StatisticsWidget
from ui.widgets.report import ReportWidget
from ui.widgets.admin_dashboard import AdminDashboardWidget
from ui.widgets.todo_list import TodoListWidget
from ui.widgets.schedule_manager import ScheduleManagerWidget
from ui.widgets.floating_timer import FloatingTimerWidget
from ui.dialogs.add_activity import AddActivityDialog
from ui.dialogs.manual_log import ManualLogDialog
from ui.dialogs.edit_log import EditLogDialog
from ui.dialogs.help_dialog import HelpDialog
from ui.widgets.activity_note import ActivityNoteDialog
from ui.styles.app_style import get_app_style, theme_manager
from utils.schedule_reminder import ScheduleReminderManager


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.db_manager = DatabaseManager()
        
        self.setWindowTitle('OpenTimeLog - 时间记录器')
        
        # 应用保存的窗口尺寸
        geom = self.config.get("geometry")
        if geom: self.setGeometry(*geom)
        else: self.setGeometry(100, 100, 1400, 900)
        
        # 状态初始化
        self.current_theme = self.config.get("theme", "default")
        self.activity_widgets = []
        self.running_widgets = {}
        self.running_order = []
        self.no_activity_label = None
        self.admin_tab_index = -1
        
        # 实例化悬浮窗 (暂不显示)
        self.floating_widget = FloatingTimerWidget(self.db_manager)
        self.floating_widget.request_show_main.connect(self.toggle_visibility)
        self.floating_widget.request_toggle_status.connect(self.toggle_activity_from_floating)

        self.setup_tray()
        self.setup_ui()
        self.setup_menu()
        self.refresh_all()

        # 定时器用于更新运行中的活动
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_running_activities)
        self.update_timer.start(1000)  # 每秒更新一次
        
        # 初始化日程提醒服务
        self.schedule_reminder = ScheduleReminderManager(self.db_manager, self)
        
        # 启动时恢复主题
        self.apply_theme(self.current_theme)

    def setup_tray(self):
        """设置系统托盘"""
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setParent(self)
        
        # 使用应用图标 (Windows优先用ico，其他优先用png或尝试回退)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'main.ico')
        png_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'main.png')
        
        if os.path.exists(icon_path) and sys.platform == 'win32':
            self.tray_icon.setIcon(QIcon(icon_path))
        elif os.path.exists(png_path):
            self.tray_icon.setIcon(QIcon(png_path))
        elif os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        
        # 托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示/隐藏主窗口")
        show_action.triggered.connect(self.toggle_visibility)
        
        tray_menu.addSeparator()
        
        # 悬浮窗开关
        float_action = tray_menu.addAction("桌面悬浮窗")
        float_action.setCheckable(True)
        float_action.setChecked(False)
        float_action.triggered.connect(self.toggle_floating_widget)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("完全退出程序")
        exit_action.triggered.connect(self.force_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def toggle_visibility(self):
        if self.isVisible(): self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_() # 确保在最上方

    def toggle_activity_from_floating(self, log_id):
        """处理来自悬浮窗的状态切换请求"""
        print(f"[悬浮窗联动] 接收到切换请求，log_id: {log_id}")
        running = self.db_manager.get_running_activities()
        print(f"[悬浮窗联动] 当前活动列表: {[(r[0], r[1], r[6]) for r in running]}")
        target = [r for r in running if r[0] == log_id]
        if target:
            status = target[0][6]
            print(f"[悬浮窗联动] 目标活动状态: {status}")
            if status == 'running':
                print(f"[悬浮窗联动] 调用 pause_activity({log_id})")
                self.pause_activity(log_id)
            else:
                print(f"[悬浮窗联动] 调用 resume_activity({log_id})")
                self.resume_activity(log_id)
        else:
            print(f"[悬浮窗联动] 未找到目标活动 log_id={log_id}")

    def toggle_floating_widget(self, checked):
        if checked: self.floating_widget.show()
        else: self.floating_widget.hide()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def force_quit(self):
        """强制完全退出程序"""
        # 关闭所有计时器
        if hasattr(self, 'update_timer'): self.update_timer.stop()
        if hasattr(self, 'floating_widget'): self.floating_widget.timer.stop()
        
        self.config.set("close_to_tray", False) # 临时改掉，确保不被 closeEvent 拦截
        self.close()
        QApplication.quit()

    def setup_ui(self):
        """设置UI"""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # 主布局 - 使用 Splitter 实现可调整分割
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 左右分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(3)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            QSplitter::handle:hover {
                background-color: #1A73E8;
            }
        """)
        
        # 左侧面板 - 使用内部 Splitter 分割活动控制和运行中活动
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 左侧内部分割器
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.setHandleWidth(2)
        
        # 活动控制区
        activities_group = QGroupBox('活动控制')
        activities_group.setStyleSheet('QGroupBox { font-size: 12px; font-weight: bold; }')
        activities_layout = QVBoxLayout()
        activities_layout.setContentsMargins(8, 12, 8, 8)
        activities_layout.setSpacing(6)

        # 搜索框 - 精简尺寸
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索活动...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMaximumHeight(28)
        self.search_box.textChanged.connect(self.filter_activities)
        activities_layout.addWidget(self.search_box)
        
        # 滚动区域用于活动按钮
        activities_scroll = QScrollArea()
        activities_scroll.setFrameShape(QScrollArea.NoFrame)
        activities_widget = QWidget()
        self.activities_layout = QGridLayout()
        self.activities_layout.setSpacing(6)
        self.activities_layout.setContentsMargins(2, 2, 2, 2)
        activities_widget.setLayout(self.activities_layout)
        activities_scroll.setWidget(activities_widget)
        activities_scroll.setWidgetResizable(True)
        
        activities_layout.addWidget(activities_scroll)
        activities_group.setLayout(activities_layout)
        
        # 运行中活动区
        running_group = QGroupBox('运行中的活动')
        running_group.setStyleSheet('QGroupBox { font-size: 12px; font-weight: bold; }')
        running_layout = QVBoxLayout()
        running_layout.setContentsMargins(8, 12, 8, 8)
        
        running_scroll = QScrollArea()
        running_scroll.setFrameShape(QScrollArea.NoFrame)
        running_widget = QWidget()
        self.running_layout = QVBoxLayout()
        self.running_layout.setContentsMargins(2, 2, 2, 2)
        self.running_layout.addStretch()
        running_widget.setLayout(self.running_layout)
        running_scroll.setWidget(running_widget)
        running_scroll.setWidgetResizable(True)
        
        running_layout.addWidget(running_scroll)
        running_group.setLayout(running_layout)
        
        # 添加到左侧分割器 - 调整比例让运行中区域更突出
        self.left_splitter.addWidget(activities_group)
        self.left_splitter.addWidget(running_group)
        self.left_splitter.setStretchFactor(0, 2)  # 活动区占 2
        self.left_splitter.setStretchFactor(1, 3)  # 运行区占 3 (增大)
        
        left_layout.addWidget(self.left_splitter)
        
        # 中间面板 - 标签页
        self.tab_widget = QTabWidget()
        
        # 1. 统计标签页
        self.statistics_widget = StatisticsWidget(self.db_manager)
        self.tab_widget.addTab(self.statistics_widget, "📊 统计分析")
        
        # 2. 待办事项标签页
        self.todo_list_widget = TodoListWidget(self.db_manager)
        self.todo_list_widget.start_activity_requested.connect(self.start_activity_from_todo)
        self.tab_widget.addTab(self.todo_list_widget, "✅ 待办事项")
        
        # 3. 日程安排标签页
        self.schedule_widget = ScheduleManagerWidget(self.db_manager)
        self.tab_widget.addTab(self.schedule_widget, "📅 日程表")
        
        # 3. 日志标签页
        self.daily_log_widget = DailyLogWidget(self.db_manager)
        self.daily_log_widget.resume_completed.connect(self.resume_completed_activity)
        self.daily_log_widget.logs_updated.connect(self.on_logs_updated)
        self.tab_widget.addTab(self.daily_log_widget, "📝 日志记录")
        
        # 4. 报告导出标签页
        self.report_widget = ReportWidget(self.db_manager)
        self.tab_widget.addTab(self.report_widget, "📋 报告导出")
        
        # 管理面板 (隐藏组件)
        self.admin_widget = AdminDashboardWidget()
        
        # 添加到主分割器
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(self.tab_widget)
        self.main_splitter.setStretchFactor(0, 1)  # 左侧占 1
        self.main_splitter.setStretchFactor(1, 3)  # 右侧占 3
        self.main_splitter.setSizes([280, 800])  # 初始尺寸
        
        main_layout.addWidget(self.main_splitter)
        central_widget.setLayout(main_layout)
        
        # 管理面板激活快捷键
        self.admin_action = QAction(self)
        self.admin_action.setShortcut("Ctrl+Alt+A")
        self.admin_action.triggered.connect(self.toggle_admin_panel)
        self.addAction(self.admin_action)

    def toggle_admin_panel(self):
        """切换管理面板显示"""
        # 创建自定义密码对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("管理员验证")
        dialog.setFixedSize(300, 150)
        dialog.setStyleSheet("""
            QDialog { background: #fff; }
            QLabel { font-size: 13px; color: #333; }
            QLineEdit {
                padding: 8px 12px;
                font-size: 13px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QLineEdit:focus { border-color: #1A73E8; }
            QPushButton {
                padding: 6px 20px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton#confirm {
                background: #1A73E8;
                color: white;
                border: none;
            }
            QPushButton#confirm:hover { background: #1557b0; }
            QPushButton#cancel {
                background: #f5f5f5;
                border: 1px solid #ddd;
            }
            QPushButton#cancel:hover { background: #eee; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # 提示文字
        label = QLabel("🔐 请输入管理员密码：")
        layout.addWidget(label)
        
        # 密码输入框
        password_input = QLineEdit()
        password_input.setPlaceholderText("密码")
        password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(password_input)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        confirm_btn = QPushButton("确认")
        confirm_btn.setObjectName("confirm")
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(dialog.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)
        
        # 回车确认
        password_input.returnPressed.connect(dialog.accept)
        
        if dialog.exec() == QDialog.Accepted:
            input_key = password_input.text()
            if input_key == "admin123":
                if self.admin_tab_index == -1:
                    self.admin_tab_index = self.tab_widget.addTab(self.admin_widget, "👨‍💼 管理面板")
                    self.tab_widget.setCurrentIndex(self.admin_tab_index)
                    QMessageBox.information(self, "成功", "管理面板已激活！")
                else:
                    self.tab_widget.setCurrentIndex(self.admin_tab_index)
            else:
                QMessageBox.warning(self, "错误", "密码错误！")

    def clear_layout(self, layout):
        """清除布局中的所有组件"""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        add_act_action = QAction('添加活动', self)
        add_act_action.setShortcut('Ctrl+N')
        add_act_action.triggered.connect(self.add_activity)
        file_menu.addAction(add_act_action)
        
        add_log_action = QAction('手动添加记录', self)
        add_log_action.setShortcut('Ctrl+M')
        add_log_action.triggered.connect(self.add_manual_log)
        file_menu.addAction(add_log_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出报告', self)
        export_action.triggered.connect(lambda: self.tab_widget.setCurrentWidget(self.report_widget))
        file_menu.addAction(export_action)
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 主题菜单 (Updated for Multi-Theme)
        theme_menu = menubar.addMenu('主题')
        
        themes = [
            ("默认浅色", "default"),
            ("专业深色", "dark"),
            ("温馨粉色", "pink"),
            ("护眼模式", "eyecare")
        ]
        
        for label, name in themes:
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, n=name: self.apply_theme(n))
            theme_menu.addAction(action)
            
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        refresh_action = QAction('刷新', self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_all)
        view_menu.addAction(refresh_action)
        
        stop_all_action = QAction('停止所有活动', self)
        stop_all_action.setShortcut('Ctrl+Shift+S')
        stop_all_action.triggered.connect(self.stop_all_activities)
        view_menu.addAction(stop_all_action)
        
        view_menu.addSeparator()
        
        toggle_admin = QAction('显示/隐藏 管理面板', self)
        toggle_admin.triggered.connect(self.toggle_admin_panel)
        view_menu.addAction(toggle_admin)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        help_action = QAction('查看手册', self)
        help_action.setShortcut('F1')
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def apply_theme(self, theme_name):
        """应用主题"""
        # 兼容性迁移：将旧版 "male" 主题映射为 "dark"
        if theme_name == "male": 
            theme_name = "dark"
            
        print(f"Switching theme to: {theme_name}")
        self.current_theme = theme_name
        self.config.set("theme", theme_name)
        
        # 1. 更新管理器状态
        from ui.styles.app_style import theme_manager, get_app_style
        theme_manager.set_theme(theme_name)
        
        # 2. 刷新全局样式表
        QApplication.instance().setStyleSheet(get_app_style())
        
        # 3. 强制重绘主窗口
        self.update()
        
        # 4. 触发组件刷新
        # StatisticsWidget 等已通过 connect(theme_manager.theme_changed) 自动刷新，无需在此调用
        
        # AdminDashboardWidget 尚未重构，仍需手动通知
        is_dark = (theme_name == "dark")
        if hasattr(self, 'admin_widget'):
            self.admin_widget.set_dark_mode(is_dark)

    def refresh_activities(self):
        """刷新活动列表"""
        activities = self.db_manager.get_activities()
        self.rebuild_activity_grid(activities)

    def rebuild_activity_grid(self, activities):
        """重建活动网格"""
        self.clear_layout(self.activities_layout)
        self.activity_widgets.clear()
        
        # 移除旧的行拉伸设置
        for i in range(self.activities_layout.rowCount()):
            self.activities_layout.setRowStretch(i, 0)
        
        for idx, activity in enumerate(activities):
            row, col = divmod(idx, 2)
            widget = ActivityControlWidget(activity)
            widget.start_clicked.connect(self.start_activity)
            widget.manual_clicked.connect(self.add_manual_log)
            widget.edit_clicked.connect(self.edit_activity)
            widget.delete_clicked.connect(self.delete_activity)
            self.activities_layout.addWidget(widget, row, col)
            self.activity_widgets.append(widget)
        
        # 在最后一行后添加拉伸因子，让内容靠顶部对齐
        last_row = (len(activities) + 1) // 2
        self.activities_layout.setRowStretch(last_row, 1)

    def update_running_activities(self):
        """更新运行中的活动列表（增量更新）"""
        running_activities = self.db_manager.get_running_activities()
        sorted_activities = sorted(running_activities, key=lambda x: x[4], reverse=True)
        current_ids = {act[0] for act in sorted_activities}
        existing_ids = set(self.running_widgets.keys())
        
        layout_changed = (current_ids != existing_ids)
        if layout_changed:
            self.running_layout.parentWidget().setUpdatesEnabled(False)
            # 更新悬浮窗
            if hasattr(self, 'floating_widget') and self.floating_widget:
                pass # 悬浮窗有自刷新机制，无需在此调用不存在的 update_display
                
            # 检查日程提醒 (每分钟检查一次，避免过于频繁)
            current_time = QTime.currentTime()
            if current_time.second() == 0: 
                self.check_schedule_alert()
                
        try:
            # 1. 移除
            for log_id in list(self.running_widgets.keys()):
                if log_id not in current_ids:
                    widget = self.running_widgets.pop(log_id)
                    self.running_layout.removeWidget(widget)
                    widget.deleteLater()
                    if log_id in self.running_order: self.running_order.remove(log_id)
            
            # 2. 状态标签
            if not current_ids:
                if not self.no_activity_label:
                    self.no_activity_label = QLabel('☕ 休息中...')
                    self.no_activity_label.setStyleSheet('''
                        QLabel {
                            text-align: center;
                            color: #adb5bd;
                            font-size: 16px;
                            font-style: italic;
                            padding: 30px;
                        }
                    ''')
                    self.no_activity_label.setAlignment(Qt.AlignCenter)
                    self.running_layout.addWidget(self.no_activity_label)
                else:
                    self.no_activity_label.show()
            else:
                if self.no_activity_label: self.no_activity_label.hide()
                # 3. 添加/更新
                for index, activity in enumerate(sorted_activities):
                    log_id = activity[0]
                    if log_id in self.running_widgets:
                        widget = self.running_widgets[log_id]
                        widget.update_data(activity)
                    else:
                        widget = RunningActivityWidget(activity, self.db_manager)
                        widget.pause_clicked.connect(self.pause_activity)
                        widget.resume_clicked.connect(self.resume_activity)
                        widget.stop_clicked.connect(self.stop_activity)
                        widget.edit_clicked.connect(self.edit_running_activity)
                        # 连接番茄钟状态变化信号到悬浮窗（防御性检查）
                        if hasattr(self, 'floating_widget') and self.floating_widget:
                            try:
                                widget.pomodoro_toggled.connect(self.floating_widget.set_pomodoro_mode)
                            except Exception as e:
                                print(f"Warning: Failed to connect pomodoro signal: {e}")
                        
                        insert_idx = index + (1 if self.no_activity_label and self.running_layout.indexOf(self.no_activity_label) != -1 else 0)
                        self.running_layout.insertWidget(insert_idx, widget)
                        self.running_widgets[log_id] = widget
                        self.running_order.append(log_id)
                    widget.update_display()
        except Exception as e:
            print(f"Error in update_running_activities: {e}")
        finally:
            if layout_changed:
                self.running_layout.parentWidget().setUpdatesEnabled(True)

    def filter_activities(self, text: str):
        text = text.lower()
        filtered = [a for a in self.db_manager.get_activities() if text in a[1].lower()]
        self.rebuild_activity_grid(filtered)

    def start_activity_from_todo(self, activity_id: int, note: str):
        """从待办事项直接启动活动（跳过备注确认）"""
        self.update_timer.stop()
        try:
            if self.db_manager.start_activity(activity_id, note):
                self.refresh_all()
        finally:
            self.update_timer.start()

    def start_activity(self, activity_id: int):
        self.update_timer.stop()
        try:
            # 使用自定义的精致对话框
            print("开始活动...", 569)
            dialog = ActivityNoteDialog("开始活动", self)
            if dialog.exec() == QDialog.Accepted:
                note = dialog.get_note()
                print("活动内容:\t", note, 573)
                if self.db_manager.start_activity(activity_id, note):
                    print("刷新全部...", 575)
                    self.refresh_all()
        finally:
            self.update_timer.start()
    
    def pause_activity(self, log_id: int):
        if self.db_manager.pause_activity(log_id):
            self.update_running_activities()
    
    def resume_activity(self, log_id: int):
        print(f"[悬浮窗联动] resume_activity({log_id}) 开始")
        result = self.db_manager.resume_activity(log_id)
        print(f"[悬浮窗联动] db_manager.resume_activity 返回: {result}")
        if result:
            print(f"[悬浮窗联动] 刷新运行中活动列表...")
            self.update_running_activities()
            # 验证状态
            running = self.db_manager.get_running_activities()
            target = [r for r in running if r[0] == log_id]
            if target:
                print(f"[悬浮窗联动] 恢复后状态: {target[0][6]}")
    
    def resume_completed_activity(self, log_id: int):
        if self.db_manager.resume_completed_activity(log_id):
            self.refresh_all()

    def stop_activity(self, log_id: int):
        """停止活动 - 优化：避免阻塞式对话框导致崩溃"""
        # 如果是批量停止模式，跳过自动刷新和定时器操作
        if getattr(self, '_is_batch_stopping', False):
            # 仅执行数据库操作
            duration = self.db_manager.stop_activity(log_id)
            print(f"批量停止活动 {log_id}:\t{duration}")
            return

        self.update_timer.stop()
        try:
            print("停止活动...")
            duration = self.db_manager.stop_activity(log_id)
            print("停止活动:\t", duration)
            if duration > 0:
                # 使用状态栏显示消息，避免阻塞式 QMessageBox
                hours = duration // 3600
                mins = (duration % 3600) // 60
                self.statusBar().showMessage(f'活动已停止 - 持续时间: {hours}小时{mins}分钟', 5000)
            self.refresh_all()
        finally:
            self.update_timer.start()
    
    
    def edit_running_activity(self, log_id: int):
        self.update_timer.stop()
        try:
            log_data = self.db_manager.get_log_by_id(log_id)
            if log_data and EditLogDialog(self.db_manager, log_data, self).exec_() == QDialog.Accepted:
                self.refresh_all()
        finally:
            self.update_timer.start()

    def add_activity(self):
        self.update_timer.stop()
        try:
            dialog = AddActivityDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_activity_data()
                if data['name'] and self.db_manager.add_activity(data['name'], data['color'], data['icon'], data['goal_minutes']):
                    self.refresh_all()
        finally:
            self.update_timer.start()

    def add_manual_log(self, activity_id: int = None):
        self.update_timer.stop()
        try:
            dialog = ManualLogDialog(self.db_manager, activity_id, self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_log_data()
                if data['end_time'] > data['start_time'] and self.db_manager.add_manual_log(data['activity_id'], data['start_time'], data['end_time'], data['note']):
                    self.refresh_all()
        finally:
            self.update_timer.start()

    def stop_all_activities(self):
        running = self.db_manager.get_running_activities()
        if running and QMessageBox.question(self, '确认', f'确定停止所有 {len(running)} 个活动？') == QMessageBox.Yes:
            for act in running: self.db_manager.stop_activity(act[0])
            self.refresh_all()

    def edit_activity(self, activity_id: int):
        """编辑活动"""
        self.update_timer.stop()
        try:
            # 查找对应的活动数据
            activity_data = None
            for w in self.activity_widgets:
                if w.activity_id == activity_id:
                    activity_data = w.activity_data
                    break
            
            if activity_data is None:
                return
            
            dialog = AddActivityDialog(self)
            dialog.set_data(activity_data)
            
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_activity_data()
                if data['name']:
                    success = self.db_manager.update_activity(
                        activity_id,
                        name=data['name'],
                        color=data['color'],
                        icon=data['icon'],
                        goal_minutes=data['goal_minutes']
                    )
                    if success:
                        self.refresh_all()
                        self.statusBar().showMessage(f'活动 "{data["name"]}" 已更新', 3000)
                    else:
                        QMessageBox.warning(self, '更新失败', '活动名称可能已存在，请使用其他名称。')
        finally:
            self.update_timer.start()
    
    def delete_activity(self, activity_id: int):
        """删除活动"""
        self.update_timer.stop()
        try:
            # 获取活动名称
            activity_name = ''
            for w in self.activity_widgets:
                if w.activity_id == activity_id:
                    activity_name = w.name
                    break
            
            # 检查是否有运行中的任务
            running = self.db_manager.get_running_activities()
            running_ids = [r[0] for r in running]
            # 检查该活动是否有正在运行的记录
            has_running = any(
                r for r in running
                if self._get_activity_id_for_log(r[0]) == activity_id
            )
            if has_running:
                QMessageBox.warning(self, '无法删除', f'活动 "{activity_name}" 当前正在运行中，请先停止后再删除。')
                return
            
            # 查询关联的时间记录数量
            log_count = self.db_manager.get_activity_log_count(activity_id)
            
            if log_count > 0:
                reply = QMessageBox.question(
                    self, '确认删除',
                    f'活动 "{activity_name}" 关联了 {log_count} 条时间记录。\n\n'
                    f'• 点击「是」将删除活动和所有关联记录\n'
                    f'• 点击「否」取消操作',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
                delete_logs = True
            else:
                reply = QMessageBox.question(
                    self, '确认删除',
                    f'确定要删除活动 "{activity_name}" 吗？',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
                delete_logs = False
            
            if self.db_manager.delete_activity(activity_id, delete_logs=delete_logs):
                self.refresh_all()
                self.statusBar().showMessage(f'活动 "{activity_name}" 已删除', 3000)
            else:
                QMessageBox.warning(self, '删除失败', '无法删除该活动，请检查是否有运行中的任务。')
        finally:
            self.update_timer.start()
    
    def _get_activity_id_for_log(self, log_id: int) -> int:
        """获取时间记录对应的活动ID"""
        result = self.db_manager.fetchone_safe(
            "SELECT activity_id FROM time_logs WHERE id = ?", (log_id,)
        )
        return result[0] if result else -1

    def on_logs_updated(self): self.refresh_all()
    
    def refresh_all(self):
        """刷新所有界面（添加防抖机制）"""
        # 初始化防抖定时器
        if not hasattr(self, '_refresh_debounce_timer'):
            self._refresh_debounce_timer = QTimer(self)
            self._refresh_debounce_timer.setSingleShot(True)
            self._refresh_debounce_timer.setInterval(200) # 200ms 延迟
            self._refresh_debounce_timer.timeout.connect(self._do_refresh_all)
            
        print("请求刷新...", 693)
        self._refresh_debounce_timer.start() # 重置定时器

    def _do_refresh_all(self):
        """执行实际刷新逻辑"""
        print("执行从容刷新...", 698)
        self.refresh_activities()
        self.update_running_activities()
        # 统计图表在快速刷新时容易崩溃 (Qt Charts 资源竞争)
        # 改为只标记脏数据，让用户切换到统计标签页时才真正刷新
        try:
            if hasattr(self, 'statistics_widget') and self.statistics_widget:
                self.statistics_widget._is_dirty = True
                # 只有当统计页当前可见时才刷新
                if self.statistics_widget.isVisible():
                    self.statistics_widget.refresh_all_stats()
        except Exception as e:
            print(f"统计刷新失败: {e}")
            
        self.daily_log_widget.refresh_logs()
        if hasattr(self, 'todo_list_widget'):
            self.todo_list_widget.refresh_list()
            self.todo_list_widget.refresh_activities() 
        print("刷新完成...", 706)

    def check_schedule_alert(self):
        """检查日程提醒"""
        from utils.log_manager import info, warning, error
        
        now_str = QTime.currentTime().toString("HH:mm")
        info(f"[日程提醒] 检查时间: {now_str}")
        
        # 查找包含当前时间的日程
        schedule = self.db_manager.get_current_schedule(now_str)
        info(f"[日程提醒] 查询结果: {schedule}")
        
        if schedule:
            # schedule: id, start, end, content
            schedule_id = schedule[0]
            start_time = schedule[1]
            end_time = schedule[2]
            content = schedule[3]
            info(f"[日程提醒] 找到日程 - ID:{schedule_id}, 时间:{start_time}-{end_time}, 内容:{content}")
            
            # 简单去重：如果当前已经在提示该内容，就不重复弹
            if hasattr(self, '_last_alert_content') and self._last_alert_content == content:
                info(f"[日程提醒] 跳过 - 已经提醒过该内容: {content}")
                return
                
            self._last_alert_content = content
            
            # 检查当前是否已经在做此事？
            running_names = [w.name for w in self.running_widgets.values()]
            info(f"[日程提醒] 当前运行中的活动: {running_names}")
            if content in running_names:
                info(f"[日程提醒] 跳过 - 该活动已在运行: {content}")
                return
                
            msg = QMessageBox(self)
            msg.setWindowTitle("日程提醒")
            msg.setText(f"当前时间段 ({start_time}-{end_time}) 计划进行：\n\n📌 {content}\n\n是否立即开始？")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            
            result = msg.exec()
            info(f"[日程提醒] 用户选择: {'是' if result == QMessageBox.Yes else '否'}")
            
            if result == QMessageBox.Yes:
                # 尝试自动开始对应活动
                activities = self.db_manager.get_activities()
                info(f"[日程提醒] 可用活动数量: {len(activities)}")
                
                # 列出所有活动名称便于调试
                activity_names = [a[1] for a in activities]
                info(f"[日程提醒] 可用活动名称: {activity_names}")
                
                # 查找匹配的活动
                target_act = next((a for a in activities if a[1] == content), None)
                info(f"[日程提醒] 匹配活动(精确匹配): {target_act}")
                
                # 如果精确匹配失败，尝试模糊匹配
                if not target_act:
                    target_act = next((a for a in activities if content in a[1] or a[1] in content), None)
                    info(f"[日程提醒] 匹配活动(模糊匹配): {target_act}")
                
                if target_act:
                    activity_id = target_act[0]
                    activity_name = target_act[1]
                    info(f"[日程提醒] 准备启动活动 - ID:{activity_id}, 名称:{activity_name}")
                    
                    # 直接启动活动
                    note = f"[日程提醒] {start_time}-{end_time}"
                    info(f"[日程提醒] 调用 db_manager.start_activity({activity_id}, '{note}')")
                    
                    try:
                        result = self.db_manager.start_activity(activity_id, note)
                        info(f"[日程提醒] start_activity 返回值: {result}")
                        
                        if result:
                            info("[日程提醒] 活动启动成功，正在刷新界面...")
                            # 确保主窗口显示并刷新界面
                            self.showNormal()
                            self.activateWindow()
                            self.raise_()
                            self.refresh_all()
                            info("[日程提醒] 界面刷新完成")
                            QMessageBox.information(self, "已开始", f"活动 '{activity_name}' 已自动开始！")
                        else:
                            warning(f"[日程提醒] start_activity 返回 False/None，活动启动失败")
                            QMessageBox.warning(self, "启动失败", f"无法启动活动 '{activity_name}'，请手动开始。")
                    except Exception as e:
                        error(f"[日程提醒] 启动活动时发生异常: {e}")
                        import traceback
                        error(f"[日程提醒] 异常堆栈: {traceback.format_exc()}")
                        QMessageBox.critical(self, "错误", f"启动活动时发生错误:\n{e}")
                else:
                    warning(f"[日程提醒] 未找到匹配的活动 - 日程内容:'{content}', 可用活动:{activity_names}")
                    QMessageBox.information(self, "提示", f"未找到名为 '{content}' 的活动，请手动开始。\n\n可用活动: {', '.join(activity_names)}")

    def show_help(self):
        """显示帮助手册"""
        dialog = HelpDialog(self)
        dialog.exec()
    
    def show_about(self):
        QMessageBox.about(self, '关于 aTimeLogPro', '<h3>aTimeLogPro v2.0</h3><p>专业的时间记录工具</p>')

    def closeEvent(self, event):
        # 记录窗口几何位置
        print("关闭软件...", 763)
        try:
            geom = self.geometry()
            self.config.set("geometry", [geom.x(), geom.y(), geom.width(), geom.height()])
        except: pass
        
        # 检查是否关闭到托盘
        if self.config.get("close_to_tray", True):
            self.hide()
            # 联动：进入后台时自动开启悬浮窗
            if hasattr(self, 'floating_widget'):
                self.floating_widget.show()
            try:
                self.tray_icon.showMessage("aTimeLogPro", "已缩小到系统托盘，悬浮窗已开启", QIcon(), 2000)
            except: pass
            event.ignore()
            return

        running = self.db_manager.get_running_activities()
        if running:
            reply = QMessageBox.question(self, '退出确认', f'还有 {len(running)} 个运行中的活动，是否停止并退出？', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel: return event.ignore()
            if reply == QMessageBox.Yes:
                for act in running: self.db_manager.stop_activity(act[0])
        
        # 安全退出：先停计时器，再关数据库
        # 停止更新定时器
        if hasattr(self, 'update_timer') and self.update_timer:
            try:
                self.update_timer.stop()
            except RuntimeError:
                pass
        
        # 停止日程提醒服务
        if hasattr(self, 'schedule_reminder') and self.schedule_reminder:
            try:
                self.schedule_reminder.stop()
            except RuntimeError:
                pass
        
        # 关闭悬浮窗
        if hasattr(self, 'floating_widget') and self.floating_widget:
            try:
                if hasattr(self.floating_widget, 'timer'):
                    self.floating_widget.timer.stop()
                self.floating_widget.close()
            except RuntimeError:
                pass

        # 关闭数据库
        try:
            self.db_manager.close()
        except Exception as e:
            print(f"关闭数据库时出错: {e}")
        
        event.accept()
        
        # 强制退出应用，确保不残留进程
        QApplication.instance().quit()

    def changeEvent(self, event):
        """处理最小化事件"""
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and self.config.get("minimize_to_tray", True):
                self.hide()
                if hasattr(self, 'floating_widget'):
                    self.floating_widget.show() # 最小化时也开启悬浮窗
                event.ignore()
        super().changeEvent(event)


class TimeLoggerApp(QApplication):
    """应用程序类"""
    
    def __init__(self, sys_argv):
        # Qt6 默认启用高 DPI 缩放，无需手动设置
        super().__init__(sys_argv)

        self.setApplicationName('aTimeLogPro')
        self.setApplicationVersion('2.0')
        # 关键修复：防止主窗口隐藏后程序自动退出
        self.setQuitOnLastWindowClosed(False)

        self.setStyle("Fusion")
        
        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'main.ico')
        png_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'main.png')
        
        if os.path.exists(icon_path) and sys.platform == 'win32':
            self.setWindowIcon(QIcon(icon_path))
        elif os.path.exists(png_path):
            self.setWindowIcon(QIcon(png_path))
        elif os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 设置应用样式
        self.setStyleSheet(get_app_style())
        
        self.main_window = MainWindow()
        self.main_window.show()
