#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面悬浮小部件 (v3.0)
实时显示当前运行活动，支持暂停/继续/显示主窗，以及番茄钟专注模式
"""

from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QPoint, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from ui.styles.app_style import theme_manager

class FloatingTimerWidget(QWidget):
    """置顶显示、半透明、支持交互的桌面悬浮窗"""
    
    # 信号
    request_show_main = Signal()
    request_toggle_status = Signal(int) # log_id
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_log_id = None
        self.is_running = False
        
        # 番茄钟状态：{log_id: True/False}
        self.pomodoro_modes = {}
        
        # 窗口属性：置顶、无边框、工具窗口
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.drag_position = QPoint()
        self.setup_ui()
        
        # 定时更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_content)
        self.timer.start(1000)
        
        # 监听主题变化
        theme_manager.theme_changed.connect(lambda t: self.update_content())

    def setup_ui(self):
        self.container = QWidget(self)
        self.container.setObjectName("floatContainer")
        
        # 主水平布局：信息区 | 按钮区
        main_h_layout = QHBoxLayout(self.container)
        main_h_layout.setContentsMargins(12, 8, 12, 8)
        main_h_layout.setSpacing(10)
        
        # 1. 信息区 (垂直)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.title_lbl = QLabel("无运行项目")
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        self.time_lbl = QLabel("--:--:--")
        self.time_lbl.setStyleSheet("font-size: 16px; font-family: 'Consolas';")
        
        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.time_lbl)
        main_h_layout.addLayout(info_layout)
        
        # 2. 按钮区 (垂直)
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)
        
        self.toggle_btn = QPushButton("⏸️")
        self.toggle_btn.setFixedSize(36, 36)
        self.toggle_btn.setStyleSheet("border-radius: 18px; padding: 0px")
        self.toggle_btn.setToolTip("暂停/继续")
        self.toggle_btn.clicked.connect(self.on_toggle_clicked)
        
        self.expand_btn = QPushButton("🏠")
        self.expand_btn.setFixedSize(36, 36)
        self.expand_btn.setStyleSheet("border-radius: 18px; padding: 0px")
        self.expand_btn.setToolTip("打开主界面")
        self.expand_btn.clicked.connect(self._on_expand_clicked)
        
        btn_layout.addWidget(self.toggle_btn)
        btn_layout.addWidget(self.expand_btn)
        main_h_layout.addLayout(btn_layout)
        
        # 容器布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.container)
        
        # 增加一点宽度以防止内容截断
        self.setFixedSize(220, 90)
        self.update_content() # 初始化样式
    
    def update_container_style(self, is_pomodoro: bool):
        """更新容器样式：普通模式或番茄钟模式"""
        t = theme_manager.current_tokens
        
        if is_pomodoro:
            # 番茄钟模式 - 红色调背景 (Hardcoded for focus, or use Danger/Warning tokens?)
            # 番茄钟通常是红色，保持特色比较好，或者使用 theme['danger']
            danger_color = t.get('danger', '#dc3545')
            # 转换为半透明 RGB
            c = QColor(danger_color)
            bg_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 220)"
            border_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 150)"
            
            self.container.setStyleSheet(f"""
                QWidget#floatContainer {{
                    background-color: {bg_rgba};
                    border-radius: 12px;
                    border: 2px solid {border_rgba};
                }}
                QLabel {{ color: {t['text_inverse']}; }}
                QPushButton {{
                    background: transparent;
                    border-radius: 4px;
                    font-size: 14px;
                    color: {t['text_inverse']};
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 40);
                }}
            """)
        else:
            # 普通模式 - 使用主题 bg_input 或 bg_card，但需要半透明
            # 为了保证悬浮窗的辨识度，默认使用深色半透明背景往往比较好。
            # 但既然我们有浅色/深色主题，应该跟随。
            
            # 使用主题背景色，添加透明度
            bg_color = QColor(t['bg_card']) 
            # 如果是浅色主题，bg_card是白的，半透明可能是白的半透明
            # 如果是深色主题，bg_card是深灰，半透明是深灰
            
            # 稍微加深一点背景以增加对比度（针对桌面壁纸）
            if theme_manager.current_theme_name in ['default', 'pink', 'eyecare']:
                 # 浅色模式下，稍微深一点的底色或者高不透明度
                 bg_rgba = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 240)"
                 border_color = t['border']
                 text_color = t['text_primary']
                 btn_text_color = t['text_secondary']
            else:
                 # 深色模式
                 bg_rgba = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 230)"
                 border_color = "rgba(255, 255, 255, 30)"
                 text_color = t['text_primary']
                 btn_text_color = t['text_secondary']

            self.container.setStyleSheet(f"""
                QWidget#floatContainer {{
                    background-color: {bg_rgba};
                    border-radius: 12px;
                    border: 1px solid {border_color};
                }}
                QLabel {{ color: {text_color}; }}
                QPushButton {{
                    background: transparent;
                    border-radius: 4px;
                    font-size: 14px;
                    color: {text_color};
                }}
                QPushButton:hover {{
                    background: {t['bg_hover']};
                }}
                QPushButton:disabled {{
                    color: {t['text_light']};
                }}
            """)
    
    def set_pomodoro_mode(self, log_id: int, enabled: bool):
        """设置指定活动的番茄钟模式状态（由主窗口调用）"""
        self.pomodoro_modes[log_id] = enabled
        # 如果当前显示的就是这个活动，立即刷新
        if self.current_log_id == log_id:
            self.update_content()

    def on_toggle_clicked(self):
        if self.current_log_id:
            self.request_toggle_status.emit(self.current_log_id)

    def update_content(self):
        t = theme_manager.current_tokens
        running = self.db_manager.get_running_activities()
        
        if not running:
            self.current_log_id = None
            self.title_lbl.setText("☕ 休息中")
            self.title_lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 12px;")
            self.time_lbl.setText("--:--:--")
            self.time_lbl.setStyleSheet(f"color: {t['text_light']}; font-size: 16px; font-family: 'Consolas';")
            self.toggle_btn.setEnabled(False)
            self.update_container_style(False)
            return

        self.toggle_btn.setEnabled(True)
        # 仅显示最近的一个
        log_id, name, color, icon, start, note, status = running[0]
        self.current_log_id = log_id
        self.is_running = (status == 'running')
        
        elapsed = self.db_manager.get_elapsed_running(log_id)
        
        # 检查是否为番茄钟模式
        is_pomodoro = self.pomodoro_modes.get(log_id, False)
        self.update_container_style(is_pomodoro)
        
        if is_pomodoro:
            # 番茄钟模式 - 显示倒计时
            cycle_sec = 25 * 60  # 25分钟一个周期
            remaining = cycle_sec - (elapsed % cycle_sec)
            m, s = remaining // 60, remaining % 60
            
            self.title_lbl.setText(f"🍅 {name}")
            # 番茄钟文字强制反白
            self.title_lbl.setStyleSheet(f"color: {t['text_inverse']}; font-weight: bold; font-size: 13px;")
            
            if self.is_running:
                self.time_lbl.setText(f"🍅 {m:02d}:{s:02d}")
                self.time_lbl.setStyleSheet(f"font-size: 18px; font-family: 'Consolas'; color: {t['text_inverse']}; font-weight: bold;")
                self.toggle_btn.setText("⏸️")
            else:
                self.time_lbl.setText(f"⏸ {m:02d}:{s:02d}")
                self.time_lbl.setStyleSheet(f"font-size: 18px; font-family: 'Consolas'; color: #FFC107; font-weight: bold;")
                self.toggle_btn.setText("▶️")
        else:
            # 普通模式 - 显示正计时
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            
            self.title_lbl.setText(f"{icon} {name}")
            self.title_lbl.setStyleSheet(f"color: {t['text_primary']}; font-weight: bold; font-size: 13px;")
            
            if self.is_running:
                self.time_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")
                self.time_lbl.setStyleSheet(f"font-size: 16px; font-family: 'Consolas'; color: {t['primary']};")
                self.toggle_btn.setText("⏸️")
            else:
                self.time_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")
                self.time_lbl.setStyleSheet(f"font-size: 16px; font-family: 'Consolas'; color: {t['warning']};")
                self.toggle_btn.setText("▶️")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        try:
            if event.buttons() == Qt.MouseButton.LeftButton:
                self.move(event.globalPos() - self.drag_position)
                event.accept()
        except:
            pass

    def _on_expand_clicked(self):
        """打开主界面按钮点击处理"""
        self.request_show_main.emit()
    
    def closeEvent(self, event):
        """关闭时停止定时器"""
        if hasattr(self, 'timer') and self.timer:
            try:
                self.timer.stop()
            except RuntimeError:
                pass
        super().closeEvent(event)
