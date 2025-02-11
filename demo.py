import requests
from bs4 import BeautifulSoup
import json
from config import Config

def get_huawei_version_html():
    """获取华为版本更新页面的HTML内容"""
    try:
        # 获取页面内容
        url = Config.API_URLS["huawei_version"]  # 使用配置中的 URL
        data = {
            "objectId": "quickapp-version-updates-0000001079803874",
            "version": "",
            "catalogName": "quickApp-Guides",
            "language": "cn"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://developer.huawei.com',
            'Referer': 'https://developer.huawei.com/'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and 'value' in data and 'content' in data['value']:
                html_content = data['value']['content']['content']
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 打印所有 h2 标签
                print("\n所有 h2 标签:")
                for h2 in soup.find_all('h2'):
                    print(h2.text)
                
                # 打印所有 h4 标签
                print("\n所有 h4 标签:")
                for h4 in soup.find_all('h4'):
                    print(h4.text)
                
                # 打印所有表格
                print("\n所有表格:")
                for table in soup.find_all('table'):
                    print(table.text[:100])
                
                # 查找所有版本标题
                version_titles = soup.find_all('h4', string=lambda x: x and '版本更新说明' in x and '[h2]' not in x)
                versions = []
                
                for title in version_titles:
                    # 解析版本信息
                    title_text = title.text.strip()
                    version_number = title_text.split('版本更新说明')[0].strip()
                    version_date = title_text[title_text.find('（')+1:title_text.find('）')] if '（' in title_text else ''
                    
                    current_version = {
                        'version': version_number,
                        'date': version_date,
                        'updates': {
                            'framework': [],
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
                        if '[h2]' in current.text:
                            text = current.text.strip()
                            if '框架' in text:
                                current_type = 'framework'
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
                                    desc = cols[1].text.strip()
                                    if name and desc:
                                        current_version['updates'][current_type].append({
                                            'name': name,
                                            'description': desc
                                        })
                        current = current.find_next()
                    
                    versions.append(current_version)
                
                # 保存为 JSON 格式
                with open('huawei_version.json', 'w', encoding='utf-8') as f:
                    json.dump(versions, f, ensure_ascii=False, indent=2)
                
                # 保存为文本格式
                with open('huawei_version.txt', 'w', encoding='utf-8') as f:
                    for version in versions:
                        f.write(f"\n版本 {version['version']} ({version['date']})\n")
                        f.write("=" * 50 + "\n")
                        
                        # 框架更新
                        if version['updates']['framework']:
                            f.write("\n【框架】\n")
                            for item in version['updates']['framework']:
                                f.write(f"• {item['name']}\n  {item['description']}\n")
                        
                        # 组件更新
                        if version['updates']['components']:
                            f.write("\n【组件】\n")
                            for item in version['updates']['components']:
                                f.write(f"• {item['name']}\n  {item['description']}\n")
                        
                        # 接口更新
                        if version['updates']['interfaces']:
                            f.write("\n【接口】\n")
                            for item in version['updates']['interfaces']:
                                f.write(f"• {item['name']}\n  {item['description']}\n")
                        
                        f.write("\n" + "=" * 50 + "\n")
                
                print("内容已保存到文件：")
                print("- huawei_version.json (JSON格式)")
                print("- huawei_version.txt (文本格式)")
                return True
        
        raise ValueError("获取内容失败")
    except Exception as e:
        print(f"获取内容失败: {str(e)}")
        return False

if __name__ == "__main__":
    get_huawei_version_html() 