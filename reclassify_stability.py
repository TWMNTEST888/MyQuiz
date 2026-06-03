#!/usr/bin/env python3
"""
1. 從「船舶操作與船上人員管理」抽出穩度/俯仰差相關題 → 船舶穩度
2. 把「船舶構造」裡的應力計算題（舯拱/舯垂/縱向彎曲/剪切力）→ 船舶穩度
"""
import json

PATH = '/Users/yangjohn/MyQuiz/questions.json'

# ── 從 SOM 抓穩度/俯仰差 ──────────────────────────────────────────────────
SOM_KEYWORDS = [
    # 初穩度/GM/KG/KM 計算
    'KM＝', 'KM=', 'KG＝', 'KG=', 'GM＝', 'GM=', 'BM＝', 'BM=',
    '定傾中心', '定傾高', '初穩度', '穩定中心',
    # 靜穩度曲線
    '靜穩度曲線', 'Statical stability', 'GZ',
    # 自由液面
    '自由液面',
    # 偃息角
    '偃息角', '偃息',
    # 橫傾/扶正
    '橫傾角', '扶正力矩', '傾覆力矩', '傾斜試驗',
    # 排水量/浮力/FWA/TPC
    '淡水修正量', 'FWA', 'DWA', '每公分排水量',
    # 俯仰差/trim
    '俯仰差', '每公分俯仰差', 'MCTC', '浮面中心', '縱傾', '艉俯',
]

# ── 從 船舶構造 移走應力計算題 ───────────────────────────────────────────
STRESS_KEYWORDS = [
    '縱向剪切力', '縱向彎曲', '舯拱', '舯垂', '曲折應力',
]

questions = json.load(open(PATH, encoding='utf-8'))

from_som = []
from_con = []

for q in questions:
    subj = q['subject']
    text = q['question']

    if subj == '船舶操作與船上人員管理':
        if any(kw in text for kw in SOM_KEYWORDS):
            q['subject'] = '船舶穩度'
            q['year']    = '115'
            from_som.append(q)

    elif subj == '船舶構造':
        if any(kw in text for kw in STRESS_KEYWORDS):
            q['subject'] = '船舶穩度'
            q['year']    = '115'
            from_con.append(q)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f'從 SOM 移出: {len(from_som)} 題')
for q in from_som:
    print(f'  [{q["groupId"]}] {q["question"][:70]}')

print(f'\n從 船舶構造 移出（應力）: {len(from_con)} 題')
for q in from_con:
    print(f'  [{q["groupId"]}] {q["question"][:70]}')

print(f'\n合計新增至 船舶穩度: {len(from_som) + len(from_con)} 題')
