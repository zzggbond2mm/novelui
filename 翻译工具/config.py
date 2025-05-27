import os
import logging
import platform
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Core Configuration ---
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL")

# 配置参数优化与默认值处理
if not API_URL:
    API_URL = "https://noapi.ggb.today/v1/chat/completions"  # 默认API地址

if not API_KEY:
    API_KEY = os.getenv("GOOGLE_API_KEY")  # 向后兼容旧版配置

if not MODEL_NAME:
    MODEL_NAME = "gemini-2.5-pro-exp-n"  # 使用默认模型

# 加载额外的API密钥
ADDITIONAL_API_KEYS = []
for i in range(1, 20):  # 支持最多20个额外的API密钥
    key_name = f"API_KEY_{i}"
    key = os.getenv(key_name)
    if key:
        ADDITIONAL_API_KEYS.append(key)

# --- 文件编码设置 ---
# 根据操作系统自动调整默认编码
SYSTEM_ENCODING = "utf-8"
if platform.system() == "Windows":
    # Windows系统添加备用编码
    AVAILABLE_ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030", "latin1"]
else:
    AVAILABLE_ENCODINGS = ["utf-8", "latin1"] 

# --- Path Configuration ---
# Assuming the script runs from the '翻译工具' directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_ROOT_DIR = os.path.join(BASE_DIR, "..", "韩文稿")  # Relative path to source files
OUTPUT_ROOT_DIR = os.path.join(BASE_DIR, "..", "中文稿")  # Relative path to output files
TERMINOLOGY_DIR = os.path.join(BASE_DIR, "术语库")
PROMPT_DIR = os.path.join(BASE_DIR, "prompt")
PROGRESS_DIR = os.path.join(BASE_DIR, "进度") 
LOG_DIR = os.path.join(BASE_DIR, "logs")  # Added log directory

# --- File Names & Patterns ---
TRANSLATE_PROMPT_FILE = os.path.join(PROMPT_DIR, "translate_prompt.md")
UPDATE_PROMPT_FILE = os.path.join(PROMPT_DIR, "update_terminology_prompt.md")
PROGRESS_FILE_NAME = "progress.json"  # Using JSON for easier parsing

# 全局术语库文件路径 (作为默认备份)
GLOBAL_CHARACTER_FILE = os.path.join(TERMINOLOGY_DIR, "character.json")
GLOBAL_PROPER_NOUNS_FILE = os.path.join(TERMINOLOGY_DIR, "proper_nouns.json")
GLOBAL_CULTURAL_EXPRESSIONS_FILE = os.path.join(TERMINOLOGY_DIR, "cultural_expressions.json")

# 小说特定术语库的文件名
CHARACTER_FILENAME = "character.json"
PROPER_NOUNS_FILENAME = "proper_nouns.json"
CULTURAL_EXPRESSIONS_FILENAME = "cultural_expressions.json"

OUTPUT_FILE_PREFIX = "中_"
SOURCE_FILE_EXTENSION = ".md"  # Assuming source files are markdown

# --- API Settings ---
# 增加超时时间，提高对网络波动的容忍度
API_TIMEOUT = 600  # 超时时间延长至10分钟
MAX_RETRIES = 5    # 增加最大重试次数 
RETRY_DELAY = 5    # 初始延迟保持不变
# 添加指数退避的最大延迟限制
MAX_RETRY_DELAY = 60  # 最大延迟不超过60秒

# --- 并行设置 ---
DEFAULT_WORKERS = 3  # 默认工作线程数
MAX_WORKERS = 10     # 最大工作线程数

# --- 异常处理设置 ---
# 对特定错误进行重试的次数可以与普通错误不同
NETWORK_ERROR_RETRIES = 8  # 网络错误可以多尝试几次
PARSE_ERROR_RETRIES = 3    # 解析错误可能是格式问题，少尝试几次
TIMEOUT_ERROR_RETRIES = 6  # 超时错误多尝试几次

# --- Logging Configuration ---
LOG_FILE = os.path.join(LOG_DIR, "translation.log")
LOG_LEVEL = logging.INFO  # Default log level
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'
# 添加日志备份设置
LOG_BACKUP_COUNT = 5  # 保留5个备份日志文件
LOG_MAX_BYTES = 5 * 1024 * 1024  # 每个日志文件最大5MB

# --- Helper Functions ---
def get_novel_terminology_dir(novel_name):
    """获取指定小说的术语库目录路径"""
    path = os.path.join(TERMINOLOGY_DIR, novel_name)
    os.makedirs(path, exist_ok=True)  # 确保目录存在
    return path

def get_novel_character_file(novel_name):
    """获取指定小说的人物术语库文件路径"""
    return os.path.join(get_novel_terminology_dir(novel_name), CHARACTER_FILENAME)

def get_novel_proper_nouns_file(novel_name):
    """获取指定小说的专有名词术语库文件路径"""
    return os.path.join(get_novel_terminology_dir(novel_name), PROPER_NOUNS_FILENAME)

def get_novel_cultural_expressions_file(novel_name):
    """获取指定小说的文化表达术语库文件路径"""
    return os.path.join(get_novel_terminology_dir(novel_name), CULTURAL_EXPRESSIONS_FILENAME)

def get_progress_file(novel_name):
    """获取指定小说的进度文件路径"""
    return os.path.join(PROGRESS_DIR, f"{novel_name}_{PROGRESS_FILE_NAME}")

def get_all_api_keys() -> List[str]:
    """获取所有API密钥列表"""
    keys = []
    if API_KEY:
        keys.append(API_KEY)
    keys.extend(ADDITIONAL_API_KEYS)
    return keys

# --- Validation ---
def validate_config():
    """Basic validation for critical configurations."""
    errors = []

    # 验证API密钥
    all_keys = get_all_api_keys()
    if not all_keys:
        errors.append("未找到有效的API密钥。请检查 .env 文件。")
    else:
        logging.info(f"已加载 {len(all_keys)} 个API密钥")
        # 隐藏部分密钥显示
        for i, key in enumerate(all_keys):
            masked_key = key[:8] + "..." + key[-4:]
            logging.info(f"  密钥 {i+1}: {masked_key}")

    if not os.path.exists(PROMPT_DIR):
        try:
            os.makedirs(PROMPT_DIR, exist_ok=True)
            logging.warning(f"提示词目录不存在，已创建: {PROMPT_DIR}")
        except Exception as e:
            errors.append(f"无法创建提示词目录: {PROMPT_DIR}, 错误: {str(e)}")

    if not os.path.exists(TERMINOLOGY_DIR):
        try:
            os.makedirs(TERMINOLOGY_DIR, exist_ok=True)
            logging.warning(f"术语库目录不存在，已创建: {TERMINOLOGY_DIR}")
        except Exception as e:
            errors.append(f"无法创建术语库目录: {TERMINOLOGY_DIR}, 错误: {str(e)}")

    # 创建必要的目录
    for directory in [LOG_DIR, PROGRESS_DIR, SOURCE_ROOT_DIR, OUTPUT_ROOT_DIR]:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            errors.append(f"无法创建目录: {directory}, 错误: {str(e)}")
    
    # 检查模板文件
    if not os.path.exists(TRANSLATE_PROMPT_FILE):
        errors.append(f"翻译提示模板文件不存在: {TRANSLATE_PROMPT_FILE}")
    
    if not os.path.exists(UPDATE_PROMPT_FILE):
        errors.append(f"术语更新提示模板文件不存在: {UPDATE_PROMPT_FILE}")
    
    # 报告错误
    if errors:
        for error in errors:
            logging.error(f"错误：{error}")
        raise ValueError("\n".join(errors))
    else:
        logging.info("配置加载成功并通过基本验证。")

# 检查API URL格式是否合法
def is_valid_url(url):
    """简单检查URL格式是否有效"""
    if not url:
        return False
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
    return True

# 添加配置自检功能
def self_check():
    """执行配置自检，打印关键配置信息"""
    all_keys = get_all_api_keys()
    check_result = {
        "系统信息": platform.system() + " " + platform.version(),
        "Python版本": platform.python_version(),
        "API地址": API_URL + (" [有效]" if is_valid_url(API_URL) else " [无效!]"),
        "API密钥数量": f"{len(all_keys)} 个" + (" [有效]" if all_keys else " [无效!]"),
        "主API密钥": "已设置" if API_KEY else "未设置 [警告!]",
        "额外API密钥": f"{len(ADDITIONAL_API_KEYS)} 个",
        "模型名称": MODEL_NAME,
        "默认编码": SYSTEM_ENCODING,
        "尝试编码列表": str(AVAILABLE_ENCODINGS),
        "API超时设置": f"{API_TIMEOUT}秒",
        "最大重试次数": MAX_RETRIES,
        "日志目录": LOG_DIR + (" [存在]" if os.path.exists(LOG_DIR) else " [不存在!]"),
        "术语库目录": TERMINOLOGY_DIR + (" [存在]" if os.path.exists(TERMINOLOGY_DIR) else " [不存在!]"),
    }
    
    logging.info("=== 配置自检结果 ===")
    for key, value in check_result.items():
        logging.info(f"{key}: {value}")
    logging.info("=== 自检完成 ===")
    
    return check_result

# 设置网络代理（如需使用）
def setup_proxy(proxy_url=None):
    """设置网络代理"""
    if proxy_url:
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        logging.info(f"已设置网络代理: {proxy_url}")
    
# Run validation on import (optional, can be called explicitly in main)
# validate_config() # Commented out to allow calling later after logger setup 