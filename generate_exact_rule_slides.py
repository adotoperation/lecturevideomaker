import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont

# Fonts
FONT_CONSOLAS_BOLD = r"C:\Windows\Fonts\consolab.ttf"
FONT_CONSOLAS_REG = r"C:\Windows\Fonts\consola.ttf"
FONT_MALGUN_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_MALGUN_REG = r"C:\Windows\Fonts\malgun.ttf"

def get_mono_font(size: int, bold: bool = True):
    p = FONT_CONSOLAS_BOLD if bold else FONT_CONSOLAS_REG
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()

def get_kr_font(size: int, bold: bool = True):
    p = FONT_MALGUN_BOLD if bold else FONT_MALGUN_REG
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()

# Colors (100% STYLE_GUIDE.md & Google Slides Standard)
COLOR_BOARD_BG = (17, 48, 34)       # #113022
COLOR_FRAME_WOOD = (62, 39, 35)     # #3E2723
COLOR_PILL_BG = (22, 59, 42)        # #163B2A
COLOR_PILL_BORDER = (46, 99, 73)    # #2E6349
COLOR_YELLOW = (248, 204, 21)       # #F8CC15
COLOR_WHITE = (255, 255, 255)       # #FFFFFF

# Constituent Colors (교안 서식 원칙 기준)
COLOR_S_BLUE = (96, 165, 250)       # Blue #60A5FA (주어 S)
COLOR_V_ROSE = (248, 113, 113)      # Rose Pink #F87171 (동사 Vi/Vt)
COLOR_O_EMERALD = (52, 211, 153)    # Emerald #34D399 (목적어 O)
COLOR_SC_INDIGO = (129, 140, 248)   # Indigo #818CF8 (주격보어 SC)
COLOR_OC_PURPLE = (192, 132, 252)   # Purple #C084FC (목적격보어 OC)
COLOR_WHITE_TEXT = (255, 255, 255)  # 일반 텍스트, 괄호
COLOR_SKY_TRIANGLE = (56, 189, 248) # Sky Blue #38BDF8 (접속사 세모)
COLOR_SLASH_PURPLE = (192, 132, 252)# Purple #C084FC (슬래시)
COLOR_SALMON_TITLE = (255, 144, 138)# Salmon Pink #FF908A (요약 제목)

def render_google_slides_base(title: str = "2026년 고3 6월 32번") -> Image.Image:
    width, height = 1920, 1080
    im = Image.new("RGB", (width, height), COLOR_BOARD_BG)
    draw = ImageDraw.Draw(im)

    # 16px 마호가니 원목 프레임
    fw = 16
    draw.rectangle([0, 0, width, fw], fill=COLOR_FRAME_WOOD)
    draw.rectangle([0, height - fw, width, height], fill=COLOR_FRAME_WOOD)
    draw.rectangle([0, 0, fw, height], fill=COLOR_FRAME_WOOD)
    draw.rectangle([width - fw, 0, width, height], fill=COLOR_FRAME_WOOD)

    # 좌측 타이틀 알약 (구글 슬라이드 12pt 비율 -> 34px)
    font_pill = get_kr_font(34, bold=True)
    tb_pill = draw.textbbox((0, 0), title, font=font_pill)
    pw = max(420, (tb_pill[2] - tb_pill[0]) + 80)
    draw.rounded_rectangle([74, 50, 74 + pw, 142], radius=18, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    draw.text((74 + 40, 73), title, fill=COLOR_YELLOW, font=font_pill)

    # 우측 브랜드 텍스트 (구글 슬라이드 13pt 비율 -> 38px)
    font_logo = get_kr_font(38, bold=True)
    draw.text((1520, 73), "에이닷 영어학원", fill=COLOR_WHITE, font=font_logo)

    return im

def draw_modifier_arrow_safe(draw: ImageDraw.Draw, start_x: float, start_y: float, end_x: float, end_y: float, color=COLOR_WHITE_TEXT, width=3):
    """
    수식 화살표: modifier 시작 괄호 '(' 아래에서 출발하여
    선행사 단어 밑줄 끝(안전 구역)을 향해 좌상단(↖)으로 뻗는 곡선 화살표.
    단어 글자를 절대 침범하거나 가리지 않도록 좌표 계산.
    """
    p0 = (start_x, start_y)
    p1 = (start_x - 18, start_y + 10)
    p2 = (end_x, end_y)

    pts = []
    steps = 20
    for i in range(steps + 1):
        t = i / float(steps)
        x = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        pts.append((x, y))

    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)

    # Arrowhead at end pointing along tangent towards ↖
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

def render_slide_00_cover(title: str = "2026년 고3 6월 모의고사 - 32번 지문", topic: str = "비언어적 소통의 중요성과 의도 숨기기의 어려움") -> Image.Image:
    im = render_google_slides_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)

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

def render_slide_sentence(slide_title: str, line_data: list) -> Image.Image:
    im = render_google_slides_base(slide_title)
    draw = ImageDraw.Draw(im)

    # 구글 슬라이드 16pt 기준 -> 46px
    font_mono = get_mono_font(46, bold=True)
    font_tag_main = get_mono_font(30, bold=True)   # 주절 기호 (상단, 정규 크기)
    font_tag_quasi = get_mono_font(21, bold=True)  # 준동사 기호 (상단, 상대적으로 작게!)
    font_triangle = get_kr_font(28, bold=True)

    char_w = 25.0 # Consolas 46 정확 advance width

    # [원칙 1: 기본 좌측 정렬, 우측 공간 넓게 활용]
    line_start_x = 120

    num_lines = len(line_data)
    if num_lines <= 2:
        first_line_y = 360
        line_gap = 180
    elif num_lines == 3:
        first_line_y = 290
        line_gap = 160
    else:
        first_line_y = 240
        line_gap = 145

    for line_idx, l in enumerate(line_data):
        text_line = l.get("text", "")
        tags = l.get("tags", [])
        triangles = l.get("triangles", [])
        arrows = l.get("arrows", [])
        
        cur_text_y = first_line_y + line_idx * line_gap
        
        # 글자별 색상 매핑
        char_colors = [COLOR_WHITE_TEXT] * len(text_line)
        for t in tags:
            c_start = t["col_start"]
            c_end = t["col_end"]
            c_color = t.get("color", COLOR_WHITE_TEXT)
            for ci in range(c_start, min(c_end, len(text_line))):
                char_colors[ci] = c_color
                
        # 1. 영문 본문 텍스트 출력
        for ci, ch in enumerate(text_line):
            cx = line_start_x + int(ci * char_w)
            draw.text((cx, cur_text_y), ch, fill=char_colors[ci], font=font_mono)

        # 2. 문장 성분 태그 및 밑줄 처리
        # [원칙 2: 준동사, 주절의 문장기호는 모두 영어 단어 위에 위치!]
        for t in tags:
            c_start = t["col_start"]
            c_end = t["col_end"]
            tag_str = t.get("tag", "")
            t_color = t.get("color", COLOR_WHITE_TEXT)
            has_u = t.get("underline", False)
            has_double_u = t.get("double_underline", False)
            is_quasi = t.get("is_quasi", False) # 준동사 여부

            tx1 = line_start_x + int(c_start * char_w)
            tx2 = line_start_x + int(c_end * char_w)

            # 주절: 단어 아래 밑줄
            if has_u:
                uy = cur_text_y + 48
                draw.line([(tx1, uy), (tx2, uy)], fill=t_color, width=3)
                if has_double_u:
                    draw.line([(tx1, uy + 6), (tx2, uy + 6)], fill=t_color, width=2)

            # 성분 기호 (단어 상단에 배치!)
            if tag_str:
                f_tag = font_tag_quasi if is_quasi else font_tag_main
                tb_tg = draw.textbbox((0, 0), tag_str, font=f_tag)
                tg_w = tb_tg[2] - tb_tg[0]
                tag_x = tx1 + (tx2 - tx1 - tg_w) // 2
                
                # 상단 배치 (글자 위 -30px)
                tag_y = cur_text_y - (26 if is_quasi else 32)
                draw.text((tag_x, tag_y), tag_str, fill=t_color, font=f_tag)

        # 3. 접속사 상단 세모 (△) 오버레이
        for tri_col in triangles:
            tri_x = line_start_x + int(tri_col * char_w) + 6
            tri_y = cur_text_y - 28
            draw.text((tri_x, tri_y), "△", fill=COLOR_SKY_TRIANGLE, font=font_triangle)

        # 4. 수식 화살표: 단어를 침범하지 않는 안전한 ↖ 곡선 화살표
        for arr_info in arrows:
            # (mod_col, ant_col)
            mod_col, ant_col = arr_info

            # modifier 시작 괄호 '(' 아래 출발 -> 선행사 밑줄 끝(안전 구역) 도착
            start_x = line_start_x + int(mod_col * char_w) + 12
            start_y = cur_text_y + 56
            end_x = line_start_x + int(ant_col * char_w) + 8
            end_y = cur_text_y + 48 # 글자 높이를 침범하지 않고 밑줄 끝에 안전 안착

            draw_modifier_arrow_safe(draw, start_x, start_y, end_x, end_y, color=COLOR_WHITE_TEXT, width=3)

    return im

def render_slide_last_summary(
    slide_title: str = "2026년 고3 6월 32번",
    topic: str = "비언어적 소통의 중요성과 의도 숨기기의 어려움"
) -> Image.Image:
    im = render_google_slides_base(slide_title)
    draw = ImageDraw.Draw(im)

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
    
    # Red Pin Graphic
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

def build_all_slides():
    out_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\exact_rule_slides"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Slide 0: Cover
    p0 = os.path.join(out_dir, "slide_00_cover.png")
    render_slide_00_cover().save(p0)
    print("Saved:", p0)

    # 2. Slide 1: Sentence 1
    # [좌측 정렬 + 모든 기호 단어 상단 배치 + 비침범 화살표]
    s1_lines = [
        {
            "text": "Speakers (don't always) put everything (that's important",
            "tags": [
                {"col_start": 0, "col_end": 8, "tag": "S", "color": COLOR_S_BLUE, "underline": True, "is_quasi": False},
                {"col_start": 24, "col_end": 27, "tag": "Vt", "color": COLOR_V_ROSE, "underline": True, "double_underline": True, "is_quasi": False},
                {"col_start": 28, "col_end": 38, "tag": "O", "color": COLOR_O_EMERALD, "underline": True, "is_quasi": False},
                {"col_start": 40, "col_end": 46, "tag": "S", "color": COLOR_S_BLUE, "underline": True, "is_quasi": False},
                {"col_start": 47, "col_end": 56, "tag": "SC", "color": COLOR_SC_INDIGO, "underline": True, "is_quasi": False}
            ],
            "triangles": [],
            "arrows": [(39, 38)] # mod_col 39 '(', ant_col 38 'everything' 끝 밑줄
        },
        {
            "text": "(to them)) (into words).",
            "tags": [],
            "triangles": [],
            "arrows": []
        }
    ]
    p1 = os.path.join(out_dir, "slide_01_sentence1.png")
    render_slide_sentence("2026년 고3 6월 32번", s1_lines).save(p1)
    print("Saved:", p1)

    # 3. Slide 2: Sentence 2
    # [좌측 정렬 + 주절/준동사 모든 기호 상단 배치]
    s2_lines = [
        {
            "text": "(Very often) you can understand a speaker's meaning",
            "tags": [
                {"col_start": 13, "col_end": 16, "tag": "S", "color": COLOR_S_BLUE, "underline": True, "is_quasi": False},
                {"col_start": 17, "col_end": 31, "tag": "Vt", "color": COLOR_V_ROSE, "underline": True, "double_underline": True, "is_quasi": False},
                {"col_start": 32, "col_end": 51, "tag": "O", "color": COLOR_O_EMERALD, "underline": True, "is_quasi": False}
            ],
            "triangles": [],
            "arrows": []
        },
        {
            "text": "(by [observing their nonverbal behaviors])",
            "tags": [
                {"col_start": 5, "col_end": 14, "tag": "Vt", "color": COLOR_V_ROSE, "underline": False, "is_quasi": True},
                {"col_start": 15, "col_end": 40, "tag": "O", "color": COLOR_O_EMERALD, "underline": False, "is_quasi": True}
            ],
            "triangles": [],
            "arrows": []
        },
        {
            "text": "such as a change (in a vocal tone or volume),",
            "tags": [],
            "triangles": [34],
            "arrows": []
        },
        {
            "text": "eye contact, facial expressions, and gestures).",
            "tags": [],
            "triangles": [33],
            "arrows": []
        }
    ]
    p2 = os.path.join(out_dir, "slide_02_sentence2.png")
    render_slide_sentence("2026년 고3 6월 32번", s2_lines).save(p2)
    print("Saved:", p2)

    # 4. Slide Last: Summary Slide
    p_last = os.path.join(out_dir, "slide_last_summary.png")
    render_slide_last_summary().save(p_last)
    print("Saved:", p_last)

if __name__ == "__main__":
    build_all_slides()
