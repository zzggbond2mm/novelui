# 韩中小说自动化翻译 Python 脚本开发方案

## 1. 目标

开发一个 Python 脚本，实现韩文小说稿件到中文的自动化翻译。该脚本使用 Gemini API，并结合动态更新的术语库，实现高质量、术语一致且符合文化习惯的翻译。脚本已实现 `readme.md` 中描述的"连续翻译流程"和"并行翻译流程"。

## 2. 核心功能

1.  **基于 API 的翻译**: 使用 Google Gemini API (`gemini-1.5-flash-latest` 或其他配置版本) 执行核心翻译任务。
2.  **连续翻译模式**:
    *   按指定顺序（起始编号、数量、范围）处理输入文件。
    *   逐文件进行翻译。
    *   翻译完成后调用 AI 分析译文，**动态更新术语库**（人名、专有名词、文化表达）。
    *   使用更新后的术语库翻译下一个文件。
3.  **并行翻译模式**:
    *   使用多个API密钥同时处理多个翻译任务。
    *   使用API密钥轮换器，确保负载均衡和错误恢复。
    *   实现线程安全的术语库更新和访问。
    *   提供实时并行进度显示。
4.  **术语库管理**:
    *   加载 `术语库` 目录下的 `character.json`, `proper_nouns.json`, `cultural_expressions.json` 文件。
    *   在构建翻译提示时，将术语库内容整合进去，指导 AI 进行一致性翻译。
    *   实现术语库的 AI 自动更新机制。
5.  **文件处理**:
    *   读取指定目录下的韩文源文件（`.md` 格式，文件名包含编号）。
    *   将翻译结果写入 `中文稿` 目录下的对应小说子目录，文件名格式为 `中_XXXXX.md`。
6.  **提示工程**:
    *   加载 `prompt/translate_prompt.md` 作为基础翻译指南。
    *   加载 `prompt/update_terminology_prompt.md` 作为术语更新指南。
    *   动态地将当前术语库信息注入到发送给 API 的最终提示中。
7.  **进度跟踪与恢复**:
    *   记录已成功翻译的文件编号，保存在 `进度/小说名_progress.json` 中。
    *   支持从上次中断处继续翻译。
    *   提供翻译统计信息（总文件数、已完成文件数、耗时、平均速度等）。
8.  **配置管理**:
    *   从 `.env` 文件和环境变量读取 API 密钥、模型名称、文件路径等。
9.  **错误处理**:
    *   对 API 调用、文件读写等操作进行基本的错误捕获和日志记录。
    *   支持 API 调用失败时的自动重试机制。

## 3. 技术选型

*   **编程语言**: Python 3.9+
*   **核心库**:
    *   `requests`: 用于与 Gemini API 交互。
    *   `json`: 处理术语库 JSON 文件和 API 响应。
    *   `os`: 文件和目录操作。
    *   `argparse`: 处理命令行参数（起始文件、数量等）。
    *   `dotenv`: 管理环境变量（API Key 等敏感信息）。
    *   `logging`: 记录程序运行信息和错误。
    *   `re`: 用于从文件名提取编号和处理 JSON 响应。
    *   `threading`: 实现多线程并行处理。
    *   `queue`: 实现线程安全的任务队列和结果收集。
    *   `concurrent.futures`: 提供高级线程池管理。

## 4. 模块设计

已实现的项目结构：

```
translate_tool/ # 脚本根目录
│
├── main.py                   # 主程序入口，处理命令行参数，协调翻译流程
├── config.py                 # 加载和管理配置（API Key, Paths, Model）
├── api_client.py             # 封装 Gemini API 调用逻辑（翻译、术语更新）
├── terminology_manager.py    # 加载、管理、更新术语库 JSON 文件
├── file_handler.py           # 处理源文件读取和译文写入，管理文件编号
├── prompt_builder.py         # 构建包含基础指南和当前术语的最终 API 提示
├── progress_tracker.py       # 跟踪翻译进度，支持断点续传
├── parallel_manager.py       # 处理并行翻译的线程管理和API密钥轮换（新增）
├── check_progress.py         # 查看翻译进度的独立工具
│
├── 术语库/                   # 术语库文件目录
│   ├── character.json        # 人物名称术语库
│   ├── proper_nouns.json     # 专有名词术语库
│   └── cultural_expressions.json  # 文化表达术语库
│
├── prompt/                   # 提示模板目录
│   ├── translate_prompt.md          # 翻译任务提示模板
│   └── update_terminology_prompt.md  # 术语更新任务提示模板
│
├── 进度/                     # 进度记录目录
│   └── 小说名_progress.json  # 每部小说独立的进度记录文件
│
├── logs/                     # 日志目录
│   └── translation.log       # 日志文件
│
├── requirements.txt          # Python 依赖列表
├── .env                      # 存储 API Key 等敏感信息（需加入 .gitignore）
├── .env.example              # 环境变量示例文件
└── readme_dev.md             # 项目开发说明文档
```

## 5. 关键组件功能

### 5.1 **主程序（main.py）**
* 处理命令行参数，支持多种文件选择模式（起始文件、单一文件、文件范围）
* 协调其他组件完成翻译流程
* 根据参数选择串行或并行翻译模式
* 提供进度和统计信息输出

### 5.2 **配置管理（config.py）**
* 从 `.env` 文件加载配置
* 提供所有路径和 API 相关配置
* 加载并管理多个API密钥
* 提供配置验证功能，确保关键配置正确设置

### 5.3 **API 客户端（api_client.py）**
* 负责与 Gemini API 的所有交互
* 提供翻译和术语更新的 API 调用功能
* 实现 API 调用重试机制和错误处理
* 支持动态切换API密钥
* 解析 API 响应，提取 JSON 数据

### 5.4 **术语管理（terminology_manager.py）**
* 加载和标准化术语库格式
* 提供格式化术语用于提示构建
* 实现线程安全的术语库更新和保存
* 处理术语冲突和格式验证

### 5.5 **文件处理（file_handler.py）**
* 获取源文件列表并按编号排序
* 读取源文件内容
* 写入翻译结果到目标文件
* 检查输出文件是否存在

### 5.6 **提示构建（prompt_builder.py）**
* 加载提示模板文件
* 格式化术语库为文本形式
* 构建翻译提示和术语更新提示
* 替换模板中的变量

### 5.7 **进度跟踪（progress_tracker.py）**
* 加载和保存进度记录
* 标记文件为已完成状态
* 提供翻译统计信息
* 支持重置进度功能
* 增强对并行任务的进度跟踪

### 5.8 **并行管理（parallel_manager.py）**
* 管理工作线程池
* 实现API密钥轮换器
* 提供线程安全的任务分配和状态更新
* 处理并行任务的异常和错误恢复
* 协调术语库的并发访问

### 5.9 **工具函数（utils.py）**
* 设置日志记录格式和处理
* 提供共享锁和同步工具

## 6. 命令行参数

```bash
# 必须参数
--novel               小说名称，对应源文件和目标文件的目录名

# 选择性参数组（三选一）
--start               起始文件编号
--file                单一文件编号（只翻译这一个文件）
--range               文件编号范围，格式如 '1-10'

# 其他参数
--count               要翻译的文件数量（与--start一起使用）
--force               强制重新翻译已完成的文件
--reset               重置进度（慎用）
--debug               启用调试日志
--parallel            启用并行翻译模式
--workers             并行工作线程数量（默认为3）
```

## 7. 使用示例

```bash
# 翻译 "我的小说" 从第 5 章开始，共翻译 20 章
python main.py --novel "我的小说" --start 5 --count 20

# 翻译 "另一部作品" 的第 10 章到第 15 章
python main.py --novel "另一部作品" --range 10-15

# 强制重新翻译第 8 章
python main.py --novel "我的小说" --file 8 --force

# 重置进度并从头开始翻译
python main.py --novel "我的小说" --reset --start 1

# 使用并行模式翻译第 1 到 30 章，使用 5 个工作线程
python main.py --novel "我的小说" --range 1-30 --parallel --workers 5
```

## 8. 环境变量配置 (.env)

创建 `.env` 文件，或从 `.env.example` 复制修改，包含以下内容：

```
API_URL="https://noapi.ggb.today/v1/chat/completions"
API_KEY="您的主要API密钥"
MODEL="gemini-2.5-pro-exp-n"

# 用于并行翻译的额外API密钥
API_KEY_1="额外的API密钥1"
API_KEY_2="额外的API密钥2"
# ... 可添加更多API密钥
```

## 9. 工作流程详解

### 9.1 串行翻译流程

1. **初始化阶段**
   * 解析命令行参数
   * 加载配置并验证
   * 设置日志记录
   * 初始化各个组件

2. **翻译流程**
   * 获取源文件列表
   * 逐个处理文件：
     * 检查文件是否已翻译（除非强制重新翻译）
     * 读取源文件内容
     * 加载当前术语库
     * 构建翻译提示
     * 调用 API 进行翻译
     * 保存翻译结果
     * 构建术语更新提示
     * 调用 API 提取新术语
     * 更新术语库
     * 标记文件为已完成
     * 提供进度统计

3. **错误处理**
   * API 调用错误时自动重试
   * 文件处理错误时跳过并继续下一个文件
   * 记录详细错误日志

### 9.2 并行翻译流程

1. **初始化阶段**
   * 解析命令行参数，包括并行选项和工作线程数量
   * 加载所有可用的API密钥
   * 验证API密钥数量是否足够支持请求的并行度
   * 初始化术语库锁和共享资源

2. **线程池设置**
   * 创建工作线程池，大小基于`--workers`参数
   * 初始化任务队列
   * 设置API密钥轮换器

3. **任务分配**
   * 收集所有需要翻译的文件
   * 根据文件数量和依赖关系，将任务分组
   * 将任务提交到线程池

4. **并行执行**
   * 每个工作线程：
     * 从队列获取翻译任务
     * 从密钥轮换器获取API密钥
     * 获取术语库共享锁（读取）
     * 执行翻译
     * 获取术语库排他锁（写入）
     * 更新术语库
     * 释放锁
     * 更新进度

5. **结果收集与监控**
   * 收集每个任务的完成状态
   * 处理失败的任务（可选择重试或跳过）
   * 更新并显示总体进度

6. **结束处理**
   * 等待所有线程完成
   * 合并结果并保存最终进度
   * 显示翻译统计信息

## 10. 并行翻译技术实现关键点

### 10.1 API密钥轮换器

API密钥轮换器是并行翻译的核心组件，负责在多个API密钥之间智能切换：

```python
class ApiKeyRotator:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_index = 0
        self.lock = threading.Lock()
        self.key_stats = {key: {"usage": 0, "errors": 0} for key in api_keys}
    
    def get_next_key(self):
        with self.lock:
            key = self.api_keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            self.key_stats[key]["usage"] += 1
            return key
    
    def report_error(self, key):
        with self.lock:
            if key in self.key_stats:
                self.key_stats[key]["errors"] += 1
```

### 10.2 术语库同步机制

为防止多线程访问术语库时发生冲突，使用读写锁实现术语库的并发控制：

```python
class TerminologyLock:
    def __init__(self):
        self.read_lock = threading.Semaphore(value=10)  # 允许多个读取
        self.write_lock = threading.Lock()              # 写入时互斥
        self.readers = 0
        self.readers_lock = threading.Lock()
    
    def acquire_read(self):
        self.read_lock.acquire()
        with self.readers_lock:
            self.readers += 1
            if self.readers == 1:
                # 第一个读取者需要获取写锁以阻止写入
                self.write_lock.acquire()
        self.read_lock.release()
    
    def release_read(self):
        with self.readers_lock:
            self.readers -= 1
            if self.readers == 0:
                # 最后一个读取者释放写锁
                self.write_lock.release()
    
    def acquire_write(self):
        self.write_lock.acquire()
    
    def release_write(self):
        self.write_lock.release()
```

### 10.3 进度跟踪与状态更新

并行进度跟踪需要支持多线程同时更新进度：

```python
class ParallelProgressTracker:
    def __init__(self, total_files):
        self.total = total_files
        self.completed = 0
        self.failed = 0
        self.in_progress = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.task_status = {}  # 跟踪每个任务的状态
    
    def start_task(self, file_id):
        with self.lock:
            self.in_progress += 1
            self.task_status[file_id] = "in_progress"
    
    def complete_task(self, file_id):
        with self.lock:
            self.completed += 1
            self.in_progress -= 1
            self.task_status[file_id] = "completed"
    
    def fail_task(self, file_id, error=None):
        with self.lock:
            self.failed += 1
            self.in_progress -= 1
            self.task_status[file_id] = f"failed: {error}"
    
    def get_progress(self):
        with self.lock:
            return {
                "total": self.total,
                "completed": self.completed,
                "failed": self.failed,
                "in_progress": self.in_progress,
                "percent": (self.completed / self.total) * 100 if self.total > 0 else 0,
                "elapsed": time.time() - self.start_time,
                "tasks": self.task_status.copy()
            }
```

### 10.4 任务协调器

并行任务协调器负责分配和管理所有翻译任务：

```python
class TranslationCoordinator:
    def __init__(self, novel_name, file_handler, api_client, terminology_manager, 
                 progress_tracker, num_workers=3):
        self.novel_name = novel_name
        self.file_handler = file_handler
        self.api_client = api_client
        self.terminology_manager = terminology_manager
        self.progress_tracker = progress_tracker
        self.num_workers = num_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.term_lock = TerminologyLock()
        
    def translate_file(self, file_id):
        # 单个文件翻译流程，包括获取锁和释放锁的逻辑
        
    def run_parallel_translation(self, file_ids):
        futures = []
        for file_id in file_ids:
            future = self.executor.submit(self.translate_file, file_id)
            futures.append(future)
        
        # 等待所有任务完成并处理结果
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                # 处理结果...
            except Exception as e:
                logging.error(f"任务执行失败: {str(e)}")
```

## 11. 待优化功能

* **长文本处理**: 当前未实现单个章节内容超过 API 单次请求限制的处理方案。可考虑分块处理和合并结果。
* **术语冲突处理**: 可优化术语合并逻辑，处理 AI 提出的可能不准确的术语，特别是在并行环境下。
* **用户界面**: 可开发简单的 Web 界面，便于不熟悉命令行的用户使用。
* **API密钥管理强化**: 添加API密钥使用统计和自动轮换策略，更好地处理API限制。
* **扩展支持的 API 类型**: 除了 Gemini，可支持其他 LLM API。
* **翻译质量评估**: 可添加翻译质量评估机制，检测可能的问题翻译段落。
* **更高级的依赖关系处理**: 优化并行任务的依赖关系判断，在保证术语一致性的同时最大化并行度。
