#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日程管理组件 (v2.0)
支持多视图（日/周/月）和增强的时间选择
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QTimeEdit, QDateEdit, QHeaderView, QMessageBox, 
    QSplitter, QComboBox, QTabWidget, QCalendarWidget, QToolButton
)
from PySide6.QtCore import Qt, QTime, QDate, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QTextCharFormat
from functools import partial

from ui.utils.time_picker import TimePickerDialog
from ui.styles.app_style import theme_manager, get_cjk_font


class ScheduleManagerWidget(QWidget):
    """日程管理组件"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_date = QDate.currentDate()
        self.setup_ui()
        self.update_styles()
        self.refresh_list()
        
        # 监听主题变更
        theme_manager.theme_changed.connect(lambda t: self.update_styles())
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部工具栏：日期选择与视图切换
        top_bar = QHBoxLayout()
        
        self.date_lbl = QLabel("📅 日期:")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(self.current_date)
        self.date_edit.dateChanged.connect(self.on_date_changed)
        self.date_edit.setFixedWidth(120)
        
        top_bar.addWidget(self.date_lbl)
        top_bar.addWidget(self.date_edit)
        
        self.today_btn = QPushButton("今天")
        self.today_btn.clicked.connect(self._on_today_clicked)
        self.today_btn.setFixedSize(60, 28)
        top_bar.addWidget(self.today_btn)
        
        top_bar.addStretch()
        
        layout.addLayout(top_bar)
        
        # 主要内容区：左侧添加，右侧显示
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- 左侧：添加区域 ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        self.add_title = QLabel("📝 添加日程")
        self.add_title.setFont(get_cjk_font(12, QFont.Weight.Bold))
        left_layout.addWidget(self.add_title)
        
        # 开始时间
        self.lbl_start = QLabel("开始时间:")
        left_layout.addWidget(self.lbl_start)
        h_start = QHBoxLayout()
        self.start_input = QTimeEdit()
        self.start_input.setDisplayFormat("HH:mm")
        self.start_input.setTime(QTime.currentTime())
        self.start_input.setFixedHeight(32)
        
        self.btn_start_pick = QToolButton()
        self.btn_start_pick.setText("🕒")
        self.btn_start_pick.setFixedSize(32, 32)
        self.btn_start_pick.clicked.connect(self._on_start_pick_clicked)
        
        h_start.addWidget(self.start_input)
        h_start.addWidget(self.btn_start_pick)
        left_layout.addLayout(h_start)
        
        # 结束时间
        self.lbl_end = QLabel("结束时间:")
        left_layout.addWidget(self.lbl_end)
        h_end = QHBoxLayout()
        self.end_input = QTimeEdit()
        self.end_input.setDisplayFormat("HH:mm")
        self.end_input.setTime(QTime.currentTime().addSecs(3600))
        self.end_input.setFixedHeight(32)
        
        self.btn_end_pick = QToolButton()
        self.btn_end_pick.setText("🕒")
        self.btn_end_pick.setFixedSize(32, 32)
        self.btn_end_pick.clicked.connect(self._on_end_pick_clicked)
        
        h_end.addWidget(self.end_input)
        h_end.addWidget(self.btn_end_pick)
        left_layout.addLayout(h_end)
        
        # 活动内容
        self.lbl_content = QLabel("活动内容:")
        left_layout.addWidget(self.lbl_content)
        self.content_input = QComboBox()
        self.content_input.setEditable(True)
        self.content_input.setFixedHeight(32)
        activities = self.db_manager.get_activities()
        self.content_input.addItems([a[1] for a in activities])
        left_layout.addWidget(self.content_input)
        
        left_layout.addStretch()
        
        # 按钮
        self.add_btn = QPushButton("添加并继续 (Next)")
        self.add_btn.setStyleSheet("padding: 10px; border-radius: 4px; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_schedule)
        left_layout.addWidget(self.add_btn)
        
        # --- 右侧：多视图展示区 ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        self.view_tabs = QTabWidget()
        
        # 1. 日视图 (List)
        self.day_page = QWidget()
        day_layout = QVBoxLayout(self.day_page)
        
        day_header = QHBoxLayout()
        self.day_title = QLabel("今日日程")
        self.day_title.setFont(get_cjk_font(10, QFont.Bold))
        
        self.clear_btn = QPushButton("清空当日")
        self.clear_btn.clicked.connect(self.clear_current_day)
        
        day_header.addWidget(self.day_title)
        day_header.addStretch()
        day_header.addWidget(self.clear_btn)
        day_layout.addLayout(day_header)
        
        self.day_table = QTableWidget()
        self.day_table.setColumnCount(3)
        self.day_table.setHorizontalHeaderLabels(["时间段", "内容", "操作"])
        self.day_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.day_table.verticalHeader().setVisible(False)
        self.day_table.setSelectionBehavior(QTableWidget.SelectRows)
        day_layout.addWidget(self.day_table)
        
        self.view_tabs.addTab(self.day_page, "日视图")
        
        # 2. 周视图 (Table)
        self.week_page = QWidget()
        week_layout = QVBoxLayout(self.week_page)
        week_layout.setContentsMargins(0, 0, 0, 0)
        self.week_table = QTableWidget()
        self.week_table.setColumnCount(7)
        self.week_table.setHorizontalHeaderLabels(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        # 让所有列均匀拉伸填满表格宽度
        self.week_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.week_table.horizontalHeader().setMinimumSectionSize(60)
        # 启用鼠标追踪和 tooltip
        self.week_table.setMouseTracking(True)
        self.week_table.setWordWrap(True)
        week_layout.addWidget(self.week_table)
        
        self.view_tabs.addTab(self.week_page, "周视图")
        
        # 3. 月视图 (增强版)
        self.month_page = QWidget()
        month_layout = QVBoxLayout(self.month_page)
        month_layout.setContentsMargins(0, 0, 0, 0)
        month_layout.setSpacing(8)
        
        # 日历控件
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.on_calendar_clicked)
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.currentPageChanged.connect(self.update_month_markers)
        month_layout.addWidget(self.calendar, 3)
        
        # 选中日期的日程详情区域
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(8, 8, 8, 8)
        
        self.month_date_label = QLabel("选中日期的日程")
        self.month_date_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        detail_layout.addWidget(self.month_date_label)
        
        # 日程列表表格
        self.month_schedule_table = QTableWidget()
        self.month_schedule_table.setColumnCount(3)
        self.month_schedule_table.setHorizontalHeaderLabels(["时间", "活动", "操作"])
        self.month_schedule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.month_schedule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.month_schedule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.month_schedule_table.setColumnWidth(0, 100)
        self.month_schedule_table.setColumnWidth(2, 60)
        self.month_schedule_table.setAlternatingRowColors(True)
        detail_layout.addWidget(self.month_schedule_table)
        
        month_layout.addWidget(detail_widget, 2)
        
        self.view_tabs.addTab(self.month_page, "月视图")
        
        self.view_tabs.currentChanged.connect(self.refresh_list)
        
        right_layout.addWidget(self.view_tabs)
        
        # 设置左右两侧最小宽度
        left_widget.setMinimumWidth(180)
        left_widget.setMaximumWidth(280)
        right_widget.setMinimumWidth(500)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 600])
        
        layout.addWidget(splitter)

    def update_styles(self):
        """更新所有组件样式"""
        t = theme_manager.current_tokens
        
        # 1. 基础文字颜色
        labels = [self.date_lbl, self.add_title, self.lbl_start, self.lbl_end, self.lbl_content, self.day_title, self.month_date_label]
        for lbl in labels:
            lbl.setStyleSheet(f"color: {t['text_primary']};")
            
        # 2. 按钮样式
        # 添加按钮 (Primary)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['primary']}; 
                color: {t['text_inverse']}; 
                padding: 10px; 
                border-radius: 4px; 
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {t['primary_hover']}; }}
        """)

        self.end_input.setStyleSheet(f"""
            /*
            QTimeEdit {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding-right: 24px; /* 给按钮留空间 */
                background-color: {t['bg_input']};
            }}
            */

            QTimeEdit::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                height: 12px;
                background-color: {t['bg_input']};
                border-left: 1px solid {t['border']};
                border-bottom: 1px solid {t['border']};
                border-top-right-radius: 4px;
            }}

            QTimeEdit::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                height: 12px;
                background-color: {t['bg_input']};
                border-left: 1px solid {t['border']};
                border-top: 1px solid {t['border']};
                border-bottom-right-radius: 4px;
            }}

            QTimeEdit::up-button:hover,
            QTimeEdit::down-button:hover {{
                background-color: {t['bg_hover']};
                border-color: {t['primary']};
            }}

            QTimeEdit::up-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid {t['bg_input']};
            }}

            QTimeEdit::down-arrow {{
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {t['bg_input']};
            }}
        """)

        # 工具按钮
        tool_btn_style = f"""
            QToolButton {{
                background-color: {t['bg_input']};
                border: 1px solid {t['border']};
                border-radius: 4px;
            }}
            QToolButton:hover {{ background-color: {t['bg_hover']}; border-color: {t['primary']}; }}
        """
        self.btn_start_pick.setStyleSheet(tool_btn_style)
        self.btn_end_pick.setStyleSheet(tool_btn_style)
        
        # 普通按钮 (Secondary/Danger)
        self.today_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['bg_input']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {t['bg_hover']}; border-color: {t['primary']}; }}
        """)
        
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: {t['danger']}; 
                border: 1px solid {t['danger']}; 
                padding: 4px 8px; 
                border-radius: 4px;
                background: transparent;
            }}
            QPushButton:hover {{ background-color: {t['danger']}20; }}
        """)
        
        # 3. 表格样式
        table_style = f"""
            QTableWidget {{
                background-color: {t['bg_card']};
                gridline-color: {t['border_light']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                alternate-background-color: {t['bg_item']};
            }}
            QHeaderView::section {{
                background-color: {t['bg_main']};
                color: {t['text_secondary']};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{ padding: 4px; }}
            QTableWidget::item:selected {{ background-color: {t['bg_hover']}; color: {t['primary']}; }}
        """
        self.day_table.setStyleSheet(table_style)
        self.week_table.setStyleSheet(table_style)
        self.month_schedule_table.setStyleSheet(table_style)
        
        # 4. 日历样式
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {t['primary']};
                min-height: 40px;
            }}
            QCalendarWidget QToolButton {{
                color: {t['text_inverse']};
                font-size: 14px;
                font-weight: bold;
                padding: 6px;
                background: transparent;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: rgba(255,255,255,0.2);
                border-radius: 4px;
            }}
            QCalendarWidget QTableView {{
                background-color: {t['bg_card']};
                selection-background-color: {t['primary']};
                selection-color: {t['text_inverse']};
                color: {t['text_primary']};
                alternate-background-color: {t['bg_item']};
            }}
        """)
        
        # 5. 更新所有删除按钮（如果当前已显示）
        # 这需要 refresh_list 被调用，theme_changed 信号连接中已经调用了 self.update_styles()
        # 我们需要在 update_styles 后调用 refresh_list 吗？
        # 实际上 theme_changed -> update_styles -> refresh_list (in lambda?)
        # 构造函数里: connect(lambda t: self.update_styles())
        # update_styles 只更新样式表。对于动态创建的按钮（如删除按钮），它们的样式是在创建时内联设置的，或者依赖 clear_btn 类似的逻辑
        
        # 重新刷新列表以应用新样式的删除按钮
        self.refresh_list()

    def open_time_picker(self, time_edit):
        """打开时间选择器"""
        dialog = TimePickerDialog(time_edit.time(), self)
        if dialog.exec():
            time_edit.setTime(dialog.selected_time)

    def on_date_changed(self, date):
        self.current_date = date
        self.refresh_list()
        
    def on_calendar_clicked(self, date):
        self.date_edit.setDate(date)
        self.view_tabs.setCurrentIndex(0) 

    def add_schedule(self):
        """添加日程"""
        start_time = self.start_input.time().toString("HH:mm")
        end_time = self.end_input.time().toString("HH:mm")
        content = self.content_input.currentText().strip()
        target_date_str = self.current_date.toString("yyyy-MM-dd")
        
        if not content:
            QMessageBox.warning(self, "提示", "请输入活动内容")
            return
            
        if self.start_input.time() >= self.end_input.time():
             QMessageBox.warning(self, "提示", "结束时间必须晚于开始时间")
             return

        self.db_manager.add_schedule(start_time, end_time, content, target_date_str)
        self.refresh_list()
        
        # 自动准备
        self.start_input.setTime(self.end_input.time())
        self.end_input.setTime(self.end_input.time().addSecs(3600))
        self.content_input.setFocus()
        
    def refresh_list(self):
        t = theme_manager.current_tokens
        date_str = self.current_date.toString("yyyy-MM-dd")
        self.day_title.setText(f"{date_str} 日程")
        
        # 1. 刷新日视图
        self.day_table.setRowCount(0)
        schedules = self.db_manager.get_schedules(date_str)
        self.day_table.setRowCount(len(schedules))
        for row, s in enumerate(schedules):
            time_str = f"{s[1]} - {s[2]}"
            
            self.day_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.day_table.setItem(row, 1, QTableWidgetItem(s[3]))
            
            del_btn = QPushButton("删除")
            del_btn.setStyleSheet(f"color: {t['danger']}; border: none; background: transparent;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(partial(self._on_delete_day_schedule, sid=s[0]))
            
            # Hover effect
            del_btn.setProperty("hover_style", f"color: {t['danger']}; font-weight: bold;")
            del_btn.setProperty("normal_style", f"color: {t['danger']};")
            
            self.day_table.setCellWidget(row, 2, del_btn)
            
        # 2. 如果当前是周视图，需要加载一周数据
        if self.view_tabs.currentIndex() == 1:
            self.load_weekly_view()
        
        # 3. 如果当前是月视图，需要更新日程标记
        if self.view_tabs.currentIndex() == 2:
            self.update_month_markers(self.calendar.yearShown(), self.calendar.monthShown())
    
    def on_calendar_clicked(self, date):
        self.current_date = date
        self.date_edit.setDate(date)
        self.load_month_schedule_list()
            
    def load_weekly_view(self):
        d = self.current_date
        monday = d.addDays(-(d.dayOfWeek() - 1))
        
        self.week_table.setRowCount(0)
        self.week_table.setRowCount(10)
        
        for i in range(7):
            day = monday.addDays(i)
            day_str = day.toString("yyyy-MM-dd")
            schedules = self.db_manager.get_schedules(day_str)
            
            for row, s in enumerate(schedules):
                if row >= 10: break
                text = f"{s[1]}-{s[2]} {s[3]}"
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled)
                item.setToolTip(f"{s[1]}-{s[2]} {s[3]}")
                self.week_table.setItem(row, i, item)

    def update_month_markers(self, year, month):
        t = theme_manager.current_tokens
        default_format = QTextCharFormat()
        # 保持无样式，继承日历背景
        
        has_schedule_format = QTextCharFormat()
        has_schedule_format.setBackground(QColor(t['primary_light'])) # 浅色背景
        has_schedule_format.setForeground(QColor(t['text_inverse']))
        has_schedule_format.setFontWeight(QFont.Bold)
        
        first_day = QDate(year, month, 1)
        days_in_month = first_day.daysInMonth()
        
        for day in range(1, days_in_month + 1):
            date = QDate(year, month, day)
            date_str = date.toString("yyyy-MM-dd")
            schedules = self.db_manager.get_schedules(date_str)
            
            if schedules:
                self.calendar.setDateTextFormat(date, has_schedule_format)
            else:
                self.calendar.setDateTextFormat(date, default_format)
        
        self.load_month_schedule_list()
    
    def load_month_schedule_list(self):
        t = theme_manager.current_tokens
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[selected_date.dayOfWeek() - 1]
        self.month_date_label.setText(f"📅 {date_str} ({weekday}) 的日程")
        
        schedules = self.db_manager.get_schedules(date_str)
        
        self.month_schedule_table.setRowCount(len(schedules))
        
        for row, s in enumerate(schedules):
            time_item = QTableWidgetItem(f"{s[1]}-{s[2]}")
            time_item.setFlags(Qt.ItemIsEnabled)
            time_item.setTextAlignment(Qt.AlignCenter)
            self.month_schedule_table.setItem(row, 0, time_item)
            
            activity_item = QTableWidgetItem(s[3])
            activity_item.setFlags(Qt.ItemIsEnabled)
            activity_item.setToolTip(s[3])
            self.month_schedule_table.setItem(row, 1, activity_item)
            
            del_btn = QPushButton("删除")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t['danger']};
                    color: {t['text_inverse']};
                    border: none;
                    border-radius: 3px;
                    padding: 3px 8px;
                }}
                QPushButton:hover {{
                    background-color: {t['danger']}CC;
                }}
            """)
            del_btn.clicked.connect(partial(self._on_delete_month_schedule, sid=s[0]))
            self.month_schedule_table.setCellWidget(row, 2, del_btn)
        
        if not schedules:
            self.month_schedule_table.setRowCount(1)
            empty_item = QTableWidgetItem("暂无日程")
            empty_item.setFlags(Qt.ItemIsEnabled)
            empty_item.setTextAlignment(Qt.AlignCenter)
            empty_item.setForeground(QColor(t['text_light']))
            self.month_schedule_table.setItem(0, 0, empty_item)
            self.month_schedule_table.setSpan(0, 0, 1, 3)
    
    def delete_month_schedule(self, sid):
        if QMessageBox.question(self, "确认", "确定删除该日程？") == QMessageBox.Yes:
            self.db_manager.delete_schedule(sid)
            self.update_month_markers(self.calendar.yearShown(), self.calendar.monthShown())

    def delete_item(self, sid):
        if QMessageBox.question(self, "确认", "确定删除该日程？") == QMessageBox.Yes:
            self.db_manager.delete_schedule(sid)
            self.refresh_list()
            
    def clear_current_day(self):
        if QMessageBox.question(self, "确认", f"确定清空 {self.current_date.toString('yyyy-MM-dd')} 的所有日程？") == QMessageBox.Yes:
            date_str = self.current_date.toString("yyyy-MM-dd")
            schedules = self.db_manager.get_schedules(date_str)
            for s in schedules:
                self.db_manager.delete_schedule(s[0])
            self.refresh_list()
    
    def _on_today_clicked(self):
        self.date_edit.setDate(QDate.currentDate())
    
    def _on_start_pick_clicked(self):
        self.open_time_picker(self.start_input)
    
    def _on_end_pick_clicked(self):
        self.open_time_picker(self.end_input)
    
    def _on_delete_day_schedule(self, sid):
        self.delete_item(sid)
    
    def _on_delete_month_schedule(self, sid):
        self.delete_month_schedule(sid)
