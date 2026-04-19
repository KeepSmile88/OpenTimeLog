#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
使用 dataclass 提供类型安全的数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Activity:
    """活动类型数据模型"""
    id: int
    name: str
    color: str
    icon: str = '⭕'
    goal_minutes: int = 0
    is_archived: bool = False
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_tuple(cls, data: tuple) -> 'Activity':
        """从数据库元组创建Activity对象"""
        return cls(
            id=data[0],
            name=data[1],
            color=data[2],
            icon=data[3] if len(data) > 3 else '⭕',
            goal_minutes=data[4] if len(data) > 4 else 0,
            is_archived=bool(data[5]) if len(data) > 5 else False,
            created_at=datetime.fromisoformat(data[6]) if len(data) > 6 and data[6] else None
        )


@dataclass
class TimeLog:
    """时间记录数据模型"""
    id: int
    activity_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str = 'running'  # running, paused, completed
    note: str = ''
    is_manual: bool = False
    paused_duration: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联的活动信息（用于显示）
    activity_name: str = ''
    activity_color: str = ''
    activity_icon: str = ''
    
    @classmethod
    def from_tuple(cls, data: tuple, include_activity: bool = False) -> 'TimeLog':
        """从数据库元组创建TimeLog对象
        
        Args:
            data: 数据库查询结果元组
            include_activity: 是否包含活动信息（JOIN查询结果）
        """
        if include_activity:
            # 格式: (id, name, color, icon, start_time, note, status) - 来自get_running_activities
            return cls(
                id=data[0],
                activity_id=0,  # 未提供
                start_time=datetime.fromisoformat(data[4]) if isinstance(data[4], str) else data[4],
                status=data[6] if len(data) > 6 else 'running',
                note=data[5] if len(data) > 5 else '',
                activity_name=data[1],
                activity_color=data[2],
                activity_icon=data[3]
            )
        else:
            return cls(
                id=data[0],
                activity_id=data[1],
                start_time=datetime.fromisoformat(data[2]) if isinstance(data[2], str) else data[2],
                end_time=datetime.fromisoformat(data[3]) if data[3] and isinstance(data[3], str) else data[3],
                duration_seconds=data[4] if len(data) > 4 else None,
                status=data[5] if len(data) > 5 else 'running',
                note=data[6] if len(data) > 6 else '',
                is_manual=bool(data[7]) if len(data) > 7 else False,
                paused_duration=data[8] if len(data) > 8 else 0
            )


@dataclass
class PauseLog:
    """暂停记录数据模型"""
    id: int
    time_log_id: int
    pause_start: datetime
    pause_end: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_tuple(cls, data: tuple) -> 'PauseLog':
        """从数据库元组创建PauseLog对象"""
        return cls(
            id=data[0],
            time_log_id=data[1],
            pause_start=datetime.fromisoformat(data[2]) if isinstance(data[2], str) else data[2],
            pause_end=datetime.fromisoformat(data[3]) if data[3] and isinstance(data[3], str) else data[3],
            created_at=datetime.fromisoformat(data[4]) if len(data) > 4 and data[4] else None
        )


@dataclass
class DailyStats:
    """每日统计数据模型"""
    activity_id: int
    activity_name: str
    activity_color: str
    activity_icon: str
    goal_minutes: int
    total_seconds: int
    session_count: int
    
    @classmethod
    def from_tuple(cls, data: tuple) -> 'DailyStats':
        """从数据库元组创建DailyStats对象"""
        return cls(
            activity_id=data[0],
            activity_name=data[1],
            activity_color=data[2],
            activity_icon=data[3],
            goal_minutes=data[4],
            total_seconds=data[5],
            session_count=data[6]
        )
    
    @property
    def total_minutes(self) -> int:
        """总分钟数"""
        return self.total_seconds // 60
    
    @property
    def completion_rate(self) -> float:
        """目标完成率（百分比）"""
        if self.goal_minutes <= 0:
            return 0.0
        return (self.total_minutes / self.goal_minutes) * 100
