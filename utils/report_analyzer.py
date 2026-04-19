#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析工具
移植自 analyze_records.py，用于解析和格式化统计数据
"""

import re
from collections import defaultdict
from typing import List, Tuple, Dict, Any


class ReportAnalyzer:
    """报告分析器"""
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """格式化时长（中文）
        
        Args:
            seconds: 秒数
            
        Returns:
            X小时Y分钟
        """
        hours = seconds // 3600
        minutes = round((seconds % 3600) / 60)
        return f"{hours}小时{minutes}分钟"
    
    @staticmethod
    def extract_ids(text: str) -> List[str]:
        """从文本中提取数字ID
        
        Args:
            text: 文本内容
            
        Returns:
            ID字符串列表
        """
        if not text:
            return []
        return re.findall(r'\d+', text)
    
    @classmethod
    def analyze(cls, records: List[Tuple]) -> Tuple[Dict[str, Any], int]:
        """分析记录
        
        Args:
            records: 数据库查询结果列表 [(activity_name, note, duration), ...]
            
        Returns:
            (groups, total_all)
            groups结构: {activity_name: {'total': seconds, 'notes': [], 'ids': []}}
        """
        groups = defaultdict(lambda: {
            "total": 0,
            "notes": [],
            "ids": []
        })
        
        total_all = 0
        
        for record in records:
            # record格式: (id, name, color, icon, start_time, end_time, duration_seconds, note, status, is_manual)
            # 索引: 0=id, 1=name, 2=color, 3=icon, 4=start_time, 5=end_time, 6=duration_seconds, 7=note, 8=status, 9=is_manual
            activity = record[1]  # activity name
            note = record[7] or ""  # note
            # 确保 duration 为整数
            duration = record[6] or 0  # duration_seconds
            if isinstance(duration, str):
                try:
                    duration = int(float(duration))
                except (ValueError, TypeError):
                    duration = 0
            else:
                duration = int(duration) if duration else 0
            
            groups[activity]["total"] += duration
            total_all += duration
            
            if note:
                groups[activity]["notes"].append(note)
                groups[activity]["ids"].extend(cls.extract_ids(note))
        
        return groups, total_all
    
    @classmethod
    def generate_text_report(cls, groups: Dict[str, Any], total_all: int) -> str:
        """生成文本报告
        
        Args:
            groups: 分组数据
            total_all: 总时长
            
        Returns:
            格式化后的报告文本
        """
        lines = []
        
        # 按总时长降序排序
        sorted_activities = sorted(
            groups.items(), 
            key=lambda x: x[1]['total'], 
            reverse=True
        )
        
        for activity, data in sorted_activities:
            duration_str = cls.format_duration(data["total"])
            lines.append(f"{activity}: 共计{duration_str}")
            
            if data["notes"]:
                # 去重并合并备注
                unique_notes = sorted(list(set(data["notes"])))
                merged_notes = "；".join(unique_notes)
                lines.append(f"项目内容: {merged_notes}")
            
            if data["ids"]:
                # 去重并排序ID
                unique_ids = sorted(set(data["ids"]), key=lambda x: int(x) if x.isdigit() else x)
                lines.append(f"    添加{','.join(unique_ids)}数据")
            else:
                lines.append(f"    无具体数据编号")
            
            lines.append("")  # 空行分隔
        
        lines.append("-" * 30)
        lines.append(f"所有项目总时长: {cls.format_duration(total_all)}")
        
        return "\n".join(lines)
