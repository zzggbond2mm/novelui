# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# TerminologyManager 类 (负责加载、格式化术语库)
# 根据原始 terminology_manager.py 修改而来
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class TerminologyManager:
    def __init__(self, 
                 character_file: str, 
                 proper_nouns_file: str, 
                 cultural_expressions_file: str):
        self.character_file = character_file
        self.proper_nouns_file = proper_nouns_file
        self.cultural_expressions_file = cultural_expressions_file
        
        self.characters: List[Dict[str, Any]] = []
        self.proper_nouns: List[Dict[str, Any]] = []
        self.cultural_expressions: List[Dict[str, Any]] = []
        
        self.logger = logging.getLogger(__name__ + ".TerminologyManager") # 更具体的logger名称
        self.load_terminology()

    def _load_file(self, filepath: str) -> List[Dict[str, Any]]:
        if not os.path.exists(filepath):
            self.logger.warning(f"术语文件不存在: {filepath}，将使用空列表。")
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if not isinstance(data, list):
                    self.logger.error(f"术语文件 {filepath} 格式错误：期望得到一个列表，实际为 {type(data)}。将使用空列表。")
                    return []
                # 进一步验证列表中的每一项是否为字典（可选，但推荐）
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        self.logger.warning(f"术语文件 {filepath} 中的第 {i+1} 项不是字典格式，将被忽略。")
                        # 可以选择移除该项或返回空列表，这里选择在后续标准化中处理
                return data
        except json.JSONDecodeError:
            self.logger.error(f"解析 JSON 文件失败: {filepath}, 将返回空列表。")
            return []
        except Exception as e:
            self.logger.error(f"加载文件失败: {filepath}, 错误: {str(e)}")
            return []

    def load_terminology(self):
        self.logger.info(f"尝试从以下文件加载术语库:")
        self.logger.info(f"  人物: {self.character_file}")
        self.logger.info(f"  专有名词: {self.proper_nouns_file}")
        self.logger.info(f"  文化表达: {self.cultural_expressions_file}")

        self.characters = self._load_file(self.character_file)
        self.proper_nouns = self._load_file(self.proper_nouns_file)
        self.cultural_expressions = self._load_file(self.cultural_expressions_file)
        
        self.logger.info(f"加载完成: {len(self.characters)}个人物, {len(self.proper_nouns)}个专有名词, {len(self.cultural_expressions)}个文化表达。")
        self._standardize_all()

    def _standardize_character(self, character: Any) -> Dict[str, Any]:
        if not isinstance(character, dict):
            self.logger.warning(f"发现非字典格式的人物术语: {character}，将尝试转换为标准格式或使用默认值。")
            return {"korean_name": str(character), "chinese_name": "", "description": ""} # 修正key名称
        return {
            "korean_name": character.get("korean_name", character.get("name", "")), # 兼容旧的 'name'
            "chinese_name": character.get("chinese_name", ""),
            "description": character.get("description", "")
        }

    def _standardize_noun(self, noun: Any) -> Dict[str, Any]:
        if not isinstance(noun, dict):
            self.logger.warning(f"发现非字典格式的专有名词术语: {noun}，将尝试转换为标准格式或使用默认值。")
            return {"korean_term": str(noun), "chinese_term": "", "description": ""} # 修正key名称
        return {
            "korean_term": noun.get("korean_term", noun.get("original", "")), # 兼容旧的 'original'
            "chinese_term": noun.get("chinese_term", noun.get("translated", "")), # 兼容旧的 'translated'
            "description": noun.get("description", "")
        }

    def _standardize_expression(self, expression: Any) -> Dict[str, Any]:
        if not isinstance(expression, dict):
            self.logger.warning(f"发现非字典格式的文化表达术语: {expression}，将尝试转换为标准格式或使用默认值。")
            return {"korean_expression": str(expression), "chinese_expression": "", "description": ""} # 修正key名称
        return {
            "korean_expression": expression.get("korean_expression", expression.get("original", "")), # 兼容旧的 'original'
            "chinese_expression": expression.get("chinese_expression", expression.get("translated", "")), # 兼容旧的 'translated'
            "description": expression.get("description", expression.get("explanation", "")) # 兼容旧的 'explanation'
        }

    def _standardize_all(self):
        self.characters = [self._standardize_character(c) for c in self.characters if isinstance(c, dict) or self.logger.warning(f"忽略无效的人物术语条目: {c}")]
        self.proper_nouns = [self._standardize_noun(n) for n in self.proper_nouns if isinstance(n, dict) or self.logger.warning(f"忽略无效的专有名词术语条目: {n}")]
        self.cultural_expressions = [self._standardize_expression(e) for e in self.cultural_expressions if isinstance(e, dict) or self.logger.warning(f"忽略无效的文化表达术语条目: {e}")]
        # 过滤掉那些标准化后可能仍然无效的条目（例如，korean_name 为空）
        self.characters = [c for c in self.characters if c.get("korean_name")]
        self.proper_nouns = [n for n in self.proper_nouns if n.get("korean_term")]
        self.cultural_expressions = [e for e in self.cultural_expressions if e.get("korean_expression")]
        self.logger.info("术语库已标准化。")

    def get_formatted_terminology(self) -> str:
        """获取格式化的术语库，用于注入到翻译提示中。"""
        lines = []
        if not self.characters and not self.proper_nouns and not self.cultural_expressions:
            return "无可用术语。"

        lines.append("## 术语库参考")

        if self.characters:
            lines.append("### 人物")
            for char in self.characters:
                korean = char.get("korean_name", "")
                chinese = char.get("chinese_name", "")
                desc = char.get("description", "")
                if korean and chinese:
                    line = f"- {korean} → {chinese}"
                    if desc:
                        line += f" (说明: {desc})"
                    lines.append(line)
                elif korean: # 如果只有韩文名，也列出，提示可能需要翻译
                    line = f"- {korean} → (待确认/翻译)"
                    if desc:
                        line += f" (说明: {desc})"
                    lines.append(line)
            lines.append("")

        if self.proper_nouns:
            lines.append("### 专有名词")
            for noun in self.proper_nouns:
                korean = noun.get("korean_term", "")
                chinese = noun.get("chinese_term", "")
                desc = noun.get("description", "")
                if korean and chinese:
                    line = f"- {korean} → {chinese}"
                    if desc:
                        line += f" (说明: {desc})"
                    lines.append(line)
                elif korean:
                    line = f"- {korean} → (待确认/翻译)"
                    if desc:
                        line += f" (说明: {desc})"
                    lines.append(line)
            lines.append("")

        if self.cultural_expressions:
            lines.append("### 文化表达与特定说法")
            for expr in self.cultural_expressions:
                korean = expr.get("korean_expression", "")
                chinese = expr.get("chinese_expression", "")
                desc = expr.get("description", "")
                if korean and chinese:
                    line = f"- {korean} → {chinese}"
                    if desc:
                        line += f" (说明: {desc})"
                    lines.append(line)
                elif korean:
                    line = f"- {korean} → (待确认/翻译)"
                    if desc:
                        line += f" (说明: {desc})"
                    lines.append(line)
            lines.append("")
        
        formatted_str = "\n".join(lines).strip()
        if not formatted_str or formatted_str == "## 术语库参考": # 如果格式化后仍然为空
             return "无可用术语。"
        return formatted_str

# PromptBuilder 类将在此处下方添加 