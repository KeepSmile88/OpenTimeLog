#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志列表组件
显示指定日期的所有时间记录
"""

import os
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QScrollArea, QDialog
)
from PySide6.QtCore import QDate, Signal, Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ui.dialogs.edit_log import EditLogDialog
from ui.styles.app_style import theme_manager

class DailyLogWidget(QWidget):
    """日志列表组件"""
    
    # 信号：恢复已完成的活动
    resume_completed = Signal(int)
    # 信号：日志已更新
    logs_updated = Signal()
    
    def __init__(self, db_manager, parent=None):
        """初始化组件"""
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.refresh_logs()
        
        # 监听主题变更，刷新列表以更新样式
        theme_manager.theme_changed.connect(lambda t: self.refresh_logs())
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 日期选择
        date_layout = QHBoxLayout()
        self.date_lbl = QLabel('日期:')
        date_layout.addWidget(self.date_lbl)
        
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.refresh_logs)
        
        self.prev_day_btn = QPushButton('◀ 前一天')
        self.next_day_btn = QPushButton('后一天 ▶')
        
        self.prev_day_btn.clicked.connect(self.prev_day)
        self.next_day_btn.clicked.connect(self.next_day)
        
        date_layout.addWidget(self.prev_day_btn)
        date_layout.addWidget(self.date_edit)
        date_layout.addWidget(self.next_day_btn)
        date_layout.addStretch()
        
        layout.addLayout(date_layout)
        
        # 日志列表
        self.log_list = QVBoxLayout()
        self.log_list.setSpacing(8)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.log_list)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # 滚动区域样式
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        # 我们需要在 refresh_logs 里更新 scroll_widget 的背景色，或者在这里设置透明，让 QScrollArea 控制
        
        self.scroll_area = scroll_area
        self.scroll_widget = scroll_widget
        
        layout.addWidget(scroll_area)
        # self.setLayout(layout) # QWidget already has layout set by passing self to QVBoxLayout
    
    def prev_day(self):
        """前一天"""
        current_date = self.date_edit.date()
        self.date_edit.setDate(current_date.addDays(-1))
    
    def next_day(self):
        """后一天"""
        current_date = self.date_edit.date()
        self.date_edit.setDate(current_date.addDays(1))
    
    def refresh_logs(self):
        """刷新日志列表"""
        t = theme_manager.current_tokens
        
        # 更新容器样式
        self.setStyleSheet(f"""
            DailyLogWidget {{ background-color: {t['bg_main']}; color: {t['text_primary']}; }}
            QLabel {{ color: {t['text_primary']}; }}
            QPushButton {{ 
                background-color: {t['bg_input']}; 
                border: 1px solid {t['border']}; 
                border-radius: 4px; 
                padding: 4px 8px;
                color: {t['text_primary']};
            }}
            QPushButton:hover {{ background-color: {t['bg_hover']}; border-color: {t['primary']}; }}
        """)
        
        self.scroll_widget.setStyleSheet(f"background-color: {t['bg_main']};")
        
        # 清除现有日志
        while self.log_list.count():
            item = self.log_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取日志
        target_date = self.date_edit.date().toPython()
        logs = self.db_manager.get_daily_logs(target_date)
        
        if not logs:
            no_data_label = QLabel('这一天没有时间记录')
            no_data_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 14px; padding: 20px;")
            no_data_label.setAlignment(Qt.AlignCenter)
            self.log_list.addWidget(no_data_label)
            self.log_list.addStretch()
            return
        
        # 添加日志项
        for log in logs:
            log_item = self.create_log_item(log, t)
            self.log_list.addWidget(log_item)
        
        self.log_list.addStretch()
    
    def create_log_item(self, log, t) -> QWidget:
        """创建日志项组件"""
        log_id, name, color, icon, start_time, end_time, duration_seconds, note, status, is_manual = log
        
        widget = QWidget()
        
        # 动态生成样式
        # 左边框使用 Activity 颜色
        act_color = color if color else t['primary']
        
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {t['bg_item']};
                border: 1px solid {t['border']};
                border-left: 4px solid {act_color};
                border-radius: 6px;
            }}
            QWidget:hover {{
                border-color: {t['primary']};
                border-left: 4px solid {act_color};
                background-color: {t['bg_hover']};
            }}
            QLabel {{ border: none; background: transparent; }}
            QPushButton {{ background: {t['bg_input']}; border: 1px solid {t['border_light']}; }}
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 活动信息
        info_layout = QVBoxLayout()
        
        title_label = QLabel(f"{icon} {name}")
        title_label.setStyleSheet(f'font-weight: bold; font-size: 13px; color: {t["text_primary"]};')
        
        # 时间信息
        start_dt = datetime.fromisoformat(start_time)
        time_info = f"开始: {start_dt.strftime('%H:%M')}"
        
        if end_time:
            end_dt = datetime.fromisoformat(end_time)
            duration_min = (duration_seconds or 0) // 60
            duration_hour = duration_min // 60
            duration_min = duration_min % 60
            time_info += f"  结束: {end_dt.strftime('%H:%M')}  时长: {duration_hour}h{duration_min}m"
        else:
            time_info += "  (进行中)"
        
        time_label = QLabel(time_info)
        time_label.setStyleSheet(f'color: {t["text_secondary"]}; font-size: 12px;')
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(time_label)
        
        if note:
            note_label = QLabel(f"备注: {note}")
            note_label.setStyleSheet(f'color: {t["text_light"]}; font-size: 11px;')
            info_layout.addWidget(note_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 状态和操作按钮
        button_layout = QVBoxLayout()
        
        # 状态标签
        if status == 'running':
            status_label = QLabel('🟢 运行中')
            status_label.setStyleSheet(f'color: {t["success"]}; font-size: 11px; font-weight: bold;')
        elif status == 'paused':
            status_label = QLabel('⏸️ 暂停')
            status_label.setStyleSheet(f'color: {t["warning"]}; font-size: 11px; font-weight: bold;')
        else:
            status_label = QLabel('✅ 完成')
            status_label.setStyleSheet(f'color: {t["text_secondary"]}; font-size: 11px; font-weight: bold;')
        
        button_layout.addWidget(status_label)
        
        if is_manual:
            manual_label = QLabel('📝 手动')
            manual_label.setStyleSheet(f'font-size: 10px; color: {t["text_light"]};')
            button_layout.addWidget(manual_label)
        
        # 按钮行
        btn_row = QHBoxLayout()
        
        # 已完成的任务显示"继续"按钮
        if status == 'completed':
            resume_btn = QPushButton('▶️')
            resume_btn.setToolTip("继续此活动")
            resume_btn.setFixedSize(24, 24)
            resume_btn.setStyleSheet(f"""
                QPushButton {{ 
                    color: {t['success']}; border: 1px solid {t['border']}; border-radius: 4px; 
                }}
                QPushButton:hover {{ background-color: {t['success']}20; }}
            """)
            resume_btn.clicked.connect(lambda: self.resume_completed.emit(log_id))
            btn_row.addWidget(resume_btn)
        
        # 编辑按钮
        edit_btn = QPushButton('✏️')
        edit_btn.setToolTip("编辑记录")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setStyleSheet(f"""
            QPushButton {{ 
                color: {t['text_secondary']}; border: 1px solid {t['border']}; border-radius: 4px; 
            }}
            QPushButton:hover {{ background-color: {t['bg_hover']}; color: {t['primary']}; }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_log(log))
        btn_row.addWidget(edit_btn)
        
        button_layout.addLayout(btn_row)
        layout.addLayout(button_layout)
        
        return widget
    
    def edit_log(self, log):
        """编辑日志"""
        dialog = EditLogDialog(self.db_manager, log, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_logs()
            self.logs_updated.emit()
