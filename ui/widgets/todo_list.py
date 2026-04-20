#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级待办事项组件 (v2.0)
支持优先级、截止日期和关联项目
"""

import datetime
import traceback
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QCheckBox,
    QLabel, QFrame, QComboBox, QDateEdit, QToolButton,
    QMenu, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QSize, QDate, Signal
from PySide6.QtGui import QFont, QColor, QPalette, QAction

from ui.styles.app_style import theme_manager

# ========== 调试日志辅助函数 ==========
def _debug_log(tag: str, msg: str, include_stack: bool = False):
    """输出调试日志，可选包含堆栈信息"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}][{tag}] {msg}")
    if include_stack:
        print("  堆栈信息:")
        for line in traceback.format_stack()[:-1]:
            for subline in line.strip().split('\n'):
                print(f"    {subline}")
    if sys.stdout is not None:
        sys.stdout.flush()


class TodoItemWidget(QWidget):
    """高级待办事项列表项组件"""
    
    # 状态映射
    PRIORITY_COLORS = {
        0: "#28a745", # 低: 绿色
        1: "#007bff", # 中: 蓝色
        2: "#ffc107", # 高: 黄色
        3: "#dc3545"  # 紧急: 红色
    }
    
    def __init__(self, data, parent_list):
        super().__init__()
        # data: (id, content, is_completed, priority, due_date, description, act_name, act_color, act_icon, act_id)
        self.todo_id = data[0]
        self.content = data[1]
        self.is_completed = data[2]
        self.priority = data[3]
        self.due_date = data[4]
        self.act_name = data[6]
        self.act_color = data[7]
        self.parent_list = parent_list
        
        self.setup_ui()
        self.update_theme() # 初始化时应用当前主题
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)
        
        # 1. 优先级标识条
        self.p_bar = QFrame()
        self.p_bar.setFixedWidth(4)
        self.p_bar.setStyleSheet(f"background-color: {self.PRIORITY_COLORS.get(self.priority, '#ccc')}; border-radius: 2px;")
        layout.addWidget(self.p_bar)
        
        # 2. 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(bool(self.is_completed))
        self.checkbox.stateChanged.connect(self.on_state_changed)
        layout.addWidget(self.checkbox)
        
        # 3. 内容区 (垂直布局：第一行标题，第二行信息)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # 标题栏
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.content)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # 状态徽章 (关联项目)
        if self.act_name:
            tag = QLabel(f"{self.act_name}")
            tag.setStyleSheet(f"""
                background-color: {self.act_color}25;
                color: {self.act_color};
                border: 1px solid {self.act_color}50;
                border-radius: 10px;
                padding: 1px 8px;
                font-size: 10px;
                font-weight: bold;
            """)
            title_layout.addWidget(tag)
        
        # 日期详情
        detail_layout = QHBoxLayout()
        if self.due_date:
            today = QDate.currentDate().toString("yyyy-MM-dd")
            is_overdue = self.due_date < today and not self.is_completed
            date_color = "#dc3545" if is_overdue else "#6c757d"
            
            self.date_lbl = QLabel(f"📅 {self.due_date}")
            # 暂时存储状态颜色，在 update_theme 中会结合主题调整
            self._date_color_status = date_color 
            self.date_lbl.setStyleSheet(f"color: {date_color}; font-size: 11px;")
            detail_layout.addWidget(self.date_lbl)
        
        detail_layout.addStretch()
        
        info_layout.addLayout(title_layout)
        info_layout.addLayout(detail_layout)
        layout.addLayout(info_layout)
        
        # 4. 删除按钮
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)
        
    def update_theme(self):
        """更新主题颜色"""
        t = theme_manager.current_tokens
        
        # 标题颜色 / 字体
        if self.is_completed:
            self.apply_completed_style()
        else:
            self.apply_normal_style()
            
        # 删除按钮样式
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {t['text_light']};
                border-radius: 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {t['danger']}40;
                color: {t['danger']};
            }}
        """)
        
        # 日期标签颜色适配 (如果是灰色说明是普通日期，跟随副标题色；如果是红色说明逾期，保持红色)
        if hasattr(self, 'date_lbl'):
            color = self._date_color_status
            if color == "#6c757d" or color == "#9AA0A6": # 默认灰色
                color = t['text_secondary']
            self.date_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")

    def on_state_changed(self, state):
        state = Qt.CheckState(state)
        checked = (state == Qt.CheckState.Checked)
        self.parent_list.update_todo_status(self.todo_id, checked)
        if checked:
            self.apply_completed_style()
        else:
            self.apply_normal_style()
            
    def apply_completed_style(self):
        t = theme_manager.current_tokens
        font = self.title_label.font()
        font.setStrikeOut(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(f"font-size: 14px; color: {t['text_light']};")
        
    def apply_normal_style(self):
        t = theme_manager.current_tokens
        font = self.title_label.font()
        font.setStrikeOut(False)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet(f"font-size: 14px; font-weight: 500; color: {t['text_primary']};")
    
    def _on_delete_clicked(self):
        """删除按钮点击处理"""
        self.parent_list.delete_todo(self.todo_id)


class TodoListWidget(QWidget):
    """高级待办事项主组件"""
    
    # 信号定义：请求启动活动 (act_id, note)
    start_activity_requested = Signal(int, str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.filter_state = "all" # all, pending, completed
        self._todo_widgets = []
        self.setup_ui()
        self.refresh_list()
        
        # 连接双击信号
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # 监听主题变更
        theme_manager.theme_changed.connect(self.update_styles)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # --- 顶部卡片：输入区域 ---
        self.input_card = QFrame()
        self.input_card.setObjectName("inputCard")
        # 初始样式
        
        card_layout = QVBoxLayout(self.input_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        
        # 第一行：快速添加框
        top_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("想做点什么？（输入内容按下回车快速添加）")
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self.add_todo)
        
        self.add_btn = QPushButton("添加待办")
        self.add_btn.setFixedSize(100, 40)
        self.add_btn.clicked.connect(self.add_todo)
        
        top_row.addWidget(self.input_field)
        top_row.addWidget(self.add_btn)
        card_layout.addLayout(top_row)
        
        # 第二行：高级选项（优先级、日期、项目）
        opt_layout = QHBoxLayout()
        opt_layout.setSpacing(10)
        
        self.p_combo = QComboBox()
        self.p_combo.addItems(["低优先级", "中优先级", "高优先级", "紧急任务"])
        self.p_combo.setCurrentIndex(1) # 默认中
        self.p_combo.setFixedWidth(120)
        
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedWidth(120)
        
        self.act_combo = QComboBox()
        self.act_combo.addItem("不关联项目", None)
        self.act_combo.setFixedWidth(150)
        
        self.label_p = QLabel("优先级:")
        self.label_d = QLabel("截止日期:")
        self.label_a = QLabel("所属项目:")
        
        opt_layout.addWidget(self.label_p)
        opt_layout.addWidget(self.p_combo)
        opt_layout.addWidget(self.label_d)
        opt_layout.addWidget(self.date_edit)
        opt_layout.addWidget(self.label_a)
        opt_layout.addWidget(self.act_combo)
        opt_layout.addStretch()
        
        card_layout.addLayout(opt_layout)
        layout.addWidget(self.input_card)
        
        # --- 中间工具栏：筛选 ---
        toolbar = QHBoxLayout()
        self.filter_all = QPushButton("全部")
        self.filter_pending = QPushButton("进行中")
        self.filter_done = QPushButton("已完成")
        
        self.filter_btns = [self.filter_all, self.filter_pending, self.filter_done]
        for btn in self.filter_btns:
            btn.setCheckable(True)
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda c, b=btn: self._on_filter_clicked(b))
        
        self.filter_all.setChecked(True)
        # 具体的 clicked connect 在 _on_filter_clicked 处理互斥
        
        toolbar.addWidget(self.filter_all)
        toolbar.addWidget(self.filter_pending)
        toolbar.addWidget(self.filter_done)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # --- 列表区域 ---
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self.refresh_activities()
        self.update_styles() # 应用初始样式

    def _on_filter_clicked(self, btn):
        # 简单的互斥逻辑
        for b in self.filter_btns:
            b.setChecked(b == btn)
            
        if btn == self.filter_all: self.apply_filter("all")
        elif btn == self.filter_pending: self.apply_filter("pending")
        elif btn == self.filter_done: self.apply_filter("completed")

    def update_styles(self, theme=None):
        """更新组件样式"""
        t = theme_manager.current_tokens
        
        # 1. 输入卡片
        self.input_card.setStyleSheet(f"""
            #inputCard {{
                background-color: {t['bg_input']}; 
                border-radius: 10px;
                border: 1px solid {t['border']};
            }}
        """)
        
        # 2. 输入框
        self.input_field.setStyleSheet(f"""
            border: none; 
            font-size: 15px; 
            background: transparent; 
            color: {t['text_primary']};
        """)
        
        # 3. 添加按钮
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['primary']};
                color: {t['text_inverse']};
                border-radius: 5px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {t['primary_hover']}; }}
        """)
        
        # 4. 标签颜色
        label_style = f"color: {t['text_secondary']}; font-size: 13px;"
        self.label_p.setStyleSheet(label_style)
        self.label_d.setStyleSheet(label_style)
        self.label_a.setStyleSheet(label_style)
        
        # 5. 筛选按钮
        btn_style = f"""
            QPushButton {{ 
                border: 1px solid {t['border_light']}; 
                border-radius: 15px; 
                padding: 5px; 
                background-color: transparent; 
                color: {t['text_secondary']};
            }}
            QPushButton:checked {{ 
                background-color: {t['primary']}; 
                color: {t['text_inverse']}; 
                border: none; 
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background-color: {t['bg_hover']}; 
            }}
        """
        for btn in self.filter_btns:
            btn.setStyleSheet(btn_style)
            
        # 6. 列表背景
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; outline: none; }}
            QListWidget::item {{ 
                background-color: {t['bg_item']}; 
                border-radius: 8px; 
                margin-bottom: 8px; 
                border: 1px solid {t['border']}; 
            }}
            QListWidget::item:selected {{ border: 1px solid {t['primary']}; }}
        """)
        
        # 7. 更新所有子项
        for widget in self._todo_widgets:
            widget.update_theme()

    def refresh_activities(self):
        """同步数据库中的活动分类"""
        self.act_combo.clear()
        self.act_combo.addItem("不关联项目", None)
        acts = self.db_manager.get_activities()
        for a in acts:
            self.act_combo.addItem(f"{a[3]} {a[1]}", a[0])

    def add_todo(self):
        content = self.input_field.text().strip()
        if not content: return
        
        priority = self.p_combo.currentIndex()
        due_date = self.date_edit.date().toString("yyyy-MM-dd")
        act_id = self.act_combo.currentData()
        
        self.db_manager.add_todo(content, priority, due_date, act_id)
        self.input_field.clear()
        self.refresh_list()

    def refresh_list(self):
        """刷新待办事项列表"""
        # _debug_log("TODO", ">>> refresh_list 开始", include_stack=True) 

        # 1. 完整清理旧内容
        self._cleanup_list_completely()

        # 2. 获取数据
        todos = self.db_manager.get_todos()
        _debug_log("TODO", f"获取到 {len(todos) if todos else 0} 条待办 (筛选: {self.filter_state})")

        # 3. 重置引用列表
        self._todo_items = []
        self._todo_widgets = []

        # 4. 创建新的列表项
        _debug_log("TODO", "步骤3: 创建列表项")
        for todo in todos:
            # 数据验证
            if len(todo) < 10:
                _debug_log("TODO", f"警告: todo 数据不完整，跳过: {todo}")
                continue

            is_completed = todo[2]

            # 筛选逻辑
            if self.filter_state == "pending" and is_completed:
                continue
            if self.filter_state == "completed" and not is_completed:
                continue

            # 创建列表项
            _debug_log("TODO", f"  创建 todo id={todo[0]}")
            item = self._create_todo_item(todo)
            widget = self._create_todo_widget(todo)

            # 保存引用
            self._todo_items.append(item)
            self._todo_widgets.append(widget)

            # 添加到列表
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        
        _debug_log("TODO", f"<<< refresh_list 完成, 显示 {len(self._todo_items)} 条")

    def _cleanup_list_completely(self):
        """完整清理列表中的所有内容"""
        self.list_widget.clear()

        # 2. 清理引用，等待 GC
        if hasattr(self, '_todo_widgets'):
            self._todo_widgets.clear()

        if hasattr(self, '_todo_items'):
            self._todo_items.clear()

    def _cleanup_old_widgets(self):
        """简化版清理函数（如果只需要清理 widgets）"""
        if not hasattr(self, '_todo_widgets'):
            return

        for widget in self._todo_widgets:
            try:
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                widget.deleteLater()
            except RuntimeError:
                pass

        self._todo_widgets.clear()
            
    def refresh_list_old(self):

        self._cleanup_old_widgets()

        # self.list_widget.clear()
        todos = self.db_manager.get_todos()

        print("刷新待办事项：\t", self.filter_state)

        # if not hasattr(self, '_todo_widgets'):
        #     self._todo_widgets = []
        # else:
        #     self._todo_widgets.clear()

        # 3. 重置引用列表
        self._todo_items = []
        self._todo_widgets = []
        
        for todo in todos:
            # 数据验证
            if len(todo) < 10:
                print(f"警告: todo 数据不完整，跳过: {todo}")
                continue
            
            print("todo :\t", todo)
            is_completed = todo[2]
            # 执行前端筛选逻辑
            if self.filter_state == "pending" and is_completed: continue
            if self.filter_state == "completed" and not is_completed: continue
            
            # item = QListWidgetItem()
            # item.setSizeHint(QSize(0, 70)) 
            
            # # 存储关键数据到 item (id, act_id, act_name)
            # item.setData(Qt.UserRole, todo[0])      # todo_id
            # item.setData(Qt.UserRole + 1, todo[9])  # act_id
            # item.setData(Qt.UserRole + 2, todo[6])  # act_name

            item = self._create_todo_item(todo)
            widget = self._create_todo_widget(todo)
            
            self._todo_items.append(item)
            self._todo_widgets.append(widget)
            
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _create_todo_item(self, todo):
        """创建单个待办事项的 QListWidgetItem"""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 70))

        item.setData(Qt.ItemDataRole.UserRole, todo[0])      # todo_id
        item.setData(Qt.ItemDataRole.UserRole + 1, todo[9])  # act_id
        item.setData(Qt.ItemDataRole.UserRole + 2, todo[6])  # act_name
    
        return item

    def _create_todo_widget(self, todo):
        """创建单个待办事项的自定义 Widget"""
        widget = TodoItemWidget(todo, self)
        
        # 如果 TodoItemWidget 有信号，在这里连接
        # widget.completed_changed.connect(self._on_todo_completed)
        # widget.deleted.connect(self._on_todo_deleted)
    
        return widget

    def _cleanup_old_widgets_old(self):
        """清理旧的 widget 引用和信号连接"""

        # 1. 先移除所有 item widgets（重要顺序!）
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            
            widget = self.list_widget.itemWidget(item)
            if widget:
                # 解除关联
                self.list_widget.removeItemWidget(item)
                
                # 清理 widget 内部资源
                if hasattr(widget, 'cleanup'):
                    try:
                        widget.cleanup()
                    except Exception as e:
                        print(f"Widget 清理失败: {e}")
            
            # 标记删除
            widget.deleteLater()

        if hasattr(self, '_todo_widgets'):
            for widget in self._todo_widgets:
                try:
                    # 断开所有信号连接 (如果 TodoItemWidget 有信号)
                    # 例如: widget.some_signal.disconnect()
                    if hasattr(widget, 'cleanup'):
                        widget.cleanup()
                    # 标记 widget 待删除
                    widget.deleteLater()
                except RuntimeError:
                    # widget 已经被删除
                    pass
            self._todo_widgets.clear()

        if hasattr(self, '_todo_items'):
            self._todo_items.clear()
    
        # 3. 清空列表
        self.list_widget.clear()
        
        # 4. 处理删除事件（可选但推荐）
        QApplication.processEvents()
            
    def apply_filter(self, state):
        self.filter_state = state
        # 更新按钮显示
        for btn, key in zip(self.filter_btns, ["all", "pending", "completed"]):
            btn.setChecked(key == state)
        self.refresh_list()

    def update_todo_status(self, todo_id, is_completed):
        print("更新数据库中的待办事项：\t", todo_id, is_completed, self.filter_state)
        self.db_manager.update_todo_status(todo_id, is_completed)
        # 如果当前在特定筛选模式下，需要刷新列表以移除不符合项
        if self.filter_state != "all":
            self.refresh_list()
        
    def delete_todo(self, todo_id):
        self.db_manager.delete_todo(todo_id)
        self.refresh_list()

    def on_item_double_clicked(self, item):
        """处理列表项双击：如果有管理活动，则启动活动并标记完成"""
        # 1. 先获取所有需要的数据，因为后续操作可能会刷新列表导致 item 被删除
        todo_id = item.data(Qt.UserRole)
        act_id = item.data(Qt.UserRole + 1)
        
        widget = self.list_widget.itemWidget(item)
        if not widget: return
        content = widget.content
        
        if act_id:
            # 2. 启动活动
            note = f"任务: {content}"
            self.start_activity_requested.emit(act_id, note)
            
            # 3. 标记为已完成
            self.update_todo_status(todo_id, True)
            
            # 4. 如果是 'all' 模式，update_todo_status 不会刷新，手动刷新以更新UI状态
            # 如果是其他模式，update_todo_status 已经刷新过了
            if self.filter_state == "all":
                self.refresh_list()
