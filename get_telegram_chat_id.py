#!/usr/bin/env python3
"""
取得 Telegram chat_id 的小工具。
使用前請先傳任意訊息給你的 bot，再執行此腳本。
"""
import urllib.request, json

TELEGRAM_BOT_TOKEN = "7974393551:AAEB4DSvcoLl2OBhJWT6i8pHlyBVQGT5rLg"

if not TELEGRAM_BOT_TOKEN:
    print("請先填入 TELEGRAM_BOT_TOKEN")
else:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())
    if data.get('result'):
        for update in data['result']:
            msg = update.get('message', {})
            chat = msg.get('chat', {})
            print(f"chat_id：{chat.get('id')}  |  名稱：{chat.get('first_name','')} {chat.get('last_name','')}")
    else:
        print("沒有收到訊息，請先在 Telegram 傳一則訊息給你的 bot")
