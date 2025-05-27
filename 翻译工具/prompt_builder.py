import os
import json
import logging
from typing import Dict, Any, List

import config
from terminology_manager import TerminologyManager

class PromptBuilder:
    """负责构建发送给API的提示，包括加载提示模板、注入术语等"""
    
    def __init__(self):
        """初始化提示构建器"""
        self.translate_prompt_template = self._load_prompt_template(config.TRANSLATE_PROMPT_FILE)
        self.update_prompt_template = self._load_prompt_template(config.UPDATE_PROMPT_FILE)
        
        logging.info("提示构建器初始化完成")
        
    def _load_prompt_template(self, prompt_file: str) -> str:
        """
        加载提示模板文件
        
        参数:
            prompt_file: 提示模板文件路径
            
        返回:
            提示模板内容字符串
        """
        try:
            if not os.path.exists(prompt_file):
                error_msg = f"提示模板文件不存在: {prompt_file}"
                logging.error(error_msg)
                raise FileNotFoundError(error_msg)
                
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            logging.info(f"成功加载提示模板: {os.path.basename(prompt_file)}, 长度: {len(content)} 字符")
            return content
            
        except Exception as e:
            logging.error(f"加载提示模板时出错: {str(e)}")
            raise
    
    def format_terminology(self, terminology: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        格式化术语库为文本形式
        
        参数:
            terminology: 术语库字典
            
        返回:
            术语库的格式化文本表示
        """
        lines = []
        
        # 添加人物术语
        if terminology.get("characters"):
            lines.append("### 人物")
            for char in terminology["characters"]:
                korean = char.get("korean_name", "")
                chinese = char.get("chinese_name", "")
                desc = char.get("description", "")
                if korean and chinese:
                    lines.append(f"- {korean} → {chinese}" + (f" ({desc})" if desc else ""))
            lines.append("")
        
        # 添加专有名词
        if terminology.get("proper_nouns"):
            lines.append("### 专有名词")
            for noun in terminology["proper_nouns"]:
                korean = noun.get("korean_term", "")
                chinese = noun.get("chinese_term", "")
                desc = noun.get("description", "")
                if korean and chinese:
                    lines.append(f"- {korean} → {chinese}" + (f" ({desc})" if desc else ""))
            lines.append("")
        
        # 添加文化表达
        if terminology.get("cultural_expressions"):
            lines.append("### 文化表达")
            for expr in terminology["cultural_expressions"]:
                korean = expr.get("korean_expression", "")
                chinese = expr.get("chinese_expression", "")
                desc = expr.get("description", "")
                if korean and chinese:
                    lines.append(f"- {korean} → {chinese}" + (f" ({desc})" if desc else ""))
            lines.append("")
        
        return "\n".join(lines)
    
    def build_translation_prompt(self, korean_text: str, terminology: str) -> str:
        """
        构建翻译提示
        
        参数:
            korean_text: 需要翻译的韩文文本
            terminology: 格式化后的术语库字符串
            
        返回:
            完整的翻译提示字符串
        """
        # 使用模板中的变量替换
        final_prompt = self.translate_prompt_template
        final_prompt = final_prompt.replace("{terminology}", terminology)
        final_prompt = final_prompt.replace("{korean_text}", korean_text)
        
        logging.debug(f"构建完成翻译提示，总长度: {len(final_prompt)} 字符")
        return final_prompt
        
    def build_terminology_update_prompt(self, korean_text: str, chinese_text: str, terminology: str) -> str:
        """
        构建术语更新提示
        
        参数:
            korean_text: 原韩文文本
            chinese_text: 翻译后的中文文本
            terminology: 格式化后的术语库字符串
            
        返回:
            完整的术语更新提示字符串
        """
        # 使用模板中的变量替换
        final_prompt = self.update_prompt_template
        final_prompt = final_prompt.replace("{terminology}", terminology)
        final_prompt = final_prompt.replace("{korean_text}", korean_text)
        final_prompt = final_prompt.replace("{chinese_text}", chinese_text)
        
        logging.debug(f"构建完成术语更新提示，总长度: {len(final_prompt)} 字符")
        return final_prompt 