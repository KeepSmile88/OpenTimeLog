# -*- coding: utf-8 -*-
"""
pytest 通用配置和 fixtures

提供所有测试文件共享的测试设施
"""

import os
import sys
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# 将项目根目录添加到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import DatabaseManager
from core.models import Activity, TimeLog, PauseLog, DailyStats
from core.time_calculator import TimeCalculator


# ==================== 数据库相关 Fixtures ====================

@pytest.fixture
def temp_db_path():
    """创建临时数据库文件路径"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_timelog.db')
    yield db_path
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def db_manager(temp_db_path):
    """创建临时数据库管理器实例
    
    每个测试使用独立的数据库，测试后自动清理
    """
    manager = DatabaseManager(db_path=temp_db_path)
    yield manager
    # 关闭连接
    manager.close()


@pytest.fixture
def empty_db_manager(temp_db_path):
    """创建空数据库管理器（无默认活动）
    
    用于测试初始化逻辑
    """
    manager = DatabaseManager(db_path=temp_db_path)
    # 清空默认活动
    cursor = manager.conn.cursor()
    cursor.execute("DELETE FROM activities")
    manager.conn.commit()
    yield manager
    manager.close()


@pytest.fixture
def sample_activity(db_manager):
    """创建示例活动"""
    activity_id = db_manager.add_activity(
        name="测试活动",
        color="#FF0000",
        icon="🧪",
        goal_minutes=60
    )
    return activity_id


@pytest.fixture
def sample_running_log(db_manager, sample_activity):
    """创建运行中的时间记录"""
    log_id = db_manager.start_activity(
        sample_activity,
        note="测试备注"
    )
    return log_id


@pytest.fixture
def sample_completed_log(db_manager, sample_activity):
    """创建已完成的时间记录"""
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    log_id = db_manager.add_manual_log(
        sample_activity,
        start_time,
        end_time,
        note="已完成的测试记录"
    )
    return log_id


# ==================== 模拟对象 Fixtures ====================

@pytest.fixture
def mock_db_manager():
    """创建模拟的数据库管理器
    
    用于不需要真实数据库的UI测试
    """
    mock = MagicMock(spec=DatabaseManager)
    
    # 配置常用方法的返回值
    mock.get_activities.return_value = [
        (1, '工作', '#FF6B6B', '💼', 480, 0, None),
        (2, '学习', '#4ECDC4', '📚', 120, 0, None),
    ]
    mock.get_running_activities.return_value = []
    mock.get_todos.return_value = []
    mock.get_schedules.return_value = []
    mock.get_daily_logs.return_value = []
    mock.get_daily_stats.return_value = []
    
    return mock


@pytest.fixture
def mock_qapp():
    """模拟 QApplication（用于不需要真实UI的测试）"""
    with patch('PySide6.QtWidgets.QApplication'):
        yield


# ==================== 时间相关 Fixtures ====================

@pytest.fixture
def fixed_datetime():
    """返回固定时间，用于可预测的时间测试"""
    return datetime(2026, 1, 28, 10, 30, 0)


@pytest.fixture
def mock_datetime(fixed_datetime):
    """模拟 datetime.now() 返回固定时间"""
    with patch('datetime.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_datetime
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.strptime = datetime.strptime
        yield mock_dt


# ==================== 辅助函数 ====================

def create_test_activity_tuple(
    id: int = 1,
    name: str = "测试活动",
    color: str = "#FF0000",
    icon: str = "🧪",
    goal_minutes: int = 60,
    is_archived: bool = False,
    created_at: str = None
) -> tuple:
    """创建测试用活动元组"""
    return (id, name, color, icon, goal_minutes, is_archived, created_at)


def create_test_timelog_tuple(
    id: int = 1,
    activity_id: int = 1,
    start_time: str = "2026-01-28 10:00:00",
    end_time: str = None,
    duration_seconds: int = None,
    status: str = "running",
    note: str = "",
    is_manual: bool = False,
    paused_duration: int = 0
) -> tuple:
    """创建测试用时间记录元组"""
    return (id, activity_id, start_time, end_time, duration_seconds, 
            status, note, is_manual, paused_duration)


def create_test_daily_stats_tuple(
    activity_id: int = 1,
    activity_name: str = "测试活动",
    activity_color: str = "#FF0000",
    activity_icon: str = "🧪",
    goal_minutes: int = 60,
    total_seconds: int = 3600,
    session_count: int = 2
) -> tuple:
    """创建测试用每日统计元组"""
    return (activity_id, activity_name, activity_color, activity_icon,
            goal_minutes, total_seconds, session_count)


# ==================== 测试标记 ====================

# 标记需要 Qt 的测试
requires_qt = pytest.mark.skipif(
    not os.environ.get('DISPLAY') and sys.platform != 'win32' and sys.platform != 'darwin',
    reason="需要图形显示环境"
)

# 标记慢速测试
slow_test = pytest.mark.slow

# 标记线程安全测试
thread_safety_test = pytest.mark.thread_safety


# ==================== pytest 配置 ====================

def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试"
    )
    config.addinivalue_line(
        "markers", "thread_safety: 标记线程安全测试"
    )
    config.addinivalue_line(
        "markers", "ui: 标记UI测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 如果运行快速测试，跳过慢速测试
    if config.getoption("--quick", default=False):
        skip_slow = pytest.mark.skip(reason="跳过慢速测试")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--quick",
        action="store_true",
        default=False,
        help="运行快速测试，跳过慢速测试"
    )
