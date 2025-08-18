# -- coding: utf-8 --
import os
import json
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

session = session_login(login_url, username, password)

if session:
    for k, v in config.get('VPS', {}).items():
        try:
            r = session.post(f"https://vps.polarbear.nyc.mn/control/detail/{v}/pay/", timeout=120, proxies=proxies)
            if r.status_code == 200 and "免费产品已经帮您续期到当前时间的最大续期时间" in r.text:
                print(f"✅ {k}续期成功")
                if telegram_bot_token and chat_id:
                    telegram_Bot(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n✅{k}已成功续期7天！😋")
            else:
                print(f"❌ {k}续期失败: 状态码 {r.status_code}")
                if telegram_bot_token and chat_id:
                    telegram_Bot(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n❌{k}续期失败！😭")
        except Exception as e:
            print(f"❌ {k}续期请求失败: {e}")
            if telegram_bot_token and chat_id:
                telegram_Bot(telegram_bot_token, chat_id, f"ArcticCloud VPS续期提醒：\n\n❌{k}续期请求失败！😭")