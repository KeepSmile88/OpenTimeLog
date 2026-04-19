#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGridLayout, QScrollArea, QWidget, QColorDialog,
    QSpinBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from functools import partial


class AddActivityDialog(QDialog):
    """添加活动对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('添加新活动')
        self.setMinimumSize(520, 600)  # 改用最小尺寸以支持缩放
        self.resize(580, 680)
        self.selected_color = '#FF6B6B'
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # 1. 活动名称
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel('<b>活动名称:</b>'))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: 深度工作、健身、阅读...")
        self.name_edit.setMinimumHeight(35)
        name_layout.addWidget(self.name_edit)
        main_layout.addLayout(name_layout)
        
        # 2. 图标选择 (增强版)
        main_layout.addWidget(QLabel('<b>选择图标:</b>'))
        
        # 已选图标预览
        preview_layout = QHBoxLayout()
        self.icon_preview = QLabel('⭕')
        self.icon_preview.setStyleSheet("font-size: 24px; background: #eee; border-radius: 5px; padding: 5px;")
        self.icon_preview.setFixedSize(50, 50)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        
        self.icon_label = QLabel('当前选择')
        self.icon_label.setStyleSheet("color: #666;")
        
        preview_layout.addWidget(self.icon_preview)
        preview_layout.addWidget(self.icon_label)
        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)

        # 图标网格滚动区
        scroll = QScrollArea()
        scroll.setMinimumHeight(180)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #ddd; border-radius: 4px; }")
        
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(5)
        
        # 极大规模图标库
        emoji_categories = [
            # 常见/基础 (第一排常用)
            '💼', '📚', '📝', '💻', '📊', '📎', '📮', '💡', '🎓', '🛠️',
            # 工作/学习/办公
            '🖱️', '⌨️', '🖨️', '📂', '📁', '📅', '📆', '📇', '📈', '📉', '📋', '📌', '📎', '📏', '📐', '✂️', '🖋️', '✒️', '🖊️', '🖌️', '🖍️', '🔍', '🔬', '🔭', '🧪', '⚖️',
            # 健身/健康/运动
            '🏃', '🚶', '🚴', '🏊', '🏋️', '🧘', '⚽', '🏀', '🏐', '🏈', '⚾', '🎾', '🥅', '🏸', '🏒', '🏓', '⛳', '🥊', '🥋', '⛷️', '⛸️', '🏇', '🏄', '🚣', '🧗', '🚵', '💊', '💉', '🦷', '🏥', '🚑',
            # 饮食/美食
            '🍽️', '☕', '🥤', '🍺', '🍷', '🍶', '🍵', '🥛', '🍼', '🍯', '🥯', '🍞', '🥐', '🥨', '🥞', '🥓', '🍖', '🍗', '🥩', '🍔', '🍕', '🍟', '🥙', '🍣', '🍱', '🍜', '🍲', '🍛', '🥚', '🍢', '🥪', '🥘', '🥗', '🍿', '🧊', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🍑', '🥝', '🍅', '🥥', '🥦', '🌽', '🥕', '🥔', '🥜', '🍄',
            # 娱乐/爱好/游戏
            '🎮', '🕹️', '🎲', '🧩', '🎭', '🎨', '🎵', '🎶', '🎼', '🎹', '🎸', '🎻', '🎻', '🥁', '🎤', '🎧', '🎬', '🎞️', '📷', '📸', '📺', '📻', '🏮', '🎫', '🎟️', '🧶', '🧵', '🪡',
            # 生活/居家/服饰
            '🏠', '🏠', '🛌', '🛋️', '🚿', '🛀', '🧼', '🧹', '🧺', '🪴', '🔥', '💡', '🔦', '🔑', '🚪', '🪑', '👗', '👕', '👖', '👔', '👠', '👟', '👢', '👜', '🎒', '🕶️', '💍', '💄', '👒',
            # 自然/天气/植物
            '☀️', '🌙', '☁️', '⛈️', '❄️', '🌈', '🌊', '🍁', '🍂', '🍀', '🌲', '🌳', '🌴', '🌵', '🌾', '🌱', '🌿', '🍃', '🌹', '🌻', '🌼', '🌷', '🌞', '🌍', '🪐',
            # 动物/宠物
            '🐶', '🐱', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🐧', '🐦', '🐥', '🦆', '🦅', '🦉', '🦇', '🐺', '🐴', '🦄', '🐝', '🐜', '🦋', '🐌', '🐞', '🐢', '🐍', '🐙', '🦑', '🦐', '🦀', '🐠', '🐟', '🐬', '🐋', '🦈',
            # 建筑/旅游/交通
            '🚗', '🚲', '🛵', '🏍️', '🏎️', '🚄', '🚇', '🚌', '🚌', '🚐', '🚚', '🚜', '✈️', '🚀', '⛵', '🚢', '🗺️', '🗿', '⛺', '🎢', '🎡', '🏰', '🏨', '🏦', '🏪', '🏫', '🏢', '🏛️', '⛪',
            # 表情/情感
            '😀', '🤣', '😆', '😊', '😋', '😎', '😍', '😘', '🙂', '🤗', '🤩', '🤔', '🤨', '😐', '😑', '😶', '🙄', '😏', '😣', '😥', '😮', '🤐', '😪', '😫', '😴', '😌', '😛', '🤤', '😒', '😓', '😔', '😕', '🙃', '🤑', '😲', '☹️', '😤', '😢', '😭', '😦', '🤯', '😬', '😰', '😱', '🥵', '🥶', '😳', '🤪', '😵', '😡', '😷', '🤕', '🤮', '😇', '🤠', '🥳', '🤓', '🧐', '👻', '👽', '👾', '🤖',
            # 工具/符号 (末尾重申基础)
            '⭕', '✅', '❌', '➕', '➖', '❓', '❗', '💯', '💰', '💎', '💳', '🏧', '🔔', '⏰', '⌛', '⏳', '🔑', '🎁', '🛒', '📦'
        ]
        
        cols = 6  # 改为6列以增大按钮尺寸
        for i, icon in enumerate(emoji_categories):
            btn = QPushButton(icon)
            btn.setFixedSize(50, 50)  # 增大图标按钮尺寸
            btn.setStyleSheet("""
                QPushButton { 
                    font-size: 22px;  /* 增大字号 */
                    background: transparent; 
                    border: 1px solid transparent; 
                    border-radius: 5px; 
                }
                QPushButton:hover { background: #e0e0e0; border: 1px solid #ccc; }
            """)
            btn.clicked.connect(partial(self.set_icon, icon))
            grid.addWidget(btn, i // cols, i % cols)
            
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        # 3. 颜色选择
        main_layout.addWidget(QLabel('<b>背景颜色:</b>'))
        
        # 使用网格布局放置颜色按钮
        color_container = QWidget()
        color_grid = QGridLayout(color_container)
        color_grid.setSpacing(10)
        color_grid.setContentsMargins(0, 5, 0, 5)
        
        # 预设色块 - 使用网格排列，每行5个
        preset_colors = [
            '#FF6B6B', '#FF9F43', '#FECA57', '#48DBFB', '#1DD1A1',
            '#54A0FF', '#5F27CD', '#FF9FF3', '#A29BFE', '#6c757d'
        ]
        for i, color in enumerate(preset_colors):
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f'''
                QPushButton {{
                    background-color: {color}; 
                    border: 3px solid transparent; 
                    border-radius: 20px;
                }}
                QPushButton:hover {{
                    border: 3px solid #333;
                }}
            ''')
            btn.clicked.connect(partial(self.update_color, color))
            color_grid.addWidget(btn, i // 5, i % 5)
        
        main_layout.addWidget(color_container)
        
        # 自定义颜色按钮 - 单独一行
        self.custom_color_btn = QPushButton('🎨 自定义颜色')
        self.custom_color_btn.setFixedHeight(36)
        self.custom_color_btn.setStyleSheet('''
            QPushButton {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #e9ecef;
                border-color: #adb5bd;
            }
        ''')
        self.custom_color_btn.clicked.connect(self.pick_custom_color)
        main_layout.addWidget(self.custom_color_btn)
        
        # 4. 目标时间
        goal_layout = QHBoxLayout()
        goal_layout.addWidget(QLabel('<b>每日目标 (分钟):</b>'))
        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(0, 1440)
        self.goal_spin.setValue(60)
        self.goal_spin.setSuffix(' min')
        self.goal_spin.setMinimumHeight(35)
        goal_layout.addWidget(self.goal_spin)
        main_layout.addLayout(goal_layout)
        
        main_layout.addStretch()
        
        # 5. 操作按钮
        btn_box = QHBoxLayout()
        self.ok_btn = QPushButton('创建活动')
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setStyleSheet("background: #28a745; color: white; font-weight: bold; border-radius: 5px;")
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_box.addWidget(self.ok_btn, 2)
        btn_box.addWidget(self.cancel_btn, 1)
        main_layout.addLayout(btn_box)
        
        self.setLayout(main_layout)
    
    def set_icon(self, icon):
        self.icon_preview.setText(icon)
        
    def update_color(self, color):
        self.selected_color = color
        self.icon_preview.setStyleSheet(f"font-size: 24px; background: {color}33; border-radius: 5px; padding: 5px; border: 2px solid {color};")
        
    def pick_custom_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color))
        if color.isValid():
            self.update_color(color.name())
    
    def get_activity_data(self) -> dict:
        return {
            'name': self.name_edit.text().strip(),
            'icon': self.icon_preview.text(),
            'color': self.selected_color,
            'goal_minutes': self.goal_spin.value()
        }

    def set_data(self, activity):
        """设置活动数据 (用于编辑)"""
        if not activity: return

        # 适应 Activity 对象或元组/字典
        if hasattr(activity, 'name'):
            name = activity.name
            icon = activity.icon
            color = activity.color
            goal = activity.goal_minutes
        else:
            # 假设是元组/列表 (id, name, color, icon, goal...)
            # 注意元组索引要对应 ActivityDao.get_all 的查询结果
            # SELECT id, name, color, icon, goal_minutes...
            name = activity[1]
            color = activity[2]
            icon = activity[3]
            goal = activity[4] if len(activity) > 4 else 0

        self.setWindowTitle('编辑活动')
        self.ok_btn.setText('保存修改')

        self.name_edit.setText(name)
        self.set_icon(icon)
        self.update_color(color)
        self.goal_spin.setValue(goal)

