#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告解析工具
用于解析导出的文本报告，提取数据用于可视化
"""

import re
from typing import Dict, List, Tuple

class ReportParser:
    """报告解析器"""
    
    @staticmethod
    def parse_time_str(time_str: str) -> int:
        """解析时间字符串（X小时Y分钟）为分钟数"""
        hours = 0
        minutes = 0
        
        h_match = re.search(r'(\d+)小时', time_str)
        if h_match:
            hours = int(h_match.group(1))
            
        m_match = re.search(r'(\d+)分钟', time_str)
        if m_match:
            minutes = int(m_match.group(1))
            
        return hours * 60 + minutes

    @classmethod
    def parse_report_file(cls, file_path: str) -> List[Dict]:
        """解析报告文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            [{
                'name': str,       # 活动名称
                'minutes': int,    # 时长(分)
                'task_count': int  # 关联的任务ID数量
            }, ...]
        """
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 分割成段落（空行分隔）
            blocks = content.split('\n\n')
            
            for block in blocks:
                lines = block.strip().split('\n')
                if not lines:
                    continue
                    
                first_line = lines[0]
                # 匹配标题行: "工作: 共计5小时30分钟"
                match = re.search(r'^(.+?):\s*共计(.+)$', first_line)
                if not match:
                    continue
                    
                name = match.group(1).strip()
                duration_str = match.group(2).strip()
                
                # 排除总结行
                if "所有项目总时长" in name:
                    continue
                    
                minutes = cls.parse_time_str(duration_str)
                task_count = 0
                
                # 查找包含ID的行
                for line in lines:
                    if "添加" in line and "数据" in line:
                        # 格式: "    添加1,2,3数据"
                        id_match = re.search(r'添加([\d,]+)数据', line)
                        if id_match:
                            ids_str = id_match.group(1)
                            # 过滤空字符串（防止 ',,' 情况）
                            ids = [i for i in ids_str.split(',') if i.strip()]
                            task_count = len(ids)
                            break
                            
                if minutes > 0:
                    data.append({
                        'name': name,
                        'minutes': minutes,
                        'task_count': task_count
                    })
                    
            # 按时长降序
            data.sort(key=lambda x: x['minutes'], reverse=True)
            return data
            
        except Exception as e:
            print(f"解析报告失败: {e}")
            return []
