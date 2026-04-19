#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行中活动组件 (v3.0)
集成番茄工作法与增强交互
"""

import os

from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QIcon, QColor

from core.system_utils import SystemUtils
from ui.styles.app_style import theme_manager


class RunningActivityWidget(QWidget):
    """集成番茄钟功能的运行中活动组件"""
    
    pause_clicked = Signal(int)
    resume_clicked = Signal(int)
    stop_clicked = Signal(int)
    edit_clicked = Signal(int)
    pomodoro_toggled = Signal(int, bool)  # (log_id, enabled) 番茄钟状态变化信号
    
    def __init__(self, log_data, db_manager=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # 基础数据加载
        self.db_manager = db_manager
        self.update_from_data(log_data)
        
        # 番茄钟属性
        self.pomodoro_mode = False
        self.last_pomo_cycle = -1
        
        self.setup_ui()
        self.update_styles()
        
        # 监听主题变更
        self.theme_manager = theme_manager
        self._theme_conn = self.theme_manager.theme_changed.connect(self._on_theme_changed)
        
    def _on_theme_changed(self, tokens):
        """安全地处理主题变更信号"""
        try:
            self.update_styles()
        except RuntimeError:
            # Widget might be deleted C++ side but Python object still alive in this slot
            pass

    def update_from_data(self, log_data):
        self.log_id = log_data[0]
        self.name = log_data[1]
        self.color = log_data[2]
        self.icon = log_data[3]
        self.start_time = log_data[4]
        self.note = log_data[5] if len(log_data) > 5 else ''
        self.status = log_data[6] if len(log_data) > 6 else 'running'

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 10, 12, 10) # 紧凑内边距
        self.main_layout.setSpacing(6) # 紧凑间距
        
        # --- 顶部栏 ---
        header = QHBoxLayout()
        header.setSpacing(10)
        self.title_lbl = QLabel(f"{self.icon} {self.name}")
        
        self.status_lbl = QLabel()
        self.update_status_display()
        
        self.pomo_btn = QPushButton("🍅")
        self.pomo_btn.setStyleSheet("padding: 0px")
        self.pomo_btn.setFixedSize(32, 32)
        self.pomo_btn.setCheckable(True)
        # 样式在 update_styles 中设置
        self.pomo_btn.toggled.connect(self.on_pomo_toggled)
        
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.status_lbl)
        header.addWidget(self.pomo_btn)
        self.main_layout.addLayout(header)

        # --- 时间显示区 (紧凑) ---
        self.time_lbl = QLabel("--:--:--")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.time_lbl)
        
        # --- 备注区 ---
        self.note_lbl = QLabel(f"备注: {self.note}" if self.note else "")
        self.note_lbl.setVisible(bool(self.note))
        self.note_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.note_lbl)
        
        # --- 控制按钮区 ---
        btns = QHBoxLayout()
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.clicked.connect(self.handle_pause_resume)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        
        self.edit_btn = QPushButton("✏️ 编辑")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        
        self.control_btns = [self.pause_btn, self.stop_btn, self.edit_btn]
        for b in self.control_btns:
            b.setFixedHeight(28)
            btns.addWidget(b)
        
        self.main_layout.addLayout(btns)
        
        # 限制高度
        self.setFixedHeight(140)
        self.update_status_display()
        self.update_display()

    def update_styles(self):
        """更新样式"""
        t = theme_manager.current_tokens
        c = self.color if self.color else t['primary']
        
        # 优化深色模式下的显示效果
        is_dark = theme_manager.current_theme_name in ["dark", "male"] # "male" is legacy fallback
        
        if is_dark:
            # 深色模式：背景透明 (使用 Card 背景)，仅保留边框和左侧指示条，避免文字对比度问题
            bg_color = "transparent" # 或者 t['bg_card']
            # 为了区分，可以加一个微弱的 tint 或者仅仅靠边框
            # 方案 A: 纯边框风格
            style_sheet = f"""
                RunningActivityWidget {{
                    background-color: {t['bg_card']};
                    border: 1px solid {t['border']};
                    border-left: 4px solid {c};
                    border-radius: 8px;
                }}
            """
        else:
            # 浅色模式：保留淡色背景风格
            style_sheet = f"""
                RunningActivityWidget {{
                    background-color: {c}15; 
                    border: 2px solid {c};
                    border-radius: 8px;
                }}
            """
            
        self.setStyleSheet(style_sheet)
        
        # 2. 标题颜色: 使用 Activity 颜色，或者主题 Primary 颜色
        self.title_lbl.setStyleSheet(f"color: {t['text_primary']}; font-size: 14px; font-weight: bold;")
        
        # 3. 时间颜色
        self.time_lbl.setStyleSheet(f"font-size: 22px; font-weight: bold; font-family: 'Consolas'; color: {t['text_primary']}; margin: 2px 0;")
        
        # 4. 备注颜色
        self.note_lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px;")
        
        # 5. 番茄钟按钮
        self.pomo_btn.setStyleSheet(f"""
            QPushButton {{ border-radius: 12px; background: transparent; font-size: 14px; border: 1px solid transparent; padding:0px }}
            QPushButton:hover {{ background: {t['bg_hover']}; }}
            QPushButton:checked {{ background: {t['danger']}22; border: 1px solid {t['danger']}; }}
        """)
        
        # 6. 控制按钮
        # 统一使用 Theme 里的 Input/Btn 样式
        btn_style = f"""
            QPushButton {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t['bg_hover']};
                border-color: {t['primary']};
                color: {t['primary']};
            }}
        """
        for b in self.control_btns:
            b.setStyleSheet(btn_style)

    def on_pomo_toggled(self, checked):
        self.pomodoro_mode = checked
        self.pomodoro_toggled.emit(self.log_id, checked)
        
        if checked:
            SystemUtils.set_dnd_mode(True)
            QMessageBox.information(self, "进入专注模式", "您已进入深度专注模式！\n\n系统通知弹窗已暂时屏蔽，请开始您的专注时刻。🍅")
        else:
            SystemUtils.set_dnd_mode(False)
        self.update_display()

    def closeEvent(self, event):
        """组件销毁时确保恢复系统设置并断开信号"""
        try:
            if hasattr(self, '_theme_conn') and self._theme_conn:
                self.theme_manager.theme_changed.disconnect(self._theme_conn)
        except (RuntimeError, TypeError):
            pass

        if hasattr(self, 'pomodoro_mode') and self.pomodoro_mode:
            try:
                SystemUtils.set_dnd_mode(False)
            except Exception as e:
                print(f"恢复系统设置失败: {e}")
        super().closeEvent(event)
    
    def _on_stop_clicked(self):
        self.stop_clicked.emit(self.log_id)
    
    def _on_edit_clicked(self):
        self.edit_clicked.emit(self.log_id)

    def handle_pause_resume(self):
        if self.status == 'running':
            self.pause_clicked.emit(self.log_id)
        else:
            self.resume_clicked.emit(self.log_id)

    def update_status_display(self):
        t = theme_manager.current_tokens
        if self.status == 'running':
            self.status_lbl.setText("🟢 计时中")
            self.status_lbl.setStyleSheet(f"color: {t['success']}; font-weight: bold;")
            if hasattr(self, 'pause_btn'): self.pause_btn.setText("⏸️ 暂停")
        else:
            self.status_lbl.setText("⏸️ 已暂停")
            self.status_lbl.setStyleSheet(f"color: {t['warning']}; font-weight: bold;")
            if hasattr(self, 'pause_btn'): self.pause_btn.setText("▶️ 继续")

    def update_display(self):
        if not self.db_manager: return
        
        elapsed = self.db_manager.get_elapsed_running(self.log_id)
        t = theme_manager.current_tokens
        
        if self.pomodoro_mode:
            cycle_sec = 25 * 60
            current_cycle_index = elapsed // cycle_sec
            remaining = cycle_sec - (elapsed % cycle_sec)

            danger_color = t.get('danger', '#dc3545')
            # 转换为半透明 RGB
            c = QColor(danger_color)
            bg_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 220)"
            border_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, 150)"
            
            if current_cycle_index > self.last_pomo_cycle and self.last_pomo_cycle != -1:
                self.trigger_pomo_notification()
            self.last_pomo_cycle = current_cycle_index
            
            m, s = remaining // 60, remaining % 60
            self.time_lbl.setText(f"🍅 {m:02d}:{s:02d}")
            self.time_lbl.setStyleSheet(f"""
                font-weight: bold; font-size: 20px; font-family: 'Consolas';
            """)

            # self.pomo_btn.setStyleSheet(f"""
            #     background-color: {bg_rgba};
            #     padding: 0px;
            #     color: {t['danger']};
            #     border: 2px solid {border_rgba};
            # """)
        else:
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60

            bg_color = QColor(t['bg_card'])

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

            self.time_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")
            self.time_lbl.setStyleSheet(f"""
                
                font-size: 22px; 
                font-weight: bold; 
                font-family: 'Consolas'; color: {text_color}; margin: 2px 0;
            """)

            # self.pomo_btn.setStyleSheet(f"""
            #     padding: 0px;
            #     color: {t['danger']};
            # """)

    def trigger_pomo_notification(self):
        try:
            parent_window = self.window()
            if parent_window is not None and hasattr(parent_window, 'tray_icon'):
                parent_window.tray_icon.showMessage(
                    "番茄钟完成！", 
                    f"恭喜！您已完成一个【{self.name}】专注周期 (25min)。请休息一会儿。",
                    QIcon(), 3000
                )
        except RuntimeError as e:
            # Qt 对象可能已被删除
            print(f"发送番茄钟通知失败（对象可能已销毁）: {e}")
        except Exception as e:
            print(f"发送番茄钟通知失败: {e}")

    def update_data(self, log_data):
        self.update_from_data(log_data)
        # 更新标题标签（名称/图标可能已变更）
        if hasattr(self, 'title_lbl'):
            self.title_lbl.setText(f"{self.icon} {self.name}")
        # 重新应用样式（颜色可能变了）
        self.update_styles()
        self.update_status_display()
        if hasattr(self, 'note_lbl'):
             self.note_lbl.setText(f"备注: {self.note}" if self.note else "")
             self.note_lbl.setVisible(bool(self.note))
        self.update_display()
