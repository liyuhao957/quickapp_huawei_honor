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

系统提供多层心跳检测机制：

### Web 界面实时检测
- 实时显示监控服务运行状态
- 显示数据库连接状态
- 显示最后更新时间
- 通过进程检测确保单实例运行

### 日志监控
- 所有监控项独立日志文件
- 日志自动按时间倒序排列
- 保留最新 50 条日志记录
- 错误日志高亮显示

### 自动检测
监控服务(app_monitor.py)内置心跳检测功能：
- 定时检测服务运行状态
- 计算服务运行时长
- 通过飞书机器人发送状态通知
- 自动记录检测时间到数据库

### 状态展示
在页面底部状态栏实时显示：
- 系统运行状态（正常/已停止）
- 数据库连接状态（已连接/未连接）
- 最后更新时间 