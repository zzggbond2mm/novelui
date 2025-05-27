#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试术语更新解析功能
"""

import os
import sys
import json
import logging
import shutil
from terminology_manager import TerminologyManager

# 示例更新响应
SAMPLE_RESPONSE = """
### 更新人物
- 金道勋 (别名: 道勋, 勋): 男主角，28岁的职业玩家
- 李敏智: 女主角，游戏公司策划
- 黄伟明 (别名: 伟明, 小黄): 男主角的好友

### 更新专有名词
- 神域 → 神的领域: 游戏名称
- 赤龙公会: 游戏中的公会组织
- 星辰大陆: 游戏中的一个大陆名称

### 更新文化表达
- 화이팅 → 加油: 韩语中表示鼓励的用语
- 대박: 大发，表示非常惊讶或者很厉害的意思
- 아이고 → 哎呦: 韩语中表示惊讶或者不满的感叹词
"""

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def clear_test_terminology(test_novel):
    """清除测试小说的术语库"""
    term_dir = os.path.join("术语库", test_novel)
    
    if os.path.exists(term_dir):
        try:
            # 如果目录存在，先删除它
            shutil.rmtree(term_dir)
            print(f"已删除原有测试术语库目录: {term_dir}")
        except Exception as e:
            print(f"删除目录时出错: {str(e)}")
    
    # 重新创建目录
    os.makedirs(term_dir, exist_ok=True)
    print(f"已创建新的测试术语库目录: {term_dir}")

def test_terminology_parsing():
    """测试术语解析功能"""
    setup_logging()
    
    # 使用测试小说名
    test_novel = "测试小说"
    
    # 清除已有的测试术语库
    clear_test_terminology(test_novel)
    
    # 初始化术语管理器
    term_manager = TerminologyManager(test_novel)
    
    # 使用示例响应测试解析功能
    char_added, noun_added, expr_added = term_manager.update_terminology_from_api_response(SAMPLE_RESPONSE)
    
    # 打印结果
    print("\n====== 测试结果 ======")
    print(f"添加人物: {char_added}个")
    print(f"添加专有名词: {noun_added}个")
    print(f"添加文化表达: {expr_added}个")
    print("======================\n")
    
    # 打印更新后的术语库内容
    print("人物术语库内容:")
    for char in term_manager.characters:
        print(f"  - {char}")
    
    print("\n专有名词术语库内容:")
    for noun in term_manager.proper_nouns:
        print(f"  - {noun}")
    
    print("\n文化表达术语库内容:")
    for expr in term_manager.cultural_expressions:
        print(f"  - {expr}")
    
    # 验证术语库文件是否正确保存
    print("\n检查术语库文件:")
    term_files = [
        os.path.join("术语库", test_novel, "character.json"),
        os.path.join("术语库", test_novel, "proper_nouns.json"),
        os.path.join("术语库", test_novel, "cultural_expressions.json")
    ]
    
    for file_path in term_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"文件 {file_path} 存在，包含 {len(data)} 条记录")
        else:
            print(f"文件 {file_path} 不存在")

if __name__ == "__main__":
    test_terminology_parsing() 