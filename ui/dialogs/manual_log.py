#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动添加时间记录对话框
"""

from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QTimeEdit, QSpinBox, QCheckBox, QTextEdit,
    QPushButton, QGroupBox
)
from PySide6.QtCore import QDate, QTime


class ManualLogDialog(QDialog):
    """手动添加时间记录对话框"""
    
    def __init__(self, db_manager, activity_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.activity_id = activity_id
        self.setWindowTitle('手动添加时间记录')
        self.setMinimumSize(450, 380)  # 改用最小尺寸
        self.resize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 活动选择
        layout.addWidget(QLabel('选择活动:'))
        self.activity_combo = QComboBox()
        activities = self.db_manager.get_activities()
        for activity in activities:
            self.activity_combo.addItem(f"{activity[3]} {activity[1]}", activity[0])
        
        if self.activity_id:
            for i in range(self.activity_combo.count()):
                if self.activity_combo.itemData(i) == self.activity_id:
                    self.activity_combo.setCurrentIndex(i)
                    break
        
        layout.addWidget(self.activity_combo)
        
        # 日期选择
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('日期:'))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.date_edit)
        layout.addLayout(date_layout)
        
        # 开始时间
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel('开始时间:'))
        self.start_time_edit = QTimeEdit(QTime.currentTime())
        start_layout.addWidget(self.start_time_edit)
        layout.addLayout(start_layout)
        
        # 结束时间
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel('结束时间:'))
        self.end_time_edit = QTimeEdit(QTime.currentTime().addSecs(3600))  # 默认1小时后
        end_layout.addWidget(self.end_time_edit)
        layout.addLayout(end_layout)
        
        # 或者直接输入时长
        duration_group = QGroupBox('或者直接输入时长')
        duration_layout = QHBoxLayout()
        
        duration_layout.addWidget(QLabel('小时:'))
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 23)
        duration_layout.addWidget(self.hours_spin)
        
        duration_layout.addWidget(QLabel('分钟:'))
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        duration_layout.addWidget(self.minutes_spin)
        
        self.use_duration_checkbox = QCheckBox('使用时长而非结束时间')
        self.use_duration_checkbox.toggled.connect(self.toggle_duration_mode)
        
        duration_layout.addWidget(self.use_duration_checkbox)
        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)
        
        # 备注
        layout.addWidget(QLabel('备注:'))
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(60)
        layout.addWidget(self.note_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton('添加记录')
        self.cancel_button = QPushButton('取消')
        
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setStyleSheet('QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }')
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def toggle_duration_mode(self, checked: bool):
        """切换时长模式"""
        self.end_time_edit.setEnabled(not checked)
    
    def get_log_data(self) -> dict:
        """获取记录数据
        
        Returns:
            包含记录信息的字典
        """
        activity_id = self.activity_combo.currentData()
        date = self.date_edit.date().toPython()
        start_time = self.start_time_edit.time().toPython()
        note = self.note_edit.toPlainText().strip()
        
        start_datetime = datetime.combine(date, start_time)
        
        if self.use_duration_checkbox.isChecked():
            hours = self.hours_spin.value()
            minutes = self.minutes_spin.value()
            end_datetime = start_datetime + timedelta(hours=hours, minutes=minutes)
        else:
            end_time = self.end_time_edit.time().toPython()
            end_datetime = datetime.combine(date, end_time)
            
            # 如果结束时间小于开始时间，假设跨日
            if end_datetime <= start_datetime:
                end_datetime += timedelta(days=1)
        
        return {
            'activity_id': activity_id,
            'start_time': start_datetime,
            'end_time': end_datetime,
            'note': note
        }

    def set_edit_mode(self, log_id, activity_id):
        """设置编辑模式"""
        print(f"DEBUG: set_edit_mode called. log_id={log_id}, activity_id={activity_id}")
        self.setWindowTitle('编辑时间记录')
        self.ok_button.setText('保存修改')
        # self.activity_combo.setEnabled(False) # 修改活动

        # 选中对应活动
        index = self.activity_combo.findData(activity_id)
        print(f"DEBUG: Found activity at index {index}")
        if index >= 0:
            self.activity_combo.setCurrentIndex(index)

        # 注意：这里只设置了 UI 状态，实际的时间/备注填充在调用处完成，
        # 或者后续可以扩展此方法接收 start_time, note 等参数直接填充。
