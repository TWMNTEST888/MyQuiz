import json

def find_incomplete_questions():
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        incomplete_list = []
        
        for q in questions:
            opts = q.get('options', {})
            # 檢查 A, B, C, D 只要有一個是空字串，就判定為不完整
            is_empty = any(not str(opts.get(letter, "")).strip() for letter in ['A', 'B', 'C', 'D'])
            
            if is_empty:
                incomplete_list.append({
                    "id": q.get('groupId'),
                    "year": q.get('year'),
                    "text": q.get('question')[:25] + "..."
                })

        if incomplete_list:
            print(f"📢 總共發現 {len(incomplete_list)} 題選項不完整：")
            print("="*40)
            for item in incomplete_list:
                print(f"📍 題號 ID: {item['id']} ({item['year']})")
                print(f"   內容: {item['text']}")
                print("-" * 20)
            print("="*40)
            print("💡 建議：請至 questions.json 搜尋上述 ID，並對照 PDF 手動補齊選項。")
        else:
            print("✅ 檢查完畢！所有題目看起來都有完整的選項。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    find_incomplete_questions()