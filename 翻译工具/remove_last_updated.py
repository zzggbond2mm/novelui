import json
import os

def remove_last_updated_field(file_path):
    """从JSON文件中移除所有的last_updated字段"""
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 移除每个项目中的last_updated字段
        for item in data:
            if 'last_updated' in item:
                del item['last_updated']
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"成功处理文件: {file_path}")
        return True
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {str(e)}")
        return False

def main():
    # 术语库目录
    base_dir = r"e:\日韩小说自动化翻译工具\程序端\程序\翻译工具\术语库\神经外科医生朴宰贤"
    
    # 需要处理的文件
    files = [
        os.path.join(base_dir, "character.json"),
        os.path.join(base_dir, "cultural_expressions.json"),
        os.path.join(base_dir, "proper_nouns.json")
    ]
    
    # 处理每个文件
    success_count = 0
    for file_path in files:
        if remove_last_updated_field(file_path):
            success_count += 1
    
    print(f"处理完成，成功处理 {success_count}/{len(files)} 个文件")

if __name__ == "__main__":
    main()