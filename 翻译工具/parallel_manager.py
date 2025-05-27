#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行翻译管理器模块 - 处理并行翻译相关的各种组件
包括API密钥轮换、术语库锁定机制和并行翻译协调器
"""

import os
import time
import logging
import threading
import queue
from typing import List, Dict, Any, Optional, Tuple, Set, Callable, Type
from datetime import datetime, timedelta
import requests

import config
from translator_core import TranslatorAPI, TranslatorPrompts
from file_handler import FileHandler
from terminology_manager import TerminologyManager
from progress_tracker import ProgressTracker
from prompt_builder import PromptBuilder

# 类型提示，用于 process_single_file_logic_ref
_ProcessFunctionType = Callable[[
    int, str, str, FileHandler, TranslatorAPI, TranslatorPrompts, str, ProgressTracker
], Tuple[bool, Optional[str], Optional[str]]]

class ApiKeyRotator:
    """API密钥轮换器 - 管理多个API密钥并在需要时自动轮换"""
    
    def __init__(self, api_keys: List[str]):
        """
        初始化API密钥轮换器
        
        参数:
            api_keys: API密钥列表
        """
        if not api_keys:
            raise ValueError("没有提供API密钥")
        
        self.api_keys = api_keys
        self.current_index = 0
        self.lock = threading.RLock()  # 可重入锁，确保线程安全
        self.error_counts = {key: 0 for key in api_keys}  # 记录每个密钥的错误次数
        self.usage_counts = {key: 0 for key in api_keys}  # 记录每个密钥的使用次数
        self.last_used = {key: None for key in api_keys}  # 记录每个密钥的上次使用时间
        
        # 使用集合记录暂时禁用的密钥
        self.disabled_keys = set()  
        self.disabled_until = {}  # 记录密钥禁用到的时间
        
        logging.info(f"API密钥轮换器初始化成功，共加载 {len(api_keys)} 个密钥")
    
    def get_next_key(self) -> Optional[str]:
        """
        获取下一个可用的API密钥
        
        返回:
            下一个可用的API密钥
        """
        with self.lock:
            self._check_disabled_keys()
            
            available_keys = [k for k in self.api_keys if k not in self.disabled_keys]
            if not available_keys:
                logging.warning("所有API密钥当前都已禁用。正在尝试恢复...")
                if not self.api_keys:
                    logging.error("ApiKeyRotator: API密钥列表为空，无法提供密钥。")
                    return None
                logging.error("所有API密钥都不可用，将强制使用第一个密钥尝试。")
                logging.error("ApiKeyRotator: 没有可用的API密钥。")
                return None 

            start_idx = self.current_index % len(self.api_keys)
            for i in range(len(self.api_keys)):
                check_idx = (start_idx + i) % len(self.api_keys)
                key = self.api_keys[check_idx]
                if key in available_keys:
                    self.current_index = check_idx
                    self.usage_counts[key] += 1
                    self.last_used[key] = datetime.now()
                    return key
            
            logging.error("ApiKeyRotator: 逻辑错误，未能从available_keys中选择一个密钥。")
            return None 

    def _check_disabled_keys(self) -> None:
        """检查并恢复暂时禁用的密钥"""
        now = datetime.now()
        keys_to_enable = []
        
        for key in list(self.disabled_keys):
            if key in self.disabled_until and now >= self.disabled_until[key]:
                keys_to_enable.append(key)
        
        for key in keys_to_enable:
            self.disabled_keys.remove(key)
            del self.disabled_until[key]
            self.error_counts[key] = 0
            logging.info(f"API密钥 {key[:8]}... 已恢复可用。")
    
    def report_error(self, key: str, error_code: Optional[int] = None, exception: Optional[Exception] = None) -> None:
        """
        报告API密钥的错误
        
        参数:
            key: 发生错误的API密钥
            error_code: 错误代码
            exception: 异常对象
        """
        with self.lock:
            if key not in self.api_keys:
                logging.warning(f"尝试报告未知密钥 {key[:8]}... 的错误。")
                return

            self.error_counts[key] = self.error_counts.get(key, 0) + 1
            error_type = "other"
            disable_duration = timedelta(seconds=60)
            permanent_disable = False

            if isinstance(exception, requests.exceptions.HTTPError):
                error_code = exception.response.status_code
            
            if error_code == 401:
                error_type = "auth"
                permanent_disable = True
                logging.error(f"API密钥 {key[:8]}... 认证失败 (401)。将永久禁用。")
            elif error_code == 429:
                error_type = "rate_limit"
                disable_duration = timedelta(minutes=config.RATE_LIMIT_DISABLE_MINUTES if hasattr(config, 'RATE_LIMIT_DISABLE_MINUTES') else 5)
                logging.warning(f"API密钥 {key[:8]}... 遭遇速率限制 (429)。暂时禁用 {disable_duration.total_seconds() / 60} 分钟。")
            elif isinstance(exception, requests.exceptions.Timeout):
                error_type = "timeout"
                disable_duration = timedelta(seconds=config.TIMEOUT_DISABLE_SECONDS if hasattr(config, 'TIMEOUT_DISABLE_SECONDS') else 30)
                logging.warning(f"API密钥 {key[:8]}... 请求超时。暂时禁用 {disable_duration.total_seconds()} 秒。")
            elif isinstance(exception, requests.exceptions.ConnectionError):
                error_type = "connection_error"
                disable_duration = timedelta(seconds=config.CONNECTION_ERROR_DISABLE_SECONDS if hasattr(config, 'CONNECTION_ERROR_DISABLE_SECONDS') else 45)
                logging.warning(f"API密钥 {key[:8]}... 连接错误。暂时禁用 {disable_duration.total_seconds()} 秒。")
            elif self.error_counts[key] >= (config.MAX_ERRORS_BEFORE_DISABLE if hasattr(config, 'MAX_ERRORS_BEFORE_DISABLE') else 5):
                error_type = "too_many_errors"
                logging.warning(f"API密钥 {key[:8]}... 连续错误次数过多 ({self.error_counts[key]}). 暂时禁用。")
            else:
                logging.info(f"API密钥 {key[:8]}... 发生错误 (类型: {type(exception).__name__ if exception else 'N/A'}, code: {error_code}), 错误次数: {self.error_counts[key]}")
                return

            self.disabled_keys.add(key)
            if not permanent_disable:
                self.disabled_until[key] = datetime.now() + disable_duration
            else:
                if key in self.disabled_until:
                    del self.disabled_until[key]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取API密钥状态信息
        
        返回:
            包含API密钥使用和错误统计的字典
        """
        with self.lock:
            return {
                "total_keys": len(self.api_keys),
                "active_keys": len(self.api_keys) - len(self.disabled_keys),
                "disabled_keys": list(self.disabled_keys),
                "usage_counts": self.usage_counts.copy(),
                "error_counts": self.error_counts.copy(),
                "disabled_until": {k[:8]+"...": v.strftime('%Y-%m-%d %H:%M:%S') if v else "Permanent" 
                                 for k, v in self.disabled_until.items()}
            }


class TerminologyLock:
    """术语库锁 - 提供对术语库的读写锁机制，允许多个读取但只有一个写入"""
    
    def __init__(self):
        """初始化术语库锁"""
        self._lock = threading.RLock()
        self._readers = 0
    
    def acquire_read(self):
        """获取读锁"""
        self._lock.acquire()
        self._readers += 1
        self._lock.release()
    
    def release_read(self):
        """释放读锁"""
        self._lock.acquire()
        self._readers -= 1
        self._lock.release()
    
    def acquire_write(self):
        """获取写锁（独占）"""
        self._lock.acquire()
    
    def release_write(self):
        """释放写锁"""
        self._lock.release()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.acquire_read()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.release_read()


class ParallelProgressTracker:
    """并行进度跟踪器 - 跟踪多个并行任务的进度"""
    
    def __init__(self, total_files: int, novel_name: str):
        """
        初始化并行进度跟踪器
        
        参数:
            total_files: 总共需要处理的文件数
            novel_name: 小说名称
        """
        self.total_files = total_files
        self.novel_name = novel_name
        self.lock = threading.RLock()
        self.processed_count = 0
        self.success_count = 0
        self.failed_files = set()
        self.in_progress_files = set() 
        self.start_time = datetime.now()
        self.completion_times = []
        self.logger = logging.getLogger(__name__ + ".ParallelProgress")
    
    def file_started(self, file_num: int):
        with self.lock:
            self.in_progress_files.add(file_num)
            self.logger.info(f"Novel '{self.novel_name}', Worker starting file: {file_num}")
    
    def file_completed(self, file_num: int, success: bool, duration: float):
        with self.lock:
            self.processed_count += 1
            if file_num in self.in_progress_files:
                self.in_progress_files.remove(file_num)
            
            if success:
                self.success_count += 1
                self.completion_times.append(duration)
                if len(self.completion_times) > 20:
                    self.completion_times.pop(0)
            else:
                self.failed_files.add(file_num)
            
            self.log_progress()
    
    def log_progress(self):
        with self.lock:
            if self.processed_count == 0:
                return

            percentage = (self.processed_count / self.total_files) * 100
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            avg_time_per_file = sum(self.completion_times) / len(self.completion_times) if self.completion_times else elapsed_time / self.processed_count
            
            eta_seconds = 0
            if avg_time_per_file > 0 and self.processed_count < self.total_files:
                remaining_files = self.total_files - self.processed_count
                eta_seconds = remaining_files * avg_time_per_file
            
            self.logger.info(
                f"Novel '{self.novel_name}' Parallel Progress: "
                f"{self.processed_count}/{self.total_files} ({percentage:.2f}%) done. "
                f"Success: {self.success_count}, Failed: {len(self.failed_files)}. "
                f"Elapsed: {utils.format_time_seconds(elapsed_time)}. "
                f"Avg: {avg_time_per_file:.2f}s/file. "
                f"ETA: {utils.format_time_seconds(eta_seconds) if eta_seconds > 0 else 'N/A'}. "
                f"In Progress: {len(self.in_progress_files)} files."
            )
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        return utils.format_time_seconds(seconds)

    def get_summary(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "total_files": self.total_files,
                "processed": self.processed_count,
                "succeeded": self.success_count,
                "failed": len(self.failed_files),
                "failed_list": sorted(list(self.failed_files)),
                "start_time": self.start_time.isoformat(),
                "current_time": datetime.now().isoformat(),
                "elapsed_seconds": (datetime.now() - self.start_time).total_seconds()
            }


class ParallelTranslationCoordinator:
    """并行翻译协调器 - 管理并行翻译任务"""
    
    def __init__(self, 
                 novel_name: str, 
                 num_workers: int, 
                 process_single_file_logic_ref: _ProcessFunctionType,
                 file_handler: FileHandler,
                 terminology_manager: TerminologyManager,
                 progress_tracker: ProgressTracker
                 ):
        self.novel_name = novel_name
        self.num_workers = max(1, min(num_workers, config.MAX_WORKERS if hasattr(config, 'MAX_WORKERS') else 10))
        self.logger = logging.getLogger(__name__ + ".Coordinator")
        
        self.process_single_file_logic_ref = process_single_file_logic_ref
        
        self.file_handler = file_handler
        self.terminology_manager = terminology_manager
        self.main_progress_tracker = progress_tracker
        
        self.translator_prompts = TranslatorPrompts(
            translate_prompt_file_path=config.TRANSLATE_PROMPT_FILE,
            term_update_prompt_file_path=config.UPDATE_PROMPT_FILE
        )
        
        all_api_keys = config.get_all_api_keys()
        if not all_api_keys:
            self.logger.error("并行模式启动失败：没有可用的API密钥配置。")
            raise ValueError("无法初始化并行协调器：缺少API密钥。")
        self.api_key_rotator = ApiKeyRotator(all_api_keys)
        
        self.terminology_lock = TerminologyLock()
        self.task_queue = queue.Queue()
        self.threads = []
        self.stop_event = threading.Event()
        self.parallel_progress_tracker: Optional[ParallelProgressTracker] = None
        self.logger.info(f"并行翻译协调器初始化: {self.num_workers} 工作线程 for novel '{self.novel_name}'")
    
    def schedule_translations(self, start_num: int, count: int, force: bool = False) -> None:
        """
        安排翻译任务
        
        参数:
            start_num: 起始文件编号
            count: 文件数量
            force: 是否强制重新翻译
        """
        self.parallel_progress_tracker = ParallelProgressTracker(count, self.novel_name)
        
        for file_num in range(start_num, start_num + count):
            self.task_queue.put((file_num, force))
        
        logging.info(f"已安排 {count} 个翻译任务，起始文件编号: {start_num}")
    
    def run_parallel_translation(self, target_files: List[int], force: bool = False) -> bool:
        """
        执行并行翻译任务
        
        参数:
            target_files: 要处理的文件编号列表
            force: 是否强制重新翻译已完成的文件
            
        返回:
            是否成功处理了至少一个文件
        """
        try:
            self.parallel_progress_tracker = ParallelProgressTracker(len(target_files), self.novel_name)
            
            for file_num in target_files:
                self.task_queue.put((file_num, force))
            
            start_time = time.time()
            logging.info(f"开始并行翻译: 共计 {len(target_files)} 个文件, {self.num_workers} 个工作线程")
            
            self.start()
            
            log_interval = 30
            last_log_time = start_time
            
            max_wait_time = len(target_files) * config.API_TIMEOUT * 1.5
            timeout_flag = not self.wait_completion(timeout=max_wait_time)
            
            if timeout_flag:
                logging.warning(f"并行翻译在指定时间内未能完成，已处理 {self.parallel_progress_tracker.processed_count} 个文件")
            
            self.stop()
            
            total_time = time.time() - start_time
            
            progress_info = self.parallel_progress_tracker.get_summary()
            
            logging.info("=" * 50)
            logging.info(f"并行翻译任务{'超时结束' if timeout_flag else '完成'}")
            logging.info(f"总文件数: {len(target_files)}")
            logging.info(f"成功处理: {progress_info['succeeded']}")
            logging.info(f"处理失败: {progress_info['failed']}")
            logging.info(f"总耗时: {progress_info['elapsed_seconds']}")
            logging.info(f"平均速度: {progress_info['succeeded'] / total_time:.2f}个/秒")
            logging.info("=" * 50)
            
            key_status = self.api_key_rotator.get_status()
            logging.info(f"API密钥使用情况: 共{key_status['total_keys']}个, "
                        f"活跃{key_status['active_keys']}个, 禁用{key_status['disabled_keys']}个")
            
            return progress_info['succeeded'] > 0
            
        except Exception as e:
            logging.error(f"并行翻译过程中发生错误: {str(e)}")
            try:
                self.stop()
            except:
                pass
            return False
    
    def start(self) -> None:
        """启动工作线程"""
        if not self.parallel_progress_tracker:
            raise ValueError("未安排任务，无法启动")
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                args=(i,),
                name=f"Translator-{i+1}"
            )
            worker.daemon = True
            worker.start()
            self.threads.append(worker)
        
        logging.info(f"并行翻译已启动，{self.num_workers} 个工作线程正在运行")
    
    def _worker_thread(self, worker_id: int) -> None:
        """
        工作线程函数
        
        参数:
            worker_id: 工作线程ID
        """
        api_client = ApiClient(api_key="")
        
        logging.info(f"工作线程 {worker_id+1} 已启动")
        
        try:
            while not self.stop_event.is_set():
                try:
                    file_num, force = self.task_queue.get(timeout=1)
                    
                    self.parallel_progress_tracker.file_started(file_num)
                    logging.info(f"工作线程 {worker_id+1} 开始处理文件 {file_num}")
                    
                    api_key = self.api_key_rotator.get_next_key()
                    api_client.set_api_key(api_key)
                    
                    success, translated_text, error_message = self.process_single_file_logic_ref(
                        file_num, api_key, self.novel_name, self.file_handler, self.translator_prompts, api_client, self.terminology_manager, translated_text, self.main_progress_tracker
                    )
                    
                    self.parallel_progress_tracker.file_completed(file_num, success, (datetime.now() - self.parallel_progress_tracker.start_time).total_seconds())
                    
                    if file_num % 5 == 0 or not success:
                        self.parallel_progress_tracker.log_progress()
                    
                    self.task_queue.task_done()
                    
                except Exception as e:
                    logging.error(f"工作线程 {worker_id+1} 处理文件时发生错误: {str(e)}")
                    try:
                        self.task_queue.task_done()
                    except:
                        pass
        except Exception as e:
            logging.error(f"工作线程 {worker_id+1} 发生未处理异常: {str(e)}")
        
        logging.info(f"工作线程 {worker_id+1} 已结束")
    
    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有任务完成
        
        参数:
            timeout: 最大等待时间（秒）
            
        返回:
            是否所有任务都已完成
        """
        start_time = time.time()
        log_interval = 30
        last_log_time = start_time
        
        while not self.task_queue.empty() or any(w.is_alive() for w in self.threads):
            if timeout and time.time() - start_time > timeout:
                logging.warning(f"等待完成超时 ({timeout}秒)")
                return False
            
            current_time = time.time()
            if current_time - last_log_time >= log_interval:
                self.parallel_progress_tracker.log_progress()
                last_log_time = current_time
            # 如果目标文件已存在且不强制重新翻译，则跳过
            if not force and self.file_handler.check_output_exists(file_num):
                logging.info(f"文件 {file_num} 已翻译，跳过")
                return True
            
            # 构建翻译提示
            with self.terminology_lock:  # 获取读锁
                terminology = self.terminology_manager.get_formatted_terminology()
                
                # 初始化 PromptBuilder
                prompt_builder = PromptBuilder()
                
                # 构建翻译提示
                prompt = prompt_builder.build_translation_prompt(source_content, terminology)
            
            # 调用API翻译
            try:
                translation = api_client.translate_text(prompt)
                if not translation:
                    raise ValueError("翻译结果为空")
            except Exception as e:
                error_type = 'timeout' if 'timeout' in str(e).lower() else 'other'
                if 'rate' in str(e).lower() and 'limit' in str(e).lower():
                    error_type = 'rate_limit'
                elif 'auth' in str(e).lower() or 'key' in str(e).lower() and 'invalid' in str(e).lower():
                    error_type = 'auth'
                
                # 报告API密钥错误
                self.key_rotator.report_error(api_client.api_key, error_type)
                raise
            
            # 保存翻译结果
            self.file_handler.write_output_file(translation, file_num)
            
            # 更新术语库
            try:
                # 步骤1: 构建术语更新提示
                terminology = self.terminology_manager.get_formatted_terminology()
                
                # 初始化 PromptBuilder
                prompt_builder = PromptBuilder()
                
                # 构建术语更新提示
                terminology_prompt = prompt_builder.build_terminology_update_prompt(
                    source_content, translation, terminology)
                
                # 步骤2: 调用API更新术语库
                new_terms = api_client.update_terminology(terminology_prompt)
                
                # 步骤3: 更新术语库
                if new_terms and isinstance(new_terms, str):
                    char_added, noun_added, expr_added = self.terminology_manager.update_terminology_from_api_response(new_terms)
                    logging.info(f"文件 {file_num} 术语库更新: {char_added}人物, {noun_added}专有名词, {expr_added}文化表达")
            except Exception as e:
                logging.warning(f"更新术语库时发生错误: {str(e)}")
            
            return True
        
        except Exception as e:
            logging.error(f"处理文件 {file_num} 时发生错误: {str(e)}")
            return False
    
    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有任务完成
        
        参数:
            timeout: 最大等待时间（秒）
            
        返回:
            是否所有任务都已完成
        """
        start_time = time.time()
        log_interval = 30  # 每30秒记录一次进度
        last_log_time = start_time
        
        while not self.task_queue.empty() or any(w.is_alive() for w in self.workers):
            # 检查超时
            if timeout and time.time() - start_time > timeout:
                logging.warning(f"等待完成超时 ({timeout}秒)")
                return False
            
            # 定期记录进度
            current_time = time.time()
            if current_time - last_log_time >= log_interval:
                self.progress_tracker.log_progress()
                last_log_time = current_time
            
            # 小睡片刻
            time.sleep(1)
        
        # 最终进度
        self.progress_tracker.log_progress()
        
        # 记录API密钥使用情况
        key_status = self.key_rotator.get_status()
        logging.info(f"API密钥使用情况: 共{key_status['total_keys']}个密钥, "
                    f"活跃{key_status['active_keys']}个, 禁用{key_status['disabled_keys']}个")
        
        return True
    
    def stop(self) -> None:
        """停止所有翻译任务"""
        logging.info("正在停止并行翻译...")
        self.should_terminate.set()
        
        # 等待所有工作线程结束
        for worker in self.workers:
            worker.join(2)  # 最多等待2秒
        
        logging.info("并行翻译已停止") 