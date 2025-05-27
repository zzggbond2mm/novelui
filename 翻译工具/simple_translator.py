import json
import logging
import time
import requests
import re
import random
from typing import Dict, Any, Optional
import argparse
import os
import sys

# 默认配置 (可以根据需要修改或通过参数传入)
DEFAULT_API_URL = "YOUR_API_URL_HERE" # 例如 "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL_NAME = "YOUR_MODEL_NAME_HERE" # 例如 "gpt-3.5-turbo"
DEFAULT_API_TIMEOUT = 60  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5  # seconds
DEFAULT_MAX_RETRY_DELAY = 60 # seconds
DEFAULT_TEMPERATURE = 0.1

DEFAULT_TRANSLATE_PROMPT_TEMPLATE = """
请将以下韩文文本翻译成流畅、自然的简体中文。

{custom_instructions}

[待翻译文本开始]
{korean_text}
[待翻译文本结束]

[术语库开始]
{terminology}
[术语库结束]

请直接输出翻译后的中文文本，不要包含任何额外解释或标签。
"""

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SimplifiedApiClient:
    """简化的API客户端，用于文本翻译"""

    def __init__(self, api_key: str, api_url: str = DEFAULT_API_URL, model_name: str = DEFAULT_MODEL_NAME):
        if not api_key:
            raise ValueError("API密钥不能为空")
        if not api_url:
            raise ValueError("API URL不能为空")
        if not model_name:
            raise ValueError("模型名称不能为空")
            
        self.api_key = api_key
        self.api_url = api_url
        self.model = model_name
        
        masked_key = self.api_key[:8] + "..." + self.api_key[-4:]
        logging.info(f"初始化简易API客户端, API URL: {self.api_url}, 模型: {self.model}, API密钥: {masked_key}")

    def _remove_thinking(self, text: str) -> str:
        """移除AI思考过程，也就是<think>...</think>标签之间的内容"""
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if cleaned_text != text:
            logging.debug(f"已移除思考内容，原长度: {len(text)}，新长度: {len(cleaned_text)}")
        return cleaned_text

    def translate_text(self, prompt: str, temperature: float = DEFAULT_TEMPERATURE, max_retries: int = DEFAULT_MAX_RETRIES) -> Optional[str]:
        """
        使用提供的提示进行文本翻译。

        参数:
            prompt: 发送给API的完整提示。
            temperature: 控制生成文本的随机性。
            max_retries: 最大重试次数。

        返回:
            翻译后的文本，如果失败则返回None。
        """
        retry_count = 0
        last_error = None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    logging.info(f"API调用重试 ({retry_count}/{max_retries})...")
                
                logging.debug(f"API请求数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                request_start_time = time.time()
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=DEFAULT_API_TIMEOUT
                )
                request_duration = time.time() - request_start_time
                logging.info(f"API响应时间: {request_duration:.2f}秒")
                
                response.raise_for_status()  # 抛出HTTP错误
                result = response.json()
                logging.debug(f"API响应原始数据: {json.dumps(result, ensure_ascii=False)[:500]}...")
                
                response_text = None
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        response_text = choice["message"]["content"]
                    elif "text" in choice: # 兼容一些旧的API格式
                        response_text = choice["text"]
                
                if not response_text: # 如果上述路径没有取到，尝试直接从 result 的 "content" (某些模型可能直接返回)
                    if "content" in result and isinstance(result["content"], str) :
                         response_text = result["content"]
                
                if not response_text and not ( "choices" in result and len(result["choices"]) > 0 ): # 如果还没有，并且没有choices
                     # 对于没有明确 "content" 或 "text" 字段的，并且没有 choices 的，将整个结果转为字符串
                     # 这是一种兼容性措施，但可能需要后续处理
                    logging.warning("API响应中没有找到明确的文本字段 ('content'或'text'在choices中)，将尝试使用整个响应的字符串形式。")
                    response_text = str(result)


                if not response_text or len(response_text.strip()) < 1: # 检查响应是否为空
                    raise ValueError(f"API返回内容为空或无效: '{response_text}'")
                
                cleaned_text = self._remove_thinking(response_text)
                
                logging.info(f"API调用成功，响应长度: {len(cleaned_text)}字符")
                return cleaned_text
                
            except requests.exceptions.Timeout as e:
                last_error = f"请求超时: {str(e)}"
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误: {str(e)}"
            except requests.exceptions.RequestException as e: # 包括HTTP错误
                last_error = f"请求异常: {str(e)}"
                if response and response.status_code == 401:
                     logging.error(f"API认证失败 (401 Unauthorized)。请检查您的API密钥。")
                     return None # 认证错误不应重试
                if response and response.status_code == 429:
                     logging.warning(f"API速率限制。请稍后重试。")
                     # 可以考虑实现更复杂的退避策略
            except (ValueError, json.JSONDecodeError) as e: # 包括API返回内容为空的ValueError
                last_error = f"响应解析错误或内容无效: {str(e)}"
            except Exception as e:
                last_error = f"未知错误: {str(e)}"

            retry_count += 1
            if retry_count <= max_retries:
                sleep_time = min(
                    DEFAULT_RETRY_DELAY * (2 ** (retry_count - 1)) * (1 + random.random() * 0.2),
                    DEFAULT_MAX_RETRY_DELAY
                )
                logging.warning(f"API调用失败 ({retry_count-1}/{max_retries}): {last_error}")
                logging.info(f"等待 {sleep_time:.1f} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logging.error(f"已达到最大重试次数 ({max_retries})，放弃API调用。最后错误: {last_error}")
                break
        
        return None

class SimplifiedPromptBuilder:
    """简化的提示构建器"""
    def __init__(self, template_str: str = DEFAULT_TRANSLATE_PROMPT_TEMPLATE):
        self.template = template_str
        logging.info("初始化简易提示构建器")

    def build_translation_prompt(self, korean_text: str, terminology: Optional[str] = None, custom_instructions: Optional[str] = None) -> str:
        """
        构建翻译提示。

        参数:
            korean_text: 需要翻译的韩文文本。
            terminology: (可选) 格式化的术语库字符串。
            custom_instructions: (可选) 用户自定义的翻译指令。

        返回:
            完整的翻译提示字符串。
        """
        final_prompt = self.template
        final_prompt = final_prompt.replace("{korean_text}", korean_text)
        final_prompt = final_prompt.replace("{terminology}", terminology or "无特定术语。")
        final_prompt = final_prompt.replace("{custom_instructions}", custom_instructions or "请注意翻译的准确性和流畅性。")
        
        logging.debug(f"构建完成翻译提示，总长度: {len(final_prompt)} 字符")
        return final_prompt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="简易文本翻译工具")
    parser.add_argument("text_to_translate", type=str, help="需要翻译的韩文文本内容。")
    parser.add_argument("--api_key", type=str, default=os.environ.get("MY_TRANSLATION_API_KEY"), help="API密钥。默认为环境变量 MY_TRANSLATION_API_KEY 的值。")
    parser.add_argument("--api_url", type=str, default=DEFAULT_API_URL, help=f"API URL。默认为：{DEFAULT_API_URL}")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL_NAME, help=f"模型名称。默认为：{DEFAULT_MODEL_NAME}")
    parser.add_argument("--terminology", type=str, default=None, help="(可选) 包含术语的字符串。例如：'### 人物\n- 한국어 → 韩语\n### 专有名词\n- 서울 → 首尔'")
    parser.add_argument("--instructions", type=str, default=None, help="(可选) 自定义翻译指令，例如：'保持原文的幽默风格。'")
    parser.add_argument("--temp", type=float, default=DEFAULT_TEMPERATURE, help=f"温度参数。默认为：{DEFAULT_TEMPERATURE}")
    
    args = parser.parse_args()

    if not args.api_key:
        print("错误：API密钥未提供。请通过 --api_key 参数或设置 MY_TRANSLATION_API_KEY 环境变量提供。")
        sys.exit(1)
    
    if args.api_url == "YOUR_API_URL_HERE" or args.model == "YOUR_MODEL_NAME_HERE":
        print("警告：API URL 或模型名称未配置。请在脚本中修改 DEFAULT_API_URL 和 DEFAULT_MODEL_NAME，或通过命令行参数提供。")
        # 仍然尝试运行，但很可能会失败

    try:
        translator_client = SimplifiedApiClient(api_key=args.api_key, api_url=args.api_url, model_name=args.model)
        prompt_builder = SimplifiedPromptBuilder()

        full_prompt = prompt_builder.build_translation_prompt(
            korean_text=args.text_to_translate,
            terminology=args.terminology,
            custom_instructions=args.instructions
        )

        print("--- 构建的提示 ---")
        print(full_prompt)
        print("---------------------")
        print("正在翻译，请稍候...")

        translated_text = translator_client.translate_text(prompt=full_prompt, temperature=args.temp)

        if translated_text:
            print("\n--- 翻译结果 ---")
            print(translated_text)
            print("-------------------")
        else:
            print("\n翻译失败。请检查日志获取更多信息。")

    except ValueError as ve:
        print(f"输入参数错误: {ve}")
    except Exception as e:
        print(f"翻译过程中发生未预期错误: {e}")
        logging.exception("详细错误信息:")

# 后续会在这里添加 SimplifiedPromptBuilder 和主函数 