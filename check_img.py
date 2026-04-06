import json
import os

# --- 設定 ---
JSON_FILE = "questions.json"
IMG_FOLDER = "./img"

def check_status():
    if not os.path.exists(JSON_FILE):
        print(f"❌ 找不到 {JSON_FILE}，請先執行主程式。")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. 篩選出所有「需要圖片」的題目
    required_images = [q for q in data if q["image"] != ""]
    
    # 2. 獲取目前 img 資料夾內已有的檔案名稱
    if not os.path.exists(IMG_FOLDER):
        os.makedirs(IMG_FOLDER)
    existing_files = set(os.listdir(IMG_FOLDER))

    missing = []
    done = []

    for q in required_images:
        # q["image"] 格式為 "img/NAV_113-1_16.png"
        file_name = os.path.basename(q["image"])
        
        if file_name in existing_files:
            done.append(file_name)
        else:
            missing.append({
                "file": file_name,
                "subject": q["subject"],
                "year": q["year"],
                "q_text": q["question"][:30] + "..."  # 只取前30字方便閱讀
            })

    # --- 輸出報告 ---
    print("=" * 50)
    print(f"📊 圖片進度報告")
    print(f"✅ 已完成截圖: {len(done)} 題")
    print(f"❌ 待截圖總數: {len(missing)} 題")
    print("=" * 50)

    if missing:
        print("\n👇 以下是尚未截圖的清單（請依此檔名存檔）：")
        # 按科目排序，方便你開同一個 PDF 一次截完
        missing.sort(key=lambda x: (x['subject'], x['year']))
        
        current_sub = ""
        for m in missing:
            if m['subject'] != current_sub:
                print(f"\n--- 【{m['subject']}】 ---")
                current_sub = m['subject']
            print(f"  [ ] {m['file']}  <- {m['q_text']}")
    else:
        print("\n✨ 太棒了！所有圖片都已備齊！")

if __name__ == "__main__":
    check_status()