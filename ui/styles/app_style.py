#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用全局样式表 (Theme Manager System)
支持多主题切换：默认、深色、粉色、护眼
"""

import os
from PySide6.QtCore import QObject, Signal

# ============ 1. 主题定义 (Theme Definitions) ============

class Theme:
    """主题数据结构"""
    def __init__(self, name, colors):
        self.name = name
        self.colors = colors

    def __getitem__(self, key):
        return self.colors.get(key, '#FF0000') # 缺省红

# 预设主题库
PRESET_THEMES = {
    "default": {
        # 基础底色
        'bg_main': '#F4F7F9',       # 主窗口背景
        'bg_card': '#FFFFFF',       # 卡片/容器背景
        'bg_input': '#FFFFFF',      # 输入框背景
        'bg_item': '#FFFFFF',       # 列表项背景
        'bg_hover': '#F8F9FA',      # 悬停背景
        
        # 文字颜色
        'text_primary': '#333333',
        'text_secondary': '#6c757d',
        'text_light': '#adb5bd',
        'text_inverse': '#FFFFFF',  # 反色文字（用于深色按钮）
        
        # 品牌色
        'primary': '#1A73E8',       # 主色
        'primary_hover': '#1557B0', 
        'primary_light': '#4A90E2', # 浅主色 (选中态等)
        'accent': '#1A73E8',        # 强调色
        
        # 边框
        'border': '#dee2e6',
        'border_light': '#e9ecef',
        'border_focus': '#1A73E8', # 聚焦边框
        
        # 图表配色
        'chart_colors': [
            '#1A73E8', '#A333CB', '#33C4AF', '#FBC02D', '#FF7043',
            '#81C784', '#29B6F6', '#AB47BC', '#EF5350', '#78909C'
        ],
        
        # 功能色
        'success': '#28a745',
        'danger': '#dc3545',
        'warning': '#ffc107'
    },
    
    "dark": { # Professional Dark
        'bg_main': '#202124',
        'bg_card': '#292A2D',
        'bg_input': '#303134',
        'bg_item': '#292A2D',
        'bg_hover': '#3C4043',
        
        'text_primary': '#E8EAED',
        'text_secondary': '#9AA0A6',
        'text_light': '#5F6368',
        'text_inverse': '#202124',
        
        'primary': '#8AB4F8',       # Google Blue (Light)
        'primary_hover': '#AECBFA',
        'primary_light': '#3C4043', # 选中态 (Dark Grey)
        'accent': '#8AB4F8',
        
        'border': '#3C4043',
        'border_light': '#5F6368',
        'border_focus': '#8AB4F8',
        
        'chart_colors': [
            '#8AB4F8', '#C58AF9', '#66BB6A', '#FDD663', '#FF8A65',
            '#4285F4', '#EA4335', '#FBBC04', '#34A853', '#F06292'
        ],
        
        'success': '#81C995',
        'danger': '#F28B82',
        'warning': '#FDD663'
    },
    
    "pink": { # Female / Warm Pink
        'bg_main': '#FFF0F5',       # 薰衣草/淡粉
        'bg_card': '#FFFFFF',
        'bg_input': '#FFFFFF',
        'bg_item': '#FFF5F7',
        'bg_hover': '#FFE4E1',
        
        'text_primary': '#5D4037',  # 暖棕色文字
        'text_secondary': '#8D6E63',
        'text_light': '#BCAAA4',
        'text_inverse': '#FFFFFF',
        
        'primary': '#FF80AB',       # 粉色
        'primary_hover': '#F06292',
        'primary_light': '#FFCDD2',
        'accent': '#FF4081',
        
        'border': '#F8BBD0',
        'border_light': '#FFCDD2',
        'border_focus': '#FF80AB',
        
        'chart_colors': [
            '#FF80AB', '#BA68C8', '#4DD0E1', '#FFD54F', '#FF8A65',
            '#AED581', '#7986CB', '#9575CD', '#F06292', '#4DB6AC'
        ],
        
        'success': '#A5D6A7',
        'danger': '#EF9A9A',
        'warning': '#FFE082'
    },
    
    "eyecare": { # Eye Care (Soft Sage/Paper)
        'bg_main': '#F2F5F0',       # 极浅豆沙绿 (更柔和，低饱和)
        'bg_card': '#FFFFFF',       # 保持白色以维持对比度
        'bg_input': '#F7F9F6',      # 极浅绿灰
        'bg_item': '#FFFFFF',
        'bg_hover': '#E2E7DF',      # 悬停灰绿
        
        'text_primary': '#3E493C',  # 深橄榄灰 (比纯黑柔和)
        'text_secondary': '#6C7A68',
        'text_light': '#9CA699',
        'text_inverse': '#FFFFFF',
        
        'primary': '#7CB342',       # 橄榄绿/草绿 (比亮绿更沉稳)
        'primary_hover': '#689F38',
        'primary_light': '#A5D6A7',
        'accent': '#8BC34A',
        
        'border': '#DCE0D9',
        'border_light': '#F2F5F0',
        'border_focus': '#7CB342',
        
        'chart_colors': [
            '#7CB342', '#8BC34A', '#AED581', '#C0CA33', '#FDD835',
            '#FFB74D', '#8D6E63', '#78909C', '#26A69A', '#66BB6A'
        ],
        
        'success': '#558B2F',
        'danger': '#E57373',        
        'warning': '#FFD54F'
    }
}

# ============ 2. 主题管理器 (Theme Manager) ============

class ThemeManager(QObject):
    """全局主题管理器单例"""
    theme_changed = Signal(object) # 发射新的 Theme 对象
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance.current_theme_name = "default"
            cls._instance.current_tokens = PRESET_THEMES["default"]
        return cls._instance

    def set_theme(self, theme_name):
        """切换主题"""
        if theme_name not in PRESET_THEMES:
            theme_name = "default"
            
        self.current_theme_name = theme_name
        self.current_tokens = PRESET_THEMES[theme_name]
        
        # 广播变更信号
        theme_obj = Theme(theme_name, self.current_tokens)
        self.theme_changed.emit(theme_obj)
        
    def get_current_theme(self) -> Theme:
        """获取当前主题对象"""
        return Theme(self.current_theme_name, self.current_tokens)
        
    def get_token(self, key):
        """获取当前主题的颜色 Token"""
        return self.current_tokens.get(key, '#000000')

# 全局实例
theme_manager = ThemeManager()


# ============ 跨平台字体支持 ============

import sys
from PySide6.QtGui import QFont, QFontDatabase

def _detect_cjk_font() -> str:
    """检测当前平台可用的 CJK 字体名称"""
    # 按平台优先级排列的候选字体
    if sys.platform == 'win32':
        candidates = ["Microsoft YaHei UI", "Microsoft YaHei", "SimHei"]
    elif sys.platform == 'darwin':
        candidates = ["PingFang SC", "Hiragino Sans GB", "STHeiti"]
    else:
        candidates = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Droid Sans Fallback"]
    
    available = QFontDatabase.families()
    for font in candidates:
        if font in available:
            return font
    
    # 兜底：返回系统默认 sans-serif
    return "sans-serif"

# 延迟初始化的全局字体名（首次使用时检测）
_cjk_font_name = None

def get_cjk_font_name() -> str:
    """获取当前平台的 CJK 字体名称（缓存结果）"""
    global _cjk_font_name
    if _cjk_font_name is None:
        _cjk_font_name = _detect_cjk_font()
    return _cjk_font_name

def get_cjk_font(size: int = 9, weight: int = -1) -> QFont:
    """获取跨平台 CJK QFont 实例
    
    Args:
        size: 字号
        weight: 字重，-1 为默认
    """
    font = QFont(get_cjk_font_name(), size)
    if weight >= 0:
        font.setWeight(QFont.Weight(weight))
    return font

# CSS 样式中使用的跨平台字体声明（回退链）
CJK_FONT_FAMILY = '"Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", sans-serif'


# ============ 3. 动态样式生成器 (Dynamic Style Generators) ============


def get_app_style() -> str:
    """获取主窗口样式 (基于当前主题)"""
    t = theme_manager.current_tokens
    
    return f'''
    QMainWindow {{
        background-color: {t['bg_main']};
    }}
    QWidget {{
        font-family: {CJK_FONT_FAMILY};
        color: {t['text_primary']};
    }}
    
    /* 顶级 Tab 系统 */
    QTabWidget::pane {{
        border-top: 1px solid {t['border']};
        background-color: {t['bg_card']};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {t['text_secondary']};
        padding: 12px 25px;
        font-size: 14px;
        font-weight: 500;
        border-bottom: 2px solid transparent;
        margin-right: 5px;
    }}
    QTabBar::tab:hover {{
        color: {t['primary_hover']};
    }}
    QTabBar::tab:selected {{
        color: {t['primary']};
        font-weight: bold;
        border-bottom: 2px solid {t['primary']};
    }}

    /* 卡片容器 */
    QGroupBox {{
        background-color: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        margin-top: 25px;
        padding-top: 15px;
        font-weight: bold;
        color: {t['text_primary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 15px;
        padding: 0 10px;
        color: {t['text_primary']};
    }}

    /* 表格 */
    QTableWidget {{
        background-color: {t['bg_card']};
        border: none;
        gridline-color: {t['border_light']};
        selection-background-color: {t['primary']}20; /* 20% opacity */
        selection-color: {t['primary']};
        color: {t['text_primary']};
    }}
    QHeaderView::section {{
        background-color: {t['bg_card']};
        color: {t['text_secondary']};
        padding: 10px;
        border: none;
        border-bottom: 1px solid {t['border']};
        font-weight: bold;
    }}
    QTableWidget::item {{
        border-bottom: 1px solid {t['border_light']};
    }}
    QTableWidget::item:selected {{
        background-color: {t['primary']}20;
    }}

    /* 滚动条 */
    QScrollBar:vertical {{
        background: {t['bg_main']};
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['text_light']};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['text_secondary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

    /* 输入框 */
    QLineEdit, QDateEdit, QComboBox {{
        background-color: {t['bg_input']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 6px 10px;
        color: {t['text_primary']};
    }}
    QLineEdit:focus, QDateEdit:focus, QComboBox:focus {{
        border: 1px solid {t['border_focus']};
    }}
    
    /* 按钮 */
    QPushButton {{
        background-color: {t['bg_card']};
        border: 1px solid {t['border']};
        color: {t['text_primary']};
        padding: 5px 12px;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {t['bg_hover']};
        border-color: {t['primary']};
        color: {t['primary']};
    }}
    
    QDialog {{
        background-color: {t['bg_main']};
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {t['bg_card']};
        border: 1px solid {t['border']};
        selection-background-color: {t['bg_hover']};
        selection-color: {t['primary']};
        color: {t['text_primary']};
        outline: none;
    }}

    /* 菜单栏 & 弹出菜单 */
    QMenuBar {{
        background-color: {t['bg_main']};
        color: {t['text_primary']};
    }}
    QMenuBar::item:selected {{
        background-color: {t['bg_hover']};
    }}
    QMenu {{
        background-color: {t['bg_card']};
        color: {t['text_primary']};
        border: 1px solid {t['border']}; 
    }}
    QMenu::item {{
        background-color: transparent;
        padding: 6px 20px;
    }}
    QMenu::item:selected {{
        background-color: {t['bg_hover']};
        color: {t['primary']};
    }}

    /* 时间/数字输入框 */
    QAbstractSpinBox, QTimeEdit, QDateEdit, QDoubleSpinBox {{
        background-color: {t['bg_input']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 6px 10px;
    }}
    QAbstractSpinBox:focus, QTimeEdit:focus, QDateEdit:focus {{
        border: 1px solid {t['border_focus']};
    }}
    QAbstractSpinBox::up-button, QTimeEdit::up-button, QDateEdit::up-button {{
        border-left: 1px solid {t['border']};
        background: {t['bg_input']};
        width: 16px; 
    }}
    QAbstractSpinBox::down-button, QTimeEdit::down-button, QDateEdit::down-button {{
        border-left: 1px solid {t['border']};
        background: {t['bg_input']};
        width: 16px;
    }}
    QAbstractSpinBox::up-arrow, QTimeEdit::up-arrow, QDateEdit::up-arrow {{
        width: 8px; height: 8px;
    }}
    '''

def get_activity_button_style(color: str, darken_color: str) -> str:
    """获取活动按钮样式 (使用 Activity 自身颜色，但适配文字颜色)"""
    t = theme_manager.current_tokens
    is_dark = theme_manager.current_theme_name in ["dark", "male"]
    
    if is_dark:
        # 深色模式：使用幽灵按钮/轮廓风格，避免大面积亮色
        return f'''
            QPushButton {{
                background-color: {color}1A; /* 10% opacity */
                color: {color}; 
                border: 1px solid {color};
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 6px;
                min-height: 34px;
            }}
            QPushButton:hover {{
                background-color: {color}33; /* 20% opacity */
                border: 1px solid {color};
            }}
            QPushButton:pressed {{
                background-color: {color}4D; /* 30% opacity */
                padding-left: 9px;
                padding-top: 9px;
            }}
        '''
    else:
        # 浅色模式：保留实心风格
        return f'''
            QPushButton {{
                background-color: {color};
                color: white; 
                border: none;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 500;
                border-radius: 6px;
                min-height: 34px;
            }}
            QPushButton:hover {{
                background-color: {darken_color};
            }}
            QPushButton:pressed {{
                background-color: {color};
                padding-left: 9px;
                padding-top: 9px;
            }}
        '''

def get_running_activity_style(color: str) -> str:
    """运行中活动样式"""
    t = theme_manager.current_tokens
    return f'''
        RunningActivityWidget {{
            background-color: {color}20;
            border: 2px solid {color};
            border-radius: 8px;
            padding: 8px;
            margin: 4px;
        }}
        /* 强制内部 Label 颜色适配 */
        QLabel {{
            color: {t['text_primary']};
        }}
    '''

def get_log_item_style(color: str) -> str:
    """日志项样式"""
    t = theme_manager.current_tokens
    return f'''
        QWidget {{
            background-color: {t['bg_item']};
            border: 1px solid {t['border']};
            border-left: 4px solid {color};
            margin: 4px 0;
            padding: 12px 16px;
            border-radius: 6px;
        }}
        QWidget:hover {{
            background-color: {t['bg_hover']};
            border-color: {t['primary']};
            border-left: 4px solid {color};
        }}
        QLabel {{
            color: {t['text_primary']};
        }}
    '''
    
def get_control_button_style() -> str:
    """控制面板按钮样式"""
    t = theme_manager.current_tokens
    # 在深色模式下，普通按钮也需要是深色背景
    return f'''
        QPushButton {{
            background-color: {t['bg_input']};
            color: {t['text_primary']};
            border: 1px solid {t['border']};
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
        }}
        QPushButton:hover {{
            background-color: {t['bg_hover']};
            border-color: {t['primary']};
        }}
    '''

# 导出静态对象以兼容旧代码 imports
APP_STYLE = get_app_style()