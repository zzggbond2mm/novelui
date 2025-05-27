# -*- coding: utf-8 -*-
"""
术语库高级统计工具

此脚本用于统计术语库JSON文件中的详细条目信息，包括：
- 总条目数、已翻译条目数、未翻译条目数
- 解释长度分布
- 术语类型分布
- 导出未翻译条目列表
- 导出CSV格式的统计结果

使用方法：
python 术语库高级统计.py [术语库JSON文件路径]

如果不提供参数，将默认统计神经外科医生朴宰贤的术语库。
"""

import json
import os
import sys
import re
import csv
from collections import Counter
from datetime import datetime

def analyze_json_file(file_path):
    """分析术语库JSON文件并生成统计报告"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_terms = len(data)
        translated_items = [item for item in data if item.get('translated') and item['translated'].strip()]
        translated_terms = len(translated_items)
        untranslated_items = [item for item in data if not item.get('translated') or not item['translated'].strip()]
        untranslated_terms = len(untranslated_items)
        
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
分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
        
        if untranslated_terms > 0:
            report += "\n\n未翻译条目列表:"
            for i, item in enumerate(untranslated_items, 1):
                report += f"\n{i}. {item['original']}"
        
        return {
            'report': report,
            'stats': {
                'total': total_terms,
                'translated': translated_terms,
                'untranslated': untranslated_terms,
                'length_ranges': length_ranges,
                'term_types': term_types
            },
            'untranslated_items': untranslated_items,
            'data': data
        }
    
    except Exception as e:
        return {'error': f"分析文件时出错: {str(e)}"}

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

def export_to_csv(result, output_dir):
    """导出统计结果到CSV文件"""
    try:
        # 导出基本统计
        stats_path = os.path.join(output_dir, '术语库统计_基本数据.csv')
        with open(stats_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['统计项', '数值', '百分比'])
            
            stats = result['stats']
            total = stats['total']
            
            writer.writerow(['总条目数', total, '100%'])
            writer.writerow(['已翻译条目数', stats['translated'], f"{stats['translated']/total*100:.1f}%"])
            writer.writerow(['未翻译条目数', stats['untranslated'], f"{stats['untranslated']/total*100:.1f}%"])
            
            writer.writerow([])
            writer.writerow(['解释长度分布', '', ''])
            for length_range, count in stats['length_ranges'].items():
                writer.writerow([length_range, count, f"{count/total*100:.1f}%"])
            
            writer.writerow([])
            writer.writerow(['术语类型分布', '', ''])
            for term_type, count in stats['term_types'].most_common():
                writer.writerow([term_type, count, f"{count/total*100:.1f}%"])
        
        # 导出未翻译条目
        if stats['untranslated'] > 0:
            untranslated_path = os.path.join(output_dir, '术语库_未翻译条目.csv')
            with open(untranslated_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['序号', '原文'])
                for i, item in enumerate(result['untranslated_items'], 1):
                    writer.writerow([i, item['original']])
        
        # 导出完整术语库数据
        full_data_path = os.path.join(output_dir, '术语库_完整数据.csv')
        with open(full_data_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['序号', '原文', '译文', '解释', '解释长度', '是否已翻译'])
            for i, item in enumerate(result['data'], 1):
                original = item.get('original', '')
                translated = item.get('translated', '')
                explanation = item.get('explanation', '')
                is_translated = '是' if translated.strip() else '否'
                writer.writerow([i, original, translated, explanation, len(explanation), is_translated])
        
        return True, [stats_path, untranslated_path if stats['untranslated'] > 0 else None, full_data_path]
    
    except Exception as e:
        return False, f"导出CSV时出错: {str(e)}"

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
    
    # 导出CSV
    print("\n正在导出CSV格式的统计结果...")
    success, csv_files = export_to_csv(result, output_dir)
    
    if success:
        print("CSV文件已导出:")
        for csv_file in csv_files:
            if csv_file:
                print(f"- {os.path.basename(csv_file)}")
    else:
        print(csv_files)  # 输出错误信息

if __name__ == "__main__":
    main()