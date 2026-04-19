#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
帮助手册对话框
使用 QWebEngineView 展示精美的 HTML 帮助文档
"""

import os
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon

# 尝试导入 WebEngine，如果未安装则提供备用方案
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    from PySide6.QtWidgets import QTextBrowser


class HelpDialog(QDialog):
    """帮助手册对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenTimeLog - 帮助文档")
        self.setMinimumSize(900, 650)
        self.resize(950, 700)
        
        # 设置窗口图标
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'resources', 'main.ico'
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 设置窗口标志 - 允许最大化和最小化
        self.setWindowFlags(
            Qt.Dialog | 
            Qt.WindowMaximizeButtonHint | 
            Qt.WindowMinimizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 帮助文档路径
        help_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'resources', 'help'
        )
        index_path = os.path.join(help_dir, 'index.html')
        
        if WEBENGINE_AVAILABLE:
            # 使用 WebEngineView 显示帮助文档
            self.web_view = QWebEngineView()
            self.web_view.setUrl(QUrl.fromLocalFile(index_path))
            layout.addWidget(self.web_view)
        else:
            # 备用方案：使用 QTextBrowser
            self.text_browser = QTextBrowser()
            self.text_browser.setOpenExternalLinks(True)
            
            # 读取 HTML 并显示（注意：QTextBrowser 对复杂 HTML/CSS 支持有限）
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.text_browser.setHtml(html_content)
            else:
                self.text_browser.setPlainText(
                    "帮助文档加载失败。\n\n"
                    "请确保 resources/help/index.html 文件存在。\n\n"
                    "如需完整的帮助体验，请安装 PySide6-WebEngine:\n"
                    "pip install PySide6-WebEngine"
                )
            
            layout.addWidget(self.text_browser)
