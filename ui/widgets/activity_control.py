# -*- coding: utf-8 -*-
"""
活动控制组件
用于显示和控制单个活动的开始
"""

import os
import sys

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMenu
from PySide6.QtCore import Signal, Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.helpers import darken_color


class ActivityControlWidget(QWidget):
    """活动控制组件"""
    
    # 信号：开始活动
    start_clicked = Signal(int)
    # 信号：手动添加记录
    manual_clicked = Signal(int)
    # 信号：请求删除 (id)
    delete_clicked = Signal(int)
    # 信号：请求编辑 (id)
    edit_clicked = Signal(int)
    
    def __init__(self, activity_data, parent=None):
        """初始化组件
        
        Args:
            activity_data: 活动数据元组 (id, name, color, icon, goal_minutes, ...)
            parent: 父组件
        """
        super().__init__(parent)

        # 保存原始活动数据（用于编辑对话框）
        self.activity_data = activity_data

        # 兼容 Activity 对象和元组
        if hasattr(activity_data, 'id'):
            self.activity_id = activity_data.id
            self.name = activity_data.name
            self.color = activity_data.color
            self.icon = activity_data.icon
            self.goal_minutes = activity_data.goal_minutes
        else:
            self.activity_id = activity_data[0]
            self.name = activity_data[1]
            self.color = activity_data[2]
            self.icon = activity_data[3] if len(activity_data) > 3 else '⭕'
            self.goal_minutes = activity_data[4] if len(activity_data) > 4 else 0

        try:
            self.setup_ui()
        except Exception as e:
            print("发生错误：\t", e)
            import traceback
            traceback.print_exc()
            raise
    
    def setup_ui(self):
        """设置UI - 简化版：主按钮 + 右侧手动图标"""
        layout = QHBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # 主按钮 - 点击即开始计时
        self.main_button = QPushButton(self)
        self.main_button.setText(f"{self.icon} {self.name}")
        self.main_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {self.color};
                color: white;
                border: none;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {darken_color(self.color)};
            }}
            QPushButton:pressed {{
                padding-left: 13px;
                padding-top: 11px;
            }}
        ''')
        self.main_button.setCursor(Qt.PointingHandCursor)
        self.main_button.clicked.connect(self._on_start_clicked)
        # 启用右键菜单（编辑/删除活动）
        self.main_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.main_button.customContextMenuRequested.connect(self.show_context_menu)
        
        # 手动记录小按钮 - 右侧图标
        self.manual_add_btn = QPushButton("📝")
        self.manual_add_btn.setFixedSize(32, 32)
        self.manual_add_btn.setToolTip("手动添加记录")
        self.manual_add_btn.setCursor(Qt.PointingHandCursor)
        self.manual_add_btn.setStyleSheet(f'''
            QPushButton {{
                background-color: {self.color}30;
                color: {self.color};
                border: 1px solid {self.color}50;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.color}50;
                border-color: {self.color};
            }}
        ''')
        self.manual_add_btn.clicked.connect(self._on_manual_clicked)
        
        layout.addWidget(self.main_button, 1)
        layout.addWidget(self.manual_add_btn)
        
        self.setLayout(layout)
    
    def _on_start_clicked(self):
        """开始按钮点击处理"""
        self.start_clicked.emit(self.activity_id)
    
    def _on_manual_clicked(self):
        """手动记录按钮点击处理"""
        self.manual_clicked.emit(self.activity_id)

    def show_context_menu(self, pos):
        print(f"DEBUG: Activity Control Context Menu requested for {self.activity_id}")
        menu = QMenu(self)

        edit_action = menu.addAction("✏️ 编辑活动")
        delete_action = menu.addAction("🗑️ 删除活动")

        action = menu.exec(self.main_button.mapToGlobal(pos))

        if action == edit_action:
            print(f"DEBUG: Edit action clicked for {self.activity_id}")
            self.edit_clicked.emit(self.activity_id)
        elif action == delete_action:
            print(f"DEBUG: Delete action clicked for {self.activity_id}")
            self.delete_clicked.emit(self.activity_id)

