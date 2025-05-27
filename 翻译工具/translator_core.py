import json
import logging
import time
import requests
import re
import random
from typing import Dict, Any, Optional
import os # 需要 os.path.exists 和 os.path.basename

# 默认重试参数，如果构造函数未提供，则使用这些
DEFAULT_API_TIMEOUT = 600
DEFAULT_MAX_RETRIES_TRANSLATE = 5
DEFAULT_MAX_RETRIES_TERMS = 7 # 术语提取可以多尝试几次
DEFAULT_RETRY_DELAY = 5
DEFAULT_MAX_RETRY_DELAY = 60

class TranslatorAPI:
    """
    负责与大模型API交互，处理文本生成请求（如翻译、术语提取）。
    通过构造函数接收API配置，而不是直接读取全局config。
    """

    def __init__(self, 
                 api_key: str, 
                 api_url: str, 
                 model_name: str,
                 api_timeout: int = DEFAULT_API_TIMEOUT,
                 max_retries_translate: int = DEFAULT_MAX_RETRIES_TRANSLATE,
                 max_retries_terms: int = DEFAULT_MAX_RETRIES_TERMS,
                 retry_delay: int = DEFAULT_RETRY_DELAY,
                 max_retry_delay: int = DEFAULT_MAX_RETRY_DELAY,
                 network_error_retries: Optional[int] = None, # 如果为None，则使用max_retries
                 parse_error_retries: Optional[int] = None,   # 如果为None，则使用max_retries
                 timeout_error_retries: Optional[int] = None  # 如果为None，则使用max_retries
                 ):
        if not api_key:
            raise ValueError("API密钥 (api_key) 不能为空")
        if not api_url:
            raise ValueError("API URL (api_url) 不能为空")
        if not model_name:
            raise ValueError("模型名称 (model_name) 不能为空")

        self.api_key = api_key
        self.api_url = api_url
        self.model_name = model_name
        
        self.api_timeout = api_timeout
        self.max_retries_translate = max_retries_translate
        self.max_retries_terms = max_retries_terms
        self.retry_delay = retry_delay
        self.max_retry_delay = max_retry_delay

        # 特定错误类型的重试次数，如果未提供，则默认为该操作类型的最大重试次数
        self.network_error_retries_translate = network_error_retries or max_retries_translate
        self.parse_error_retries_translate = parse_error_retries or max_retries_translate
        self.timeout_error_retries_translate = timeout_error_retries or max_retries_translate
        
        self.network_error_retries_terms = network_error_retries or max_retries_terms
        self.parse_error_retries_terms = parse_error_retries or max_retries_terms
        self.timeout_error_retries_terms = timeout_error_retries or max_retries_terms

        self.logger = logging.getLogger(__name__ + ".TranslatorAPI")
        masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
        self.logger.info(f"TranslatorAPI 初始化: URL={self.api_url}, Model={self.model_name}, Key={masked_key}")

    def _remove_thinking(self, text: str) -> str:
        """移除AI思考过程，也就是<think>...</think>标签之间的内容"""
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if cleaned_text != text:
            self.logger.debug(f"已移除思考内容，原长度: {len(text)}，新长度: {len(cleaned_text)}")
        return cleaned_text

    def _make_api_call(self, prompt: str, temperature: float, request_type: str) -> str:
        """
        执行API调用。

        参数:
            prompt: 提示文本。
            temperature: 温度参数（控制随机性）。
            request_type: 请求类型 ("translate" 或 "terms")，用于选择重试策略。

        返回:
            API响应文本。
        
        抛出:
            Exception: 如果所有重试均失败。
        """
        if request_type == "translate":
            max_retries = self.max_retries_translate
            network_error_retries = self.network_error_retries_translate
            parse_error_retries = self.parse_error_retries_translate
            timeout_error_retries = self.timeout_error_retries_translate
        elif request_type == "terms":
            max_retries = self.max_retries_terms
            network_error_retries = self.network_error_retries_terms
            parse_error_retries = self.parse_error_retries_terms
            timeout_error_retries = self.timeout_error_retries_terms
        else:
            # 默认使用翻译的重试次数，或者可以抛出错误
            self.logger.warning(f"未知的 request_type: {request_type}，将使用翻译重试策略。")
            max_retries = self.max_retries_translate
            network_error_retries = self.network_error_retries_translate
            parse_error_retries = self.parse_error_retries_translate
            timeout_error_retries = self.timeout_error_retries_translate

        retry_count = 0
        last_error = "No error recorded"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }

        while retry_count <= max_retries:
            should_retry = False
            current_max_specific_retries = max_retries # 默认特定错误重试上限为通用上限

            try:
                if retry_count > 0:
                    self.logger.info(f"API调用重试 ({retry_count}/{max_retries}) for {request_type}...")
                
                self.logger.debug(f"API请求数据 ({request_type}): {json.dumps(data, ensure_ascii=False)[:500]}...")
                request_start_time = time.time()

                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=self.api_timeout
                )
                request_duration = time.time() - request_start_time
                self.logger.info(f"API响应时间 ({request_type}): {request_duration:.2f}秒, Status: {response.status_code}")

                response.raise_for_status()  # HTTP错误会在这里抛出
                result = response.json()
                self.logger.debug(f"API响应原始数据 ({request_type}): {json.dumps(result, ensure_ascii=False)[:500]}...")

                response_text = None
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        response_text = choice["message"]["content"]
                    elif "text" in choice: # 兼容旧API
                        response_text = choice["text"]
                elif "content" in result: # 有些模型可能直接在顶层返回 content
                     response_text = result["content"] if isinstance(result["content"], str) else str(result)
                
                if response_text is None : # 如果还没找到，并且没有choices，尝试整个结果转字符串
                    self.logger.warning(
                        f"API响应 ({request_type}) 中没有找到明确的文本字段 ('content'/'text' in choices or top-level 'content')。 "
                        f"将尝试使用整个响应的字符串形式。这可能需要后续处理。响应: {str(result)[:200]}..."
                    )
                    response_text = str(result)

                if not response_text or len(response_text.strip()) < 1: # 检查API返回是否为空
                    raise ValueError(f"API ({request_type}) 返回内容为空或无效: '{response_text}'")

                cleaned_text = self._remove_thinking(response_text)
                self.logger.info(f"API调用成功 ({request_type})，响应长度: {len(cleaned_text)}字符")
                return cleaned_text

            except requests.exceptions.Timeout as e:
                last_error = f"请求超时 ({request_type}): {str(e)}"
                current_max_specific_retries = timeout_error_retries
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误 ({request_type}): {str(e)}"
                current_max_specific_retries = network_error_retries
            except requests.exceptions.RequestException as e: # HTTP错误等
                last_error = f"请求异常 ({request_type}): {str(e)} (Status: {e.response.status_code if e.response else 'N/A'})
 Response: {e.response.text[:200] if e.response else 'N/A'}..."
                if e.response is not None:
                    if e.response.status_code == 401: # 认证失败
                        self.logger.error(f"API认证失败 (401) for {request_type} with key {self.api_key[:8]}... 请检查API密钥。")
                        # 认证错误不应重试，直接抛出
                        raise Exception(f"API认证失败 (401) for {request_type}. Key: {self.api_key[:8]}...") 
                    if e.response.status_code == 429: # 速率限制
                        self.logger.warning(f"API速率限制 (429) for {request_type} with key {self.api_key[:8]}...")
                        # 速率限制错误也应该由ApiKeyRotator处理，这里只记录
                # 对于其他HTTP错误，使用通用重试逻辑
                current_max_specific_retries = max_retries
            except (ValueError, json.JSONDecodeError) as e: # 包括API返回内容为空的ValueError
                last_error = f"响应解析错误或内容无效 ({request_type}): {str(e)}"
                current_max_specific_retries = parse_error_retries
            except Exception as e:
                last_error = f"未知错误 ({request_type}): {str(e)}"
                current_max_specific_retries = max_retries # 未知错误使用通用重试

            retry_count += 1
            if retry_count <= max_retries and retry_count <= current_max_specific_retries:
                should_retry = True
            
            if should_retry:
                sleep_time = min(
                    self.retry_delay * (2 ** (retry_count - 1)) * (1 + random.random() * 0.2),
                    self.max_retry_delay
                )
                masked_key_info = self.api_key[:8] + "..." + self.api_key[-4:]
                self.logger.warning(f"API调用失败 ({retry_count}/{max_retries if max_retries == current_max_specific_retries else str(max_retries) + '(general)/' + str(current_max_specific_retries) + '(specific)'}) [{masked_key_info}, {request_type}]: {last_error}")
                self.logger.info(f"等待 {sleep_time:.1f} 秒后重试 ({request_type})...")
                time.sleep(sleep_time)
            else:
                self.logger.error(f"已达到最大重试次数 ({retry_count-1}) for {request_type}，放弃API调用。最后错误: {last_error}")
                break
        
        # 如果所有重试都失败
        masked_key_info = self.api_key[:8] + "..." + self.api_key[-4:]
        error_message = f"API ({request_type}) 调用失败，已重试 {retry_count-1} 次: {last_error} [API密钥: {masked_key_info}]"
        self.logger.error(error_message)
        raise Exception(error_message)

    def translate(self, prompt: str, temperature: float = 0.1) -> str:
        """
        翻译文本。

        参数:
            prompt: 包含待翻译韩文和术语库的完整提示。
            temperature: 生成文本的温度参数。

        返回:
            翻译后的中文文本。
        
        抛出:
            Exception: 如果API调用失败。
        """
        self.logger.info(f"开始翻译文本 (temp={temperature})...")
        try:
            response = self._make_api_call(prompt, temperature=temperature, request_type="translate")
            return response
        except Exception as e:
            self.logger.error(f"翻译文本时出错: {str(e)}")
            raise # 重新抛出异常，让调用者处理

    def extract_terms(self, prompt: str, temperature: float = 0.01) -> str:
        """
        从API提取术语信息 (例如，根据原文和译文建议新的术语)。

        参数:
            prompt: 包含韩文原文、中文译文和现有术语库的提示。
            temperature: 生成文本的温度参数。

        返回:
            API返回的原始响应文本，预计包含术语信息。
        
        抛出:
            Exception: 如果API调用失败或返回内容无效。
        """
        self.logger.info(f"开始从API提取术语 (temp={temperature})...")
        try:
            response = self._make_api_call(prompt, temperature=temperature, request_type="terms")
            
            # 进一步验证响应，因为术语提取可能对格式有要求
            if not response or len(response.strip()) < 5: # 简单检查，具体检查应在TerminologyManager中
                self.logger.warning(f"API返回的术语提取响应内容为空或过短: '{response}'")
                # 之前ApiClient是返回字符串错误，这里改为抛出异常，由调用方决定如何处理
                raise ValueError(f"API返回的术语提取响应内容为空或过短: '{response}'")
            
            self.logger.info(f"术语提取API调用成功，响应长度: {len(response)} 字符")
            return response
        except Exception as e:
            # 如果是特定于 extract_terms 的 ValueError，可能不需要记录为通用错误
            if not isinstance(e, ValueError) or "API返回的术语提取响应内容为空或过短" not in str(e):
                 self.logger.error(f"提取术语时出错: {str(e)}")
            raise # 重新抛出异常

# TranslatorPrompts 类将在这里定义
class TranslatorPrompts:
    """
    负责加载和构建用于翻译和术语更新的提示。
    模板从外部文件加载，路径通过构造函数传入。
    """
    def __init__(self, translate_prompt_file_path: str, term_update_prompt_file_path: str):
        self.logger = logging.getLogger(__name__ + ".TranslatorPrompts")
        
        if not translate_prompt_file_path:
            raise ValueError("翻译提示模板文件路径 (translate_prompt_file_path) 不能为空")
        if not term_update_prompt_file_path:
            raise ValueError("术语更新提示模板文件路径 (term_update_prompt_file_path) 不能为空")

        self.translate_prompt_template = self._load_prompt_template(translate_prompt_file_path, "翻译")
        self.term_update_prompt_template = self._load_prompt_template(term_update_prompt_file_path, "术语更新")
        
        self.logger.info("TranslatorPrompts 初始化完成。")

    def _load_prompt_template(self, prompt_file_path: str, template_name: str) -> str:
        """
        加载指定的提示模板文件。

        参数:
            prompt_file_path: 提示模板文件的完整路径。
            template_name: 模板的名称 (用于日志记录)。

        返回:
            提示模板内容字符串。
        
        抛出:
            FileNotFoundError: 如果模板文件不存在。
            Exception: 如果加载过程中发生其他错误。
        """
        try:
            if not os.path.exists(prompt_file_path):
                error_msg = f"{template_name}提示模板文件不存在: {prompt_file_path}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.logger.info(f"成功加载{template_name}提示模板: {os.path.basename(prompt_file_path)}, 长度: {len(content)}字符")
            return content
        except Exception as e:
            self.logger.error(f"加载{template_name}提示模板 {prompt_file_path} 时出错: {str(e)}")
            raise # 重新抛出，让调用者处理或记录

    def build_translation_prompt(self, korean_text: str, formatted_terminology: str) -> str:
        """
        构建翻译提示。

        参数:
            korean_text: 需要翻译的韩文文本。
            formatted_terminology: 格式化后的术语库字符串。

        返回:
            完整的翻译提示字符串。
        """
        final_prompt = self.translate_prompt_template
        # 替换占位符，确保占位符的准确性，例如 {korean_text} 和 {terminology}
        final_prompt = final_prompt.replace("{korean_text}", korean_text)
        final_prompt = final_prompt.replace("{terminology}", formatted_terminology or "无特定术语。") # 如果术语为空，提供默认值
        
        self.logger.debug(f"构建完成翻译提示，总长度: {len(final_prompt)}字符")
        return final_prompt

    def build_terminology_update_prompt(self, korean_text: str, chinese_text: str, formatted_terminology: str) -> str:
        """
        构建术语更新提示。

        参数:
            korean_text: 原韩文文本
            chinese_text: 翻译后的中文文本
            formatted_terminology: 格式化后的术语库字符串

        返回:
            完整的术语更新提示字符串
        """
        final_prompt = self.term_update_prompt_template
        # 替换占位符，例如 {korean_text}, {chinese_text}, {terminology}
        final_prompt = final_prompt.replace("{korean_text}", korean_text)
        final_prompt = final_prompt.replace("{chinese_text}", chinese_text)
        final_prompt = final_prompt.replace("{terminology}", formatted_terminology or "无特定术语。") # 如果术语为空，提供默认值

        self.logger.debug(f"构建完成术语更新提示，总长度: {len(final_prompt)}字符")
        return final_prompt

# 可以考虑添加一个顶层 Translator 类来组合 TranslatorAPI 和 TranslatorPrompts
# class Translator:
#     def __init__(self, api_config: Dict, prompt_config: Dict):
#         self.api_client = TranslatorAPI(**api_config)
#         self.prompt_builder = TranslatorPrompts(**prompt_config)
# 
#     def translate_novel_text(self, korean_text: str, formatted_terminology: str, temperature_translate: float = 0.1) -> str:
#         prompt = self.prompt_builder.build_translation_prompt(korean_text, formatted_terminology)
#         return self.api_client.translate(prompt, temperature=temperature_translate)
# 
#     def suggest_new_terms(self, korean_text: str, chinese_text: str, formatted_terminology: str, temperature_terms: float = 0.01) -> str:
#         prompt = self.prompt_builder.build_terminology_update_prompt(korean_text, chinese_text, formatted_terminology)
#         return self.api_client.extract_terms(prompt, temperature=temperature_terms)

# TranslatorPrompts 类将在这里定义
# ... 