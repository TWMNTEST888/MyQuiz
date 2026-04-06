import pdfplumber
import re
import json
import os

# --- 設定區 ---
PDF_FILE_MAP = {
    "ANS01301": "航行安全與氣象",
    "ANS02301": "航海學",
    "ANS03301": "貨物作業",
    "ANS04305": "船舶操作與船上人員管理",
    "ANS05301": "船舶通訊與航海英文"
}

SUBJECT_CODE_MAP = {
    "貨物作業": "CAR",
    "船舶通訊與航海英文": "CNE",
    "航海學": "NAV",
    "航行安全與氣象": "NSM",
    "船舶操作與船上人員管理": "SOM"
}

# 資料夾路徑
LIB_FOLDER = "./PDF_Library" 

def format_year_folder(folder_name):
    # 邏輯：114101 -> 114-1
    match = re.search(r'^(\d{3})\d(\d{2})', folder_name)
    if match:
        year = match.group(1)
        exam_num = str(int(match.group(2)))
        return f"{year}-{exam_num}"
    return folder_name

def scan_and_convert(root_folder):
    all_questions = []
    
    if not os.path.exists(root_folder):
        print(f"❌ 錯誤：找不到資料夾 '{root_folder}'")
        return []

    print(f"🚀 開始掃描路徑: {os.path.abspath(root_folder)}")

    for root, dirs, files in os.walk(root_folder):
        current_dir_name = os.path.basename(root)
        
        for file_name in files:
            file_key = os.path.splitext(file_name)[0].strip()
            
            if not file_name.lower().endswith('.pdf') or file_key not in PDF_FILE_MAP:
                continue
            
            pdf_path = os.path.join(root, file_name)
            year_label = format_year_folder(current_dir_name)
            subject_name = PDF_FILE_MAP[file_key]
            subject_code = SUBJECT_CODE_MAP.get(subject_name, "UNK")
            
            print(f"📄 處理中：【{year_label}】{subject_name}...")
            
            # 用來追蹤題組的變數
            last_assigned_group_id = ""

            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        has_physical_images = len(page.images) > 0
                        page_text = page.extract_text()
                        if not page_text: continue

                        lines = page_text.split('\n')
                        current_q = None

                        for line in lines:
                            line = line.strip()
                            if not line or "--- PAGE" in line: continue

                            # 偵測題目起點 (A) 1. 
                            q_match = re.match(r'^\(\s*([A-D])\s*\)\s*(\d+)\.\s*(.*)', line)
                            if q_match:
                                if current_q:
                                    all_questions.append(current_q)
                                
                                ans_val, q_num, q_content = q_match.groups()
                                
                                # --- 智慧題組邏輯 ---
                                q_text_clean = q_content.replace(" ", "")
                                is_follow_up = any(kw in q_text_clean for kw in ["承上題", "續上題", "同上題"])
                                
                                # 建立此題的唯一 ID (例如 CNE_114-1_20)
                                this_q_unique_id = f"{subject_code}_{year_label}_{q_num}"
                                
                                if is_follow_up and last_assigned_group_id:
                                    # 如果是承上題，沿用上一題的群組 ID
                                    current_group_id = last_assigned_group_id
                                else:
                                    # 如果是新題，開啟新的群組 ID
                                    current_group_id = this_q_unique_id
                                    last_assigned_group_id = this_q_unique_id

                                # 圖片偵測邏輯
                                img_keywords = ["如圖", "下圖", "圖中", "附圖", "如下圖", "如下所示"]
                                text_needs_img = any(kw in q_content for kw in img_keywords)
                                
                                img_path = ""
                                if has_physical_images and text_needs_img:
                                    img_path = f"img/{subject_code}_{year_label}_{q_num}.png"

                                current_q = {
                                    "year": year_label,
                                    "subject": subject_name,
                                    "question": f"{q_num}. {q_content}",
                                    "options": {"A": "", "B": "", "C": "", "D": ""},
                                    "answer": ans_val,
                                    "image": img_path,
                                    "groupId": current_group_id, # 存入智慧 ID
                                    "q_num_int": int(q_num),     # 供內部排序使用
                                    "temp_state": "Q"
                                }
                                continue

                            if current_q:
                                # 選項偵測 (支援希臘字母)
                                opt_match = re.match(r'^([A-DΑ-Δ])\.\s*(.*)', line)
                                if opt_match:
                                    label, content = opt_match.groups()
                                    label_map = {"Α": "A", "Β": "B", "Γ": "C", "Δ": "D"}
                                    std_label = label_map.get(label, label)
                                    current_q["options"][std_label] = content
                                    current_q["temp_state"] = std_label
                                else:
                                    # 文字接續
                                    if current_q["temp_state"] == "Q":
                                        current_q["question"] += " " + line
                                    elif current_q["temp_state"] in ["A", "B", "C", "D"]:
                                        current_q["options"][current_q["temp_state"]] += " " + line
                        
                        if current_q:
                            # 選項圖偵測
                            opts_len = sum(len(str(v).strip()) for v in current_q["options"].values())
                            if opts_len < 4 and has_physical_images and current_q["image"] == "":
                                current_q["image"] = f"img/{subject_code}_{year_label}_{current_q['question'].split('.')[0]}.png"
                            all_questions.append(current_q)
                            current_q = None

            except Exception as e:
                print(f"❌ 讀取 {file_name} 出錯: {e}")

    # 排序邏輯：先分「有無圖片」，再按「年份」，最後按「題號」
    all_questions.sort(key=lambda x: (x["image"] == "", x["year"], x["q_num_int"]))
    return all_questions

if __name__ == "__main__":
    print("--- 程式啟動 ---")
    data = scan_and_convert(LIB_FOLDER)
    
    if data:
        # 清洗資料：移除內部使用的暫存欄位
        for item in data:
            item.pop("temp_state", None)
            item.pop("q_num_int", None)

        with open("questions.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        img_count = sum(1 for d in data if d["image"] != "")
        print("-" * 30)
        print(f"✅ 轉換完成！")
        print(f"📊 總題數：{len(data)}")
        print(f"🖼️  待截圖數：{img_count}")
        print(f"📁 資料已更新至 questions.json")