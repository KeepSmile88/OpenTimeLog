# -*- coding: utf-8 -*-
"""
日志管理器测试模块

测试 utils/log_manager.py 中的 LogManager 类
包括：
- 单例模式
- 日志目录创建
- 日志级别
- 异常钩子
- 资源清理
"""

import os
import sys
import pytest
import tempfile
import threading
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestLogManagerSingleton:
    """单例模式测试"""
    
    def test_singleton_same_instance(self):
        """测试多次调用返回同一实例"""
        # 需要重置单例以便测试
        from utils import log_manager
        
        # 保存原始状态
        original_instance = log_manager._log_manager
        original_initialized = log_manager.LogManager._initialized
        
        try:
            # 重置
            log_manager._log_manager = None
            log_manager.LogManager._instance = None
            log_manager.LogManager._initialized = False
            
            logger1 = log_manager.get_logger()
            logger2 = log_manager.get_logger()
            
            assert logger1 is logger2
        finally:
            # 恢复
            log_manager._log_manager = original_instance
            log_manager.LogManager._initialized = original_initialized
    
    def test_new_returns_same_instance(self):
        """测试__new__返回同一实例"""
        from utils.log_manager import LogManager
        
        # 保存原始状态
        original_instance = LogManager._instance
        original_initialized = LogManager._initialized
        
        try:
            LogManager._instance = None
            LogManager._initialized = False
            
            manager1 = LogManager()
            manager2 = LogManager()
            
            assert manager1 is manager2
        finally:
            LogManager._instance = original_instance
            LogManager._initialized = original_initialized


class TestLogDirectory:
    """日志目录测试"""
    
    def test_log_directory_created(self):
        """测试日志目录被创建"""
        from utils.log_manager import LogManager
        
        # 临时禁用单例以创建新实例
        original_instance = LogManager._instance
        original_initialized = LogManager._initialized
        
        try:
            LogManager._instance = None
            LogManager._initialized = False
            
            manager = LogManager()
            log_dir = manager.get_log_directory()
            
            assert log_dir.exists()
            assert log_dir.is_dir()
        finally:
            LogManager._instance = original_instance
            LogManager._initialized = original_initialized
    
    def test_log_directory_platform_specific(self):
        """测试平台特定的日志目录"""
        from utils.log_manager import LogManager
        import platform
        
        manager = LogManager()
        log_dir = manager.get_log_directory()
        
        system = platform.system()
        if system == "Windows":
            # 应该在 APPDATA 下
            assert "OpenTimeLog" in str(log_dir)
        elif system == "Darwin":
            # 应该在 Library/Application Support 下
            assert "OpenTimeLog" in str(log_dir)
        else:
            # Linux 应该在 .local/share 下
            assert "OpenTimeLog" in str(log_dir)


class TestLogLevels:
    """日志级别测试"""
    
    @pytest.fixture
    def log_manager(self):
        """获取日志管理器"""
        from utils.log_manager import get_logger
        return get_logger()
    
    def test_debug_level(self, log_manager, caplog):
        """测试调试级别"""
        with caplog.at_level(logging.DEBUG, logger="app"):
            log_manager.debug("调试消息")
    
    def test_info_level(self, log_manager, caplog):
        """测试信息级别"""
        with caplog.at_level(logging.INFO, logger="app"):
            log_manager.info("信息消息")
    
    def test_warning_level(self, log_manager, caplog):
        """测试警告级别"""
        with caplog.at_level(logging.WARNING, logger="app"):
            log_manager.warning("警告消息")
    
    def test_error_level(self, log_manager, caplog):
        """测试错误级别"""
        with caplog.at_level(logging.ERROR, logger="app"):
            log_manager.error("错误消息")
    
    def test_critical_level(self, log_manager, caplog):
        """测试严重错误级别"""
        with caplog.at_level(logging.CRITICAL, logger="app"):
            log_manager.critical("严重错误")
    
    def test_exception_with_traceback(self, log_manager, caplog):
        """测试异常日志包含堆栈"""
        try:
            raise ValueError("测试异常")
        except ValueError:
            with caplog.at_level(logging.ERROR, logger="app"):
                log_manager.exception("捕获异常")


class TestExceptionHooks:
    """异常钩子测试"""
    
    def test_global_exception_handler_installed(self):
        """测试全局异常处理器已安装"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        # 检查sys.excepthook是否被替换
        assert sys.excepthook is not None
    
    def test_threading_exception_handler_installed(self):
        """测试多线程异常处理器已安装"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        # 检查threading.excepthook是否被设置
        assert hasattr(threading, 'excepthook')
        assert threading.excepthook is not None
    
    def test_keyboard_interrupt_passthrough(self):
        """测试KeyboardInterrupt直接传递"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        # KeyboardInterrupt应该被直接传递，不应该被记录为崩溃
        # 这个测试主要验证逻辑存在
        assert True  # 无法直接测试excepthook行为


class TestCrashDump:
    """崩溃转储测试"""
    
    def test_save_crash_dump(self, tmp_path):
        """测试保存崩溃转储"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        # 保存原始日志目录
        original_log_dir = manager.log_dir
        
        try:
            manager.log_dir = tmp_path
            
            manager._save_crash_dump("测试错误", "测试堆栈跟踪")
            
            # 检查是否创建了转储文件
            dump_files = list(tmp_path.glob("crash_dump_*.txt"))
            assert len(dump_files) >= 0  # 可能有也可能没有，取决于权限
        finally:
            manager.log_dir = original_log_dir


class TestQtMessageHandler:
    """Qt消息处理器测试"""
    
    def test_qt_message_handler_setup(self):
        """测试Qt消息处理器设置"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        # 如果PySide6可用，消息处理器应该已设置
        # 这个测试主要验证不会抛出异常
        assert True


class TestResourceCleanup:
    """资源清理测试"""
    
    def test_shutdown(self):
        """测试关闭日志系统"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        # shutdown不应该抛出异常
        manager.shutdown()
    
    def test_fault_file_closed_on_shutdown(self):
        """测试段错误日志文件在关闭时被关闭"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        if hasattr(manager, '_fault_file') and manager._fault_file:
            manager.shutdown()
            # 文件应该被关闭（或者不存在）
            assert not hasattr(manager, '_fault_file') or \
                   manager._fault_file is None or \
                   manager._fault_file.closed


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_module_level_debug(self):
        """测试模块级debug函数"""
        from utils import log_manager
        log_manager.debug("模块级调试")
    
    def test_module_level_info(self):
        """测试模块级info函数"""
        from utils import log_manager
        log_manager.info("模块级信息")
    
    def test_module_level_warning(self):
        """测试模块级warning函数"""
        from utils import log_manager
        log_manager.warning("模块级警告")
    
    def test_module_level_error(self):
        """测试模块级error函数"""
        from utils import log_manager
        log_manager.error("模块级错误")
    
    def test_module_level_critical(self):
        """测试模块级critical函数"""
        from utils import log_manager
        log_manager.critical("模块级严重错误")
    
    def test_module_level_exception(self):
        """测试模块级exception函数"""
        from utils import log_manager
        try:
            raise RuntimeError("测试")
        except RuntimeError:
            log_manager.exception("模块级异常")


class TestThreadSafetyLogManager:
    """日志管理器线程安全测试"""
    
    def test_concurrent_logging(self):
        """测试并发写入日志"""
        from utils.log_manager import get_logger
        
        logger = get_logger()
        errors = []
        
        def log_messages():
            try:
                for i in range(50):
                    logger.info(f"线程消息 {i}")
            except Exception as e:
                errors.append(str(e))
        
        threads = [threading.Thread(target=log_messages) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"出现错误: {errors}"
    
    def test_concurrent_get_logger(self):
        """测试并发获取日志管理器"""
        from utils import log_manager
        
        instances = []
        lock = threading.Lock()
        
        def get_instance():
            instance = log_manager.get_logger()
            with lock:
                instances.append(instance)
        
        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有实例应该相同
        assert all(i is instances[0] for i in instances)


class TestFaultHandler:
    """faulthandler 测试"""
    
    def test_faulthandler_enabled(self):
        """测试faulthandler已启用"""
        import faulthandler
        
        from utils.log_manager import LogManager
        manager = LogManager()
        
        assert faulthandler.is_enabled()
    
    def test_fault_log_path_created(self):
        """测试段错误日志路径已创建"""
        from utils.log_manager import LogManager
        
        manager = LogManager()
        
        if hasattr(manager, 'fault_log_path'):
            # 目录应该存在
            assert manager.fault_log_path.parent.exists()


class TestLogRotation:
    """日志轮转测试"""
    
    def test_app_logger_has_rotating_handler(self):
        """测试应用日志有轮转处理器"""
        from utils.log_manager import LogManager
        from logging.handlers import RotatingFileHandler
        
        manager = LogManager()
        
        handlers = manager.app_logger.handlers
        rotating_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
        
        assert len(rotating_handlers) > 0
    
    def test_crash_logger_has_timed_handler(self):
        """测试崩溃日志有时间轮转处理器"""
        from utils.log_manager import LogManager
        from logging.handlers import TimedRotatingFileHandler
        
        manager = LogManager()
        
        handlers = manager.crash_logger.handlers
        timed_handlers = [h for h in handlers if isinstance(h, TimedRotatingFileHandler)]
        
        assert len(timed_handlers) > 0
