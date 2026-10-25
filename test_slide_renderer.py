import os
import sys
import re
import json
from PIL import Image, ImageDraw, ImageFont

# Fonts
FONT_BOLD_PATH = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_REG_PATH = r"C:\Windows\Fonts\malgun.ttf"

def get_font(size: int, bold: bool = True):
    p = FONT_BOLD_PATH if bold else FONT_REG_PATH
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()

# Colors (Standard 교안 & Google Slides Palette)
BOARD_BG = (20, 56, 39)          # #143827
FRAME_WOOD = (62, 39, 35)        # #3E2723
FRAME_GOLD = (141, 110, 99)      # #8D6E63
PANEL_BG = (16, 47, 32)          # #102F20
PANEL_BORDER = (35, 88, 62)      # #23583E
DIVIDER_LINE = (38, 92, 65)

# Text Colors
WHITE = (255, 255, 255)
YELLOW = (250, 204, 21)          # #FACC15
MINT = (167, 243, 208)           # #A7F3D0
SLATE_MUTED = (148, 163, 184)    # #94A3B8
SLATE_LIGHT = (226, 232, 240)    # #E2E8F0

# Constituent Colors (STYLE_GUIDE.md Standard)
COLOR_S_BLUE = (96, 165, 250)    # Blue #60A5FA
COLOR_V_ROSE = (248, 113, 113)   # Rose Pink #F87171
COLOR_O_EMERALD = (52, 211, 153) # Emerald #34D399
COLOR_SC_INDIGO = (129, 140, 248)# Indigo #818CF8
COLOR_OC_PURPLE = (192, 132, 252)# Purple #C084FC
COLOR_SLASH_PURPLE = (192, 132, 252) # Purple #C084FC
COLOR_TRIANGLE_SKY = (56, 189, 248)  # Sky Blue #38BDF8

PURE_CONJUNCTIONS = [
    'and', 'but', 'or', 'so', 'yet', 'nor',
    'both', 'either', 'neither',
    'however', 'therefore', 'furthermore', 'moreover', 'thus', 'consequently',
    'instead', 'meanwhile', 'besides', 'likewise', 'similarly'
]

def render_base_board(title: str, s_num: int = 0, total_sentences: int = 0) -> Image.Image:
    """기본 칠판 캔버스 및 상단 헤더 생성"""
    im = Image.new("RGB", (1920, 1080), BOARD_BG)
    draw = ImageDraw.Draw(im)

    # 마호가니 원목 외곽 프레임 (16px)
    fw = 16
    draw.rectangle([0, 0, 1920, fw], fill=FRAME_WOOD)
    draw.rectangle([0, 1080 - fw, 1920, 1080], fill=FRAME_WOOD)
    draw.rectangle([0, 0, fw, 1080], fill=FRAME_WOOD)
    draw.rectangle([1920 - fw, 0, 1920, 1080], fill=FRAME_WOOD)
    # 골드 라인
    draw.line([(fw, fw), (1920 - fw, fw)], fill=FRAME_GOLD, width=1)
    draw.line([(fw, 1080 - fw), (1920 - fw, 1080 - fw)], fill=FRAME_GOLD, width=1)
    draw.line([(fw, fw), (fw, 1080 - fw)], fill=FRAME_GOLD, width=1)
    draw.line([(1920 - fw, fw), (1920 - fw, 1080 - fw)], fill=FRAME_GOLD, width=1)

    # 상단 헤더
    # 좌측 타이틀 알약 (노란색)
    font_pill = get_font(20, bold=True)
    tb = draw.textbbox((0, 0), title, font=font_pill)
    pw = max(260, tb[2] - tb[0] + 36)
    draw.rounded_rectangle([60, 36, 60 + pw, 82], radius=10, fill=PANEL_BG, outline=PANEL_BORDER, width=1)
    draw.text((78, 46), title, fill=YELLOW, font=font_pill)

    # 문장 번호 알약
    if s_num > 0:
        sent_badge = f"{s_num}번 문장" if total_sentences == 0 else f"{s_num}번 문장  ( {s_num} / {total_sentences} )"
        tb_s = draw.textbbox((0, 0), sent_badge, font=font_pill)
        bw = tb_s[2] - tb_s[0] + 32
        bx = 60 + pw + 16
        draw.rounded_rectangle([bx, 36, bx + bw, 82], radius=10, fill=(24, 63, 44), outline=PANEL_BORDER, width=1)
        draw.text((bx + 16, 46), sent_badge, fill=MINT, font=font_pill)

    # 우측 브랜드 로고
    font_logo = get_font(22, bold=True)
    draw.text((1680, 46), "에이닷 영어학원", fill=WHITE, font=font_logo)

    # 상단 구분선
    draw.line([(60, 96), (1860, 96)], fill=DIVIDER_LINE, width=1)
    return im

def render_cover_slide(title: str, topic: str = "") -> Image.Image:
    """구글 슬라이드 1번 장표 (표지 슬라이드)"""
    im = render_base_board(title)
    draw = ImageDraw.Draw(im)

    # 중앙 대형 제목
    center_y = 360
    title_font = get_font(52, bold=True)
    tb = draw.textbbox((0, 0), title, font=title_font)
    tw = tb[2] - tb[0]
    draw.text(((1920 - tw) // 2, center_y), title, fill=WHITE, font=title_font)

    # 하단 둥근 주제 카드
    if topic:
        topic_font = get_font(26, bold=True)
        tb_t = draw.textbbox((0, 0), topic, font=topic_font)
        box_w = max(900, tb_t[2] - tb_t[0] + 80)
        box_x1 = (1920 - box_w) // 2
        box_y1 = center_y + 170
        draw.rounded_rectangle([box_x1, box_y1, box_x1 + box_w, box_y1 + 94], radius=16, fill=PANEL_BG, outline=PANEL_BORDER, width=2)
        draw.text((box_x1 + (box_w - (tb_t[2] - tb_t[0])) // 2, box_y1 + 28), topic, fill=YELLOW, font=topic_font)

    return im

def render_last_summary_slide(title: str, summary_info: dict, vocabulary: list = None) -> Image.Image:
    """구글 슬라이드 17번 (마지막 장표) 핵심 정리 양식"""
    im = render_base_board(title)
    draw = ImageDraw.Draw(im)

    subject = summary_info.get("subject", "")
    summary_points = summary_info.get("summary", [])

    # 1. 지문 주제 카드 (상단)
    sy = 120
    draw.rounded_rectangle([60, sy, 1860, sy + 76], radius=12, fill=PANEL_BG, outline=PANEL_BORDER, width=1)
    draw.text((86, sy + 22), "📌 지문 주제", fill=YELLOW, font=get_font(24, bold=True))
    draw.text((250, sy + 22), subject, fill=WHITE, font=get_font(24, bold=True))

    # 2. 핵심 어휘 3개 카드 (중단)
    vy = 216
    raw_kw = summary_info.get("keywords", "")
    # Parse 3 keywords
    kw_items = []
    # Try keywords string: e.g. "① nonverbal (비언어적) ② meaning (의미) ③ conceal (숨기다)"
    matches = re.findall(r'[①②③\d\.]*\s*([a-zA-Z\s\-]+)\s*\(([^)]+)\)', raw_kw)
    if matches:
        for en, kr in matches[:3]:
            kw_items.append((en.strip(), kr.strip()))
    elif vocabulary and isinstance(vocabulary, list):
        for v in vocabulary[:3]:
            if isinstance(v, dict):
                kw_items.append((v.get("word", ""), v.get("meaning", "")))

    # Fallback if empty
    if len(kw_items) < 3:
        kw_items = [("nonverbal", "비언어적인"), ("meaning", "의미, 의도"), ("conceal", "숨기다, 감추다")]

    card_w = 573
    gap = 40
    start_x = 60
    for i in range(3):
        cx = start_x + i * (card_w + gap)
        draw.rounded_rectangle([cx, vy, cx + card_w, vy + 90], radius=12, fill=(24, 63, 44), outline=PANEL_BORDER, width=1)
        # Badge
        draw.text((cx + 20, vy + 14), f"핵심어휘 {chr(9312+i)}", fill=MINT, font=get_font(16, bold=True))
        # Word + Meaning
        en_word, kr_mean = kw_items[i]
        draw.text((cx + 20, vy + 42), en_word, fill=WHITE, font=get_font(24, bold=True))
        draw.text((cx + 20 + len(en_word) * 16 + 20, vy + 46), f"({kr_mean})", fill=SLATE_MUTED, font=get_font(18, bold=False))

    # 3. 지문 핵심 3단 정리 카드 (하단)
    cy = 330
    ch = 440
    step_titles = [
        "1. 핵심 요인 (Key Factor)",
        "2. 문제점 (Challenge)",
        "3. 대안 및 결론 (Solution)"
    ]
    step_colors = [YELLOW, COLOR_V_ROSE, COLOR_TRIANGLE_SKY]

    for i in range(3):
        cx = start_x + i * (card_w + gap)
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + ch], radius=14, fill=PANEL_BG, outline=PANEL_BORDER, width=2)
        # Header
        draw.text((cx + 24, cy + 24), step_titles[i], fill=step_colors[i], font=get_font(22, bold=True))
        draw.line([(cx + 24, cy + 62), (cx + card_w - 24, cy + 62)], fill=DIVIDER_LINE, width=1)

        # Content lines
        content = summary_points[i] if i < len(summary_points) else ""
        lines = []
        cur_l = ""
        for w in content.split(" "):
            if len(cur_l + w) > 20:
                lines.append(cur_l)
                cur_l = w + " "
            else:
                cur_l += w + " "
        if cur_l:
            lines.append(cur_l)

        text_y = cy + 85
        for l in lines:
            draw.text((cx + 24, text_y), l, fill=SLATE_LIGHT, font=get_font(21, bold=False))
            text_y += 38

    return im

def render_sentence_chalkboard_slide(
    title: str,
    s_num: int,
    total_sentences: int,
    tokens: list,
    chunk_korean: str = "",
    grammar_points: str = ""
) -> Image.Image:
    """
    구글 슬라이드 판서 원본 및 깃허브 강의용 교안 양식과 100% 일치하는 대형 칠판 판서 슬라이드
    - 영문 폰트 44px 대형 폰트
    - 대괄호 [ ], 소괄호 ( ) 품사별 색상
    - 등위접속사/접속부사 세모(△) 오버레이
    - 관계사/형용사구 화살표(⬑)
    - 주어/본동사 밑줄 (본동사 2줄)
    - 하단 S/Vt/Vi/O 성분 태그
    - 상단 준동사 성분 top_label
    - 1:1 직독직해 끊어읽기 패널
    - 핵심 어법 및 서술형 출제 포인트 패널
    """
    im = render_base_board(title, s_num, total_sentences)
    draw = ImageDraw.Draw(im)

    font_word = get_font(44, bold=True)
    font_sub = get_font(28, bold=True)
    font_top = get_font(22, bold=True)
    font_arrow = get_font(24, bold=True)

    # 1. 영문 토큰 배치 계산 (Word Wrap)
    start_x = 90
    cur_x = start_x
    cur_y = 170
    line_height = 175
    max_line_width = 1780 # Full blackboard width

    positioned = []
    for t in tokens:
        raw_text = t.get("text", "")
        if not raw_text:
            continue
        is_slash = (raw_text.strip() == "/")
        
        tb = draw.textbbox((0, 0), raw_text, font=font_word)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]

        if cur_x + tw > max_line_width and not is_slash and cur_x > start_x:
            cur_x = start_x
            cur_y += line_height

        item = dict(t)
        item["x"] = cur_x
        item["y"] = cur_y
        item["w"] = tw
        item["h"] = th
        positioned.append(item)

        cur_x += tw + (10 if is_slash else 18)

    # 2. 토큰별 렌더링
    for item in positioned:
        raw_text = item.get("text", "")
        x = item["x"]
        y = item["y"]
        w = item["w"]
        h = item["h"]

        sub_tag = (item.get("sub_tag") or "").strip()
        top_label = (item.get("top_label") or "").strip()
        color_key = item.get("color", "slate")
        underline = item.get("underline", False)
        is_conj = item.get("is_conjunction", False)

        # 슬래시 끊어읽기 기호
        if raw_text.strip() == "/":
            draw.text((x, y), "/", fill=COLOR_SLASH_PURPLE, font=font_word)
            continue

        # 클린 단어 및 괄호 분리
        clean_word = raw_text.replace("[", "").replace("]", "").replace("(", "").replace(")", "").strip()
        clean_word_lower = re.sub(r'[^a-zA-Z]', '', clean_word).lower()

        # 색상 결정
        if color_key == "rose" or sub_tag in ("Vi", "Vt") or top_label in ("Vi", "Vt"):
            word_color = COLOR_V_ROSE
        elif color_key == "blue" or sub_tag == "S":
            word_color = COLOR_S_BLUE
        elif color_key == "emerald" or sub_tag.startswith("O"):
            word_color = COLOR_O_EMERALD
        elif color_key == "indigo" or sub_tag.startswith("SC"):
            word_color = COLOR_SC_INDIGO
        elif color_key == "purple" or sub_tag.startswith("OC"):
            word_color = COLOR_OC_PURPLE
        else:
            word_color = WHITE

        # 단어 출력 (괄호 색상 특화)
        # 만약 [ 또는 ( 로 시작하거나 끝나는 경우
        char_x = x
        for ch in raw_text:
            tb_ch = draw.textbbox((0, 0), ch, font=font_word)
            cw = tb_ch[2] - tb_ch[0]
            if ch == "[":
                # 대괄호 색상: 목적어절(초록), 주어절(파랑), 보어절(보라)
                b_color = COLOR_O_EMERALD if sub_tag.startswith("O") or top_label.startswith("O") else (COLOR_S_BLUE if sub_tag == "S" else COLOR_OC_PURPLE)
                draw.text((char_x, y), ch, fill=b_color, font=font_word)
            elif ch == "]":
                b_color = COLOR_O_EMERALD if sub_tag.startswith("O") or top_label.startswith("O") else (COLOR_S_BLUE if sub_tag == "S" else COLOR_OC_PURPLE)
                draw.text((char_x, y), ch, fill=b_color, font=font_word)
            elif ch in ("(", ")"):
                draw.text((char_x, y), ch, fill=SLATE_MUTED, font=font_word)
            else:
                draw.text((char_x, y), ch, fill=word_color, font=font_word)
            char_x += cw

        # 세모 (△) 오버레이 (등위접속사, 접속부사)
        if is_conj or top_label == "△" or clean_word_lower in PURE_CONJUNCTIONS:
            # 단어 정중앙에 깔끔한 스카이블루 정삼각형 그리기
            tri_w = min(w + 12, 70)
            tri_cx = x + w // 2
            tri_top_y = y - 6
            tri_bot_y = y + h + 6
            pts = [
                (tri_cx, tri_top_y),
                (tri_cx + tri_w // 2, tri_bot_y),
                (tri_cx - tri_w // 2, tri_bot_y),
                (tri_cx, tri_top_y)
            ]
            draw.line(pts, fill=COLOR_TRIANGLE_SKY, width=3)

        # 밑줄 (주어 S 및 본동사 Vi/Vt)
        if underline or sub_tag in ("S", "Vi", "Vt"):
            uy = y + h + 8
            u_color = COLOR_V_ROSE if sub_tag in ("Vi", "Vt") or color_key == "rose" else COLOR_S_BLUE
            draw.line([(x, uy), (x + w, uy)], fill=u_color, width=4)
            # 본동사는 2줄 밑줄
            if sub_tag in ("Vi", "Vt"):
                draw.line([(x, uy + 6), (x + w, uy + 6)], fill=u_color, width=3)

        # 상단 라벨 (top_label: Vt, Vi, O 등 준동사 성분)
        if top_label and top_label != "△":
            tb_top = draw.textbbox((0, 0), top_label, font=font_top)
            tw_top = tb_top[2] - tb_top[0]
            top_x = x + (w - tw_top) // 2
            top_y = y - 30
            top_c = COLOR_V_ROSE if top_label in ("Vi", "Vt") else (COLOR_O_EMERALD if top_label.startswith("O") else YELLOW)
            draw.text((top_x, top_y), top_label, fill=top_c, font=font_top)

        # 하단 태그 (sub_tag: S, Vt, Vi, O, SC, OC 등)
        clean_sub = sub_tag.replace("⬑", "").strip()
        if clean_sub:
            tag_y = y + h + (24 if (sub_tag in ("Vi", "Vt") and underline) else 16)
            tb_tag = draw.textbbox((0, 0), clean_sub, font=font_sub)
            tw_tag = tb_tag[2] - tb_tag[0]
            tag_x = x + (w - tw_tag) // 2
            tag_c = COLOR_V_ROSE if clean_sub in ("Vi", "Vt") else (COLOR_S_BLUE if clean_sub.startswith("S") else (COLOR_O_EMERALD if clean_sub.startswith("O") else WHITE))
            draw.text((tag_x, tag_y), clean_sub, fill=tag_c, font=font_sub)

        # 수식 화살표 (⬑)
        if "⬑" in sub_tag or item.get("sub_tag") == "⬑":
            arrow_x = x
            arrow_y = y + h + 14
            draw.text((arrow_x, arrow_y), "⬑", fill=COLOR_SC_INDIGO, font=font_arrow)

    # 3. 하단 패널: 1:1 직독직해 끊어읽기 패널
    # Teacher PIP 위치: X: 1480 ~ 1880, Y: 800 ~ 1040
    # 따라서 좌측 영역 폭: 1390px (X: 70 ~ 1460)
    panel_x = 70
    panel_w = 1380
    
    # 직독직해 패널 Y: 560 ~ 720
    panel_1_y = 560
    panel_1_h = 160
    draw.rounded_rectangle([panel_x, panel_1_y, panel_x + panel_w, panel_1_y + panel_1_h], radius=14, fill=PANEL_BG, outline=PANEL_BORDER, width=2)
    
    # 패널 1 제목 배지
    draw.text((panel_x + 24, panel_1_y + 18), "📖 1:1 직독직해 끊어읽기", fill=YELLOW, font=get_font(21, bold=True))
    draw.line([(panel_x + 24, panel_1_y + 52), (panel_x + panel_w - 24, panel_1_y + 52)], fill=DIVIDER_LINE, width=1)
    
    # 직독직해 본문
    kr_chunks = chunk_korean.split(" / ") if " / " in chunk_korean else chunk_korean.split("/")
    chunk_line_1 = ""
    chunk_line_2 = ""
    cur_line = ""
    
    for c in kr_chunks:
        c_str = c.strip()
        if not c_str:
            continue
        piece = f" / {c_str}" if cur_line else c_str
        if len(cur_line + piece) > 42:
            if not chunk_line_1:
                chunk_line_1 = cur_line
                cur_line = c_str
            else:
                chunk_line_2 = cur_line
                cur_line = c_str
        else:
            cur_line += piece
    if not chunk_line_1:
        chunk_line_1 = cur_line
    elif not chunk_line_2:
        chunk_line_2 = cur_line

    # 직독직해 텍스트 출력 (슬래시는 보라색, 한글은 밝은 화이트)
    def draw_chunk_line(line_text: str, start_y: int):
        cur_pos_x = panel_x + 24
        parts = line_text.split(" / ")
        for p_idx, p in enumerate(parts):
            if p_idx > 0:
                draw.text((cur_pos_x, start_y), " / ", fill=COLOR_SLASH_PURPLE, font=get_font(23, bold=True))
                cur_pos_x += 32
            draw.text((cur_pos_x, start_y), p, fill=SLATE_LIGHT, font=get_font(23, bold=True))
            tb_p = draw.textbbox((0, 0), p, font=get_font(23, bold=True))
            cur_pos_x += (tb_p[2] - tb_p[0])

    draw_chunk_line(chunk_line_1, panel_1_y + 68)
    if chunk_line_2:
        draw_chunk_line(chunk_line_2, panel_1_y + 108)

    # 4. 하단 패널: 핵심 어법 & 서술형 출제 포인트 패널
    # Y: 740 ~ 1020 (높이 280px)
    panel_2_y = 740
    panel_2_h = 280
    draw.rounded_rectangle([panel_x, panel_2_y, panel_x + panel_w, panel_2_y + panel_2_h], radius=14, fill=(15, 42, 29), outline=PANEL_BORDER, width=2)

    draw.text((panel_x + 24, panel_2_y + 18), "💡 핵심 어법 & 서술형 출제 포인트", fill=COLOR_V_ROSE, font=get_font(21, bold=True))
    draw.line([(panel_x + 24, panel_2_y + 52), (panel_x + panel_w - 24, panel_2_y + 52)], fill=DIVIDER_LINE, width=1)

    # 어법 포인트 텍스트 줄바꿈 및 출력
    g_lines = [l.strip() for l in grammar_points.split("\n") if l.strip()][:5]
    py = panel_2_y + 66
    for gl in g_lines:
        # Check length
        display_gl = gl if len(gl) <= 52 else gl[:50] + "..."
        draw.text((panel_x + 28, py), f"• {display_gl}", fill=SLATE_LIGHT, font=get_font(20, bold=False))
        py += 38

    return im

if __name__ == "__main__":
    out_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\test_slides"
    os.makedirs(out_dir, exist_ok=True)
    
    json_path = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output_q32_processed.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    analysis_data = data.get("analysis_data", {})
    title = analysis_data.get("title", "2026년 고3 6월 모의고사 32번")
    summary_info = analysis_data.get("summary_info", {})
    topic = summary_info.get("subject", "")
    sentences = analysis_data.get("sentences", [])
    
    # 1. Slide 0: Cover Slide
    p0 = os.path.join(out_dir, "slide_00_cover.jpg")
    render_cover_slide(title, topic).save(p0, quality=95)
    print("Rendered:", p0)
    
    # 2. Slide 1: Sentence 1
    s1 = sentences[0]
    p1 = os.path.join(out_dir, "slide_01_sentence1.jpg")
    render_sentence_chalkboard_slide(
        title, 1, len(sentences),
        s1.get("tokens", []),
        s1.get("chunk_korean", ""),
        s1.get("grammar_points", "")
    ).save(p1, quality=95)
    print("Rendered:", p1)
    
    # 3. Slide 2: Sentence 2
    s2 = sentences[1]
    p2 = os.path.join(out_dir, "slide_02_sentence2.jpg")
    render_sentence_chalkboard_slide(
        title, 2, len(sentences),
        s2.get("tokens", []),
        s2.get("chunk_korean", ""),
        s2.get("grammar_points", "")
    ).save(p2, quality=95)
    print("Rendered:", p2)
    
    # 4. Slide Last: Summary Slide
    p_last = os.path.join(out_dir, "slide_last_summary.jpg")
    render_last_summary_slide(title, summary_info, analysis_data.get("vocabulary", [])).save(p_last, quality=95)
    print("Rendered:", p_last)
