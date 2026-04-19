#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器
负责所有数据库操作
"""

import os
import sqlite3
import threading
from datetime import datetime, timedelta, date



class DatabaseManager:
    """数据库管理类，负责所有数据库操作"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认在程序根目录创建数据文件夹
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, 'data')
            if not os.path.exists(data_dir): os.makedirs(data_dir)
            db_path = os.path.join(data_dir, 'timelog.db')
            
        self.db_path = db_path
        # 线程安全：使用 RLock 允许同一线程重入
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.is_closed = False
        self._init_db()
    
    def get_cursor(self):
        """获取数据库游标（线程安全）"""
        if self.is_closed:
            return None
        return self.conn.cursor()
    
    def execute_safe(self, sql, params=(), commit=True):
        """线程安全的 SQL 执行
        
        Args:
            sql: SQL 语句
            params: 参数元组
            commit: 是否自动提交
            
        Returns:
            cursor 对象
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return

            cursor.execute(sql, params)
            if commit:
                self.conn.commit()
            return cursor
    
    def fetchall_safe(self, sql, params=()):
        """线程安全的查询执行
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            查询结果列表
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return

            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def fetchone_safe(self, sql, params=()):
        """线程安全的单行查询
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            单行结果或 None
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return

            cursor.execute(sql, params)
            return cursor.fetchone()

    def _init_db(self):
        """初始化数据库表结构"""
        cursor = self.get_cursor()
        if cursor is None: return
        
        # 活动类型表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                icon TEXT,
                goal_minutes INTEGER DEFAULT 0,
                is_archived BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 时间记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                status TEXT DEFAULT 'running',
                note TEXT,
                is_manual BOOLEAN DEFAULT 0,
                paused_duration INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (activity_id) REFERENCES activities (id)
            )
        ''')
        
        # 暂停记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pause_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_log_id INTEGER NOT NULL,
                pause_start TIMESTAMP NOT NULL,
                pause_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (time_log_id) REFERENCES time_logs (id)
            )
        ''')
        
        # 待办事项表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                is_completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 日程表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                content TEXT NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        self.init_default_activities()
    
    def init_default_activities(self):
        """初始化默认活动类型"""
        cursor = self.get_cursor()
        if cursor is None: return

        cursor.execute("SELECT COUNT(*) FROM activities WHERE is_archived = 0")
        if cursor.fetchone()[0] == 0:
            default_activities = [
                ('工作', '#FF6B6B', '💼', 480),
                ('学习', '#4ECDC4', '📚', 120),
                ('运动', '#45B7D1', '🏃', 60),
                ('休息', '#96CEB4', '😴', 480),
                ('娱乐', '#FECA57', '🎮', 120),
                ('社交', '#FF9FF3', '👥', 90),
                ('通勤', '#54A0FF', '🚗', 120),
                ('饮食', '#5F27CD', '🍽️', 90)
            ]
            
            cursor.executemany(
                "INSERT INTO activities (name, color, icon, goal_minutes) VALUES (?, ?, ?, ?)",
                default_activities
            )
            self.conn.commit()

        # 待办事项表升级
        cursor.execute('PRAGMA table_info(todos)')
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'priority' not in columns:
            cursor.execute('ALTER TABLE todos ADD COLUMN priority INTEGER DEFAULT 1') # 0:低, 1:中, 2:高, 3:紧急
        if 'due_date' not in columns:
            cursor.execute('ALTER TABLE todos ADD COLUMN due_date TEXT')
        if 'activity_id' not in columns:
            cursor.execute('ALTER TABLE todos ADD COLUMN activity_id INTEGER REFERENCES activities(id)')
        if 'description' not in columns:
            cursor.execute('ALTER TABLE todos ADD COLUMN description TEXT')
        if 'updated_at' not in columns:
            cursor.execute('ALTER TABLE todos ADD COLUMN updated_at TIMESTAMP')
            
        # 日程表升级
        cursor.execute('PRAGMA table_info(schedules)')
        s_columns = [c[1] for c in cursor.fetchall()]
        if 'target_date' not in s_columns:
            cursor.execute('ALTER TABLE schedules ADD COLUMN target_date TEXT') # YYYY-MM-DD
        
        self.conn.commit()

    # ==================== 待办事项管理 ====================

    def add_todo(self, content: str, priority: int = 1, due_date: str = None, 
                activity_id: int = None, description: str = '') -> int:
        """添加高级待办事项"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return 0
            
            cursor.execute('''
                INSERT INTO todos (content, priority, due_date, activity_id, description) 
                VALUES (?, ?, ?, ?, ?)
            ''', (content, priority, due_date, activity_id, description))
            self.conn.commit()
            return cursor.lastrowid

    def get_todos(self, include_completed: bool = True) -> list[tuple]:
        """获取所有待办事项（按优先级和截止日期排序）"""
        with self._lock:
            cursor = self.conn.cursor()
            query = '''
                SELECT t.id, t.content, t.is_completed, t.priority, t.due_date, t.description, 
                       a.name, a.color, a.icon, t.activity_id
                FROM todos t
                LEFT JOIN activities a ON t.activity_id = a.id
            '''
            if not include_completed:
                query += ' WHERE t.is_completed = 0'
                
            # 排序逻辑：未完成优先，紧急度优先，日期优先
            query += ' ORDER BY t.is_completed ASC, t.priority DESC, t.due_date ASC, t.created_at DESC'
            
            cursor.execute(query)
            return cursor.fetchall()

    def update_todo_status(self, todo_id: int, is_completed: bool):
        """更新待办状态"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return
            cursor.execute('UPDATE todos SET is_completed = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                          (1 if is_completed else 0, todo_id))
            self.conn.commit()

    def update_todo(self, todo_id: int, **kwargs):
        """更新待办事项详情"""
        if not kwargs: return
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return None
            sets = [f"{k} = ?" for k in kwargs.keys()]
            cursor.execute(f'UPDATE todos SET {", ".join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                          list(kwargs.values()) + [todo_id])
            self.conn.commit()

    def delete_todo(self, todo_id: int):
        """删除待办事项"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return None
            cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
            self.conn.commit()

    
    # ==================== 活动管理 ====================
    
    def add_activity(self, name: str, color: str, icon: str = '⭕', goal_minutes: int = 0) -> int | None:
        """添加新活动
        
        Args:
            name: 活动名称
            color: 活动颜色
            icon: 活动图标
            goal_minutes: 每日目标时间（分钟）
            
        Returns:
            新活动的ID，如果名称重复返回None
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return None
            
            try:
                cursor.execute(
                    "INSERT INTO activities (name, color, icon, goal_minutes) VALUES (?, ?, ?, ?)",
                    (name, color, icon, goal_minutes)
                )
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
    
    def get_activities(self, include_archived: bool = False) -> list[tuple]:
        """获取所有活动
        
        Args:
            include_archived: 是否包含已归档的活动
            
        Returns:
            活动列表
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            
            if include_archived:
                cursor.execute("SELECT * FROM activities ORDER BY name")
            else:
                cursor.execute("SELECT * FROM activities WHERE is_archived = 0 ORDER BY name")
            return cursor.fetchall()
    
    def update_activity(self, activity_id: int, name: str = None, color: str = None, 
                       icon: str = None, goal_minutes: int = None) -> bool:
        """更新活动信息
        
        Args:
            activity_id: 活动ID
            name: 新名称
            color: 新颜色
            icon: 新图标
            goal_minutes: 新目标时间
            
        Returns:
            是否更新成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False

            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            if icon is not None:
                updates.append("icon = ?")
                params.append(icon)
            if goal_minutes is not None:
                updates.append("goal_minutes = ?")
                params.append(goal_minutes)
            
            if not updates:
                return False
            
            params.append(activity_id)
            query = f"UPDATE activities SET {', '.join(updates)} WHERE id = ?"
            
            try:
                cursor.execute(query, params)
                self.conn.commit()
                return cursor.rowcount > 0
            except sqlite3.IntegrityError:
                return False
    
    def archive_activity(self, activity_id: int) -> bool:
        """归档活动
        
        Args:
            activity_id: 活动ID
            
        Returns:
            是否归档成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False
            cursor.execute("UPDATE activities SET is_archived = 1 WHERE id = ?", (activity_id,))
            self.conn.commit()
            return cursor.rowcount > 0
    
    def get_activity_log_count(self, activity_id: int) -> int:
        """获取活动关联的时间记录数量
        
        Args:
            activity_id: 活动ID
            
        Returns:
            关联的时间记录数量
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return 0
            cursor.execute("SELECT COUNT(*) FROM time_logs WHERE activity_id = ?", (activity_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def delete_activity(self, activity_id: int, delete_logs: bool = False) -> bool:
        """删除活动
        
        Args:
            activity_id: 活动ID
            delete_logs: 是否同时删除关联的时间记录
            
        Returns:
            是否删除成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False
            
            try:
                # 检查是否有运行中的活动
                cursor.execute(
                    "SELECT COUNT(*) FROM time_logs WHERE activity_id = ? AND status IN ('running', 'paused')",
                    (activity_id,)
                )
                running_count = cursor.fetchone()[0]
                if running_count > 0:
                    return False  # 有运行中的任务，不允许删除
                
                if delete_logs:
                    # 先删除关联的暂停记录
                    cursor.execute(
                        "DELETE FROM pause_logs WHERE time_log_id IN (SELECT id FROM time_logs WHERE activity_id = ?)",
                        (activity_id,)
                    )
                    # 再删除关联的时间记录
                    cursor.execute("DELETE FROM time_logs WHERE activity_id = ?", (activity_id,))
                
                # 清除待办事项中的活动关联
                cursor.execute("UPDATE todos SET activity_id = NULL WHERE activity_id = ?", (activity_id,))
                
                # 删除活动本身
                cursor.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
                self.conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"删除活动失败: {e}")
                return False
    
    # ==================== 时间记录管理 ====================
    
    def start_activity(self, activity_id: int, note: str = '', start_time: datetime = None) -> int:
        """开始一个活动
        
        Args:
            activity_id: 活动ID
            note: 备注
            start_time: 开始时间，默认为当前时间
            
        Returns:
            新时间记录的ID
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return 0
            if start_time is None:
                start_time = datetime.now()
            
            cursor.execute(
                "INSERT INTO time_logs (activity_id, start_time, note, status) VALUES (?, ?, ?, 'running')",
                (activity_id, start_time, note)
            )
            self.conn.commit()
            return cursor.lastrowid
    
    def pause_activity(self, log_id: int) -> bool:
        """暂停活动
        
        Args:
            log_id: 时间记录ID
            
        Returns:
            是否暂停成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return False
            
            try:
                cursor.execute(
                    "UPDATE time_logs SET status = 'paused', updated_at = ? WHERE id = ? AND status = 'running'",
                    (datetime.now(), log_id)
                )
                
                if cursor.rowcount > 0:
                    cursor.execute(
                        "INSERT INTO pause_logs (time_log_id, pause_start) VALUES (?, ?)",
                        (log_id, datetime.now())
                    )
                    self.conn.commit()
                    return True
                return False
            except Exception as e:
                print(f"Error pausing activity: {e}")
                return False
    
    def resume_activity(self, log_id: int) -> bool:
        """继续活动（从暂停状态恢复）
        
        Args:
            log_id: 时间记录ID
            
        Returns:
            是否继续成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return False
            
            try:
                cursor.execute(
                    "UPDATE time_logs SET status = 'running', updated_at = ? WHERE id = ? AND status = 'paused'",
                    (datetime.now(), log_id)
                )
                
                if cursor.rowcount > 0:
                    # 结束当前暂停记录
                    cursor.execute(
                        "UPDATE pause_logs SET pause_end = ? WHERE time_log_id = ? AND pause_end IS NULL",
                        (datetime.now(), log_id)
                    )
                    self.conn.commit()
                    return True
                return False
            except Exception as e:
                print(f"Error resuming activity: {e}")
                return False
    
    def resume_completed_activity(self, log_id: int) -> bool:
        """恢复已完成的活动（重新开始计时）
        
        将已完成的任务恢复为运行状态，从结束时间到当前时间的间隔作为暂停时间
        
        Args:
            log_id: 时间记录ID
            
        Returns:
            是否恢复成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return False
            
            try:
                # 获取原记录信息
                cursor.execute("SELECT end_time, status FROM time_logs WHERE id = ?", (log_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                end_time_str, status = result
                
                if status != 'completed':
                    return False
                
                if not end_time_str:
                    return False
                
                end_time = datetime.fromisoformat(end_time_str)
                now = datetime.now()
                
                # 创建一条暂停记录（从结束时间到现在）
                cursor.execute(
                    "INSERT INTO pause_logs (time_log_id, pause_start, pause_end) VALUES (?, ?, ?)",
                    (log_id, end_time, now)
                )
                
                # 更新时间记录状态为运行中
                cursor.execute("""
                    UPDATE time_logs 
                    SET status = 'running', 
                        end_time = NULL, 
                        duration_seconds = NULL,
                        updated_at = ?
                    WHERE id = ?
                """, (now, log_id))
                
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error resuming completed activity: {e}")
                return False
    
    def stop_activity(self, log_id: int, end_time: datetime = None) -> int:
        """停止活动
        
        Args:
            log_id: 时间记录ID
            end_time: 结束时间，默认为当前时间
            
        Returns:
            实际持续时间（秒）
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return 0
            
            if end_time is None:
                end_time = datetime.now()
            
            # 获取开始时间
            cursor.execute("SELECT start_time FROM time_logs WHERE id = ?", (log_id,))
            result = cursor.fetchone()
            if not result:
                return 0
            
            start_dt = datetime.fromisoformat(result[0])
            
            # 计算暂停总时间
            cursor.execute("""
                SELECT SUM(
                    CASE 
                        WHEN pause_end IS NULL THEN (julianday(?) - julianday(pause_start)) * 86400
                        ELSE (julianday(pause_end) - julianday(pause_start)) * 86400
                    END
                ) as total_pause
                FROM pause_logs WHERE time_log_id = ?
            """, (end_time, log_id))
            
            pause_seconds = cursor.fetchone()[0] or 0
            total_seconds = int((end_time - start_dt).total_seconds() - pause_seconds)
            
            # 结束未完成的暂停记录
            cursor.execute(
                "UPDATE pause_logs SET pause_end = ? WHERE time_log_id = ? AND pause_end IS NULL",
                (end_time, log_id)
            )
            
            try:
                cursor.execute(
                    "UPDATE time_logs SET end_time = ?, duration_seconds = ?, paused_duration = ?, status = 'completed', updated_at = ? WHERE id = ?",
                    (end_time, total_seconds, int(pause_seconds), datetime.now(), log_id)
                )
                self.conn.commit()
                return total_seconds
            except Exception as e:
                print(f"Error stopping activity: {e}")
                return 0
    
    def get_running_activities(self) -> list[tuple]:
        """获取运行中的活动列表（线程安全）"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            cursor.execute('''
                SELECT tl.id, a.name, a.color, a.icon, tl.start_time, tl.note, tl.status
                FROM time_logs tl
                JOIN activities a ON tl.activity_id = a.id
                WHERE tl.status IN ('running', 'paused')
                ORDER BY (CASE WHEN tl.status = 'running' THEN 0 ELSE 1 END) ASC, tl.start_time DESC
            ''')
            return cursor.fetchall()
    
    def get_elapsed_running(self, log_id: int, now: datetime = None) -> int:
        """获取运行中活动的真实耗时（扣除暂停时间）
        
        Args:
            log_id: 时间记录ID
            now: 当前时间，默认为datetime.now()
            
        Returns:
            真实耗时（秒）
        """
        if now is None:
            now = datetime.now()

        with self._lock:
            cur = self.get_cursor()
            if cur is None:
                return 0
            
            try:
                # 取 start_time 和当前状态
                cur.execute("SELECT start_time, status FROM time_logs WHERE id = ?", (log_id,))
                row = cur.fetchone()
                if not row:
                    return 0
                start_dt = datetime.fromisoformat(row[0])
                status = row[1]

                if status == 'paused':
                    # 暂停状态下显示到最近一次 pause_start 为止
                    cur.execute(
                        "SELECT pause_start FROM pause_logs WHERE time_log_id = ? AND pause_end IS NULL ORDER BY pause_start DESC LIMIT 1",
                        (log_id,))
                    ps = cur.fetchone()
                    if not ps:
                        # 没有未结束的暂停（容错），当作运行中处理
                        return self.get_elapsed_running(log_id, now)
                    pause_start_dt = datetime.fromisoformat(ps[0])

                    # 已结束暂停总秒数（不含当前暂停段）
                    cur.execute("""
                        SELECT COALESCE(SUM((julianday(pause_end) - julianday(pause_start)) * 86400), 0)
                        FROM pause_logs 
                        WHERE time_log_id = ? AND pause_end IS NOT NULL
                    """, (log_id,))
                    paused_sec_done = int(cur.fetchone()[0] or 0)

                    total_seconds = int((pause_start_dt - start_dt).total_seconds() - paused_sec_done)
                    return max(0, total_seconds)

                else:
                    # status == 'running'：包含未结束暂停（用 now 作为临时结束点）
                    cur.execute("""
                        SELECT SUM(
                            CASE 
                                WHEN pause_end IS NULL THEN (julianday(?) - julianday(pause_start)) * 86400
                                ELSE (julianday(pause_end) - julianday(pause_start)) * 86400
                            END
                        )
                        FROM pause_logs WHERE time_log_id = ?
                    """, (now, log_id))
                    paused_sec_all = int((cur.fetchone()[0] or 0))
                    total_seconds = int((now - start_dt).total_seconds() - paused_sec_all)
                    return max(0, total_seconds)
            except Exception as e:
                print(f"Error getting elapsed time: {e}")
                return 0
    
    def add_manual_log(self, activity_id: int, start_time: datetime, 
                      end_time: datetime, note: str = '') -> int:
        """添加手动时间记录
        
        Args:
            activity_id: 活动ID
            start_time: 开始时间
            end_time: 结束时间
            note: 备注
            
        Returns:
            新记录的ID
        """
        with self._lock:
            cursor = self.conn.cursor()
            duration = int((end_time - start_time).total_seconds())
            
            cursor.execute("""
                INSERT INTO time_logs (activity_id, start_time, end_time, duration_seconds, note, status, is_manual)
                VALUES (?, ?, ?, ?, ?, 'completed', 1)
            """, (activity_id, start_time, end_time, duration, note))
            
            self.conn.commit()
            return cursor.lastrowid
    
    def update_log_times(self, log_id: int, start_time: datetime, 
                        end_time: datetime = None) -> bool:
        """更新时间记录的时间
        
        Args:
            log_id: 时间记录ID
            start_time: 新的开始时间
            end_time: 新的结束时间
            
        Returns:
            是否更新成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False
            
            if end_time:
                duration = int((end_time - start_time).total_seconds())
                cursor.execute("""
                    UPDATE time_logs 
                    SET start_time = ?, end_time = ?, duration_seconds = ?, updated_at = ?
                    WHERE id = ?
                """, (start_time, end_time, duration, datetime.now(), log_id))
            else:
                cursor.execute("""
                    UPDATE time_logs 
                    SET start_time = ?, updated_at = ?
                    WHERE id = ?
                """, (start_time, datetime.now(), log_id))
            
            self.conn.commit()
            return cursor.rowcount > 0
    
    def update_log_note(self, log_id: int, note: str) -> bool:
        """更新时间记录的备注
        
        Args:
            log_id: 时间记录ID
            note: 新备注
            
        Returns:
            是否更新成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False
            cursor.execute("UPDATE time_logs SET note = ?, updated_at = ? WHERE id = ?", 
                          (note, datetime.now(), log_id))
            self.conn.commit()
            return cursor.rowcount > 0

    def update_log_activity(self, log_id: int, new_activity_id: int) -> bool:
        """更新时间记录的活动类型
        
        Args:
            log_id: 时间记录ID
            new_activity_id: 新的活动ID
            
        Returns:
            是否更新成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False
            cursor.execute("UPDATE time_logs SET activity_id = ?, updated_at = ? WHERE id = ?",
                          (new_activity_id, datetime.now(), log_id))
            self.conn.commit()
            return cursor.rowcount > 0
    
    def delete_log(self, log_id: int) -> bool:
        """删除时间记录
        
        Args:
            log_id: 时间记录ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return False
            cursor.execute("DELETE FROM pause_logs WHERE time_log_id = ?", (log_id,))
            cursor.execute("DELETE FROM time_logs WHERE id = ?", (log_id,))
            self.conn.commit()
            return cursor.rowcount > 0
    
    def get_log_by_id(self, log_id: int) -> tuple | None:
        """根据ID获取时间记录详情
        
        Args:
            log_id: 时间记录ID
            
        Returns:
            时间记录元组
        """
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return None
            cursor.execute("""
                SELECT tl.id, a.name, a.color, a.icon, tl.start_time, tl.end_time, 
                       tl.duration_seconds, tl.note, tl.status, tl.is_manual
                FROM time_logs tl
                JOIN activities a ON tl.activity_id = a.id
                WHERE tl.id = ?
            """, (log_id,))
            return cursor.fetchone()
    
    # ==================== 统计查询 ====================
    
    def get_daily_logs(self, target_date: date = None) -> list[tuple]:
        """获取指定日期的所有记录
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            当天的时间记录列表
        """
        if target_date is None:
            target_date = date.today()
        
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            
            cursor.execute('''
                SELECT tl.id, a.name, a.color, a.icon, tl.start_time, tl.end_time, 
                       tl.duration_seconds, tl.note, tl.status, tl.is_manual
                FROM time_logs tl
                JOIN activities a ON tl.activity_id = a.id
                WHERE DATE(tl.start_time) = ?
                ORDER BY tl.start_time DESC
            ''', (target_date.strftime('%Y-%m-%d'),))
            return cursor.fetchall()
    
    def get_daily_stats(self, target_date: date = None) -> list[tuple]:
        """获取指定日期的统计数据
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            统计数据列表
        """
        if target_date is None:
            target_date = date.today()
        
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            cursor.execute('''
                SELECT a.id, a.name, a.color, a.icon, a.goal_minutes,
                       COALESCE(SUM(CASE WHEN tl.status = 'completed' THEN tl.duration_seconds ELSE 0 END), 0) as total_seconds,
                       COUNT(CASE WHEN tl.status = 'completed' THEN 1 END) as session_count
                FROM activities a
                LEFT JOIN time_logs tl ON a.id = tl.activity_id AND DATE(tl.start_time) = ?
                WHERE a.is_archived = 0
                GROUP BY a.id, a.name, a.color, a.icon, a.goal_minutes
                ORDER BY total_seconds DESC
            ''', (target_date.strftime('%Y-%m-%d'),))
            return cursor.fetchall()

    def get_weekly_stats(self, target_date: date = None) -> list[tuple]:
        """获取指定日期所在周的统计数据
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            统计数据列表
        """
        if target_date is None:
            target_date = date.today()

        # 获取该日期所在周的周一和周日
        start_of_week = target_date - timedelta(days=target_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            cursor.execute('''
                SELECT a.id, a.name, a.color, a.icon, a.goal_minutes,
                       COALESCE(SUM(CASE WHEN tl.status = 'completed' THEN tl.duration_seconds ELSE 0 END), 0) as total_seconds,
                       COUNT(CASE WHEN tl.status = 'completed' THEN 1 END) as session_count
                FROM activities a
                LEFT JOIN time_logs tl 
                    ON a.id = tl.activity_id 
                    AND DATE(tl.start_time) BETWEEN ? AND ?
                WHERE a.is_archived = 0
                GROUP BY a.id, a.name, a.color, a.icon, a.goal_minutes
                ORDER BY total_seconds DESC
            ''', (start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')))
            return cursor.fetchall()

    def get_monthly_stats(self, target_date: date = None) -> list[tuple]:
        """获取指定日期所在月的统计数据
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            统计数据列表
        """
        if target_date is None:
            target_date = date.today()

        start_of_month = target_date.replace(day=1)
        # 下个月的第一天 - 1天 = 本月最后一天
        if start_of_month.month == 12:
            next_month = start_of_month.replace(year=start_of_month.year + 1, month=1, day=1)
        else:
            next_month = start_of_month.replace(month=start_of_month.month + 1, day=1)
        end_of_month = next_month - timedelta(days=1)

        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            cursor.execute('''
                SELECT a.id, a.name, a.color, a.icon, a.goal_minutes,
                       COALESCE(SUM(CASE WHEN tl.status = 'completed' THEN tl.duration_seconds ELSE 0 END), 0) as total_seconds,
                       COUNT(CASE WHEN tl.status = 'completed' THEN 1 END) as session_count
                FROM activities a
                LEFT JOIN time_logs tl 
                    ON a.id = tl.activity_id 
                    AND DATE(tl.start_time) BETWEEN ? AND ?
                WHERE a.is_archived = 0
                GROUP BY a.id, a.name, a.color, a.icon, a.goal_minutes
                ORDER BY total_seconds DESC
            ''', (start_of_month.strftime('%Y-%m-%d'), end_of_month.strftime('%Y-%m-%d')))
            return cursor.fetchall()
    
    def get_analysis_records(self, start_date: date, end_date: date) -> list[tuple]:
        """获取分析所需的原始记录数据"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            cursor.execute('''
                SELECT tl.id, a.name, a.color, a.icon, tl.start_time, tl.end_time, 
                       tl.duration_seconds, tl.note, tl.status, tl.is_manual
                FROM time_logs tl
                JOIN activities a ON tl.activity_id = a.id
                WHERE DATE(tl.start_time) BETWEEN ? AND ? AND tl.status = 'completed'
                ORDER BY tl.start_time ASC
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchall()

    def get_yearly_heatmap_data(self, year: int) -> dict:
        """获取指定年份的每日总时长（热力图数据）"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return []
            cursor.execute('''
                SELECT DATE(start_time) as day, SUM(duration_seconds) as total_sec
                FROM time_logs
                WHERE strftime('%Y', start_time) = ? AND status = 'completed'
                GROUP BY day
            ''', (str(year),))
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_period_comparison_data(self, period_type: str, target_date: date) -> dict:
        """获取周期对比数据 (本期 vs 上期)
        period_type: 'week' or 'month'
        """
        if period_type == 'week':
            # 本周一到周日
            start_this = target_date - timedelta(days=target_date.weekday())
            end_this = start_this + timedelta(days=6)
            # 上周一到周日
            start_last = start_this - timedelta(days=7)
            end_last = start_last + timedelta(days=6)
        else: # month
            # 本月第一天到最后一天
            start_this = target_date.replace(day=1)
            next_month = (start_this + timedelta(days=32)).replace(day=1)
            end_this = next_month - timedelta(days=1)
            # 上月第一天到最后一天
            end_last = start_this - timedelta(days=1)
            start_last = end_last.replace(day=1)

        # 获取各类别分布
        def get_dist(s, e):
            with self._lock:
                cursor = self.get_cursor()
                if cursor is None: return dict()
                cursor.execute('''
                    SELECT a.name, SUM(tl.duration_seconds) 
                    FROM activities a 
                    JOIN time_logs tl ON a.id = tl.activity_id 
                    WHERE DATE(tl.start_time) >= ? AND DATE(tl.start_time) <= ? 
                    AND tl.status = 'completed'
                    GROUP BY a.name
                ''', (s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')))
                return dict(cursor.fetchall())

        return {
            "this_period": get_dist(start_this, end_this),
            "last_period": get_dist(start_last, end_last),
            "start_this": start_this, "end_this": end_this,
            "start_last": start_last, "end_last": end_last
        }

    # ==================== 日程管理 (Schedule) ====================

    def add_schedule(self, start_time: str, end_time: str, content: str, target_date: str = None) -> int:
        """添加日程
        target_date: YYYY-MM-DD, None表示每日重复(暂保留兼容性, 或视作今日)
        """
        if target_date is None:
            target_date = date.today().strftime('%Y-%m-%d')

        with self._lock:
            cursor = self.get_cursor()
            if cursor is None: return 0
            cursor.execute('''
                INSERT INTO schedules (start_time, end_time, content, target_date)
                VALUES (?, ?, ?, ?)
            ''', (start_time, end_time, content, target_date))
            self.conn.commit()
            return cursor.lastrowid

    def get_schedules(self, target_date: str = None) -> list[tuple]:
        """获取日程
        target_date: YYYY-MM-DD. 如果为None，获取今日的
        """
        if target_date is None:
            target_date = date.today().strftime('%Y-%m-%d')

        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return []

            try:
                cursor.execute('SELECT * FROM schedules WHERE target_date = ? ORDER BY start_time ASC', (target_date,))
                return cursor.fetchall()
            except Exception as e:
                print(f"Error getting schedules: {e}")
                return []
    
    def get_current_schedule(self, current_time_str: str) -> tuple | None:
        """获取当前时间对应的日程(仅限今日)"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return None

            try:
                today_str = date.today().strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT * FROM schedules 
                    WHERE target_date = ? AND start_time <= ? AND end_time > ?
                    LIMIT 1
                ''', (today_str, current_time_str, current_time_str))
                return cursor.fetchone()
            except Exception as e:
                print(f"Error getting current schedule: {e}")
                return None

    def delete_schedule(self, schedule_id: int):
        """删除日程"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return

            try:
                cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
                self.conn.commit()
            except Exception as e:
                print(f"Error deleting schedule: {e}")
        
    def clear_schedules(self):
        """清空所有日程"""
        with self._lock:
            cursor = self.get_cursor()
            if cursor is None:
                return

            try:
                cursor.execute('DELETE FROM schedules')
                self.conn.commit()
            except Exception as e:
                print(f"Error clearing schedules: {e}")

    def close(self):
        """关闭数据库连接"""
        self.is_closed = True
        if self.conn:
            try:
                self.conn.close()
            except: pass
