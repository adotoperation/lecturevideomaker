# 🎓 AI 수능/모의고사 영어 강의 영상 제작 시스템 (Lecture Video Maker)

> 에이닷 영어학원의 수능 및 평가원 모의고사 지문을 기반으로, 실제 교재와 100% 일치하는 직독직해 판서와 자연스러운 고품질 단일 성우 AI 해설을 결합한 FHD 칠판 강의 영상을 완전 자동으로 생성하는 파이프라인입니다.

---

## ✨ 핵심 기능

1. **에이닷 정밀 직독직해 판서 렌더링**:
   - 주어(S), 타동사(Vt 두 줄 밑줄), 목적어(O), 보어(SC) 등 정확한 문장 성분 표기
   - 주절 기호 36px, 종속절 기호 26px 및 수식 관계를 나타내는 부드러운 베지어 곡선 화살표
   - 영문 본문의 모든 끊어 읽기 단위마다 노란색 슬래시(`/`) 표기 (종속절, 준동사 내부 포함)
   - 접속사 단어 전체를 감싸는 세모(△) 도형 포괄 표기
   - **학생 필기 유도**: 판서 하단의 텍스트 박스를 비우고, 설명 단계에 따라 영문 위에 직접 `★ 어법 중요`, `★ 서술형 중요` 별표 배지 판서

2. **Google NotebookLM급 고품질 단일 성우 TTS**:
   - Google Gemini 2.5 Studio Aoede (여성, 또렷하고 신뢰감 있는 강의 톤) 단일 성우 100% 고정
   - 프롬프트 최적화로 빠른 응답 시간(청크당 3~6초) 및 음색 흔들림 없는 완벽한 일관성 보장

3. **강사 원형 PIP (Picture-in-Picture)**:
   - 560x560 중심 크롭 및 260x260 리사이즈된 강사 모션 영상(`teacher_pip_circle.mp4`)
   - 칠판 우측 하단 골드 링 테두리 합성

---

## 🚀 빠른 시작 (Quick Start)

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (선택 사항)
Gemini API 키가 `config.py`에 기본 탑재되어 있어 별도 설정 없이 바로 구동 가능합니다.
필요 시 환경변수를 통해 지정할 수 있습니다:
```bash
export GEMINI_API_KEY="your-api-key"
```

### 3. 표지 + 1번 문장 검증 강의 생성
```bash
python build_test_s1_only.py
```
- 출력 결과물: `output/videos/2026_고3_6월_32번_1문장_테스트강의.mp4`

---

## 📁 주요 디렉토리 및 파일 구성

```
├── ANTIGRAVITY.md              # Antigravity AI 인수인계 및 작업 가이드
├── DATA_SOURCES.md             # 스프레드시트 및 원본 교안 데이터 레퍼런스
├── README.md                   # 프로젝트 소개 및 매뉴얼
├── requirements.txt            # 파이썬 의존성 패키지 목록
├── config.py                   # 경로, 스프레드시트, API 키 및 모델 설정
├── tts_engine.py               # Google Gemini 2.5 Aoede 음성 합성 엔진
├── progressive_lecture_data.py # 32번 지문 전체 구문 분석 및 판서 데이터
├── build_test_s1_only.py       # 표지 + 1번 문장 단독 빌드 스크립트
├── build_test_3sentences.py    # 1~3번 문장 빌드 스크립트
├── build_full_q32_lecture.py   # 전체 지문 풀버전 빌드 스크립트
├── assets/                     # 강사 동영상 및 PIP 마스크 리소스
│   ├── teacher_pip_circle.mp4  # 무음 원형 강사 모션 비디오
│   ├── pip_mask_circle.png     # 알파 마스크
│   └── pip_ring_circle.png     # 골드 링 테두리
└── output/                     # 생성된 영상 및 오디오 출력 디렉토리
```

---

## 📖 시스템 아키텍처 및 상세 지침
다른 환경(회사 컴퓨터 등)의 AI 에이전트로 작업을 이어가실 경우 [`ANTIGRAVITY.md`](ANTIGRAVITY.md)를 먼저 확인해 주세요.
