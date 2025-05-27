# -*- coding: utf-8 -*-
"""
术语库统计工具

此脚本用于统计术语库JSON文件中的条目信息，包括：
- 总条目数
- 已翻译条目数
- 未翻译条目数
- 解释长度分布
- 术语类型分布（谚语、俚语、感叹词等）

使用方法：
python 术语库统计.py [术语库JSON文件路径]

如果不提供参数，将默认统计神经外科医生朴宰贤的术语库。
"""

import json
import os
import sys
import re
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# 设置中文字体
try:
    # 尝试使用系统中文字体
    font = FontProperties(fname=r"c:\windows\fonts\simsun.ttc")
except:
    font = None

def count_terms_by_type(explanations):
    """根据解释文本分析术语类型"""
    type_patterns = {
        '谚语': [r'谚语', r'俗语', r'proverb'],
        '俚语': [r'俚语', r'口语', r'slang'],
        '感叹词': [r'感叹词', r'叹词', r'interjection'],
        '敬语': [r'敬语', r'尊称', r'敬称', r'polite'],
        '比喻': [r'比喻', r'metaphor'],
        '习语': [r'习语', r'惯用语', r'idiom'],
        '其他': []
    }
    
    results = Counter()
    
    for explanation in explanations:
        matched = False
        for term_type, patterns in type_patterns.items():
            if any(re.search(pattern, explanation, re.IGNORECASE) for pattern in patterns):
                results[term_type] += 1
                matched = True
                break
        
        if not matched:
            results['其他'] += 1
    
    return results

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
        explanations = [item.get('explanation', '') for item in data]
        term_types = count_terms_by_type(explanations)
        
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
        
        return {
            'report': report,
            'stats': {
                'total': total_terms,
                'translated': translated_terms,
                'untranslated': untranslated_terms,
                'length_ranges': length_ranges,
                'term_types': term_types
            }
        }
    
    except Exception as e:
        return {'error': f"分析文件时出错: {str(e)}"}

def plot_statistics(stats, output_dir):
    """生成统计图表"""
    try:
        # 翻译状态饼图
        plt.figure(figsize=(10, 6))
        plt.pie(
            [stats['translated'], stats['untranslated']], 
            labels=['已翻译', '未翻译'],
            autopct='%1.1f%%',
            colors=['#4CAF50', '#F44336']
        )
        plt.title('术语翻译状态')
        plt.savefig(os.path.join(output_dir, '翻译状态.png'))
        plt.close()
        
        # 解释长度分布柱状图
        plt.figure(figsize=(10, 6))
        lengths = stats['length_ranges']
        plt.bar(
            lengths.keys(),
            lengths.values(),
            color='#2196F3'
        )
        plt.title('解释长度分布')
        plt.ylabel('条目数')
        if font:
            plt.xticks(fontproperties=font)
            plt.title('解释长度分布', fontproperties=font)
            plt.ylabel('条目数', fontproperties=font)
        plt.savefig(os.path.join(output_dir, '解释长度分布.png'))
        plt.close()
        
        # 术语类型分布柱状图
        plt.figure(figsize=(12, 6))
        types = stats['term_types']
        plt.bar(
            types.keys(),
            types.values(),
            color='#FF9800'
        )
        plt.title('术语类型分布')
        plt.ylabel('条目数')
        if font:
            plt.xticks(fontproperties=font)
            plt.title('术语类型分布', fontproperties=font)
            plt.ylabel('条目数', fontproperties=font)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '术语类型分布.png'))
        plt.close()
        
        return True
    except Exception as e:
        print(f"生成图表时出错: {str(e)}")
        return False

def main():
    # 默认术语库路径
    default_path = r"e:\日韩小说自动化翻译工具\程序端\程序\翻译工具\术语库\神经外科医生朴宰贤\cultural_expressions.json"
    
    # 获取命令行参数
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_path
    
    print(f"正在分析术语库: {file_path}")
    result = analyze_json_file(file_path)
    
    if 'error' in result:
        print(result['error'])
        return
    
    # 输出报告
    print("\n" + result['report'])
    
    # 保存报告到文件
    output_dir = os.path.dirname(file_path)
    report_path = os.path.join(output_dir, '术语库统计报告.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(result['report'])
    
    print(f"\n报告已保存至: {report_path}")
    
    # 尝试生成图表
    try:
        import matplotlib
        print("\n正在生成统计图表...")
        if plot_statistics(result['stats'], output_dir):
            print(f"图表已保存至: {output_dir}")
    except ImportError:
        print("\n注意: 未安装matplotlib库，无法生成图表。")
        print("可以通过运行 'pip install matplotlib' 安装该库。")

if __name__ == "__main__":
    main()