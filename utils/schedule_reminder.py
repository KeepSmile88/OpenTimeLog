#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日程提醒服务
根据日程表在指定时间弹出提醒通知
"""

import os
from PySide6.QtCore import QObject, QTimer, Signal, QTime, QDate, Qt
from PySide6.QtWidgets import (
    QMessageBox, QSystemTrayIcon, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QIcon

from datetime import datetime, timedelta
from functools import partial


class ScheduleReminder(QObject):
    """日程提醒服务"""
    
    # 信号：当有日程需要提醒时发出
    reminder_triggered = Signal(str, str, str)  # start_time, end_time, content
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.reminded_schedules = set()  # 已提醒过的日程ID集合
        self.advance_minutes = 1  # 提前多少分钟提醒
        
        # 定时器：每30秒检查一次
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_schedules)
        self.check_timer.start(30 * 1000)  # 30秒
        
        # 每天零点重置已提醒列表
        self.reset_timer = QTimer(self)
        self.reset_timer.timeout.connect(self.reset_reminded_list)
        self._schedule_midnight_reset()
        
        # 延迟初始检查
        self._init_check_timer = QTimer(self)
        self._init_check_timer.setSingleShot(True)
        self._init_check_timer.timeout.connect(self.check_schedules)
        self._init_check_timer.start(1000)
    
    def _schedule_midnight_reset(self):
        """安排午夜重置"""
        now = datetime.now()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        ms_until_midnight = int((tomorrow - now).total_seconds() * 1000)
        self.reset_timer.start(ms_until_midnight)
    
    def reset_reminded_list(self):
        """重置已提醒列表（每天零点调用）"""
        self.reminded_schedules.clear()
        # 重新安排下次午夜重置
        self._schedule_midnight_reset()
    
    def check_schedules(self):
        """检查是否有需要提醒的日程"""
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            
            print(f"[提醒服务] 检查日程... 当前时间: {current_time}")
            
            # 获取今天的日程
            schedules = self.db_manager.get_schedules(today_str)
            print(f"[提醒服务] 今日日程数量: {len(schedules) if schedules else 0}")
            
            if not schedules:
                return
            
            for schedule in schedules:
                schedule_id = schedule[0]
                start_time = schedule[1]
                end_time = schedule[2]
                content = schedule[3]
                
                print(f"[提醒服务] 检查日程: ID={schedule_id}, 开始={start_time}, 内容={content}")
                
                # 检查是否已经提醒过
                if schedule_id in self.reminded_schedules:
                    print(f"[提醒服务] 日程 {schedule_id} 已提醒过，跳过")
                    continue
                
                # 检查是否到达提醒时间
                should_remind, reason = self._should_remind(current_time, start_time)
                print(f"[提醒服务] 是否提醒: {should_remind}, 原因: {reason}")
                
                if should_remind:
                    self.reminded_schedules.add(schedule_id)
                    print(f"[提醒服务] 触发提醒: {content}")
                    self.reminder_triggered.emit(start_time, end_time, content)
                    
        except Exception as e:
            print(f"[提醒服务] 检查日程出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _should_remind(self, current_time: str, start_time: str) -> tuple:
        """判断是否应该提醒，返回 (是否提醒, 原因)"""
        try:
            # 解析时间
            current = datetime.strptime(current_time, "%H:%M")
            start = datetime.strptime(start_time, "%H:%M")
            
            # 提前提醒的时间点
            remind_time = start - timedelta(minutes=self.advance_minutes)
            
            # 在提醒时间窗口内（提前N分钟到开始后2分钟）
            window_start = remind_time
            window_end = start + timedelta(minutes=2)
            
            in_window = window_start <= current <= window_end
            
            reason = f"当前:{current_time}, 开始:{start_time}, 提醒窗口:{window_start.strftime('%H:%M')}-{window_end.strftime('%H:%M')}"
            
            return in_window, reason
        except Exception as e:
            return False, f"解析错误: {e}"
    
    def set_advance_minutes(self, minutes: int):
        """设置提前提醒的分钟数"""
        self.advance_minutes = max(0, minutes)
    
    def stop(self):
        """停止提醒服务"""
        self.check_timer.stop()
        self.reset_timer.stop()
        # 停止初始检查定时器
        if hasattr(self, '_init_check_timer'):
            self._init_check_timer.stop()


class ReminderDialog(QDialog):
    """ 日程提醒对话框 """
    
    def __init__(self, start_time: str, end_time: str, content: str, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("📅 日程提醒")
        self.setFixedWidth(400)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部标题栏
        header_layout = QHBoxLayout()
        icon_label = QLabel("⏰")
        icon_label.setStyleSheet("font-size: 24px;")
        
        title_label = QLabel("活动开始提醒")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #E8EAED;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #3C4043;")
        layout.addWidget(line)
        
        # 内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)
        
        # 时间
        time_lbl = QLabel(f"时间：{start_time} - {end_time}")
        time_lbl.setStyleSheet("font-size: 14px; color: #9AA0A6;")
        
        # 活动
        activity_lbl = QLabel(content)
        activity_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #8AB4F8; margin: 5px 0;")
        activity_lbl.setWordWrap(True)
        
        # 提示语
        tip_lbl = QLabel(f"是时候开始 {content} 了！")
        tip_lbl.setStyleSheet("font-size: 13px; color: #9AA0A6; font-style: italic;")
        
        content_layout.addWidget(time_lbl)
        content_layout.addWidget(activity_lbl)
        content_layout.addWidget(tip_lbl)
        layout.addLayout(content_layout)
        
        layout.addSpacing(10)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_start = QPushButton("开始活动")
        self.btn_snooze = QPushButton("稍后提醒")
        self.btn_ignore = QPushButton("忽略")
        
        # 按钮样式
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #5C9EFF; }
        """)
        
        self.btn_snooze.setStyleSheet("""
            QPushButton {
                background-color: #3C4043;
                color: #E8EAED;
                border: 1px solid #5F6368;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #4B4F52; }
        """)
        
        self.btn_ignore.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9AA0A6;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { color: #E8EAED; background-color: #3C4043; }
        """)
        
        # 连接信号
        self.btn_start.clicked.connect(self.accept) # AcceptRole -> 1
        self.btn_snooze.clicked.connect(self.reject) # RejectRole -> 0 (We can use specific codes)
        self.btn_ignore.clicked.connect(lambda: self.done(2)) # DestructiveRole -> 2
        
        btn_layout.addWidget(self.btn_ignore)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_snooze)
        btn_layout.addWidget(self.btn_start)
        
        layout.addLayout(btn_layout)
        
        # 全局样式
        self.setStyleSheet("""
            QDialog {
                background-color: #202124;
                border: 1px solid #5F6368;
                border-radius: 8px;
            }
        """)
        
        # 窗口标志
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

    # 兼容 QMessageBox 的接口
    def exec(self):
        return super().exec()
        
    def clickedButton(self):
        # 这个方法是为了兼容 Manager 的调用
        # Manager logic: 
        # if clicked.text() == "开始活动" ...
        # Since we use done(code), exec() returns the code.
        # We need to adapt the manager or adapt this class to pretend to be QMessageBox
        # Or simpler: store the clicked button
        return self._clicked_btn

    def accept(self):
        self._clicked_btn = self.btn_start
        super().accept()
        
    def reject(self):
        self._clicked_btn = self.btn_snooze
        super().reject()
        
    def done(self, r):
        if r == 2:
            self._clicked_btn = self.btn_ignore
        super().done(r)

    _clicked_btn = None


class ScheduleReminderManager:
    """日程提醒管理器 - 集成到主窗口使用"""
    
    def __init__(self, db_manager, main_window=None):
        self.db_manager = db_manager
        self.main_window = main_window
        self.reminder = ScheduleReminder(db_manager)
        self.reminder.reminder_triggered.connect(self.show_reminder)
        self.snooze_schedules = {}  # 稍后提醒的日程
    
    def show_reminder(self, start_time: str, end_time: str, content: str):
        """显示提醒对话框"""
        try:
            print(f"[提醒服务] 显示提醒对话框: {content}")
            dialog = ReminderDialog(start_time, end_time, content, self.main_window)
            dialog.setWindowModality(Qt.NonModal)
            
            # 获取对话框按钮列表（用于调试）
            buttons = dialog.buttons()
            print(f"[提醒服务] 对话框按钮数量: {len(buttons)}")
            for i, btn in enumerate(buttons):
                print(f"[提醒服务] 按钮 {i}: {btn.text()}")
            
            # 播放系统提示音（如果可用）
            try:
                from PySide6.QtMultimedia import QSoundEffect
                # 可以添加自定义提示音
            except ImportError:
                pass
            
            dialog.exec()
            
            clicked = dialog.clickedButton()
            print(f"[提醒服务] 用户点击的按钮: {clicked.text() if clicked else 'None'}")
            
            if clicked:
                btn_text = clicked.text()
                if btn_text == "开始活动":
                    print(f"[提醒服务] 用户选择开始活动")
                    self.start_activity_from_schedule(content)
                elif btn_text == "稍后提醒":
                    print(f"[提醒服务] 用户选择稍后提醒")
                    self.snooze_reminder(start_time, end_time, content)
                else:
                    print(f"[提醒服务] 用户选择忽略")
            else:
                print(f"[提醒服务] 未检测到点击的按钮")
            
        except Exception as e:
            print(f"[提醒服务] 显示提醒时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def start_activity_from_schedule(self, content: str):
        """根据日程内容开始对应活动"""
        if not self.main_window:
            print("[提醒服务] 无法开始活动：主窗口未设置")
            return
        
        try:
            # 根据日程内容查找匹配的活动
            activities = self.db_manager.get_activities()
            print(f"[提醒服务] 获取到 {len(activities) if activities else 0} 个活动")
            
            if not activities:
                print("[提醒服务] 没有可用的活动")
                self._show_main_window()
                return
            
            matched_activity = None
            
            for activity in activities:
                # activity: (id, name, color, icon, ...)
                activity_name = activity[1]
                # 检查日程内容是否包含活动名称（或完全匹配）
                if activity_name.lower() == content.lower() or activity_name.lower() in content.lower():
                    matched_activity = activity
                    print(f"[提醒服务] 匹配到活动: {activity_name}")
                    break
            
            if matched_activity:
                activity_id = matched_activity[0]
                activity_name = matched_activity[1]
                print(f"[提醒服务] 正在启动活动: {activity_name} (ID: {activity_id})")
                
                # 直接通过 db_manager 启动活动（跳过备注对话框）
                note = f"从日程提醒自动启动"
                result = self.db_manager.start_activity(activity_id, note)
                
                if result:
                    print(f"[提醒服务] 活动启动成功: {activity_name}")
                    # 刷新主窗口显示
                    if hasattr(self.main_window, 'refresh_all'):
                        self.main_window.refresh_all()
                    self._show_main_window()
                else:
                    print(f"[提醒服务] 活动启动失败")
                    self._show_main_window()
            else:
                print(f"[提醒服务] 未找到匹配的活动: '{content}'")
                print(f"[提醒服务] 可用活动: {[a[1] for a in activities]}")
                self._show_main_window()
                    
        except Exception as e:
            print(f"[提醒服务] 开始活动时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_main_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.show()
            self.main_window.activateWindow()
            self.main_window.raise_()
    
    def snooze_reminder(self, start_time: str, end_time: str, content: str, minutes: int = 5):
        """稍后提醒（默认5分钟后）
        
        使用可取消的 QTimer 替代 QTimer.singleShot + lambda，
        避免 lambda 捕获 self 导致的内存泄漏和对象销毁后访问问题。
        """
        key = f"{start_time}_{content}"
        if key not in self.snooze_schedules:
            # 创建可取消的定时器，父对象设为 self
            timer = QTimer()
            timer.setSingleShot(True)

            timer.timeout.connect(partial(
                self._snooze_callback, 
                start_time=start_time, 
                end_time=end_time, 
                content=content, 
                key=key
            ))
            timer.start(minutes * 60 * 1000)
            # 保存定时器引用以便取消
            self.snooze_schedules[key] = timer
    
    def _snooze_callback(self, start_time: str, end_time: str, content: str, key: str):
        """稍后提醒回调"""
        if key in self.snooze_schedules:
            # 清理定时器引用
            timer = self.snooze_schedules.pop(key, None)
            if timer:
                timer.deleteLater()
            self.show_reminder(start_time, end_time, content)
    
    def stop(self):
        """停止提醒服务"""
        self.reminder.stop()
        # 停止所有 snooze 定时器
        for key, timer in list(self.snooze_schedules.items()):
            try:
                timer.stop()
                timer.deleteLater()
            except RuntimeError:
                pass
        self.snooze_schedules.clear()
