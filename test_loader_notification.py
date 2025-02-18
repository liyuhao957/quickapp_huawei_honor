from app_monitor import HuaweiLoaderMonitor

def test_notification():
    """测试华为加载器的通知格式"""
    monitor = HuaweiLoaderMonitor()
    
    # 测试场景1: 下载链接版本高于页面版本
    content1 = {
        'version': '14.5.1.300',
        'actual_version': '14.5.1.302',
        'spec': '1119',
        'text': 'HwQuickApp_Loader_Phone_V14.5.1.300.apk',
        'url': 'https://example.com/loader-14.5.1.302.apk'
    }
    
    # 测试场景2: 页面版本更新但下载链接未更新
    content2 = {
        'version': '14.5.1.302',
        'actual_version': '14.5.1.302',
        'spec': '1119',
        'text': 'HwQuickApp_Loader_Phone_V14.5.1.302.apk',
        'url': 'https://example.com/loader-14.5.1.302.apk'
    }
    
    print("\n=== 测试场景1: 下载链接版本高于页面版本 ===")
    monitor.send_notification(content1)
    
    print("\n=== 测试场景2: 页面版本更新但下载链接未更新 ===")
    monitor.send_notification(content2)

if __name__ == "__main__":
    test_notification() 