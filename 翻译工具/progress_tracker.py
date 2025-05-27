import os
import json
import logging
import time
from typing import Dict, List, Optional, Set

import config

class ProgressTracker:
    """负责跟踪翻译进度，支持断点续译"""
    
    def __init__(self, novel_name: str):
        """
        初始化进度跟踪器
        
        参数:
            novel_name: 小说名称，用于区分不同小说的进度
        """
        self.novel_name = novel_name
        # 每个小说有独立的进度文件
        self.progress_file = os.path.join(config.PROGRESS_DIR, f"{novel_name}_{config.PROGRESS_FILE_NAME}")
        self.completed_files = set()  # 已完成文件编号集合
        self.stats = {
            "total_files": 0,
            "completed_files": 0,
            "last_updated": "",
            "last_file": None,
            "start_time": time.time()
        }
        
        # 加载现有进度
        self._load_progress()
        logging.info(f"初始化进度跟踪器: 小说 '{novel_name}', 已完成 {len(self.completed_files)} 个文件")
        
    def _load_progress(self) -> None:
        """加载现有的进度文件"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 加载已完成文件列表
                if "completed_files" in data:
                    self.completed_files = set(data["completed_files"])
                
                # 加载统计信息
                if "stats" in data:
                    self.stats.update(data["stats"])
                    
                logging.info(f"成功加载翻译进度: {len(self.completed_files)} 个已完成文件")
            else:
                logging.info(f"未找到进度文件，将创建新进度")
                # 确保目录存在
                os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
                self._save_progress()  # 创建初始进度文件
        except Exception as e:
            logging.error(f"加载进度文件时出错: {str(e)}")
            # 出错时使用空进度，但不要覆盖现有文件
            self.completed_files = set()
            
    def _save_progress(self) -> None:
        """保存当前进度到文件"""
        try:
            # 更新统计信息
            self.stats["completed_files"] = len(self.completed_files)
            self.stats["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 准备保存的数据
            data = {
                "novel_name": self.novel_name,
                "completed_files": list(self.completed_files),
                "stats": self.stats
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
            
            # 写入进度文件
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logging.debug(f"进度已保存: {len(self.completed_files)} 个已完成文件")
        except Exception as e:
            logging.error(f"保存进度文件时出错: {str(e)}")
            
    def is_completed(self, file_number: int) -> bool:
        """
        检查指定编号的文件是否已完成翻译
        
        参数:
            file_number: 文件编号
            
        返回:
            是否已完成（布尔值）
        """
        return file_number in self.completed_files
        
    def mark_completed(self, file_number: int) -> None:
        """
        标记文件为已完成
        
        参数:
            file_number: 文件编号
        """
        self.completed_files.add(file_number)
        self.stats["last_file"] = file_number
        self._save_progress()
        logging.info(f"已标记文件 {file_number} 为完成状态")
        
    def get_completed_files(self) -> List[int]:
        """
        获取所有已完成文件的编号列表
        
        返回:
            已完成文件的编号列表
        """
        return list(self.completed_files)
        
    def get_completed_files_set(self) -> Set[int]:
        """
        获取所有已完成文件的编号集合，用于高效查找。

        返回:
            已完成文件的编号集合。
        """
        return self.completed_files
        
    def get_stats(self) -> Dict:
        """
        获取当前统计信息
        
        返回:
            包含统计数据的字典
        """
        # 计算运行时间
        elapsed = time.time() - self.stats["start_time"]
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # 更新统计信息
        current_stats = self.stats.copy()
        current_stats["elapsed_time"] = f"{int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
        
        if current_stats["completed_files"] > 0 and elapsed > 0:
            # 计算平均每文件耗时
            avg_time = elapsed / current_stats["completed_files"]
            avg_min, avg_sec = divmod(avg_time, 60)
            current_stats["avg_time_per_file"] = f"{int(avg_min)}分钟{int(avg_sec)}秒"
            
            # 计算处理速度
            current_stats["files_per_hour"] = round(current_stats["completed_files"] * 3600 / elapsed, 2)
        
        return current_stats
        
    def get_next_pending_file(self, file_list: List[int]) -> Optional[int]:
        """
        从文件列表中获取下一个未完成的文件编号
        
        参数:
            file_list: 文件编号列表
            
        返回:
            下一个未完成的文件编号，如果所有文件都已完成则返回None
        """
        for file_num in file_list:
            if file_num not in self.completed_files:
                return file_num
        return None
        
    def reset_progress(self) -> None:
        """重置进度（清空已完成文件列表）"""
        self.completed_files = set()
        self.stats["start_time"] = time.time()
        self.stats["completed_files"] = 0
        self.stats["last_file"] = None
        self._save_progress()
        logging.warning("翻译进度已重置") 