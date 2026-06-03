#!/usr/bin/env python3
"""
補轉 ANS04301（一等船副/船舶操作與船上人員管理）所有缺漏考期，
合併進 questions.json，以 groupId 去重。
"""
import pdfplumber, re, json, os

SUBJECT_NAME = '船舶操作與船上人員管理'
SUBJECT_CODE = 'SOM'
LIB_FOLDER   = './PDF_Library'
OUT_FILE     = './questions.json'

def parse_year_period(folder_name):
    m = re.search(r'^(\d{3})\d(\d{2})', folder_name)
    if m:
        return f"{m.group(1)}-{int(m.group(2))}"
    return folder_name

def convert_pdfs(root):
    new_qs = []
    for dirpath, _, files in os.walk(root):
        if 'ANS04301.pdf' not in files:
            continue
        folder = os.path.basename(dirpath)
        year_label = parse_year_period(folder)
        pdf_path = os.path.join(dirpath, 'ANS04301.pdf')

        current_q = None
        last_group_id = ''
        print(f'  [{year_label}] {pdf_path}')

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line or re.match(r'^第\s*\d+\s*頁$', line):
                            continue

                        q_match = re.match(r'^\(\s*([A-D])\s*\)\s*(\d+)\.\s*(.*)', line)
                        if q_match:
                            if current_q:
                                new_qs.append(current_q)
                            ans, qnum, content = q_match.groups()
                            is_follow = any(kw in content.replace(' ', '')
                                            for kw in ['承上題', '續上題', '同上題'])
                            uid = f'{SUBJECT_CODE}_{year_label}_{qnum}'
                            group_id = last_group_id if (is_follow and last_group_id) else uid
                            if not is_follow:
                                last_group_id = uid

                            img_keywords = ['如圖', '下圖', '圖中', '附圖', '如下圖', '如下所示']
                            has_img = any(kw in content for kw in img_keywords)

                            current_q = {
                                'year':    year_label,
                                'subject': SUBJECT_NAME,
                                'question': f'{qnum}. {content}',
                                'options': {'A': '', 'B': '', 'C': '', 'D': ''},
                                'answer':  ans,
                                'image':   f'img/{SUBJECT_CODE}_{year_label}_{qnum}.png' if has_img else '',
                                'groupId': group_id,
                                '_qnum':   int(qnum),
                                '_state':  'Q',
                            }
                            continue

                        if current_q:
                            opt = re.match(r'^([A-D])\.\s*(.*)', line)
                            if opt:
                                lbl, txt = opt.groups()
                                current_q['options'][lbl] = txt
                                current_q['_state'] = lbl
                            else:
                                if current_q['_state'] == 'Q':
                                    current_q['question'] += ' ' + line
                                elif current_q['_state'] in 'ABCD':
                                    current_q['options'][current_q['_state']] += ' ' + line

                if current_q:
                    new_qs.append(current_q)
                    current_q = None

        except Exception as e:
            print(f'    ERROR: {e}')

    for q in new_qs:
        q.pop('_qnum', None)
        q.pop('_state', None)
    return new_qs

# ── 主程式 ──────────────────────────────────────────────────────────────────
print('掃描 ANS04301 SOM 試卷...')
new_qs = convert_pdfs(LIB_FOLDER)
print(f'掃描完畢，共 {len(new_qs)} 題')

existing = json.load(open(OUT_FILE, encoding='utf-8'))
existing_ids = {q['groupId'] for q in existing}

added = [q for q in new_qs if q['groupId'] not in existing_ids]
print(f'新增（去重後）: {len(added)} 題')

merged = existing + added
merged.sort(key=lambda x: (
    x['subject'],
    x['year'],
    int(re.search(r'_(\d+)$', x['groupId']).group(1))
    if re.search(r'_(\d+)$', x['groupId']) else 0
))

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f'questions.json 更新完成：{len(existing)} → {len(merged)} 題')

# 確認 SOM 題數
som_total = sum(1 for q in merged if q['subject'] == SUBJECT_NAME)
print(f'SOM 科目現有: {som_total} 題')
