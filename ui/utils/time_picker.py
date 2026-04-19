#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间选择器组件
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QWidget, QTabWidget
)
from PySide6.QtCore import Qt, QTime
from ui.styles.app_style import theme_manager


class TimePickerDialog(QDialog):
    """自定义时间选择器对话框"""
    
    def __init__(self, initial_time=None, parent=None):
        super().__init__(parent)
        self.selected_time = initial_time or QTime.currentTime()
        self.setWindowTitle("选择时间")
        self.setModal(True)
        # self.setFixedSize(360, 400)
        self.setup_ui()
        self.update_styles()
        
        # 监听主题变更
        theme_manager.theme_changed.connect(lambda t: self.update_styles())
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        
        # 顶部时间显示
        self.header = QWidget()
        self.header.setFixedHeight(50)
        h_layout = QVBoxLayout(self.header)
        h_layout.setContentsMargins(10, 8, 10, 8)
        
        self.time_lbl = QLabel(self.selected_time.toString("HH:mm"))
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_lbl.setStyleSheet("font-size: 24px; font-weight: bold; font-family: Consolas;")
        h_layout.addWidget(self.time_lbl)
        
        layout.addWidget(self.header)
        
        # 构建小时和分钟网格
        self.hour_btns = []
        self.min_btns = []
        
        self.hour_grid = QGridLayout()
        self.hour_grid.setSpacing(3)
        for h in range(24):
            btn = QPushButton(f"{h:02d}")
            btn.setFixedSize(36, 36) # Increased size
            btn.setCheckable(True)
            if h == self.selected_time.hour():
                btn.setChecked(True)
            btn.clicked.connect(lambda c, val=h: self.set_hour(val))
            self.hour_grid.addWidget(btn, h // 4, h % 4)
            self.hour_btns.append(btn)
        
        self.min_grid = QGridLayout()
        self.min_grid.setSpacing(6) # Increased spacing
        for i, m in enumerate(range(0, 60, 5)):
            btn = QPushButton(f"{m:02d}")
            btn.setFixedSize(36, 36) # Increased size
            btn.setCheckable(True)
            if self._match_minute(m, self.selected_time.minute()):
                btn.setChecked(True)
            btn.clicked.connect(lambda c, val=m: self.set_minute(val))
            self.min_grid.addWidget(btn, i // 4, i % 4)
            self.min_btns.append(btn)

        # 使用 Tabs
        self.tabs = QTabWidget()
        
        hour_page = QWidget()
        hour_page_layout = QVBoxLayout(hour_page)
        hour_page_layout.setContentsMargins(4, 4, 4, 4)
        hour_page_layout.addLayout(self.hour_grid)
        hour_page_layout.addStretch()
        self.tabs.addTab(hour_page, "小时")
        
        min_page = QWidget()
        min_page_layout = QVBoxLayout(min_page)
        min_page_layout.setContentsMargins(4, 4, 4, 4)
        min_page_layout.addLayout(self.min_grid)
        min_page_layout.addStretch()
        self.tabs.addTab(min_page, "分钟")
        
        layout.addWidget(self.tabs)
        
        # 底部按钮
        btns = QHBoxLayout()
        btns.setContentsMargins(0, 4, 0, 0)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setFixedHeight(28)
        self.ok_btn.clicked.connect(self.accept)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(self.ok_btn)
        layout.addLayout(btns)

    def update_styles(self):
        """更新弹窗样式"""
        t = theme_manager.current_tokens
        
        # 对话框整体
        self.setStyleSheet(f"""
            QDialog {{ background-color: {t['bg_main']}; color: {t['text_primary']}; }}
            QWidget {{ background-color: {t['bg_main']}; color: {t['text_primary']}; }}
            QTabWidget::pane {{ border: 1px solid {t['border']}; border-radius: 4px; background-color: {t['bg_card']}; }}
            QTabBar::tab {{
                background: {t['bg_card']};
                color: {t['text_secondary']};
                padding: 8px 12px;
                border: 1px solid {t['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {t['bg_main']};
                color: {t['primary']};
                border-top: 2px solid {t['primary']};
                font-weight: bold;
            }}
            QPushButton {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                background-color: {t['bg_input']};
                color: {t['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {t['bg_hover']};
                border-color: {t['primary']};
            }}
        """)
        
        # 头部区域
        self.header.setStyleSheet(f"background-color: {t['primary']}; color: {t['text_inverse']}; border-radius: 6px;")
        self.time_lbl.setStyleSheet("font-size: 24px; font-weight: bold; font-family: Consolas; background: transparent; color: white;")
        
        # 确定按钮
        self.ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['primary']}; 
                color: {t['text_inverse']}; 
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {t['primary_hover']}; 
            }}
        """)
        
        # 更新所有网格按钮样式
        # 更新所有网格按钮样式
        # 增加尺寸，确保文字可见
        btn_size = "36px" 
        
        btn_style = f"""
            QPushButton {{ 
                min-width: {btn_size};
                min-height: {btn_size};
                border: 1px solid {t['border']}; 
                border-radius: 6px; 
                font-size: 14px;
                font-weight: bold;
                background-color: transparent; 
                color: {t['text_primary']};
            }}
            QPushButton:checked {{ 
                background-color: {t['primary']}; 
                color: {t['text_inverse']}; 
                border: 1px solid {t['primary']}; 
            }}
            QPushButton:hover {{ 
                background-color: {t['bg_hover']}; 
                border-color: {t['primary']};
            }}
        """
        for btn in self.hour_btns + self.min_btns:
            btn.setFixedSize(36, 36) # Explicitly resize python object too
            btn.setStyleSheet(btn_style)

    def set_hour(self, h):
        self.selected_time = QTime(h, self.selected_time.minute())
        self.time_lbl.setText(self.selected_time.toString("HH:mm"))
        self._update_hour_checks()

    def set_minute(self, m):
        self.selected_time = QTime(self.selected_time.hour(), m)
        self.time_lbl.setText(self.selected_time.toString("HH:mm"))
        self._update_min_checks()
        
    def _update_hour_checks(self):
        for i, btn in enumerate(self.hour_btns):
            btn.setChecked(i == self.selected_time.hour())
            
    def _update_min_checks(self):
        for i, btn in enumerate(self.min_btns):
            m = i * 5
            btn.setChecked(self._match_minute(m, self.selected_time.minute()))

    def _match_minute(self, val, target):
        """模糊匹配分钟 (0-4 -> 0, 5-9 -> 5, etc.)"""
        return abs(val - target) < 3
