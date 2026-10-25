import os
import sys
import re
import json
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

# Exact Google Slides Template Palette
COLOR_BOARD_BG = (17, 48, 34)       # #113022
COLOR_FRAME_WOOD = (62, 39, 35)     # #3E2723
COLOR_PILL_BG = (22, 59, 42)        # #163B2A
COLOR_PILL_BORDER = (46, 99, 73)    # #2E6349
COLOR_YELLOW = (248, 204, 21)       # #F8CC15
COLOR_WHITE = (255, 255, 255)       # #FFFFFF

# Word & Tag Colors in Slide 2
COLOR_PINK_VERB = (255, 112, 143)   # #FF708F (S, V, Vt, Vi words & tags)
COLOR_MINT_OBJ = (105, 240, 174)    # #69F0AE (O, O→, SC words & tags)
COLOR_WHITE_TEXT = (255, 255, 255)  # (General text, parenthesis, brackets)
COLOR_SKY_TRIANGLE = (56, 189, 248) # #38BDF8 (Triangle for conjunctions)

# Summary Slide Colors in Slide 17
COLOR_SALMON_TITLE = (255, 144, 138)# #FF908A (Summary Card Titles)
COLOR_CARD_BORDER = (46, 99, 73)    # #2E6349

def render_google_slides_base(title: str = "2026년 고3 6월 32번") -> Image.Image:
    """구글 슬라이드 원본 칠판 및 상단 헤더 100% 동일 구현"""
    width, height = 1920, 1080
    im = Image.new("RGB", (width, height), COLOR_BOARD_BG)
    draw = ImageDraw.Draw(im)

    # 16px 마호가니 원목 테두리
    fw = 16
    draw.rectangle([0, 0, width, fw], fill=COLOR_FRAME_WOOD)
    draw.rectangle([0, height - fw, width, height], fill=COLOR_FRAME_WOOD)
    draw.rectangle([0, 0, fw, height], fill=COLOR_FRAME_WOOD)
    draw.rectangle([width - fw, 0, width, height], fill=COLOR_FRAME_WOOD)

    # 좌측 타이틀 알약 박스 (X: 74, Y: 52, W: ~560, H: 88, Radius: 16)
    font_pill = get_kr_font(26, bold=True)
    tb_pill = draw.textbbox((0, 0), title, font=font_pill)
    pw = max(380, (tb_pill[2] - tb_pill[0]) + 70)
    draw.rounded_rectangle([74, 52, 74 + pw, 140], radius=16, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    draw.text((74 + 35, 78), title, fill=COLOR_YELLOW, font=font_pill)

    # 우측 브랜드 텍스트 (에이닷 영어학원)
    font_logo = get_kr_font(26, bold=True)
    draw.text((1570, 78), "에이닷 영어학원", fill=COLOR_WHITE, font=font_logo)

    return im

def render_slide_01_cover(title: str = "2026년 고3 6월 모의고사 - 32번 지문", topic: str = "비언어적 소통의 중요성과 의도 숨기기의 어려움") -> Image.Image:
    """구글 슬라이드 1번 표지 장표 100% 동일 렌더링"""
    im = render_google_slides_base("2026년 고3 6월 32번")
    draw = ImageDraw.Draw(im)

    # 중앙 대형 제목 (Y ≈ 380, Font: 60px Bold)
    font_title = get_kr_font(60, bold=True)
    tb_t = draw.textbbox((0, 0), title, font=font_title)
    tw = tb_t[2] - tb_t[0]
    draw.text(((1920 - tw) // 2, 360), title, fill=COLOR_WHITE, font=font_title)

    # 하단 둥근 주제 카드 (Y: 590, W: 1500, H: 150, Radius: 20)
    font_topic = get_kr_font(28, bold=True)
    tb_top = draw.textbbox((0, 0), topic, font=font_topic)
    top_w = tb_top[2] - tb_top[0]
    box_w = max(1100, top_w + 140)
    box_x = (1920 - box_w) // 2
    draw.rounded_rectangle([box_x, 590, box_x + box_w, 740], radius=20, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    draw.text((box_x + (box_w - top_w) // 2, 645), topic, fill=COLOR_YELLOW, font=font_topic)

    return im

def render_slide_sentence(
    slide_title: str,
    line_data: list, # List of lines: [{"text": str, "tags": [{"col_start": int, "col_end": int, "tag": str, "color": tuple, "underline": bool, "double_underline": bool}], "triangles": [col_idx]}]
) -> Image.Image:
    """
    구글 슬라이드 2번 장표 판서와 100% 동일한 Monospaced 정밀 구문분석 렌더러
    """
    im = render_google_slides_base(slide_title)
    draw = ImageDraw.Draw(im)

    font_mono = get_mono_font(38, bold=True)
    font_tag = get_mono_font(30, bold=True)
    font_triangle = get_kr_font(28, bold=True)

    char_w = 23 # Consolas 38px character width approx
    line_start_x = 120
    first_line_y = 265
    line_gap = 160 # Vertical gap between lines

    for line_idx, l in enumerate(line_data):
        text_line = l.get("text", "")
        tags = l.get("tags", [])
        triangles = l.get("triangles", [])
        
        cur_text_y = first_line_y + line_idx * line_gap
        cur_tag_y = cur_text_y + 50
        
        # Draw base white text
        # But color specific words according to tags
        char_colors = [COLOR_WHITE_TEXT] * len(text_line)
        for t in tags:
            c_start = t["col_start"]
            c_end = t["col_end"]
            c_color = t.get("color", COLOR_WHITE_TEXT)
            for ci in range(c_start, min(c_end, len(text_line))):
                char_colors[ci] = c_color
                
        # Draw each character
        for ci, ch in enumerate(text_line):
            cx = line_start_x + ci * char_w
            draw.text((cx, cur_text_y), ch, fill=char_colors[ci], font=font_mono)

        # Draw underlines & tags
        for t in tags:
            c_start = t["col_start"]
            c_end = t["col_end"]
            tag_str = t.get("tag", "")
            t_color = t.get("color", COLOR_WHITE_TEXT)
            has_u = t.get("underline", False)
            has_double_u = t.get("double_underline", False)

            tx1 = line_start_x + c_start * char_w
            tx2 = line_start_x + c_end * char_w

            # Underline
            if has_u:
                uy = cur_text_y + 44
                draw.line([(tx1, uy), (tx2, uy)], fill=t_color, width=3)
                if has_double_u:
                    draw.line([(tx1, uy + 6), (tx2, uy + 6)], fill=t_color, width=2)

            # Tag text centered beneath the constituent
            if tag_str:
                tb_tg = draw.textbbox((0, 0), tag_str, font=font_tag)
                tg_w = tb_tg[2] - tb_tg[0]
                tag_x = tx1 + (tx2 - tx1 - tg_w) // 2
                draw.text((tag_x, cur_tag_y), tag_str, fill=t_color, font=font_tag)

        # Draw triangles (△) over conjunctions
        for tri_col in triangles:
            # Over word (e.g. 'and' or 'or')
            tri_x = line_start_x + tri_col * char_w + 8
            tri_y = cur_text_y - 28
            draw.text((tri_x, tri_y), "△", fill=COLOR_SKY_TRIANGLE, font=font_triangle)

    return im

def render_slide_last_summary(
    slide_title: str = "2026년 고3 6월 32번",
    topic: str = "비언어적 소통의 중요성과 의도 숨기기의 어려움",
    vocab_list: list = None,
    summary_list: list = None
) -> Image.Image:
    """구글 슬라이드 17번 (마지막 장표) 100% 동일 렌더링"""
    im = render_google_slides_base(slide_title)
    draw = ImageDraw.Draw(im)

    if not vocab_list:
        vocab_list = [
            ("nonverbal", "비언어적인"),
            ("meaning", "의미, 의도"),
            ("conceal", "숨기다, 감추다")
        ]

    if not summary_list:
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

    # 1. 지문 주제 카드 (Y: 150 ~ 270, X: 100 ~ 1820)
    draw.rounded_rectangle([100, 150, 1820, 270], radius=18, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
    
    # Red Pin Graphic
    pin_x, pin_y = 145, 192
    draw.polygon([(pin_x, pin_y), (pin_x + 14, pin_y - 8), (pin_x + 22, pin_y + 4), (pin_x + 8, pin_y + 12)], fill=(239, 68, 68))
    draw.ellipse([pin_x + 4, pin_y - 6, pin_x + 18, pin_y + 8], fill=(248, 113, 113))
    draw.line([(pin_x, pin_y + 8), (pin_x - 10, pin_y + 22)], fill=(203, 213, 225), width=3)
    
    font_topic_label = get_kr_font(26, bold=True)
    draw.text((180, 188), "지문 주제", fill=COLOR_YELLOW, font=font_topic_label)
    font_topic_val = get_kr_font(26, bold=True)
    draw.text((330, 188), topic, fill=COLOR_WHITE, font=font_topic_val)

    # 2. 핵심 어휘 3개 카드 (Y: 295 ~ 415)
    card_w = 540
    gap = 50
    start_x = 100
    font_v_en = get_kr_font(28, bold=True)
    font_v_kr = get_kr_font(20, bold=False)

    for i in range(3):
        cx = start_x + i * (card_w + gap)
        draw.rounded_rectangle([cx, 295, cx + card_w, 415], radius=18, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
        en_w, kr_m = vocab_list[i]
        
        # Center text horizontally
        tb_en = draw.textbbox((0, 0), en_w, font=font_v_en)
        w_en = tb_en[2] - tb_en[0]
        draw.text((cx + (card_w - w_en) // 2, 320), en_w, fill=COLOR_YELLOW, font=font_v_en)
        
        tb_kr = draw.textbbox((0, 0), kr_m, font=font_v_kr)
        w_kr = tb_kr[2] - tb_kr[0]
        draw.text((cx + (card_w - w_kr) // 2, 365), kr_m, fill=COLOR_WHITE, font=font_v_kr)

    # 3. 3단 핵심 요약 카드 3장 (Y: 440 ~ 915, Height: 475px, Radius: 28px)
    card_h = 475
    font_sum_title = get_kr_font(24, bold=True)
    font_sum_body = get_kr_font(20, bold=False)

    for i in range(3):
        cx = start_x + i * (card_w + gap)
        draw.rounded_rectangle([cx, 440, cx + card_w, 440 + card_h], radius=28, fill=COLOR_PILL_BG, outline=COLOR_PILL_BORDER, width=2)
        s_item = summary_list[i]
        
        # Title (Salmon Pink #FF908A)
        t_lines = s_item["title"].split("\n")
        ty = 480
        for tl in t_lines:
            draw.text((cx + 40, ty), tl, fill=COLOR_SALMON_TITLE, font=font_sum_title)
            ty += 36

        # Body (White #FFFFFF)
        b_lines = s_item["body"].split("\n")
        by = ty + 30
        for bl in b_lines:
            draw.text((cx + 40, by), bl, fill=COLOR_WHITE, font=font_sum_body)
            by += 34

    return im

if __name__ == "__main__":
    out_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\google_slides_exact"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Slide 0: Cover Slide
    p0 = os.path.join(out_dir, "slide_00_cover.png")
    render_slide_01_cover().save(p0)
    print("Saved:", p0)

    # 2. Slide 1: Sentence 1
    # "Speakers don't always put everything [that's important (to them)] (into words)."
    s1_lines = [
        {
            "text": "Speakers (don't always) put everything [that's important",
            "tags": [
                {"col_start": 0, "col_end": 8, "tag": "S", "color": COLOR_PINK_VERB, "underline": True},
                {"col_start": 24, "col_end": 27, "tag": "Vt", "color": COLOR_PINK_VERB, "underline": True, "double_underline": True},
                {"col_start": 28, "col_end": 38, "tag": "O", "color": COLOR_MINT_OBJ, "underline": True},
                {"col_start": 40, "col_end": 46, "tag": "S", "color": COLOR_PINK_VERB, "underline": True},
                {"col_start": 47, "col_end": 56, "tag": "SC", "color": COLOR_MINT_OBJ, "underline": True}
            ],
            "triangles": []
        },
        {
            "text": "(to them)] (into words).",
            "tags": [],
            "triangles": []
        }
    ]
    p1 = os.path.join(out_dir, "slide_01_sentence1.png")
    render_slide_sentence("2026년 고3 6월 32번", s1_lines).save(p1)
    print("Saved:", p1)

    # 3. Slide 2: Sentence 2
    # "Very often you can understand a speaker's meaning (by [observing their nonverbal behaviors] such as a change (in a vocal tone or volume), eye contact, facial expressions, and gestures)."
    s2_lines = [
        {
            "text": "Very often you can understand a speaker's meaning",
            "tags": [
                {"col_start": 11, "col_end": 14, "tag": "S", "color": COLOR_PINK_VERB, "underline": True},
                {"col_start": 15, "col_end": 29, "tag": "Vt", "color": COLOR_PINK_VERB, "underline": True, "double_underline": True},
                {"col_start": 30, "col_end": 49, "tag": "O", "color": COLOR_MINT_OBJ, "underline": True}
            ],
            "triangles": []
        },
        {
            "text": "(by [observing their nonverbal behaviors] such as a change",
            "tags": [
                {"col_start": 5, "col_end": 14, "tag": "Vt", "color": COLOR_PINK_VERB, "underline": False},
                {"col_start": 15, "col_end": 40, "tag": "O", "color": COLOR_MINT_OBJ, "underline": False}
            ],
            "triangles": []
        },
        {
            "text": "(in a vocal tone or volume), eye contact, facial expressions, and gestures).",
            "tags": [],
            "triangles": [17, 62] # 'or' at col 17, 'and' at col 62
        }
    ]
    p2 = os.path.join(out_dir, "slide_02_sentence2.png")
    render_slide_sentence("2026년 고3 6월 32번", s2_lines).save(p2)
    print("Saved:", p2)

    # 4. Slide Last: Summary Slide
    p_last = os.path.join(out_dir, "slide_last_summary.png")
    render_slide_last_summary().save(p_last)
    print("Saved:", p_last)
