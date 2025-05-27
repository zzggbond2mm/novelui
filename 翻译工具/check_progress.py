#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import time

def check_progress(novel_name):
    """检查翻译进度"""
    # 定义路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    progress_dir = os.path.join(script_dir, "进度")
    output_dir = os.path.join(script_dir, "..", "中文稿", novel_name)
    
    # 确保进度目录存在
    if not os.path.exists(progress_dir):
        print(f"进度目录不存在: {progress_dir}")
        return
    
    # 读取进度文件 - 使用正确的格式：novel_name + _progress.json
    progress_file = os.path.join(progress_dir, f"{novel_name}_progress.json")
    if not os.path.exists(progress_file):
        print(f"进度文件不存在: {progress_file}")
        return
    
    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)
        
        completed_files = progress.get("completed_files", [])
        total_files = progress.get("total_files", 0)
        
        print(f"小说: {novel_name}")
        print(f"已完成: {len(completed_files)}/{total_files} 个文件")
        
        if completed_files:
            print(f"已完成文件: {', '.join(map(str, sorted(completed_files)))}")
        
        # 检查输出目录
        if os.path.exists(output_dir):
            output_files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
            print(f"输出目录: {output_dir}")
            print(f"输出文件数量: {len(output_files)}")
            if output_files:
                print(f"输出文件: {', '.join(sorted(output_files))}")
                
                # 显示最新文件的内容
                if output_files:
                    newest_file = sorted(output_files)[-1]
                    newest_path = os.path.join(output_dir, newest_file)
                    try:
                        with open(newest_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        print(f"\n最新文件 ({newest_file}) 内容预览:")
                        print("-" * 50)
                        print(content[:500] + ("..." if len(content) > 500 else ""))
                        print("-" * 50)
                    except Exception as e:
                        print(f"读取文件时出错: {str(e)}")
        else:
            print(f"输出目录不存在: {output_dir}")
    
    except Exception as e:
        print(f"检查进度时出错: {str(e)}")

def main():
    if len(sys.argv) < 2:
        print("用法: python check_progress.py 小说名称")
        sys.exit(1)
    
    novel_name = sys.argv[1]
    check_progress(novel_name)

if __name__ == "__main__":
    main() 