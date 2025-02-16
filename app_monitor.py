import requests
import time
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import threading
from config import Config  # 直接使用 config.py 中的 Config
from database import VersionDatabase
from logger_config import setup_module_logger
from utils import parse_time_from_url  # 添加这行

class BaseMonitor:
    """监控基类"""
    def __init__(self, name: str):
        self.name = name
        self.webhook_url = Config.WEBHOOK_URLS[name]
        self.logger = setup_module_logger(name)
        self.last_hash = None
        self.last_content = None
        self._stop_flag = threading.Event()
        self._thread = None
        self.timeout = 30
        self.db = VersionDatabase()

    @property
    def check_interval(self):
        """动态获取检查间隔"""
        interval = Config.CHECK_INTERVALS[self.name]
        return interval

    def calculate_hash(self, content: Any) -> str:
        """计算内容哈希值"""
        return hashlib.md5(str(content).encode('utf-8')).hexdigest()

    def send_notification(self, content, is_startup=False):
        """发送通知"""
        try:
            headers = {'Content-Type': 'application/json'}
            msg = self._format_notification(content, is_startup)
            
            response = requests.post(
                self.webhook_url,
                json=msg,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            self.logger.info(f"通知发送成功: {self.name}")
            return True
        except Exception as e:
            self.logger.error(f"发送通知失败: {str(e)}")
            return False

    def compare_versions(self, new_version: str, old_version: str) -> int:
        """比较版本号"""
        try:
            new_ver = new_version.replace('V', '').strip()
            old_ver = old_version.replace('V', '').strip()
            
            new_parts = [int(x) for x in new_ver.split('.')]
            old_parts = [int(x) for x in old_ver.split('.')]
            
            for new, old in zip(new_parts, old_parts):
                if new > old:
                    return 1
                elif new < old:
                    return -1
            
            return len(new_parts) - len(old_parts)
        except Exception as e:
            print(f"版本比较出错: {str(e)}")
            return 0

    def start(self) -> None:
        """启动监控"""
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self.monitor)
        self._thread.start()

    def stop(self) -> None:
        """停止监控"""
        print(f"正在停止监控器: {self.name}")
        self._stop_flag.set()  # 设置停止标志
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)  # 等待最多5秒
            if self._thread.is_alive():
                print(f"监控器 {self.name} 未能在5秒内停止")
            else:
                print(f"监控器 {self.name} 已完全停止")

    def send_error_notification(self, error_msg: str) -> None:
        """发送错误通知"""
        try:
            headers = {'Content-Type': 'application/json'}
            data = {
                "msg_type": "interactive",
                "card": {
                    "config": {"wide_screen_mode": True},
                    "header": {
                        "template": "red",  # 使用红色表示错误
                        "title": {"content": f"{self.name} 监控异常", "tag": "plain_text"}
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": (
                                "❌ **错误详情**\n\n"
                                f"```\n{error_msg}\n```\n\n"
                                f"发生时间：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
                            )
                        }
                    ]
                }
            }
            
            response = requests.post(
                Config.ERROR_WEBHOOK,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            print("错误通知发送成功")
        except Exception as e:
            print(f"发送错误通知失败: {str(e)}")

    def monitor(self) -> None:
        """监控主循环"""
        self.logger.info(f"开始监控: {self.name}, 检查间隔: {self.check_interval}秒")
        
        try:
            # 获取初始内容
            retry_count = 0
            while retry_count < 3 and not self._stop_flag.is_set():
                self.logger.info(f"正在获取初始内容: {self.name}")
                current_content = self.get_latest_version()
                if current_content:
                    # 保存到数据库
                    self.logger.info(f"获取初始内容成功: {self.name}")
                    self.save_to_database(current_content)
                    self.last_content = current_content
                    self.last_hash = self.calculate_hash(current_content)
                    self.send_notification(current_content, is_startup=True)
                    break
                retry_count += 1
                error_msg = f"获取数据失败，重试第{retry_count}次"
                self.logger.warning(error_msg)
                self.send_error_notification(error_msg)
                time.sleep(5)
            
            if retry_count == 3:
                error_msg = "获取数据失败，监控启动失败"
                self.logger.error(error_msg)
                self.send_error_notification(error_msg)
                return
            
            while not self._stop_flag.wait(self.check_interval):
                self.logger.info(f"当前检查间隔: {self.check_interval}秒")
                try:
                    current_content = self.get_latest_version()
                    if current_content:
                        current_hash = self.calculate_hash(current_content)
                        if current_hash != self.last_hash:
                            # 保存到数据库
                            self.save_to_database(current_content)
                            self.send_notification(current_content)
                            self.last_hash = current_hash
                            self.last_content = current_content
                        else:
                            self.logger.info(f"{self.name}: 成功获取内容，但未发现更新")
                    else:
                        error_msg = f"获取数据失败，等待下次重试"
                        self.logger.error(error_msg)
                        self.send_error_notification(error_msg)
                except Exception as e:
                    error_msg = f"监控出错: {str(e)}"
                    self.logger.error(error_msg)
                    self.send_error_notification(error_msg)
                    time.sleep(60)
        
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        finally:
            self.logger.info(f"监控器 {self.name} 已停止")
            self.send_notification("监控服务已停止", is_startup=True)

    def save_to_database(self, content: Dict) -> bool:
        """保存内容到数据库 - 子类必须实现此方法"""
        raise NotImplementedError("子类必须实现此方法")

    def _format_notification(self, content, is_startup=False):
        """格式化荣耀调试器/引擎更新通知"""
        prefix = "🔔 监控服务已启动" if is_startup else "🚨 检测到更新！"
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"content": f"{self.name}更新", "tag": "plain_text"}
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"{prefix}\n\n"
                            "|  类型  |  内容  |\n"
                            "|:------:|:------|\n"
                            f"|  版本号  | `{content['version']}` |\n"
                            f"|  更新时间  | `{content['date']}` |\n\n"
                            "📋 更新内容\n" +
                            "\n".join([f"• {item}" for item in content['updates']['features']])  # 显示所有更新内容
                        )
                    }
                ]
            }
        }

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """运行监控器"""
        try:
            # 获取最新版本
            latest = self.get_latest_version()
            if latest:
                self.send_notification(latest, is_startup=True)
        except Exception as e:
            print(f"运行监控器失败: {str(e)}")

    def is_running(self):
        """检查监控器是否在运行"""
        return not self._stop_flag.is_set()

    def parse_time_from_url(self, url: str) -> Optional[str]:
        """从URL中提取时间信息"""
        return parse_time_from_url(url)  # 使用工具函数

class HuaweiVersionMonitor(BaseMonitor):
    """华为快应用版本监控"""
    def __init__(self):
        super().__init__("huawei_version")
        self.url = "https://developer.huawei.com/consumer/cn/doc/quickApp-Guides/quickapp-version-updates-0000001079803874"

    def get_page_content(self):
        """获取页面内容"""
        try:
            self.logger.info("正在获取页面内容...")
            data = {
                "objectId": "quickapp-version-updates-0000001079803874",
                "version": "",
                "catalogName": "quickApp-Guides",
                "language": "cn"
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://developer.huawei.com',
                'Referer': 'https://developer.huawei.com/'
            }
            
            response = requests.post(
                Config.API_URLS[self.name], 
                json=data, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'value' in data and 'content' in data['value']:
                    return self.parse_content(data['value']['content']['content'])
                else:
                    print(f"API响应格式错误: {data}")
            
            raise ValueError(f"API请求失败: {response.status_code}")
        except requests.Timeout:
            print("请求超时")
        except requests.RequestException as e:
            print(f"请求失败: {str(e)}")
        except ValueError as e:
            print(str(e))
        except Exception as e:
            print(f"获取内容失败: {str(e)}")
        return None

    def parse_content(self, html_content):
        """解析页面内容，返回所有版本信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            version_titles = soup.find_all(['h1', 'h2', 'h3', 'h4'])
            
            versions = []
            current_version = None
            
            for title in version_titles:
                title_text = title.text.strip()
                if '版本更新说明' in title_text and '（' in title_text:
                    # 如果已有版本信息，保存它
                    if current_version:
                        versions.append(current_version)
                    
                    # 开始新的版本信息
                    version_number = title_text.split('版本更新说明')[0].strip()
                    version_date = title_text[title_text.find('（')+1:title_text.find('）')]
                    
                    current_version = {
                        'version': version_number,
                        'date': version_date,
                        'updates': {
                            'components': [],
                            'interfaces': []
                        }
                    }
                    
                    # 找到下一个版本标题
                    next_version = title.find_next('h4', string=lambda x: x and '版本更新说明' in x and '[h2]' not in x)
                    
                    # 查找当前版本的内容
                    current = title
                    current_type = None
                    
                    while current and current != next_version:
                        if current.name == 'h4':
                            text = current.text.strip()
                            if '框架' in text:
                                current_type = 'framework'
                                if 'framework' not in current_version['updates']:
                                    current_version['updates']['framework'] = []
                            elif '组件' in text:
                                current_type = 'components'
                            elif '接口' in text:
                                current_type = 'interfaces'
                        elif current.name == 'table' and current_type:
                            # 解析表格内容
                            rows = current.find_all('tr')[1:]  # 跳过表头
                            for row in rows:
                                cols = row.find_all('td')
                                if len(cols) >= 2:
                                    name = cols[0].text.strip()
                                    description_cell = cols[1]
                                    
                                    descriptions = []
                                    for text in description_cell.stripped_strings:
                                        if text.strip():
                                            descriptions.append(text.strip())
                                    
                                    doc_link = description_cell.find('a')
                                    update_info = {
                                        'name': name,
                                        'description': descriptions[0] if descriptions else "",
                                        'doc_link': {
                                            'text': doc_link.text.strip() if doc_link else "",
                                            'url': "https://developer.huawei.com/consumer/cn/doc/" + doc_link.get('href', '').replace('https://developer.huawei.com/consumer/cn/doc/', '') if doc_link else ""
                                        } if doc_link else None
                                    }
                                    current_version['updates'][current_type].append(update_info)
                        
                        current = current.find_next()
            
            # 添加最后一个版本
            if current_version:
                versions.append(current_version)
            
            return versions
            
        except Exception as e:
            self.logger.error(f"解析内容失败: {str(e)}")
            self.send_error_notification(f"解析内容失败: {str(e)}")  # 发送错误通知
            return None

    def get_latest_version(self):
        """获取最新版本信息"""
        versions = self.get_page_content()
        return versions[0] if versions else None

    def get_all_versions(self):
        """获取所有版本信息"""
        return self.get_page_content()

    def _format_notification(self, content, is_startup=False):
        """格式化通知消息"""
        prefix = "🔔 监控服务已启动" if is_startup else "🚨 检测到版本更新！"
        
        # 格式化更新内容
        updates = []
        # 添加框架更新部分
        if content['updates'].get('framework'):
            updates.append("【框架更新】")
            for item in content['updates']['framework']:
                update_text = f"• {item['name']}: {item['description']}"
                if item['doc_link']:
                    update_text += f"\n  📖 [{item['doc_link']['text']}]({item['doc_link']['url']})"
                updates.append(update_text)
        
        if content['updates']['components']:
            updates.append("【组件更新】")
            for item in content['updates']['components']:
                update_text = f"• {item['name']}: {item['description']}"
                if item['doc_link']:
                    update_text += f"\n  📖 [{item['doc_link']['text']}]({item['doc_link']['url']})"
                updates.append(update_text)
        
        if content['updates']['interfaces']:
            updates.append("\n【接口更新】")
            for item in content['updates']['interfaces']:
                update_text = f"• {item['name']}: {item['description']}"
                if item['doc_link']:
                    update_text += f"\n  📖 [{item['doc_link']['text']}]({item['doc_link']['url']})"
                updates.append(update_text)
        
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"content": "华为快应用版本更新", "tag": "plain_text"}
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"{prefix}\n\n" +
                                 f"版本号: `{content['version']}`\n" +
                                 f"更新日期: `{content['date']}`\n\n" +
                                 "\n".join(updates)
                    }
                ]
            }
        }

    def save_to_database(self, content: Dict) -> bool:
        """保存华为版本更新到数据库"""
        return self.db.save_huawei_version(content)

class HonorDebuggerMonitor(BaseMonitor):
    """荣耀调试器监控"""
    def __init__(self):
        super().__init__("honor_debugger")
        self.api_url = Config.API_URLS['honor']

    def get_page_content(self):
        """获取页面内容"""
        try:
            self.logger.info("正在获取页面内容...")
            params = {
                "platformNo": "10001",
                "lang": "cn"
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://developer.honor.com',
                'Referer': 'https://developer.honor.com/cn/doc/guides/101380'
            }
            
            response = requests.get(self.api_url, params=params, headers=headers)
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200':
                    html_content = data.get('data', {}).get('documentInfo', {}).get('text', '')
                    return self.parse_debugger_info(BeautifulSoup(html_content, 'html.parser'))
            
            raise ValueError(f"API请求失败: {response.status_code}")
        except Exception as e:
            print(f"获取内容失败: {str(e)}")
            return None

    def parse_debugger_info(self, soup):
        """解析调试器信息，返回所有版本信息"""
        try:
            debugger_section = soup.find('h1', id=lambda x: x and 'h1-1717124946965' in x)
            if not debugger_section:
                raise ValueError("未找到调试器下载部分")

            table = debugger_section.find_next('table')
            if not table:
                raise ValueError("未找到调试器下载表格")

            rows = table.find_all('tr')[1:]  # 跳过表头
            versions = []

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    debugger_info = {
                        "快应用引擎版本号": cols[0].get_text().strip(),
                        "荣耀引擎版本号": cols[1].get_text().strip(),
                        "快应用联盟平台版本号": cols[2].get_text().strip(),
                        "下载地址": cols[3].find('a')['href'] if cols[3].find('a') else "",
                        "调试器版本号": cols[4].get_text().strip(),
                        "功能": [item.strip() for item in cols[5].get_text().split('\n') if item.strip()]
                    }
                    versions.append(debugger_info)

            # 修改排序逻辑：按荣耀引擎版本号排序
            versions.sort(key=lambda x: int(x['荣耀引擎版本号']), reverse=True)
            return versions

        except Exception as e:
            print(f"解析调试器信息失败: {str(e)}")
            return None

    def get_latest_version(self):
        """获取最新版本信息"""
        versions = self.get_page_content()
        return versions[0] if versions else None

    def get_all_versions(self):
        """获取所有版本信息"""
        return self.get_page_content()

    def _format_notification(self, content, is_startup=False):
        """格式化荣耀调试器更新通知"""
        prefix = "🔔 监控服务已启动" if is_startup else "🚨 检测到调试器更新！"
        release_time = self.parse_time_from_url(content.get('下载地址', '')) or '未知'
        
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "orange",  # 修改为橙色
                    "title": {"content": "荣耀快应用调试器更新", "tag": "plain_text"}
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"{prefix}\n\n"
                            "|  类型  |  内容  |\n"
                            "|:------:|:------|\n"
                            f"|  调试器版本  | `{content['调试器版本号']}` |\n"
                            f"|  引擎版本  | `{content['荣耀引擎版本号']}` |\n"
                            f"|  联盟版本  | `{content['快应用联盟平台版本号']}` |\n"
                            f"|  发布时间  | `{release_time}` |\n"
                            f"|  下载地址  | [点击下载]({content.get('下载地址', '暂无')}) |"
                        )
                    }
                ]
            }
        }

    def save_to_database(self, content: Dict) -> bool:
        """保存荣耀调试器信息到数据库"""
        return self.db.save_honor_debugger(content)

class HonorEngineMonitor(BaseMonitor):
    """荣耀引擎监控"""
    def __init__(self):
        super().__init__("honor_engine")
        self.api_url = Config.API_URLS['honor']

    def clean_feature_text(self, text):
        """清理功能文本，去掉所有bullet point和格式化前缀"""
        text = text.strip()
        
        # 去掉所有bullet point符号
        text = text.replace('●  ', '')
        text = text.replace('● ', '')
        text = text.replace('●', '')  # 直接去掉●
        text = text.replace('•  ', '')
        text = text.replace('• ', '')
        text = text.replace('•', '')  # 直接去掉•
        text = text.replace('：', ':')
        text = text.strip()  # 再次去掉可能的空格
        
        # 确保以正确的前缀开头
        if not any(text.startswith(prefix) for prefix in ['新增:', '优化:', '废弃:']):
            if text.startswith('优化'):
                text = '优化:' + text[2:]
            elif text.startswith('新增'):
                text = '新增:' + text[2:]
            elif text.startswith('废弃'):
                text = '废弃:' + text[2:]
        
        return text

    def parse_engine_info(self, soup):
        """解析引擎版本信息，返回所有版本信息"""
        try:
            versions = []
            # 找到"快应用引擎版本更新日志"标题
            update_log_title = soup.find('h1', string=lambda x: x and '快应用引擎版本更新日志' in x)
            if not update_log_title:
                raise ValueError("未找到版本更新日志部分")
            
            # 从标题开始解析后续内容
            current = update_log_title
            while current:
                current = current.find_next()
                if not current:
                    break
                
                # 如果是版本号链接
                if current.name == 'a' and current.get('href', '').endswith('.apk'):
                    version_text = current.get_text(strip=True)
                    if not version_text.startswith('V'):
                        continue
                    
                    # 收集这个版本的信息
                    version_info = {
                        "版本号": version_text,
                        "上线时间": "",
                        "下载地址": current.get('href', ''),
                        "引擎版本": {},
                        "功能": []
                    }
                    
                    # 查找版本信息
                    next_element = current
                    release_date = ''
                    while next_element:
                        next_element = next_element.find_next()
                        
                        # 如果遇到下一个版本号，停止
                        if next_element and next_element.name == 'a' and next_element.get('href', '').endswith('.apk'):
                            break
                        
                        # 获取上线时间 - 支持多种格式
                        if next_element and next_element.name in ['p', 'div', 'span']:
                            text = next_element.get_text(strip=True)
                            # 新增: 使用正则表达式匹配日期格式
                            date_pattern = r'(?:上线时间\s*)?(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
                            date_match = re.search(date_pattern, text)
                            
                            if date_match:
                                release_date = date_match.group(1)
                            # 保留原有的日期检查逻辑作为备选
                            elif text.startswith('20') and len(text) >= 8:
                                release_date = text
                            elif '上线时间' in text:
                                date_element = next_element.find_next(['p', 'div', 'span'])
                                if date_element:
                                    date_text = date_element.get_text(strip=True)
                                    date_match = re.search(date_pattern, date_text)
                                    if date_match:
                                        release_date = date_match.group(1)
                                    elif date_text.startswith('20') and len(date_text) >= 8:
                                        release_date = date_text
                        
                        # 获取引擎版本
                        if next_element and next_element.name == 'td' and '荣耀快应用引擎平台' in next_element.get_text():
                            version_td = next_element.find_next('td')
                            if version_td:
                                version_info["引擎版本"]['荣耀快应用引擎平台'] = version_td.get_text(strip=True)
                        elif next_element and next_element.name == 'td' and '快应用联盟平台' in next_element.get_text():
                            version_td = next_element.find_next('td')
                            if version_td:
                                version_info["引擎版本"]['快应用联盟平台'] = version_td.get_text(strip=True)
                        
                        # 获取功能列表
                        if next_element and next_element.name in ['p', 'li', 'h2']:
                            text = next_element.get_text(strip=True)
                            if text and any(text.startswith(prefix) for prefix in ['新增', '优化', '废弃', '●', '•']):
                                text = self.clean_feature_text(text)
                                if text and text not in version_info["功能"]:
                                    version_info["功能"].append(text)
                    
                    # 过滤掉非日期格式的值
                    if release_date in ['模板', '']:
                        # 再次尝试查找日期
                        date_divs = soup.find_all('div', string=lambda x: x and x.strip().startswith('20'))
                        for div in date_divs:
                            date_text = div.get_text(strip=True)
                            if date_text.startswith('20') and len(date_text) >= 8:
                                release_date = date_text
                                break
                    
                    version_info["上线时间"] = release_date
                    
                    # 只保存有功能的版本
                    if version_info["功能"]:
                        versions.append(version_info)
            
            # 按版本号排序
            versions.sort(key=lambda x: [int(i) for i in x['版本号'].replace('V', '').split('.')], reverse=True)
            return versions
            
        except Exception as e:
            print(f"解析引擎版本信息失败: {str(e)}")
            return None

    def get_latest_version(self):
        """获取最新版本信息"""
        versions = self.get_page_content()
        return versions[0] if versions else None

    def get_all_versions(self):
        """获取所有版本信息"""
        return self.get_page_content()

    def _format_notification(self, content, is_startup=False):
        """格式化荣耀引擎更新通知"""
        prefix = "🔔 监控服务已启动" if is_startup else "🚨 检测到引擎版本更新！"
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "orange",  # 修改为橙色
                    "title": {"content": "荣耀快应用引擎更新", "tag": "plain_text"}
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"{prefix}\n\n"
                            "|  类型  |  内容  |\n"
                            "|:------:|:------|\n"
                            f"|  版本号  | `{content['版本号']}` |\n"
                            f"|  上线时间  | `{content['上线时间']}` |\n"
                            f"|  荣耀版本  | `{content['引擎版本'].get('荣耀快应用引擎平台', '')}` |\n"
                            f"|  联盟版本  | `{content['引擎版本'].get('快应用联盟平台', '')}` |\n\n"
                            "📋 更新内容\n" +
                            "\n".join([f"• {item}" for item in content['功能']]) +
                            f"\n\n📥 [下载地址]({content.get('下载地址', '暂无')})"
                        )
                    }
                ]
            }
        }

    def save_to_database(self, content: Dict) -> bool:
        """保存荣耀引擎信息到数据库"""
        try:
            # 确保所有必要字段都存在
            required_fields = ['版本号', '上线时间', '下载地址', '引擎版本', '功能']
            missing_fields = [f for f in required_fields if f not in content]
            if missing_fields:
                print(f"缺少必要字段: {missing_fields}")
                return False
            
            # 处理空值
            if not content['上线时间']:
                content['上线时间'] = datetime.now().strftime('%Y-%m-%d')
            if not content['功能']:
                content['功能'] = []
            if not content['引擎版本']:
                content['引擎版本'] = {
                    '荣耀快应用引擎平台': '',
                    '快应用联盟平台': ''
                }
            
            # 验证版本号格式
            if not re.match(r'^V?\d+\.\d+\.\d+\.\d+$', content['版本号']):
                print(f"版本号格式错误: {content['版本号']}")
                return False
            
            # 确保版本号格式统一
            if not content['版本号'].startswith('V'):
                content['版本号'] = 'V' + content['版本号']
            
            return self.db.save_honor_engine(content)
            
        except Exception as e:
            print(f"保存荣耀引擎信息失败: {str(e)}")
            return False

    def get_page_content(self):
        """获取页面内容"""
        try:
            self.logger.info("正在获取页面内容...")
            params = {
                "platformNo": "10001",
                "lang": "cn"
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://developer.honor.com',
                'Referer': 'https://developer.honor.com/cn/doc/guides/101380'
            }
            
            response = requests.get(self.api_url, params=params, headers=headers)
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '200':
                    html_content = data.get('data', {}).get('documentInfo', {}).get('text', '')
                    return self.parse_engine_info(BeautifulSoup(html_content, 'html.parser'))
            
            raise ValueError(f"API请求失败: {response.status_code}")
        except Exception as e:
            print(f"获取内容失败: {str(e)}")
            return None

    def monitor(self) -> None:
        """监控主循环"""
        self.logger.info(f"开始监控: {self.name}, 检查间隔: {self.check_interval}秒")
        
        try:
            # 获取初始内容
            retry_count = 0
            while retry_count < 3 and not self._stop_flag.is_set():
                self.logger.info(f"正在获取初始内容: {self.name}")
                current_content = self.get_latest_version()
                if current_content:
                    # 保存到数据库
                    self.logger.info(f"获取初始内容成功: {self.name}")
                    self.save_to_database(current_content)
                    self.last_content = current_content
                    self.last_hash = self.calculate_hash(current_content)
                    self.send_notification(current_content, is_startup=True)
                    break
                retry_count += 1
                error_msg = f"获取数据失败，重试第{retry_count}次"
                self.logger.warning(error_msg)
                time.sleep(5)
            
            if retry_count == 3:
                error_msg = "获取数据失败，监控启动失败"
                self.logger.error(error_msg)
                return
            
            while not self._stop_flag.wait(self.check_interval):
                self.logger.info(f"当前检查间隔: {self.check_interval}秒")
                try:
                    current_content = self.get_latest_version()
                    if current_content:
                        # 判断版本号和下载链接
                        if self.last_content:
                            if current_content['版本号'] == self.last_content['版本号']:
                                if current_content['下载地址'] == self.last_content['下载地址']:
                                    self.logger.info(f"{self.name}: 成功获取内容，但未发现更新")
                                    continue
                                else:
                                    self.logger.info(f"检测到下载链接变化 - 版本: {current_content['版本号']}")
                            else:
                                self.logger.info(f"检测到新版本: {current_content['版本号']}")
                        
                        # 保存到数据库并发送通知
                        self.save_to_database(current_content)
                        self.send_notification(current_content)
                        self.last_content = current_content
                        self.last_hash = self.calculate_hash(current_content)
                    else:
                        error_msg = f"获取数据失败，等待下次重试"
                        self.logger.error(error_msg)
                except Exception as e:
                    error_msg = f"监控出错: {str(e)}"
                    self.logger.error(error_msg)
                    time.sleep(60)
        
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        finally:
            self.logger.info(f"监控器 {self.name} 已停止")

class HuaweiLoaderMonitor(BaseMonitor):
    """华为加载器监控"""
    def __init__(self):
        super().__init__("huawei_loader")
        self.url = "https://developer.huawei.com/consumer/cn/doc/Tools-Library/quickapp-ide-download-0000001101172926"

    def get_page_content(self):
        """获取页面内容"""
        try:
            self.logger.info("正在获取页面内容...")
            data = {
                "objectId": "quickapp-ide-download-0000001101172926",
                "version": "",
                "catalogName": "Tools-Library",
                "language": "cn"
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://developer.huawei.com',
                'Referer': 'https://developer.huawei.com/'
            }
            
            response = requests.post(
                Config.API_URLS[self.name], 
                json=data, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 0 and 'value' in data and 'content' in data['value']:
                    html_content = data['value']['content']['content']
                    return self.parse_content(BeautifulSoup(html_content, 'html.parser'))
            
            raise ValueError(f"API请求失败: {response.status_code}")
        except requests.Timeout:
            print("请求超时")
        except requests.RequestException as e:
            print(f"请求失败: {str(e)}")
        except ValueError as e:
            print(str(e))
        except Exception as e:
            print(f"获取内容失败: {str(e)}")
        return None

    def parse_content(self, soup):
        """解析页面内容，返回所有版本信息"""
        try:
            # 查找手机加载器部分
            phone_loader_section = soup.find('div', id='section9347192715112')
            if not phone_loader_section:
                raise ValueError("未找到手机加载器部分")

            # 查找所有加载器链接
            all_links = phone_loader_section.find_all('a')
            
            # 筛选手机加载器的链接
            phone_links = []
            for link in all_links:
                text = link.get_text().strip()
                if text.startswith('HwQuickApp_Loader_Phone'):
                    phone_links.append(link)
            
            # 收集所有版本信息
            versions = []
            for link in phone_links:
                text = link.get_text().strip()
                href = link.get('href')
                version = None
                spec = None
                
                parent = link.find_parent('td') or link.parent
                if parent:
                    row = parent.find_parent('tr')
                    row_text = row.get_text() if row else parent.get_text()
                    
                    version_match = re.search(r'V?(\d+\.\d+\.\d+\.\d+)', text)
                    spec_match = re.search(r'支持(\d{4})规范|（支持(\d{4})规范）', row_text)
                    
                    if version_match:
                        version = version_match.group(1)
                    if spec_match:
                        spec = spec_match.group(1) or spec_match.group(2)
                    
                    if version and spec:
                        versions.append({
                            'text': text,
                            'url': href,
                            'version': version,
                            'spec': spec
                        })
            
            if versions:
                # 按版本号排序
                versions.sort(key=lambda x: [int(i) for i in x['version'].split('.')], reverse=True)
                return versions
            
            raise ValueError("未找到有效的版本信息")
        except Exception as e:
            print(f"解析内容失败: {str(e)}")
            return None

    def get_latest_version(self):
        """获取最新版本信息"""
        versions = self.get_page_content()
        return versions[0] if versions else None

    def get_all_versions(self):
        """获取所有版本信息"""
        return self.get_page_content()

    def _format_notification(self, content, is_startup=False):
        """格式化华为加载器更新通知"""
        prefix = "🔔 监控服务已启动" if is_startup else "🚨 检测到加载器更新！"
        release_time = self.parse_time_from_url(content.get('url', '')) or '未知'
        
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"content": "华为快应用加载器更新", "tag": "plain_text"}
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": (
                            f"{prefix}\n\n"
                            "|  类型  |  内容  |\n"
                            "|:------:|:------|\n"
                            f"|  版本号  | `{content['version']}` |\n"
                            f"|  规范版本  | `{content['spec']}` |\n"
                            f"|  发布时间  | `{release_time}` |\n"
                            f"|  下载地址  | [点击下载]({content.get('url', '暂无')}) |"
                        )
                    }
                ]
            }
        }

    def save_to_database(self, content: Dict) -> bool:
        """保存华为加载器信息到数据库"""
        return self.db.save_huawei_loader(content)

class MonitorManager:
    """监控管理器"""
    def __init__(self):
        self.monitors = {}
        self._init_monitors()
        self._start_time = datetime.now()  # 记录启动时间
        self._last_heartbeat = datetime.now()  # 初始化最后心跳时间
        
    def _init_monitors(self):
        self.monitors = {
            'huawei_version': HuaweiVersionMonitor(),
            'honor_debugger': HonorDebuggerMonitor(),
            'honor_engine': HonorEngineMonitor(),
            'huawei_loader': HuaweiLoaderMonitor()
        }
        print(f"当前配置的检查间隔: {Config.CHECK_INTERVALS}")
        
    def _send_startup_heartbeat(self):
        """发送启动通知"""
        try:
            # 创建监控项目名称映射
            monitor_names = {
                'huawei_loader': '华为加载器',
                'huawei_version': '华为版本更新说明',
                'honor_debugger': '荣耀调试器',
                'honor_engine': '荣耀引擎'
            }
            
            # 获取中文名称列表
            chinese_names = [monitor_names[key] for key in self.monitors.keys()]
            
            message = {
                "msg_type": "interactive",
                "card": {
                    "config": {"wide_screen_mode": True},
                    "header": {
                        "template": "blue",
                        "title": {"content": "监控服务启动", "tag": "plain_text"}
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": (
                                "🚀 **服务已成功启动**\n\n"
                                f"启动时间：`{self._start_time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                                f"监控项目：`{'、'.join(chinese_names)}`\n"
                                f"检查间隔：`{Config.CHECK_INTERVALS['huawei_version']}秒`"
                            )
                        }
                    ]
                }
            }
            requests.post(Config.HEARTBEAT_WEBHOOK, json=message, timeout=30)
            print("启动通知发送成功")
        except Exception as e:
            print(f"发送启动通知失败: {str(e)}")

    def send_heartbeat(self):
        """发送心跳通知"""
        try:
            now = datetime.now()
            # 只在 0:00 发送一次心跳
            if now.hour == 0 and now.minute == 0:
                # 检查是否已经发送过
                if self._last_heartbeat and self._last_heartbeat.date() == now.date():
                    return  # 今天已经发送过，直接返回
                
                # 使用启动时间计算运行时长
                runtime = now - self._start_time
                days = runtime.days
                hours, remainder = divmod(runtime.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                message = {
                    "msg_type": "interactive",
                    "card": {
                        "config": {"wide_screen_mode": True},
                        "header": {
                            "template": "green",  # 使用绿色表示正常
                            "title": {"content": "监控服务心跳", "tag": "plain_text"}
                        },
                        "elements": [
                            {
                                "tag": "markdown",
                                "content": (
                                    "💗 **服务状态：运行正常**\n\n"
                                    f"运行时长：`{days}天{hours}小时{minutes}分钟`\n"
                                    f"检测时间：`{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                                    f"启动时间：`{self._start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
                                )
                            }
                        ]
                    }
                }
                
                requests.post(Config.HEARTBEAT_WEBHOOK, json=message, timeout=30)
                self._last_heartbeat = now
        except Exception as e:
            print(f"发送心跳通知失败: {str(e)}")

    def start_all(self):
        """启动所有监控器"""
        print("正在启动所有监控器...")
        for name, monitor in self.monitors.items():
            try:
                monitor.start()
                print(f"已启动监控器: {name}")
            except Exception as e:
                print(f"启动监控器失败 {name}: {str(e)}")
        
        # 发送启动通知
        self._send_startup_heartbeat()

    def stop_all(self):
        """停止所有监控器"""
        print("正在停止所有监控器...")
        
        # 首先设置所有监控器的停止标志
        for name, monitor in self.monitors.items():
            try:
                monitor.stop()  # 使用 BaseMonitor 的 stop 方法
                if monitor._thread and monitor._thread.is_alive():
                    print(f"监控器 {name} 仍在运行")
                else:
                    print(f"监控器 {name} 已完全停止")
            except Exception as e:
                print(f"停止监控器失败 {name}: {str(e)}")

        # 清理资源
        for monitor in self.monitors.values():
            monitor.cleanup()

        print("所有监控器停止操作完成")

    def cleanup(self):
        """清理资源"""
        for monitor in self.monitors.values():
            monitor.cleanup()

def should_init_history():
    """检查是否需要初始化历史数据"""
    try:
        db = VersionDatabase()
        # 检查数据库是否有数据
        versions = db.get_latest_versions()
        return len(versions) == 0  # 如果没有数据，返回True
    finally:
        db.close()

def test_history():
    """测试历史版本获取功能"""
    print("开始测试历史版本获取...")
    
    monitors = {
        'huawei_version': HuaweiVersionMonitor(),
        'honor_debugger': HonorDebuggerMonitor(),
        'honor_engine': HonorEngineMonitor(),
        'huawei_loader': HuaweiLoaderMonitor()
    }
    
    for name, monitor in monitors.items():
        print(f"\n开始测试 {name}...")
        try:
            versions = monitor.get_all_versions()
            if versions:
                print(f"✅ 成功获取 {len(versions)} 个版本")
                # 保存所有版本到数据库
                for version in versions:
                    if monitor.save_to_database(version):
                        print(f"✅ 版本 {version.get('version', '')} 保存成功")
                    else:
                        print(f"❌ 版本 {version.get('version', '')} 保存失败")
            else:
                print(f"❌ 获取版本失败")
        except Exception as e:
            print(f"❌ 测试出错: {str(e)}")
        finally:
            monitor.cleanup()

def main():
    """主函数"""
    manager = None
    try:
        # 创建监控管理器
        manager = MonitorManager()
        
        # 启动所有监控器
        manager.start_all()
        
        while True:
            time.sleep(60)  # 每分钟检查一次
            manager.send_heartbeat()  # 检查是否需要发送心跳
            
    except KeyboardInterrupt:
        print("\n收到停止信号，正在停止所有监控器...")
    finally:
        if manager:
            manager.stop_all()
            manager.cleanup()
            print("监控服务已停止")

if __name__ == "__main__":
    try:
        # 检查是否需要初始化历史数据
        if should_init_history():
            print("数据库为空，开始获取历史版本...")
            test_history()
        
        # 只调用一次 main()
        main()
    except Exception as e:
        print(f"程序运行出错: {str(e)}") 