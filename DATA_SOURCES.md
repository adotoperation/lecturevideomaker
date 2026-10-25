# 📌 AI 강의 메이커 (AI Lecture Maker) 데이터 출처 및 환경 가이드

본 문서는 회사 컴퓨터 또는 다른 환경에서 본 프로젝트를 그대로 복제하여 이어서 작업할 수 있도록 모든 **데이터 출처, 구글 시트/드라이브 링크, 서비스 계정 키, 에셋 위치 및 실행 방법**을 정리한 종합 가이드입니다.

---

## 1. 📊 구글 스프레드시트 (데이터 원천)

- **스프레드시트 URL**: [2026 수능/모의고사 분석 마스터 시트](https://docs.google.com/spreadsheets/d/1W9975c52Y8GQ748Jvv4CiK64muT_l7JtAEfjmXCRBww/edit)
- **스프레드시트 ID (`SPREADSHEET_ID`)**: `1W9975c52Y8GQ748Jvv4CiK64muT_l7JtAEfjmXCRBww`
- **주요 워크시트 구성**:
  1. **`RDB_지문`**:
     - **2026년 고3 6월 32번 지문 데이터 위치**: **Row 96 ~ 103** (문장 1번 ~ 8번)
     - **F열**: 최종 강의 대본 (한글 발음 직독직해, 1.0초 텀 적용)
     - **G열**: 문장 구조 분석 토큰 (JSON 데이터)
     - **H열**: 지문 요약 정보 (문장 1번 행에 주제/핵심어휘/3단요약 메타데이터 저장)
     - **J열**: 파이프라인 처리 상태 (`DONE`)
  2. **`RDB_ 교안`**:
     - 교안 생성 기본 메타데이터 및 분석 연동 데이터
  3. **`대본규칙`**:
     - 4단계 강의 대본 원칙 (1단계 구조분석 직독직해, 2단계 내용맥락, 3단계 핵심문법, 4단계 서술형영작)
  4. **`문장해석원리`**:
     - 에이닷 5개 해석 공식 (주절 하단 밑줄/태그, 종속절·준동사 상단 기호, 거품 소괄호, 준동사 대괄호, 수식 화살표 등)

---

## 2. 📑 구글 슬라이드 (장표 디자인 템플릿)

- **슬라이드 템플릿 URL**: [에이닷 칠판형 슬라이드 템플릿](https://docs.google.com/presentation/d/1D_VcwBzmWmTjXV2cRIZUNffHxwruekiUzSTrTZrTV8A/edit?slide=id.SLIDES_API198451560_0#slide=id.SLIDES_API198451560_0)
- **장표 디자인 규격**:
  - **해상도**: 1920 × 1080 (16:9 FHD)
  - **칠판 테마 배경색**: `#113022` (딥 다크 초록)
  - **외곽 프레임**: `#3E2723` (다크 마호가니 원목)
  - **좌측 상단 알약 카드**: 문항 타이틀 (`2026년 고3 6월 32번`, `#163B2A` 배경 + 노란 분필 폰트)
  - **우측 상단 로고**: `에이닷 영어학원` (흰색 볼드 38px)
  - **폰트 규격**:
    - 영문 본문: Consolas Bold (42~44px)
    - 주절 기호 (단어 아래): 36px (`S`: 파랑 `#60A5FA`, `Vt`: 로즈핑크 `#F87171`, `O`: 에메랄드 `#34D399`)
    - 종속절/준동사 기호 (단어 위): 26px
    - 직독직해 박스 및 해시태그 바: Malgun Gothic Bold

---

## 3. 🔑 구글 서비스 계정 키 (Service Account Key)

- **키 파일명**: `google-key.json`
- **프로젝트 내 위치**: `c:\Users\stone\Desktop\workspace\ai_lecture_maker\google-key.json` (본 프로젝트 루트에 복사 완료)
- **우선순위 로직**:
  - `config.py`에서 프로젝트 폴더 내 `google-key.json`을 1순위로 자동 인식하므로, 다른 컴퓨터로 복사 시 별도 환경변수 설정 없이 즉시 동작합니다.
- **서비스 계정 이메일**: 스프레드시트 접근 권한이 부여된 Google Cloud 서비스 계정
- **구글 드라이브 업로드 타겟 폴더 ID**: `1ACmmG-77ycbPwLXgu8vrK3bSOaeNKHtO`

---

## 4. 👩‍🏫 버튜버 (Avatar) PIP 에셋

- **저장 위치**: `ai_lecture_maker/assets/`
  1. **`teacher_pip_circle.mp4`**: 260 × 260 원형 무음 버튜버 모션 루프 영상
  2. **`pip_mask_circle.png`**: 260 × 260 원형 알파 블렌딩 마스크
  3. **`pip_ring_circle.png`**: 260 × 260 깔끔한 흰색 테두리 링
- `config.py`의 `TEACHER_PIP_CIRCLE`, `PIP_MASK_CIRCLE`, `PIP_RING_CIRCLE`이 자동으로 `assets/` 폴더를 참조하도록 설정되어 있습니다.

---

## 5. 💻 핵심 파이프라인 스크립트 안내

| 파일명 | 역할 및 기능 | 실행 명령 |
| :--- | :--- | :--- |
| **`build_test_2sentences.py`** | **1번·2번 문장 테스트 파이프라인**<br>• 끊어읽기(`/`) + 커진 문장기호(36px/26px)<br>• 하단 `[직독직해 끊어 읽기]` 카드 연동<br>• `▶ #어법중요`, `★ #서술형중요` 동적 해시태그 표출 | `python build_test_2sentences.py` |
| **`build_full_q32_lecture.py`** | **전체 8문장 풀버전 파이프라인**<br>• 표지 ➔ 1~8번 문장 실시간 판서 ➔ 마무리 요약 장표<br>• 1.0초 무음 호흡 텀 + 무손실 병합<br>• 구글 시트 `RDB_지문` Row 96~103 대본 자동 업데이트 | `python build_full_q32_lecture.py` |
| **`progressive_lecture_data.py`** | 전체 8문장 및 요약 장표의 판서 상태 렌더러와 청크 대본 데이터베이스 | 모듈 라이브러리 |
| **`config.py`** | 구글 시트 ID, API 키, 에셋 경로, 색상/폰트 테마 설정 | 설정 파일 |
| **`sheet_loader.py`** | 구글 시트 API 연동 및 `RDB_지문` 데이터 로더/업데이터 | 연동 모듈 |

---

## 6. 🚀 회사 컴퓨터에서 세팅하는 방법 (Quick Start)

1. **프로젝트 폴더 전체 복사**:
   - `ai_lecture_maker` 폴더를 회사 컴퓨터의 원하는 경로에 복사합니다.
   - (`google-key.json`과 `assets/`가 포함되어 있어 추가 다운로드 없이 바로 사용 가능)
2. **파이썬 가상환경 생성 및 의존성 설치**:
   ```bash
   python -m venv venv
   # 윈도우 PowerShell인 경우:
   .\venv\Scripts\Activate.ps1
   # 패키지 설치:
   pip install -r requirements.txt
   ```
3. **강의 생성 실행**:
   - 2문장 테스트 생성:
     ```bash
     python build_test_2sentences.py
     ```
   - 전체 8문장 풀버전 생성:
     ```bash
     python build_full_q32_lecture.py
     ```
   - 생성된 영상은 `output/videos/` 폴더에 즉시 저장됩니다.
