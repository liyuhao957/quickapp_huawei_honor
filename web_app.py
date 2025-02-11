from flask import Flask, render_template, request, redirect, flash, jsonify
import logging
from database import VersionDatabase
from config import Config  # 只需要 Config 类来读取配置
from datetime import datetime
import json
import os
import requests
import time
import subprocess
from logger_config import setup_module_logger

# 先创建 Flask 应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# 然后配置日志
logger = setup_module_logger('web_app')
werkzeug_logger = setup_module_logger('werkzeug')

# 设置 Flask logger
app.logger.handlers = []
app.logger.addHandler(setup_module_logger('flask').handlers[0])

db = VersionDatabase()  # 只需要数据库连接来读取状态

def is_monitor_running():
    """检查 app_monitor.py 是否在运行"""
    try:
        # 使用 ps 命令并检查完整命令行
        cmd = "ps -ef | grep 'python.*app_monitor.py' | grep -v grep | wc -l"
        output = subprocess.check_output(cmd, shell=True)
        count = int(output.strip())
        app.logger.info(f"检测到 {count} 个监控进程")
        
        if count > 1:
            app.logger.warning(f"检测到多个监控进程实例，建议清理")
            return False  # 多个实例运行时返回 False
        
        return count == 1  # 只有一个实例时返回 True
    except Exception as e:
        app.logger.error(f"检查进程状态失败: {str(e)}")
        return False

@app.route('/')
def index():
    """首页路由"""
    try:
        # 首先检查监控进程状态
        monitor_running = is_monitor_running()
        
        # 获取所有监控项的最新版本
        versions = db.get_latest_versions()
        if not versions:
            return render_template('error.html', 
                                error="暂无数据，请先运行监控脚本获取数据")
        
        # 调整显示顺序
        ordered_versions = {}
        order = [
            'huawei_loader',     # 华为加载器
            'huawei_version',    # 华为版本说明
            'honor_debugger',    # 荣耀调试器
            'honor_engine'       # 荣耀引擎版本
        ]
        
        # 根据进程状态设置监控项状态
        for key in order:
            if key in versions:
                versions[key]['status'] = '正常运行中' if monitor_running else '已停止'
                ordered_versions[key] = versions[key]
        
        # 获取系统状态信息
        system_status = {
            'running': '正常运行中' if monitor_running else '已停止',
            'db_connected': '已连接' if db.is_connected() else '未连接',
            'last_update': db.get_last_update_time()
        }
                
        return render_template('index.html', 
                             versions=ordered_versions,
                             system_status=system_status)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/monitor/<monitor_type>')
def monitor_detail(monitor_type):
    """监控详情页路由"""
    try:
        # 首先检查监控进程状态
        monitor_running = is_monitor_running()
        
        # 获取指定监控项的历史版本
        history = db.get_version_history(monitor_type)
        
        # 获取所有监控项的最新版本
        versions = db.get_latest_versions()
        
        # 根据进程状态更新历史记录的状态
        if history:
            for record in history:
                record['status'] = '正常运行中' if monitor_running else '已停止'
        
        # 获取系统状态信息
        system_status = {
            'running': '正常运行中' if monitor_running else '已停止',
            'db_connected': '已连接' if db.is_connected() else '未连接',
            'last_update': db.get_last_update_time()
        }
        
        return render_template('monitor_detail.html',
                             monitor_type=monitor_type,
                             history=history,
                             versions=versions,
                             system_status=system_status)
    except Exception as e:
        # 错误页面也需要 system_status
        system_status = {
            'running': '正常运行中' if monitor_running else '已停止',
            'db_connected': '已连接' if db.is_connected() else '未连接',
            'last_update': db.get_last_update_time()
        }
        return render_template('error.html', 
                             error=str(e),
                             system_status=system_status)

@app.route('/logs')
def show_logs():
    """显示监控日志"""
    try:
        # 首先检查监控进程状态
        monitor_running = is_monitor_running()
        
        # 获取系统状态信息
        system_status = {
            'running': '正常运行中' if monitor_running else '已停止',
            'db_connected': '已连接' if db.is_connected() else '未连接',
            'last_update': db.get_last_update_time()
        }
        
        logs = {}
        log_files = {
            'huawei_loader': 'logs/huawei_loader.log',
            'huawei_version': 'logs/huawei_version.log',
            'honor_debugger': 'logs/honor_debugger.log',
            'honor_engine': 'logs/honor_engine.log'
        }
        
        for name, path in log_files.items():
            try:
                with open(path, 'r') as f:
                    # 读取所有行
                    lines = f.readlines()
                    # 倒序排列
                    lines.reverse()
                    # 取前50行
                    logs[name] = lines[:50]
            except Exception as e:
                logs[name] = [f"读取日志失败: {str(e)}"]
        
        return render_template('logs.html', logs=logs, system_status=system_status)
    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True, port=5001) 