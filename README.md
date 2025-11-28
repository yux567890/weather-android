# 🐧 Account Auto-Renewal Script

This project implements an automatic account renewal feature based on GitHub Actions, supporting:

- ✅ Scheduled renewal (runs automatically every 3 days)
- ✅ Telegram notification push (notifies on both success and failure)
- ✅ Global SOCKS5 proxy support

---

## 📅 Automatic Execution Instructions

- By default, GitHub Actions runs automatically every 3 days.
- Manual triggering is also supported (click "Run workflow" on the GitHub page).
- Takes effect after creating Secrets in your forked repository.

---

## 🔐 Environment Variable Configuration (GitHub Secrets)

Go to your repository → Settings → Secrets and variables → Actions → New repository secret, and add the following variables.

| Variable Name | Required | Description |
| --- | --- | --- |
| ARCTIC_USERNAME | ✅ Required | Login username |
| ARCTIC_PASSWORD | ✅ Required | Login password |
| TELEGRAM_BOT_TOKEN | ✅ Recommended | Bot Token for sending Telegram notifications |
| TG_CHAT_ID | ✅ Recommended | Your Telegram account or channel chat_id |
| SOCKS5_PROXY | ✅ Recommended | Use SOCKS5 proxy to access websites (see format below) |

---

## 🌐 SOCKS5_PROXY Example

socks5://username:password@ip:port

---

## 📬 Telegram Setup Guide

1. Search and message @BotFather to create a Bot, and obtain the TELEGRAM_BOT_TOKEN.
2. Send a message to your own Telegram, then visit the following link (replace <YOUR_TOKEN> with your Bot Token):
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
Open it to view and obtain your chat_id.
3. Add TELEGRAM_BOT_TOKEN and TG_CHAT_ID to your GitHub repository Secrets.

---

## 🚀 Usage Instructions

1. Fork this repository to your own GitHub account.
2. Enter your repository and go to Settings → Secrets and variables → Actions to add the Secrets obtained in the previous step.
3. GitHub Actions will automatically run every three days (10 AM Beijing time), and manual triggering is also supported.

---

## 💡 Acknowledgements

- Thanks to the author of the curl_cffi library, which is used in the project to simulate real browser requests.
