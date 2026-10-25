# 🚀 Antigravity 핸드오버 가이드 (Handover Guide)

> **안내**: 이 문서는 회사 컴퓨터 또는 다른 환경의 Google Antigravity AI가 이 레포지토리를 열었을 때, 이전 작업 맥락과 제작 규칙을 100% 이해하고 즉시 이어서 개발할 수 있도록 작성된 프로젝트 시스템 가이드입니다.

---

## 📌 1. 프로젝트 개요 (Overview)
- **프로젝트명**: 에이닷 영어학원 AI 칠판 강의 영상 자동 제작 시스템 (`lecturevideomaker`)
- **타겟 지문**: 2026년 고3 6월 모의고사 32번 빈칸 추론 지문 (주제: *비언어적 소통의 중요성과 의도 숨기기의 어려움*)
- **최종 목표**: 수능/모의고사 지문을 입력받아 **교재와 100% 일치하는 직독직해 판서 + 고음질 단일 성우 해설(NotebookLM급) + 원형 강사 PIP 영상**을 FHD(1920x1080) 비디오로 완전 자동 렌더링.

---

## 🎯 2. 검증 완료된 현재 작업 상태 (Current Status)
- **최신 성공 스크립트**: [`build_test_s1_only.py`](build_test_s1_only.py)
  - 표지 오프닝(Intro) + 1번 문장(Sentence 1, 10개 청크) 렌더링 완료.
  - 생성된 비디오: `output/videos/2026_고3_6월_32번_1문장_테스트강의.mp4` (2분 14초, 15.8MB)
  - 소요 시간: 단 89.7초 (초고속 병렬 렌더링).

---

## 📐 3. 핵심 강의 및 판서 규칙 (Must-Follow Rules)

### 1) 판서 영역 정리 (학생 직접 필기 유도)
- **판서 하단 직독직해 카드 및 `#핵심포인트` 바 완전 삭제**:
  - 판서 하단을 가득 채우던 한국어 해석 박스를 제거하여 칠판을 시원하고 넓게 비웠습니다.
  - 강사의 설명에 따라 학생들이 교재에 직접 필기할 수 있는 학습 환경을 조성합니다.
- **영문 본문 끊어 읽기 슬래시(`/`) 표기**:
  - 영문 본문에 끊어 읽는 단위마다 노란색 슬래시(` / `) 표기.
  - 주절뿐만 아니라 **종속절, 준동사(by observing / their nonverbal behaviors 등) 내부에도 슬래시를 추가**.
- **구문 기호 크기 및 위치 규격**:
  - **주절 기호**: 36px 굵은 폰트, 단어 하단 밑줄 + 기호(S, Vt 두 줄 밑줄, O, C 등).
  - **종속절 기호**: 26px 폰트, 단어 상단에 기호 배치.
  - **수식 관계**: 부드러운 3차 베지어 곡선 화살표(`draw_modifier_arrow_safe`)로 선행사를 지목.
  - **접속사 세모(△)**: 접속사 단어(and, that, as 등)를 완전히 둘러싸며 포괄하는 하늘색 삼각형(`draw_encompassing_triangle`).

### 2) 어법 및 서술형 중요 별표(★) 배지 표기
- **어법 중요 단계**:
  - 설명하는 문법 요소(예: `don't always`, `that's important` 등) 바로 상단에:
  - `★ 어법 중요: not always (부분부정)`, `★ 어법 중요: everything 단수 수일치 is`
  - 코랄/로즈 분필 배지(`draw_important_badge(..., badge_type='grammar')`)로 별표와 함께 표기.
- **서술형 중요 단계**:
  - 영작 핵심 구문(예: `put A into words` 구동사 + 관계대명사절) 전체를 감싸는 황금색 강조 테두리 박스 형성.
  - 구문 상단에 `★ 서술형 중요: [put A into words] 구동사 + 관계대명사 후치수식` 황금색 배지(`badge_type='writing'`) 표기.

---

## 🎙️ 4. TTS 음성 엔진 핵심 노하우 (Google NotebookLM 스타일)

### 1) Gemini 2.5 Studio Aoede 100% 단일 성우 유지 원리
- 모델: `gemini-2.5-flash-preview-tts` (Voice: `Aoede`, 여성 명확한 설명형 톤)
- **낭독 프롬프트 접두어 필수**:
  ```python
  prompt_text = f"다음 한국어 문장을 또렷하게 낭독하세요:\n\n{text}"
  ```
  > **[중요]** 텍스트만 전달할 경우 모델이 텍스트 모드로 오인하여 400 에러를 뱉거나 지연됩니다. 위의 한국어 지시어를 붙이면 지시어는 발화하지 않고 본문 텍스트만 3~6초 만에 200 OK로 반환합니다.
- **Temperature 파라미터 완전 제외**:
  > **[중요]** 음성 합성 API에 `temperature: 0.1` 등을 넘기면 토큰 반복 루프(repetitive decoding)가 발생하여 90초 타임아웃 오류가 발생합니다. `temperature` 파라미터를 아예 생략해야 7초 이내에 안정적으로 합성됩니다.
- **PCM 무음 패딩 트리밍**:
  - Gemini TTS가 반환하는 PCM 끝단의 긴 무음 바이트를 `numpy`로 탐색하여 마지막 음성 + 0.25초 지점에서 깔끔하게 컷오프.
- **단일 성우 보장**:
  - `tts_engine.py`에서 `preferred_engine == "gemini"` 모드일 때는 Edge-TTS로의 fallback을 원천 차단하여 다른 목소리가 섞이지 않습니다.

---

## 👤 5. 강사 원형 PIP (Picture-in-Picture)
- **영상 소스**: [`assets/teacher_pip_circle.mp4`](assets/teacher_pip_circle.mp4) (212KB)
  - 사용자가 제공한 원본 강사 영상(`gemini_generated_video_2447ddbb`)에서 오디오를 제거하고 인물 중심으로 260x260 원형 크롭한 최적화 영상.
- **합성 마스크 및 링**:
  - [`assets/pip_mask_circle.png`](assets/pip_mask_circle.png) (알파 마스크)
  - [`assets/pip_ring_circle.png`](assets/pip_ring_circle.png) (골드 테두리 링)
- **화면 배치**:
  - 1920x1080 해상도 우측 하단 `(1590, 760)` 위치에 오버레이.

---

## 📂 6. 데이터 출처 및 캐시 (Data Sources)
1. **Google Spreadsheet**:
   - ID: `1W9975c52Y8GQ748Jvv4CiK64muT_l7JtAEfjmXCRBww`
   - URL: https://docs.google.com/spreadsheets/d/1W9975c52Y8GQ748Jvv4CiK64muT_l7JtAEfjmXCRBww/edit
   - 주요 탭: `RDB_ 교안`, `RDB_지문`, `대본규칙`, `문장해석원리`
2. **Google Slides Template**:
   - URL: https://docs.google.com/presentation/d/1D_VcwBzmWmTjXV2cRIZUNffHxwruekiUzSTrTZrTV8A/edit
3. **로컬 데이터 덤프 (오프라인에서도 즉시 구동 가능)**:
   - [`preview_q32.txt`](preview_q32.txt): 32번 지문 교안 전체 텍스트 덤프
   - [`output_q32_processed.json`](output_q32_processed.json): 전처리된 문장별 직독직해 JSON 데이터
   - [`google_slides_dump.txt`](google_slides_dump.txt): 구글 슬라이드 레이아웃 분석 덤프
   - [`DATA_SOURCES.md`](DATA_SOURCES.md): 데이터 상세 레퍼런스

---

## ⚡ 7. 실행 방법 (Quick Start)

### 가상환경 및 패키지 설치
```bash
pip install -r requirements.txt
```

### 테스트 강의 (표지 + 1번 문장) 생성
```bash
py build_test_s1_only.py
```
결과 비디오는 `output/videos/2026_고3_6월_32번_1문장_테스트강의.mp4`로 출력됩니다.

### 다음 단계 작업 시 안내 (Next Steps)
- 2번 문장 ~ 7번 문장으로 확장할 경우 [`progressive_lecture_data.py`](progressive_lecture_data.py)의 문장별 데이터 구조를 바탕으로 `build_full_q32_lecture.py`를 실행하거나 확장하면 됩니다.
- 모든 스크립트는 `build_test_s1_only.py`의 최신 판서 배지(`draw_important_badge`), 슬래시(`/`), 낭독 프롬프트 로직을 동일하게 계승합니다.
