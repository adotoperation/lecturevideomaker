import os
import sys
import json
import re
import time
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Add adopting paths
sys.path.append(r"c:\Users\stone\Desktop\workspace\adotlecturemaker")
from parser_engine import (
    EXPERT_PERSONA_PROMPT,
    post_process_adverbs,
    extract_vocabulary,
    generate_summary_info_dynamically,
    strip_korean_brackets,
    build_exact_1to1_korean_chunks,
    analyze_clause_structure_dynamically,
    generate_grammar_points_dynamically,
    rule_tokenize,
    generate_oral_test
)

from config import (
    SPREADSHEET_ID,
    GOOGLE_KEY_PATH,
    GEMINI_API_KEY,
    GEMINI_MODEL
)

def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_PATH, scope)
    return gspread.authorize(creds)

def ensure_headers(ws):
    """F1: 대본, G1: 구조분석, H1: 지문요약, J1: 상태 확인 및 설정"""
    try:
        row1 = ws.row_values(1)
        needed = {
            6: "대본",      # F
            7: "구조분석",  # G
            8: "지문요약",  # H
            10: "상태"      # J
        }
        updates = []
        for col_idx, expected_title in needed.items():
            current_val = row1[col_idx - 1] if len(row1) >= col_idx else ""
            if current_val != expected_title:
                updates.append({"col": col_idx, "val": expected_title})

        if updates:
            print("[ensure_headers] Updating header row...")
            for u in updates:
                ws.update_cell(1, u["col"], u["val"])
            print("[ensure_headers] Headers successfully updated!")
    except Exception as e:
        print(f"[ensure_headers] Note: Header update skipped or permission restricted: {e}")


def analyze_structure_with_gemini(sentence_pairs, title=""):
    """
    Gemini 2.5 Flash를 사용하여 문장별 PPT/HTML 구문분석 데이터 및 지문 요약 생성
    """
    input_sentences = [p.get('english', '').strip() for p in sentence_pairs if p.get('english', '').strip()]
    input_korean_sentences = [p.get('korean', '').strip() for p in sentence_pairs if p.get('english', '').strip()]
    passage = " ".join(input_sentences)
    korean_passage = "\n".join(input_korean_sentences)

    numbered_sentences_text = "\n".join([f"[문장 {i+1}] {s}" for i, s in enumerate(input_sentences)])
    numbered_kr_text = "\n".join([f"[문장 {i+1} 해석] {s}" for i, s in enumerate(input_korean_sentences)])

    user_input_prompt = f"""
[분석 대상 영어 문장 목록 (총 {len(input_sentences)}개 문장 - 중복 복제 엄금!)]
{numbered_sentences_text}

[한글 해석 문장 목록]
{numbered_kr_text}

[★필수 요청 사항★]
1. 위 목록에 제공된 [문장 1]부터 [문장 {len(input_sentences)}]까지 각각을 'sentences' 배열에 1:1로 정확하게 작성하십시오.
2. 절대로 앞 문장의 tokens나 구문 분석을 다음 문장에 복사(Duplicate)하지 마십시오!
3. 각 sentences 항목의 "original" 필드는 반드시 해당 번호의 원문 텍스트와 완벽히 일치해야 합니다.
4. `chunk_korean` 한글 직독직해에는 괄호 `()`, `[]`를 쓰지 말고 슬래시 `/`만 사용할 것.
5. 절 내부에도 슬래시 {{"text": " / ", "color": "purple"}} 끊어읽기 토큰을 분리 삽입할 것.
6. summary_info에는 subject, keywords, summary(3단 요약: 핵심 요인, 전개/문제, 결론), title_en, illustration_scene_en을 필수로 생성할 것.
"""

    payload = {
        "system_instruction": {"parts": [{"text": EXPERT_PERSONA_PROMPT}]},
        "contents": [{"parts": [{"text": user_input_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    print(f"[analyze_structure] Calling Gemini 2.5 Flash for {len(input_sentences)} sentences...")
    t0 = time.time()
    res = requests.post(url, json=payload, timeout=90)
    if res.status_code != 200:
        raise Exception(f"Gemini API Error {res.status_code}: {res.text}")
    print(f"[analyze_structure] Gemini returned in {round(time.time() - t0, 2)}s")

    data = res.json()
    raw_text = data['candidates'][0]['content']['parts'][0]['text']
    parsed_json = json.loads(raw_text, strict=False)

    full_vocab = extract_vocabulary(passage)
    default_summary = generate_summary_info_dynamically(input_sentences, full_vocab, title)
    summary_info = parsed_json.get("summary_info", default_summary)
    sentences = parsed_json.get("sentences", [])

    results = []
    for idx in range(len(input_sentences)):
        orig_sentence = input_sentences[idx]
        raw_kr = input_korean_sentences[idx] if idx < len(input_korean_sentences) else ""
        s_data = sentences[idx] if idx < len(sentences) else {}
        sent_tokens = s_data.get("tokens", [])

        orig_clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', orig_sentence.lower()).strip()
        orig_words = [w for w in orig_clean_text.split() if len(w) >= 2]

        tok_text = " ".join(t.get('text', '') for t in sent_tokens if t.get('text') not in [' / ', ' // '])
        tok_clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', tok_text.lower()).strip()
        tok_words = [w for w in tok_clean_text.split() if len(w) >= 2]

        matched_words = [w for w in orig_words if w in tok_words]
        overlap_ratio = len(matched_words) / max(1, len(orig_words))

        is_duplicate_of_prev = False
        if idx > 0 and len(results) > 0:
            prev_tok_text = " ".join(t.get('text', '') for t in results[idx-1]["tokens"] if t.get('text') not in [' / ', ' // ']).strip().lower()
            if tok_clean_text and tok_clean_text == re.sub(r'[^a-zA-Z0-9\s]', '', prev_tok_text).strip():
                is_duplicate_of_prev = True

        if not sent_tokens or len(sent_tokens) < 3 or overlap_ratio < 0.70 or is_duplicate_of_prev:
            sent_tokens = rule_tokenize(orig_sentence)
            c_struct = analyze_clause_structure_dynamically(orig_sentence, sent_tokens)
            g_pts = generate_grammar_points_dynamically(orig_sentence, sent_tokens)
        else:
            c_struct = s_data.get("clause_structure", "") or analyze_clause_structure_dynamically(orig_sentence, sent_tokens)
            g_pts = s_data.get("grammar_points", "") or generate_grammar_points_dynamically(orig_sentence, sent_tokens)

        raw_chunk_kr = s_data.get("chunk_korean", "")
        ensured_chunk_kr = build_exact_1to1_korean_chunks(sent_tokens, raw_chunk_kr if raw_chunk_kr and not is_duplicate_of_prev else raw_kr)
        w_pts = s_data.get("writing_points", "") or f"[서술형 대비 핵심 구문] {orig_sentence[:45]}..."

        results.append({
            "index": idx + 1,
            "original": orig_sentence,
            "tokens": sent_tokens,
            "chunk_korean": strip_korean_brackets(ensured_chunk_kr),
            "clause_structure": c_struct,
            "detected_structures": s_data.get("detected_structures", []),
            "grammar_points": g_pts,
            "writing_points": w_pts,
            "page_break": False
        })

    raw_vocab = parsed_json.get("vocabulary") or full_vocab
    final_vocab = []
    if isinstance(raw_vocab, list):
        for v in raw_vocab:
            if isinstance(v, dict) and "word" in v and "meaning" in v:
                final_vocab.append(v)
            elif isinstance(v, str):
                final_vocab.append({"word": v, "meaning": ""})

    final_analysis = {
        "title": title,
        "summary_info": summary_info,
        "passage_raw": passage,
        "korean_raw": korean_passage,
        "sentence_count": len(results),
        "sentences": results,
        "vocabulary": final_vocab
    }

    # Post process adverbs
    final_analysis = post_process_adverbs(final_analysis)

    # 1:1 Oral Test Generation
    print("[analyze_structure] Generating 1:1 oral test sheet...")
    try:
        oral_test = generate_oral_test(passage, sentences=results, topic=summary_info.get("subject", ""), api_key=GEMINI_API_KEY)
        final_analysis["oral_test"] = oral_test
    except Exception as e:
        print(f"[analyze_structure] Oral test generation error: {e}")
        final_analysis["oral_test"] = {}

    return final_analysis

def generate_lecture_scripts(analysis_data, title="2026년 고3 6월 모의고사 32번"):
    """
    사용자 확정 대본 규칙에 맞추어 문장별 강의 대본(순수 구어체 TTS 텍스트) 생성
    """
    sentences = analysis_data.get("sentences", [])
    summary_info = analysis_data.get("summary_info", {})
    subject = summary_info.get("subject", "")
    keywords = summary_info.get("keywords", "")
    summary_list = summary_info.get("summary", [])

    system_instruction = f"""
당신은 대한민국 고등학교 내신 및 수능 1타 스타 강사입니다.
[Role & Persona: 20대 후반 ~ 30대 초반 여성 스타 강사]
- 어조 및 태도: 대단히 명쾌하고 깔끔하며, 학생들과 친근하게 호흡하면서도 전문성과 카리스마가 넘치는 1타 강사 스타일.
- 청자 대상: 중학교 및 고등학교 학생들.
- 어미 및 말투 (★반말체 필수★):
  * 반드시 자연스러운 구어체 반말(~야, ~지, ~해, ~거든, ~잖아, ~보자, ~체크해, ~기억해 둬 등)을 사용합니다.
  * 존댓말(~합니다, ~입니다, ~하죠, ~하십시오 등) 절대 금지!
  * 성분 설명 예시: "주어는 이거야.", "주절의 본동사 브이티지.", "3형식이야.", "that절 내부는 2형식이야.", "거품 걷어내기 원칙에 따라 소괄호로 묶어서 날려줘."
- 호칭: 학생들을 부를 때 친근하게 '친구들' 또는 '얘들아'를 사용합니다.
- 절대 금지 사항:
  1. 유치한 은어나 유행어, 비속어 절대 금지 (❌ '쪼개버릴 거야', '뽀개자', '렛츠 고', '꼬우~', '개꿀' 등 절대 사용 금지). 강사의 지적 신뢰감과 품위를 유지할 것.
  2. TTS(음성합성)용 원고이므로 이모티콘(✨, 💗, 😊 등) 절대 사용 금지.
  3. 볼드 마크다운(**텍스트**), 제목 헤더(#, ##) 절대 사용 금지. 순수 텍스트 줄바꿈으로만 출력할 것.
  4. 강의 도중 특정 학원 이름 언급이나 교육과정 자랑 금지.
- 숫자 및 기호 표기:
  TTS 발음을 위해 영문 기호와 숫자는 읽기 편한 한글로 표기합니다.
  (예: S -> 주어 에스, Vt -> 타동사 브이티, Vi -> 자동사 브이아이, O -> 목적어 오, SC -> 보어 에스씨, 32번 -> 삼십이 번, 일형식, 이형식, 삼형식, 사형식, 오형식, 제일법칙, 제이법칙, 제삼법칙, 제사법칙 등).

[문장별 분석 필수 4단계 레이아웃]
모든 문장은 반드시 아래 4단계 흐름을 엄격하게 지킵니다. (각 단계 헤더 표기 준수)

1단계 [구조분석 직독직해]:
- 다른 어떤 설명보다 먼저 무조건 맨 처음 시작합니다.
- 영어를 통째로 다시 읽지 않고, 문장 맨 앞부터 순서대로 끊어가면서 한글 직독직해 의미와 [주절의 주어 / 종속절의 주어 / 주절의 본동사 / 종속절의 동사 / 목적어 / 보어 / 부사구 거품 / 형용사절 수식 역할 / 준동사의 목적어]를 실시간으로 결합하여 설명합니다. (문장 뒤에서 앞으로 역순 해석 절대 금지).
- 성분과 문장 형식을 명확하게 규정합니다: "주어 에스야.", "본동사 브이티야.", "목적어 오야.", "3형식 문장이야."
- '진짜 주어'라는 표현은 쓰지 않고, '주절의 주어', '종속절의 주어', '주절의 본동사', '종속절의 동사'로 부릅니다.
- 수식어구 구분:
  * 부사, 부사구, 부사절: "제이법칙 거품 걷어내기 원칙에 따라 소괄호로 묶어서 제외해." 또는 "소괄호로 묶어서 날려줘."
  * 형용사, 형용사구, 형용사절(관계사절): 보어 역할인지 또는 앞에 있는 어떤 명사를 후치수식하는지 역할을 명확히 밝힙니다. (예: "관계대명사 that에 세모 치고 소괄호로 묶자. 형용사절이니까 앞의 선행사 everything을 꾸며주는 역할을 해.")
- 판서 기호 실시간 언급: 접속사/관계사 세모(△), 부사/전명구/형용사절 소괄호 ( ), 명사절/목적어절 대괄호 [ ]

2단계 [내용 맥락 설명]:
- 해당 문장이 지문 전체 맥락에서 쉽게 말해 무슨 의미인지 명료하게 반말로 1~2문장으로 정리합니다.

3단계 [핵심 문법 출제 포인트]:
- 수일치, 관계사 vs 접속사, 준동사의 태, 가주어-진주어 등 시험에 반드시 출제되는 핵심 포인트를 친절하면서도 똑 부러지게 짚어줍니다.

4단계 [서술형 영작 대비 포인트 (선택적)]:
- 내신 서술형 킬러 문장인 경우 핵심 영작 포인트 및 어순 배열 팁을 설명합니다.

[오프닝 & 클로징 규칙]
- 문장 1 (첫 번째 문장):
  문장 1 대본의 맨 앞에는 반드시 10초 분량의 [제목 장표 오프닝]을 포함해야 합니다.
  예시:
  [제목 장표 오프닝]
  "친구들 안녕! 오늘 같이 볼 지문은 {title}이야. 빈칸 추론 문항이니까 끝까지 집중 바짝 하고 잘 따라와야 해. 자, 그럼 첫 번째 문장부터 바로 들어가 보자!"
  (이후 곧바로 1단계 [구조분석 직독직해]로 연결)
- 마지막 문장 (끝 문장):
  대본 마지막에 친근하고 힘찬 클로징 멘트를 반드시 포함합니다:
  "이상으로 {title}의 모든 문장 분석을 마쳤어! 오늘 배운 내용 꼭 담당 선생님과 일대일 구두테스트로 복습하고 완전히 자기 걸로 만들어야 해. 모두 수고 많았어!"
"""

    prompt = f"""
[강의 정보]
- 제목: {title}
- 지문 주제: {subject}
- 핵심 키워드: {keywords}
- 3단 요약: {json.dumps(summary_list, ensure_ascii=False)}

[분석 대상 문장 목록 (총 {len(sentences)}개)]
{json.dumps([{
    'index': s['index'],
    'original': s['original'],
    'chunk_korean': s.get('chunk_korean'),
    'clause_structure': s.get('clause_structure'),
    'grammar_points': s.get('grammar_points'),
    'writing_points': s.get('writing_points')
} for s in sentences], ensure_ascii=False, indent=2)}

위 {len(sentences)}개 문장 각각에 대해, 지정된 페르소나와 4단계 레이아웃 규칙을 엄격히 준수한 순수 구어체 강의 대본을 생성하십시오.
출력은 반드시 JSON 배열 형태이어야 하며, sentences 배열의 순서대로 {len(sentences)}개의 대본 문자열을 담아야 합니다.

반환 JSON 스키마:
{{
  "scripts": [
    {{
      "index": 1,
      "script": "문장 1 대본 전체 텍스트 (오프닝 포함)"
    }},
    ...
    {{
      "index": {len(sentences)},
      "script": "문장 {len(sentences)} 대본 전체 텍스트 (클로징 포함)"
    }}
  ]
}}
"""

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    print(f"[generate_lecture_scripts] Calling Gemini for {len(sentences)} scripts...")
    t0 = time.time()
    res = requests.post(url, json=payload, timeout=90)
    if res.status_code != 200:
        raise Exception(f"Gemini API Error {res.status_code}: {res.text}")
    print(f"[generate_lecture_scripts] Finished in {round(time.time() - t0, 2)}s")

    raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
    parsed = json.loads(raw_text)
    scripts_list = parsed.get("scripts", [])
    
    # Map index to script
    script_dict = {}
    for item in scripts_list:
        script_dict[item.get("index")] = item.get("script", "").strip()

    return script_dict

def process_question(target_question="32", force=False):
    """
    RDB_지문 워크시트에서 특정 문제번호의 행들을 찾아 대본, 구조분석, 지문요약, 상태를 업데이트
    """
    client = get_gspread_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("RDB_지문")

    print(f"=== [Processing Question {target_question}] ===")
    ensure_headers(ws)

    rows = ws.get_all_values()
    q_rows = []
    for idx, r in enumerate(rows[1:], start=2):
        if len(r) >= 3 and r[2] == str(target_question):
            status = r[9] if len(r) > 9 else ""
            q_rows.append((idx, r, status))

    if not q_rows:
        print(f"No rows found for question {target_question}!")
        return

    print(f"Found {len(q_rows)} rows for question {target_question}.")

    # Check already completed
    all_completed = all(status == "완성" for _, _, status in q_rows)
    if all_completed and not force:
        print(f"Question {target_question} is already marked as '완성'. Use force=True to reprocess.")
        return

    # Extract sentence pairs
    sentence_pairs = []
    for idx, r, status in q_rows:
        sentence_pairs.append({
            "english": r[3] if len(r) > 3 else "",
            "korean": r[4] if len(r) > 4 else ""
        })

    title = f"2026년 고3 6월 모의고사 {target_question}번"
    cached_file = os.path.join(os.path.dirname(__file__), f"output_q{target_question}_processed.json")
    
    if os.path.exists(cached_file) and not force:
        print(f"[Cache Found] Loading pre-generated data from {cached_file}...")
        with open(cached_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        analysis_data = cached_data.get("analysis_data", {})
        # Ensure scripts_dict keys are ints
        scripts_dict = {int(k): v for k, v in cached_data.get("scripts", {}).items()}
    else:
        # Step 1: Generate Structure and Passage Summary
        analysis_data = analyze_structure_with_gemini(sentence_pairs, title=title)
        # Step 2: Generate Sentence Scripts
        scripts_dict = generate_lecture_scripts(analysis_data, title=title)


    # Step 3: Prepare Updates
    # Columns:
    # F (Col 6): 대본
    # G (Col 7): 구조분석 (JSON string)
    # H (Col 8): 지문요약 (JSON string on sentence 1 only, empty for others)
    # J (Col 10): 상태 ("완성")

    sentences = analysis_data.get("sentences", [])
    summary_info = analysis_data.get("summary_info", {})
    if len(sentences) > 0:
        sentences[0]["title_slide"] = {
            "slide_type": "cover",
            "main_title": title,
            "topic_kr": summary_info.get("subject", ""),
            "duration_sec": 10
        }

    passage_summary_json = json.dumps({
        "title": analysis_data.get("title"),
        "title_slide": {
            "slide_type": "cover",
            "main_title": title,
            "topic_kr": summary_info.get("subject", ""),
            "duration_sec": 10
        },
        "summary_info": summary_info,
        "passage_raw": analysis_data.get("passage_raw"),
        "korean_raw": analysis_data.get("korean_raw"),
        "sentence_count": analysis_data.get("sentence_count"),
        "vocabulary": analysis_data.get("vocabulary"),
        "oral_test": analysis_data.get("oral_test")
    }, ensure_ascii=False)

    print("\n[Updating Google Sheets] Writing Columns F, G, H, J...")
    cell_updates = []
    for s_idx, (row_idx, r, _) in enumerate(q_rows):
        sent_num = s_idx + 1
        
        script_text = scripts_dict.get(sent_num, "")
        
        sent_struct = sentences[s_idx] if s_idx < len(sentences) else {}
        struct_json = json.dumps(sent_struct, ensure_ascii=False)
        
        summary_cell_val = passage_summary_json if sent_num == 1 else ""
        status_val = "완성"

        cell_updates.append(gspread.Cell(row_idx, 6, script_text))
        cell_updates.append(gspread.Cell(row_idx, 7, struct_json))
        cell_updates.append(gspread.Cell(row_idx, 8, summary_cell_val))
        cell_updates.append(gspread.Cell(row_idx, 10, status_val))

    sheet_updated = False
    try:
        ws.update_cells(cell_updates)
        print(f"=== Successfully updated Question {target_question} in Google Sheet (Rows {q_rows[0][0]} ~ {q_rows[-1][0]})! ===")
        sheet_updated = True
    except Exception as e:
        print(f"\n[Warning] Could not write to Google Sheet directly ({e})")
        print("Note: The service account 'adot-workflow@adot-workflow.iam.gserviceaccount.com' has 'Viewer' (뷰어) permission.")
        print("To allow automated writing directly to the sheet, please grant 'Editor' (편집자) access on the spreadsheet.")

    # Save to local file
    output_path = os.path.join(os.path.dirname(__file__), f"output_q{target_question}_processed.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "target_question": target_question,
            "sheet_updated": sheet_updated,
            "q_rows": [(r[0], r[1][1], r[1][2], r[1][3]) for r in q_rows],
            "scripts": scripts_dict,
            "analysis_data": analysis_data
        }, f, ensure_ascii=False, indent=2)
    print(f"[Local Save] Full output saved to: {output_path}")

    return {
        "analysis_data": analysis_data,
        "scripts_dict": scripts_dict,
        "q_rows": q_rows,
        "sheet_updated": sheet_updated
    }

def process_all_questions(force=False):
    """
    RDB_지문 워크시트의 모든 문제번호를 순회하며, J열이 '완성'이 아닌 지문만 자동 대량 처리
    """
    client = get_gspread_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet("RDB_지문")
    rows = ws.get_all_values()

    seen_questions = []
    for r in rows[1:]:
        if len(r) >= 3 and r[2].strip() and r[2].strip() not in seen_questions:
            seen_questions.append(r[2].strip())

    print(f"=== [Batch Mode] Found {len(seen_questions)} questions: {seen_questions} ===")
    for q in seen_questions:
        print(f"\n>>> Processing Question {q}...")
        try:
            process_question(q, force=force)
        except Exception as e:
            print(f"Error processing question {q}: {e}")

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    if "--all" in sys.argv:
        process_all_questions(force=force_run)
    else:
        target = "32"
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                target = arg
                break
        result = process_question(target, force=force_run)


