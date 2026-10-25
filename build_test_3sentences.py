import os
import sys
import time
import math
import asyncio
import subprocess
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from video_renderer import get_audio_duration
from config import VIDEOS_DIR, TEACHER_PIP_CIRCLE, PIP_MASK_CIRCLE, PIP_RING_CIRCLE
from tts_engine import synthesize_best_audio

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "Aoede" # Gemini 2.5 Studio Aoede (여성, 명확하고 또렷한 설명형 톤)

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

def draw_encompassing_triangle(draw, x1, x2, y, text_h=44, color=COLOR_SKY_TRIANGLE, width=3):
    """접속사 단어를 완전히 포괄(둘러싸는/겹치는)하는 세모(△) 도형 그리기"""
    pad_x = 8
    pad_top = 8
    pad_bot = 6
    top_x = (x1 + x2) // 2
    top_y = y - pad_top
    bot_y = y + text_h + pad_bot
    left_x = x1 - pad_x
    right_x = x2 + pad_x
    draw.polygon([(top_x, top_y), (left_x, bot_y), (right_x, bot_y)], outline=color, width=width)

def draw_main_clause_tag(draw, x1, x2, y, tag, color, double_u=False):
    has_kr = any(ord(c) > 127 for c in tag)
    font_tag_main = get_kr_font(32, bold=True) if has_kr else get_mono_font(36)
    draw.line([(x1, y + 54), (x2, y + 54)], fill=color, width=3)
    if double_u:
        draw.line([(x1, y + 60), (x2, y + 60)], fill=color, width=2)
    tb = draw.textbbox((0, 0), tag, font=font_tag_main)
    w = tb[2] - tb[0]
    draw.text((x1 + (x2 - x1 - w) // 2, y + (66 if double_u else 60)), tag, fill=color, font=font_tag_main)

def draw_dep_clause_tag(draw, x1, x2, y, tag, color):
    has_kr = any(ord(c) > 127 for c in tag)
    font_tag_dep = get_kr_font(24, bold=True) if has_kr else get_mono_font(26)
    tb = draw.textbbox((0, 0), tag, font=font_tag_dep)
    w = tb[2] - tb[0]
    draw.text((x1 + (x2 - x1 - w) // 2, y - 36), tag, fill=color, font=font_tag_dep)

def draw_korean_chunk_box(draw, x, y, w, h, chunks):
    """직독직해 실시간 끊어 읽기 표시 카드"""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill=(18, 48, 34), outline=(46, 99, 73), width=2)
    font_header = get_kr_font(22, bold=True)
    draw.text((x + 24, y + 16), "[ 직독직해 끊어 읽기 ]", fill=COLOR_YELLOW, font=font_header)

    font_label = get_kr_font(20, bold=False)
    font_word = get_kr_font(24, bold=True)
    font_slash = get_kr_font(24, bold=True)

    cur_x = x + 24
    cur_y = y + 56
    max_line_w = w - 48

    for i, (label, meaning) in enumerate(chunks):
        t_label = f"[{label}] "
        tb_l = draw.textbbox((0, 0), t_label, font=font_label)
        wl = tb_l[2] - tb_l[0]

        tb_m = draw.textbbox((0, 0), meaning, font=font_word)
        wm = tb_m[2] - tb_m[0]

        slash_str = "  /  " if i < len(chunks) - 1 else ""
        tb_s = draw.textbbox((0, 0), slash_str, font=font_slash)
        ws = tb_s[2] - tb_s[0]

        chunk_total_w = wl + wm + ws
        if cur_x + chunk_total_w > x + max_line_w:
            cur_x = x + 24
            cur_y += 48

        draw.text((cur_x, cur_y + 3), t_label, fill=COLOR_GRAY, font=font_label)
        cur_x += wl

        is_latest = (i == len(chunks) - 1)
        w_color = COLOR_YELLOW if is_latest else COLOR_WHITE
        draw.text((cur_x, cur_y), meaning, fill=w_color, font=font_word)
        cur_x += wm

        if slash_str:
            draw.text((cur_x, cur_y), slash_str, fill=COLOR_SLASH, font=font_slash)
            cur_x += ws

def draw_hashtag_bar(draw, x, y, w, h, mode='normal', tags=None):
    """어법/서술형 해시태그 안내 바"""
    if tags is None:
        tags = []

    if mode == 'grammar':
        bg_color = (60, 24, 28)
        border_color = (248, 113, 113)
        prefix = "▶ #어법중요 : "
        prefix_color = (248, 113, 113)
    elif mode == 'writing':
        bg_color = (65, 50, 18)
        border_color = (250, 204, 21)
        prefix = "★ #서술형중요 : "
        prefix_color = (250, 204, 21)
    else:
        bg_color = (22, 59, 42)
        border_color = (46, 99, 73)
        prefix = "● #핵심포인트 : "
        prefix_color = (56, 189, 248)

    draw.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=bg_color, outline=border_color, width=2)
    font_p = get_kr_font(24, bold=True)
    draw.text((x + 24, y + 20), prefix, fill=prefix_color, font=font_p)

    tb_p = draw.textbbox((0, 0), prefix, font=font_p)
    cx = x + 24 + (tb_p[2] - tb_p[0])

    font_t = get_kr_font(22, bold=True)
    for i, tag in enumerate(tags):
        tag_str = tag + ("   " if i < len(tags)-1 else "")
        draw.text((cx, y + 22), tag_str, fill=COLOR_WHITE, font=font_t)
        tb_t = draw.textbbox((0, 0), tag_str, font=font_t)
        cx += tb_t[2] - tb_t[0]

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

    l1 = "1. Speakers / (don't always) / put / everything / (that's important"
    l2 = "   / (to them)) / (into words)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

    if state >= 1:
        draw_main_clause_tag(draw, sx + int(3*char_w), sx + int(11*char_w), y1, "S", COLOR_S_BLUE)
    if state >= 2:
        draw_main_clause_tag(draw, sx + int(31*char_w), sx + int(34*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    if state >= 3:
        draw_main_clause_tag(draw, sx + int(37*char_w), sx + int(47*char_w), y1, "O", COLOR_O_EMERALD)
    if state >= 4:
        draw_dep_clause_tag(draw, sx + int(51*char_w), sx + int(57*char_w), y1, "S", COLOR_S_BLUE)
        draw_dep_clause_tag(draw, sx + int(58*char_w), sx + int(67*char_w), y1, "SC", COLOR_SC_INDIGO)
        draw_modifier_arrow_safe(draw, sx + int(50*char_w) + 12, y1 + 56, sx + int(47*char_w) + 8, y1 + 48)

    s1_all_chunks = [
        ("주어인", "화자들은"),
        ("타동사인", "항상 표현하는 것은 아니다"),
        ("목적어인", "모든 것을"),
        ("관계사절인", "그들에게 중요한"),
        ("부사구인", "그들에게"),
        ("구동사인", "말로")
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

    if state == 8:
        draw_hashtag_bar(draw, 100, 730, 1420, 70, 'grammar', ["#부분부정_not_always", "#선행사_단수_수일치", "#어법빈출"])
    elif state == 9:
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
    l3 = "   / (such as a change / (in a vocal tone or volume),"
    l4 = "   / eye contact, / facial expressions, / and gestures)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y4), l4, fill=COLOR_WHITE, font=font_mono)

    if state >= 2:
        draw_main_clause_tag(draw, sx + int(18*char_w), sx + int(21*char_w), y1, "S", COLOR_S_BLUE)
    if state >= 3:
        draw_main_clause_tag(draw, sx + int(24*char_w), sx + int(38*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    if state >= 4:
        draw_main_clause_tag(draw, sx + int(41*char_w), sx + int(60*char_w), y1, "O", COLOR_O_EMERALD)
    if state >= 5:
        draw_dep_clause_tag(draw, sx + int(10*char_w), sx + int(19*char_w), y2, "Vt", COLOR_V_ROSE)
        draw_dep_clause_tag(draw, sx + int(22*char_w), sx + int(47*char_w), y2, "O", COLOR_O_EMERALD)
    if state >= 6:
        # Encompassing triangle on 'and'
        draw_encompassing_triangle(draw, sx + int(42*char_w), sx + int(45*char_w), y4)

    s2_all_chunks = [
        ("부사구인", "매우 흔하게"),
        ("주어인", "너는"),
        ("본동사인", "이해할 수 있다"),
        ("목적어인", "화자의 의미를"),
        ("준동사구인", "비언어적 행동들을 관찰함으로써"),
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
        cur_chunks = s2_all_chunks[:5]
    elif state == 6:
        cur_chunks = s2_all_chunks[:6]
    elif state >= 7:
        cur_chunks = s2_all_chunks

    draw_korean_chunk_box(draw, 100, 620, 1420, 180, cur_chunks)

    if state == 9:
        draw_hashtag_bar(draw, 100, 830, 1420, 70, 'grammar', ["#by_observing_동명사", "#such_as_병렬구조", "#수단방법부사구"])
    elif state == 10:
        draw_hashtag_bar(draw, 100, 830, 1420, 70, 'writing', ["#by_observing_영작", "#비언어적행동_예시나열", "#병렬어순배열"])
    elif state == 8:
        draw_hashtag_bar(draw, 100, 830, 1420, 70, 'normal', ["#내용이해", "#비언어적신호관찰", "#진짜의미파악"])
    else:
        draw_hashtag_bar(draw, 100, 830, 1420, 70, 'normal', ["#2번문장", "#직독직해", "#구조분석"])

    return im

def render_s3_state(state: int) -> Image.Image:
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(42)
    char_w = 23.0
    sx = 100
    y1, y2, y3 = 220, 360, 500

    l1 = "3. (As it is easy / [to misinterpret / nonverbal behavior]),"
    l2 = "   / effective listeners / (verbally) / confirm / their interpretations"
    l3 = "   / (of someone's nonverbal communication)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)

    if state >= 1:
        # Encompassing triangle on 'As'
        draw_encompassing_triangle(draw, sx + int(4*char_w), sx + int(6*char_w), y1)
        draw_dep_clause_tag(draw, sx + int(7*char_w), sx + int(9*char_w), y1, "가S", COLOR_S_BLUE)
        draw_dep_clause_tag(draw, sx + int(10*char_w), sx + int(12*char_w), y1, "Vi", COLOR_V_ROSE)
        draw_dep_clause_tag(draw, sx + int(13*char_w), sx + int(17*char_w), y1, "SC", COLOR_SC_INDIGO)
    if state >= 2:
        draw_dep_clause_tag(draw, sx + int(21*char_w), sx + int(36*char_w), y1, "Vt", COLOR_V_ROSE)
        draw_dep_clause_tag(draw, sx + int(39*char_w), sx + int(57*char_w), y1, "O", COLOR_O_EMERALD)
    if state >= 3:
        draw_main_clause_tag(draw, sx + int(5*char_w), sx + int(24*char_w), y2, "S", COLOR_S_BLUE)
    if state >= 4:
        draw_main_clause_tag(draw, sx + int(40*char_w), sx + int(47*char_w), y2, "Vt", COLOR_V_ROSE, double_u=True)
    if state >= 5:
        draw_main_clause_tag(draw, sx + int(50*char_w), sx + int(71*char_w), y2, "O", COLOR_O_EMERALD)

    s3_all_chunks = [
        ("이유 부사절인", "비언어적 행동을 오해하기 쉽기 때문에"),
        ("진주어 준동사구인", "비언어적 행동을 오해하는 것은"),
        ("주절 주어인", "효과적인 청자들은"),
        ("본동사인", "말로 확인한다"),
        ("목적어인", "그들의 해석을"),
        ("부사구 거품인", "누군가의 비언어적 소통에 대한")
    ]
    cur_chunks = []
    if state == 1:
        cur_chunks = s3_all_chunks[:1]
    elif state == 2:
        cur_chunks = s3_all_chunks[:2]
    elif state == 3:
        cur_chunks = s3_all_chunks[:3]
    elif state == 4:
        cur_chunks = s3_all_chunks[:4]
    elif state == 5:
        cur_chunks = s3_all_chunks[:5]
    elif state >= 6:
        cur_chunks = s3_all_chunks

    draw_korean_chunk_box(draw, 100, 590, 1420, 180, cur_chunks)

    if state == 8:
        draw_hashtag_bar(draw, 100, 800, 1420, 70, 'grammar', ["#가주어_it_진주어_to", "#부사_verbally_위치", "#접속사_As_이유"])
    elif state == 9:
        draw_hashtag_bar(draw, 100, 800, 1420, 70, 'writing', ["#가주어진주어_어순배열", "#verbally_confirm_구문", "#서술형핵심문항"])
    elif state == 7:
        draw_hashtag_bar(draw, 100, 800, 1420, 70, 'normal', ["#내용이해", "#오해방지", "#말로_직접확인"])
    else:
        draw_hashtag_bar(draw, 100, 800, 1420, 70, 'normal', ["#3번문장", "#직독직해", "#구조분석"])

    return im

S1_CHUNKS = [
    (0, "1번 문장 직독직해와 구조 분석이야."),
    (1, "주어인 화자는,"),
    (2, "항상 말로 표현하는 것은 아니다이고, 타동사야. 항상 하는 건 아니다라는 부분부정이 들어가 있어."),
    (3, "모든 것을은 목적어야. 그래서 주절이 3형식이야."),
    (4, "중요한으로 해석해 주격 관계대명사 절이고 앞의 모든 것을 수식하고 있고, 중요한이 주격보어 역할을 하는 2형식 문장이야."),
    (5, "그들에게이며, 전명구가 부사구의 역할을 하고 있어."),
    (6, "풋 인투 워드는 하나로 묶어서 구동사의 역할을 하고 있다는 거 중요해. 말로라는 전명구 부사구 거품이야. 주절 3형식에 2형식 형용사절이 결합된 완전한 문장이야."),
    (7, "이어서 2단계, 내용 맥락 설명이야. 화자들은 자기가 중요하다고 생각하는 모든 것을 말로 다 표현하지는 않는다는 내용이야. 언어로 표현하지 않는 다른 중요한 비언어적 메시지가 있을 수 있다는 걸 암시하지."),
    (8, "다음으로 3단계, 시험에 무조건 출제되는 핵심 문법 포인트야. 여기서 not always는 항상 ~하는 것은 아니다라는 부분 부정을 나타내는 표현이야. 그리고 주격 관계대명사절 안의 동사는 앞의 선행사 everything에 수일치하여 단수 동사가 온다는 점을 꼭 기억해 둬."),
    (9, "마지막으로 4단계, 내신 서술형 영작 대비 포인트야. 타동사 구문과 주격 관계대명사절이 결합된 형태라서 서술형으로 출제되기 아주 좋아. 관계대명사절이 선행사를 뒤에서 수식하는 어순에 유의해서 영작 연습 꼭 해봐야 해.")
]

S2_CHUNKS = [
    (0, "2번 문장 직독직해와 구조 분석이야."),
    (1, "문장 맨 앞의 매우 흔하게는 부사구 거품이야."),
    (2, "주어인 너는,"),
    (3, "조동사와 결합된 이해할 수 있다는 타동사야."),
    (4, "화자의 의미를은 목적어야. 그래서 주절이 3형식이야."),
    (5, "그들의 비언어적 행동들을 관찰함으로써는 수단을 나타내는 전명구 부사구야. 준동사 관찰하는 것은 타동사이고, 그들의 비언어적 행동들은 준동사의 목적어야."),
    (6, "목소리 톤이나 음량의 변화, 시선 교환, 얼굴 표정, 그리고 몸짓과 같은은 비언어적 행동의 구체적인 예시를 나열하는 거품이야. 접속사 and는 단어를 세모로 둘러싸줘."),
    (7, "주절의 3형식에 준동사구와 병렬 구조가 이어진 완전한 문장이야."),
    (8, "이어서 2단계, 내용 맥락 설명이야. 우리는 화자의 말이 아니라 목소리 톤이나 시선, 표정, 몸짓 같은 비언어적인 행동을 관찰함으로써 상대방의 진짜 의미를 파악할 수 있다는 구체적인 설명이야."),
    (9, "다음으로 3단계, 시험에 꼭 나오는 핵심 어법 포인트야. 첫째로 전치사 by 뒤에 동명사 observing이 와서 '~함으로써'라는 수단과 방법을 나타내고 있어. 둘째로 such as 뒤에 변화, 시선 교환, 표정, 몸짓이 콤마와 접속사 and로 대등하게 병렬 연결되어 있으니 병렬 구조의 형태 일치에 꼭 별표를 쳐둬."),
    (10, "마지막으로 4단계, 내신 서술형 영작 대비 포인트야. '비언어적 행동을 관찰함으로써 의미를 이해할 수 있다'는 핵심 구문을 영작할 때, by observing their nonverbal behaviors의 형태와 예시를 나열하는 병렬 어순을 정확하게 쓰는 연습을 해둬야 해.")
]

S3_CHUNKS = [
    (0, "3번 문장 직독직해와 구조 분석이야."),
    (1, "비언어적 행동을 오해하기 쉽기 때문에라는 이유의 부사절이야. 접속사 As를 세모로 둘러싸고, 그것은은 가주어, 이다는 자동사, 쉬운은 주격보어야."),
    (2, "진주어인 비언어적 행동을 오해하는 것은 대괄호로 묶고, 준동사 오해하다는 타동사, 비언어적 행동은 준동사의 목적어야."),
    (3, "주절의 주어인 효과적인 청자들은,"),
    (4, "말로라는 부사 거품을 거쳐, 확인한다는 타동사야."),
    (5, "그들의 해석을은 목적어야. 그래서 주절이 3형식이야."),
    (6, "누군가의 비언어적 소통에 대한은 전명구 부사구 거품이야. 이유 부사절과 주절의 3형식이 결합된 문장이야."),
    (7, "이어서 2단계, 내용 맥락 설명이야. 비언어적 행동은 주관적으로 오해하기가 너무 쉬워. 그래서 소통을 잘하는 효과적인 청자들은 상대방의 비언어적 표현을 말로 직접 되물어서 확인하는 습관을 가진다는 거야."),
    (8, "다음으로 3단계, 시험에 꼭 나오는 핵심 문법 포인트야. 접속사 As는 이유를 나타내어 비코즈나 신스로 바꾸어 쓸 수 있어. 또한 가주어 it과 진주어 to 부정사 구문이 사용되었으니 진주어의 위치와 역할을 정확히 알아두어야 해. 부사 verbally의 위치도 확인해 둬."),
    (9, "마지막으로 4단계, 내신 서술형 영작 대비 포인트야. 이유 부사절과 주절의 3형식 어순, 특히 as절 내부의 가주어 it과 진주어 to 부정사 구문을 정확하게 영작하는 것이 중요해. 주절에서 verbally confirm their interpretations of의 어순도 꼭 기억해 두자.")
]

async def synthesize_chunk_audio(text: str, raw_path: str, timed_path: str, silence_path: str):
    await synthesize_best_audio(text, raw_path, preferred_engine="gemini", voice=VOICE)
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

async def run_3sentences_pipeline():
    start_time = time.time()
    base_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker"
    work_dir = os.path.join(base_dir, "output", "test_3sentences_temp")
    audio_dir = os.path.join(base_dir, "output", "audio", "test_3sentences")
    states_dir = os.path.join(base_dir, "output", "test_3sentences_states")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(states_dir, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    muted_circle = TEACHER_PIP_CIRCLE
    pip_mask = PIP_MASK_CIRCLE
    pip_ring = PIP_RING_CIRCLE

    print("======================================================================")
    print("🚀 [2026년 고3 6월 32번: 1~3번 문장 집중 테스트 강의 비디오 제작]")
    print("   1. 모든 단어 직독직해 + 성분 + 형식 + 구문포인트 동시 설명")
    print("   2. 영문 본문 / 슬래시 표시 (주절 + 종속절 + 준동사 전면 적용)")
    print("   3. 접속사 포괄 세모(△) 표시 (and, As 등 단어 둘러싸기)")
    print("   4. TTS 일관성 및 생동감 (Gemini 2.5 Studio Aoede)")
    print("   5. 신규 강사 영상(gemini_generated_video_2447ddbb) 원형 PIP 합성")
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

    s3_imgs = {}
    for st in range(10):
        p = os.path.join(states_dir, f"s3_st{st}.png")
        render_s3_state(st).save(p)
        s3_imgs[st] = p
    print("  [OK] 3번 문장 10개 상태 이미지 완료")

    # 3. 비디오 세그먼트 생성
    print("\n[STEP 2/4] 음성 합성 및 비디오 렌더링 중...")
    seg_files = []

    # Intro (Cover)
    t0 = time.time()
    intro_text = "친구들 안녕! 오늘 같이 분석해 볼 지문은 2026년 고3 6월 모의고사 삼십이 번이야. 비언어적 소통의 중요성을 다룬 핵심 빈칸 문항이니까, 첫 번째 문장부터 집중해서 바로 들어가 보자!"
    intro_raw = os.path.join(audio_dir, "intro_raw.mp3")
    intro_timed = os.path.join(audio_dir, "intro_timed.mp3")
    await synthesize_chunk_audio(intro_text, intro_raw, intro_timed, silence_1s)
    seg_intro = os.path.join(work_dir, "seg_00_intro.mp4")
    render_mini_segment(cover_img, intro_timed, muted_circle, pip_mask, pip_ring, seg_intro)
    print(f"  [OK] 표지 오프닝 렌더링 완료 ({round(get_audio_duration(seg_intro), 1)}초)")
    seg_files.append(seg_intro)

    # S1
    t1 = time.time()
    s1_work = os.path.join(work_dir, "s1")
    os.makedirs(s1_work, exist_ok=True)
    s1_minis = []
    for c_idx, (st, text) in enumerate(S1_CHUNKS):
        raw_a = os.path.join(s1_work, f"raw_{c_idx:02d}.mp3")
        timed_a = os.path.join(s1_work, f"timed_{c_idx:02d}.mp3")
        await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)
        mini_v = os.path.join(s1_work, f"mini_{c_idx:02d}.mp4")
        render_mini_segment(s1_imgs[st], timed_a, muted_circle, pip_mask, pip_ring, mini_v)
        s1_minis.append(mini_v)

    cat_s1 = os.path.join(s1_work, "concat_s1.txt")
    with open(cat_s1, "w", encoding="utf-8") as f:
        for m in s1_minis:
            f.write(f"file '{m.replace(chr(92), '/')}'\n")
    seg_s1 = os.path.join(work_dir, "seg_01_s1.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cat_s1, "-c", "copy", seg_s1], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"  [OK] 1번 문장 완성 ({round(get_audio_duration(seg_s1), 1)}초 분량, {round(time.time()-t1, 1)}초 소요)")
    seg_files.append(seg_s1)

    # S2
    t2 = time.time()
    s2_work = os.path.join(work_dir, "s2")
    os.makedirs(s2_work, exist_ok=True)
    s2_minis = []
    for c_idx, (st, text) in enumerate(S2_CHUNKS):
        raw_a = os.path.join(s2_work, f"raw_{c_idx:02d}.mp3")
        timed_a = os.path.join(s2_work, f"timed_{c_idx:02d}.mp3")
        await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)
        mini_v = os.path.join(s2_work, f"mini_{c_idx:02d}.mp4")
        render_mini_segment(s2_imgs[st], timed_a, muted_circle, pip_mask, pip_ring, mini_v)
        s2_minis.append(mini_v)

    cat_s2 = os.path.join(s2_work, "concat_s2.txt")
    with open(cat_s2, "w", encoding="utf-8") as f:
        for m in s2_minis:
            f.write(f"file '{m.replace(chr(92), '/')}'\n")
    seg_s2 = os.path.join(work_dir, "seg_02_s2.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cat_s2, "-c", "copy", seg_s2], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"  [OK] 2번 문장 완성 ({round(get_audio_duration(seg_s2), 1)}초 분량, {round(time.time()-t2, 1)}초 소요)")
    seg_files.append(seg_s2)

    # S3
    t3 = time.time()
    s3_work = os.path.join(work_dir, "s3")
    os.makedirs(s3_work, exist_ok=True)
    s3_minis = []
    for c_idx, (st, text) in enumerate(S3_CHUNKS):
        raw_a = os.path.join(s3_work, f"raw_{c_idx:02d}.mp3")
        timed_a = os.path.join(s3_work, f"timed_{c_idx:02d}.mp3")
        await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)
        mini_v = os.path.join(s3_work, f"mini_{c_idx:02d}.mp4")
        render_mini_segment(s3_imgs[st], timed_a, muted_circle, pip_mask, pip_ring, mini_v)
        s3_minis.append(mini_v)

    cat_s3 = os.path.join(s3_work, "concat_s3.txt")
    with open(cat_s3, "w", encoding="utf-8") as f:
        for m in s3_minis:
            f.write(f"file '{m.replace(chr(92), '/')}'\n")
    seg_s3 = os.path.join(work_dir, "seg_03_s3.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cat_s3, "-c", "copy", seg_s3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"  [OK] 3번 문장 완성 ({round(get_audio_duration(seg_s3), 1)}초 분량, {round(time.time()-t3, 1)}초 소요)")
    seg_files.append(seg_s3)

    # 4. 최종 병합
    print("\n[STEP 3/4] 3문장 테스트 강의 최종 병합 중...")
    cat_master = os.path.join(work_dir, "concat_master.txt")
    with open(cat_master, "w", encoding="utf-8") as f:
        for sf in seg_files:
            f.write(f"file '{sf.replace(chr(92), '/')}'\n")

    final_mp4 = os.path.join(VIDEOS_DIR, "2026_고3_6월_32번_3문장_테스트강의.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cat_master, "-c", "copy", final_mp4], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    dur = get_audio_duration(final_mp4)
    sz_mb = round(os.path.getsize(final_mp4) / (1024 * 1024), 2)
    elapsed = round(time.time() - start_time, 1)

    print("\n" + "=" * 70)
    print("🎉 [완성] 2026년 고3 6월 32번 3문장 테스트 강의 완성!")
    print(f" - 파일: {final_mp4}")
    print(f" - 재생 시간: {round(dur / 60, 1)}분 ({round(dur, 1)}초)")
    print(f" - 용량: {sz_mb} MB")
    print(f" - 소요 시간: {elapsed}초")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_3sentences_pipeline())
