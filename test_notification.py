from datetime import datetime
import requests
from config import Config

def test_heartbeat():
    """测试心跳通知"""
    now = datetime.now()
    start_time = now  # 模拟启动时间
    
    # 构造心跳消息
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
                        f"运行时长：`0天0小时0分钟`\n"
                        f"检测时间：`{now.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                        f"启动时间：`{start_time.strftime('%Y-%m-%d %H:%M:%S')}`"
                    )
                }
            ]
        }
    }
    
    try:
        response = requests.post(Config.HEARTBEAT_WEBHOOK, json=message, timeout=30)
        print(f"发送结果: {response.status_code}")
        print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"发送失败: {str(e)}")

if __name__ == "__main__":
    test_heartbeat() 