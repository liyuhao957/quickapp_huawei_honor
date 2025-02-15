import re
import logging
from typing import Optional
from logger_config import setup_module_logger

logger = setup_module_logger('utils')

def parse_time_from_url(url: str) -> Optional[str]:
    """从URL中提取时间信息"""
    try:
        # 华为加载器格式1: HW-CC-Date=20250115T085605Z
        hw_match = re.search(r'HW-CC-Date=(\d{8})T(\d{6})Z', url)
        if hw_match:
            date_str, time_str = hw_match.groups()
            formatted_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            logger.info(f"华为加载器时间解析(格式1): {formatted_time}")
            return formatted_time
        
        # 华为加载器格式2: .20240103092652.
        hw_match2 = re.search(r'\.(\d{8})(\d{6})\.', url)
        if hw_match2:
            date_str, time_str = hw_match2.groups()
            formatted_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            logger.info(f"华为加载器时间解析(格式2): {formatted_time}")
            return formatted_time
        
        # 荣耀调试器格式1: _20250116_144827
        honor_match = re.search(r'_(\d{8})_(\d{6})', url)
        if honor_match:
            date_str, time_str = honor_match.groups()
            formatted_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            logger.info(f"荣耀调试器时间解析(格式1): {formatted_time}")
            return formatted_time
        
        # 荣耀调试器格式2: _20240321024128.apk
        honor_match2 = re.search(r'_(\d{14})\.apk', url)
        if honor_match2:
            timestamp = honor_match2.group(1)
            formatted_time = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}"
            logger.info(f"荣耀调试器时间解析(格式2): {formatted_time}")
            return formatted_time
        
        logger.warning(f"未能从URL中提取时间: {url}")
        return None
    except Exception as e:
        logger.error(f"解析时间失败: {str(e)}")
        return None 