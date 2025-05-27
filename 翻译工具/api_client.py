import json
import logging
import time
import requests
import re
import random
from typing import Dict, List, Any, Optional, Tuple, Union

import config

class ApiClient:
    """负责与自定义API交互，处理翻译请求和术语更新请求"""
    
    def __init__(self, api_key=None):
        """初始化API客户端
        
        参数:
            api_key: 可选，API密钥（如果不提供则使用配置中的默认密钥）
        """
        # 使用提供的API密钥或者配置中的默认密钥
        self.api_key = api_key or config.API_KEY
        
        if not self.api_key:
            error_msg = "API密钥未设置，无法初始化API客户端"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        self.api_url = config.API_URL
        self.model = config.MODEL_NAME
        
        # 显示部分密钥以便于日志识别不同客户端
        masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
        logging.info(f"初始化API客户端，API密钥: {masked_key}")
        logging.info(f"使用模型: {self.model}")
    
    def set_api_key(self, api_key):
        """设置新的API密钥"""
        if not api_key:
            raise ValueError("API密钥不能为空")
        self.api_key = api_key
        masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
        logging.info(f"已切换API密钥: {masked_key}")
            
    def _make_api_call(self, prompt: str, temperature: float = 0.1, max_retries: int = None, request_type: str = "翻译") -> str:
        """
        执行API调用
        
        参数:
            prompt: 提示文本
            temperature: 温度参数（控制随机性）
            max_retries: 最大重试次数（如果为None则使用配置值）
            request_type: 请求类型，用于错误处理（翻译/术语更新）
            
        返回:
            API响应文本
        """
        # 根据请求类型选择对应的重试策略
        if max_retries is None:
            if request_type == "翻译":
                max_retries = config.MAX_RETRIES
            elif request_type == "术语更新":
                # 术语更新可以更激进地重试
                max_retries = config.MAX_RETRIES + 2
            else:
                max_retries = config.MAX_RETRIES
            
        retry_count = 0
        last_error = None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 使用OpenAI格式的请求数据
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        while retry_count <= max_retries:
            try:
                # 调用API前记录尝试次数
                if retry_count > 0:
                    logging.info(f"API调用重试 ({retry_count}/{max_retries})...")
                
                # 调用API
                logging.debug(f"API请求数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                
                # 添加请求开始时间记录
                request_start_time = time.time()
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=config.API_TIMEOUT
                )
                request_duration = time.time() - request_start_time
                
                # 记录API响应时间
                logging.info(f"API响应时间: {request_duration:.2f}秒")
                
                response.raise_for_status()  # 抛出HTTP错误
                result = response.json()
                logging.debug(f"API响应原始数据: {json.dumps(result, ensure_ascii=False)[:500]}...")
                
                # 获取并返回响应文本 - 适配OpenAI格式
                if "choices" in result and len(result["choices"]) > 0:
                    if "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                        response_text = result["choices"][0]["message"]["content"]
                    elif "text" in result["choices"][0]:
                        response_text = result["choices"][0]["text"]
                    else:
                        response_text = str(result["choices"][0])
                elif "content" in result:
                    response_text = result["content"]
                else:
                    response_text = str(result)
                
                # 检查响应是否为空或过短
                if not response_text or len(response_text.strip()) < 5:
                    raise ValueError(f"API返回内容为空或过短: '{response_text}'")
                
                # 移除思考过程 <think>...</think>
                response_text = self._remove_thinking(response_text)
                
                logging.info(f"API调用成功，响应长度: {len(response_text)} 字符")
                return response_text
                
            except requests.exceptions.Timeout as e:
                retry_count += 1
                last_error = f"请求超时: {str(e)}"
                # 超时错误使用专门的重试策略
                should_retry = retry_count <= config.TIMEOUT_ERROR_RETRIES
                
            except requests.exceptions.ConnectionError as e:
                retry_count += 1
                last_error = f"连接错误: {str(e)}"
                # 网络错误使用专门的重试策略
                should_retry = retry_count <= config.NETWORK_ERROR_RETRIES
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                last_error = f"请求异常: {str(e)}"
                should_retry = retry_count <= max_retries
                
            except (ValueError, json.JSONDecodeError) as e:
                retry_count += 1
                last_error = f"解析错误: {str(e)}"
                # 解析错误使用专门的重试策略
                should_retry = retry_count <= config.PARSE_ERROR_RETRIES
                
            except Exception as e:
                retry_count += 1
                last_error = f"未知错误: {str(e)}"
                should_retry = retry_count <= max_retries
            
            # 判断是否继续重试
            if should_retry:
                # 计算指数退避延迟，增加随机因子
                sleep_time = min(
                    config.RETRY_DELAY * (2 ** (retry_count - 1)) * (1 + random.random() * 0.2),
                    config.MAX_RETRY_DELAY
                )
                masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
                logging.warning(f"API调用失败 ({retry_count}/{max_retries}) [{masked_key}]: {last_error}")
                logging.info(f"等待 {sleep_time:.1f} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logging.error(f"已达到最大重试次数，放弃API调用")
                break
                    
        # 如果所有重试都失败，则抛出异常
        masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
        error_message = f"API调用失败，已重试 {retry_count} 次: {last_error} [API密钥: {masked_key}]"
        logging.error(error_message)
        raise Exception(error_message)
    
    def _remove_thinking(self, text: str) -> str:
        """移除AI思考过程，也就是<think>...</think>标签之间的内容"""
        # 使用正则表达式匹配<think>...</think>之间的内容并替换为空
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # 如果有移除，记录日志
        if cleaned_text != text:
            logging.debug(f"已移除思考内容，原长度: {len(text)}，新长度: {len(cleaned_text)}")
            
        return cleaned_text
        
    def translate_text(self, prompt: str) -> str:
        """
        翻译文本
        
        参数:
            prompt: 包含待翻译韩文和术语库的完整提示
            
        返回:
            翻译后的中文文本
        """
        logging.info("开始翻译文本...")
        
        try:
            # 对翻译任务使用较低的temperature
            response = self._make_api_call(prompt, temperature=0.1, request_type="翻译")
            return response
            
        except Exception as e:
            logging.error(f"翻译文本时出错: {str(e)}")
            raise
            
    def update_terminology(self, prompt: str) -> str:
        """
        更新术语库
        
        参数:
            prompt: 包含韩文原文、中文译文和现有术语库的提示
            
        返回:
            原始响应文本，由术语管理器负责解析
        """
        logging.info("开始更新术语库...")
        
        try:
            # 对术语提取使用接近0的temperature以确保一致性
            response = self._make_api_call(prompt, temperature=0.01, request_type="术语更新")
            
            # 验证响应不为空
            if not response or len(response.strip()) < 5:
                logging.warning("API返回的术语更新响应内容为空或过短")
                return "术语更新响应为空"
            
            logging.info(f"术语更新API调用成功，响应长度: {len(response)} 字符")
            # 返回原始响应文本，由术语管理器负责解析
            return response
                
        except Exception as e:
            error_msg = f"更新术语库时出错: {str(e)}"
            logging.error(error_msg)
            
            # 返回错误信息但不终止进程
            return f"术语更新失败: {str(e)}"
    
    def _extract_json(self, text: str) -> str:
        """
        从文本中提取JSON格式内容
        
        参数:
            text: 包含JSON的文本
            
        返回:
            提取出的JSON文本，如果没有找到则返回空字符串
        """
        # 匹配```json ... ```格式
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, text)
        if match:
            return match.group(1).strip()
            
        # 匹配[{...}]格式（直接的JSON数组）
        array_pattern = r'\[\s*\{\s*"type"\s*:.*\}\s*\]'
        match = re.search(array_pattern, text)
        if match:
            return match.group(0).strip()
            
        # 尝试匹配任何看起来像JSON的内容
        bracket_pattern = r'\[\s*[\{\[][\s\S]*?[\}\]]\s*\]'
        match = re.search(bracket_pattern, text)
        if match:
            return match.group(0).strip()
            
        return "" 