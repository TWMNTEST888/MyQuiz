#!/usr/bin/env python3
"""
每週三晚上 10 點執行：
從 Firestore 讀取 status=pending 的題目回報，發送摘要 Email。

使用方式：
  python3 send_weekly_report.py

設定 Mac 排程：
  crontab -e
  加入：0 22 * * 3 /usr/bin/python3 /Users/yangjohn/MyQuiz/send_weekly_report.py
"""

import urllib.request
import urllib.parse
import json
import os
from datetime import datetime

# ── 設定區（敏感資訊從 config.py 讀取）──────
FIREBASE_PROJECT = "myquiz-443fc"
try:
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID   = ""
# ─────────────────────────────────────────────

def get_firestore_reports():
    """從 Firestore 讀取 pending 的回報記錄"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serviceAccountKey.json')
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        reports_ref = db.collection('reports').where('status', '==', 'pending')
        docs = reports_ref.stream()

        reports = []
        for doc in docs:
            data = doc.to_dict()
            data['doc_id'] = doc.id
            reports.append(data)
        return reports

    except ImportError:
        print("請安裝 firebase-admin：pip3 install firebase-admin")
        return []
    except Exception as e:
        print(f"Firestore 讀取失敗：{e}")
        return []


def build_message(reports):
    """組成 LINE 通知訊息（簡潔格式）"""
    now = datetime.now().strftime("%m/%d %H:%M")

    if not reports:
        return f"\n【MyQuiz 週報】{now}\n✅ 本週無待確認回報"

    missing_options = [r for r in reports if '缺少ABCD選項' in (r.get('issues') or [])]
    missing_images  = [r for r in reports if '缺少圖示'     in (r.get('issues') or [])]

    lines = [f"\n【MyQuiz 週報】{now}",
             f"共 {len(reports)} 筆待人工確認\n"]

    if missing_options:
        lines.append(f"📝 缺少選項（{len(missing_options)} 題）")
        for r in missing_options[:5]:   # 最多顯示 5 筆
            code = r.get('subjectCode', '')
            year = r.get('year', '')
            qnum = r.get('questionNum', '')
            subj = r.get('subject', '')
            lines.append(f"  • {subj} {year} 題{qnum} [{code}]")
        if len(missing_options) > 5:
            lines.append(f"  …另 {len(missing_options)-5} 題")
        lines.append("")

    if missing_images:
        lines.append(f"🖼️  缺少圖示（{len(missing_images)} 題）")
        for r in missing_images[:5]:
            gid  = r.get('groupId', '')
            subj = r.get('subject', '')
            lines.append(f"  • {subj} {gid}")
        if len(missing_images) > 5:
            lines.append(f"  …另 {len(missing_images)-5} 題")
        lines.append("")

    lines.append("🔗 查看完整回報：")
    lines.append(f"https://console.firebase.google.com/project/{FIREBASE_PROJECT}/firestore/data/reports")

    return "\n".join(lines)


def send_telegram(message):
    """透過 Telegram Bot 傳送訊息"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  請設定 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
        print("\n取得方式：")
        print("  1. 在 Telegram 搜尋 @BotFather → /newbot → 拿到 token")
        print("  2. 傳任意訊息給你的 bot")
        print("  3. 執行：python3 get_telegram_chat_id.py 拿到 chat_id")
        print("\n--- 訊息預覽 ---")
        print(message)
        return

    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       message,
            "parse_mode": "HTML"
        }).encode('utf-8')
        req = urllib.request.Request(
            url, data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            if result.get('ok'):
                print("✅ Telegram 訊息已送出")
            else:
                print(f"⚠️  Telegram 回應：{result}")
    except Exception as e:
        print(f"❌ Telegram 發送失敗：{e}")


def run_auto_fix():
    """先執行自動修復腳本"""
    import subprocess, sys
    fix_script = os.path.join(os.path.dirname(__file__), 'fix_questions.py')
    if os.path.exists(fix_script):
        print(f"[{datetime.now()}] 執行自動修復...")
        result = subprocess.run([sys.executable, fix_script], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)


def main():
    # 1. 先執行自動修復（掃描 PDF 補齊選項）
    run_auto_fix()

    # 2. 再讀取剩餘 pending 的回報（自動修復後還剩的才需人工）
    print(f"[{datetime.now()}] 開始讀取回報記錄...")
    reports = get_firestore_reports()
    print(f"  找到 {len(reports)} 筆待人工確認")

    message = build_message(reports)
    send_telegram(message)


if __name__ == '__main__':
    main()
