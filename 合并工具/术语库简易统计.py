# -*- coding: utf-8 -*-
"""
术语库简易统计工具

此脚本用于统计术语库JSON文件中的基本条目信息，包括：
- 总条目数
- 已翻译条目数
- 未翻译条目数
- 解释长度分布

使用方法：
python 术语库简易统计.py [术语库JSON文件路径]

如果不提供参数，将默认统计神经外科医生朴宰贤的术语库。
"""

import json
import os
import sys
import re
from collections import Counter

def analyze_json_file(file_path):
    """分析术语库JSON文件并生成统计报告"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_terms = len(data)
        translated_terms = sum(1 for item in data if item.get('translated') and item['translated'].strip())
        untranslated_terms = total_terms - translated_terms
        
        # 计算解释长度分布
        explanation_lengths = [len(item.get('explanation', '')) for item in data]
        length_ranges = {
            '短 (< 50字)': 0,
            '中 (50-100字)': 0,
            '长 (> 100字)': 0
        }
        
        for length in explanation_lengths:
            if length < 50:
                length_ranges['短 (< 50字)'] += 1
            elif length <= 100:
                length_ranges['中 (50-100字)'] += 1
            else:
                length_ranges['长 (> 100字)'] += 1
        
        # 分析术语类型
        term_types = analyze_term_types(data)
        
        # 生成报告
        report = f"""术语库统计报告
文件: {os.path.basename(file_path)}

基本统计:
- 总条目数: {total_terms}
- 已翻译条目数: {translated_terms} ({translated_terms/total_terms*100:.1f}%)
- 未翻译条目数: {untranslated_terms} ({untranslated_terms/total_terms*100:.1f}%)

解释长度分布:
- 短 (< 50字): {length_ranges['短 (< 50字)']} ({length_ranges['短 (< 50字)']/total_terms*100:.1f}%)
- 中 (50-100字): {length_ranges['中 (50-100字)']} ({length_ranges['中 (50-100字)']/total_terms*100:.1f}%)
- 长 (> 100字): {length_ranges['长 (> 100字)']} ({length_ranges['长 (> 100字)']/total_terms*100:.1f}%)

术语类型分布:"""
        
        for term_type, count in term_types.most_common():
            report += f"\n- {term_type}: {count} ({count/total_terms*100:.1f}%)"
        
        return report
    
    except Exception as e:
        return f"分析文件时出错: {str(e)}"

def analyze_term_types(data):
    """分析术语类型分布"""
    type_patterns = {
        '谚语': [r'谚语', r'俗语', r'proverb'],
        '俚语': [r'俚语', r'口语', r'slang', r'colloquial'],
        '感叹词': [r'感叹词', r'叹词', r'interjection'],
        '敬语': [r'敬语', r'尊称', r'敬称', r'polite'],
        '比喻': [r'比喻', r'metaphor'],
        '习语': [r'习语', r'惯用语', r'idiom'],
        '其他': []
    }
    
    results = Counter()
    
    for item in data:
        explanation = item.get('explanation', '')
        matched = False
        for term_type, patterns in type_patterns.items():
            if any(re.search(pattern, explanation, re.IGNORECASE) for pattern in patterns):
                results[term_type] += 1
                matched = True
                break
        
        if not matched:
            results['其他'] += 1
    
    return results

def main():
    # 默认术语库路径
    default_path = r"e:\日韩小说自动化翻译工具\程序端\程序\翻译工具\术语库\神经外科医生朴宰贤\cultural_expressions.json"
    
    # 获取命令行参数
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_path
    
    print(f"正在分析术语库: {file_path}")
    report = analyze_json_file(file_path)
    
    # 输出报告
    print("\n" + report)
    
    # 保存报告到文件
    output_dir = os.path.dirname(file_path)
    report_path = os.path.join(output_dir, '术语库统计报告.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n报告已保存至: {report_path}")

if __name__ == "__main__":
    main()