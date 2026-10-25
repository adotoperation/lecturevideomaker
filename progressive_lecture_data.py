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

COLOR_S_BLUE = (96, 165, 250)       # Blue #60A5FA (주어 S)
COLOR_V_ROSE = (248, 113, 113)      # Rose Pink #F87171 (동사 Vi/Vt)
COLOR_O_EMERALD = (52, 211, 153)    # Emerald #34D399 (목적어 O)
COLOR_SC_INDIGO = (129, 140, 248)   # Indigo #818CF8 (주격보어 SC)
COLOR_SKY_TRIANGLE = (56, 189, 248) # Sky Blue #38BDF8 (접속사 세모)
COLOR_SALMON_TITLE = (255, 144, 138)# Salmon Pink #FF908A (요약 제목)
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
    """
    접속사 단어를 완전히 포괄(둘러싸는/겹치는)하는 세모(△) 도형 그리기
    """
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

def draw_important_badge(draw, x, y, text, badge_type='grammar'):
    """어법 중요 / 서술형 중요 별표(★) 배지"""
    font_badge = get_kr_font(22, bold=True)
    tb = draw.textbbox((0, 0), text, font=font_badge)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    pad_h = 16
    pad_v = 8
    bx1 = x
    by1 = y
    bx2 = x + tw + pad_h * 2
    by2 = y + th + pad_v * 2
    if badge_type == 'grammar':
        fill_bg = (60, 24, 28)
        border_col = (248, 113, 113)
        text_col = (255, 180, 180)
    else:
        fill_bg = (65, 50, 18)
        border_col = (250, 204, 21)
        text_col = (255, 235, 130)
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=10, fill=fill_bg, outline=border_col, width=2)
    draw.text((bx1 + pad_h, by1 + pad_v - 2), text, fill=text_col, font=font_badge)

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

def render_summary_slide():
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)

    topic = "비언어적 소통의 중요성과 의도 숨기기의 어려움"
    vocab_list = [
        ("nonverbal", "비언어적인"),
        ("meaning", "의미, 의도"),
        ("conceal", "숨기다, 감추다")
    ]
    summary_list = [
        {
            "title": "화자의 불완전한 언어 표현과\n비언어적 전달의 중요성",
            "body": "화자는 자신에게 중요한 모든 것을 말로\n다 표현하지 않으며, 상당 부분의 의미가\n목소리 톤이나 표정, 몸짓 등 비언어적\n신호를 통해 전달된다."
        },
        {
            "title": "비언어적 신호의 오해 가능성과\n적극적 확인의 필요성",
            "body": "비언어적 행동은 주관적으로 오해하기\n쉬우므로, 효과적인 청자는 상대방의\n의도를 말로 직접 물어 확인하여 소통의\n오류를 방지한다."
        },
        {
            "title": "대면 집단 토론에서의\n의도와 감정 은폐의 불가능성",
            "body": "프로이트의 통찰처럼 입술이 침묵해도\n손가락 끝이나 온몸의 신호로 속마음이\n스며 나오므로, 대면 토론에서 진정한\n의미를 숨기기는 사실상 불가능하다."
        }
    ]

    # 1. 지문 주제 카드
    draw.rounded_rectangle([100, 155, 1820, 275], radius=20, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    pin_x, pin_y = 145, 195
    draw.polygon([(pin_x, pin_y), (pin_x + 14, pin_y - 8), (pin_x + 22, pin_y + 4), (pin_x + 8, pin_y + 12)], fill=(239, 68, 68))
    draw.ellipse([pin_x + 4, pin_y - 6, pin_x + 18, pin_y + 8], fill=(248, 113, 113))
    draw.line([(pin_x, pin_y + 8), (pin_x - 10, pin_y + 22)], fill=(203, 213, 225), width=3)

    font_topic_label = get_kr_font(28, bold=True)
    draw.text((185, 192), "지문 주제", fill=COLOR_YELLOW, font=font_topic_label)
    font_topic_val = get_kr_font(28, bold=True)
    draw.text((340, 192), topic, fill=COLOR_WHITE, font=font_topic_val)

    # 2. 핵심 어휘 3개 카드
    card_w = 540
    gap = 50
    start_x = 100
    font_v_en = get_kr_font(30, bold=True)
    font_v_kr = get_kr_font(22, bold=False)

    for i in range(3):
        cx = start_x + i * (card_w + gap)
        draw.rounded_rectangle([cx, 300, cx + card_w, 425], radius=20, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
        en_w, kr_m = vocab_list[i]
        tb_en = draw.textbbox((0, 0), en_w, font=font_v_en)
        w_en = tb_en[2] - tb_en[0]
        draw.text((cx + (card_w - w_en) // 2, 325), en_w, fill=COLOR_YELLOW, font=font_v_en)
        tb_kr = draw.textbbox((0, 0), kr_m, font=font_v_kr)
        w_kr = tb_kr[2] - tb_kr[0]
        draw.text((cx + (card_w - w_kr) // 2, 372), kr_m, fill=COLOR_WHITE, font=font_v_kr)

    # 3. 3단 핵심 요약 카드
    card_h = 475
    font_sum_title = get_kr_font(25, bold=True)
    font_sum_body = get_kr_font(21, bold=False)

    for i in range(3):
        cx = start_x + i * (card_w + gap)
        draw.rounded_rectangle([cx, 450, cx + card_w, 450 + card_h], radius=28, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
        s_item = summary_list[i]
        t_lines = s_item["title"].split("\n")
        ty = 490
        for tl in t_lines:
            draw.text((cx + 40, ty), tl, fill=COLOR_SALMON_TITLE, font=font_sum_title)
            ty += 38
        b_lines = s_item["body"].split("\n")
        by = ty + 30
        for bl in b_lines:
            draw.text((cx + 40, by), bl, fill=COLOR_WHITE, font=font_sum_body)
            by += 35

    return im

def render_sentence_state(s_idx: int, state: int) -> Image.Image:
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(44)
    char_w = 24.0
    sx = 100

    if s_idx == 1:
        y1, y2 = 340, 520
        l1 = "1. Speakers / (don't always) / put / everything / (that's important"
        l2 = "   / (to them)) / (into words)."
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

        # State 1+: S under Speakers
        if state >= 1:
            draw_main_clause_tag(draw, sx + int(3*char_w), sx + int(11*char_w), y1, "S", COLOR_S_BLUE)
        # State 2+: Vt under put
        if state >= 2:
            draw_main_clause_tag(draw, sx + int(31*char_w), sx + int(34*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
        # State 3+: O under everything
        if state >= 3:
            draw_main_clause_tag(draw, sx + int(37*char_w), sx + int(47*char_w), y1, "O", COLOR_O_EMERALD)
        # State 4+: that's S, important SC above, arrow
        if state >= 4:
            draw_dep_clause_tag(draw, sx + int(51*char_w), sx + int(57*char_w), y1, "S", COLOR_S_BLUE)
            draw_dep_clause_tag(draw, sx + int(58*char_w), sx + int(67*char_w), y1, "SC", COLOR_SC_INDIGO)
            draw_modifier_arrow_safe(draw, sx + int(50*char_w) + 12, y1 + 56, sx + int(47*char_w) + 8, y1 + 48)

    elif s_idx == 2:
        y1, y2, y3, y4 = 230, 375, 520, 665
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
            # Encompassing triangle for 'and'
            draw_encompassing_triangle(draw, sx + int(42*char_w), sx + int(45*char_w), y4)

    elif s_idx == 3:
        y1, y2, y3 = 280, 440, 600
        l1 = "3. (As it is easy / [to misinterpret / nonverbal behavior]),"
        l2 = "   / effective listeners / (verbally) / confirm / their interpretations"
        l3 = "   / (of someone's nonverbal communication)."
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)

        if state >= 1:
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

    elif s_idx == 4:
        y1, y2 = 340, 520
        l1 = "4. A question / (as simple as \"Do your nods indicate a yes vote?\")"
        l2 = "   / can make sure / [that everyone / is / (on the same wavelength)]."
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

        if state >= 1:
            draw_main_clause_tag(draw, sx + int(3*char_w), sx + int(13*char_w), y1, "S", COLOR_S_BLUE)
        if state >= 3:
            draw_main_clause_tag(draw, sx + int(5*char_w), sx + int(18*char_w), y2, "Vt", COLOR_V_ROSE, double_u=True)
        if state >= 4:
            draw_encompassing_triangle(draw, sx + int(22*char_w), sx + int(26*char_w), y2)
            draw_dep_clause_tag(draw, sx + int(27*char_w), sx + int(35*char_w), y2, "S", COLOR_S_BLUE)
            draw_dep_clause_tag(draw, sx + int(38*char_w), sx + int(40*char_w), y2, "Vi", COLOR_V_ROSE)

    elif s_idx == 5:
        y1, y2, y3, y4 = 230, 375, 520, 665
        l1 = "5. (If, / (as nonverbal research indicates), / more than half"
        l2 = "   / (of a speaker's meaning) / is conveyed / (nonverbally)),"
        l3 = "   / we / are missing / a lot of important information"
        l4 = "   / (if we fail / [to \"listen\" / (to nonverbal behavior)])."
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y4), l4, fill=COLOR_WHITE, font=font_mono)

        if state >= 1:
            draw_encompassing_triangle(draw, sx + int(4*char_w), sx + int(6*char_w), y1)
            draw_encompassing_triangle(draw, sx + int(11*char_w), sx + int(13*char_w), y1)
            draw_dep_clause_tag(draw, sx + int(47*char_w), sx + int(61*char_w), y1, "S", COLOR_S_BLUE)
        if state >= 2:
            draw_dep_clause_tag(draw, sx + int(32*char_w), sx + int(43*char_w), y2, "V", COLOR_V_ROSE)
        if state >= 3:
            draw_main_clause_tag(draw, sx + int(5*char_w), sx + int(7*char_w), y3, "S", COLOR_S_BLUE)
        if state >= 4:
            draw_main_clause_tag(draw, sx + int(10*char_w), sx + int(21*char_w), y3, "Vt", COLOR_V_ROSE, double_u=True)
        if state >= 5:
            draw_main_clause_tag(draw, sx + int(24*char_w), sx + int(54*char_w), y3, "O", COLOR_O_EMERALD)
        if state >= 6:
            draw_encompassing_triangle(draw, sx + int(6*char_w), sx + int(8*char_w), y4)
            draw_dep_clause_tag(draw, sx + int(9*char_w), sx + int(11*char_w), y4, "S", COLOR_S_BLUE)
            draw_dep_clause_tag(draw, sx + int(12*char_w), sx + int(16*char_w), y4, "Vi", COLOR_V_ROSE)

    elif s_idx == 6:
        y1, y2, y3 = 280, 440, 600
        l1 = "6. (Even) Freud / suggested / [that \"he / (that has eyes / to see"
        l2 = "   / and ears / to hear) / may convince / himself"
        l3 = "   / [that no mortal / can keep / a secret]].\""
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)

        if state >= 1:
            draw_main_clause_tag(draw, sx + int(10*char_w), sx + int(15*char_w), y1, "S", COLOR_S_BLUE)
        if state >= 2:
            draw_main_clause_tag(draw, sx + int(18*char_w), sx + int(27*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
        if state >= 3:
            draw_encompassing_triangle(draw, sx + int(31*char_w), sx + int(35*char_w), y1)
            draw_dep_clause_tag(draw, sx + int(37*char_w), sx + int(39*char_w), y1, "S", COLOR_S_BLUE)
        if state >= 4:
            draw_encompassing_triangle(draw, sx + int(5*char_w), sx + int(8*char_w), y2)
            draw_modifier_arrow_safe(draw, sx + int(42*char_w), y1 + 54, sx + int(38*char_w) + 12, y1 + 48)
        if state >= 5:
            draw_dep_clause_tag(draw, sx + int(27*char_w), sx + int(39*char_w), y2, "Vt", COLOR_V_ROSE)
            draw_dep_clause_tag(draw, sx + int(42*char_w), sx + int(49*char_w), y2, "O", COLOR_O_EMERALD)
        if state >= 6:
            draw_encompassing_triangle(draw, sx + int(6*char_w), sx + int(10*char_w), y3)
            draw_dep_clause_tag(draw, sx + int(11*char_w), sx + int(20*char_w), y3, "S", COLOR_S_BLUE)
            draw_dep_clause_tag(draw, sx + int(23*char_w), sx + int(31*char_w), y3, "Vt", COLOR_V_ROSE)
            draw_dep_clause_tag(draw, sx + int(34*char_w), sx + int(42*char_w), y3, "O", COLOR_O_EMERALD)

    elif s_idx == 7:
        y1, y2 = 340, 520
        l1 = "7. (If his lips / are / silent), / he / chatters / (with his fingertips);"
        l2 = "   / betrayal / oozes out / (of him) / (at every pore)."
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

        if state >= 1:
            draw_encompassing_triangle(draw, sx + int(4*char_w), sx + int(6*char_w), y1)
            draw_dep_clause_tag(draw, sx + int(7*char_w), sx + int(15*char_w), y1, "S", COLOR_S_BLUE)
            draw_dep_clause_tag(draw, sx + int(18*char_w), sx + int(21*char_w), y1, "Vi", COLOR_V_ROSE)
            draw_dep_clause_tag(draw, sx + int(24*char_w), sx + int(30*char_w), y1, "SC", COLOR_SC_INDIGO)
        if state >= 2:
            draw_main_clause_tag(draw, sx + int(35*char_w), sx + int(37*char_w), y1, "S", COLOR_S_BLUE)
            draw_main_clause_tag(draw, sx + int(40*char_w), sx + int(48*char_w), y1, "Vi", COLOR_V_ROSE, double_u=True)
        if state >= 3:
            draw_main_clause_tag(draw, sx + int(5*char_w), sx + int(13*char_w), y2, "S", COLOR_S_BLUE)
            draw_main_clause_tag(draw, sx + int(16*char_w), sx + int(25*char_w), y2, "Vi", COLOR_V_ROSE, double_u=True)

    elif s_idx == 8:
        y1, y2, y3 = 280, 440, 600
        l1 = "8. (No wonder) / it / is / difficult / (for most people)"
        l2 = "   / [to conceal / [what they / mean / and feel]]"
        l3 = "   / (in a face-to-face group discussion)."
        draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)
        draw.text((sx, y3), l3, fill=COLOR_WHITE, font=font_mono)

        if state >= 2:
            draw_dep_clause_tag(draw, sx + int(17*char_w), sx + int(19*char_w), y1, "가S", COLOR_S_BLUE)
            draw_main_clause_tag(draw, sx + int(22*char_w), sx + int(24*char_w), y1, "Vi", COLOR_V_ROSE, double_u=True)
            draw_dep_clause_tag(draw, sx + int(27*char_w), sx + int(36*char_w), y1, "SC", COLOR_SC_INDIGO)
        if state >= 3:
            draw_dep_clause_tag(draw, sx + int(44*char_w), sx + int(55*char_w), y1, "의미상S", COLOR_S_BLUE)
        if state >= 4:
            draw_dep_clause_tag(draw, sx + int(6*char_w), sx + int(16*char_w), y2, "Vt", COLOR_V_ROSE)
        if state >= 5:
            draw_encompassing_triangle(draw, sx + int(20*char_w), sx + int(24*char_w), y2)
            draw_dep_clause_tag(draw, sx + int(25*char_w), sx + int(29*char_w), y2, "S", COLOR_S_BLUE)
            draw_dep_clause_tag(draw, sx + int(32*char_w), sx + int(36*char_w), y2, "Vt", COLOR_V_ROSE)
            draw_encompassing_triangle(draw, sx + int(39*char_w), sx + int(42*char_w), y2)
            draw_dep_clause_tag(draw, sx + int(43*char_w), sx + int(47*char_w), y2, "Vt", COLOR_V_ROSE)

    return im

# All Narration Chunks (완벽한 직독직해 + 문장구조 분석 동시 설명, 기호 알파벳 읽지 않기, 1.0s 텀, 일관된 1타 강사 발화)
LECTURE_CHUNKS = {
    0: [
        (0, "친구들 안녕! 오늘 같이 분석해 볼 지문은 2026년 고3 6월 모의고사 삼십이 번이야. 비언어적 소통의 중요성과 의도를 숨기기 어렵다는 주제를 다룬 핵심 빈칸 문항이야. 모든 문장을 하나도 빠짐없이 완벽하게 직독직해하고 구문 구조를 파헤쳐 볼 테니까 집중해서 잘 따라와 줘. 자, 그럼 첫 번째 문장부터 바로 들어가 보자!")
    ],
    1: [
        (0, "1번 문장 직독직해와 구조 분석이야."),
        (1, "주어인 화자는,"),
        (2, "항상 말로 표현하는 것은 아니다이고, 타동사야. 항상 하는 건 아니다라는 부분부정이 들어가 있어."),
        (3, "모든 것을은 목적어야. 그래서 주절이 3형식이야."),
        (4, "중요한으로 해석해 주격 관계대명사 절이고 앞의 모든 것을 수식하고 있고, 중요한이 주격보어 역할을 하는 2형식 문장이야."),
        (5, "그들에게이며, 전명구가 부사구의 역할을 하고 있어."),
        (6, "풋 인투 워드는 하나로 묶어서 구동사의 역할을 하고 있다는 거 중요해. 말로라는 전명구 부사구 거품이야. 주절 3형식에 2형식 형용사절이 결합된 완전한 문장이야.")
    ],
    2: [
        (0, "2번 문장 직독직해와 구조 분석이야."),
        (1, "문장 맨 앞의 매우 흔하게는 부사구 거품이야."),
        (2, "주어인 너는,"),
        (3, "조동사와 결합된 이해할 수 있다는 타동사야."),
        (4, "화자의 의미를은 목적어야. 그래서 주절이 3형식이야."),
        (5, "그들의 비언어적 행동들을 관찰함으로써는 수단을 나타내는 전명구 부사구야. 준동사 관찰하는 것은 타동사이고, 그들의 비언어적 행동들은 준동사의 목적어야."),
        (6, "목소리 톤이나 음량의 변화, 시선 교환, 얼굴 표정, 그리고 몸짓과 같은은 비언어적 행동의 구체적인 예시를 나열하는 거품이야. 접속사 and는 단어를 세모로 포괄해 줘. 주절 3형식에 준동사구와 병렬 구조가 연결된 문장이야.")
    ],
    3: [
        (0, "3번 문장 직독직해와 구조 분석이야."),
        (1, "비언어적 행동을 오해하기 쉽기 때문에라는 이유의 부사절이야. 접속사 As를 세모로 포괄하고, 그것은은 가주어, 이다는 자동사, 쉬운은 주격보어야."),
        (2, "진주어인 비언어적 행동을 오해하는 것은 대괄호로 묶고, 준동사 오해하다는 타동사, 비언어적 행동은 준동사의 목적어야."),
        (3, "주절의 주어인 효과적인 청자들은,"),
        (4, "말로라는 부사 거품을 거쳐, 확인한다는 타동사야."),
        (5, "그들의 해석을은 목적어야. 그래서 주절이 3형식이야."),
        (6, "누군가의 비언어적 소통에 대한은 전명구 부사구 거품이야. 이유 부사절과 주절의 3형식이 결합된 문장이야.")
    ],
    4: [
        (0, "4번 문장 직독직해와 구조 분석이야."),
        (1, "주어인 질문은,"),
        (2, "당신의 끄덕임이 찬성을 나타내나요만큼 간단한은 주어를 수식하는 동등비교 형용사구 거품이야."),
        (3, "확실히 할 수 있다는 조동사와 결합된 타동사구야."),
        (4, "모두가 같은 파장 위에 즉 같은 이해를 공유하고 있다는 것을은 목적어 역할을 하는 명사절이야. 접속사 that을 세모로 포괄해 줘."),
        (5, "명사절 안에서 모두가는 종속절 주어, 이다는 자동사, 같은 파장 위에는 전명구 거품이야. 1형식 명사절이 목적어로 결합된 완전한 3형식 문장이야.")
    ],
    5: [
        (0, "5번 문장 직독직해와 구조 분석이야."),
        (1, "조건 부사절인 만약 비언어적 연구가 보여주듯이, 화자의 의미의 절반 이상이 비언어적으로 전달된다면이야. 접속사 If와 as를 세모로 포괄해 줘."),
        (2, "절반 이상은 종속절 주어이고, 전달된다는 수동태 동사야. 비언어적으로는 부사구 거품이야."),
        (3, "주절의 주어인 우리는,"),
        (4, "놓치고 있다는 진행형 타동사야."),
        (5, "많은 중요한 정보를은 목적어야. 그래서 주절이 3형식이야."),
        (6, "만약 우리가 비언어적 행동을 귀담아듣지 못한다면은 두 번째 조건 부사절 거품이야. 접속사 if를 세모로 포괄해 줘. 실패하다는 자동사, 귀담아듣는 것은 준동사구야. 조건절 2개와 주절 3형식이 결합된 문장이야.")
    ],
    6: [
        (0, "6번 문장 직독직해와 구조 분석이야."),
        (1, "부사 거품인 심지어를 거쳐, 주어인 프로이트는,"),
        (2, "시사했다는 타동사야."),
        (3, "뒤이어 인용된 문장 전체가 목적어 명사절이야. 접속사 that을 세모로 포괄해 줘. 종속절의 주어는 그 사람이야."),
        (4, "볼 눈과 들을 귀를 가진은 그 사람을 수식하는 주격 관계대명사절이야. 접속사 and를 세모로 포괄하고, 앞의 선행사 그 사람을 향해 수식 화살표를 달아줘."),
        (5, "스스로에게 확신시킬 수 있다는 조동사와 결합된 타동사와 재귀대명사 목적어야."),
        (6, "어떤 인간도 비밀을 지킬 수 없다는 것을은 두 번째 목적어 명사절이야. 접속사 that을 세모로 포괄해 줘. 어떤 인간도 주어, 지킬 수 있다 타동사, 비밀을 목적어의 3형식 명사절이야. 복합 명사절이 중첩된 고난도 3형식 문장이야.")
    ],
    7: [
        (0, "7번 문장 직독직해와 구조 분석이야."),
        (1, "만약 그의 입술이 침묵한다면은 조건 부사절이야. 접속사 If를 세모로 포괄하고, 그의 입술은 주어, 이다는 자동사, 침묵하는은 주격보어인 2형식 부사절이야."),
        (2, "첫 번째 주절에서 주어인 그는, 본동사인 재잘거린다는 자동사야. 손가락 끝으로는 전명구 부사구 거품이야. 1형식 문장이야."),
        (3, "세미콜론 뒤 두 번째 주절에서 주어인 배신은, 본동사인 스며 나온다는 자동사 구동사야. 그에게서와 모든 모공에서는 전명구 부사구 거품이야. 역시 1형식 문장이야. 조건 부사절과 2개의 1형식 주절이 대등하게 연결된 구조야.")
    ],
    8: [
        (0, "8번 문장 직독직해와 구조 분석이야."),
        (1, "놀랄 일도 아니다, 자연스럽다는 관용 표현 부사구 거품이야."),
        (2, "가주어인 그것은, 본동사인 이다는 자동사, 어려운은 주격보어야. 2형식 주절의 뼈대야."),
        (3, "대부분의 사람들에게는 to부정사의 의미상 주어 거품이야."),
        (4, "진주어인 자신이 의미하고 느끼는 바를 숨기는 것은 대괄호로 묶어줘. 준동사 숨기다는 타동사야."),
        (5, "그들이 의미하고 느끼는 것을은 준동사의 목적어 명사절이야. 관계대명사 what과 접속사 and를 세모로 포괄해 줘. 그들은 주어, 의미하고 느낀다는 타동사야."),
        (6, "대면 집단 토론에서는 전명구 부사구 거품이야. 가주어 진주어와 3형식 준동사구가 결합된 완전한 문장이야.")
    ],
    9: [
        (0, "오늘 배운 삼십이 번 지문 핵심 내용을 최종 정리해보자."),
        (0, "이 지문의 주제는 '비언어적 소통의 중요성과 의도 숨기기의 어려움'이야."),
        (0, "핵심 어휘 세 개를 살펴보면, 첫째로 nonverbal은 비언어적인이라는 뜻이야. 둘째로 meaning은 의미나 의도를 뜻해. 셋째로 conceal은 숨기다, 감추다라는 뜻이야."),
        (0, "이어서 삼단 내용 정리야. 첫 번째 내용으로는 '화자의 불완전한 언어 표현과 비언어적 전달의 중요성'이야. 화자는 중요한 모든 것을 말로 표현하지 않으며, 많은 의미가 비언어적 신호로 전달돼."),
        (0, "두 번째 내용으로는 '비언어적 신호의 오해 가능성과 적극적 확인의 필요성'이야. 비언어적 신호는 오해하기 쉬우니, 좋은 청자는 상대방에게 말로 직접 물어 확인해야 해."),
        (0, "세 번째 내용으로는 '대면 집단 토론에서의 의도와 감정 은폐의 불가능성'이야. 프로이트가 말했듯 아무리 침묵해도 온몸의 신호로 진실이 드러나므로, 대면 토론에서 속마음을 숨기는 것은 불가능하다는 결론이었지."),
        (0, "오늘 정리한 어휘와 삼단 요약을 꼼꼼히 복습하면서 삼십이 번 지문 완벽하게 마스터하자. 수고 많았어 친구들!")
    ]
}
