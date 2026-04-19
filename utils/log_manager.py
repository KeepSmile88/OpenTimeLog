#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理器
提供完整的日志系统，包括：
- 应用程序日志
- 崩溃日志
- 未捕获异常日志
- Qt/C++ 层面错误日志
- 日志轮转管理
"""

import os
import sys
import logging
import platform
import traceback
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path


class LogManager:
    """日志管理器单例"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if LogManager._initialized:
            return
        LogManager._initialized = True
        
        self.app_name = "aTimeLogPro"
        self.log_dir = self._get_log_directory()
        self._setup_faulthandler()  # 必须最先初始化
        self._setup_logging()
        self._setup_exception_hooks()
        self._setup_qt_message_handler()
    
    def _setup_faulthandler(self):
        """设置 faulthandler 捕获段错误等致命崩溃"""
        import faulthandler
        
        # 创建专门的段错误日志文件
        self.fault_log_path = self.log_dir / "segfault.log"
        try:
            self._fault_file = open(self.fault_log_path, 'a', encoding='utf-8')
            # 写入分隔符
            self._fault_file.write(f"\n{'='*60}\n")
            self._fault_file.write(f"Session started: {datetime.now().isoformat()}\n")
            self._fault_file.write(f"{'='*60}\n")
            self._fault_file.flush()
            
            # 启用 faulthandler，将段错误输出到文件
            faulthandler.enable(file=self._fault_file, all_threads=True)
            
            # 仅在 Unix 系统上注册额外的信号处理 (Windows 不支持 register)
            if platform.system() != "Windows" and hasattr(faulthandler, 'register'):
                try:
                    import signal
                    faulthandler.register(signal.SIGUSR1, file=self._fault_file, all_threads=True)
                except (ValueError, OSError, AttributeError):
                    pass  # 某些信号可能无法注册
        except Exception as e:
            print(f"Warning: Could not setup faulthandler: {e}")
    
    def _get_log_directory(self) -> Path:
        """获取跨平台的日志目录"""
        system = platform.system()
        
        if system == "Windows":
            # Windows: %APPDATA%\aTimeLogPro\logs
            base = Path(os.environ.get("APPDATA", os.path.expanduser("~")))
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/aTimeLogPro/logs
            base = Path.home() / "Library" / "Application Support"
        else:
            # Linux/其他: ~/.local/share/aTimeLogPro/logs
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        
        log_dir = base / self.app_name / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    
    def _setup_logging(self):
        """配置日志系统"""
        # 主应用日志
        self.app_logger = logging.getLogger("app")
        self.app_logger.setLevel(logging.DEBUG)
        
        # 崩溃/异常日志
        self.crash_logger = logging.getLogger("crash")
        self.crash_logger.setLevel(logging.ERROR)
        
        # Qt/C++ 层错误日志
        self.qt_logger = logging.getLogger("qt")
        self.qt_logger.setLevel(logging.WARNING)
        
        # 日志格式
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] [%(threadName)s:%(thread)d] '
            '%(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 应用日志文件 (按大小轮转, 最多5个文件, 每个10MB)
        app_handler = RotatingFileHandler(
            self.log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(detailed_formatter)
        self.app_logger.addHandler(app_handler)
        
        # 崩溃日志文件 (按天轮转, 保留30天)
        crash_handler = TimedRotatingFileHandler(
            self.log_dir / "crash.log",
            when='D',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        crash_handler.setLevel(logging.ERROR)
        crash_handler.setFormatter(detailed_formatter)
        self.crash_logger.addHandler(crash_handler)
        
        # Qt/C++ 日志文件
        qt_handler = RotatingFileHandler(
            self.log_dir / "qt_errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        qt_handler.setLevel(logging.WARNING)
        qt_handler.setFormatter(detailed_formatter)
        self.qt_logger.addHandler(qt_handler)
        
        # 控制台输出 (仅在调试模式)
        if os.environ.get("DEBUG") or "--debug" in sys.argv:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(simple_formatter)
            self.app_logger.addHandler(console_handler)
        
        # 记录启动信息
        self.info(f"=== {self.app_name} 启动 ===")
        self.info(f"Python版本: {sys.version}")
        self.info(f"平台: {platform.platform()}")
        self.info(f"日志目录: {self.log_dir}")
    
    def _setup_exception_hooks(self):
        """设置全局异常钩子"""
        # 主线程未捕获异常
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._global_exception_handler
        
        # 多线程未捕获异常
        self._original_threading_excepthook = getattr(threading, 'excepthook', None)
        threading.excepthook = self._threading_exception_handler
    
    def _setup_qt_message_handler(self):
        """设置 Qt 消息处理器"""
        try:
            from PySide6.QtCore import qInstallMessageHandler, QtMsgType
            
            def qt_message_handler(mode, context, message):
                """处理 Qt 内部消息"""
                if mode == QtMsgType.QtDebugMsg:
                    level = "DEBUG"
                elif mode == QtMsgType.QtInfoMsg:
                    level = "INFO"
                elif mode == QtMsgType.QtWarningMsg:
                    level = "WARNING"
                    self.qt_logger.warning(f"[Qt] {message} (file: {context.file}, line: {context.line})")
                elif mode == QtMsgType.QtCriticalMsg:
                    level = "CRITICAL"
                    self.qt_logger.critical(f"[Qt] {message} (file: {context.file}, line: {context.line})")
                elif mode == QtMsgType.QtFatalMsg:
                    level = "FATAL"
                    self.qt_logger.critical(f"[Qt FATAL] {message} (file: {context.file}, line: {context.line})")
                    # 保存崩溃现场
                    self._save_crash_dump(f"Qt Fatal: {message}")
            
            qInstallMessageHandler(qt_message_handler)
            self.debug("Qt 消息处理器已安装")
        except ImportError:
            self.warning("无法导入 PySide6，Qt 消息处理器未安装")
    
    def _global_exception_handler(self, exc_type, exc_value, exc_tb):
        """全局异常处理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 正常退出
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        
        # 记录崩溃
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.crash_logger.critical(
            f"未捕获异常 (主线程):\n"
            f"类型: {exc_type.__name__}\n"
            f"消息: {exc_value}\n"
            f"堆栈:\n{tb_str}"
        )
        
        # 保存崩溃转储
        self._save_crash_dump(f"{exc_type.__name__}: {exc_value}", tb_str)
        
        # 调用原始处理器
        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_tb)
    
    def _threading_exception_handler(self, args):
        """多线程异常处理器"""
        exc_type = args.exc_type
        exc_value = args.exc_value
        exc_tb = args.exc_traceback
        thread = args.thread
        
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.crash_logger.critical(
            f"未捕获异常 (线程: {thread.name if thread else 'Unknown'}):\n"
            f"类型: {exc_type.__name__}\n"
            f"消息: {exc_value}\n"
            f"堆栈:\n{tb_str}"
        )
        
        # 保存崩溃转储
        self._save_crash_dump(
            f"{exc_type.__name__}: {exc_value} (Thread: {thread.name if thread else 'Unknown'})",
            tb_str
        )
        
        # 调用原始处理器
        if self._original_threading_excepthook:
            self._original_threading_excepthook(args)
    
    def _save_crash_dump(self, error_msg: str, traceback_str: str = ""):
        """保存崩溃转储文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_file = self.log_dir / f"crash_dump_{timestamp}.txt"
        
        try:
            with open(dump_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {self.app_name} 崩溃报告 ===\n")
                f.write(f"时间: {datetime.now().isoformat()}\n")
                f.write(f"Python版本: {sys.version}\n")
                f.write(f"平台: {platform.platform()}\n")
                f.write(f"错误: {error_msg}\n")
                f.write(f"\n=== 堆栈跟踪 ===\n")
                f.write(traceback_str or "无可用堆栈信息\n")
                f.write(f"\n=== 线程信息 ===\n")
                for thread in threading.enumerate():
                    f.write(f"- {thread.name} (ID: {thread.ident}, Daemon: {thread.daemon})\n")
            
            self.app_logger.info(f"崩溃转储已保存: {dump_file}")
        except Exception as e:
            self.app_logger.error(f"保存崩溃转储失败: {e}")
    
    # ========== 便捷日志方法 ==========
    
    def debug(self, msg: str):
        """调试日志"""
        self.app_logger.debug(msg)
    
    def info(self, msg: str):
        """信息日志"""
        self.app_logger.info(msg)
    
    def warning(self, msg: str):
        """警告日志"""
        self.app_logger.warning(msg)
    
    def error(self, msg: str, exc_info: bool = False):
        """错误日志"""
        self.app_logger.error(msg, exc_info=exc_info)
    
    def critical(self, msg: str, exc_info: bool = True):
        """严重错误日志"""
        self.app_logger.critical(msg, exc_info=exc_info)
        self.crash_logger.critical(msg, exc_info=exc_info)
    
    def exception(self, msg: str):
        """记录异常（自动包含堆栈）"""
        self.app_logger.exception(msg)
        self.crash_logger.exception(msg)
    
    def get_log_directory(self) -> Path:
        """获取日志目录路径"""
        return self.log_dir
    
    def shutdown(self):
        """关闭日志系统"""
        self.info(f"=== {self.app_name} 关闭 ===")
        logging.shutdown()
        # 关闭 faulthandler 文件句柄
        if hasattr(self, '_fault_file') and self._fault_file:
            try:
                self._fault_file.close()
            except:
                pass


# 全局日志管理器实例
_log_manager = None

def get_logger() -> LogManager:
    """获取日志管理器实例"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager

# 便捷函数
def debug(msg: str): get_logger().debug(msg)
def info(msg: str): get_logger().info(msg)
def warning(msg: str): get_logger().warning(msg)
def error(msg: str, exc_info: bool = False): get_logger().error(msg, exc_info)
def critical(msg: str): get_logger().critical(msg)
def exception(msg: str): get_logger().exception(msg)
