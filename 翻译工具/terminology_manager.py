import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from config import (
    get_novel_character_file, 
    get_novel_proper_nouns_file, 
    get_novel_cultural_expressions_file,
    get_novel_terminology_dir,
    GLOBAL_CHARACTER_FILE,
    GLOBAL_PROPER_NOUNS_FILE,
    GLOBAL_CULTURAL_EXPRESSIONS_FILE
)

import config

class TerminologyManager:
    """负责加载、格式化和更新术语库"""

    def __init__(self, novel_name):
        """
        初始化术语管理器
        
        Args:
            novel_name: 小说名称，用于定位和管理特定小说的术语库
        """
        self.novel_name = novel_name
        self.characters = []
        self.proper_nouns = []
        self.cultural_expressions = []
        self.logger = logging.getLogger(__name__)
        
        # 确保小说术语库目录存在
        self._ensure_novel_terminology_dir()
        
        # 加载术语库
        self.load_terminology()
        
    def _ensure_novel_terminology_dir(self):
        """确保小说的术语库目录存在，如果不存在则创建"""
        novel_term_dir = get_novel_terminology_dir(self.novel_name)
        if not os.path.exists(novel_term_dir):
            os.makedirs(novel_term_dir, exist_ok=True)
            self.logger.info(f"为小说「{self.novel_name}」创建术语库目录: {novel_term_dir}")
    
    def load_terminology(self):
        """
        加载术语库
        先尝试加载特定小说的术语库，如果文件不存在，则从全局术语库复制
        """
        # 获取当前小说的术语库文件路径
        character_file = get_novel_character_file(self.novel_name)
        proper_nouns_file = get_novel_proper_nouns_file(self.novel_name)
        cultural_expressions_file = get_novel_cultural_expressions_file(self.novel_name)
        
        # 加载人物术语
        if os.path.exists(character_file):
            self.characters = self._load_file(character_file)
            self.logger.info(f"已加载小说「{self.novel_name}」的人物术语: {len(self.characters)} 条记录")
        elif os.path.exists(GLOBAL_CHARACTER_FILE):
            # 如果小说特定的文件不存在但全局文件存在，从全局复制
            self.characters = self._load_file(GLOBAL_CHARACTER_FILE)
            self._save_file(character_file, self.characters)
            self.logger.info(f"已从全局术语库复制人物术语到小说「{self.novel_name}」: {len(self.characters)} 条记录")
        else:
            self.logger.warning(f"人物术语库文件不存在，创建空术语库: {character_file}")
            self._save_file(character_file, [])
        
        # 加载专有名词术语
        if os.path.exists(proper_nouns_file):
            self.proper_nouns = self._load_file(proper_nouns_file)
            self.logger.info(f"已加载小说「{self.novel_name}」的专有名词术语: {len(self.proper_nouns)} 条记录")
        elif os.path.exists(GLOBAL_PROPER_NOUNS_FILE):
            # 如果小说特定的文件不存在但全局文件存在，从全局复制
            self.proper_nouns = self._load_file(GLOBAL_PROPER_NOUNS_FILE)
            self._save_file(proper_nouns_file, self.proper_nouns)
            self.logger.info(f"已从全局术语库复制专有名词术语到小说「{self.novel_name}」: {len(self.proper_nouns)} 条记录")
        else:
            self.logger.warning(f"专有名词术语库文件不存在，创建空术语库: {proper_nouns_file}")
            self._save_file(proper_nouns_file, [])
            
        # 加载文化表达术语
        if os.path.exists(cultural_expressions_file):
            self.cultural_expressions = self._load_file(cultural_expressions_file)
            self.logger.info(f"已加载小说「{self.novel_name}」的文化表达术语: {len(self.cultural_expressions)} 条记录")
        elif os.path.exists(GLOBAL_CULTURAL_EXPRESSIONS_FILE):
            # 如果小说特定的文件不存在但全局文件存在，从全局复制
            self.cultural_expressions = self._load_file(GLOBAL_CULTURAL_EXPRESSIONS_FILE)
            self._save_file(cultural_expressions_file, self.cultural_expressions)
            self.logger.info(f"已从全局术语库复制文化表达术语到小说「{self.novel_name}」: {len(self.cultural_expressions)} 条记录")
        else:
            self.logger.warning(f"文化表达术语库文件不存在，创建空术语库: {cultural_expressions_file}")
            self._save_file(cultural_expressions_file, [])
        
        # 标准化所有术语格式
        self._standardize_all()
    
    def _load_file(self, filepath):
        """从文件加载数据，处理可能的错误"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as file:
                    return json.load(file)
            return []
        except json.JSONDecodeError:
            self.logger.error(f"解析 JSON 文件失败: {filepath}, 将返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"加载文件失败: {filepath}, 错误: {str(e)}")
            return []
    
    def _save_file(self, filepath, data):
        """保存数据到文件，处理可能的错误"""
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"保存文件失败: {filepath}, 错误: {str(e)}")
            return False
    
    def _standardize_all(self):
        """标准化所有术语格式"""
        self.characters = [self._standardize_character(c) for c in self.characters]
        self.proper_nouns = [self._standardize_noun(n) for n in self.proper_nouns]
        self.cultural_expressions = [self._standardize_expression(e) for e in self.cultural_expressions]
    
    def _standardize_character(self, character):
        """
        标准化人物术语格式，确保包含所有必要字段
        """
        if isinstance(character, dict):
            return {
                "name": character.get("name", ""),
                "alias": character.get("alias", []),
                "description": character.get("description", "")
            }
        elif isinstance(character, str):
            return {
                "name": character,
                "alias": [],
                "description": ""
            }
        return character
    
    def _standardize_noun(self, noun):
        """
        标准化专有名词术语格式，确保包含所有必要字段
        """
        if isinstance(noun, dict):
            return {
                "original": noun.get("original", ""),
                "translated": noun.get("translated", ""),
                "description": noun.get("description", "")
            }
        elif isinstance(noun, str):
            return {
                "original": noun,
                "translated": "",
                "description": ""
            }
        return noun
    
    def _standardize_expression(self, expression):
        """
        标准化文化表达术语格式，确保包含所有必要字段
        """
        if isinstance(expression, dict):
            return {
                "original": expression.get("original", ""),
                "translated": expression.get("translated", ""),
                "explanation": expression.get("explanation", "")
            }
        elif isinstance(expression, str):
            return {
                "original": expression,
                "translated": "",
                "explanation": ""
            }
        return expression
    
    def get_formatted_terminology(self):
        """
        获取格式化的术语库，用于翻译提示
        """
        formatted = "## 术语库\n\n"
        
        # 添加人物列表
        if self.characters:
            formatted += "### 人物\n"
            for char in self.characters:
                name = char.get("name", "")
                alias = char.get("alias", [])
                desc = char.get("description", "")
                
                formatted += f"- {name}"
                if alias:
                    formatted += f" (别名: {', '.join(alias)})"
                if desc:
                    formatted += f": {desc}"
                formatted += "\n"
            formatted += "\n"
        
        # 添加专有名词
        if self.proper_nouns:
            formatted += "### 专有名词\n"
            for noun in self.proper_nouns:
                original = noun.get("original", "")
                translated = noun.get("translated", "")
                desc = noun.get("description", "")
                
                if translated:
                    formatted += f"- {original} → {translated}"
                else:
                    formatted += f"- {original}"
                
                if desc:
                    formatted += f": {desc}"
                formatted += "\n"
            formatted += "\n"
        
        # 添加文化表达
        if self.cultural_expressions:
            formatted += "### 文化表达\n"
            for expr in self.cultural_expressions:
                original = expr.get("original", "")
                translated = expr.get("translated", "")
                explanation = expr.get("explanation", "")
                
                if translated:
                    formatted += f"- {original} → {translated}"
                else:
                    formatted += f"- {original}"
                
                if explanation:
                    formatted += f": {explanation}"
                formatted += "\n"
            formatted += "\n"
        
        return formatted
    
    def update_terminology_from_api_response(self, response_text):
        """
        从API响应更新术语库
        
        Args:
            response_text: API响应的文本，包含更新建议
        
        Returns:
            tuple: 更新的(人物数量, 专有名词数量, 文化表达数量)
        """
        # 解析响应文本，查找术语更新建议
        # 假设响应文本包含特定格式的术语更新建议
        chars_added = 0
        nouns_added = 0
        exprs_added = 0
        
        try:
            updated = False
            
            # 简单的解析逻辑，可以根据实际响应格式进行调整
            if "### 更新人物" in response_text or "### 人物更新" in response_text:
                chars_added = self._parse_character_updates(response_text) 
                updated = chars_added > 0 or updated
            
            if "### 更新专有名词" in response_text or "### 专有名词更新" in response_text:
                nouns_added = self._parse_proper_noun_updates(response_text)
                updated = nouns_added > 0 or updated
            
            if "### 更新文化表达" in response_text or "### 文化表达更新" in response_text:
                exprs_added = self._parse_cultural_expression_updates(response_text)
                updated = exprs_added > 0 or updated
            
            # 如果有更新，保存术语库
            if updated:
                self._save_all_terminology()
                self.logger.info(f"成功更新小说「{self.novel_name}」的术语库")
            else:
                self.logger.info("API响应中未找到有效的术语更新建议")
            
            return (chars_added, nouns_added, exprs_added)
            
        except Exception as e:
            self.logger.error(f"解析API响应以更新术语库时出错: {str(e)}")
            return (0, 0, 0)
    
    def _parse_character_updates(self, response_text):
        """
        解析人物更新建议
        返回: 更新的人物数量
        """
        try:
            # 查找人物更新章节
            section_start = None
            for pattern in ["### 更新人物", "### 人物更新"]:
                if pattern in response_text:
                    section_start = response_text.find(pattern)
                    break
                    
            if section_start is None:
                return 0
                
            # 获取人物更新部分的文本
            section_text = response_text[section_start:]
            
            # 查找下一个章节开始，如果有的话
            next_section = None
            for pattern in ["### 更新专有名词", "### 专有名词更新", "### 更新文化表达", "### 文化表达更新"]:
                next_pos = section_text.find(pattern)
                if next_pos > 0:
                    next_section = next_pos
                    break
            
            # 提取人物更新部分
            if next_section:
                section_text = section_text[:next_section]
            
            # 用正则表达式提取人物信息
            import re
            
            # 首先匹配带别名的格式
            alias_pattern = r'- ([^:()]+)\s+\(别名:\s*([^)]+)\)(?::\s*(.+))?'
            alias_matches = re.findall(alias_pattern, section_text)
            
            chars_added = 0
            processed_names = []
            
            # 处理带别名的人物
            for match in alias_matches:
                name = match[0].strip()
                processed_names.append(name)  # 记录已处理的名称
                
                alias_str = match[1].strip()
                alias_list = [a.strip() for a in alias_str.split(',')]
                desc = match[2].strip() if len(match) > 2 and match[2] else ""
                
                # 查找是否已存在此人物
                existing_char = None
                for char in self.characters:
                    if char.get("name") == name:
                        existing_char = char
                        break
                
                if existing_char:
                    # 如果已存在，更新信息
                    # 更新别名，避免重复
                    for alias in alias_list:
                        if alias and alias not in existing_char["alias"]:
                            existing_char["alias"].append(alias)
                    
                    # 更新描述（如果有新描述且旧描述为空）
                    if desc and not existing_char.get("description"):
                        existing_char["description"] = desc
                    
                    # 更新信息已完成
                else:
                    # 添加新人物
                    new_char = {
                        "name": name,
                        "alias": alias_list,
                        "description": desc
                    }
                    self.characters.append(new_char)
                    chars_added += 1
            
            # 然后匹配不带别名的格式
            simple_pattern = r'- ([^:()\r\n]+)(?::\s*([^\r\n]+))?'
            simple_matches = re.findall(simple_pattern, section_text)
            
            for match in simple_matches:
                name = match[0].strip()
                
                # 跳过已处理的名称
                if name in processed_names:
                    continue
                
                desc = match[1].strip() if len(match) > 1 and match[1] else ""
                
                # 查找是否已存在此人物
                existing_char = None
                for char in self.characters:
                    if char.get("name") == name:
                        existing_char = char
                        break
                
                if existing_char:
                    # 如果已存在，更新信息
                    # 更新描述（如果有新描述且旧描述为空）
                    if desc and not existing_char.get("description"):
                        existing_char["description"] = desc
                    
                    # 更新信息已完成
                else:
                    # 添加新人物
                    new_char = {
                        "name": name,
                        "alias": [],
                        "description": desc
                    }
                    self.characters.append(new_char)
                    chars_added += 1
            
            self.logger.info(f"解析到 {chars_added} 个新人物")
            return chars_added
        except Exception as e:
            self.logger.error(f"解析人物更新建议时出错: {str(e)}")
            return 0
    
    def _parse_proper_noun_updates(self, response_text):
        """
        解析专有名词更新建议
        返回: 更新的专有名词数量
        """
        try:
            # 查找专有名词更新章节
            section_start = None
            for pattern in ["### 更新专有名词", "### 专有名词更新"]:
                if pattern in response_text:
                    section_start = response_text.find(pattern)
                    break
                    
            if section_start is None:
                return 0
                
            # 获取专有名词更新部分的文本
            section_text = response_text[section_start:]
            
            # 查找下一个章节开始，如果有的话
            next_section = None
            for pattern in ["### 更新人物", "### 人物更新", "### 更新文化表达", "### 文化表达更新"]:
                next_pos = section_text.find(pattern)
                if next_pos > 0:
                    next_section = next_pos
                    break
            
            # 提取专有名词更新部分
            if next_section:
                section_text = section_text[:next_section]
            
            # 用正则表达式提取专有名词信息
            # 匹配格式如 "- 原词 → 译词: 描述" 或 "- 原词: 描述"
            import re
            
            # 首先尝试匹配带有→符号的格式
            arrow_pattern = r'- ([^→:]+)\s*→\s*([^:]+)(?::\s*(.+))?'
            matches = re.findall(arrow_pattern, section_text)
            
            nouns_added = 0
            for match in matches:
                original = match[0].strip()
                translated = match[1].strip()
                description = match[2].strip() if len(match) > 2 and match[2] else ""
                
                # 查找是否已存在此专有名词
                existing_noun = None
                for noun in self.proper_nouns:
                    if noun.get("original") == original:
                        existing_noun = noun
                        break
                
                if existing_noun:
                    # 如果存在则更新
                    if translated and not existing_noun.get("translated"):
                        existing_noun["translated"] = translated
                    if description and not existing_noun.get("description"):
                        existing_noun["description"] = description
                    # 更新信息已完成
                else:
                    # 添加新专有名词
                    new_noun = {
                        "original": original,
                        "translated": translated,
                        "description": description
                    }
                    self.proper_nouns.append(new_noun)
                    nouns_added += 1
            
            # 然后尝试匹配没有→符号的格式，只处理之前没有匹配过的条目
            # 记录已处理的原词，避免重复
            processed_originals = [noun.get("original") for noun in self.proper_nouns]
            simple_pattern = r'- ([^:→]+)(?::\s*(.+))?'
            simple_matches = re.findall(simple_pattern, section_text)
            
            for match in simple_matches:
                original = match[0].strip()
                description = match[1].strip() if len(match) > 1 and match[1] else ""
                
                # 检查是否已处理过此原词
                if original in processed_originals:
                    continue
                
                # 查找是否已存在此专有名词
                existing_noun = None
                for noun in self.proper_nouns:
                    if noun.get("original") == original:
                        existing_noun = noun
                        break
                
                if existing_noun:
                    # 如果存在则更新
                    if description and not existing_noun.get("description"):
                        existing_noun["description"] = description
                    # 更新信息已完成
                else:
                    # 添加新专有名词
                    new_noun = {
                        "original": original,
                        "translated": "",
                        "description": description
                    }
                    self.proper_nouns.append(new_noun)
                    nouns_added += 1
            
            self.logger.info(f"解析到 {nouns_added} 个新专有名词")
            return nouns_added
        except Exception as e:
            self.logger.error(f"解析专有名词更新建议时出错: {str(e)}")
            return 0
    
    def _parse_cultural_expression_updates(self, response_text):
        """
        解析文化表达更新建议
        返回: 更新的文化表达数量
        """
        try:
            # 查找文化表达更新章节
            section_start = None
            for pattern in ["### 更新文化表达", "### 文化表达更新"]:
                if pattern in response_text:
                    section_start = response_text.find(pattern)
                    break
                    
            if section_start is None:
                return 0
                
            # 获取文化表达更新部分的文本
            section_text = response_text[section_start:]
            
            # 查找下一个章节开始，如果有的话
            next_section = None
            for pattern in ["### 更新人物", "### 人物更新", "### 更新专有名词", "### 专有名词更新"]:
                next_pos = section_text.find(pattern)
                if next_pos > 0:
                    next_section = next_pos
                    break
            
            # 提取文化表达更新部分
            if next_section:
                section_text = section_text[:next_section]
            
            # 用正则表达式提取文化表达信息
            import re
            
            # 首先尝试匹配带有→符号的格式
            arrow_pattern = r'- ([^→:]+)\s*→\s*([^:]+)(?::\s*(.+))?'
            matches = re.findall(arrow_pattern, section_text)
            
            exprs_added = 0
            for match in matches:
                original = match[0].strip()
                translated = match[1].strip()
                explanation = match[2].strip() if len(match) > 2 and match[2] else ""
                
                # 查找是否已存在此文化表达
                existing_expr = None
                for expr in self.cultural_expressions:
                    if expr.get("original") == original:
                        existing_expr = expr
                        break
                
                if existing_expr:
                    # 如果存在则更新
                    if translated and not existing_expr.get("translated"):
                        existing_expr["translated"] = translated
                    if explanation and not existing_expr.get("explanation"):
                        existing_expr["explanation"] = explanation
                    # 更新信息已完成
                else:
                    # 添加新文化表达
                    new_expr = {
                        "original": original,
                        "translated": translated,
                        "explanation": explanation
                    }
                    self.cultural_expressions.append(new_expr)
                    exprs_added += 1
            
            # 然后尝试匹配没有→符号的格式，只处理之前没有匹配过的条目
            # 记录已处理的原词，避免重复
            processed_originals = [expr.get("original") for expr in self.cultural_expressions]
            simple_pattern = r'- ([^:→]+)(?::\s*(.+))?'
            simple_matches = re.findall(simple_pattern, section_text)
            
            for match in simple_matches:
                original = match[0].strip()
                explanation = match[1].strip() if len(match) > 1 and match[1] else ""
                
                # 检查是否已处理过此原词
                if original in processed_originals:
                    continue
                
                # 查找是否已存在此文化表达
                existing_expr = None
                for expr in self.cultural_expressions:
                    if expr.get("original") == original:
                        existing_expr = expr
                        break
                
                if existing_expr:
                    # 如果存在则更新
                    if explanation and not existing_expr.get("explanation"):
                        existing_expr["explanation"] = explanation
                    # 更新信息已完成
                else:
                    # 添加新文化表达
                    new_expr = {
                        "original": original,
                        "translated": "",
                        "explanation": explanation
                    }
                    self.cultural_expressions.append(new_expr)
                    exprs_added += 1
            
            self.logger.info(f"解析到 {exprs_added} 个新文化表达")
            return exprs_added
        except Exception as e:
            self.logger.error(f"解析文化表达更新建议时出错: {str(e)}")
            return 0
    
    def _save_all_terminology(self):
        """保存所有术语库到对应文件"""
        character_file = get_novel_character_file(self.novel_name)
        proper_nouns_file = get_novel_proper_nouns_file(self.novel_name)
        cultural_expressions_file = get_novel_cultural_expressions_file(self.novel_name)
        
        self._save_file(character_file, self.characters)
        self._save_file(proper_nouns_file, self.proper_nouns)
        self._save_file(cultural_expressions_file, self.cultural_expressions)
        
        self.logger.info(f"已保存小说「{self.novel_name}」的所有术语库文件")
    
    def _save_terminology(self) -> bool:
        """
        将更新后的术语库保存到文件
        返回：保存是否成功（布尔值）
        """
        try:
            # 确保术语库目录存在
            os.makedirs(config.TERMINOLOGY_DIR, exist_ok=True)
            
            # 保存人物名称
            with open(config.CHARACTER_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.characters, f, ensure_ascii=False, indent=2)
                
            # 保存专有名词
            with open(config.PROPER_NOUNS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.proper_nouns, f, ensure_ascii=False, indent=2)
                
            # 保存文化表达
            with open(config.CULTURAL_EXPRESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cultural_expressions, f, ensure_ascii=False, indent=2)
                
            logging.info("术语库已成功保存")
            return True
            
        except Exception as e:
            logging.error(f"保存术语库时发生错误: {str(e)}")
            return False