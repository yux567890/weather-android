import os
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

# 环境变量配置
USERNAME = os.environ.get("ARCTIC_USERNAME")
PASSWORD = os.environ.get("ARCTIC_PASSWORD")
TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

PROXY = os.environ.get("SOCKS5_PROXY")  # 设置代理


LOGIN_URL = "https://vps.polarbear.nyc.mn/index/login/?referer=%2Fcontrol%2Findex%2F"
CONTROL_INDEX_URL = "https://vps.polarbear.nyc.mn/control/index/"



def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_telegram(title, content):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("Telegram 推送配置缺失，跳过发送。")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": content,
        "parse_mode": "MarkdownV2"
    }
    try:
        resp = requests.post(url, data=data, timeout=15)
        if resp.status_code == 200:
            print("Telegram 推送成功")
        else:
            print(f"Telegram 推送失败，状态码 {resp.status_code}，响应：{resp.text}")
    except Exception as e:
        print(f"Telegram 推送异常: {e}")

def login_and_get_session():
    session = requests.Session(impersonate="chrome110")
    try:
        session.get(LOGIN_URL, proxies=proxies)
    except Exception as e:
        print(f"登录页访问失败: {e}")
        return None


    proxies = {
        "http": PROXY,
        "https": PROXY,
    } if PROXY else {}
    
    payload = {
        "swapname": USERNAME,
        "swappass": PASSWORD,
    }

     headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36",
        'origin': "https://vps.polarbear.nyc.mn/",
        'referer': LOGIN_URL,
    }

    if not USERNAME or not PASSWORD:
        print("账号密码不全！退出脚本！")
        exit()
    
    response = session.post(LOGIN_URL, data=payload, headers=headers, proxies=proxies, timeout=60)
    if response.status_code == 200 and ('欢迎回来' in response.text or '退出登录' in response.text):
        print(f"✅ 登录成功")
        return session
    print("❌ 登录失败")    
    except Exception as e:
        print("登录异常:", e)
    return None

def find_and_renew_instances(session):
    print("查找 VPS 实例列表...")
    response = session.get(CONTROL_INDEX_URL, proxies={"http": PROXY, "https": PROXY})
    
    print("页面返回:\n" + response.text)  # 打印格式化后的 HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("页面内容:\n" + soup.prettify())  # 打印格式化后的 HTML
    manage_buttons = soup.find_all('a', class_='btn btn-primary', href=lambda href: href and '/control/detail/' in href)
    if not manage_buttons:
        print("没有找到任何服务器实例")
        return

    results = []
    for btn in manage_buttons:
        href = btn['href']
        instance_id = href.split("/")[-2]
        instance_name = btn.text.strip() or "未命名实例"
        print(f"处理实例: 名称={instance_name} ID={instance_id}")
        
        detail_response = session.get(f"https://vps.polarbear.nyc.mn{href}", proxies={"http": PROXY, "https": PROXY})
        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')

        try:
            renew_button = detail_soup.find('button', {'data-target': '#addcontactmodal'})
            if renew_button:
                # 模拟点击续期按钮及提交
                submit_button = detail_soup.find('input', class_='btn-success')
                # 假设提交续期
                submit_response = session.post(f"https://vps.polarbear.nyc.mn{renew_button['href']}", proxies={"http": PROXY, "https": PROXY})
                print(f"✅ 续期成功，实例：{instance_name}")

                expiration_text = " ❌ 未找到到期时间信息"
                # 查找到期时间
                expiration_info = detail_soup.find(text=re.compile("到期时间"))
                if expiration_info:
                    expiration_text = expiration_info.strip()

                msg = (
                    f"✅ ArcticCloud VPS 续期成功：【{instance_name}】\n"
                    "———————————————————\n"
                    f"🗓️ {expiration_text}"
                )
                results.append(escape_markdown_v2(msg))

        except Exception as e:
            print(f"续期实例 {instance_name} 出错: {e}")
            err_msg = f"❌ ArcticCloud 续期失败【{instance_name}】，错误: {e}"
            results.append(escape_markdown_v2(err_msg))

    if results:
        send_telegram("", "以下为续期结果:\n\n".join(results))

def main():
    try:
        print("启动自动续期...")
        session = login_and_get_session()
        find_and_renew_instances(session)
    except Exception:
        print("主程序异常退出")

if __name__ == "__main__":
    main()