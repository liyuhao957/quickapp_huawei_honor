import re
from typing import Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_time_from_url(url: str) -> Optional[str]:
    """从URL中提取时间信息"""
    try:
        # 华为加载器格式: HW-CC-Date=20250115T085605Z
        hw_match = re.search(r'HW-CC-Date=(\d{8})T(\d{6})Z', url)
        if hw_match:
            date_str, time_str = hw_match.groups()
            formatted_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            logger.info(f"华为加载器时间解析: {formatted_time}")
            return formatted_time
        
        # 荣耀调试器格式: _20250116_144827
        honor_match = re.search(r'_(\d{8})_(\d{6})', url)
        if honor_match:
            date_str, time_str = honor_match.groups()
            formatted_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            logger.info(f"荣耀调试器时间解析: {formatted_time}")
            return formatted_time
        
        logger.warning(f"未能从URL中提取时间: {url}")
        return None
    except Exception as e:
        logger.error(f"解析时间失败: {str(e)}")
        return None

def test_parse_time():
    """测试时间解析函数"""
    test_urls = [
        # 华为加载器URL
        "enter-vali-drcn.dbankcdn.cn/pvt_2/DeveloperAlliance_package_901_9/1e/v3/a7MV677cTmSfPpVLRKzCSA/QuickAPP-newly-product-release-loader-14.5.1.300.apk?HW-CC-KV=V1&HW-CC-Date=20250115T085605Z&HW-CC-Expire=315360000&HW-CC-Sign=C258197E362B9596E1C206",
        
        # 荣耀调试器URL
        "ntentplatform-drcn.hihonorcdn.com/developerPlatform/Debugger_v12.0.10.301/Debugger_v12.0.10.301_phoneDebugger_release_20250116_144827.a",
        
        # 无效URL测试
        "https://example.com/no-time-info",
        "https://example.com/invalid_20250x16_144827",
        ""
    ]
    
    print("\n开始测试时间解析函数...")
    for url in test_urls:
        print(f"\n测试URL: {url[:100]}...")  # 只显示URL的前100个字符
        result = parse_time_from_url(url)
        print(f"解析结果: {result}")

if __name__ == "__main__":
    test_parse_time() 