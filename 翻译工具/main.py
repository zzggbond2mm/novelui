#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Callable

import config
import utils
# from api_client import ApiClient # Removed
from terminology_manager import TerminologyManager
from file_handler import FileHandler
# from prompt_builder import PromptBuilder # Removed
from progress_tracker import ProgressTracker
from parallel_manager import ParallelTranslationCoordinator
from translator_core import TranslatorAPI, TranslatorPrompts # Added

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="韩中小说自动翻译工具")
    
    parser.add_argument("--novel", required=True, help="小说名称，对应源文件和目标文件的目录名")
    
    # 文件选择相关参数组
    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument("--start", type=int, help="起始文件编号")
    file_group.add_argument("--file", type=int, help="单一文件编号（只翻译这一个文件）")
    file_group.add_argument("--range", help="文件编号范围，格式如 '1-10'")
    
    # 其他参数
    parser.add_argument("--count", type=int, help="要翻译的文件数量（与--start一起使用）")
    parser.add_argument("--force", action="store_true", help="强制重新翻译已完成的文件")
    parser.add_argument("--reset", action="store_true", help="重置进度（慎用）")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    parser.add_argument("--parallel", action="store_true", help="启用并行翻译模式")
    parser.add_argument("--workers", type=int, default=config.DEFAULT_WORKERS, help=f"并行工作线程数量（默认为{config.DEFAULT_WORKERS}）")
    
    args = parser.parse_args()
    
    # 参数验证和处理
    if args.file is not None:
        args.start = args.file
        args.count = 1
    elif args.range is not None:
        try:
            start, end = map(int, args.range.split('-'))
            args.start = start
            args.count = end - start + 1
        except ValueError:
            parser.error("--range 参数格式无效，应为 'START-END'，例如 '1-10'")
    
    return args

# Renamed from process_single_file and parameters changed
def _process_single_file_logic(
    file_number: int,
    korean_text: str,
    file_name: str,
    file_handler: FileHandler,
    translator_api: TranslatorAPI,
    translator_prompts: TranslatorPrompts,
    formatted_terminology: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    核心单文件翻译与术语提取逻辑（不含进度标记或术语库直接更新）。
    返回翻译API调用是否成功，翻译后的文本（如果成功），以及术语提取API的响应（如果成功）。
    """
    try:
        logging.debug(f"_process_single_file_logic: File {file_name} (Num {file_number}) - Korean len {len(korean_text)}, Terminology len {len(formatted_terminology)}")
        # 步骤1: 构建翻译提示
        translation_prompt = translator_prompts.build_translation_prompt(korean_text, formatted_terminology)
        
        # 步骤2: 调用API进行翻译
        chinese_text = translator_api.translate(translation_prompt, temperature=0.1)
        
        if not chinese_text or not isinstance(chinese_text, str) or len(chinese_text.strip()) < 10:
            logging.error(f"API返回的翻译结果无效或过短 for file {file_name}: {chinese_text[:100]}...")
            # No specific error type to throw here that TranslatorAPI wouldn't have already for severe issues
            return False, None, None # Indicate translation failure

        # 步骤3: 保存翻译结果 (由调用者决定是否以及何时保存，这里仅返回文本)
        # output_path = file_handler.write_output_file(chinese_text, file_number) 
        # logging.info(f"File {file_name} translated, output temporarily in memory.")

        # 步骤4: 构建术语更新提示
        terminology_update_prompt = translator_prompts.build_terminology_update_prompt(
            korean_text, chinese_text, formatted_terminology)
        
        # 步骤5: 调用API提取术语建议
        new_terms_response = None
        try:
            new_terms_response = translator_api.extract_terms(terminology_update_prompt, temperature=0.01)
        except Exception as e_term_extract:
            # Log error in term extraction, but main translation is successful
            logging.warning(f"File {file_name}: 术语提取API调用失败: {str(e_term_extract)}. 翻译仍视为成功。")
            # new_terms_response remains None

        # 主要翻译流程视为成功，返回译文和术语提取响应（可能为None）
        return True, chinese_text, new_terms_response
            
    except Exception as e_translate:
        # 主翻译流程或提示构建中的错误 (TranslatorAPI.translate 会抛出自己的详细错误)
        logging.error(f"_process_single_file_logic for file {file_name} (Num {file_number}) 失败: {str(e_translate)}")
        return False, None, None

def continuous_translation(novel_name: str, start_num: Optional[int] = None, 
                         count: Optional[int] = None, force: bool = False,
                         parallel: bool = False, num_workers: int = config.DEFAULT_WORKERS):
    """连续翻译多个文件"""
    try:
        # 初始化通用组件
        progress_tracker = ProgressTracker(novel_name)
        file_handler = FileHandler(novel_name)
        
        logging.info("=" * 50)
        logging.info("韩中小说自动翻译工具启动")
        logging.info(f"小说名称: {novel_name}")
        logging.info(f"翻译模式: {'并行' if parallel else '串行'}")
        if parallel:
            logging.info(f"工作线程数: {num_workers}")
        logging.info("=" * 50)
        
        if hasattr(config, 'self_check'):
            config.self_check()
        
        file_numbers = file_handler.get_file_numbers()
        if not file_numbers:
            logging.error(f"未找到任何源文件，请检查小说目录: {config.SOURCE_ROOT_DIR}/{novel_name}")
            return False # Changed from return to return False for consistency
            
        # 确定要处理的文件列表 (target_files)
        target_files: List[int] = []
        if start_num is not None:
            if start_num not in file_numbers:
                logging.error(f"起始文件编号 {start_num} 不存在于文件列表 {file_numbers}")
                return False
            start_idx = file_numbers.index(start_num)
            if count is not None:
                end_idx = min(start_idx + count, len(file_numbers))
                target_files = file_numbers[start_idx:end_idx]
            else:
                target_files = file_numbers[start_idx:]
        else: # start_num is None
            if force:
                target_files = file_numbers
            else:
                completed_set = progress_tracker.get_completed_files_set() # Now using the new method
                target_files = [f_num for f_num in file_numbers if f_num not in completed_set]
            
            if count is not None and target_files: # Apply count if not processing all from start
                target_files = target_files[:count]
                
        if not target_files:
            logging.info("没有需要处理的文件（可能已全部完成或范围无效）。")
            # 检查是否所有文件都已完成
            if not force and len(progress_tracker.get_completed_files_set()) == len(file_numbers) and len(file_numbers)>0 :
                 logging.info("所有文件均已翻译完成！")
            elif len(file_numbers) == 0:
                 logging.info("源目录中没有文件。")
            return True
        
        logging.info(f"计划处理文件: {target_files}")

        if parallel:
            logging.info(f"开始并行翻译流程: 共 {len(target_files)} 个文件")
            # ParallelTranslationCoordinator 将需要适配新的 _process_single_file_logic
            # 它内部会创建 TranslatorAPI 实例 (可能每个 worker 一个，通过 ApiKeyRotator 管理 key)
            # 和 TranslatorPrompts 实例 (共享)
            # TerminologyManager 实例也需要共享并使用锁
            coordinator = ParallelTranslationCoordinator(
                novel_name=novel_name, 
                num_workers=num_workers,
                # 将 _process_single_file_logic 作为回调传递，或者 Coordinator 内部调用它
                # 这部分需要进一步设计 ParallelTranslationCoordinator 的接口
                )
            # The run_parallel_translation method will also need adjustment
            # to correctly use/pass instances or configurations for TranslatorAPI/TranslatorPrompts
            # and manage TerminologyManager共享与锁
            return coordinator.run_parallel_translation(target_files, force, _process_single_file_logic_ref=_process_single_file_logic)

        else: # 串行翻译模式
            logging.info(f"开始串行翻译流程: 共 {len(target_files)} 个文件")
            
            # 初始化串行模式所需的组件实例
            terminology_manager = TerminologyManager(novel_name) # 每个小说一个实例
            
            translator_prompts = TranslatorPrompts(
                translate_prompt_file_path=config.TRANSLATE_PROMPT_FILE,
                term_update_prompt_file_path=config.UPDATE_PROMPT_FILE
            )
            
            # 为串行模式创建一个 TranslatorAPI 实例
            # 这些参数从 config.py 获取
            # 注意：config.py 中特定错误的重试次数是全局的，不是按 translate/terms 区分的
            # TranslatorAPI 的 __init__ 已处理此情况 (如果特定重试次数为None，则用通用次数)
            translator_api_serial = TranslatorAPI(
                api_key=config.API_KEY, # 主 API Key
                api_url=config.API_URL,
                model_name=config.MODEL_NAME,
                api_timeout=config.API_TIMEOUT,
                max_retries_translate=config.MAX_RETRIES, 
                max_retries_terms=config.MAX_RETRIES + 2, # 保持旧逻辑，术语提取多两次重试
                retry_delay=config.RETRY_DELAY,
                max_retry_delay=config.MAX_RETRY_DELAY,
                network_error_retries=config.NETWORK_ERROR_RETRIES,
                parse_error_retries=config.PARSE_ERROR_RETRIES,
                timeout_error_retries=config.TIMEOUT_ERROR_RETRIES
            )
            
            start_time_processing = time.time()
            files_processed_count = 0
            files_succeeded_count = 0
            
            for i, file_num_to_process in enumerate(target_files):
                logging.info("-" * 30)
                logging.info(f"串行处理文件 {i+1}/{len(target_files)} (编号 {file_num_to_process})")
                
                success, translated_content, terms_api_response = _process_single_file_logic(
                    file_number=file_num_to_process,
                    korean_text=korean_text_content, # Fetched before calling
                    file_name=actual_file_name,    # Fetched before calling
                    file_handler=file_handler,
                    translator_api=translator_api_serial,
                    translator_prompts=translator_prompts,
                    formatted_terminology=terms_for_prompt # Fetched before calling
                )
                
                files_processed_count += 1
                if success:
                    files_succeeded_count += 1
                
                # 显示进度
                elapsed = time.time() - start_time_processing
                avg_speed = files_processed_count / elapsed if elapsed > 0 else 0
                eta_seconds = (elapsed / files_processed_count) * (len(target_files) - files_processed_count) if files_processed_count > 0 else 0
                
                logging.info(f"进度: {files_processed_count}/{len(target_files)} "
                             f"({(files_processed_count/len(target_files))*100:.1f}%)")
                if files_processed_count > 0 : # 避免除零
                    logging.info(f"成功率: {files_succeeded_count}/{files_processed_count} "
                                 f"({(files_succeeded_count/files_processed_count)*100:.1f}%)")
                logging.info(f"耗时: {utils.format_time_seconds(elapsed)}, "
                             f"速度: {avg_speed:.2f}个/秒, "
                             f"预计剩余: {utils.format_time_seconds(eta_seconds) if eta_seconds > 0 else 'N/A'}")
            
            total_processing_time = time.time() - start_time_processing
            logging.info("=" * 50)
            logging.info(f"串行翻译任务完成。共处理 {files_processed_count} 个文件, 成功 {files_succeeded_count} 个。")
            logging.info(f"总耗时: {utils.format_time_seconds(total_processing_time)}")
            logging.info("=" * 50)
            return files_succeeded_count == files_processed_count and files_processed_count > 0

    except FileNotFoundError as fnf_error:
        logging.error(f"初始化失败: {str(fnf_error)}")
        return False
    except ValueError as val_error: # 例如API Key未配置等从TranslatorAPI构造函数抛出
        logging.error(f"配置或参数错误: {str(val_error)}")
        return False
    except Exception as e_main:
        logging.error(f"翻译流程发生未预期错误: {str(e_main)}", exc_info=True)
        return False

def main():
    """主函数入口"""
    args = parse_arguments()
    
    # 设置日志
    # utils.setup_logging(debug=args.debug, log_dir=config.LOG_DIR, log_file_name="translation.log")
    # 使用 config.py 中更完整的日志配置
    utils.setup_logging(
        log_level=logging.DEBUG if args.debug else config.LOG_LEVEL,
        log_file=config.LOG_FILE,
        log_format=config.LOG_FORMAT,
        backup_count=config.LOG_BACKUP_COUNT,
        max_bytes=config.LOG_MAX_BYTES
    )

    # 验证配置 (例如 API Key, 模板文件等)
    # 应该在日志设置之后，以便错误可以被记录
    try:
        if hasattr(config, 'validate_config'):
            config.validate_config()
    except ValueError as e: # validate_config 可能会抛出 ValueError
        logging.error(f"配置验证失败，程序无法启动: {e}")
        sys.exit(1)


    if args.reset:
        try:
            # 重置需要 novel_name
            if args.novel:
                temp_progress_tracker = ProgressTracker(args.novel)
                temp_progress_tracker.reset_progress()
                logging.info(f"小说《{args.novel}》的进度已重置。")
            else:
                logging.error("重置进度需要提供 --novel 参数。")
                sys.exit(1)
        except Exception as e_reset:
            logging.error(f"重置进度时发生错误: {str(e_reset)}")
            sys.exit(1)
        # 重置后，通常不继续执行翻译，除非用户有其他操作
        # 根据需求，可以选择在此处退出或提示用户
        logging.info("如果需要开始新的翻译，请重新运行命令而不带 --reset 参数。")
        sys.exit(0)

    # 运行翻译任务
    success = continuous_translation(
        novel_name=args.novel,
        start_num=args.start,
        count=args.count,
        force=args.force,
        parallel=args.parallel,
        num_workers=args.workers
    )
    
    if success:
        logging.info("所有指定任务已成功完成。")
        sys.exit(0)
    else:
        logging.error("部分或全部任务失败。请检查日志获取详细信息。")
        sys.exit(1)

if __name__ == '__main__':
    main() 