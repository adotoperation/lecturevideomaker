import os
import sys
import time
import math
import asyncio
import subprocess
from PIL import Image, ImageDraw, ImageFont
import edge_tts
import imageio_ffmpeg
from video_renderer import get_audio_duration
from config import VIDEOS_DIR, TEACHER_PIP_CIRCLE, PIP_MASK_CIRCLE, PIP_RING_CIRCLE, GEMINI_TTS_VOICE, GOOGLE_CLOUD_TTS_VOICE
from tts_engine import synthesize_best_audio

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = GEMINI_TTS_VOICE

# Colors
COLOR_BOARD_BG = (17, 48, 34)       # #113022
COLOR_FRAME_WOOD = (62, 39, 35)     # #3E2723
COLOR_PILL_BG = (22, 59, 42)        # #163B2A
COLOR_PILL_BORDER = (46, 99, 73)    # #2E6349
COLOR_YELLOW = (248, 204, 21)       # #F8CC15
COLOR_WHITE = (255, 255, 255)       # #FFFFFF
COLOR_GRAY = (148, 163, 184)        # #94A3B8

COLOR_S_BLUE = (96, 165, 250)       # Blue #60A5FA (주어 S)
COLOR_V_ROSE = (248, 113, 113)      # Rose Pink #F87171 (동사 Vi/Vt)
COLOR_O_EMERALD = (52, 211, 153)    # Emerald #34D399 (목적어 O)
COLOR_SC_INDIGO = (129, 140, 248)   # Indigo #818CF8 (주격보어 SC)
COLOR_SKY_TRIANGLE = (56, 189, 248) # Sky Blue #38BDF8 (접속사 세모)
COLOR_SLASH = (248, 204, 21)        # 끊어읽기 슬래시 노란색 (#F8CC15)

# Fonts
FONT_CONSOLAS_BOLD = r"C:\Windows\Fonts\consolab.ttf"
FONT_MALGUN_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_MALGUN_REG = r"C:\Windows\Fonts\malgun.ttf"

def get_mono_font(size: int):
    return ImageFont.truetype(FONT_CONSOLAS_BOLD, size)

def get_kr_font(size: int, bold: bool = True):
    p = FONT_MALGUN_BOLD if bold else FONT_MALGUN_REG
    return ImageFont.truetype(p, size)

def render_board_base(title: str = "2026년 고3 6월 32번"):
    width, height = 1920, 1080
    im = Image.new("RGB", (width, height), COLOR_BOARD_BG)
    draw = ImageDraw.Draw(im)

    fw = 16
    draw.rectangle([0, 0, width, fw], fill=COLOR_FRAME_WOOD)
    draw.rectangle([0, height - fw, width, height], fill=COLOR_FRAME_WOOD)
    draw.rectangle([0, 0, fw, height], fill=COLOR_FRAME_WOOD)
    draw.rectangle([width - fw, 0, width, height], fill=COLOR_FRAME_WOOD)

    font_pill = get_kr_font(34, bold=True)
    draw.rounded_rectangle([74, 50, 74 + 430, 142], radius=18, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    draw.text((114, 73), title, fill=COLOR_YELLOW, font=font_pill)

    font_logo = get_kr_font(38, bold=True)
    draw.text((1520, 73), "에이닷 영어학원", fill=COLOR_WHITE, font=font_logo)

    return im

def draw_main_clause_tag(draw, x1, x2, y, tag, color, double_u=False):
    # 폰트 2단계 확대 (36px / 한글 32px)
    has_kr = any(ord(c) > 127 for c in tag)
    font_tag_main = get_kr_font(32, bold=True) if has_kr else get_mono_font(36)
    draw.line([(x1, y + 48), (x2, y + 48)], fill=color, width=3)
    if double_u:
        draw.line([(x1, y + 54), (x2, y + 54)], fill=color, width=2)
    tb = draw.textbbox((0, 0), tag, font=font_tag_main)
    w = tb[2] - tb[0]
    draw.text((x1 + (x2 - x1 - w) // 2, y + (60 if double_u else 54)), tag, fill=color, font=font_tag_main)

def draw_dep_clause_tag(draw, x1, x2, y, tag, color):
    # 폰트 2단계 확대 (26px / 한글 24px)
    has_kr = any(ord(c) > 127 for c in tag)
    font_tag_dep = get_kr_font(24, bold=True) if has_kr else get_mono_font(26)
    tb = draw.textbbox((0, 0), tag, font=font_tag_dep)
    w = tb[2] - tb[0]
    draw.text((x1 + (x2 - x1 - w) // 2, y - 34), tag, fill=color, font=font_tag_dep)

def draw_triangle(draw, x, y, color=COLOR_SKY_TRIANGLE):
    font_triangle = get_kr_font(28, bold=True)
    draw.text((x, y - 32), "△", fill=color, font=font_triangle)

def draw_modifier_arrow_safe(draw, start_x, start_y, end_x, end_y, color=COLOR_WHITE, width=3):
    p0 = (start_x, start_y)
    p1 = (start_x - 18, start_y + 10)
    p2 = (end_x, end_y)

    pts = []
    for i in range(21):
        t = i / 20.0
        x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        pts.append((x, y))

    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)

    dx = pts[-1][0] - pts[-3][0]
    dy = pts[-1][1] - pts[-3][1]
    angle = math.atan2(dy, dx)
    arrow_len = 11
    half_a = math.pi / 5.2
    lx = end_x - arrow_len * math.cos(angle - half_a)
    ly = end_y - arrow_len * math.sin(angle - half_a)
    rx = end_x - arrow_len * math.cos(angle + half_a)
    ry = end_y - arrow_len * math.sin(angle + half_a)
    draw.polygon([(end_x, end_y), (lx, ly), (rx, ry)], fill=color)

def draw_korean_chunk_box(draw, box_x, box_y, box_w, box_h, chunks_list):
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=16, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    font_lbl = get_kr_font(22, bold=True)
    draw.text((box_x + 30, box_y + 18), "[ 직독직해 끊어 읽기 ]", fill=COLOR_YELLOW, font=font_lbl)

    if not chunks_list:
        font_sub = get_kr_font(22, bold=False)
        draw.text((box_x + 30, box_y + 60), "강사의 설명을 들으며 앞에서부터 순서대로 의미 덩어리를 파악해 보세요.", fill=COLOR_GRAY, font=font_sub)
        return

    font_txt = get_kr_font(24, bold=True)
    font_slash = get_mono_font(26)

    cur_x = box_x + 30
    cur_y = box_y + 60
    line_max_x = box_x + box_w - 40

    for idx, (role, meaning) in enumerate(chunks_list):
        chunk_str = f"{role} '{meaning}'" if role else f"'{meaning}'"
        tb = draw.textbbox((0, 0), chunk_str, font=font_txt)
        cw = tb[2] - tb[0]

        if cur_x + cw > line_max_x and cur_x > box_x + 40:
            cur_x = box_x + 30
            cur_y += 38

        draw.text((cur_x, cur_y), chunk_str, fill=COLOR_WHITE, font=font_txt)
        cur_x += cw + 8

        if idx < len(chunks_list) - 1:
            draw.text((cur_x, cur_y - 2), "/", fill=COLOR_SLASH, font=font_slash)
            cur_x += 20

def draw_hashtag_bar(draw, bar_x, bar_y, bar_w, bar_h, mode: str, tags: list):
    if mode == 'grammar':
        bg = (55, 25, 30)
        border = (248, 113, 113)
        badge_text = "▶ #어법중요"
        badge_color = (255, 235, 59)
    elif mode == 'writing':
        bg = (20, 50, 40)
        border = (52, 211, 153)
        badge_text = "★ #서술형중요"
        badge_color = (255, 235, 59)
    else:
        bg = COLOR_PILL_BG
        border = COLOR_PILL_BORDER
        badge_text = "● #학습포인트"
        badge_color = COLOR_YELLOW

    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=16, fill=bg, outline=border, width=2)
    font_badge = get_kr_font(24, bold=True)
    draw.text((bar_x + 30, bar_y + 18), badge_text, fill=badge_color, font=font_badge)

    font_tag = get_kr_font(23, bold=True)
    cur_x = bar_x + 230
    for t in tags:
        tb = draw.textbbox((0, 0), t, font=font_tag)
        tw = tb[2] - tb[0]
        draw.rounded_rectangle([cur_x, bar_y + 12, cur_x + tw + 24, bar_y + bar_h - 12], radius=10, fill=(30, 75, 55), outline=border, width=1)
        draw.text((cur_x + 12, bar_y + 18), t, fill=COLOR_WHITE, font=font_tag)
        cur_x += tw + 35

def render_cover_slide():
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    title = "2026년 고3 6월 모의고사 - 32번 지문"
    topic = "비언어적 소통의 중요성과 의도 숨기기의 어려움"

    font_title = get_kr_font(64, bold=True)
    tb_t = draw.textbbox((0, 0), title, font=font_title)
    tw = tb_t[2] - tb_t[0]
    draw.text(((1920 - tw) // 2, 350), title, fill=COLOR_WHITE, font=font_title)

    font_topic = get_kr_font(32, bold=True)
    tb_top = draw.textbbox((0, 0), topic, font=font_topic)
    top_w = tb_top[2] - tb_top[0]
    box_w = max(1160, top_w + 160)
    box_x = (1920 - box_w) // 2
    draw.rounded_rectangle([box_x, 580, box_x + box_w, 740], radius=24, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    draw.text((box_x + (box_w - top_w) // 2, 638), topic, fill=COLOR_YELLOW, font=font_topic)
    return im

def render_s1_state(state: int) -> Image.Image:
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(44)
    char_w = 24.0
    sx = 100
    y1, y2 = 240, 390

    l1 = "1. Speakers / (don't always) / put / everything (that's important"
    l2 = "   / (to them)) / (into words)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

    # State 1+: S below Speakers
    if state >= 1:
        draw_main_clause_tag(draw, sx + int(3*char_w), sx + int(11*char_w), y1, "S", COLOR_S_BLUE)
    # State 3+: Vt double underline below put
    if state >= 3:
        draw_main_clause_tag(draw, sx + int(31*char_w), sx + int(34*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    # State 4+: O below everything
    if state >= 4:
        draw_main_clause_tag(draw, sx + int(37*char_w), sx + int(47*char_w), y1, "O", COLOR_O_EMERALD)
    # State 5+: that's S, important SC, arrow
    if state >= 5:
        draw_dep_clause_tag(draw, sx + int(49*char_w), sx + int(55*char_w), y1, "S", COLOR_S_BLUE)
        draw_dep_clause_tag(draw, sx + int(56*char_w), sx + int(65*char_w), y1, "SC", COLOR_SC_INDIGO)
        draw_modifier_arrow_safe(draw, sx + int(48*char_w) + 12, y1 + 56, sx + int(47*char_w) + 8, y1 + 48)

    # Korean chunk box accumulation
    s1_all_chunks = [
        ("주어인", "화자들은"),
        ("빈도부사인", "항상은"),
        ("본동사인", "표현하지 않는다"),
        ("목적어인", "모든 것을"),
        ("선행사를 수식하는", "그들에게 중요한"),
        ("거품인", "말로")
    ]
    cur_chunks = []
    if state == 1:
        cur_chunks = s1_all_chunks[:1]
    elif state == 2:
        cur_chunks = s1_all_chunks[:2]
    elif state == 3:
        cur_chunks = s1_all_chunks[:3]
    elif state == 4:
        cur_chunks = s1_all_chunks[:4]
    elif state == 5:
        cur_chunks = s1_all_chunks[:5]
    elif state >= 6:
        cur_chunks = s1_all_chunks

    draw_korean_chunk_box(draw, 100, 520, 1420, 180, cur_chunks)

    # Hashtag bar mode & tags
    if state == 8:
        # Grammar mode
        draw_hashtag_bar(draw, 100, 730, 1420, 70, 'grammar', ["#부분부정_not_always", "#선행사_단수_수일치", "#어법빈출"])
    elif state == 9:
        # Writing mode
        draw_hashtag_bar(draw, 100, 730, 1420, 70, 'writing', ["#부분부정_어순배열", "#선행사_관계사절_후치수식", "#영작핵심구문"])
    elif state == 7:
        draw_hashtag_bar(draw, 100, 730, 1420, 70, 'normal', ["#내용이해", "#비언어적소통", "#불완전한언어표현"])
    else:
        draw_hashtag_bar(draw, 100, 730, 1420, 70, 'normal', ["#1번문장", "#직독직해", "#구조분석"])

    return im

def render_s2_state(state: int) -> Image.Image:
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(42)
    char_w = 23.0
    sx = 100
    y1, y2, y3, y4 = 200, 320, 430, 540

    l1 = "2. (Very often) / you / can understand / a speaker's meaning"
    l2 = "   / (by [observing / their nonverbal behaviors])"
    l3 = "   / such as a change (in a vocal tone / or volume),"
    l4 = "   / eye contact, / facial expressions, / and gestures)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y4), l4, fill=COLOR_WHITE, font=font_mono)

    # State 2+: S below you
    if state >= 2:
        draw_main_clause_tag(draw, sx + int(18*char_w), sx + int(21*char_w), y1, "S", COLOR_S_BLUE)
    # State 3+: Vt below can understand
    if state >= 3:
        draw_main_clause_tag(draw, sx + int(24*char_w), sx + int(38*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    # State 4+: O below a speaker's meaning
    if state >= 4:
        draw_main_clause_tag(draw, sx + int(41*char_w), sx + int(60*char_w), y1, "O", COLOR_O_EMERALD)
    # State 5+: Vt above observing, O above their nonverbal behaviors
    if state >= 5:
        draw_dep_clause_tag(draw, sx + int(10*char_w), sx + int(19*char_w), y2, "Vt", COLOR_V_ROSE)
        draw_dep_clause_tag(draw, sx + int(22*char_w), sx + int(47*char_w), y2, "O", COLOR_O_EMERALD)
    # State 6+: triangle on or
    if state >= 6:
        draw_triangle(draw, sx + int(42*char_w) + 4, y3)
    # State 7+: triangle on and
    if state >= 7:
        draw_triangle(draw, sx + int(42*char_w) + 4, y4)

    # Korean chunk box accumulation
    s2_all_chunks = [
        ("부사구인", "매우 흔하게"),
        ("주어인", "너는"),
        ("본동사인", "이해할 수 있다"),
        ("목적어인", "화자의 의미를"),
        ("준동사인", "관찰함으로써"),
        ("준동사의 목적어인", "그들의 비언어적 행동들을"),
        ("예시인", "목소리 톤이나 음량의 변화"),
        ("병렬인", "시선 교환, 표정, 몸짓과 같은")
    ]
    cur_chunks = []
    if state == 1:
        cur_chunks = s2_all_chunks[:1]
    elif state == 2:
        cur_chunks = s2_all_chunks[:2]
    elif state == 3:
        cur_chunks = s2_all_chunks[:3]
    elif state == 4:
        cur_chunks = s2_all_chunks[:4]
    elif state == 5:
        cur_chunks = s2_all_chunks[:6]
    elif state == 6:
        cur_chunks = s2_all_chunks[:7]
    elif state >= 7:
        cur_chunks = s2_all_chunks

    draw_korean_chunk_box(draw, 100, 660, 1420, 170, cur_chunks)

    # Hashtag bar mode & tags
    if state == 9:
        # Grammar mode
        draw_hashtag_bar(draw, 100, 850, 1420, 70, 'grammar', ["#by_동명사_수단방법", "#such_as_예시나열", "#명사구_병렬구조_일치"])
    elif state == 10:
        # Writing mode
        draw_hashtag_bar(draw, 100, 850, 1420, 70, 'writing', ["#by_observing_영작", "#동명사_목적어_수식", "#서술형빈출"])
    elif state == 8:
        draw_hashtag_bar(draw, 100, 850, 1420, 70, 'normal', ["#내용이해", "#비언어적단서", "#의도파악방법"])
    else:
        draw_hashtag_bar(draw, 100, 850, 1420, 70, 'normal', ["#2번문장", "#직독직해", "#구조분석"])

    return im

# Narration Chunks for 2 Sentences
CHUNKS_S1 = [
    (0, "자, 1번 문장 끊어 읽기와 구조 분석을 함께 시작해 볼게."),
    (1, "먼저 첫 번째 청크, 주절의 주어인 '화자들은'."),
    (2, "다음으로, 빈도부사인 '항상은' 거품 걷어내기 원칙에 따라 소괄호로 묶어서 제외해."),
    (3, "이어서, 주절의 본동사이자 타동사인 '표현하지 않는다'."),
    (4, "본동사의 목적어인 '모든 것을'."),
    (5, "이어서 앞의 명사 '모든 것'을 뒤에서 꾸며주는 주격 관계대명사절이야. 수식하니까 소괄호로 묶고 화살표를 달아줘. 관계사절 안에서 주어인 '관계대명사가' 그리고 보어인 '중요한'."),
    (6, "마지막으로 전치사구 거품인 '그들에게'와 '말로'를 소괄호로 묶어주면 끝까지 끊어 읽기가 완성돼. 주절의 3형식과 관계사절의 2형식이 결합된 구조야."),
    (7, "이어서 2단계, 내용 맥락을 짚어볼게. 화자들은 자신에게 중요한 모든 것을 말로 다 표현하지는 않는다는 내용이야. 말 이면에 숨겨진 비언어적인 표현이 매우 중요하다는 걸 암시하고 있어."),
    (8, "다음으로 3단계, 시험에 무조건 출제되는 핵심 어법 포인트야. 첫째로 not always는 '항상 ~하는 것은 아니다'라는 부분 부정 표현이야. 전체 부정이 아니라는 점에 주의해야 해. 둘째로 관계대명사절 안의 동사는 선행사인 everything에 수일치하여 단수 동사가 온다는 점을 꼭 기억해 둬."),
    (9, "마지막으로 4단계, 내신 서술형 영작 대비 포인트야. '화자가 항상 모든 중요한 것을 말로 표현하는 것은 아니다'를 영작할 때, 부분 부정 not always의 위치와 선행사 everything 뒤에 붙는 관계사절의 어순을 정확히 배열하는 훈련을 반복해.")
]

CHUNKS_S2 = [
    (0, "이어서 2번 문장 끊어 읽기와 구조 분석으로 들어가 보자."),
    (1, "첫 번째 청크, 문장 맨 앞의 부사구 거품인 '매우 흔하게'는 소괄호로 묶어서 제외해."),
    (2, "다음으로 주절의 주어인 '너는'."),
    (3, "조동사와 결합된 주절의 본동사인 '이해할 수 있다'는 타동사야."),
    (4, "본동사의 목적어인 '화자의 의미를'."),
    (5, "이어서 전치사구 안에서 '관찰하는 것'은 동명사 준동사야. 단어 위에 작은 타동사 기호를 달아줘. 그리고 준동사의 목적어인 '그들의 비언어적 행동들을'도 단어 위에 표시하고 대괄호로 묶어줘."),
    (6, "비언어적 행동의 예시를 나열하는 전치사구야. '목소리 톤이나 음량의 변화와 같은'으로 끊어 읽고, 접속사 or 위에는 세모를 쳐줘."),
    (7, "마지막으로 대등하게 병렬 연결된 '시선 교환, 얼굴 표정, 그리고 몸짓과 같은'까지 묶어주면 문장 전체의 끊어 읽기가 완성돼. 주절의 3형식에 준동사구와 병렬 구조가 이어진 문장이야."),
    (8, "이어서 2단계, 내용 맥락 설명이야. 우리는 화자의 말이 아니라 목소리 톤이나 시선, 표정, 몸짓 같은 비언어적인 행동을 관찰함으로써 상대방의 진짜 의미를 파악할 수 있다는 구체적인 설명이야."),
    (9, "다음으로 3단계, 시험에 꼭 나오는 핵심 어법 포인트야. 첫째로 전치사 by 뒤에 동명사 observing이 와서 '~함으로써'라는 수단과 방법을 나타내고 있어. 둘째로 such as 뒤에 변화, 시선 교환, 표정, 몸짓이 콤마와 접속사 and로 대등하게 병렬 연결되어 있으니 병렬 구조의 형태 일치에 꼭 별표를 쳐둬."),
    (10, "마지막으로 4단계, 내신 서술형 영작 대비 포인트야. '비언어적 행동을 관찰함으로써 의미를 이해할 수 있다'는 핵심 구문을 영작할 때, by observing their nonverbal behaviors의 형태와 예시를 나열하는 병렬 어순을 정확하게 쓰는 연습을 해둬야 해.")
]

async def synthesize_chunk_audio(text: str, raw_path: str, timed_path: str, silence_path: str):
    await synthesize_best_audio(text, raw_path, preferred_engine="gemini", voice=VOICE)
    # Re-encode and concat cleanly with 1.0s silence to ensure exact audio stream sync
    cmd = [
        FFMPEG, "-y",
        "-i", raw_path,
        "-i", silence_path,
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]",
        "-map", "[a]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        timed_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def render_mini_segment(img_path: str, audio_path: str, muted_circle: str, pip_mask: str, pip_ring: str, out_seg: str):
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", img_path,
        "-stream_loop", "-1", "-i", muted_circle,
        "-loop", "1", "-i", pip_mask,
        "-loop", "1", "-i", pip_ring,
        "-i", audio_path,
        "-filter_complex", "[1:v][2:v]alphamerge[pip];[pip][3:v]overlay[pip_with_ring];[0:v][pip_with_ring]overlay=1590:760:shortest=1[v]",
        "-map", "[v]", "-map", "4:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        out_seg
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

async def run_2sentences_pipeline():
    start_time = time.time()
    base_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker"
    work_dir = os.path.join(base_dir, "output", "test_2sentences_temp")
    audio_dir = os.path.join(base_dir, "output", "audio", "test_2sentences")
    states_dir = os.path.join(base_dir, "output", "test_2sentences_states")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(states_dir, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    muted_circle = TEACHER_PIP_CIRCLE
    pip_mask = PIP_MASK_CIRCLE
    pip_ring = PIP_RING_CIRCLE

    print("======================================================================")
    print("🚀 [2문장 테스트 강의 제작: 끊어읽기(/) + 직독직해표시 + 문장기호확대 + 어법/서술형 해시태그]")
    print("======================================================================")

    # 1. 1.0s 무음 생성
    silence_1s = os.path.join(audio_dir, "silence_1s.mp3")
    subprocess.run([
        FFMPEG, "-y", "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", "1.0", "-c:a", "libmp3lame", silence_1s
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 2. 이미지 생성
    print("\n[STEP 1/4] 장표 상태 이미지 생성 중...")
    cover_img = os.path.join(states_dir, "cover.png")
    render_cover_slide().save(cover_img)

    s1_imgs = {}
    for st in range(10):
        p = os.path.join(states_dir, f"s1_st{st}.png")
        render_s1_state(st).save(p)
        s1_imgs[st] = p
    print("  [OK] 1번 문장 10개 상태 이미지 완료")

    s2_imgs = {}
    for st in range(11):
        p = os.path.join(states_dir, f"s2_st{st}.png")
        render_s2_state(st).save(p)
        s2_imgs[st] = p
    print("  [OK] 2번 문장 11개 상태 이미지 완료")

    # 3. 비디오 세그먼트 생성
    print("\n[STEP 2/4] 음성 합성 및 비디오 렌더링 중...")
    seg_files = []

    # Intro (Cover)
    t0 = time.time()
    intro_txt = "친구들 안녕! 오늘 같이 볼 지문은 2026년 고3 6월 모의고사 삼십이 번이야. 끊어 읽기와 직독직해, 그리고 핵심 어법과 서술형까지 집중해서 잘 따라와야 해. 첫 번째 문장부터 바로 들어가 보자!"
    intro_raw = os.path.join(audio_dir, "intro_raw.mp3")
    intro_timed = os.path.join(audio_dir, "intro_timed.mp3")
    await synthesize_chunk_audio(intro_txt, intro_raw, intro_timed, silence_1s)
    seg_intro = os.path.join(work_dir, "seg_00_intro.mp4")
    render_mini_segment(cover_img, intro_timed, muted_circle, pip_mask, pip_ring, seg_intro)
    print(f"  [OK] 표지 오프닝 렌더링 완료 ({round(time.time() - t0, 1)}초)")
    seg_files.append(seg_intro)

    # S1
    t_s1 = time.time()
    s1_work = os.path.join(work_dir, "s1")
    os.makedirs(s1_work, exist_ok=True)
    s1_mini_segs = []
    for idx, (st, text) in enumerate(CHUNKS_S1):
        raw_a = os.path.join(s1_work, f"raw_{idx:02d}.mp3")
        timed_a = os.path.join(s1_work, f"timed_{idx:02d}.mp3")
        await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)

        img_p = s1_imgs[st]
        m_mp4 = os.path.join(s1_work, f"mini_{idx:02d}.mp4")
        render_mini_segment(img_p, timed_a, muted_circle, pip_mask, pip_ring, m_mp4)
        s1_mini_segs.append(m_mp4)

    s1_cat = os.path.join(s1_work, "concat_s1.txt")
    with open(s1_cat, "w", encoding="utf-8") as f:
        for ms in s1_mini_segs:
            f.write(f"file '{ms.replace(chr(92), '/')}'\n")

    seg_s1 = os.path.join(work_dir, "seg_01_s1.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", s1_cat, "-c", "copy", seg_s1], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    dur_s1 = get_audio_duration(seg_s1)
    print(f"  [OK] 1번 문장 완성 ({round(dur_s1, 1)}초 분량, {round(time.time() - t_s1, 1)}초 소요)")
    seg_files.append(seg_s1)

    # S2
    t_s2 = time.time()
    s2_work = os.path.join(work_dir, "s2")
    os.makedirs(s2_work, exist_ok=True)
    s2_mini_segs = []
    for idx, (st, text) in enumerate(CHUNKS_S2):
        raw_a = os.path.join(s2_work, f"raw_{idx:02d}.mp3")
        timed_a = os.path.join(s2_work, f"timed_{idx:02d}.mp3")
        await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)

        img_p = s2_imgs[st]
        m_mp4 = os.path.join(s2_work, f"mini_{idx:02d}.mp4")
        render_mini_segment(img_p, timed_a, muted_circle, pip_mask, pip_ring, m_mp4)
        s2_mini_segs.append(m_mp4)

    s2_cat = os.path.join(s2_work, "concat_s2.txt")
    with open(s2_cat, "w", encoding="utf-8") as f:
        for ms in s2_mini_segs:
            f.write(f"file '{ms.replace(chr(92), '/')}'\n")

    seg_s2 = os.path.join(work_dir, "seg_02_s2.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", s2_cat, "-c", "copy", seg_s2], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    dur_s2 = get_audio_duration(seg_s2)
    print(f"  [OK] 2번 문장 완성 ({round(dur_s2, 1)}초 분량, {round(time.time() - t_s2, 1)}초 소요)")
    seg_files.append(seg_s2)

    # 4. Concat all
    print("\n[STEP 3/4] 2문장 테스트 강의 최종 병합 중...")
    master_txt = os.path.join(work_dir, "concat_master.txt")
    with open(master_txt, "w", encoding="utf-8") as f:
        for sf in seg_files:
            f.write(f"file '{sf.replace(chr(92), '/')}'\n")

    final_mp4 = os.path.join(VIDEOS_DIR, "2026_고3_6월_32번_2문장_테스트강의.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", master_txt, "-c", "copy", final_mp4], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    total_dur = get_audio_duration(final_mp4)
    file_size_mb = round(os.path.getsize(final_mp4) / (1024 * 1024), 2)
    print("\n" + "=" * 70)
    print("🎉 [완성] 2026년 고3 6월 32번 2문장 테스트 강의 완성!")
    print(f" - 파일: {final_mp4}")
    print(f" - 재생 시간: {round(total_dur / 60, 1)}분 ({round(total_dur, 1)}초)")
    print(f" - 용량: {file_size_mb} MB")
    print(f" - 소요 시간: {round(time.time() - start_time, 1)}초")
    print("======================================================================")

if __name__ == "__main__":
    asyncio.run(run_2sentences_pipeline())
