import os
import json
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, SCRIPTS_DIR

def generate_lecture_script(lecture_data: dict, rules_data: dict = None) -> dict:
    """
    분석데이터(analysis_data)와 대본규칙/문장해석원리를 기반으로
    Gemini 2.5 Flash API를 호출하여 구조화된 강의 대본과 판서 액션 타임라인을 생성합니다.
    """
    title = lecture_data.get("title", "영어 내신 지문 분석 강의")
    analysis = lecture_data.get("analysis_data", {})
    sentences = analysis.get("sentences", [])
    
    # 지문 요약 및 키워드 정보
    summary_info = analysis.get("summary_info", {})
    subject = summary_info.get("subject", "")
    keywords = summary_info.get("keywords", "")
    summary_points = summary_info.get("summary", [])

    # 규칙 가져오기
    rules_text = rules_data.get("rules", "") if rules_data else ""
    principles_text = rules_data.get("principles", "") if rules_data else ""

    # 문장별 구문 및 토큰 데이터 간소화 정리
    sentences_payload = []
    for s in sentences:
        s_tokens = []
        for t in s.get("tokens", []):
            if t.get("text", "").strip():
                s_tokens.append({
                    "text": t.get("text", ""),
                    "color": t.get("color", "slate"),
                    "sub_tag": t.get("sub_tag", ""),
                    "top_label": t.get("top_label", ""),
                    "underline": t.get("underline", False),
                    "is_conjunction": t.get("is_conjunction", False)
                })
        
        sentences_payload.append({
            "index": s.get("index"),
            "original": s.get("original"),
            "chunk_korean": s.get("chunk_korean"),
            "clause_structure": s.get("clause_structure"),
            "grammar_points": s.get("grammar_points"),
            "writing_points": s.get("writing_points"),
            "tokens": s_tokens
        })

    system_instruction = f"""
당신은 대한민국 고등학교 내신 및 수능 1타 영어 강사(에이닷 스타일)입니다.
학생들이 강의를 들으며 태블릿 판서를 실시간으로 보는 느낌이 들도록,
주어진 구문 분석 데이터와 규칙에 맞추어 생생하고 확신에 찬 구어체 강의 대본과 실시간 판서 액션 큐(actions)를 생성해야 합니다.

[핵심 규칙 - 절대 준수]
1. 오프닝: "학생 여러분 안녕~! 오늘 날씨만큼 상큼하게 내신 대비 시작해 볼까? 사대 원칙으로 쪼개버릴 거니까 펜 꽉 잡고 따라와! 렛츠 고~!" 스타일로 힘차게 시작.
2. 문장별 5단계 루틴 (영어를 통째로 읽지 않음!):
   - 1단계 [끊어읽기 해석]: 구어체로 직독직해 순서대로 한글로 끊어 읽기. ("이 문장 끊어 읽기 해석해보자! ...")
   - 2단계 [내용 설명]: "무슨 내용이냐면 말이야~" 등 상황을 비유하며 학생 눈높이에서 쉽게 설명.
   - 3단계 [구조 분석]: 사대 원칙(일문장일본동사, 거품걷어내기 등)을 언급하며 주절/종속절/형식 설명. 이때 판서 액션(draw_s, draw_v, draw_triangle, draw_bracket 등)을 지시.
   - 4단계 [문법 포인트]: 지문에 적힌 핵심 어법(수일치, 관계사, 분사구문, 도치 등)을 콕 짚어 설명.
   - 5단계 [서술형 강조]: 서술형 영작으로 출제될 포인트 강조.
3. 지문 최종 요약: 지문의 핵심 주제와 3단 요약을 깔끔하게 정리.
4. 클로징: "담당 쌤과의 일대일 구두테스트 완벽 통과 전까지 방심 금지! 시험 보는 날까지 쌤이 끝까지 달릴 거야! 다음 문항에서 봐, 꼬우~!"

[판서 액션 타입 (actions)]:
- "draw_s": 주어 S 기호 쓰기 + 밑줄
- "draw_v": 동사 V/Vi/Vt 기호 쓰기 + 두줄밑줄
- "draw_o": 목적어 O 기호 쓰기 + 밑줄
- "draw_sc": 보어 SC 기호 쓰기
- "draw_triangle": 접속사/관계사 위에 세모(△) 그리기
- "draw_bracket_round": 전치사구/부사 수식어구에 소괄호 ( ) 묶기
- "draw_bracket_square": 명사절/목적어절에 대괄호 [ ] 묶기
- "draw_slash": 끊어읽기 사선 / 긋기
- "highlight": 빈칸/어법 핵심 단어 형광펜 칠하기
- "note": 단어 위에 한글 뜻 손글씨 메모 노출

출력 형식은 순수한 JSON이어야 합니다.
"""

    user_prompt = f"""
[강의 제목]
{title}

[지문 주제 및 키워드]
- 주제: {subject}
- 키워드: {keywords}
- 3단 요약: {json.dumps(summary_points, ensure_ascii=False)}

[문장별 구문분석 데이터]
{json.dumps(sentences_payload, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 완전한 강의 대본과 각 단계별 판서 액션을 담은 JSON을 생성하세요.

JSON 출력 스키마:
{{
  "title": "{title}",
  "opening": {{
    "narration": "선생님 오프닝 멘트"
  }},
  "sentences": [
    {{
      "sentence_index": 1,
      "original": "문장 원문",
      "steps": [
        {{
          "step_type": "chunk_reading",
          "title": "끊어 읽기 해석",
          "narration": "구어체 끊어읽기 멘트",
          "actions": [
            {{ "type": "draw_slash", "target": "단어 또는 구문", "label": "/" }}
          ]
        }},
        {{
          "step_type": "content_explanation",
          "title": "내용 설명",
          "narration": "쉬운 상황 설명 멘트",
          "actions": []
        }},
        {{
          "step_type": "syntax_analysis",
          "title": "구조 분석",
          "narration": "사대원칙 및 문장 성분 판서 멘트",
          "actions": [
            {{ "type": "draw_triangle", "target": "접속사단어", "label": "△" }},
            {{ "type": "draw_v", "target": "동사단어", "label": "Vi", "underline": true }},
            {{ "type": "draw_s", "target": "주어단어", "label": "S", "underline": true }},
            {{ "type": "draw_bracket_round", "target": "수식어구", "label": "()" }}
          ]
        }},
        {{
          "step_type": "grammar_points",
          "title": "문법 포인트",
          "narration": "핵심 어법 설명 멘트",
          "actions": [
            {{ "type": "highlight", "target": "핵심단어" }},
            {{ "type": "note", "target": "단어", "note_text": "한글뜻" }}
          ]
        }},
        {{
          "step_type": "writing_highlight",
          "title": "서술형 강조",
          "narration": "서술형 영작 암기 멘트",
          "actions": []
        }}
      ]
    }}
  ],
  "summary": {{
    "narration": "지문 전체 엑기스 요약 멘트"
  }},
  "closing": {{
    "narration": "선생님 클로징 및 구두테스트 강조 멘트"
  }}
}}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {"parts": [{"text": system_instruction + "\n\n" + user_prompt}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4
        }
    }

    res = requests.post(url, json=payload, timeout=120)
    if res.status_code != 200:
        raise Exception(f"Gemini API 오류 ({res.status_code}): {res.text}")

    result_json = res.json()
    text_content = result_json["candidates"][0]["content"]["parts"][0]["text"]
    script_data = json.loads(text_content)

    # 로컬 저장
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
    out_path = os.path.join(SCRIPTS_DIR, f"{safe_title}_script.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    return script_data

if __name__ == "__main__":
    from sheet_loader import get_lecture_data, load_lecture_rules
    print("Testing script_generator with Row 4...")
    lecture_data = get_lecture_data(4)
    rules_data = load_lecture_rules()
    script = generate_lecture_script(lecture_data, rules_data)
    print("Script Title:", script.get("title"))
    print("Opening:", script.get("opening", {}).get("narration")[:80])
    print("Sentence 1 Steps count:", len(script.get("sentences", [{}])[0].get("steps", [])))
