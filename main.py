# -*- coding: utf-8 -*-
"""
OpenTimeLog - 时间记录器
应用入口文件
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 初始化日志系统（必须在其他模块之前）
from utils.log_manager import get_logger, info, error, exception

logger = get_logger()

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.main_window import TimeLoggerApp


def main():
    """应用入口函数"""
    try:
        info("应用启动中...")
        
        # PySide6 高 DPI 适配新策略
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        
        # 创建并运行应用
        app = TimeLoggerApp(sys.argv)
        info("主窗口已创建")
        
        exit_code = app.exec()
        info(f"应用正常退出，退出码: {exit_code}")
        
        # 关闭日志系统
        logger.shutdown()
        sys.exit(exit_code)
        
    except Exception as e:
        exception(f"应用启动失败: {e}")
        logger.shutdown()
        sys.exit(1)


if __name__ == '__main__':
    main()
