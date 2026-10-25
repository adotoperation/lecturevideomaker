import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SCRIPTS_DIR = os.path.join(OUTPUT_DIR, "scripts")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
VIDEOS_DIR = os.path.join(OUTPUT_DIR, "videos")

for d in [ASSETS_DIR, OUTPUT_DIR, SCRIPTS_DIR, AUDIO_DIR, VIDEOS_DIR]:
    os.makedirs(d, exist_ok=True)

# Google Spreadsheet & Drive Configuration
SPREADSHEET_ID = "1W9975c52Y8GQ748Jvv4CiK64muT_l7JtAEfjmXCRBww"
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
GOOGLE_SLIDES_URL = "https://docs.google.com/presentation/d/1D_VcwBzmWmTjXV2cRIZUNffHxwruekiUzSTrTZrTV8A/edit"

SHEET_NAME_LECTURE = "RDB_ 교안"
SHEET_NAME_PASSAGE = "RDB_지문"
SHEET_NAME_RULES = "대본규칙"
SHEET_NAME_PRINCIPLES = "문장해석원리"

# Google Service Account Key (프로젝트 내부 키 우선 탐색)
GOOGLE_KEY_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(BASE_DIR, "google-key.json")
    if os.path.exists(os.path.join(BASE_DIR, "google-key.json"))
    else r"c:\Users\stone\Desktop\workspace\adot-workflow\backend\google-key.json"
)

# Google Cloud Text-to-Speech Service Account Key (ttsmaker key)
GOOGLE_TTS_KEY_PATH = (
    os.path.join(BASE_DIR, "ttsmaker-key.json")
    if os.path.exists(os.path.join(BASE_DIR, "ttsmaker-key.json"))
    else r"C:\Users\stone\Downloads\ttsmaker-499105-761edd14dfce.json"
)
GOOGLE_CLOUD_TTS_VOICE = "ko-KR-Neural2-A"  # ko-KR-Neural2-A, ko-KR-Neural2-B, ko-KR-Neural2-C, ko-KR-Wavenet-A

# Google Drive Target Folder for lecture videos
GDRIVE_TARGET_FOLDER_ID = "1ACmmG-77ycbPwLXgu8vrK3bSOaeNKHtO"

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AIzaSyC7sBdTtPsQ7Zmnh3MUHzXBkSXgdmLlWm8"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

# TTS Voice Preference ("auto", "google_cloud", "gemini", "edge_tts")
TTS_PREFERRED_ENGINE = "gemini"
GEMINI_TTS_VOICE = "Aoede"  # Aoede (여성, 명확하고 또렷한 설명형 톤)
DEFAULT_TTS_VOICE = "ko-KR-SunHiNeural"

# Teacher Video PIP Source (assets 폴더 또는 output 폴더)
TEACHER_VIDEO_SOURCE = (
    os.path.join(ASSETS_DIR, "teacher_pip_circle.mp4")
    if os.path.exists(os.path.join(ASSETS_DIR, "teacher_pip_circle.mp4"))
    else os.path.join(OUTPUT_DIR, "teacher_pip_circle.mp4")
)
TEACHER_PIP_CIRCLE = TEACHER_VIDEO_SOURCE
PIP_MASK_CIRCLE = (
    os.path.join(ASSETS_DIR, "pip_mask_circle.png")
    if os.path.exists(os.path.join(ASSETS_DIR, "pip_mask_circle.png"))
    else os.path.join(OUTPUT_DIR, "pip_mask_circle.png")
)
PIP_RING_CIRCLE = (
    os.path.join(ASSETS_DIR, "pip_ring_circle.png")
    if os.path.exists(os.path.join(ASSETS_DIR, "pip_ring_circle.png"))
    else os.path.join(OUTPUT_DIR, "pip_ring_circle.png")
)

# 칠판 디자인 테마 (구글 슬라이드 양식)
BOARD_BG_COLOR = (20, 56, 39)       # 딥 다크 초록 칠판 (#143827)
WOOD_FRAME_COLOR = (62, 39, 35)     # 클래식 다크 마호가니 나무 프레임 (#3E2723)
PILL_BG_COLOR = (25, 68, 48)        # 헤더 카드 배경 (#194430)
PILL_BORDER_COLOR = (52, 120, 82)   # 헤더 카드 테두리 (#347852)
YELLOW_TEXT_COLOR = (253, 224, 71)  # 칠판 노란 분필 (#FDE047)
WHITE_TEXT_COLOR = (248, 250, 252)  # 칠판 흰색 분필 (#F8FAFC)
VERB_ROSE_COLOR = (248, 113, 113)   # 동사 및 Vt/Vi 로즈핑크 (#F87171)
SKY_BLUE_COLOR = (56, 189, 248)     # 주어/목적어 강조 (#38BDF8)
