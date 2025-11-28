# 🐧 账号自动续期脚本

本项目基于 GitHub Actions 实现对账号自动续期功能，支持：

- ✅ 定时续期（每 3 天自动运行）
- ✅ Telegram 通知推送（成功或失败都通知）
- ✅ 全局 SOCKS5 代理支持

---

## 📅 自动运行说明

- 默认通过 **GitHub Actions 每 3 天自动运行一次**。
- 也可手动触发运行（在 GitHub 页面点击 `Run workflow`）。
- 可在 Fork 的仓库中创建 [Secrets](#🔐环境变量配置github-secrets) 后生效。

---

## 🔐 环境变量配置（GitHub Secrets）

点击你的仓库 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`，添加以下变量。

| 变量名 | 是否必填 | 用途说明 |
|--------|----------|-----------|
| `ARCTIC_USERNAME` | ✅ 必填 | 登录账号 |
| `ARCTIC_PASSWORD` | ✅ 必填 | 登录密码 |
| `TELEGRAM_BOT_TOKEN` | ✅ 推荐 | 用于发送 Telegram 通知的 Bot Token |
| `TG_CHAT_ID` | ✅ 推荐 | Telegram 你的账号或频道的 chat_id |
| `SOCKS5_PROXY` | ✅ 推荐 | 使用 SOCKS5 代理访问网站（格式见下） |

---



---

### 🌐 SOCKS5_PROXY 示例

socks5://用户:密码@ip:端口

---

### 📬 Telegram 设置方法
1. 搜索并私聊 [@BotFather](https://t.me/BotFather)，创建一个 Bot，获取 `TELEGRAM_BOT_TOKEN`。  
2. 向你自己的 Telegram 发送一条消息，然后访问以下链接（将 `<你的TOKEN>` 替换为你的 Bot Token）：  
   https://api.telegram.org/bot<你的TOKEN>/getUpdates  
   打开后即可查看并获取你的 `chat_id`。  
3. 将 `TELEGRAM_BOT_TOKEN` 和 `TG_CHAT_ID` 添加到 GitHub 仓库的 Secrets 中。

---

### 🚀 使用方法
1. Fork 本仓库到你自己的 GitHub 账号。  
2. 进入你的仓库，依次点击 **Settings → Secrets and variables → Actions**，添加上一步获取的 Secrets。  
3. GitHub Actions 会自动每三天（北京时间上午 10 点）运行一次，也支持手动触发运行。

---

### 💡 鸣谢
- 感谢 [curl_cffi](https://github.com/romis2012/curl_cffi) 库的作者，项目中使用该库模拟真实浏览器请求。
