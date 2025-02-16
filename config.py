"""监控系统配置"""
import json
import os
from datetime import datetime
from logger_config import setup_module_logger  # 添加日志

class Config:
    """配置类"""
    _config_file = 'monitor_config.json'
    _logger = setup_module_logger('config')  # 添加日志记录器
    _last_load_time = 0  # 添加最后加载时间记录
    
    # 默认配置
    CHECK_INTERVALS = {
        'huawei_version': 20,
        'honor_debugger': 20,
        'honor_engine': 20,
        'huawei_loader': 20
    }
    
    # API URLs
    API_URLS = {
        'huawei_version': 'https://svc-drcn.developer.huawei.com/community/servlet/consumer/cn/documentPortal/getDocumentById',
        'honor': 'https://developer.honor.com/document/portal/tree/101380',
        'huawei_loader': 'https://svc-drcn.developer.huawei.com/community/servlet/consumer/cn/documentPortal/getDocumentById'
    }

    # 固定的 webhook 配置
    WEBHOOK_URLS = {
        'huawei_version': 'https://open.feishu.cn/open-apis/bot/v2/hook/1a11a0f0-b246-423c-909f-5ebbbbf4e2f4',
        'honor_debugger': 'https://open.feishu.cn/open-apis/bot/v2/hook/3359b367-baf6-44c4-8536-3ebd7aedc03e', 
        'honor_engine': 'https://open.feishu.cn/open-apis/bot/v2/hook/5fe61b9f-a14e-468e-aeb7-72b473f2e6df',
        'huawei_loader': 'https://open.feishu.cn/open-apis/bot/v2/hook/b5d78e2d-502d-42c7-81d2-48eebf43224e'
    }

    # 固定的错误通知 webhook
    ERROR_WEBHOOK = 'https://open.feishu.cn/open-apis/bot/v2/hook/0073ebb8-c91f-42c9-a88a-b4ecae2b82ba'

    # 心跳检测配置
    HEARTBEAT_WEBHOOK = 'https://open.feishu.cn/open-apis/bot/v2/hook/dd7a3644-a1c7-457a-90af-9a72cc7e41bd'

    @classmethod
    def load_config(cls):
        """从配置文件加载配置"""
        try:
            if os.path.exists(cls._config_file):
                with open(cls._config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cls._logger.info(f"读取配置文件: {config}")  # 记录读取的配置
                    if 'intervals' in config:
                        old_intervals = cls.CHECK_INTERVALS.copy()  # 保存旧配置
                        cls.CHECK_INTERVALS.update(config['intervals'])
                        # 记录配置变化
                        for key, value in cls.CHECK_INTERVALS.items():
                            if value != old_intervals.get(key):
                                cls._logger.info(f"配置已更新: {key} = {value}秒")
        except Exception as e:
            cls._logger.error(f"加载配置文件失败: {e}")

    @classmethod
    def save_config(cls):
        """保存配置到文件"""
        try:
            config = {
                'intervals': cls.CHECK_INTERVALS,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            cls._logger.info(f"正在保存配置: {config}")  # 记录要保存的配置
            with open(cls._config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            cls._logger.info("配置文件保存成功")  # 记录保存成功
            return True
        except Exception as e:
            cls._logger.error(f"保存配置文件失败: {e}")
            return False

    @classmethod
    def update_interval(cls, monitor: str, interval: int) -> bool:
        """更新检查间隔"""
        try:
            if monitor in cls.CHECK_INTERVALS and 10 <= interval <= 3600:
                old_interval = cls.CHECK_INTERVALS[monitor]
                cls._logger.info(f"更新间隔: {monitor} {old_interval}秒 -> {interval}秒")  # 记录更新
                cls.CHECK_INTERVALS[monitor] = interval
                return cls.save_config()
            return False
        except Exception as e:
            cls._logger.error(f"更新间隔失败: {e}")
            return False

    @classmethod
    def get_interval(cls, monitor: str) -> int:
        """获取检查间隔"""
        # 检查配置文件是否有更新
        if os.path.exists(cls._config_file):
            mtime = os.path.getmtime(cls._config_file)
            if mtime > cls._last_load_time:
                cls.load_config()
                cls._last_load_time = mtime
        return cls.CHECK_INTERVALS.get(monitor, 20)

# 初始加载配置
Config.load_config() 