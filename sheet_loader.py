import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import (
    SPREADSHEET_ID,
    SHEET_NAME_LECTURE,
    SHEET_NAME_RULES,
    SHEET_NAME_PRINCIPLES,
    GOOGLE_KEY_PATH
)

def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_PATH, scope)
    return gspread.authorize(creds)

def list_available_lectures():
    """RDB_ 교안 워크시트에서 생성 가능한 교안 목록 조회"""
    client = get_gspread_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME_LECTURE)
    rows = ws.get_all_values()

    lectures = []
    # Row 1 is header: ['분류', '유형', '제목', '문장데이터', '분석데이터', '삽화데이터', '저장일시', '아이디']
    for idx, r in enumerate(rows[1:], start=2):
        if len(r) < 5:
            continue
        material_type = r[0] if len(r) > 0 else ""
        doc_type = r[1] if len(r) > 1 else ""
        title = r[2] if len(r) > 2 else ""
        has_sentence = bool(r[3].strip()) if len(r) > 3 else False
        has_analysis = bool(r[4].strip()) if len(r) > 4 else False
        saved_at = r[6] if len(r) > 6 else ""

        lectures.append({
            "row_index": idx,
            "material_type": material_type,
            "doc_type": doc_type,
            "title": title,
            "has_sentence": has_sentence,
            "has_analysis": has_analysis,
            "saved_at": saved_at
        })
    return lectures

def get_lecture_data(row_index: int):
    """특정 행 번호(row_index)의 문장데이터 및 분석데이터 파싱 반환"""
    client = get_gspread_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_NAME_LECTURE)
    row = ws.row_values(row_index)

    material_type = row[0] if len(row) > 0 else ""
    doc_type = row[1] if len(row) > 1 else ""
    title = row[2] if len(row) > 2 else ""
    
    sentence_data = json.loads(row[3]) if len(row) > 3 and row[3].strip() else []
    analysis_data = json.loads(row[4]) if len(row) > 4 and row[4].strip() else {}
    illustration_data = row[5] if len(row) > 5 else ""

    return {
        "row_index": row_index,
        "material_type": material_type,
        "doc_type": doc_type,
        "title": title,
        "sentence_data": sentence_data,
        "analysis_data": analysis_data,
        "illustration_data": illustration_data
    }

def load_lecture_rules():
    """스프레드시트의 '대본규칙' 및 '문장해석원리' 시트 내용을 실시간 로드"""
    client = get_gspread_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    rules_text = ""
    try:
        ws_rules = sh.worksheet(SHEET_NAME_RULES)
        for r in ws_rules.get_all_values():
            filtered = [cell for cell in r if cell.strip()]
            if filtered:
                rules_text += " ".join(filtered) + "\n"
    except Exception as e:
        rules_text = "대본규칙 로드 실패: " + str(e)

    principles_text = ""
    try:
        ws_principles = sh.worksheet(SHEET_NAME_PRINCIPLES)
        for r in ws_principles.get_all_values():
            filtered = [cell for cell in r if cell.strip()]
            if filtered:
                principles_text += " ".join(filtered) + "\n"
    except Exception as e:
        principles_text = "문장해석원리 로드 실패: " + str(e)

    return {
        "rules": rules_text,
        "principles": principles_text
    }

if __name__ == "__main__":
    print("Testing sheet_loader...")
    lectures = list_available_lectures()
    print(f"Total lectures found: {len(lectures)}")
    for l in lectures[:5]:
        print(f"Row {l['row_index']}: [{l['doc_type']}] {l['title']}")
