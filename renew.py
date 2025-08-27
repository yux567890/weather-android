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
chat_id = os.environ.get("TG_CHAT_ID", "")
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
    从产品列表页面获取产品ID和管理URL，产品名称在续期时从管理界面获取
    
    Args:
        session (requests.Session): 已登录的会话对象
    
    Returns:
        list: 产品信息列表，每个元素包含 id、manage_url
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
        
        # 使用更精确的方式获取管理按钮
        # 查找包含 class="btn btn-primary" 且 href 包含 /control/detail 的按钮
        print("🔍 搜索管理按钮: class='btn btn-primary' 且 href 包含 '/control/detail'")
        
        # 匹配模式: <a class="btn btn-primary" href="/control/detail/{product_id}/">或类似格式
        # 支持 btn 和 btn-primary 的任意顺序
        manage_button_pattern = r'<a[^>]*class=["\'][^"\'>]*(?:btn[^"\'>]*btn-primary|btn-primary[^"\'>]*btn)[^"\'>]*["\'][^>]*href=["\']([^"\'>]*control/detail/(\d+)[^"\'>]*)["\'][^>]*>'
        matches = re.finditer(manage_button_pattern, html_content, re.IGNORECASE)
        
        product_ids = []
        manage_urls = []
        
        for match in matches:
            full_href = match.group(1)
            product_id = match.group(2)
            product_ids.append(product_id)
            manage_urls.append(full_href)
            print(f"✅ 找到管理按钮: 产品ID {product_id}, URL: {full_href}")
        
        if not product_ids:
            print("❌ 未找到任何符合条件的管理按钮")
            print("🔍 尝试备用方案: 查找任何包含 /control/detail 的链接")
            
            # 备用方案: 查找任何包含 /control/detail 的链接
            fallback_pattern = r'href=["\']([^"\'>]*control/detail/(\d+)[^"\'>]*)["\']'
            fallback_matches = re.finditer(fallback_pattern, html_content, re.IGNORECASE)
            
            for match in fallback_matches:
                full_href = match.group(1)
                product_id = match.group(2)
                product_ids.append(product_id)
                manage_urls.append(full_href)
                print(f"⚠️ 备用方案找到: 产品ID {product_id}, URL: {full_href}")
        
        if not product_ids:
            print("❌ 未在页面中找到任何产品管理链接")
            return []
        
        # 去重产品ID
        unique_product_ids = list(set(product_ids))
        print(f"🔍 找到 {len(unique_product_ids)} 个唯一产品 ID: {unique_product_ids}")
        
        # 创建产品ID到管理URL的映射
        product_url_map = {}
        for i, product_id in enumerate(product_ids):
            if product_id not in product_url_map:
                # 确保 URL 是完整的
                full_url = manage_urls[i]
                if not full_url.startswith('http'):
                    full_url = BASE_URL + ('' if full_url.startswith('/') else '/') + full_url
                product_url_map[product_id] = full_url
        
        products = []
        
        # 为每个产品创建基本信息，产品名称在续期时获取
        for product_id in unique_product_ids:
            manage_url = product_url_map.get(product_id, f'{BASE_URL}/control/detail/{product_id}/')
            product_info = {
                'id': product_id,
                'name': f'VPS_{product_id}',  # 临时名称，在续期时会更新
                'manage_url': manage_url,
                'expiry_date': None  # 在续期时获取
            }
            products.append(product_info)
        
        print(f"\n🎉 最终获取到 {len(products)} 个产品（详细信息将在续期时获取）:")
        for product in products:
            print(f"   • 产品ID: {product['id']}, 管理URL: {product['manage_url']}")
        
        return products
        
    except Exception as error:
        print(f"❌ 解析产品列表失败: {error}")
        return []



# 原 _get_product_details_from_manage_page 函数已移除，因为现在在续期时直接获取产品信息

def _extract_product_name_from_manage_page(html_content, product_id):
    """
    从产品管理界面提取产品名称
    
    Args:
        html_content (str): 管理界面的 HTML 内容
        product_id (str): 产品 ID
    
    Returns:
        str: 产品名称
    """
    default_name = f'VPS_{product_id}'
    
    try:
        # 在管理界面中尝试多种模式来匹配产品名称
        name_patterns = [
            # 模式 1: 匹配页面标题中的产品名称
            r'<title[^>]*>([^<]*(?:产品|服务器|主机|VPS)[^<]*)</title>',
            r'<title[^>]*>([^<]*)</title>',
            
            # 模式 2: 匹配 h1, h2, h3 标题中的产品名称
            r'<h[1-3][^>]*>([^<]*[一-鿿][^<]*)</h[1-3]>',
            r'<h[1-3][^>]*>([^<]+?)</h[1-3]>',
            
            # 模式 3: 匹配包含“产品名称”、“服务器名称”等关键词的内容
            r'(?:产品名称|服务器名称|主机名称|VPS名称)[^:]*[:]：]?\s*([^<\r\n]+)',
            
            # 模式 4: 匹配 class 包含 name、title、product 的标签
            r'<[^>]+class=["\'][^"\'>]*(?:name|title|product)[^"\'>]*["\'][^>]*>\s*([^<]+?)\s*</[^>]+>',
            
            # 模式 5: 匹配强调标签中的产品名称
            r'<(?:strong|b)[^>]*>\s*([^<]*[一-鿿][^<]*)\s*</(?:strong|b)>',
            r'<(?:strong|b)[^>]*>\s*([^<]+?)\s*</(?:strong|b)>',
            
            # 模式 6: 在表格中查找产品相关信息
            r'<td[^>]*>\s*([^<]*[一-鿿][^<]*)\s*</td>',
            r'<td[^>]*>\s*([^<]+?)\s*</td>',
        ]
        
        candidates = []
        
        for pattern_index, pattern in enumerate(name_patterns, 1):
            matches = re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                potential_name = match.group(1).strip()
                
                # 验证产品名称的有效性
                if _is_valid_product_name_for_manage_page(potential_name):
                    candidates.append((potential_name, pattern_index))
        
        if candidates:
            # 优先选择包含中文的名称
            chinese_candidates = [c for c in candidates if re.search(r'[一-鿿]', c[0])]
            if chinese_candidates:
                best_name, best_pattern = chinese_candidates[0]
                print(f"🎯 从管理界面使用模式 {best_pattern} 提取到产品名称 (中文优先): {best_name}")
                return best_name
            
            # 其次选择不像域名且长度较长的名称
            non_domain_candidates = [c for c in candidates if not _looks_like_domain(c[0])]
            if non_domain_candidates:
                best_name, best_pattern = max(non_domain_candidates, key=lambda x: len(x[0]))
                print(f"🎯 从管理界面使用模式 {best_pattern} 提取到产品名称 (非域名优先): {best_name}")
                return best_name
            
            # 最后选择第一个候选名称
            best_name, best_pattern = candidates[0]
            print(f"🎯 从管理界面使用模式 {best_pattern} 提取到产品名称 (备用): {best_name}")
            return best_name
        
        print(f"⚠️ 未能从管理界面提取产品 {product_id} 的有效名称，使用默认名称")
        return default_name
        
    except Exception as error:
        print(f"⚠️ 从管理界面提取产品 {product_id} 名称失败: {error}")
        return default_name


def _is_valid_product_name_for_manage_page(name):
    """
    验证从管理界面提取的产品名称是否有效（相比列表页面更宽松）
    
    Args:
        name (str): 待验证的产品名称
    
    Returns:
        bool: 是否为有效的产品名称
    """
    if not name or len(name) < 2 or len(name) > 200:
        return False
    
    # 过滤空白字符
    if re.match(r'^\s*$', name):
        return False
    
    # 过滤明显的域名格式
    if _looks_like_domain(name):
        return False
    
    # 过滤包含HTML标签的内容
    if '<' in name and '>' in name:
        return False
    
    # 过滤纠明显不是产品名称的关键词（管理界面相对宽松）
    invalid_keywords = [
        'control', 'detail', 'manage', 'admin', 'panel',
        'login', 'logout', 'sign', 'register',
        'http', 'https', 'www', 'html', 'css', 'js',
        'error', 'success', 'fail', 'warning'
    ]
    
    name_lower = name.lower()
    for keyword in invalid_keywords:
        if keyword in name_lower:
            return False
    
    # 过滤纯数字或纯特殊字符
    if name.isdigit() or re.match(r'^[^a-zA-Z\u4e00-\u9fff]+$', name):
        return False
    
    # 对于管理界面，接受更多类型的名称
    return True


def _extract_expiry_from_manage_page(html_content):
    """
    从产品管理界面提取到期时间
    
    Args:
        html_content (str): 管理界面的 HTML 内容
    
    Returns:
        str: 到期时间，如果未找到则返回 None
    """
    try:
        # 定义多种到期时间匹配模式，针对管理界面优化
        expiry_patterns = [
            # 模式 1: 中文日期描述
            r'(?:到期时间|过期时间|有效期至|截止时间)[^0-9]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[\s]+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})?)',
            
            # 模式 2: 英文日期描述
            r'(?:Expiry|expiry|Expires|expires|Valid\s+until|valid\s+until)[^0-9]*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[\s]+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})?)',
            
            # 模式 3: 在表格中查找日期格式
            r'<td[^>]*>\s*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[\s]+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})?)\s*</td>',
            
            # 模式 4: 在span或div中查找日期
            r'<(?:span|div)[^>]*>\s*([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[\s]+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})?)\s*</(?:span|div)>',
            
            # 模式 5: 任意日期格式（作为备选）
            r'([0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[\s]+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2})?)',
            
            # 模式 6: 其他日期格式
            r'([0-9]{4}/[0-9]{1,2}/[0-9]{1,2})',
            r'([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)',
        ]
        
        for pattern_index, pattern in enumerate(expiry_patterns, 1):
            matches = re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                potential_date = match.group(1).strip()
                
                # 验证日期格式是否合理
                if _is_valid_date_format(potential_date):
                    print(f"📅 从管理界面使用模式 {pattern_index} 提取到期时间: {potential_date}")
                    return potential_date
        
        print(f"⚠️ 未能从管理界面提取到期时间")
        return None
        
    except Exception as error:
        print(f"⚠️ 从管理界面提取到期时间失败: {error}")
        return None


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
        
        # 获取更大范围的上下文片段用于分析（前 800 字符，后 200 字符）
        start_pos = max(0, match_position.start() - 800)
        end_pos = min(len(html_content), match_position.end() + 200)
        context_html = html_content[start_pos:end_pos]
        
        # 尝试多种模式来匹配产品名称，优先匹配产品名称而非域名
        name_patterns = [
            # 模式 1: 产品名称在表格的第一列，管理链接在后面的列
            rf'<td[^>]*>\s*([^<]+?)\s*</td>(?:[\s\S]*?<td[^>]*>){0,3}[\s\S]*?control/detail/{product_id}',
            
            # 模式 4: 产品名称在 class 包含 "name" 或 "title" 的标签中
            rf'<[^>]+class=["\'][^"\'>]*(?:name|title|product)[^"\'>]*["\'][^>]*>\s*([^<]+?)\s*</[^>]+>[\s\S]*?control/detail/{product_id}',
            
            # 模式 5: 产品名称在 h3, h4, h5 标题标签中
            rf'<h[3-5][^>]*>\s*([^<]+?)\s*</h[3-5]>[\s\S]*?control/detail/{product_id}',
            
            # 模式 6: 产品名称在 strong 或 b 标签中
            rf'<(?:strong|b)[^>]*>\s*([^<]+?)\s*</(?:strong|b)>[\s\S]*?control/detail/{product_id}',
            
            # 模式 7: 产品名称在第一个 td 中，优先选择非域名内容
            rf'<tr[^>]*>[\s\S]*?<td[^>]*>\s*([^<]+?)\s*</td>[\s\S]*?control/detail/{product_id}',
            
            # 模式 8: 产品名称在 div 中，但排除包含域名特征的
            rf'<div[^>]*>\s*([^<]+?)\s*</div>[\s\S]*?control/detail/{product_id}',
            
            # 模式 9: 从 title 或 alt 属性中提取
            rf'(?:title|alt)=["\']([^"\'>]+?)["\'][\s\S]*?control/detail/{product_id}',
        ]
        
        for pattern_index, pattern in enumerate(name_patterns, 1):
            matches = re.finditer(pattern, context_html, re.IGNORECASE | re.DOTALL)
            
            candidates = []  # 收集所有候选名称
            for match in matches:
                potential_name = match.group(1).strip()
                
                # 收集所有有效的候选名称
                if _is_valid_product_name(potential_name):
                    candidates.append((potential_name, pattern_index))
            
            # 如果找到候选名称，选择最优的一个
            if candidates:
                # 优先选择包含中文的名称
                chinese_candidates = [c for c in candidates if re.search(r'[\u4e00-\u9fff]', c[0])]
                if chinese_candidates:
                    best_name, best_pattern = chinese_candidates[0]
                    print(f"🎯 使用模式 {best_pattern} 提取到产品名称 (中文优先): {best_name}")
                    return best_name
                
                # 其次选择长度较长且不像域名的名称
                non_domain_candidates = [c for c in candidates if not _looks_like_domain(c[0])]
                if non_domain_candidates:
                    # 按长度排序，选择最长的
                    best_name, best_pattern = max(non_domain_candidates, key=lambda x: len(x[0]))
                    print(f"🎯 使用模式 {best_pattern} 提取到产品名称 (非域名优先): {best_name}")
                    return best_name
                
                # 最后选择第一个候选名称
                best_name, best_pattern = candidates[0]
                print(f"🎯 使用模式 {best_pattern} 提取到产品名称 (备用): {best_name}")
                return best_name
        
        print(f"⚠️ 未能提取产品 {product_id} 的有效名称，使用默认名称")
        return default_name
        
    except Exception as error:
        print(f"⚠️ 提取产品 {product_id} 名称失败: {error}")
        return default_name


def _looks_like_domain(name):
    """
    检查名称是否看起来像域名
    
    Args:
        name (str): 待检查的名称
    
    Returns:
        bool: 是否看起来像域名
    """
    if not name:
        return False
    
    name = name.strip().lower()
    
    # 检查是否包含域名特征
    domain_indicators = [
        # 包含顶级域名
        r'\.(com|org|net|cn|io|co|me|info|biz)\b',
        # 以 www 开头
        r'^www\.',
        # 包含 http/https
        r'https?://',
        # 标准域名格式 (字母数字.字母数字.字母)
        r'^[a-z0-9-]+\.[a-z0-9-]+\.[a-z]{2,}$',
        # 简单域名格式 (字母数字.字母)
        r'^[a-z0-9-]+\.[a-z]{2,}$',
    ]
    
    for pattern in domain_indicators:
        if re.search(pattern, name):
            return True
    
    # 检查是否主要由域名字符组成且包含点
    if '.' in name and re.match(r'^[a-z0-9.-]+$', name):
        return True
    
    return False


def _is_valid_product_name(name):
    """
    验证产品名称是否有效，优先过滤掉域名格式的内容
    
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
    
    # 增强域名过滤：首先使用专门的域名检测函数
    if _looks_like_domain(name):
        print(f"🙅 过滤域名格式: {name}")
        return False
    
    # 过滤明显的域名格式（保留原有逻辑作为补充）
    domain_patterns = [
        r'^https?://',  # URL 格式
        r'^www\.',  # www 开头
    ]
    
    for pattern in domain_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            print(f"🙅 过滤URL格式: {name}")
            return False
    
    # 过滤包含特定关键词的内容
    invalid_keywords = [
        '管理', 'detail', 'control', 'action', 'button',
        'edit', 'delete', 'view', 'show', 'hide', 'click',
        'href', 'link', 'url', 'http', 'https', 'www'
    ]
    
    name_lower = name.lower()
    for keyword in invalid_keywords:
        if keyword in name_lower:
            print(f"🙅 过滤包含关键词 '{keyword}': {name}")
            return False
    
    # 过滤纯数字或纯特殊字符
    if name.isdigit() or re.match(r'^[^a-zA-Z\u4e00-\u9fff]+$', name):
        print(f"🙅 过滤纯数字或特殊字符: {name}")
        return False
    
    # 过滤过短的单词或缩写
    if len(name) < 4 and not re.search(r'[\u4e00-\u9fff]', name):  # 非中文且过短
        print(f"🙅 过滤过短内容: {name}")
        return False
    
    # 优先选择包含中文或有意义英文的名称
    if re.search(r'[\u4e00-\u9fff]', name):  # 包含中文
        print(f"✅ 首选中文产品名称: {name}")
        return True
    
    # 检查是否为有意义的英文名称（包含空格或有多个单词）
    if ' ' in name or len(name) >= 6:
        print(f"✅ 接受英文产品名称: {name}")
        return True
    
    print(f"⚠️ 跳过不确定的内容: {name}")
    return False


def _extract_expiry_from_list_page(html_content, product_id):
    """
    从产品列表页面提取指定产品的到期时间
    
    Args:
        html_content (str): HTML 页面内容
        product_id (str): 产品 ID
    
    Returns:
        str: 到期时间，如果未找到则返回 None
    """
    try:
        # 找到包含该产品 ID 的 HTML 片段
        id_pattern = rf'control/detail/{product_id}[/"\'>]'
        match_position = re.search(id_pattern, html_content)
        
        if not match_position:
            return None
        
        # 获取更大范围的上下文片段用于分析（前 1000 字符，后 300 字符）
        start_pos = max(0, match_position.start() - 1000)
        end_pos = min(len(html_content), match_position.end() + 300)
        context_html = html_content[start_pos:end_pos]
        
        # 定义多种到期时间匹配模式，优先级排列
        expiry_patterns = [
            # 模式 1: 在同一表格行中，在管理链接前的单元格中寻找日期
            rf'<tr[^>]*>[\s\S]*?<td[^>]*>\s*([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]*?</td>[\s\S]*?control/detail/{product_id}',
            
            # 模式 2: 在同一行中，查找中文日期描述后的日期
            rf'<tr[^>]*>[\s\S]*?到期时间[\uff1a:]?\s*([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]*?control/detail/{product_id}',
            rf'<tr[^>]*>[\s\S]*?过期时间[\uff1a:]?\s*([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]*?control/detail/{product_id}',
            rf'<tr[^>]*>[\s\S]*?有效期至[\uff1a:]?\s*([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]*?control/detail/{product_id}',
            
            # 模式 3: 在div容器中查找日期
            rf'<div[^>]*>[\s\S]*?到期[\uff1a:]?\s*([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]*?control/detail/{product_id}',
            
            # 模式 4: 英文格式的日期描述
            rf'(?:Expiry|expiry|Expires|expires)[\uff1a:]?\s*([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]*?control/detail/{product_id}',
            
            # 模式 5: 在产品上下文中查找任何日期格式（作为备选）
            rf'([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)[\s\S]{{0,100}}control/detail/{product_id}',
            
            # 模式 6: 反向查找 - 从管理链接向前查找日期
            rf'control/detail/{product_id}[\s\S]{{0,200}}([0-9]{{4}}-[0-9]{{1,2}}-[0-9]{{1,2}}(?:[\s]+[0-9]{{1,2}}:[0-9]{{1,2}}:[0-9]{{1,2}})?)',
            
            # 模式 7: 其他日期格式
            rf'([0-9]{{4}}/[0-9]{{1,2}}/[0-9]{{1,2}})[\s\S]*?control/detail/{product_id}',
            rf'([0-9]{{4}}年[0-9]{{1,2}}月[0-9]{{1,2}}日)[\s\S]*?control/detail/{product_id}',
        ]
        
        for pattern_index, pattern in enumerate(expiry_patterns, 1):
            matches = re.finditer(pattern, context_html, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                potential_date = match.group(1).strip()
                
                # 验证日期格式是否合理
                if _is_valid_date_format(potential_date):
                    print(f"📅 使用模式 {pattern_index} 从列表页提取到期时间: {potential_date} (产品ID: {product_id})")
                    return potential_date
        
        print(f"⚠️ 未能从列表页提取产品 {product_id} 的到期时间")
        return None
        
    except Exception as error:
        print(f"⚠️ 从列表页提取产品 {product_id} 到期时间失败: {error}")
        return None


def _is_valid_date_format(date_str):
    """
    验证日期格式是否合理
    
    Args:
        date_str (str): 日期字符串
    
    Returns:
        bool: 是否为有效的日期格式
    """
    if not date_str:
        return False
    
    # 检查常见的日期格式
    date_patterns = [
        r'^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$',  # YYYY-MM-DD
        r'^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}\s+[0-9]{1,2}:[0-9]{1,2}:[0-9]{1,2}$',  # YYYY-MM-DD HH:MM:SS
        r'^[0-9]{4}/[0-9]{1,2}/[0-9]{1,2}$',  # YYYY/MM/DD
        r'^[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日$',  # YYYY年MM月DD日
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, date_str):
            # 进一步检查日期的合理性（月份1-12，日期1-31）
            try:
                # 提取数字部分
                numbers = re.findall(r'[0-9]+', date_str)
                if len(numbers) >= 3:
                    year, month, day = int(numbers[0]), int(numbers[1]), int(numbers[2])
                    if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return True
            except:
                pass
    
    return False

# 原 _remove_duplicate_products 函数已在新逻辑中处理，不再需要

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
    """
    对单个产品进行续期操作
    
    优化说明：
    - 直接从续期按钮界面（管理界面）获取产品名称和到期时间
    - 续期后重新从管理界面获取更新的到期时间
    - 增强日志输出和错误处理
    
    Args:
        session: 已登录的会话对象
        product: 产品信息字典，包含 id、name、expiry_date 等
    
    Returns:
        dict: 包含 success和expiry_date的结果字典
    """
    import time
    
    try:
        product_id = product['id']
        manage_url = product.get('manage_url', f"{BASE_URL}/control/detail/{product_id}/")
        
        print(f"🔄 开始续期操作: 产品 ID {product_id}")
        print(f"📎 产品管理页面: {manage_url}")
        
        # 步骤 1: 从续期按钮界面（管理界面）获取准确的产品名称和到期时间
        print(f"🔍 步骤 1: 从续期按钮界面获取产品信息...")
        
        try:
            response = session.get(manage_url, proxies=proxy_config, timeout=60)
            if response.status_code == 200:
                html_content = response.text
                
                # 从管理界面获取准确的产品名称
                actual_product_name = _extract_product_name_from_manage_page(html_content, product_id)
                
                # 从管理界面获取到期时间
                old_expiry = _extract_expiry_from_manage_page(html_content)
                
                print(f"✅ 从续期按钮界面获取到:")
                print(f"    产品名称: {actual_product_name}")
                print(f"    到期时间: {old_expiry or '未知'}")
                
                # 更新产品信息
                product['name'] = actual_product_name
                product['expiry_date'] = old_expiry
                
            else:
                print(f"⚠️ 无法访问管理界面: HTTP {response.status_code}")
                print(f"⚠️ 使用原有产品信息进行续期")
                actual_product_name = product.get('name', f'VPS_{product_id}')
                old_expiry = product.get('expiry_date')
                
        except Exception as e:
            print(f"⚠️ 获取管理界面信息失败: {e}")
            print(f"⚠️ 使用原有产品信息进行续期")
            actual_product_name = product.get('name', f'VPS_{product_id}')
            old_expiry = product.get('expiry_date')
        
        print(f"\n🔄 步骤 2: 开始续期操作 - {actual_product_name}")
        
        # 步骤 3: 执行续期操作
        pay_url = f"{BASE_URL}/control/detail/{product_id}/pay/"
        print(f"💳 执行续期请求: {pay_url}")
        
        renew_response = session.post(pay_url, timeout=120, proxies=proxy_config)
        
        if renew_response.status_code == 200 and "免费产品已经帮您续期到当前时间的最大续期时间" in renew_response.text:
            print(f"✅ {actual_product_name} 续期操作成功")
            print(f"🔄 步骤 4: 获取续期后的更新信息...")
            
            # 续期成功后，重新从产品管理界面获取更新后的到期时间
            new_expiry = _get_updated_expiry_from_manage_page(session, product_id, old_expiry)
            
            return {'success': True, 'expiry_date': new_expiry}
            
        else:
            print(f"❌ {actual_product_name} 续期操作失败: 状态码 {renew_response.status_code}")
            if renew_response.status_code == 200:
                print(f"🗎 响应内容片段: {renew_response.text[:200]}...")
            elif renew_response.status_code == 403:
                print("🔐 可能需要重新登录或会话已过期")
            elif renew_response.status_code == 404:
                print("🔍 产品不存在或已被删除")
            
            return {'success': False, 'expiry_date': old_expiry}
            
    except Exception as e:
        actual_product_name = product.get('name', f'VPS_{product.get("id", "unknown")}')
        print(f"❌ {actual_product_name} 续期请求异常: {e}")
        if "timeout" in str(e).lower():
            print("⏰ 请求超时，可能是网络问题")
        elif "connection" in str(e).lower():
            print("🌐 连接失败，检查网络或代理设置")
        
        return {'success': False, 'expiry_date': product.get('expiry_date')}


def _get_updated_expiry_from_manage_page(session, product_id, old_expiry):
    """
    从产品管理界面获取续期后的新到期时间
    
    优化说明：
    - 直接从管理界面获取最新数据，更加准确可靠
    - 增加智能等待策略和错误处理
    - 更好的日志输出和进度显示
    
    Args:
        session (requests.Session): 会话对象
        product_id (str): 产品 ID
        old_expiry (str): 续期前的到期时间
    
    Returns:
        str: 更新后的到期时间
    """
    print("⏳ 等待服务器更新数据...")
    time.sleep(3)  # 初始等待，让服务器处理续期操作
    
    max_retries = 5  # 增加重试次数以提高成功率
    retry_delays = [2, 3, 5, 8, 10]  # 递增的等待旴间
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 第 {attempt + 1}/{max_retries} 次尝试从管理界面获取更新后的到期时间...")
            
            manage_url = f"{BASE_URL}/control/detail/{product_id}/"
            print(f"🌐 请求地址: {manage_url}")
            
            # 重新获取产品管理页面，确保获取最新数据
            response = session.get(
                manage_url, 
                proxies=proxy_config, 
                timeout=60,
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            
            if response.status_code == 200:
                print(f"✅ 成功获取产品管理页面 (响应大小: {len(response.text)} 字符)")
                
                # 从新的页面内容中提取到期时间
                new_expiry = _extract_expiry_from_manage_page(response.text)
                
                if new_expiry:
                    # 检查时间是否真的更新了
                    if new_expiry != old_expiry:
                        print(f"✅ 检测到到期时间变化!")
                        print(f"📅 续期前: {old_expiry}")
                        print(f"📅 续期后: {new_expiry}")
                        print(f"🎉 续期成功！从管理界面确认时间已更新")
                        return new_expiry
                    else:
                        print(f"📅 获取到时间: {new_expiry} (与续期前相同)")
                        if attempt < max_retries - 1:
                            print(f"⏳ 服务器可能还在更新数据，等待 {retry_delays[attempt]} 秒后重试...")
                        else:
                            print(f"⚠️ 经过 {max_retries} 次尝试，时间仍未更新")
                            print(f"💡 可能原因: 1) 续期未生效 2) 服务器更新延迟 3) 已经是最新时间")
                            # 即使时间相同，也返回从管理界面获取的时间，确保数据一致性
                            return new_expiry
                else:
                    print(f"⚠️ 第 {attempt + 1} 次尝试未能从管理界面提取到期时间")
                    print(f"🔍 产品ID: {product_id} 在页面中可能暂时不可见")
            else:
                print(f"❌ 获取产品管理页面失败: HTTP {response.status_code}")
                if response.status_code == 403:
                    print(f"🔐 可能需要重新登录或会话已过期")
                elif response.status_code == 502 or response.status_code == 503:
                    print(f"🌐 服务器临时不可用，稍后重试")
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                print(f"⏳ 等待 {delay} 秒后进行第 {attempt + 2} 次尝试...")
                time.sleep(delay)
                
        except Exception as error:
            print(f"❌ 第 {attempt + 1} 次获取到期时间异常: {error}")
            if "timeout" in str(error).lower():
                print(f"⏰ 网络超时，可能是网络连接问题")
            elif "connection" in str(error).lower():
                print(f"🌐 连接失败，检查网络或代理设置")
            
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                print(f"⏳ 异常恢复等待 {delay} 秒...")
                time.sleep(delay)
    
    # 如果所有尝试都失败，返回原有的到期时间
    final_expiry = old_expiry or '未知'
    print(f"⚠️ 经过 {max_retries} 次尝试仍无法从管理界面获取更新后的到期时间")
    print(f"🔄 回退策略: 使用续期前时间 [{final_expiry}]")
    print(f"💡 建议: 稍后可手动检查产品管理界面确认续期状态")
    return final_expiry


def _get_updated_expiry_from_list(session, product_id, old_expiry):
    """
    从产品列表页面获取续期后的新到期时间
    
    优化说明：
    - 增加更智能的等待策略
    - 改进时间比较逻辑
    - 增强错误处理和日志输出
    - 确保从 https://vps.polarbear.nyc.mn/control/index/ 获取最新数据
    
    Args:
        session (requests.Session): 会话对象
        product_id (str): 产品 ID
        old_expiry (str): 续期前的到期时间
    
    Returns:
        str: 更新后的到期时间
    """
    print("⏳ 等待服务器更新数据...")
    time.sleep(3)  # 初始等待，让服务器处理续期操作
    
    max_retries = 5  # 增加重试次数以提高成功率
    retry_delays = [2, 3, 5, 8, 10]  # 递增的等待时间
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 第 {attempt + 1}/{max_retries} 次尝试从列表页获取更新后的到期时间...")
            print(f"🌐 请求地址: {PRODUCT_LIST_URL}")
            
            # 重新获取产品列表页面，确保获取最新数据
            response = session.get(
                PRODUCT_LIST_URL, 
                proxies=proxy_config, 
                timeout=60,
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            
            if response.status_code == 200:
                print(f"✅ 成功获取产品列表页面 (响应大小: {len(response.text)} 字符)")
                
                # 从新的页面内容中提取到期时间
                new_expiry = _extract_expiry_from_list_page(response.text, product_id)
                
                if new_expiry:
                    # 检查时间是否真的更新了
                    if new_expiry != old_expiry:
                        print(f"✅ 检测到到期时间变化!")
                        print(f"📅 续期前: {old_expiry}")
                        print(f"📅 续期后: {new_expiry}")
                        print(f"🎉 续期成功！从列表页面确认时间已更新")
                        return new_expiry
                    else:
                        print(f"📅 获取到时间: {new_expiry} (与续期前相同)")
                        if attempt < max_retries - 1:
                            print(f"⏳ 服务器可能还在更新数据，等待 {retry_delays[attempt]} 秒后重试...")
                        else:
                            print(f"⚠️ 经过 {max_retries} 次尝试，时间仍未更新")
                            print(f"💡 可能原因: 1) 续期未生效 2) 服务器更新延迟 3) 已经是最新时间")
                            # 即使时间相同，也返回从列表页获取的时间，确保数据一致性
                            return new_expiry
                else:
                    print(f"⚠️ 第 {attempt + 1} 次尝试未能从列表页提取到期时间")
                    print(f"🔍 产品ID: {product_id} 在页面中可能暂时不可见")
            else:
                print(f"❌ 获取产品列表页面失败: HTTP {response.status_code}")
                if response.status_code == 403:
                    print(f"🔐 可能需要重新登录或会话已过期")
                elif response.status_code == 502 or response.status_code == 503:
                    print(f"🌐 服务器临时不可用，稍后重试")
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                print(f"⏳ 等待 {delay} 秒后进行第 {attempt + 2} 次尝试...")
                time.sleep(delay)
                
        except Exception as error:
            print(f"❌ 第 {attempt + 1} 次获取到期时间异常: {error}")
            if "timeout" in str(error).lower():
                print(f"⏰ 网络超时，可能是网络连接问题")
            elif "connection" in str(error).lower():
                print(f"🌐 连接失败，检查网络或代理设置")
            
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                print(f"⏳ 异常恢复等待 {delay} 秒...")
                time.sleep(delay)
    
    # 如果所有尝试都失败，返回原有的到期时间
    final_expiry = old_expiry or '未知'
    print(f"⚠️ 经过 {max_retries} 次尝试仍无法从列表页获取更新后的到期时间")
    print(f"🔄 回退策略: 使用续期前时间 [{final_expiry}]")
    print(f"💡 建议: 稍后可手动检查产品列表确认续期状态")
    return final_expiry

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
            print(f"   - {product['name']} (当前到期: {product['expiry_date']})")