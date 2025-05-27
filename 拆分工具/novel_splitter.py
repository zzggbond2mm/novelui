#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import argparse
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import regex

def extract_text_from_epub(epub_path):
    """从EPUB文件中提取文本内容"""
    book = epub.read_epub(epub_path)
    chapters = []
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # 获取HTML内容
            html_content = item.get_content().decode('utf-8')
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            # 提取文本
            text = soup.get_text()
            # 清理文本
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                chapters.append(text)
    
    return '\n\n'.join(chapters)

def extract_text_from_txt(txt_path):
    """从TXT文件中提取文本内容"""
    with open(txt_path, 'r', encoding='utf-8') as file:
        return file.read()

def split_text_by_paragraph(text, language, max_chars=800):
    """按段落拆分文本，确保每个片段不超过指定字符数"""
    if language == 'ja':
        # 日语分句正则
        sentence_pattern = regex.compile(r'[^。！？]+[。！？]')
    else:  # 韩语
        # 韩语分句正则
        sentence_pattern = regex.compile(r'[^\.!?]+[\.!?]')
    
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # 如果段落本身就超过了字符限制，需要按句子拆分
        if len(paragraph) > max_chars:
            sentences = sentence_pattern.findall(paragraph)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) <= max_chars:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
        else:
            # 如果当前块加上这个段落超过了字符限制
            if len(current_chunk) + len(paragraph) > max_chars:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(current_chunk)
    
    # 确保每个块的大小在600-800字之间
    final_chunks = []
    for chunk in chunks:
        if len(chunk) < 600 and final_chunks:
            # 如果当前块太小，尝试合并到前一个块
            if len(final_chunks[-1]) + len(chunk) <= max_chars:
                final_chunks[-1] += "\n\n" + chunk
            else:
                final_chunks.append(chunk)
        else:
            final_chunks.append(chunk)
    
    return final_chunks

def save_chunks_to_md(chunks, output_dir, base_filename):
    """将文本块保存为Markdown文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建索引文件
    index_content = f"# {base_filename} 索引\n\n"
    
    for i, chunk in enumerate(chunks, 1):
        # 创建Markdown文件名
        md_filename = f"{base_filename}_{i:03d}.md"
        file_path = os.path.join(output_dir, md_filename)
        
        # 写入Markdown文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(chunk)
        
        # 更新索引
        index_content += f"- [{md_filename}]({md_filename})\n"
    
    # 保存索引文件
    with open(os.path.join(output_dir, f"{base_filename}_index.md"), 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    return len(chunks)

def process_single_file(input_path, output_dir, language):
    """处理单个文件"""
    print(f"处理文件: {input_path}")
    
    # 根据文件类型提取文本
    if input_path.suffix.lower() == '.epub':
        text = extract_text_from_epub(input_path)
    elif input_path.suffix.lower() == '.txt':
        text = extract_text_from_txt(input_path)
    else:
        print(f"不支持的文件格式: {input_path.suffix}")
        return
    
    # 拆分文本
    chunks = split_text_by_paragraph(text, language)
    
    # 保存文件
    base_filename = input_path.stem
    
    # 如果未指定输出目录，则创建与文件名同名的目录
    if output_dir is None:
        parent_dir = os.path.dirname(os.path.dirname(input_path))
        output_dir = os.path.join(parent_dir, base_filename)
    
    count = save_chunks_to_md(chunks, output_dir, base_filename)
    
    print(f"处理完成! 共拆分为 {count} 个文件.")
    print(f"输出目录: {output_dir}")
    print(f"索引文件: {base_filename}_index.md")
    
    return count

def process_directory(input_dir, language):
    """处理目录中的所有文件"""
    input_dir = Path(input_dir)
    total_files = 0
    processed_files = 0
    
    print(f"扫描目录: {input_dir}")
    
    # 遍历目录中的所有文件
    for file_path in input_dir.glob('*.*'):
        if file_path.suffix.lower() in ['.epub', '.txt']:
            total_files += 1
            # 设置输出目录为上一级目录下的同名目录
            output_dir = os.path.join(file_path.parent.parent, file_path.stem)
            
            try:
                if process_single_file(file_path, output_dir, language):
                    processed_files += 1
            except Exception as e:
                print(f"处理文件 {file_path.name} 时出错: {str(e)}")
    
    print(f"\n总结: 扫描了 {total_files} 个文件，成功处理了 {processed_files} 个文件")

def main():
    parser = argparse.ArgumentParser(description='将长篇小说拆分成多个Markdown文档')
    parser.add_argument('-i', '--input', help='输入文件或目录路径')
    parser.add_argument('-o', '--output', help='输出目录路径')
    parser.add_argument('-l', '--language', choices=['ja', 'ko'], help='原文语言')
    parser.add_argument('-a', '--auto', action='store_true', help='使用自动模式，处理默认路径下的文件')
    
    args = parser.parse_args()
    
    # 自动模式
    if args.auto:
        # 韩文小说默认路径
        ko_input_dir = os.path.join("程序端", "程序", "韩文稿", "日韩小说原始文档")
        # 日文小说默认路径可以根据需要添加
        
        if os.path.exists(ko_input_dir):
            process_directory(ko_input_dir, 'ko')
        else:
            print(f"错误: 找不到默认韩文小说目录 {ko_input_dir}")
    
    # 手动模式
    elif args.input:
        input_path = Path(args.input)
        
        # 设置语言
        language = args.language
        if language is None:
            if "韩文" in str(input_path):
                language = 'ko'
            elif "日文" in str(input_path):
                language = 'ja'
            else:
                print("错误: 无法自动判断语言，请使用 -l 参数指定语言")
                return
        
        # 处理目录
        if input_path.is_dir():
            process_directory(input_path, language)
        # 处理单个文件
        elif input_path.is_file():
            process_single_file(input_path, args.output, language)
        else:
            print(f"错误: 输入路径 {input_path} 不存在")
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 