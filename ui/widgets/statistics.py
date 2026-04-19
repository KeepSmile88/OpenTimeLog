#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计分析组件 (v6.0 - 纯Qt原生绘图版)
使用 QChart + QPainter 实现高性能图表
"""

import sys
import datetime
import traceback

from collections import defaultdict
from functools import partial

# ========== 调试日志辅助函数 ==========
def _debug_log(tag: str, msg: str, include_stack: bool = False):
    """输出调试日志，可选包含堆栈信息"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}][{tag}] {msg}")
    sys.stdout.flush()  # 确保立即输出

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QTableWidget, QTableWidgetItem, QTabWidget,
    QScrollArea, QFrame, QHeaderView, QGraphicsDropShadowEffect,
    QSplitter, QApplication
)
from PySide6.QtCore import QDate, Qt, QRectF, QPointF, QMargins
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath

# 导入自绘图表组件
from ui.widgets.chart_widgets import PieChartWidget, BarChartWidget, ComparisonChartWidget
from ui.styles.app_style import theme_manager, get_cjk_font, CJK_FONT_FAMILY


class HeatmapWidget(QWidget):
    """热力图组件 - 增强版"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        self.year = datetime.date.today().year
        self.setMinimumHeight(320)
        self.setMouseTracking(True)  # 启用鼠标追踪
        self.hovered_cell = None  # 当前悬停的格子
        self.cell_rects = {}  # 存储每个日期的矩形区域
        
        # 监听主题变更自动重绘
        theme_manager.theme_changed.connect(lambda t: self.update())
        
    def set_data(self, data, year):
        self.data = data
        self.year = year
        self.cell_rects.clear()
        self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于悬停效果"""
        pos = event.position() if hasattr(event, 'position') else event.pos()
        new_hovered = None
        for date_str, rect in self.cell_rects.items():
            if rect.contains(pos):
                new_hovered = date_str
                break
        
        if new_hovered != self.hovered_cell:
            self.hovered_cell = new_hovered
            self.update()
            
            # 设置工具提示
            if new_hovered and new_hovered in self.data:
                value = self.data[new_hovered]  # 值为秒
                hours = int(value // 3600)
                mins = int((value % 3600) // 60)
                self.setToolTip(f"📅 {new_hovered}\n⏱️ 活动时长: {hours}小时{mins}分钟")
            elif new_hovered:
                self.setToolTip(f"📅 {new_hovered}\n⏱️ 无活动记录")
            else:
                self.setToolTip("")
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.hovered_cell = None
        self.setToolTip("")
        self.update()
    
    def paintEvent(self, event):
        if not hasattr(self, 'year'):
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        t = theme_manager.current_tokens
        
        # 绘制背景卡片
        bg_rect = QRectF(10, 5, self.width() - 20, self.height() - 10)
        painter.setBrush(QBrush(QColor(t['bg_card'])))
        painter.setPen(QPen(QColor(t['border']), 1))
        painter.drawRoundedRect(bg_rect, 12, 12)
        
        # 计算绘图区域
        margin_left = 70
        margin_top = 80
        margin_right = 30
        margin_bottom = 50
        
        width = self.width() - margin_left - margin_right
        height = self.height() - margin_top - margin_bottom
        
        cell_width = max(width / 53, 12)
        cell_height = max(height / 7, 12)
        cell_gap = 3  # 格子间距
        
        # 绘制标题（渐变效果）
        font_title = get_cjk_font(14, QFont.Bold)
        painter.setFont(font_title)
        
        # 标题
        title = f"📊 {self.year} 年度活动热力图"
        title_rect = QRectF(0, 20, self.width(), 35)
        painter.setPen(QColor(t['primary']))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, title)
        
        # 绘制副标题
        font_subtitle = get_cjk_font(9)
        painter.setFont(font_subtitle)
        painter.setPen(QColor(t['text_secondary']))
        
        # 统计信息（数据单位是秒）
        total_days = len([v for v in self.data.values() if v > 0])
        total_seconds = sum(self.data.values()) if self.data else 0
        total_hours = total_seconds / 3600  # 秒转小时
        subtitle = f"全年活跃天数: {total_days} 天  |  累计时长: {int(total_hours)} 小时"
        painter.drawText(QRectF(0, 48, self.width(), 20), Qt.AlignmentFlag.AlignCenter, subtitle)
        
        # 获取最大值用于颜色映射
        max_val = max(self.data.values()) if self.data else 1
        
        # 绘制月份标签
        font_month = get_cjk_font(8)
        painter.setFont(font_month)
        painter.setPen(QColor(t['text_secondary']))
        
        months = ['1月', '2月', '3月', '4月', '5月', '6月', 
                  '7月', '8月', '9月', '10月', '11月', '12月']
        month_weeks = [0, 4, 8, 13, 17, 22, 26, 31, 35, 39, 44, 48]  # 大致对应的周数
        
        for i, (month, week) in enumerate(zip(months, month_weeks)):
            x = margin_left + week * cell_width
            painter.drawText(QRectF(x, margin_top - 18, 60, 15), 
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, month)
        
        # 生成日期网格
        start_date = datetime.date(self.year, 1, 1)
        current = start_date - datetime.timedelta(days=start_date.weekday())
        
        self.cell_rects.clear()  # 重置格子区域映射
        
        # 颜色渐变定义 (基于主题色生成)
        base = QColor(t['primary'])
        # 生成5个等级：0=背景色/灰色, 1-4为逐渐加深的颜色
        # 0级（无数据）：使用较淡的边框色或专门的空闲色
        color_levels = [
            QColor(t['bg_hover']),      # 0级
            base.lighter(170),          # 1级 (最淡)
            base.lighter(145),          # 2级
            base.lighter(120),          # 3级
            base                        # 4级 (基准色)
        ]
        
        # 绘制热力图格子
        for week in range(53):
            for day in range(7):
                x = margin_left + week * cell_width
                y = margin_top + day * cell_height
                
                date_str = current.strftime('%Y-%m-%d')
                value = self.data.get(date_str, 0)
                
                # 仅绘制有效日期
                if current.year == self.year or (current.year == self.year - 1 and current.month == 12):
                    # 计算颜色
                    if value == 0:
                        color = color_levels[0]
                    else:
                        intensity = value / max_val
                        if intensity < 0.2: color = color_levels[1]
                        elif intensity < 0.4: color = color_levels[2]
                        elif intensity < 0.7: color = color_levels[3]
                        else: color = color_levels[4]
                    
                    # 格子矩形
                    rect = QRectF(x + cell_gap/2, y + cell_gap/2, 
                                 cell_width - cell_gap, cell_height - cell_gap)
                    
                    # 存储格子区域用于鼠标事件
                    self.cell_rects[date_str] = rect
                    
                    # 悬停效果
                    if date_str == self.hovered_cell:
                        # 高亮边框
                        painter.setPen(QPen(QColor(t['accent']), 2))
                        painter.setBrush(QBrush(color.lighter(110)))
                    else:
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(QBrush(color))
                    
                    # 绘制圆角矩形
                    painter.drawRoundedRect(rect, 2, 2)
                
                current += datetime.timedelta(days=1)
                if current.year > self.year and week > 45:
                    break
        
        # 绘制星期标签
        font_label = get_cjk_font(9)
        painter.setFont(font_label)
        painter.setPen(QColor(t['text_secondary']))
        
        weekdays = [("周一", 0), ("周二", 1), ("周三", 2), ("周四", 3), 
                    ("周五", 4), ("周六", 5), ("周日", 6)]
        for label, idx in weekdays:
            y = margin_top + idx * cell_height + cell_height / 2
            painter.drawText(QRectF(15, y - 8, margin_left - 20, 16),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
        
        # 绘制图例
        legend_x = margin_left
        legend_y = self.height() - 35
        
        painter.setFont(get_cjk_font(9))
        painter.setPen(QColor(t['text_secondary']))
        painter.drawText(legend_x, legend_y + 10, "活动强度:")
        
        legend_x += 65
        painter.drawText(legend_x - 5, legend_y + 10, "少")
        
        for i, color in enumerate(color_levels):
            x = legend_x + 25 + i * 22
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(105), 0.5))
            painter.drawRoundedRect(QRectF(x, legend_y, 18, 18), 3, 3)
        
        painter.setPen(QColor(t['text_secondary']))
        painter.drawText(legend_x + 25 + len(color_levels) * 22 + 8, 
                        legend_y + 10, "多")

class StatisticsWidget(QWidget):
    """统计分析组件 - 纯Qt版"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # 刷新互斥标志 - 防止刷新重入导致资源竞争
        self._is_refreshing = False
        
        self.setup_ui()
        self.update_styles() # Apply initial styles
        
        # 不在构造函数中刷新，标记为脏数据，让 showEvent 来触发首次刷新
        self._is_dirty = True
        
        # 监听主题变更
        theme_manager.theme_changed.connect(self.update_styles)

    def setup_ui(self):
        """构建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)  # 统一边距
        layout.setSpacing(12)
        
        # 顶部控制
        top_ctrl = QHBoxLayout()
        self.date_label = QLabel("基准日期:")
        self.date_label.setFont(get_cjk_font(9))
        
        self.global_date = QDateEdit(QDate.currentDate())
        self.global_date.setCalendarPopup(True)
        self.global_date.setDisplayFormat("yyyy-MM-dd")
        self.global_date.setMinimumWidth(120)
        self.global_date.dateChanged.connect(self.refresh_all_stats)
        
        top_ctrl.addWidget(self.date_label)
        top_ctrl.addWidget(self.global_date)
        top_ctrl.addStretch()
        layout.addLayout(top_ctrl)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 基础统计页
        self.basic_tab = QWidget()
        self.setup_basic_tab()
        self.tabs.addTab(self.basic_tab, "📊 基本分布")
        
        # 趋势分析页
        self.trend_tab = QWidget()
        self.setup_trend_tab()
        self.tabs.addTab(self.trend_tab, "📈 深度洞察")
        
        layout.addWidget(self.tabs)

    def setup_basic_tab(self):
        """基础统计页"""
        layout = QVBoxLayout(self.basic_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # 1. 顶部控制栏
        ctrl_layout = QHBoxLayout()
        self.view_label = QLabel("统计维度:")
        self.view_label.setFont(get_cjk_font(9))
        self.view_combo = QComboBox()
        self.view_combo.addItems(['日统计', '周统计', '月统计'])
        self.view_combo.setMinimumWidth(100)
        self.view_combo.currentTextChanged.connect(self.refresh_basic_stats)
        ctrl_layout.addWidget(self.view_label)
        ctrl_layout.addWidget(self.view_combo)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)
        
        # 2. 分割器容器
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(2)
        
        # 数据表格
        self.table = QTableWidget()
        self.table.setMinimumHeight(120)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.splitter.addWidget(self.table)
        
        # 图表容器 - 使用水平分割器让用户可调整两图比例
        chart_splitter = QSplitter(Qt.Orientation.Horizontal)
        chart_splitter.setHandleWidth(3)
        
        # 饼图 - 使用 QPainter 自绘组件替代 Qt Charts
        self.pie_chart_widget = PieChartWidget()
        self.pie_chart_widget.setMinimumSize(300, 280)
        
        # 条形图 - 使用 QPainter 自绘组件替代 Qt Charts
        self.bar_chart_widget = BarChartWidget()
        self.bar_chart_widget.setMinimumSize(300, 280)
        
        chart_splitter.addWidget(self.pie_chart_widget)
        chart_splitter.addWidget(self.bar_chart_widget)
        chart_splitter.setStretchFactor(0, 1)
        chart_splitter.setStretchFactor(1, 1)
        
        self.splitter.addWidget(chart_splitter)
        
        # 设置初始比例: 表格占 2, 图表占 5
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 5)
        
        layout.addWidget(self.splitter)

    def setup_trend_tab(self):
        """趋势分析页"""
        layout = QVBoxLayout(self.trend_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(25)
        
        # 对比分析
        self.comp_title = QLabel("▶ 周期对比分析 (本期 vs 上期)")
        self.comp_title.setFont(get_cjk_font(10, QFont.Weight.Bold))
        c_layout.addWidget(self.comp_title)
        
        self.comp_chart_widget = ComparisonChartWidget()
        self.comp_chart_widget.setMinimumHeight(300)
        c_layout.addWidget(self.comp_chart_widget)
        
        # 热力图
        self.heat_title = QLabel("▶ 年度时间贡献热力图")
        self.heat_title.setFont(get_cjk_font(10, QFont.Weight.Bold))
        c_layout.addWidget(self.heat_title)
        
        self.heatmap = HeatmapWidget()
        c_layout.addWidget(self.heatmap)
        
        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def update_styles(self, theme=None):
        """应用样式 (动态主题)"""
        t = theme_manager.current_tokens
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {t['bg_main']};
                font-family: {CJK_FONT_FAMILY};
                font-size: 9pt;
                color: {t['text_primary']};
            }}
            QLabel {{
                color: {t['text_primary']};
            }}
            QTableWidget {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                background-color: {t['bg_card']};
                gridline-color: {t['border_light']};
                color: {t['text_primary']};
                alternate-background-color: {t['bg_item']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {t['bg_hover']};
                color: {t['primary']};
            }}
            QHeaderView::section {{
                background-color: {t['bg_card']};
                padding: 10px;
                border: none;
                border-bottom: 2px solid {t['border']};
                font-weight: bold;
                color: {t['text_secondary']};
            }}
            QComboBox, QDateEdit {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 6px 12px;
                background: {t['bg_input']};
                color: {t['text_primary']};
                min-height: 26px;
                selection-background-color: {t['primary']};
            }}
            QComboBox:hover, QDateEdit:hover {{
                border-color: {t['primary']};
            }}
            /* QTabWidget 样式在 app_style 全局定义更好，这里仅覆盖 content pane */
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                border-radius: 4px;
                background: {t['bg_main']};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {t['bg_card']};
                color: {t['text_secondary']};
                border: 1px solid {t['border']};
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {t['bg_main']};
                color: {t['primary']};
                border-bottom: 1px solid {t['bg_main']}; /* 遮住 pane border */
                font-weight: bold;
            }}
            QSplitter::handle {{
                background-color: {t['border']};
            }}
        """)
        
        # 强制更新组件
        if hasattr(self, 'table'):
            # 更新表头颜色等
            pass

    def showEvent(self, event):
        """窗口显示时，如果数据脏了，执行刷新"""
        super().showEvent(event)
        if getattr(self, '_is_dirty', False):
            self.refresh_all_stats()

    def refresh_all_stats(self):
        """刷新统计（惰性加载，仅在可见时真正执行）"""
        _debug_log("STATS", "=== refresh_all_stats 开始 ===")
        
        # 1. 如果窗口不可见，标记为脏数据并跳过
        if not self.isVisible():
            self._is_dirty = True
            return
        
        # 2. 如果正在刷新中，标记脏数据并跳过（防止重入）
        if self._is_refreshing:
            self._is_dirty = True
            return

        self._is_refreshing = True  # 设置互斥标志
        self._is_dirty = False
        try:
            self.refresh_basic_stats()
            # 恢复趋势统计
            self.refresh_trend_stats()
            _debug_log("STATS", "=== refresh_all_stats 完成 ===")
        except Exception as e:
            _debug_log("STATS", f"❌ 统计刷新异常: {e}", include_stack=True)
            traceback.print_exc()
        finally:
            self._is_refreshing = False  # 释放互斥标志

    def refresh_basic_stats(self):
        """刷新基础统计"""
        d = self.global_date.date().toPython()
        v = self.view_combo.currentText()
        
        try:
            if v == '日统计': 
                stats = self.db_manager.get_daily_stats(d)
            elif v == '周统计': 
                stats = self.db_manager.get_weekly_stats(d)
            else: 
                stats = self.db_manager.get_monthly_stats(d)
            
            self.update_basic_table(stats)
            self.update_pie_chart(stats)
            self.update_bar_chart(stats)
        except Exception as e:
            _debug_log("STATS", f"❌ refresh_basic_stats failed: {e}", include_stack=True)

    def update_basic_table(self, stats):
        """更新表格"""
        headers = ['活动', '总时长', '目标', '完成度', '次数']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(stats))
        
        t = theme_manager.current_tokens
        
        for row, s in enumerate(stats):
            mins = s[5] // 60
            goal = s[4]
            comp = (mins/goal*100) if goal > 0 else 0
            
            # 活动名称
            name_item = QTableWidgetItem(f"{s[3]} {s[1]}")
            # 使用主题色混和，或者保持原色
            # 这里简单使用 Activity 本身颜色作为标记，不需要改变
            # 但背景最好透明或适配主题
            # name_item.setBackground(QColor(s[2] + "20")) 
            
            # 总时长
            duration_item = QTableWidgetItem(f"{mins//60:02d}:{mins%60:02d}")
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 目标
            goal_item = QTableWidgetItem(f"{goal//60:02d}:{goal%60:02d}")
            goal_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 完成度
            progress_item = QTableWidgetItem(f"{comp:.1f}%")
            progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if comp >= 100:
                progress_item.setForeground(QColor(t['success']))
                progress_item.setFont(get_cjk_font(9, QFont.Weight.Bold))
            elif comp >= 80:
                progress_item.setForeground(QColor(t['warning']))
            else:
                progress_item.setForeground(QColor(t['text_primary']))
            
            # 次数
            count_item = QTableWidgetItem(str(s[6]))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, duration_item)
            self.table.setItem(row, 2, goal_item)
            self.table.setItem(row, 3, progress_item)
            self.table.setItem(row, 4, count_item)

    def update_pie_chart(self, stats):
        """更新饼图"""
        try:
            active = []
            for s in stats:
                if len(s) > 5 and isinstance(s[5], (int, float)) and s[5] > 0:
                    active.append(s)
            
            if not active:
                self.pie_chart_widget.set_data([])
                return
            
            active.sort(key=lambda x: x[5], reverse=True)
            
            chart_data = []
            t = theme_manager.current_tokens
            chart_colors = t['chart_colors']
            
            for idx, s in enumerate(active):
                name = str(s[1]) if s[1] else "unnamed"
                # 如果 Activity 自带颜色有效则使用，否则使用 Token
                if s[2] and s[2].startswith('#'):
                     color = s[2]
                else:
                     color = chart_colors[idx % len(chart_colors)]
                     
                value = float(s[5]) 
                chart_data.append((name, color, value))
            
            self.pie_chart_widget.set_data(chart_data)
            
        except Exception as e:
            _debug_log("PIE", f"❌ update_pie_chart failed: {e}")
            traceback.print_exc()

    def update_bar_chart(self, stats):
        """更新柱状图"""
        try:
            active = [s for s in stats if len(s) > 5 and s[5] > 0]
            if not active:
                self.bar_chart_widget.set_data([])
                return
            
            chart_data = []
            t = theme_manager.current_tokens
            chart_colors = t['chart_colors']
            
            for idx, s in enumerate(active):
                name = str(s[1]) if s[1] else "unnamed"
                if s[2] and s[2].startswith('#'):
                     color = s[2]
                else:
                     color = chart_colors[idx % len(chart_colors)]
                value = float(s[5]) 
                chart_data.append((name, color, value))
            
            self.bar_chart_widget.set_data(chart_data)
        except Exception as e:
            _debug_log("BAR", f"❌ update_bar_chart failed: {e}")
            traceback.print_exc()

    def refresh_trend_stats(self):
        """刷新趋势"""
        self.update_comparison_chart()
        self.update_heatmap()

    def update_comparison_chart(self):
        """更新对比图"""
        try:
            data = self.db_manager.get_period_comparison_data(
                'week', self.global_date.date().toPython())

            if not data:
                self.comp_chart_widget.set_data([], [])
                return

            this_p = data.get('this_period', {})
            last_p = data.get('last_period', {})

            all_acts = sorted(list(set(this_p.keys()) | set(last_p.keys())))
            
            if not all_acts:
                self.comp_chart_widget.set_data([], [])
                return

            current_data = []
            previous_data = []
            
            for act in all_acts:
                last_val = last_p.get(act, 0) / 3600
                this_val = this_p.get(act, 0) / 3600
                name = str(act) if act else "未命名"
                
                previous_data.append((name, last_val))
                current_data.append((name, this_val))

            self.comp_chart_widget.set_data(current_data, previous_data)

        except Exception as e:
            _debug_log("COMP", f"❌ update_comparison_chart 异常: {e}")
            traceback.print_exc()

    def update_heatmap(self):
        """更新热力图"""
        year = self.global_date.date().year()
        data = self.db_manager.get_yearly_heatmap_data(year)
        self.heatmap.set_data(data, year)

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        super().closeEvent(event)