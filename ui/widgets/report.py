#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成与导出组件
"""

import os
import sys

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QDateEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QColor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.report_analyzer import ReportAnalyzer
from ui.styles.app_style import theme_manager


class ReportWidget(QWidget):
    """报告生成与导出组件"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.update_styles()
        
        # 监听主题变更
        theme_manager.theme_changed.connect(lambda t: self.update_styles())
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 控制面板
        control_group = QWidget()
        control_layout = QHBoxLayout(control_group)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 日期选择
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        
        self.info_labels = []
        
        lbl1 = QLabel("开始日期:")
        self.info_labels.append(lbl1)
        self.start_date = QDateEdit(first_day)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        
        lbl2 = QLabel("结束日期:")
        self.info_labels.append(lbl2)
        self.end_date = QDateEdit(today)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        
        # 按钮
        self.generate_btn = QPushButton("生成报告")
        self.generate_btn.clicked.connect(self.generate_report)
        
        self.export_btn = QPushButton("导出文本")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        
        control_layout.addWidget(lbl1)
        control_layout.addWidget(self.start_date)
        control_layout.addWidget(lbl2)
        control_layout.addWidget(self.end_date)
        control_layout.addWidget(self.generate_btn)
        control_layout.addWidget(self.export_btn)
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # 报告显示区域
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text)
        
        self.setLayout(layout)
        
    def update_styles(self):
        """更新样式"""
        t = theme_manager.current_tokens
        
        # 1. 标签颜色
        for lbl in self.info_labels:
            lbl.setStyleSheet(f"color: {t['text_primary']};")
            
        # 2. 按钮样式
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['primary']};
                color: {t['text_inverse']};
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {t['primary_hover']};
            }}
        """)
        
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['bg_input']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {t['bg_hover']};
                border-color: {t['primary']};
            }}
            QPushButton:disabled {{
                color: {t['text_light']};
                background-color: {t['bg_main']};
            }}
        """)
        
        # 3. 报告文本域样式
        self.report_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['bg_input']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                font-family: Consolas, "Microsoft YaHei", monospace;
                font-size: 13px;
                line-height: 1.5;
            }}
        """)
        
        # 4. 日期选择器样式 (通常由全局样式处理，但这里显式设置以防万一)
        date_style = f"""
            QDateEdit {{
                background-color: {t['bg_input']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                padding: 4px;
                border-radius: 4px;
            }}
        """
        self.start_date.setStyleSheet(date_style)
        self.end_date.setStyleSheet(date_style)

    def generate_report(self):
        """生成报告"""
        start_date = self.start_date.date().toPython()
        end_date = self.end_date.date().toPython()
        
        if start_date > end_date:
            QMessageBox.warning(self, "日期错误", "开始日期不能晚于结束日期")
            return
        
        # 获取数据
        records = self.db_manager.get_analysis_records(start_date, end_date)
        
        if not records:
            self.report_text.setText("所选时间段内没有已完成的记录。")
            self.export_btn.setEnabled(False)
            return
        
        # 分析数据
        groups, total_all = ReportAnalyzer.analyze(records)
        
        # 生成文本
        report_content = ReportAnalyzer.generate_text_report(groups, total_all)
        
        # 添加头部信息
        header = f"aTimeLogPro 统计报告\n日期范围: {start_date} 至 {end_date}\n{'=' * 40}\n\n"
        full_report = header + report_content
        
        self.report_text.setText(full_report)
        self.export_btn.setEnabled(True)
    
    def export_report(self):
        """导出报告"""
        content = self.report_text.toPlainText()
        if not content:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", 
            f"report_{self.start_date.date().toString('yyyyMMdd')}_{self.end_date.date().toString('yyyyMMdd')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(self, "导出成功", f"报告已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"保存文件时出错:\n{str(e)}")
