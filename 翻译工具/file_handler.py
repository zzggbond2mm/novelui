import os
import logging
import re
from typing import List, Tuple, Optional

import config

class FileHandler:
    """负责处理文件读写操作，包括源文件读取和目标文件写入"""
    
    def __init__(self, novel_name: str):
        """
        初始化文件处理器
        
        参数:
            novel_name: 小说名称，用于确定目录结构
        """
        self.novel_name = novel_name
        self.source_dir = os.path.join(config.SOURCE_ROOT_DIR, novel_name)
        self.output_dir = os.path.join(config.OUTPUT_ROOT_DIR, novel_name)
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        logging.info(f"初始化文件处理器: 小说 '{novel_name}'")
        logging.info(f"源文件目录: {self.source_dir}")
        logging.info(f"输出目录: {self.output_dir}")
        
        # 验证源文件目录是否存在
        if not os.path.exists(self.source_dir):
            logging.error(f"源文件目录不存在: {self.source_dir}")
            raise FileNotFoundError(f"源文件目录不存在: {self.source_dir}")
            
        # 初始化时计算总文件数
        self.total_files = len(self.get_file_numbers())
            
    def get_source_files(self, start_num: Optional[int] = None, count: Optional[int] = None) -> List[str]:
        """
        获取源文件列表，按编号排序
        
        参数:
            start_num: 起始文件编号（可选）
            count: 要处理的文件数量（可选）
            
        返回:
            排序后的源文件路径列表
        """
        # 获取所有指定扩展名的文件
        files = [f for f in os.listdir(self.source_dir) 
                if f.endswith(config.SOURCE_FILE_EXTENSION)]
        
        # 根据文件名中的数字排序
        files.sort(key=lambda f: self._extract_file_number(f))
        
        # 过滤出满足编号范围的文件
        if start_num is not None:
            files = [f for f in files if self._extract_file_number(f) >= start_num]
            
        # 限制文件数量
        if count is not None and count > 0:
            files = files[:count]
            
        # 构建完整路径
        file_paths = [os.path.join(self.source_dir, f) for f in files]
        
        logging.info(f"找到 {len(file_paths)} 个源文件")
        return file_paths
        
    def get_file_numbers(self) -> List[int]:
        """
        获取所有源文件的编号列表
        
        返回:
            按顺序排列的文件编号列表
        """
        try:
            # 获取所有指定扩展名的文件
            files = [f for f in os.listdir(self.source_dir) 
                    if f.endswith(config.SOURCE_FILE_EXTENSION)]
            
            # 提取每个文件的编号
            file_numbers = [self._extract_file_number(f) for f in files]
            
            # 排序并去重
            file_numbers = sorted(set(file_numbers))
            
            logging.info(f"找到 {len(file_numbers)} 个文件编号")
            return file_numbers
        except Exception as e:
            logging.error(f"获取文件编号列表时出错: {str(e)}")
            return []
    
    def get_source_file(self, file_number: int) -> Tuple[str, str]:
        """
        根据文件编号获取源文件内容
        
        参数:
            file_number: 文件编号
            
        返回:
            元组 (文件名, 文件内容)
        """
        try:
            # 查找匹配编号的文件
            for file in os.listdir(self.source_dir):
                if file.endswith(config.SOURCE_FILE_EXTENSION) and self._extract_file_number(file) == file_number:
                    file_path = os.path.join(self.source_dir, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    logging.info(f"成功读取源文件: {file}, 编号: {file_number}, 长度: {len(content)} 字符")
                    return file, content
            
            # 如果找不到匹配的文件
            logging.error(f"未找到编号为 {file_number} 的源文件")
            return "", ""
        except Exception as e:
            logging.error(f"读取源文件时发生错误: {str(e)}")
            return "", ""
        
    def read_source_file(self, file_path: str) -> Tuple[str, str, int]:
        """
        读取源文件内容
        
        参数:
            file_path: 源文件路径
            
        返回:
            元组 (文件内容, 文件名, 文件编号)
        """
        try:
            file_name = os.path.basename(file_path)
            file_number = self._extract_file_number(file_name)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            logging.info(f"成功读取源文件: {file_name}, 编号: {file_number}, 长度: {len(content)} 字符")
            return content, file_name, file_number
            
        except Exception as e:
            logging.error(f"读取源文件时发生错误: {str(e)}")
            raise
            
    def write_output_file(self, content: str, file_number: int) -> str:
        """
        将翻译结果写入输出文件
        
        参数:
            content: 翻译后的内容
            file_number: 文件编号
            
        返回:
            输出文件路径
        """
        try:
            # 格式化文件名 "中_00001.md"
            output_filename = f"{config.OUTPUT_FILE_PREFIX}{file_number:05d}{config.SOURCE_FILE_EXTENSION}"
            output_path = os.path.join(self.output_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logging.info(f"成功写入译文: {output_filename}, 长度: {len(content)} 字符")
            return output_path
            
        except Exception as e:
            logging.error(f"写入译文时发生错误: {str(e)}")
            raise
            
    def check_output_exists(self, file_number: int) -> bool:
        """
        检查指定编号的输出文件是否已存在
        
        参数:
            file_number: 文件编号
            
        返回:
            文件是否存在（布尔值）
        """
        output_filename = f"{config.OUTPUT_FILE_PREFIX}{file_number:05d}{config.SOURCE_FILE_EXTENSION}"
        output_path = os.path.join(self.output_dir, output_filename)
        return os.path.exists(output_path)
        
    def _extract_file_number(self, filename: str) -> int:
        """
        从文件名中提取数字编号
        
        参数:
            filename: 文件名
            
        返回:
            文件编号（整数）
        """
        # 尝试提取数字部分
        match = re.search(r'(\d+)', filename)
        if match:
            return int(match.group(1))
        else:
            # 如果没有找到数字，使用一个非常大的数值作为返回
            logging.warning(f"无法从文件名中提取编号: {filename}")
            return 999999  # 使未命名文件排在最后 