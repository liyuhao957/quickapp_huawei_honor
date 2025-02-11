"""监控系统配置"""

class Config:
    """配置类"""
    # 检查间隔配置（秒）
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