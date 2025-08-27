# -- coding: utf-8 --
import os
import json
import re
import time
from curl_cffi import requests

# 获取 SOCKS5 代理地址（如：socks5://user:pass@host:port）
socks5_proxy = os.environ.get("SOCKS5_PROXY", "")
proxies = {
    "http": socks5_proxy,
    "https": socks5_proxy
} if socks5_proxy else {}

# 加载 ArcticCloud_CONFIG 环境变量
config = os.environ.get("ArcticCloud_CONFIG", '{"username": "", "password": "", "VPS": {}}')
try:
    config = json.loads(config)
except json.JSONDecodeError as e:
    raise ValueError(f"解析 'ArcticCloud_CONFIG' 时出错: {str(e)}")

username = config.get('username', '')
password = config.get('password', '')
if not username or not password:
    print("账号密码不全！退出脚本！")
    exit()

login_url = "https://vps.polarbear.nyc.mn/index/login/?referer=%2Fcontrol%2Findex%2F"

telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat_id = os.environ.get("CHAT_ID", "")
thread_id = os.environ.get("THREAD_ID", "")
telegram_api_url = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")

def telegram_Bot(token, chat_id, message):
    url = f'{telegram_api_url}/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'message_thread_id': thread_id,
        'text': message
    }
    try:
        r = requests.post(url, json=data, timeout=30, proxies=proxies)
        print(f"Telegram推送成功: {r.json().get('ok')}")
    except Exception as e:
        print(f"Telegram推送失败: {e}")

def session_login(url, username, password):
    session = requests.Session(impersonate="chrome110")
    try:
        session.get(url, proxies=proxies)
    except Exception as e:
        print(f"登录页访问失败: {e}")
        return None

    data = {"swapname": username, "swappass": password}
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36",
        'origin': "https://vps.polarbear.nyc.mn/",
        'referer': url,
    }
    try:
        response = session.post(url, data=data, headers=headers, proxies=proxies, timeout=60)
        if response.status_code == 200 and ('欢迎回来' in response.text or '退出登录' in response.text):
            print("✅ 登录成功")
            return session
        print("❌ 登录失败")
    except Exception as e:
        print("登录异常:", e)
    return None

def parse_product_list(session):
    """解析产品列表页面，获取产品信息和管理链接"""
    try:
        list_url = "https://vps.polarbear.nyc.mn/control/index/"
        response = session.get(list_url, proxies=proxies, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ 获取产品列表失败: 状态码 {response.status_code}")
            return []
        
        print("✅ 成功获取产品列表页面")
        
        products = []
        html_content = response.text
        
        # 尝试多种模式来匹配产品信息
        # 模式1: 寻找包含产品名称和管理链接的表格行或div块
        # 常见的HTML结构可能是: <td>产品名称</td>...<a href="/control/detail/123/">管理</a>
        
        # 首先提取所有管理链接和对应的产品ID
        manage_pattern = r'/control/detail/(\d+)/?["\'>]'
        product_ids = re.findall(manage_pattern, html_content)
        
        if not product_ids:
            print("❌ 未找到任何管理链接")
            return []
        
        # 为了获取产品名称，我们需要分析HTML结构
        # 尝试几种常见的模式来匹配产品名称
        
        # 模式1: 表格结构 - 查找包含产品ID的行，然后向前查找产品名称
        for product_id in product_ids:
            product_name = f'VPS_{product_id}'  # 默认名称
            
            # 尝试匹配包含该产品ID的HTML片段
            id_pattern = rf'control/detail/{product_id}[/"\'>]'
            match_pos = re.search(id_pattern, html_content)
            
            if match_pos:
                # 获取匹配位置前后的文本片段用于分析
                start_pos = max(0, match_pos.start() - 500)
                end_pos = min(len(html_content), match_pos.end() + 100)
                context = html_content[start_pos:end_pos]
                
                # 尝试多种产品名称提取模式
                name_patterns = [
                    # 模式1: <td>产品名称</td> ... 管理链接
                    r'<td[^>]*>([^<]+)</td>[\s\S]*?control/detail/' + product_id,
                    # 模式2: <div>产品名称</div> ... 管理链接  
                    r'<div[^>]*>([^<]+)</div>[\s\S]*?control/detail/' + product_id,
                    # 模式3: <span>产品名称</span> ... 管理链接
                    r'<span[^>]*>([^<]+)</span>[\s\S]*?control/detail/' + product_id,
                    # 模式4: 产品名称在管理链接前的任何标签中
                    r'>([^<>]+)</[^>]*>[\s\S]*?control/detail/' + product_id,
                    # 模式5: title或alt属性中的产品名称
                    r'(?:title|alt)=["\']([^"\'>]+)["\'][\s\S]*?control/detail/' + product_id
                ]
                
                for pattern in name_patterns:
                    name_match = re.search(pattern, context, re.IGNORECASE | re.DOTALL)
                    if name_match:
                        potential_name = name_match.group(1).strip()
                        # 过滤掉明显不是产品名称的内容
                        if (len(potential_name) > 2 and 
                            len(potential_name) < 100 and
                            not re.match(r'^\s*$', potential_name) and
                            '管理' not in potential_name and
                            'detail' not in potential_name and
                            not potential_name.isdigit()):
                            product_name = potential_name
                            break
            
            products.append({
                'id': product_id,
                'name': product_name,
                'manage_url': f'https://vps.polarbear.nyc.mn/control/detail/{product_id}/'
            })
        
        # 去重处理（根据产品ID）
        seen_ids = set()
        unique_products = []
        for product in products:
            if product['id'] not in seen_ids:
                seen_ids.add(product['id'])
                unique_products.append(product)
        
        print(f"🔍 找到 {len(unique_products)} 个产品")
        for product in unique_products:
            print(f"  - {product['name']} (ID: {product['id']})")
        
        return unique_products
        
    except Exception as e:
        print(f"❌ 解析产品列表失败: {e}")
        return []

def extract_expiry_date(html_content):
    """从产品管理页面提取到期时间"""
    try:
        # 尝试多种模式来匹配到期时间
        expiry_patterns = [
            # 模式1: 到期时间: 2024-01-01
            r'到期时间[：:][\s]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
            # 模式2: 过期时间: 2024-01-01  
            r'过期时间[：:][\s]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
            # 模式3: 有效期至: 2024-01-01
            r'有效期至[：:][\s]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
            # 模式4: 截止时间: 2024-01-01
            r'截止时间[：:][\s]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
            # 模式5: Expiry: 2024-01-01
            r'(?:Expiry|expiry)[：:][\s]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})',
            # 模式6: 任何包含日期格式的内容
            r'([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}[\s]*[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})',
            r'([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})',
            r'([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
        ]
        
        for pattern in expiry_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
        
    except Exception as e:
        print(f"提取到期时间失败: {e}")
        return None

def renew_product(session, product):
    """对单个产品进行续期操作"""
    import time
    
    try:
        print(f"🔄 开始续期: {product['name']}")
        
        # 首先访问产品管理页面
        manage_response = session.get(product['manage_url'], proxies=proxies, timeout=60)
        if manage_response.status_code != 200:
            print(f"❌ 访问管理页面失败: 状态码 {manage_response.status_code}")
            return {'success': False, 'expiry_date': None}
        
        print(f"✅ 成功访问 {product['name']} 管理页面")
        
        # 提取续期前的到期时间
        old_expiry = extract_expiry_date(manage_response.text)
        if old_expiry:
            print(f"📅 续期前到期时间: {old_expiry}")
        
        # 执行续期操作
        pay_url = f"https://vps.polarbear.nyc.mn/control/detail/{product['id']}/pay/"
        renew_response = session.post(pay_url, timeout=120, proxies=proxies)
        
        if renew_response.status_code == 200 and "免费产品已经帮您续期到当前时间的最大续期时间" in renew_response.text:
            print(f"✅ {product['name']} 续期成功")
            
            # 续期成功后，等待服务器更新数据，然后重新获取管理页面来获取新的到期时间
            print(f"⏳ 等待服务器更新数据...")
            time.sleep(3)  # 等待3秒让服务器更新数据
            
            # 尝试多次获取更新后的到期时间
            new_expiry = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    print(f"🔄 第{attempt + 1}次尝试获取更新后的到期时间...")
                    updated_response = session.get(product['manage_url'], proxies=proxies, timeout=60)
                    
                    if updated_response.status_code == 200:
                        new_expiry = extract_expiry_date(updated_response.text)
                        if new_expiry and new_expiry != old_expiry:
                            print(f"📅 续期后到期时间: {new_expiry}")
                            print(f"✅ 成功获取到续期后的新到期时间")
                            break
                        elif new_expiry:
                            print(f"📅 获取到时间: {new_expiry} (与续期前相同，可能需要等待更新)")
                        else:
                            print(f"⚠️ 未能提取到期时间，将在{2}秒后重试...")
                    else:
                        print(f"❌ 获取管理页面失败: 状态码 {updated_response.status_code}")
                    
                    # 如果不是最后一次尝试，则等待后重试
                    if attempt < max_retries - 1:
                        time.sleep(2)  # 等待2秒后重试
                        
                except Exception as e:
                    print(f"❌ 第{attempt + 1}次获取到期时间失败: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
            
            # 确定最终返回的到期时间
            final_expiry = new_expiry if new_expiry else old_expiry
            
            if new_expiry and new_expiry != old_expiry:
                print(f"🎉 续期成功！到期时间已从 {old_expiry} 更新为 {new_expiry}")
            elif new_expiry:
                print(f"✅ 续期成功！到期时间: {new_expiry}")
            else:
                print(f"⚠️ 续期成功，但无法获取更新后的到期时间，使用续期前时间: {final_expiry}")
            
            return {'success': True, 'expiry_date': final_expiry}
            
        else:
            print(f"❌ {product['name']} 续期失败: 状态码 {renew_response.status_code}")
            # 打印部分响应内容用于调试
            print(f"响应内容片段: {renew_response.text[:200]}...")
            return {'success': False, 'expiry_date': old_expiry}
            
    except Exception as e:
        print(f"❌ {product['name']} 续期请求失败: {e}")
        return {'success': False, 'expiry_date': None}

session = session_login(login_url, username, password)

if session:
    # 获取产品列表
    products = parse_product_list(session)
    
    if not products:
        print("❌ 未找到任何产品，退出脚本")
        if telegram_bot_token and chat_id:
            telegram_Bot(telegram_bot_token, chat_id, "ArcticCloud VPS续期提醒：\n\n❌未找到任何产品！😭")
        exit()
    
    # 对每个产品进行续期
    success_count = 0
    fail_count = 0
    success_products = []
    failed_products = []
    
    for product in products:
        result = renew_product(session, product)
        if result['success']:
            success_count += 1
            success_products.append({
                'name': product['name'],
                'expiry_date': result['expiry_date'] or '未知'
            })
            
            # 单个产品成功通知
            expiry_info = f"\n📅 到期时间: {result['expiry_date']}" if result['expiry_date'] else ""
            if telegram_bot_token and chat_id:
                telegram_Bot(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n✅{product['name']}已成功续期7天！😋{expiry_info}")
        else:
            fail_count += 1
            failed_products.append({
                'name': product['name'],
                'expiry_date': result['expiry_date'] or '未知'
            })
            
            # 单个产品失败通知
            expiry_info = f"\n📅 当前到期时间: {result['expiry_date']}" if result['expiry_date'] else ""
            if telegram_bot_token and chat_id:
                telegram_Bot(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n❌{product['name']}续期失败！😭{expiry_info}")
    
    # 发送汇总通知
    if telegram_bot_token and chat_id:
        summary_message = f"ArcticCloud VPS续期汇总：\n\n📊 总计: {len(products)} 个产品\n✅ 成功: {success_count} 个\n❌ 失败: {fail_count} 个\n"
        
        # 添加成功产品的详细信息
        if success_products:
            summary_message += "\n✅ 成功续期的产品：\n"
            for i, product in enumerate(success_products, 1):
                summary_message += f"{i}. {product['name']}\n   📅 到期时间: {product['expiry_date']}\n"
        
        # 添加失败产品的详细信息
        if failed_products:
            summary_message += "\n❌ 续期失败的产品：\n"
            for i, product in enumerate(failed_products, 1):
                summary_message += f"{i}. {product['name']}\n   📅 当前到期: {product['expiry_date']}\n"
        
        telegram_Bot(telegram_bot_token, chat_id, summary_message)
    
    print(f"\n📊 续期完成汇总：")
    print(f"   总计: {len(products)} 个产品")
    print(f"   成功: {success_count} 个")
    print(f"   失败: {fail_count} 个")
    
    # 打印详细信息
    if success_products:
        print(f"\n✅ 成功续期的产品：")
        for product in success_products:
            print(f"   - {product['name']} (到期时间: {product['expiry_date']})")
    
    if failed_products:
        print(f"\n❌ 续期失败的产品：")
        for product in failed_products:
            print(f"   - {product['name']} (当前到期: {product['expiry_date']})")