import os
import math
from PIL import Image, ImageDraw, ImageFont

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
    # Font size increased to 36!
    has_kr = any(ord(c) > 127 for c in tag)
    font_tag_main = get_kr_font(32, bold=True) if has_kr else get_mono_font(36)
    draw.line([(x1, y + 48), (x2, y + 48)], fill=color, width=3)
    if double_u:
        draw.line([(x1, y + 54), (x2, y + 54)], fill=color, width=2)
    tb = draw.textbbox((0, 0), tag, font=font_tag_main)
    w = tb[2] - tb[0]
    draw.text((x1 + (x2 - x1 - w) // 2, y + (60 if double_u else 54)), tag, fill=color, font=font_tag_main)

def draw_dep_clause_tag(draw, x1, x2, y, tag, color):
    # Font size increased to 26!
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
    """
    직독직해 끊어 읽기 박스 렌더링
    chunks_list: [(role, text), ...]
    """
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
    """
    하단 해시태그 바 렌더링
    mode: 'normal' | 'grammar' | 'writing'
    """
    if mode == 'grammar':
        bg = (55, 25, 30)
        border = (248, 113, 113) # Red/Rose highlight
        badge_text = "▶ #어법중요"
        badge_color = (255, 235, 59)
    elif mode == 'writing':
        bg = (20, 50, 40)
        border = (52, 211, 153) # Emerald highlight
        badge_text = "★ #서술형중요"
        badge_color = (255, 235, 59)
    else:
        bg = COLOR_PILL_BG
        border = COLOR_PILL_BORDER
        badge_text = "● #핵심포인트"
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

def render_s1_full():
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(44)
    char_w = 24.0
    sx = 100
    y1, y2 = 240, 390

    # Line 1: 1. Speakers / (don't always) / put / everything (that's important
    # Line 2:    / (to them)) / (into words).
    l1 = "1. Speakers / (don't always) / put / everything (that's important"
    l2 = "   / (to them)) / (into words)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

    # Speakers: cols 3..11
    draw_main_clause_tag(draw, sx + int(3*char_w), sx + int(11*char_w), y1, "S", COLOR_S_BLUE)
    # put: cols 31..34
    draw_main_clause_tag(draw, sx + int(31*char_w), sx + int(34*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    # everything: cols 37..47
    draw_main_clause_tag(draw, sx + int(37*char_w), sx + int(47*char_w), y1, "O", COLOR_O_EMERALD)

    # that's: cols 49..55
    draw_dep_clause_tag(draw, sx + int(49*char_w), sx + int(55*char_w), y1, "S", COLOR_S_BLUE)
    # important: cols 56..65
    draw_dep_clause_tag(draw, sx + int(56*char_w), sx + int(65*char_w), y1, "SC", COLOR_SC_INDIGO)

    # Safe curved arrow pointing back from ( (col 48) to everything (col 47)
    draw_modifier_arrow_safe(draw, sx + int(48*char_w) + 12, y1 + 56, sx + int(47*char_w) + 8, y1 + 48)

    # Korean chunk box
    s1_chunks = [
        ("주어인", "화자들은"),
        ("빈도부사인", "항상은"),
        ("본동사인", "표현하지 않는다"),
        ("목적어인", "모든 것을"),
        ("선행사를 수식하는", "그들에게 중요한"),
        ("거품인", "말로")
    ]
    draw_korean_chunk_box(draw, 100, 520, 1420, 180, s1_chunks)

    # Grammar Hashtag Bar
    s1_grammar_tags = ["#부분부정_not_always", "#선행사_단수_수일치", "#어법빈출"]
    draw_hashtag_bar(draw, 100, 730, 1420, 70, 'grammar', s1_grammar_tags)

    return im

def render_s2_full():
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(42)
    char_w = 23.0
    sx = 100
    y1, y2, y3, y4 = 210, 320, 430, 540

    l1 = "2. (Very often) / you / can understand / a speaker's meaning"
    l2 = "   / (by [observing / their nonverbal behaviors])"
    l3 = "   / such as a change (in a vocal tone / or volume),"
    l4 = "   / eye contact, / facial expressions, / and gestures)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y4), l4, fill=COLOR_WHITE, font=font_mono)

    # you: cols 18..21
    draw_main_clause_tag(draw, sx + int(18*char_w), sx + int(21*char_w), y1, "S", COLOR_S_BLUE)
    # can understand: cols 24..38
    draw_main_clause_tag(draw, sx + int(24*char_w), sx + int(38*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    # a speaker's meaning: cols 41..60
    draw_main_clause_tag(draw, sx + int(41*char_w), sx + int(60*char_w), y1, "O", COLOR_O_EMERALD)

    # observing: cols 10..19
    draw_dep_clause_tag(draw, sx + int(10*char_w), sx + int(19*char_w), y2, "Vt", COLOR_V_ROSE)
    # their nonverbal behaviors: cols 22..47
    draw_dep_clause_tag(draw, sx + int(22*char_w), sx + int(47*char_w), y2, "O", COLOR_O_EMERALD)

    # Triangle on or: col 42
    draw_triangle(draw, sx + int(42*char_w) + 4, y3)
    # Triangle on and: col 42
    draw_triangle(draw, sx + int(42*char_w) + 4, y4)

    # Korean chunk box
    s2_chunks = [
        ("부사구인", "매우 흔하게"),
        ("주어인", "너는"),
        ("본동사인", "이해할 수 있다"),
        ("목적어인", "화자의 의미를"),
        ("준동사인", "관찰함으로써"),
        ("준동사의 목적어인", "그들의 비언어적 행동들을"),
        ("예시인", "목소리 톤이나 음량의 변화"),
        ("병렬인", "시선 교환, 표정, 몸짓과 같은")
    ]
    draw_korean_chunk_box(draw, 100, 660, 1420, 170, s2_chunks)

    # Writing Hashtag Bar
    s2_writing_tags = ["#by_observing_동명사영작", "#such_as_병렬구조", "#서술형빈출"]
    draw_hashtag_bar(draw, 100, 850, 1420, 70, 'writing', s2_writing_tags)

    return im

if __name__ == "__main__":
    out = r"output\test_new_design"
    os.makedirs(out, exist_ok=True)
    render_s1_full().save(os.path.join(out, "s1_new_full.png"))
    render_s2_full().save(os.path.join(out, "s2_new_full.png"))
    print("S1 and S2 new designs saved!")
