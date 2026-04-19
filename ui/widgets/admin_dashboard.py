#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理面板组件
用于导入报告并进行可视化分析
"""

import os
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QHorizontalBarSeries, QBarSet,
    QBarCategoryAxis, QValueAxis
)
from functools import partial


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.report_parser import ReportParser

# 顶级商业 SaaS 配色
ACCENT_COLORS = ['#00897B', '#E64A19', '#FFA000', '#5E35B1', '#1976D2', '#388E3C']


class ModernChartView(QChartView):
    """现代化的图表视图，支持抗锯齿"""
    def __init__(self, chart):
        super().__init__(chart)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)


class KPICard(QFrame):
    """关键指标卡片"""
    
    def __init__(self, title, value, subtext="", color="#007bff", parent=None):
        super().__init__(parent)
        self.color = color
        self.setFrameShape(QFrame.StyledPanel)
        self._apply_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 12, 12)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #6c757d; font-size: 12px; font-weight: bold;")
        
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        
        self.sub_lbl = QLabel(subtext)
        self.sub_lbl.setStyleSheet("color: #adb5bd; font-size: 11px;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.sub_lbl)
    
    def _apply_style(self, is_dark=False):
        """应用样式，支持深色模式"""
        bg_color = "#2d2d30" if is_dark else "white"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                border-left: 5px solid {self.color};
            }}
        """)
    
    def update_value(self, value, subtext=""):
        self.value_lbl.setText(str(value))
        self.sub_lbl.setText(subtext)
    
    def set_dark_mode(self, is_dark):
        """更新深色模式"""
        self._apply_style(is_dark)


class AdminDashboardWidget(QWidget):
    """管理仪表盘组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = False
        self.current_data = None
        self.current_filename = ""
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. 顶部栏：标题 + 导入按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("👨‍💼 管理层仪表盘")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #343a40;")
        
        self.import_btn = QPushButton("📂 导入报告")
        self.import_btn.clicked.connect(self.import_report)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.import_btn)
        layout.addLayout(header_layout)
        
        # 2. KPI 卡片区
        kpi_layout = QHBoxLayout()
        self.card_total_time = KPICard("总投入时长", "-", "等待导入数据...", "#28a745")
        self.card_total_tasks = KPICard("总任务产出", "-", "关联ID数量", "#17a2b8")
        self.card_top_focus = KPICard("核心聚焦", "-", "耗时最多的活动", "#ffc107")
        self.card_efficiency = KPICard("平均效率", "-", "分钟/任务", "#6610f2")
        
        kpi_layout.addWidget(self.card_total_time)
        kpi_layout.addWidget(self.card_total_tasks)
        kpi_layout.addWidget(self.card_top_focus)
        kpi_layout.addWidget(self.card_efficiency)
        layout.addLayout(kpi_layout)
        
        # 3. 核心内容区 (Splitter: 左图表 右表格)
        splitter = QSplitter(Qt.Horizontal)
        
        # 纵向滚动容器
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        scroll.setWidget(container)
        chart_layout = QVBoxLayout(container)
        chart_layout.setSpacing(20)
        chart_layout.setContentsMargins(10, 20, 10, 20)
        
        # ===== 图表1: 环形饼图 =====
        self.pie_chart = QChart()
        self.pie_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.pie_chart.setTitle("全员效能/产出比例看板")
        self.pie_chart.setTitleFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.pie_chart_view = ModernChartView(self.pie_chart)
        self.pie_chart_view.setMinimumHeight(350)
        chart_layout.addWidget(self.pie_chart_view)
        
        # ===== 图表2: 水平柱状图 =====
        self.bar_chart = QChart()
        self.bar_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.bar_chart.setTitle("Top 5 核心活动效能透视")
        self.bar_chart.setTitleFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.bar_chart_view = ModernChartView(self.bar_chart)
        self.bar_chart_view.setMinimumHeight(350)
        chart_layout.addWidget(self.bar_chart_view)
        
        chart_layout.addStretch()
        
        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["活动名称", "时长", "占比", "产出任务数"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        splitter.addWidget(scroll)
        splitter.addWidget(self.table)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
        # 初始状态：隐藏图表和表格
        self.pie_chart_view.hide()
        self.bar_chart_view.hide()
        self.table.hide()

    def import_report(self):
        """导入报告"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择报告文件", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        data = ReportParser.parse_report_file(file_path)
        
        if not data:
            QMessageBox.warning(self, "导入失败", "未能解析文件内容或文件为空。")
            return
        
        self.update_dashboard(data, os.path.basename(file_path))
    
    def set_dark_mode(self, is_dark):
        """设置深色模式"""
        self.is_dark = is_dark
        
        # 更新 KPI 卡片样式
        for card in [self.card_total_time, self.card_total_tasks, 
                     self.card_top_focus, self.card_efficiency]:
            card.set_dark_mode(is_dark)
        
        # 更新图表主题
        self._apply_chart_theme()
        
        # 如果有数据，重新绘图
        if self.current_data:
            self.update_dashboard(self.current_data, self.current_filename)
    
    def _apply_chart_theme(self):
        """应用图表主题"""
        bg_color = QColor("#2d2d30") if self.is_dark else QColor("white")
        text_color = QColor("#d4d4d4") if self.is_dark else QColor("#333333")
        
        for chart in [self.pie_chart, self.bar_chart]:
            chart.setBackgroundBrush(QBrush(bg_color))
            chart.setTitleBrush(QBrush(text_color))
            chart.legend().setLabelColor(text_color)

    def update_dashboard(self, data, filename):
        """更新仪表盘数据"""
        self.current_data = data
        self.current_filename = filename
        
        self.pie_chart_view.show()
        self.bar_chart_view.show()
        self.table.show()
        
        # 计算总计数据
        total_minutes = sum(d['minutes'] for d in data)
        total_tasks = sum(d['task_count'] for d in data)
        
        # 更新 KPI 卡片
        self.card_total_time.update_value(
            f"{total_minutes // 60}h {total_minutes % 60}m", 
            f"总计 {total_minutes} 分钟"
        )
        self.card_total_tasks.update_value(str(total_tasks), "个关联ID")
        
        if data:
            top_percentage = data[0]['minutes'] / total_minutes * 100 if total_minutes > 0 else 0
            self.card_top_focus.update_value(data[0]['name'], f"占比 {top_percentage:.1f}%")
        else:
            self.card_top_focus.update_value("-")
        
        if total_tasks > 0:
            self.card_efficiency.update_value(f"{int(total_minutes/total_tasks)} min", "每任务平均耗时")
        else:
            self.card_efficiency.update_value("-", "无任务计数")

        # 更新表格
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            percentage = (item['minutes'] / total_minutes * 100) if total_minutes > 0 else 0
            hours = item['minutes'] // 60
            mins = item['minutes'] % 60
            
            self.table.setItem(row, 0, QTableWidgetItem(item['name']))
            self.table.setItem(row, 1, QTableWidgetItem(f"{hours}h {mins}m"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{percentage:.1f}%"))
            self.table.setItem(row, 3, QTableWidgetItem(str(item['task_count'])))

        # 更新图表
        self._draw_pie_chart(data, total_minutes)
        self._draw_bar_chart(data)

    def _draw_pie_chart(self, data, total_minutes):
        """绘制环形饼图"""
        self.pie_chart.removeAllSeries()
        
        if not data or total_minutes == 0:
            return
        
        series = QPieSeries()
        
        for idx, item in enumerate(data):
            percentage = item['minutes'] / total_minutes * 100
            hours = item['minutes'] // 60
            mins = item['minutes'] % 60
            color = ACCENT_COLORS[idx % len(ACCENT_COLORS)]
            
            # 创建切片
            pie_slice = series.append(f"{item['name']} ({percentage:.1f}%)", item['minutes'])
            pie_slice.setLabelVisible(False)  # 隐藏标签，使用图例
            pie_slice.setBrush(QColor(color))
            pie_slice.setPen(QPen(QColor("white"), 2))
            
            # 存储元数据到切片对象
            pie_slice.setProperty("hover_label", f"{item['name']}\n{hours}h {mins}m ({percentage:.1f}%)")
            
            # 悬停效果
            pie_slice.hovered.connect(self._on_pie_slice_hovered)
        
        # 设置为甜甜圈样式
        series.setHoleSize(0.45)
        self.pie_chart.addSeries(series)
        
        # 配置图例
        self.pie_chart.legend().setVisible(True)
        self.pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        self.pie_chart.legend().setFont(QFont("Microsoft YaHei", 9))
        self.pie_chart.setBackgroundVisible(False)
    
    def _on_pie_slice_hovered(self, state):
        """饼图切片悬停效果"""
        pie_slice = self.sender()
        if not pie_slice:
            return
        
        if state:
            pie_slice.setExploded(True)
            pie_slice.setExplodeDistanceFactor(0.08)
            pie_slice.setLabelVisible(True)
            hover_label = pie_slice.property("hover_label")
            if hover_label:
                pie_slice.setLabel(hover_label)
        else:
            pie_slice.setExploded(False)
            pie_slice.setLabelVisible(False)

    def _draw_bar_chart(self, data):
        """绘制水平柱状图 - Top 5"""
        # 清除旧数据
        self.bar_chart.removeAllSeries()
        for axis in self.bar_chart.axes():
            self.bar_chart.removeAxis(axis)
        
        if not data:
            return
        
        # 取 Top 5 数据，升序排列使最大的在顶部
        top_data = sorted(data[:5], key=lambda x: x['minutes'])
        
        categories = []
        bar_set = QBarSet("时长")
        bar_set.setColor(QColor("#00897B"))  # 统一专业商务绿
        
        for item in top_data:
            categories.append(item['name'])
            bar_set.append(item['minutes'])
        
        # 使用水平柱状图
        series = QHorizontalBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)
        series.setLabelsFormat("@value min")
        series.setLabelsPosition(QHorizontalBarSeries.LabelsOutsideEnd)
        
        # 柱状图悬停效果 - 使用 partial 替代 lambda
        bar_set.hovered.connect(partial(self._on_bar_hovered, bar_set=bar_set, data=top_data))
        
        self.bar_chart.addSeries(series)
        
        # 配置坐标轴
        max_val = max(item['minutes'] for item in top_data) if top_data else 100
        
        axis_x = QValueAxis()
        axis_x.setRange(0, max_val * 1.3)  # 留出标签空间
        axis_x.setLabelFormat("%d")
        axis_x.setGridLineVisible(True)
        axis_x.setGridLineColor(QColor("#EEEEEE"))
        
        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        axis_y.setLabelsFont(QFont("Microsoft YaHei", 10))
        
        self.bar_chart.addAxis(axis_x, Qt.AlignBottom)
        self.bar_chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        
        self.bar_chart.legend().setVisible(False)
        self.bar_chart.setBackgroundVisible(False)
    
    def _on_bar_hovered(self, state, idx, bar_set, data):
        """柱状图条悬停效果"""
        if state and 0 <= idx < len(data):
            # 高亮当前条
            bar_set.setColor(QColor("#00695C"))  # 深色高亮
            # 设置 tooltip
            item = data[idx]
            hours = item['minutes'] // 60
            mins = item['minutes'] % 60
            self.bar_chart_view.setToolTip(
                f"{item['name']}\n时长: {hours}h {mins}m\n任务数: {item['task_count']}")
        else:
            bar_set.setColor(QColor("#00897B"))  # 恢复原色
            self.bar_chart_view.setToolTip("")
