import logging
import sys
import config

def setup_logging():
    """Configures the logging for the application."""
    # Ensure log directory exists
    os.makedirs(config.LOG_DIR, exist_ok=True)

    # Create handlers
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)

    # Set formatters
    formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Get root logger and set level
    logger = logging.getLogger()
    logger.setLevel(config.LOG_LEVEL)

    # Add handlers if they don't already exist
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    elif not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
         logger.addHandler(file_handler)
    elif not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
         logger.addHandler(console_handler)

    logging.info("日志记录已设置完成。")

# Import os for makedirs, needs to be at the top
import os 