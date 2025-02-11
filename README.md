# 快应用版本监控系统

一个基于 Python 的监控系统，用于监控华为和荣耀快应用相关版本的更新。

## 主要功能

- 监控华为加载器版本更新
- 监控华为快应用版本说明更新
- 监控荣耀调试器版本更新
- 监控荣耀引擎版本更新
- Web 界面展示监控结果
- 自动保存历史记录
- 实时日志查看
- 每日心跳检测通知

## 运行环境

- Python 3.7+
- SQLite 3

## 安装依赖

```bash
pip install flask
pip install beautifulsoup4
pip install requests
pip install psutil
```

## 使用方法

1. 启动监控服务：
```bash
python app_monitor.py
```

2. 启动 Web 服务：
```bash
python web_app.py
```

3. 访问 Web 界面：
```
http://127.0.0.1:5001
```

## 项目结构

```
.
├── app_monitor.py     # 监控主程序
├── web_app.py        # Web 服务
├── database.py       # 数据库操作
├── config.py         # 配置文件
├── logger_config.py  # 日志配置
├── demo.py           # 测试脚本
├── templates/        # 页面模板
├── logs/            # 日志目录
└── versions.db      # SQLite 数据库
```

## 心跳检测

系统会在每天凌晨 00:00 自动检测监控服务的运行状态：

- 检测 app_monitor.py 是否在运行
- 计算服务运行时长
- 通过飞书机器人发送状态通知

配置定时任务：
```bash
crontab -e
# 添加配置
0 0 * * * cd /path/to/project && /usr/bin/python3 heartbeat_monitor.py >> logs/cron.log 2>&1
``` 