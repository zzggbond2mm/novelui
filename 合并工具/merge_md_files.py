#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
import datetime

def print_status(msg):
    """打印状态信息并刷新输出"""
    print(msg, flush=True)

def natural_sort_key(s):
    """用于自然排序的键函数，确保文件按照数字顺序排序（如00001在00002之前）"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

def merge_md_files(input_dir, output_file=None, header=None, footer=None, formats=None):
    """
    合并指定目录下的所有.md文件到指定格式的文件
    
    参数:
        input_dir (str): 包含.md文件的文件夹路径
        output_file (str, optional): 输出文件路径（不含扩展名），默认为"程序端\完整版\[文件夹名]完整版"
        header (str): 要添加到合并文件开头的文本
        footer (str): 要添加到合并文件结尾的文本
        formats (list): 输出文件格式列表，可包含'txt'和'md'，默认两种都输出
    """
    print_status(f"开始处理：合并 {input_dir} 目录中的Markdown文件")
    
    if not os.path.isdir(input_dir):
        print_status(f"错误: 目录 '{input_dir}' 不存在")
        return False
    
    # 如果没有指定输出文件，则默认为"程序端\完整版\[文件夹名]完整版"
    if output_file is None:
        # 获取输入目录的文件夹名
        dir_name = os.path.basename(os.path.normpath(input_dir))
        
        # 创建默认的输出目录路径
        default_output_dir = os.path.normpath(os.path.join(os.getcwd(), "..", "..", "完整版"))
        
        # 确保输出目录存在
        try:
            os.makedirs(default_output_dir, exist_ok=True)
            print_status(f"输出目录已确认: {default_output_dir}")
        except Exception as e:
            print_status(f"创建默认输出目录失败: {str(e)}")
        
        # 设置默认输出文件路径（不含扩展名）
        output_file = os.path.join(default_output_dir, f"{dir_name}完整版")
    
    # 如果output_file带有扩展名，则去掉扩展名
    output_file = os.path.splitext(output_file)[0]
    print_status(f"输出文件基础路径: {output_file}")
    
    # 确保输出文件的目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            print_status(f"创建输出目录: {output_dir}")
        except Exception as e:
            print_status(f"创建输出目录失败: {str(e)}")
            return False
    
    # 设置默认格式
    if formats is None:
        formats = ['txt', 'md']
    
    print_status(f"将输出格式: {', '.join(formats)}")
    
    # 获取所有.md文件
    md_files = [f for f in os.listdir(input_dir) if f.endswith('.md')]
    
    if not md_files:
        print_status(f"错误: 在目录 '{input_dir}' 中未找到.md文件")
        return False
    
    # 使用自然排序方法对文件进行排序（按文件名中的数字排序）
    md_files.sort(key=natural_sort_key)
    
    print_status(f"找到 {len(md_files)} 个.md文件，开始合并...")
    print_status(f"使用自然排序方法（按文件名序号排序）")
    
    # 输出文件字典，格式为键，文件对象为值
    output_files = {}
    error_files = []
    merged_count = 0
    success = True
    
    try:
        # 为每种格式打开一个输出文件
        for fmt in formats:
            output_path = f"{output_file}.{fmt}"
            try:
                output_files[fmt] = open(output_path, 'w', encoding='utf-8')
                print_status(f"将输出到: {output_path}")
            except Exception as e:
                print_status(f"无法创建输出文件 {output_path}: {str(e)}")
                success = False
        
        if not output_files:
            print_status("错误: 无法创建任何输出文件")
            return False
        
        # 写入页眉（如果有）
        if header:
            for fmt, f in output_files.items():
                f.write(header + '\n\n')
                print_status(f"已写入页眉到 .{fmt} 格式文件")
        
        # 合并文件内容
        for i, md_file in enumerate(md_files):
            file_path = os.path.join(input_dir, md_file)
            print_status(f"合并文件 ({i+1}/{len(md_files)}): {md_file}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    for fmt, f in output_files.items():
                        f.write(content)
                        # 确保文件之间有换行
                        if not content.endswith('\n'):
                            f.write('\n')
                merged_count += 1
            except Exception as e:
                print_status(f"  警告: 处理文件 '{md_file}' 时出错: {str(e)}")
                error_files.append((md_file, str(e)))
        
        # 写入页脚（如果有）
        if footer:
            for fmt, f in output_files.items():
                f.write('\n' + footer)
                print_status(f"已写入页脚到 .{fmt} 格式文件")
        
        # 关闭所有输出文件
        for fmt, f in output_files.items():
            f.close()
            print_status(f"已关闭 .{fmt} 格式文件")
        
        for fmt in formats:
            output_path = f"{output_file}.{fmt}"
            print_status(f"合并完成! 已生成文件: {output_path}")
        
        print_status(f"成功合并了 {merged_count}/{len(md_files)} 个.md文件")
        
        if error_files:
            print_status("\n处理以下文件时出现错误:")
            for file_name, error in error_files:
                print_status(f"- {file_name}: {error}")
        
        return merged_count == len(md_files) and success
    except Exception as e:
        print_status(f"合并过程中出错: {str(e)}")
        # 确保关闭所有已打开的文件
        for f in output_files.values():
            try:
                f.close()
            except:
                pass
        return False

def create_default_header():
    """创建默认页眉，包含时间戳和版权信息"""
    now = datetime.datetime.now()
    header = f"# 合并文档\n\n"
    header += f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
    return header

def create_default_footer():
    """创建默认页脚"""
    return "文档结束"

def main():
    parser = argparse.ArgumentParser(description='将指定文件夹中的所有Markdown文件合并为一个或多个指定格式的文件')
    parser.add_argument('input_dir', help='包含.md文件的文件夹路径')
    parser.add_argument('-o', '--output', help='输出文件路径（不含扩展名）')
    parser.add_argument('--header', help='要添加到合并文件开头的文本')
    parser.add_argument('--footer', help='要添加到合并文件结尾的文本')
    parser.add_argument('--no-header', action='store_true', help='不添加默认页眉')
    parser.add_argument('--no-footer', action='store_true', help='不添加默认页脚')
    parser.add_argument('-f', '--format', choices=['txt', 'md', 'both'], default='both',
                      help='输出文件格式: txt, md, 或both(两种都输出，默认)')
    
    # 处理旧的命令行格式（向后兼容）
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        if len(sys.argv) > 2 and not sys.argv[2].startswith('-'):
            args = parser.parse_args([sys.argv[1], '-o', sys.argv[2]] + sys.argv[3:])
        else:
            args = parser.parse_args([sys.argv[1]] + sys.argv[2:])
    else:
        args = parser.parse_args()
    
    print_status("\n====== MD文件合并工具 ======")
    print_status(f"输入目录: {args.input_dir}")
    print_status(f"输出文件: {args.output if args.output else '默认路径'}")
    print_status(f"输出格式: {args.format}")
    print_status(f"页眉设置: {'不使用' if args.no_header else '使用自定义' if args.header else '使用默认'}")
    print_status(f"页脚设置: {'不使用' if args.no_footer else '使用自定义' if args.footer else '使用默认'}")
    print_status("=============================\n")
    
    # 设置页眉和页脚
    header = None if args.no_header else (args.header or create_default_header())
    footer = None if args.no_footer else (args.footer or create_default_footer())
    
    # 设置输出格式
    formats = []
    if args.format == 'txt':
        formats = ['txt']
    elif args.format == 'md':
        formats = ['md']
    else:  # 'both'
        formats = ['txt', 'md']
    
    success = merge_md_files(args.input_dir, args.output, header, footer, formats)
    
    if success:
        print_status("合并任务成功完成!")
    else:
        print_status("合并任务完成，但有部分文件处理失败!")
    
    print_status("=============================")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 