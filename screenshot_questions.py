#!/usr/bin/env python3
"""Extract question screenshots from exam PDFs."""

import fitz
import re
import os
import sys

PDF_BASE = "/Users/yangjohn/MyQuiz/PDF_Library"
IMG_OUT = "/Users/yangjohn/MyQuiz/img"

SUBJECT_PDF = {
    "NAV": "ANS02301",
    "NSM": "ANS01301",
    "CNE": "ANS05301",
    "CAR": "ANS03301",
    "SOM": "ANS04301",
}

QUESTIONS = [
    # NAV
    "NAV_107-1_3", "NAV_107-3_5", "NAV_107-4_9",
    "NAV_108-1_12", "NAV_108-3_23",
    "NAV_109-2_17", "NAV_109-2_23", "NAV_109-4_21",
    "NAV_110-3_28", "NAV_110-4_15", "NAV_110-4_16",
    "NAV_111-1_10", "NAV_111-1_12", "NAV_111-2_5",
    "NAV_111-3_16", "NAV_111-3_17",
    "NAV_112-3_13",
    "NAV_113-1_3", "NAV_113-1_18", "NAV_113-1_24",
    "NAV_113-2_2", "NAV_113-2_7",
    "NAV_113-3_17", "NAV_113-3_19",
    # NSM
    "NSM_107-1_36", "NSM_107-1_38",
    "NSM_107-2_28", "NSM_107-2_30", "NSM_107-2_36",
    "NSM_107-3_13", "NSM_107-3_31", "NSM_107-3_33",
    "NSM_107-4_29", "NSM_107-4_33", "NSM_107-4_37",
    "NSM_108-1_30",
    "NSM_108-2_14", "NSM_108-2_15", "NSM_108-2_16",
    "NSM_108-3_13", "NSM_108-3_31", "NSM_108-3_37",
    "NSM_108-4_32",
    "NSM_109-2_17", "NSM_109-2_24",
    "NSM_109-3_8", "NSM_109-3_32",
    "NSM_109-4_13", "NSM_109-4_39",
    "NSM_110-1_10", "NSM_110-1_36",
    "NSM_110-3_16", "NSM_110-3_38",
    "NSM_110-4_12",
    "NSM_111-1_8", "NSM_111-1_10", "NSM_111-1_21",
    "NSM_111-2_19", "NSM_111-2_23", "NSM_111-2_39",
    "NSM_111-3_27", "NSM_111-3_30", "NSM_111-3_40",
    "NSM_112-1_33",
    "NSM_112-2_11", "NSM_112-2_31", "NSM_112-2_36", "NSM_112-2_39",
    "NSM_112-3_6", "NSM_112-3_32",
    "NSM_112-4_10", "NSM_112-4_35", "NSM_112-4_39",
    "NSM_113-1_9", "NSM_113-1_11", "NSM_113-1_15", "NSM_113-1_16",
    "NSM_113-1_31", "NSM_113-1_32",
    "NSM_113-2_6", "NSM_113-2_14", "NSM_113-2_15", "NSM_113-2_24",
    "NSM_113-3_28", "NSM_113-3_32",
    "NSM_113-4_16", "NSM_113-4_29", "NSM_113-4_32",
    "NSM_114-1_39",
    "NSM_114-2_6",
    "NSM_114-3_9", "NSM_114-3_11", "NSM_114-3_37",
    # CNE
    "CNE_109-3_2", "CNE_111-4_2", "CNE_112-1_3",
    "CNE_113-1_3", "CNE_113-3_2",
    # CAR
    "CAR_107-4_19",
    "CAR_108-1_4", "CAR_108-2_1", "CAR_108-2_20", "CAR_108-2_24",
    "CAR_108-4_15", "CAR_108-4_20",
    "CAR_109-2_3", "CAR_109-2_38", "CAR_109-4_38",
    "CAR_110-1_23",
    "CAR_110-3_7", "CAR_110-3_10", "CAR_110-3_11",
    "CAR_110-3_13", "CAR_110-3_24",
    "CAR_111-3_4", "CAR_111-4_2",
    "CAR_112-3_6", "CAR_112-3_24",
    "CAR_112-4_3",
    "CAR_113-4_9",
]

Q_PATTERN = re.compile(r'^\s*[\(\（]\s*[A-D]\s*[\)\）]\s*(\d+)\.', re.MULTILINE)


def get_pdf_path(subject, year_exam):
    year, exam = year_exam.split("-")
    folder = f"{year}1{int(exam):02d}_A"
    pdf_name = SUBJECT_PDF[subject] + ".pdf"
    return os.path.join(PDF_BASE, year, folder, pdf_name)


def find_question_crop(doc, question_num):
    """Return (page_num, fitz.Rect) for the given question number."""
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        if not re.search(rf'[\(\（]\s*[A-D]\s*[\)\）]\s*{question_num}\.', text):
            continue

        # Collect text line positions and image block positions
        q_positions = {}  # qnum -> y_top_of_line
        all_blocks = page.get_text("dict")["blocks"]

        for block in all_blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                line_text = "".join(s["text"] for s in line["spans"])
                m = re.match(r'\s*[\(\（]\s*[A-D]\s*[\)\）]\s*(\d+)\.', line_text)
                if m:
                    qnum = int(m.group(1))
                    q_positions[qnum] = line["bbox"][1]

        if question_num not in q_positions:
            continue

        sorted_qs = sorted(q_positions.keys())
        q_idx = sorted_qs.index(question_num)
        y_q = q_positions[question_num]

        # Top: go back 80pt to catch any figure placed above the question text,
        # but don't cross into the previous question's text body.
        if q_idx > 0:
            y_prev = q_positions[sorted_qs[q_idx - 1]]
            top = max(y_q - 80, (y_prev + y_q) / 2)
        else:
            top = max(0.0, y_q - 30)

        # Bottom: just before the next question starts.
        if q_idx < len(sorted_qs) - 1:
            y_next = q_positions[sorted_qs[q_idx + 1]]
            bottom = y_next - 5
        else:
            bottom = page.rect.height - 20

        return page_num, fitz.Rect(0, top, page.rect.width, bottom)

    return None, None


def screenshot_question(tag, force=False):
    parts = tag.split("_")
    subject = parts[0]
    year_exam = parts[1]
    qnum = int(parts[2])
    out_path = os.path.join(IMG_OUT, tag + ".png")

    if os.path.exists(out_path) and not force:
        print(f"  SKIP (exists): {tag}.png")
        return True

    pdf_path = get_pdf_path(subject, year_exam)
    if not os.path.exists(pdf_path):
        print(f"  ERROR: PDF not found: {pdf_path}")
        return False

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  ERROR opening {pdf_path}: {e}")
        return False

    page_num, crop_rect = find_question_crop(doc, qnum)
    if page_num is None:
        print(f"  ERROR: Q{qnum} not found in {pdf_path}")
        return False

    page = doc[page_num]
    mat = fitz.Matrix(2, 2)  # 2× for readable resolution
    pix = page.get_pixmap(matrix=mat, clip=crop_rect)
    pix.save(out_path)
    print(f"  OK: {tag}.png  ({pix.width}×{pix.height})")
    return True


def main():
    force = "--force" in sys.argv
    os.makedirs(IMG_OUT, exist_ok=True)

    ok = fail = skip = 0
    for tag in QUESTIONS:
        result = screenshot_question(tag, force=force)
        if result is True:
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} saved, {fail} failed")


if __name__ == "__main__":
    main()
