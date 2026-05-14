#!/usr/bin/env python3
"""
從 Firestore 讀取「缺少ABCD選項」的回報，
掃描 PDF_Library 補齊選項，
結果寫入 question_fixes.json（絕不修改 questions.json）。

使用方式：
  python3 fix_questions.py

可由 send_weekly_report.py 自動呼叫，或手動執行。
"""

import pdfplumber
import json
import re
import os
from datetime import datetime

# ── 設定 ──────────────────────────────────────
LIB_FOLDER       = "./PDF_Library"
FIXES_FILE       = "./question_fixes.json"   # 輸出（不動 questions.json）
QUESTIONS_FILE   = "./questions.json"         # 只讀，用來核對
# ──────────────────────────────────────────────

# 科目代號 → PDF 檔案前綴數字（對應 convert_quiz.py 的 PDF_FILE_MAP）
SUBJECT_PREFIX = {
    "NSM": "013",   # 航行安全與氣象
    "NAV": "023",   # 航海學
    "CAR": "033",   # 貨物作業
    "SOM": "043",   # 船舶操作與船上人員管理
    "CNE": "053",   # 船舶通訊與航海英文
    "BRM": "063",   # 駕駛台資源管理（如有）
}


def get_pdf_folder(year_str, period_str):
    """
    groupId NAV_107-1_3 → year_str='107', period_str='1'
    → PDF_Library/107/107101_A/
    """
    year_int   = int(year_str)
    period_int = int(period_str)
    folder_name = f"{year_int}{period_int:02d}01_A"
    return os.path.join(LIB_FOLDER, year_str, folder_name)


def find_subject_pdfs(pdf_folder, subject_code):
    """
    在 pdf_folder 中找到對應科目的所有 PDF 檔案
    例如 NSM → ANS013xx.pdf
    """
    prefix = SUBJECT_PREFIX.get(subject_code, "")
    if not prefix:
        return []
    result = []
    if not os.path.isdir(pdf_folder):
        return []
    for f in os.listdir(pdf_folder):
        if f.upper().startswith(f"ANS{prefix}") and f.lower().endswith(".pdf"):
            result.append(os.path.join(pdf_folder, f))
    return sorted(result)


def extract_options_for_question(pdf_path, target_qnum):
    """
    解析 PDF，找到題號 target_qnum 的選項 A/B/C/D。
    回傳 dict 或 None。
    """
    target = str(target_qnum)
    current_q  = None
    found_q    = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue

                    # 題目行格式：(A) 3. 如圖之海岸線...
                    q_match = re.match(r'^\(\s*([A-D])\s*\)\s*(\d+)\.\s*(.*)', line)
                    if q_match:
                        if current_q and current_q['num'] == target:
                            found_q = current_q
                        _, q_num, _ = q_match.groups()
                        current_q = {'num': q_num, 'options': {'A':'','B':'','C':'','D':''}, 'state': 'Q'}
                        continue

                    if current_q:
                        # 選項行格式：A. 沙岸
                        opt_match = re.match(r'^([A-DΑ-Δ])\.\s*(.*)', line)
                        if opt_match:
                            label, content = opt_match.groups()
                            label_map = {"Α":"A","Β":"B","Γ":"C","Δ":"D"}
                            std = label_map.get(label, label)
                            if std in current_q['options']:
                                current_q['options'][std] = content.strip()
                                current_q['state'] = std
                        elif current_q['state'] in ['A','B','C','D']:
                            current_q['options'][current_q['state']] += ' ' + line

            # 最後一題
            if current_q and current_q['num'] == target:
                found_q = current_q

    except Exception as e:
        print(f"  ⚠️  解析 {os.path.basename(pdf_path)} 出錯：{e}")
        return None

    if not found_q:
        return None

    opts = found_q['options']
    # 確認 A/B/C/D 都有內容才算有效
    if all(opts.get(k, '').strip() for k in ['A','B','C','D']):
        return opts
    # 有部分選項才回傳（讓呼叫端自行判斷）
    if any(opts.get(k, '').strip() for k in ['A','B','C','D']):
        return opts
    return None


def parse_group_id(group_id):
    """NAV_107-1_3 → (code='NAV', year='107', period='1', qnum='3')"""
    m = re.match(r'^([A-Z]+)_(\d+)-(\d+)_(\d+)$', group_id or '')
    if m:
        return m.group(1), m.group(2), m.group(3), m.group(4)
    return None, None, None, None


def load_existing_fixes():
    if os.path.exists(FIXES_FILE):
        with open(FIXES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_fixes(fixes):
    with open(FIXES_FILE, 'w', encoding='utf-8') as f:
        json.dump(fixes, f, ensure_ascii=False, indent=2)
    print(f"✅ 已寫入 {FIXES_FILE}（共 {len(fixes)} 筆修復）")


def get_pending_reports_from_firestore():
    """從 Firestore 讀取 status=pending 且 issues 含「缺少ABCD選項」的回報"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fs

        if not firebase_admin._apps:
            key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serviceAccountKey.json')
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)

        db = fs.client()
        docs = db.collection('reports') \
                 .where('status', '==', 'pending') \
                 .stream()

        reports = []
        for doc in docs:
            d = doc.to_dict()
            if '缺少ABCD選項' in (d.get('issues') or []):
                d['doc_id'] = doc.id
                reports.append(d)
        return reports, db

    except ImportError:
        print("請安裝 firebase-admin：pip3 install firebase-admin")
        return [], None
    except Exception as e:
        print(f"Firestore 讀取失敗：{e}")
        return [], None


def update_firestore_fix(db, group_id, options, doc_ids_to_mark):
    """寫入 Firestore question_fixes，並標記 reports 為 fixed"""
    if not db:
        return
    try:
        from firebase_admin import firestore as fs
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP

        # 寫入修復記錄
        db.collection('question_fixes').document(group_id).set({
            'options':  options,
            'fixedAt':  SERVER_TIMESTAMP,
            'fixedBy':  'auto_script',
            'source':   'PDF_Library'
        })

        # 標記 report 為已修復
        for doc_id in doc_ids_to_mark:
            db.collection('reports').document(doc_id).update({
                'status':   'fixed',
                'fixedAt':  SERVER_TIMESTAMP
            })
    except Exception as e:
        print(f"  ⚠️  Firestore 更新失敗：{e}")


def main():
    print(f"\n{'='*50}")
    print(f"  MyQuiz 選項自動修復腳本")
    print(f"  {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # 載入現有修復記錄
    fixes = load_existing_fixes()
    print(f"📂 已有修復記錄：{len(fixes)} 筆\n")

    # 從 Firestore 取待處理回報
    reports, db = get_pending_reports_from_firestore()
    print(f"📋 待處理回報：{len(reports)} 筆\n")

    if not reports:
        print("✅ 無需處理，結束。")
        return

    # 按 groupId 分組（同一題可能被多人回報）
    by_group = {}
    for r in reports:
        gid = r.get('groupId') or r.get('questionId', '')
        if gid not in by_group:
            by_group[gid] = {'report': r, 'doc_ids': []}
        by_group[gid]['doc_ids'].append(r['doc_id'])

    fixed_count    = 0
    not_found      = 0
    already_fixed  = 0

    for gid, info in by_group.items():
        r = info['report']
        print(f"🔍 處理：{gid}")
        print(f"   科目：{r.get('subject','')} | 年份：{r.get('year','')}")

        # 已有修復記錄就跳過
        if gid in fixes and all(fixes[gid].get('options',{}).get(k,'').strip() for k in 'ABCD'):
            print("   ✓ 已有完整修復記錄，跳過\n")
            already_fixed += 1
            continue

        code, year, period, qnum = parse_group_id(gid)
        if not code:
            print(f"   ❌ 無法解析 groupId：{gid}\n")
            not_found += 1
            continue

        pdf_folder = get_pdf_folder(year, period)
        pdf_files  = find_subject_pdfs(pdf_folder, code)

        if not pdf_files:
            print(f"   ❌ 找不到 PDF：{pdf_folder}/ANS{SUBJECT_PREFIX.get(code,'???')}*.pdf\n")
            not_found += 1
            continue

        print(f"   📄 掃描 {len(pdf_files)} 個 PDF 檔案")
        found_options = None
        for pdf_path in pdf_files:
            opts = extract_options_for_question(pdf_path, qnum)
            if opts:
                found_options = opts
                print(f"   ✅ 在 {os.path.basename(pdf_path)} 找到選項")
                break

        if found_options:
            fixes[gid] = {
                'options': found_options,
                'fixedAt': datetime.now().isoformat(),
                'source':  'PDF_Library'
            }
            update_firestore_fix(db, gid, found_options, info['doc_ids'])
            fixed_count += 1
            for k, v in found_options.items():
                print(f"     {k}. {v[:40]}{'…' if len(v)>40 else ''}")
        else:
            print(f"   ⚠️  PDF 中找不到題號 {qnum} 的選項，需人工確認")
            not_found += 1
        print()

    # 儲存結果
    save_fixes(fixes)

    print(f"\n{'─'*40}")
    print(f"  修復完成：{fixed_count} 題")
    print(f"  未找到：  {not_found} 題（需人工確認）")
    print(f"  已有記錄：{already_fixed} 題（跳過）")
    print(f"{'─'*40}\n")


if __name__ == '__main__':
    main()
