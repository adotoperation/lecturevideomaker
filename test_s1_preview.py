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
    """
    어법 중요 / 서술형 중요 별표 뱃지
    """
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
    else: # writing
        fill_bg = (65, 50, 18)
        border_col = (250, 204, 21)
        text_col = (255, 235, 130)
        
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=10, fill=fill_bg, outline=border_col, width=2)
    draw.text((bx1 + pad_h, by1 + pad_v - 2), text, fill=text_col, font=font_badge)

def render_s1_state(state: int) -> Image.Image:
    im = render_board_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)
    font_mono = get_mono_font(44)
    char_w = 24.0
    sx = 100
    y1, y2 = 280, 440

    l1 = "1. Speakers / (don't always) / put / everything / (that's important"
    l2 = "   / (to them)) / (into words)."
    draw.text((sx, y1), l1, fill=COLOR_WHITE, font=font_mono)
    draw.text((sx, y2), l2, fill=COLOR_WHITE, font=font_mono)

    if state >= 1:
        # Speakers -> S
        draw_main_clause_tag(draw, sx + int(3*char_w), sx + int(11*char_w), y1, "S", COLOR_S_BLUE)
    if state >= 2:
        # put -> Vt
        draw_main_clause_tag(draw, sx + int(31*char_w), sx + int(34*char_w), y1, "Vt", COLOR_V_ROSE, double_u=True)
    if state >= 3:
        # everything -> O
        draw_main_clause_tag(draw, sx + int(37*char_w), sx + int(47*char_w), y1, "O", COLOR_O_EMERALD)
    if state >= 4:
        # that's -> S, important -> SC
        draw_dep_clause_tag(draw, sx + int(51*char_w), sx + int(57*char_w), y1, "S", COLOR_S_BLUE)
        draw_dep_clause_tag(draw, sx + int(58*char_w), sx + int(67*char_w), y1, "SC", COLOR_SC_INDIGO)
        draw_modifier_arrow_safe(draw, sx + int(50*char_w) + 12, y1 + 56, sx + int(47*char_w) + 8, y1 + 48)

    # 1. 사용자의 요청: 직독직해 끊어 읽기 박스와 핵심포인트 바는 완전히 삭제! (학생들이 강의를 들으며 필기 유도)
    # 2. 어법, 서술형 설명 시 해당 부분에 별표(★)와 어법 중요 / 서술형 중요 라벨 표시!
    if state == 8:
        # 어법 중요 표시
        # (1) don't always 상단
        x_not_always = sx + int(14 * char_w)
        draw_important_badge(draw, x_not_always, y1 - 90, "★ 어법 중요: not always (부분부정)", badge_type='grammar')
        # (2) that's important 상단
        x_rel_clause = sx + int(50 * char_w)
        draw_important_badge(draw, x_rel_clause - 80, y1 - 90, "★ 어법 중요: everything 단수 수일치 is", badge_type='grammar')
        
    elif state == 9:
        # 서술형 중요 표시
        # put everything that's important to them into words 구동사 + 관계사절
        # 구문 강조 테두리
        box_x1 = sx + int(30 * char_w)
        box_y1 = y1 - 15
        box_x2 = sx + int(68 * char_w) + 20
        box_y2 = y2 + 65
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, outline=COLOR_YELLOW, width=3)
        
        # 상단 서술형 중요 뱃지
        draw_important_badge(draw, box_x1, y1 - 85, "★ 서술형 중요: [put A into words] 구동사 + 관계대명사 후치수식", badge_type='writing')

    return im

if __name__ == "__main__":
    os.makedirs("output/test_preview", exist_ok=True)
    s8 = render_s1_state(8)
    s8.save("output/test_preview/s1_state8_grammar.png")
    s9 = render_s1_state(9)
    s9.save("output/test_preview/s1_state9_writing.png")
    s3 = render_s1_state(3)
    s3.save("output/test_preview/s1_state3_clean.png")
    print("Preview images saved successfully!")
