# -*- coding: utf-8 -*-
"""
ArcticCloud VPS 自动续期脚本

功能:
- 自动登录 ArcticCloud 管理面板
- 获取所有 VPS 产品列表
- 自动续期免费 VPS 产品
- 通过 Telegram 发送续期状态通知
- 支持 SOCKS5 代理访问

作者: xiong_renew 项目
版本: 2.0
"""

import os
import json
import re
import time
from curl_cffi import requests

# =============================================================================
# 配置部分 - 从环境变量读取配置信息
# =============================================================================

# SOCKS5 代理配置 (可选)
# 格式: socks5://username:password@host:port
socks5_proxy_url = os.environ.get("SOCKS5_PROXY", "")
proxy_config = {
    "http": socks5_proxy_url,
    "https": socks5_proxy_url
} if socks5_proxy_url else {}

if socks5_proxy_url:
    print(f"🌐 已配置 SOCKS5 代理: {socks5_proxy_url[:20]}...")
else:
    print("🌐 未配置代理，使用直连")

# ArcticCloud 账号配置 (必需)
username = os.environ.get("ARCTIC_USERNAME", "")
password = os.environ.get("ARCTIC_PASSWORD", "")

if not username or not password:
    print("❌ 账号密码不全！请设置 ARCTIC_USERNAME 和 ARCTIC_PASSWORD 环境变量！")
    print("   示例: export ARCTIC_USERNAME='your_username'")
    print("   示例: export ARCTIC_PASSWORD='your_password'")
    exit(1)

print(f"✅ 已加载账号配置: {username[:3]}***")

# ArcticCloud 登录地址
LOGIN_URL = "https://vps.polarbear.nyc.mn/index/login/?referer=%2Fcontrol%2Findex%2F"
PRODUCT_LIST_URL = "https://vps.polarbear.nyc.mn/control/index/"
BASE_URL = "https://vps.polarbear.nyc.mn"

# Telegram 通知配置 (可选)
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat_id = os.environ.get("CHAT_ID", "")
thread_id = os.environ.get("THREAD_ID", "")
telegram_api_url = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")

if telegram_bot_token and chat_id:
    print("✅ 已配置 Telegram 通知")
else:
    print("⚠️ 未配置 Telegram 通知，将仅显示控制台输出")

# =============================================================================
# 工具函数部分
# =============================================================================

def send_telegram_notification(token, chat_id, message):
    """
    发送 Telegram 通知
    
    Args:
        token (str): Telegram Bot Token
        chat_id (str): 聊天 ID
        message (str): 要发送的消息
    
    Returns:
        bool: 发送是否成功
    """
    if not token or not chat_id:
        print("⚠️ Telegram 配置不全，跳过发送通知")
        return False
    
    api_url = f'{telegram_api_url}/bot{token}/sendMessage'
    notification_data = {
        'chat_id': chat_id,
        'text': message
    }
    
    # 如果配置了线程 ID，则添加到请求中
    if thread_id:
        notification_data['message_thread_id'] = thread_id
    
    try:
        response = requests.post(
            api_url, 
            json=notification_data, 
            timeout=30, 
            proxies=proxy_config
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Telegram 通知发送成功")
                return True
            else:
                print(f"❌ Telegram API 返回错误: {result.get('description', '未知错误')}")
        else:
            print(f"❌ Telegram 请求失败: HTTP {response.status_code}")
        
        return False
        
    except Exception as error:
        print(f"❌ Telegram 通知发送失败: {error}")
        return False

def login_to_arcticcloud(login_url, username, password):
    """
    登录到 ArcticCloud 管理面板
    
    Args:
        login_url (str): 登录页面地址
        username (str): 用户名
        password (str): 密码
    
    Returns:
        requests.Session: 登录成功的会话对象，失败返回 None
    """
    print(f"🔑 开始登录 ArcticCloud: {username[:3]}***")
    
    # 创建会话对象，模拟 Chrome 浏览器
    session = requests.Session(impersonate="chrome110")
    
    try:
        # 首先访问登录页面获取 Cookies
        print("🌐 访问登录页面...")
        session.get(login_url, proxies=proxy_config, timeout=30)
        
    except Exception as error:
        print(f"❌ 登录页访问失败: {error}")
        return None

    # 准备登录数据
    login_data = {
        "swapname": username,
        "swappass": password
    }
    
    # 设置请求头，模拟真实浏览器
    request_headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36",
        'Origin': "https://vps.polarbear.nyc.mn",
        'Referer': login_url,
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8",
        'Accept-Encoding': "gzip, deflate, br",
        'Connection': "keep-alive",
        'Upgrade-Insecure-Requests': "1"
    }
    
    try:
        print("🔐 提交登录表单...")
        response = session.post(
            login_url, 
            data=login_data, 
            headers=request_headers, 
            proxies=proxy_config, 
            timeout=60
        )
        
        # 检查登录是否成功
        if response.status_code == 200:
            response_text = response.text
            # 检查登录成功的标志
            if '欢迎回来' in response_text or '退出登录' in response_text:
                print("✅ ArcticCloud 登录成功")
                return session
            elif '错误' in response_text or '失败' in response_text:
                print("❌ 登录失败: 用户名或密码错误")
            else:
                print("❌ 登录失败: 未知错误")
        else:
            print(f"❌ 登录请求失败: HTTP {response.status_code}")
            
    except Exception as error:
        print(f"❌ 登录异常: {error}")
    
    return None

def get_product_list_from_page(session):
    """
    从产品列表页面获取所有 VPS 产品信息
    
    Args:
        session (requests.Session): 已登录的会话对象
    
    Returns:
        list: 产品信息列表，每个元素包含 id、name、manage_url
    """
    print(f"📋 获取产品列表: {PRODUCT_LIST_URL}")
    
    try:
        response = session.get(PRODUCT_LIST_URL, proxies=proxy_config, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ 获取产品列表失败: HTTP {response.status_code}")
            return []
        
        print("✅ 成功获取产品列表页面")
        
        # 解析 HTML 内容
        html_content = response.text
        products = []
        
        # 使用正则表达式匹配所有管理链接
        # 匹配模式: /control/detail/{product_id}/
        manage_link_pattern = r'/control/detail/(\d+)/?["\'>]'
        product_ids = re.findall(manage_link_pattern, html_content)
        
        if not product_ids:
            print("❌ 未在页面中找到任何产品管理链接")
            return []
        
        print(f"🔍 找到 {len(product_ids)} 个产品 ID: {product_ids}")
        
        # 为每个产品 ID 提取产品名称
        for product_id in product_ids:
            product_name = _extract_product_name(html_content, product_id)
            
            product_info = {
                'id': product_id,
                'name': product_name,
                'manage_url': f'{BASE_URL}/control/detail/{product_id}/'
            }
            
            products.append(product_info)
        
        # 去重处理（根据产品 ID）
        unique_products = _remove_duplicate_products(products)
        
        print(f"🎉 最终获取到 {len(unique_products)} 个唯一产品:")
        for product in unique_products:
            print(f"   • {product['name']} (ID: {product['id']})")
        
        return unique_products
        
    except Exception as error:
        print(f"❌ 解析产品列表失败: {error}")
        return []


def _extract_product_name(html_content, product_id):
    """
    从 HTML 内容中提取指定产品 ID 的产品名称
    
    Args:
        html_content (str): HTML 页面内容
        product_id (str): 产品 ID
    
    Returns:
        str: 产品名称，如果无法提取则返回默认名称
    """
    default_name = f'VPS_{product_id}'
    
    try:
        # 找到包含该产品 ID 的 HTML 片段
        id_pattern = rf'control/detail/{product_id}[/"\'>]'
        match_position = re.search(id_pattern, html_content)
        
        if not match_position:
            return default_name
        
        # 获取上下文片段用于分析（前 500 字符，后 100 字符）
        start_pos = max(0, match_position.start() - 500)
        end_pos = min(len(html_content), match_position.end() + 100)
        context_html = html_content[start_pos:end_pos]
        
        # 尝试多种模式来匹配产品名称
        name_patterns = [
            # 模式 1: <td>产品名称</td> ... 管理链接
            rf'<td[^>]*>([^<]+)</td>[\s\S]*?control/detail/{product_id}',
            # 模式 2: <div>产品名称</div> ... 管理链接
            rf'<div[^>]*>([^<]+)</div>[\s\S]*?control/detail/{product_id}',
            # 模式 3: <span>产品名称</span> ... 管理链接
            rf'<span[^>]*>([^<]+)</span>[\s\S]*?control/detail/{product_id}',
            # 模式 4: 任意标签中的内容 ... 管理链接
            rf'>([^<>]+)</[^>]*>[\s\S]*?control/detail/{product_id}',
            # 模式 5: title 或 alt 属性中的内容
            rf'(?:title|alt)=["\']([^"\'>]+)["\'][\s\S]*?control/detail/{product_id}'
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, context_html, re.IGNORECASE | re.DOTALL)
            if name_match:
                potential_name = name_match.group(1).strip()
                
                # 过滤掉不合理的内容
                if _is_valid_product_name(potential_name):
                    return potential_name
        
        return default_name
        
    except Exception as error:
        print(f"⚠️ 提取产品 {product_id} 名称失败: {error}")
        return default_name


def _is_valid_product_name(name):
    """
    验证产品名称是否有效
    
    Args:
        name (str): 待验证的产品名称
    
    Returns:
        bool: 是否为有效的产品名称
    """
    if not name or len(name) < 2 or len(name) > 100:
        return False
    
    # 过滤空白字符
    if re.match(r'^\s*$', name):
        return False
    
    # 过滤包含特定关键词的内容
    invalid_keywords = ['管理', 'detail', 'control']
    if any(keyword in name for keyword in invalid_keywords):
        return False
    
    # 过滤纯数字
    if name.isdigit():
        return False
    
    return True


def _remove_duplicate_products(products):
    """
    移除重复的产品（根据产品 ID）
    
    Args:
        products (list): 产品列表
    
    Returns:
        list: 去重后的产品列表
    """
    seen_ids = set()
    unique_products = []
    
    for product in products:
        if product['id'] not in seen_ids:
            seen_ids.add(product['id'])
            unique_products.append(product)
    
    return unique_products

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
        manage_response = session.get(product['manage_url'], proxies=proxy_config, timeout=60)
        if manage_response.status_code != 200:
            print(f"❌ 访问管理页面失败: 状态码 {manage_response.status_code}")
            return {'success': False, 'expiry_date': None}
        
        print(f"✅ 成功访问 {product['name']} 管理页面")
        
        # 提取续期前的到期时间
        old_expiry = extract_expiry_date(manage_response.text)
        if old_expiry:
            print(f"📅 续期前到期时间: {old_expiry}")
        
        # 执行续期操作
        pay_url = f"{BASE_URL}/control/detail/{product['id']}/pay/"
        renew_response = session.post(pay_url, timeout=120, proxies=proxy_config)
        
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
                    updated_response = session.get(product['manage_url'], proxies=proxy_config, timeout=60)
                    
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

session = login_to_arcticcloud(LOGIN_URL, username, password)

if session:
    # 获取产品列表
    products = get_product_list_from_page(session)
    
    if not products:
        print("❌ 未找到任何产品，退出脚本")
        if telegram_bot_token and chat_id:
            send_telegram_notification(telegram_bot_token, chat_id, "ArcticCloud VPS续期提醒：\n\n❌未找到任何产品！😭")
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
                send_telegram_notification(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n✅{product['name']}已成功续期7天！😋{expiry_info}")
        else:
            fail_count += 1
            failed_products.append({
                'name': product['name'],
                'expiry_date': result['expiry_date'] or '未知'
            })
            
            # 单个产品失败通知
            expiry_info = f"\n📅 当前到期时间: {result['expiry_date']}" if result['expiry_date'] else ""
            if telegram_bot_token and chat_id:
                send_telegram_notification(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n❌{product['name']}续期失败！😭{expiry_info}")
    
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
        
        send_telegram_notification(telegram_bot_token, chat_id, summary_message)
    
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
            print(f"   - {product['name']} (当前到期: {product['expiry_date']})")            print(f"   - {product['name']} (当前到期: {product['expiry_date']})")