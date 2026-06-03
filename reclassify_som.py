#!/usr/bin/env python3
"""
把 questions.json 中「船舶操作與船上人員管理」裡屬於船舶構造主題的題目
改為 subject='船舶構造'、year='115'。
"""
import json, re

PATH = '/Users/yangjohn/MyQuiz/questions.json'

# 關鍵字 → 屬於船舶構造（只要命中任一個即歸類）
KEYWORDS = [
    # 船舶尺寸及船型
    '方塊係數', '稜塊係數', '稜形係數', '方形係數',
    # 船舶應力
    '縱向剪切力', '縱向彎曲', '舯拱', '舯垂', '強度甲板', '曲折應力',
    # 貨艙結構
    '之艙壁稱之', '縱向艙壁', 'Torsion Box', 'Torsion box',
    '混合肋骨系統', '混合肋骨', '肋骨系統',
    # 艏艉
    '艏艉結構',
    # 船舶屬具
    '繫栓屬具',
    # 舵及推進器
    '串列螺槳', '螺距', '滑失率', 'Weather Adjustment',
    # 載重線與吃水標誌
    '國際載重線公約', '載重線與水線', '國際載重線證書',
    # 錨與錨鏈
    '錨鏈', '拋錨', '起錨',
]

questions = json.load(open(PATH, encoding='utf-8'))

changed = []
for q in questions:
    if q['subject'] != '船舶操作與船上人員管理':
        continue
    text = q['question']
    if any(kw in text for kw in KEYWORDS):
        q['subject'] = '船舶構造'
        q['year']    = '115'
        changed.append(q)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f'Changed {len(changed)} questions → subject=船舶構造, year=115\n')
for q in changed:
    print(f'  [{q["groupId"]}] {q["question"][:80]}')
