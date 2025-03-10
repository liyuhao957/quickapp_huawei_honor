import sqlite3
import json
from logger_config import setup_module_logger
from datetime import datetime
from typing import Dict, List, Any, Optional
import re
import threading
from utils import parse_time_from_url

logger = setup_module_logger('database')

class VersionDatabase:
    """版本数据库管理类"""
    def __init__(self, db_file: str = 'versions.db'):
        self.db_file = db_file
        self.logger = logger
        self._init_database()
        # 使用线程本地存储
        self._local = threading.local()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # 华为版本更新表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS huawei_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version TEXT NOT NULL,
                        release_date TEXT NOT NULL,
                        components TEXT NOT NULL,     -- JSON 格式的组件更新
                        interfaces TEXT NOT NULL,     -- JSON 格式的接口更新
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(version)
                    )
                ''')
                
                # 荣耀调试器表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS honor_debugger_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        engine_version TEXT NOT NULL,  -- 快应用引擎版本号
                        honor_version TEXT NOT NULL,   -- 荣耀引擎版本号
                        union_version TEXT NOT NULL,   -- 联盟平台版本号
                        debugger_version TEXT NOT NULL,-- 调试器版本号
                        download_url TEXT NOT NULL,
                        features TEXT NOT NULL,        -- JSON 格式的功能列表
                        release_time TEXT,             -- 新增：发布时间
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(debugger_version)
                    )
                ''')
                
                # 荣耀引擎表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS honor_engine_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version TEXT NOT NULL,         -- 版本号
                        release_date TEXT NOT NULL,    -- 发布日期
                        honor_version TEXT,            -- 荣耀引擎版本号
                        union_version TEXT,            -- 联盟平台版本号
                        download_url TEXT NOT NULL,    -- 下载地址
                        features TEXT NOT NULL,        -- JSON 格式的功能列表
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(version)
                    )
                ''')
                
                # 华为加载器表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS huawei_loader_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version TEXT NOT NULL,         -- 页面显示的版本号
                        actual_version TEXT,           -- 新增：实际下载文件的版本号
                        spec TEXT NOT NULL,            -- 规范版本
                        file_name TEXT NOT NULL,       -- 文件名
                        download_url TEXT NOT NULL,    -- 下载地址
                        release_time TEXT,             -- 发布时间
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                self.logger.info("数据库表初始化完成")
                
        except Exception as e:
            self.logger.error(f"初始化数据库失败: {str(e)}")
            raise 

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_file)
        return self._local.connection
    
    def _validate_data(self, data: Dict, required_fields: List[str]) -> bool:
        """验证数据完整性"""
        return all(field in data and data[field] for field in required_fields)
    
    def save_huawei_version(self, version_data: Dict) -> bool:
        """保存华为版本更新信息"""
        required_fields = ['version', 'date', 'updates']
        try:
            if not self._validate_data(version_data, required_fields):
                raise ValueError("缺少必要字段")
            
            # 修改验证逻辑,检查是否有任何更新内容
            if not any([
                version_data['updates'].get('framework'),
                version_data['updates'].get('components'),
                version_data['updates'].get('interfaces')
            ]):
                raise ValueError("更新内容为空")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                # 只保存实际存在的更新内容
                updates = {}
                if version_data['updates'].get('framework'):
                    updates['framework'] = version_data['updates']['framework']
                if version_data['updates'].get('components'):
                    updates['components'] = version_data['updates']['components']
                if version_data['updates'].get('interfaces'):
                    updates['interfaces'] = version_data['updates']['interfaces']

                cursor.execute('''
                    INSERT OR REPLACE INTO huawei_versions 
                    (version, release_date, components, interfaces) 
                    VALUES (?, ?, ?, ?)
                ''', (
                    version_data['version'],
                    version_data['date'],
                    json.dumps(updates, ensure_ascii=False),  # 只保存有内容的更新
                    '[]'  # interfaces 字段保持为空数组
                ))
                conn.commit()
                self.logger.info(f"保存华为版本更新成功: {version_data['version']}")
                return True
            except Exception:
                conn.rollback()
                raise
        except Exception as e:
            self.logger.error(f"保存华为版本更新失败: {str(e)}")
            return False

    def save_honor_debugger(self, debugger_data: Dict) -> bool:
        """保存荣耀调试器信息"""
        required_fields = ['快应用引擎版本号', '荣耀引擎版本号', '快应用联盟平台版本号', 
                          '调试器版本号', '下载地址', '功能']
        try:
            if not self._validate_data(debugger_data, required_fields):
                raise ValueError("缺少必要字段")
            
            if not debugger_data['功能']:
                raise ValueError("功能列表为空")
            
            # 解析发布时间
            release_time = parse_time_from_url(debugger_data['下载地址'])
            
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO honor_debugger_versions 
                    (engine_version, honor_version, union_version, debugger_version, 
                     download_url, features, release_time) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    debugger_data['快应用引擎版本号'],
                    debugger_data['荣耀引擎版本号'],
                    debugger_data['快应用联盟平台版本号'],
                    debugger_data['调试器版本号'],
                    debugger_data['下载地址'],
                    json.dumps(debugger_data['功能'], ensure_ascii=False),
                    release_time
                ))
                conn.commit()
                self.logger.info(f"保存荣耀调试器信息成功: {debugger_data['调试器版本号']}")
                return True
            except Exception:
                conn.rollback()
                raise
        except Exception as e:
            self.logger.error(f"保存荣耀调试器信息失败: {str(e)}")
            return False

    def save_honor_engine(self, content: Dict) -> bool:
        """保存荣耀引擎信息到数据库"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # 检查版本是否已存在
                cursor.execute(
                    'SELECT id FROM honor_engine_versions WHERE version = ?',
                    (content['版本号'],)
                )
                
                # 准备数据
                data = (
                    content['版本号'],
                    content['上线时间'],
                    content.get('引擎版本', {}).get('荣耀快应用引擎平台', ''),
                    content.get('引擎版本', {}).get('快应用联盟平台', ''),
                    content['下载地址'],
                    json.dumps(content['功能'], ensure_ascii=False)
                )
                
                if cursor.fetchone():
                    # 更新现有记录
                    cursor.execute('''
                        UPDATE honor_engine_versions 
                        SET release_date = ?, 
                            honor_version = ?,
                            union_version = ?,
                            download_url = ?,
                            features = ?
                        WHERE version = ?
                    ''', data[1:] + (data[0],))
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO honor_engine_versions 
                        (version, release_date, honor_version, union_version, download_url, features)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', data)
                
                conn.commit()
                self.logger.info(f"保存荣耀引擎信息成功: {content['版本号']}")
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"保存荣耀引擎信息失败: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"数据库连接失败: {str(e)}")
            return False

    def save_huawei_loader(self, loader_data: Dict) -> bool:
        """保存华为加载器信息"""
        required_fields = ['version', 'actual_version', 'spec', 'text', 'url']
        try:
            if not self._validate_data(loader_data, required_fields):
                raise ValueError("缺少必要字段")
            
            if not loader_data['url'].startswith('http'):
                raise ValueError("下载地址格式错误")
            
            # 修改版本号格式验证
            version = loader_data['version'].replace('V', '')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                raise ValueError("版本号格式错误")
            
            # 解析发布时间
            release_time = parse_time_from_url(loader_data['url'])
            
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                # 检查是否已存在相同版本
                cursor.execute('''
                    SELECT id FROM huawei_loader_versions 
                    WHERE version = ? AND actual_version = ?
                ''', (loader_data['version'], loader_data['actual_version']))
                
                if not cursor.fetchone():
                    # 只有当完全相同的记录不存在时才插入
                    cursor.execute('''
                        INSERT INTO huawei_loader_versions 
                        (version, actual_version, spec, file_name, download_url, release_time) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        loader_data['version'],
                        loader_data['actual_version'],
                        loader_data['spec'],
                        loader_data['text'],
                        loader_data['url'],
                        release_time
                    ))
                    conn.commit()
                    self.logger.info(f"保存华为加载器信息成功: {loader_data['version']} (实际版本: {loader_data['actual_version']})")
                    return True
                else:
                    self.logger.info(f"版本已存在，跳过保存: {loader_data['version']} (实际版本: {loader_data['actual_version']})")
                    return True
                
            except Exception:
                conn.rollback()
                raise
        except Exception as e:
            self.logger.error(f"保存华为加载器信息失败: {str(e)}")
            return False

    # 修改获取最新版本的查询
    def get_latest_versions(self) -> Dict:
        """获取所有监控项的最新版本信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            latest_versions = {}
            
            # 华为版本更新 - 使用 release_date
            cursor.execute('SELECT version, release_date, components, interfaces FROM huawei_versions')
            rows = cursor.fetchall()
            if rows:
                sorted_rows = sorted(rows, 
                                   key=lambda x: self._version_to_tuple(x[0]), 
                                   reverse=True)
                latest_versions['huawei_version'] = {
                    'name': '华为版本说明',
                    'version': sorted_rows[0][0],
                    'date': sorted_rows[0][1],  # release_date
                    'updates': json.loads(sorted_rows[0][2])
                }
            
            # 荣耀调试器 - 修改为使用 release_time
            cursor.execute('''
                SELECT engine_version, honor_version, union_version, debugger_version, 
                       download_url, features, release_time 
                FROM honor_debugger_versions
            ''')
            rows = cursor.fetchall()
            if rows:
                sorted_rows = sorted(rows, key=lambda x: self._version_to_tuple(x[3]), reverse=True)
                latest_versions['honor_debugger'] = {
                    'name': '荣耀调试器',
                    'version': sorted_rows[0][3],
                    'date': sorted_rows[0][6],  # release_time
                    'updates': {
                        'features': json.loads(sorted_rows[0][5])
                    }
                }
            
            # 荣耀引擎 - 使用 release_date
            cursor.execute('SELECT version, release_date, honor_version, union_version, download_url, features FROM honor_engine_versions')
            rows = cursor.fetchall()
            if rows:
                sorted_rows = sorted(rows,
                                   key=lambda x: self._version_to_tuple(x[0]),
                                   reverse=True)
                latest_versions['honor_engine'] = {
                    'name': '荣耀引擎版本',
                    'version': sorted_rows[0][0],
                    'date': sorted_rows[0][1],  # release_date
                    'updates': {
                        'features': json.loads(sorted_rows[0][5])
                    }
                }
            
            # 华为加载器 - 使用 release_time
            cursor.execute('SELECT version, actual_version, spec, file_name, download_url, release_time FROM huawei_loader_versions')
            rows = cursor.fetchall()
            if rows:
                sorted_rows = sorted(rows,
                                   key=lambda x: self._version_to_tuple(x[0]),
                                   reverse=True)
                latest_versions['huawei_loader'] = {
                    'name': '华为加载器',
                    'version': sorted_rows[0][0],
                    'actual_version': sorted_rows[0][1],  # 添加 actual_version
                    'date': sorted_rows[0][5],  # release_time
                    'updates': {
                        'features': [f'规范版本: {sorted_rows[0][2]}', f'文件: {sorted_rows[0][3]}']
                    }
                }
            
            return latest_versions
            
        except Exception as e:
            self.logger.error(f"获取最新版本信息失败: {str(e)}")
            return {}

    def get_version_history(self, monitor_type: str) -> List[Dict]:
        """获取指定监控项的历史版本记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if monitor_type == 'huawei_loader':
                cursor.execute('''
                    SELECT version, actual_version, spec, file_name, download_url, release_time, created_at 
                    FROM huawei_loader_versions
                ''')
                rows = cursor.fetchall()
                sorted_rows = sorted(rows,
                                   key=lambda x: self._version_to_tuple(x[0]),
                                   reverse=True)
                return [{
                    'version': row[0],
                    'actual_version': row[1],
                    'spec': row[2],
                    'text': row[3],
                    'url': row[4],
                    'release_time': row[5],
                    'created_at': row[6]
                } for row in sorted_rows]
            
            elif monitor_type == 'honor_debugger':
                cursor.execute('''
                    SELECT engine_version, honor_version, union_version, debugger_version, 
                           download_url, features, release_time, created_at 
                    FROM honor_debugger_versions
                ''')
                rows = cursor.fetchall()
                sorted_rows = sorted(rows,
                                   key=lambda x: self._version_to_tuple(x[3]),
                                   reverse=True)
                return [{
                    '快应用引擎版本号': row[0],
                    '荣耀引擎版本号': row[1],
                    '快应用联盟平台版本号': row[2],
                    '调试器版本号': row[3],
                    '下载地址': row[4],
                    '功能': json.loads(row[5]),
                    'release_time': row[6],
                    'created_at': row[7]
                } for row in sorted_rows]
            
            elif monitor_type == 'huawei_version':
                cursor.execute('SELECT version, release_date, components, interfaces FROM huawei_versions')
                rows = cursor.fetchall()
                sorted_rows = sorted(rows,
                                   key=lambda x: self._version_to_tuple(x[0]),
                                   reverse=True)
                return [{
                    'version': row[0],
                    'date': row[1],
                    'updates': json.loads(row[2])
                } for row in sorted_rows]
            
            elif monitor_type == 'honor_engine':
                cursor.execute('SELECT version, release_date, features, download_url FROM honor_engine_versions')
                rows = cursor.fetchall()
                sorted_rows = sorted(rows,
                                   key=lambda x: self._version_to_tuple(x[0]),
                                   reverse=True)
                return [{
                    '版本号': row[0],
                    '上线时间': row[1],
                    '功能': json.loads(row[2]),
                    '下载地址': row[3]
                } for row in sorted_rows]
            
            return []
        except Exception as e:
            self.logger.error(f"获取历史版本记录失败: {str(e)}")
            return []

    def _format_version_data(self, monitor_type: str, rows: List[tuple]) -> List[Dict]:
        """格式化版本数据"""
        result = []
        try:
            for row in rows:
                if monitor_type == 'huawei_version':
                    result.append({
                        'version': row[0],
                        'date': row[1],
                        'updates': {
                            'components': json.loads(row[2]),
                            'interfaces': json.loads(row[3])
                        }
                    })
                elif monitor_type == 'honor_debugger':
                    result.append({
                        '快应用引擎版本号': row[0],
                        '荣耀引擎版本号': row[1],
                        '快应用联盟平台版本号': row[2],
                        '调试器版本号': row[3],
                        '下载地址': row[4],
                        '功能': json.loads(row[5])
                    })
                elif monitor_type == 'honor_engine':
                    result.append({
                        '版本号': row[0],
                        '上线时间': row[1],
                        '引擎版本': {
                            '荣耀快应用引擎平台': row[2],
                            '快应用联盟平台': row[3]
                        },
                        '下载地址': row[4],
                        '功能': json.loads(row[5])
                    })
                elif monitor_type == 'huawei_loader':
                    result.append({
                        'version': row[0],
                        'spec': row[1],
                        'text': row[2],
                        'url': row[3]
                    })
        except Exception as e:
            self.logger.error(f"格式化版本数据失败: {str(e)}")
        
        return result

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')

    def debug_show_tables(self):
        """显示所有表的内容"""
        try:
            # 显示华为加载器表
            self.logger.info("\n=== 华为加载器表内容 ===")
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM huawei_loader_versions ORDER BY version DESC')
            rows = cursor.fetchall()
            for row in rows:
                self.logger.info(f"版本: {row[0]}, 规范: {row[1]}, 文件名: {row[2]}, 下载地址: {row[3]}, 创建时间: {row[4]}")
            
            # 显示华为版本表
            self.logger.info("\n=== 华为版本表内容 ===")
            cursor.execute('SELECT * FROM huawei_versions ORDER BY version DESC')
            rows = cursor.fetchall()
            for row in rows:
                self.logger.info(f"版本: {row[0]}, 日期: {row[1]}")
            
            # 显示荣耀引擎表
            self.logger.info("\n=== 荣耀引擎表内容 ===")
            cursor.execute('SELECT * FROM honor_engine_versions ORDER BY version DESC')
            rows = cursor.fetchall()
            for row in rows:
                self.logger.info(f"版本: {row[0]}, 日期: {row[1]}")
            
            # 显示荣耀调试器表
            self.logger.info("\n=== 荣耀调试器表内容 ===")
            cursor.execute('SELECT * FROM honor_debugger_versions ORDER BY version DESC')
            rows = cursor.fetchall()
            for row in rows:
                self.logger.info(f"版本: {row[0]}, 日期: {row[1]}")
            
        except Exception as e:
            self.logger.error(f"显示表内容失败: {str(e)}")

    def is_connected(self):
        """检查数据库连接状态"""
        try:
            self._get_connection().cursor()
            return True
        except:
            return False

    def get_last_update_time(self):
        """获取最后更新时间"""
        try:
            # 从日志文件获取最后更新时间
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            self.logger.error(f"获取最后更新时间失败: {str(e)}")
            return '获取失败'

    def _version_to_tuple(self, version: str) -> tuple:
        """将版本号转换为可比较的元组
        Args:
            version: 版本号字符串
        Returns:
            tuple: 版本号元组
        """
        try:
            return tuple(int(i) for i in version.replace('V', '').strip().split('.'))
        except Exception as e:
            self.logger.error(f"版本号转换失败: {str(e)}")
            return (0,)