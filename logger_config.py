import os
import logging
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
if not os.path.exists('logs'):
    os.makedirs('logs')

def setup_module_logger(name):
    """为每个模块设置独立的logger"""
    logger = logging.getLogger(name)
    
    # 如果 logger 已经有 handler，直接返回避免重复配置
    if logger.handlers:
        return logger
    
    logger.propagate = False  # 阻止日志传递
    logger.setLevel(logging.INFO)
    
    # 创建处理器
    handler = RotatingFileHandler(
        f'logs/{name}.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=0,       # 不保留备份
        encoding='utf-8'
    )
    
    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(handler)
    return logger 