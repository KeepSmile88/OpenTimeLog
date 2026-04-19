#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动备注对话框 (v4.0)
用于开始活动前输入备注
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt

class ActivityNoteDialog(QDialog):
    """精致的活动备注输入对话框"""
    
    def __init__(self, title="开始活动", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标签
        label = QLabel("备注 (可选):")
        label.setStyleSheet("font-weight: bold; color: #606266;")
        layout.addWidget(label)
        
        # 输入框
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("输入活动详情...")
        self.note_input.setMinimumHeight(32)
        layout.addWidget(self.note_input)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
        
    def get_note(self):
        return self.note_input.text().strip()
