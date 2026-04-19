#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自绘图表组件 - 使用 QPainter 替代不稳定的 Qt Charts
避免 Qt Charts 模块在创建 QBarSet/QPieSeries 时触发的 access violation 崩溃
"""

import math
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QFontMetrics, QLinearGradient, QPainterPath

from ui.styles.app_style import theme_manager, get_cjk_font

class PieChartWidget(QWidget):
    """使用 QPainter 绘制的甜甜圈图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # [(name, color, value), ...]
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)
        self.hovered_index = -1
        self._slice_angles = []  # 存储每个扇形的角度范围
        self.title = "当日分布"
        
        # 监听主题变更自动重绘
        theme_manager.theme_changed.connect(lambda t: self.update())
        
    def set_data(self, data):
        """设置数据并重绘
        Args:
            data: [(name, color, value), ...]
        """
        self.data = data if data else []
        self._calculate_slices()
        self.update()
        
    def set_title(self, title):
        """设置标题"""
        self.title = title
        self.update()
        
    def _calculate_slices(self):
        """计算每个扇形的角度范围"""
        self._slice_angles = []
        if not self.data:
            return
            
        total = sum(item[2] for item in self.data)
        if total <= 0:
            return
            
        current_angle = 90 # 从 12 点钟方向开始 (Qt 默认是 3 点钟，需要 +90 度)
        for item in self.data:
            span = -(item[2] / total) * 360 # 顺时针只是负角度
            self._slice_angles.append((current_angle, span))
            current_angle += span
            
    def paintEvent(self, event):
        """绘制甜甜圈图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 获取当前主题 Token
        t = theme_manager.current_tokens
        chart_colors = t['chart_colors']
        
        # 背景透明
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        
        # 绘制标题
        title_font = get_cjk_font(12, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(t['text_primary']))
        title_rect = QRectF(0, 10, self.width(), 30)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        if not self.data or not self._slice_angles:
            # 无数据时显示灰色圆环
            painter.setPen(QPen(QColor(t['border']), 15))
            margin = 60
            size = min(self.width(), self.height()) - margin * 2
            rect = QRectF((self.width() - size)/2, (self.height() - size)/2, size, size)
            painter.drawEllipse(rect)
            
            painter.setFont(get_cjk_font(10))
            painter.setPen(QColor(t['text_secondary']))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无数据")
            return
        
        # 计算绘图区域
        margin = 60
        chart_top = 50
        available_width = self.width() - margin * 2
        available_height = self.height() - chart_top - margin
        size = min(available_width, available_height)
        
        center = QPointF(self.width() / 2, chart_top + available_height / 2)
        outer_radius = size / 2
        inner_radius = outer_radius * 0.6 # 甜甜圈孔径
        
        total = sum(item[2] for item in self.data)
        
        # 绘制扇形
        for idx, (item, (start_angle, span_angle)) in enumerate(zip(self.data, self._slice_angles)):
            name, color, value = item
            
            # 处理颜色
            if not color or not color.startswith('#'):
                color = chart_colors[idx % len(chart_colors)]
            base_color = QColor(color)
            
            # 悬停效果：轻微放大
            is_hovered = (idx == self.hovered_index)
            draw_outer_radius = outer_radius * 1.05 if is_hovered else outer_radius
            draw_inner_radius = inner_radius # 内部半径不变
            
            # 使用 QPainterPath 构建扇形
            path = self._create_donut_slice_path(center, draw_inner_radius, draw_outer_radius, start_angle, span_angle)
            
            # 渐变填充
            gradient = QColor(base_color)
            if is_hovered:
                gradient = gradient.lighter(110)
                
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)
            
            # --- 标签绘制优化 ---
            percentage = (value / total * 100) if total > 0 else 0
            if percentage >= 3: # 只有大于3%才显示标签
                # 计算标签位置 (扇形中心线)
                mid_angle_rad = math.radians(start_angle + span_angle / 2)
                
                # 标签中心点 (根据是否悬停稍微往外一点)
                label_dist = draw_outer_radius + 20
                label_x = center.x() + label_dist * math.cos(mid_angle_rad)
                label_y = center.y() - label_dist * math.sin(mid_angle_rad) # Y轴反向
                
                # 绘制连接线
                line_start_x = center.x() + draw_outer_radius * 0.95 * math.cos(mid_angle_rad)
                line_start_y = center.y() - draw_outer_radius * 0.95 * math.sin(mid_angle_rad)
                
                painter.setPen(QPen(QColor(t['border']), 1))
                painter.drawLine(QPointF(line_start_x, line_start_y), QPointF(label_x, label_y))
                
                # 绘制文字
                label_font = get_cjk_font(9)
                if is_hovered:
                    label_font.setBold(True)
                painter.setFont(label_font)
                painter.setPen(QColor(t['text_primary']))
                
                label_text = f"{percentage:.1f}%"
                fm = QFontMetrics(label_font)
                text_rect = fm.boundingRect(label_text)
                
                # 调整文字位置，避免覆盖连线端点
                text_x = label_x - text_rect.width() / 2
                text_y = label_y - text_rect.height() / 2
                
                # 背景以便阅读
                bg_rect = QRectF(text_x - 2, text_y - 1, text_rect.width() + 4, text_rect.height() + 2)
                
                # 使用主题相关的半透明背景
                bg_color = QColor(t['bg_card'])
                bg_color.setAlpha(200)
                painter.setBrush(QBrush(bg_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg_rect, 2, 2)
                
                painter.setPen(QColor(t['text_primary']))
                painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, label_text)
                
        # 绘制中心文字 (总时间或悬停项)
        painter.setFont(get_cjk_font(10, QFont.Weight.Bold))
        painter.setPen(QColor(t['text_secondary']))
        
        center_text = f"Total\n{int(total/60/60)}h{int(total/60)%60}m"
        
        if self.hovered_index >= 0 and self.hovered_index < len(self.data):
             item = self.data[self.hovered_index]
             center_text = f"{item[0]}\n{item[2]//60} min"
             
        # 多行文字绘制
        lines = center_text.split('\n')
        line_height = painter.fontMetrics().height()
        total_height = len(lines) * line_height
        start_y = center.y() - total_height / 2 + line_height / 2 + 2 # 微调
        
        for i, line in enumerate(lines):
            rect = QRectF(center.x() - inner_radius, start_y + i * line_height - line_height, inner_radius * 2, line_height)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, line)

    def _create_donut_slice_path(self, center, inner_radius, outer_radius, start_angle, span_angle):
        """构建甜甜圈扇形路径"""
        path = QPainterPath()
        
        # 简单的数学计算端点
        start_rad = math.radians(start_angle)
        
        # 使用 arcTo 更简单
        outer_rect = QRectF(center.x() - outer_radius, center.y() - outer_radius, outer_radius * 2, outer_radius * 2)
        inner_rect = QRectF(center.x() - inner_radius, center.y() - inner_radius, inner_radius * 2, inner_radius * 2)
        
        path.arcMoveTo(outer_rect, start_angle)
        path.arcTo(outer_rect, start_angle, span_angle)
        
        # 连接到内圆 (注意反向画内圆以形成闭合环)
        path.arcTo(inner_rect, start_angle + span_angle, -span_angle)
        
        path.closeSubpath()
        return path
    
    def mouseMoveEvent(self, event):
        """鼠标移动 - 悬停效果"""
        if not self.data or not self._slice_angles:
            return
            
        pos = event.position() if hasattr(event, 'position') else event.pos()
        
        # 重新计算中心和半径
        margin = 60
        chart_top = 50
        available_width = self.width() - margin * 2
        available_height = self.height() - chart_top - margin
        size = min(available_width, available_height)
        
        center = QPointF(self.width() / 2, chart_top + available_height / 2)
        outer_radius = size / 2
        
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()  # Y 轴向上为正
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > outer_radius:
            new_hovered = -1
        else:
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0: angle += 360
            
            new_hovered = -1
            for idx, (start, span) in enumerate(self._slice_angles):
                # 简单方法：计算相对 start 的偏移
                diff = (start - angle) % 360 
                if 0 <= diff <= abs(span):
                    new_hovered = idx
                    break
        
        if new_hovered != self.hovered_index:
            self.hovered_index = new_hovered
            self.update()
            
            # Tooltip
            if new_hovered >= 0:
                item = self.data[new_hovered]
                QToolTip.showText(event.globalPosition().toPoint(), f"{item[0]}: {item[2]//60} min")
            else:
                QToolTip.hideText()
    
    def leaveEvent(self, event):
        self.hovered_index = -1
        self.update()
        QToolTip.hideText()


class BarChartWidget(QWidget):
    """使用 QPainter 绘制的水平柱状图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # [(name, color, value), ...]
        self.setMinimumSize(200, 150)
        self.setMouseTracking(True)
        self.hovered_index = -1
        self._bar_rects = []  # 存储每个柱子的矩形区域
        self.title = "时间统计"
        
        theme_manager.theme_changed.connect(lambda t: self.update())
        
    def set_data(self, data):
        self.data = data if data else []
        self.update()
        
    def set_title(self, title):
        self.title = title
        self.update()
        
    def paintEvent(self, event):
        """绘制柱状图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 主题
        t = theme_manager.current_tokens
        chart_colors = t['chart_colors']
        
        # 背景透明
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        
        # 绘制标题
        title_font = get_cjk_font(12, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(t['text_primary']))
        title_rect = QRectF(0, 10, self.width(), 30)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        if not self.data:
            painter.setFont(get_cjk_font(10))
            painter.setPen(QColor(t['text_secondary']))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无数据")
            return
        
        # 计算布局
        margin_left = 100  # 左边距（放标签）
        margin_right = 40
        margin_top = 50
        margin_bottom = 40 
        
        chart_width = self.width() - margin_left - margin_right
        chart_height = self.height() - margin_top - margin_bottom
        
        num_bars = len(self.data)
        bar_height = min(36, (chart_height - (num_bars - 1) * 8) / num_bars)
        bar_gap = 8
        
        max_val_data = max(item[2] for item in self.data) if self.data else 0
        if max_val_data <= 0: max_val_data = 1
        
        # 向上取整到最近的 60 的倍数
        max_value = math.ceil(max_val_data / 60) * 60 
        if max_value == 0: max_value = 60
        
        # 绘制网格线
        painter.setPen(QPen(QColor(t['border']), 1, Qt.PenStyle.DashLine))
        label_font = get_cjk_font(8)
        painter.setFont(label_font)
        
        grid_count = 5
        for i in range(grid_count + 1):
            x = margin_left + (chart_width / grid_count) * i
            if i > 0:
                painter.setPen(QPen(QColor(t['border']), 1, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(x, margin_top), QPointF(x, margin_top + chart_height))
            
            # 刻度文字
            val = (max_value / grid_count) * i
            minutes = int(val / 60)
            text = f"{minutes}m"
            if minutes >= 60:
                text = f"{minutes/60:.1f}h"
                
            painter.setPen(QColor(t['text_secondary']))
            painter.drawText(QRectF(x - 25, margin_top + chart_height + 5, 50, 20), Qt.AlignmentFlag.AlignCenter, text)
 
        self._bar_rects = []
        name_font = get_cjk_font(9)
        
        for idx, item in enumerate(self.data):
            name, color, value = item
            
            # 柱子颜色
            if not color or not color.startswith('#'):
                color = chart_colors[idx % len(chart_colors)]
            
            base_color = QColor(color)
            
            # 悬停效果
            is_hovered = (idx == self.hovered_index)
            if is_hovered:
                base_color = base_color.lighter(110)
            
            # 计算柱子位置
            y = margin_top + idx * (bar_height + bar_gap)
            bar_width = (value / max_value) * chart_width if max_value > 0 else 0
            bar_width = max(bar_width, 4)
            
            bar_rect = QRectF(margin_left, y, bar_width, bar_height)
            self._bar_rects.append(bar_rect)
            
            # 渐变色填充
            gradient = QLinearGradient(bar_rect.topLeft(), bar_rect.topRight())
            gradient.setColorAt(0, base_color.lighter(120))
            gradient.setColorAt(1, base_color)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_rect, 4, 4)
            
            # 绘制标签（左侧）
            painter.setFont(name_font)
            painter.setPen(QColor(t['text_primary']))
            if is_hovered:
                painter.setPen(QColor(color)) 
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                
            label_rect = QRectF(5, y, margin_left - 10, bar_height)
            fm = QFontMetrics(painter.font())
            display_name = fm.elidedText(name, Qt.TextElideMode.ElideRight, int(margin_left - 15))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, display_name)
            
            # 绘制数值
            value_text = f"{int(value/60)}m"
            value_width = fm.horizontalAdvance(value_text) + 10
            
            if bar_width > value_width + 10:
                # 内部
                painter.setPen(QColor(t['text_inverse']))
                painter.drawText(QRectF(margin_left, y, bar_width - 5, bar_height), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, value_text)
            else:
                # 外部
                painter.setPen(QColor(t['text_secondary']))
                painter.drawText(QRectF(margin_left + bar_width + 5, y, 50, bar_height), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, value_text)
    
    def mouseMoveEvent(self, event):
        if not self.data or not self._bar_rects:
            return
        pos = event.position() if hasattr(event, 'position') else event.pos()
        
        new_hovered = -1
        for idx, rect in enumerate(self._bar_rects):
            extended_rect = QRectF(0, rect.y(), self.width(), rect.height())
            if extended_rect.contains(pos):
                new_hovered = idx
                break
        
        if new_hovered != self.hovered_index:
            self.hovered_index = new_hovered
            self.update()
            
            if new_hovered >= 0:
                item = self.data[new_hovered]
                QToolTip.showText(event.globalPosition().toPoint(), f"{item[0]}: {item[2]//60} min")
            else:
                QToolTip.hideText()
    
    def leaveEvent(self, event):
        self.hovered_index = -1
        self.update()
        QToolTip.hideText()


class ComparisonChartWidget(QWidget):
    """使用 QPainter 绘制的对比柱状图组件（本期 vs 上期）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = [] 
        self.previous_data = [] 
        self.setMinimumSize(300, 250)
        self.setMouseTracking(True)
        self.hovered_index = -1
        self._bar_rects = []
        self.title = "周期对比"
        
        theme_manager.theme_changed.connect(lambda t: self.update())
        
    def set_data(self, current_data, previous_data):
        self.current_data = current_data if current_data else []
        self.previous_data = previous_data if previous_data else []
        self.update()
        
    def set_title(self, title):
        self.title = title
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        t = theme_manager.current_tokens
        
        # 背景透明
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        
        # 1. 绘制标题
        title_font = get_cjk_font(12, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(t['text_primary']))
        title_rect = QRectF(0, 5, self.width(), 30)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        if not self.current_data and not self.previous_data:
            painter.setFont(get_cjk_font(10))
            painter.setPen(QColor(t['text_secondary']))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无对比数据")
            return
        
        # 2. 计算布局参数 (垂直柱状图)
        # 左侧留给 Y轴数值，底部留给 X轴标签
        margin_left = 60
        margin_right = 20
        margin_top = 70 
        margin_bottom = 50 
        
        chart_width = self.width() - margin_left - margin_right
        chart_height = self.height() - margin_top - margin_bottom
        
        # 3. 绘制图例 (右上角或顶部居中)
        legend_y = 40
        legend_font = get_cjk_font(9)
        painter.setFont(legend_font)
        
        color_current = QColor(t['primary'])
        color_previous = QColor(t['text_light']) 
        if theme_manager.current_theme_name == 'dark':
             color_previous = QColor('#888888') 
        
        # 计算图例总宽度以居中
        legend_w = 150
        start_x = (self.width() - legend_w) / 2
        
        # 本期 图例
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color_current))
        painter.drawRoundedRect(QRectF(start_x, legend_y, 14, 14), 4, 4)
        painter.setPen(QColor(t['text_primary']))
        painter.drawText(QRectF(start_x + 20, legend_y - 1, 40, 16), Qt.AlignmentFlag.AlignLeft, "本期")
        
        # 上期 图例
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color_previous))
        painter.drawRoundedRect(QRectF(start_x + 80, legend_y, 14, 14), 4, 4)
        painter.setPen(QColor(t['text_primary']))
        painter.drawText(QRectF(start_x + 100, legend_y - 1, 40, 16), Qt.AlignmentFlag.AlignLeft, "上期")
        
        # 4. 数据处理
        current_dict = {name: value for name, value in self.current_data}
        previous_dict = {name: value for name, value in self.previous_data}
        all_names = set(current_dict.keys()) | set(previous_dict.keys())
        
        # 排序：本期时长倒序
        sorted_names = sorted(all_names, key=lambda n: (current_dict.get(n, 0), previous_dict.get(n, 0)), reverse=True)
        # 限制数量，防止X轴太挤
        if len(sorted_names) > 8:
             sorted_names = sorted_names[:8]
             
        if not sorted_names:
            return
            
        num_items = len(sorted_names)
        
        # 计算Y轴最大值
        all_values = list(current_dict.values()) + list(previous_dict.values())
        max_val_data = max(all_values) if all_values else 0
        if max_val_data <= 0: max_val_data = 1
        
        # 计算刻度 (nice ticks)
        tick_interval = max_val_data / 5
        if tick_interval < 60: nice_tick = 60
        elif tick_interval < 300: nice_tick = 300 
        elif tick_interval < 600: nice_tick = 600
        elif tick_interval < 1800: nice_tick = 1800
        elif tick_interval < 3600: nice_tick = 3600
        else: nice_tick = math.ceil(tick_interval / 3600) * 3600
        max_limit = nice_tick * 5
        
        # 5. 绘制网格线与Y轴刻度 (水平线)
        painter.setPen(QPen(QColor(t['border']), 1, Qt.PenStyle.DotLine))
        painter.setFont(get_cjk_font(8))
        
        grid_count = 5
        for i in range(grid_count + 1):
            y = margin_top + chart_height - (chart_height / grid_count) * i # 从下往上画
            val = (max_limit / grid_count) * i
            
            # 网格线
            if i > 0:
                painter.setPen(QPen(QColor(t['border']), 1, Qt.PenStyle.DotLine))
                painter.drawLine(QPointF(margin_left, y), QPointF(margin_left + chart_width, y))
            
            # Y轴文字
            if val < 60: text = "0" if val == 0 else f"{int(val)}s"
            elif val < 3600: text = f"{int(val/60)}m"
            else: text = f"{val/3600:.1f}h"
            
            painter.setPen(QColor(t['text_secondary']))
            # 文字右对齐绘制在左边距内
            painter.drawText(QRectF(5, y - 10, margin_left - 10, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        
        # 6. 绘制柱子 (垂直)
        self._bar_rects = []
        name_font = get_cjk_font(9)
        painter.setFont(name_font)
        
        # 每个组(item)在X轴上的宽度
        group_width = chart_width / num_items
        
        # 柱子宽度：组宽的 60%
        # 每个组有2个柱子(本期/上期)，加间隙
        # 设 bar_width 为组宽的 25%
        bar_width = min(40, group_width * 0.35) 
        gap = 4 # 两个柱子之间的间隙
        
        group_inner_width = bar_width * 2 + gap
        start_offset_x = (group_width - group_inner_width) / 2 # 组内居中
        
        for idx, name in enumerate(sorted_names):
            current_value = current_dict.get(name, 0)
            previous_value = previous_dict.get(name, 0)
            
            group_x = margin_left + idx * group_width
            
            # 计算高度 (注意Y轴向下增长，所以y坐标是 margin_top + chart_height - bar_height)
            h_curr = (current_value / max_limit) * chart_height
            h_prev = (previous_value / max_limit) * chart_height
            
            # 最小高度保证可见
            if current_value > 0: h_curr = max(h_curr, 2)
            if previous_value > 0: h_prev = max(h_prev, 2)
            
            # 本期柱子 (左)
            x_curr = group_x + start_offset_x
            y_curr = margin_top + chart_height - h_curr
            rect_curr = QRectF(x_curr, y_curr, bar_width, h_curr)
            
            # 上期柱子 (右)
            x_prev = x_curr + bar_width + gap
            y_prev = margin_top + chart_height - h_prev
            rect_prev = QRectF(x_prev, y_prev, bar_width, h_prev)
            
            # 悬停颜色高亮
            c1, c2 = color_current, color_previous
            is_hovered = (idx == self.hovered_index)
            if is_hovered:
                c1, c2 = c1.lighter(120), c2.lighter(120)
                
            # 绘制 本期
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(c1))
            painter.drawRoundedRect(rect_curr, 4, 4)
            
            # 绘制 上期
            painter.setBrush(QBrush(c2))
            painter.drawRoundedRect(rect_prev, 4, 4)
            
            # 记录交互区域 (整列)
            col_rect = QRectF(group_x, margin_top, group_width, chart_height)
            self._bar_rects.append((col_rect, name, current_value, previous_value))
            
            # 绘制 X轴标签 (居中)
            painter.setPen(QColor(t['text_primary']))
            if is_hovered:
                 f = painter.font(); f.setBold(True); painter.setFont(f)
            else:
                 f = painter.font(); f.setBold(False); painter.setFont(f)
            
            label_rect = QRectF(group_x, margin_top + chart_height + 5, group_width, 20)
            fm = QFontMetrics(painter.font())
            elided = fm.elidedText(name, Qt.TextElideMode.ElideMiddle, int(group_width))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, elided)
            
            # 数值悬停显示 (在柱子上方)
            if is_hovered:
                painter.setFont(get_cjk_font(8))
                painter.setPen(QColor(t['text_primary']))
                
                # 本期数值
                if current_value > 0:
                    v_text = f"{int(current_value//60)}m"
                    painter.drawText(QRectF(rect_curr.x()-10, rect_curr.y()-20, bar_width+20, 20), 
                                     Qt.AlignmentFlag.AlignCenter, v_text)
                # 上期数值
                if previous_value > 0:
                    painter.setPen(QColor(t['text_secondary']))
                    v_text = f"{int(previous_value//60)}m"
                    painter.drawText(QRectF(rect_prev.x()-10, rect_prev.y()-20, bar_width+20, 20), 
                                     Qt.AlignmentFlag.AlignCenter, v_text)

