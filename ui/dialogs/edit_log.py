#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编辑时间记录对话框
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDateEdit, QTimeEdit, QTextEdit, QPushButton, QMessageBox,
    QComboBox
)
from PySide6.QtCore import QDate, QTime


class EditLogDialog(QDialog):
    """编辑时间记录对话框"""
    
    def __init__(self, db_manager, log_data, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.log_id = log_data[0]
        self.log_data = log_data
        self.original_activity_id = None
        self.setup_ui(log_data)
    
    def setup_ui(self, log_data):
        """设置UI"""
        self.setWindowTitle('编辑时间记录')
        self.setMinimumWidth(320)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # --- 活动选择 ---
        layout.addWidget(QLabel('活动类型:'))
        self.activity_combo = QComboBox()
        self.activity_combo.setMaximumHeight(28)
        self.activities = self.db_manager.get_activities()
        
        current_activity_name = log_data[1]
        current_index = 0
        
        for idx, act in enumerate(self.activities):
            self.activity_combo.addItem(f"{act[3]} {act[1]}", act[0])
            if act[1] == current_activity_name:
                current_index = idx
                self.original_activity_id = act[0]

        self.activity_combo.setCurrentIndex(current_index)
        layout.addWidget(self.activity_combo)
        
        # 解析时间
        start_dt = datetime.fromisoformat(log_data[4])  # start_time
        
        # 开始时间
        layout.addWidget(QLabel('开始时间:'))
        start_layout = QHBoxLayout()
        
        self.start_date_edit = QDateEdit(QDate(start_dt.year, start_dt.month, start_dt.day))
        self.start_date_edit.setCalendarPopup(True)
        self.start_time_edit = QTimeEdit(QTime(start_dt.hour, start_dt.minute, start_dt.second))
        
        start_layout.addWidget(self.start_date_edit)
        start_layout.addWidget(self.start_time_edit)
        layout.addLayout(start_layout)
        
        # 结束时间
        if log_data[5]:  # end_time exists
            end_dt = datetime.fromisoformat(log_data[5])
            
            layout.addWidget(QLabel('结束时间:'))
            end_layout = QHBoxLayout()
            
            self.end_date_edit = QDateEdit(QDate(end_dt.year, end_dt.month, end_dt.day))
            self.end_date_edit.setCalendarPopup(True)
            self.end_time_edit = QTimeEdit(QTime(end_dt.hour, end_dt.minute, end_dt.second))
            
            end_layout.addWidget(self.end_date_edit)
            end_layout.addWidget(self.end_time_edit)
            layout.addLayout(end_layout)
        else:
            self.end_date_edit = None
            self.end_time_edit = None
        
        # 备注
        layout.addWidget(QLabel('备注:'))
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(45)
        self.note_edit.setPlainText(log_data[7] or '')
        layout.addWidget(self.note_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)
        
        self.save_button = QPushButton('保存')
        self.delete_button = QPushButton('删除')
        self.cancel_button = QPushButton('取消')
        
        for btn in [self.save_button, self.delete_button, self.cancel_button]:
            btn.setFixedHeight(28)
        
        self.save_button.clicked.connect(self.save_changes)
        self.delete_button.clicked.connect(self.delete_log)
        self.cancel_button.clicked.connect(self.reject)
        
        self.delete_button.setStyleSheet('QPushButton { background-color: #dc3545; color: white; }')
        self.save_button.setStyleSheet('QPushButton { background-color: #28a745; color: white; font-weight: bold; }')
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_changes(self):
        """保存更改"""
        # 1. 更新活动类型
        new_activity_id = self.activity_combo.currentData()
        if new_activity_id != self.original_activity_id:
            self.db_manager.update_log_activity(self.log_id, new_activity_id)

        # 2. 更新时间
        start_date = self.start_date_edit.date().toPython()
        start_time = self.start_time_edit.time().toPython()
        start_datetime = datetime.combine(start_date, start_time)
        
        end_datetime = None
        if self.end_date_edit and self.end_time_edit:
            end_date = self.end_date_edit.date().toPython()
            end_time = self.end_time_edit.time().toPython()
            end_datetime = datetime.combine(end_date, end_time)
        
        self.db_manager.update_log_times(self.log_id, start_datetime, end_datetime)
        
        # 3. 更新备注
        self.db_manager.update_log_note(self.log_id, self.note_edit.toPlainText().strip())
        
        self.accept()
    
    def delete_log(self):
        """删除记录"""
        reply = QMessageBox.question(
            self, '确认删除', '确定要删除这条记录吗？',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db_manager.delete_log(self.log_id)
            self.accept()
