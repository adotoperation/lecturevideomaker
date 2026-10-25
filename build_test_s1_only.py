import os
import sys
import time
import math
import asyncio
import subprocess
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from video_renderer import get_audio_duration
from tts_engine import synthesize_best_audio

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "Aoede" # Google Gemini 2.5 Studio Aoede (여성, 명확하고 또렷한 설명형 톤)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(BASE_DIR, "output", "test_s1_gemini")
OUT_VIDEO_DIR = os.path.join(BASE_DIR, "output", "videos")
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(OUT_VIDEO_DIR, exist_ok=True)

TEACHER_PIP_CIRCLE = os.path.join(BASE_DIR, "assets", "teacher_pip_circle.mp4")
PIP_MASK_CIRCLE = os.path.join(BASE_DIR, "assets", "pip_mask_circle.png")
PIP_RING_CIRCLE = os.path.join(BASE_DIR, "assets", "pip_ring_circle.png")

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

    # 1. 직독직해 끊어읽기 박스와 핵심포인트 바 완전 삭제 (필기 유도)
    # 2. 어법/서술형 설명 시 해당 부분에 별표(★)와 어법 중요 / 서술형 중요 라벨 표시
    if state == 8:
        # (1) don't always 상단
        x_not_always = sx + int(14 * char_w)
        draw_important_badge(draw, x_not_always, y1 - 90, "★ 어법 중요: not always (부분부정)", badge_type='grammar')
        # (2) that's important 상단
        x_rel_clause = sx + int(50 * char_w)
        draw_important_badge(draw, x_rel_clause - 80, y1 - 90, "★ 어법 중요: everything 단수 수일치 is", badge_type='grammar')
        
    elif state == 9:
        # 구문 강조 테두리
        box_x1 = sx + int(30 * char_w)
        box_y1 = y1 - 15
        box_x2 = sx + int(68 * char_w) + 20
        box_y2 = y2 + 65
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, outline=COLOR_YELLOW, width=3)
        # 상단 서술형 중요 뱃지
        draw_important_badge(draw, box_x1, y1 - 85, "★ 서술형 중요: [put A into words] 구동사 + 관계대명사 후치수식", badge_type='writing')

    return im

INTRO_SCRIPT = (
    "안녕하세요, 여러분. 오늘은 2026년 고3 6월 모의고사 32번 빈칸 추론 지문을 함께 공부해 보겠습니다. "
    "이 글의 주제는 비언어적 소통의 중요성과 의도 숨기기의 어려움인데요. "
    "문장 하나하나 직독직해와 문장 구조를 꼼꼼하게 분석해 볼 테니 필기 준비하시고 집중해서 따라오세요. "
    "그럼 1번 문장부터 시작합니다!"
)

S1_CHUNKS = [
    (0, "1번 문장 직독직해와 구조 분석이야."),
    (1, "주어인 화자는,"),
    (2, "항상 말로 표현하는 것은 아니다이고, 타동사야. 항상 하는 건 아니다라는 부분부정이 들어가 있어."),
    (3, "모든 것을은 목적어야. 그래서 주절이 3형식이야."),
    (4, "중요한으로 해석해 주격 관계대명사 절이고 앞의 모든 것을 수식하고 있고, 중요한이 주격보어 역할을 하는 2형식 문장이야."),
    (5, "그들에게이며, 전명구가 부사구의 역할을 하고 있어."),
    (6, "풋 인투 워드는 하나로 묶어서 구동사의 역할을 하고 있다는 거 중요해. 말로라는 전명구 부사구 거품이야. 주절 3형식에 2형식 형용사절이 결합된 완전한 문장이야."),
    (7, "이어서 2단계, 내용 맥락 설명이야. 화자들은 자기가 중요하다고 생각하는 모든 것을 말로 다 표현하지는 않는다는 내용이야. 언어로 표현하지 않는 다른 중요한 비언어적 메시지가 있을 수 있다는 걸 암시하지."),
    (8, "다음으로 3단계, 시험에 무조건 출제되는 핵심 어법 포인트야. 별표 치고 필기해 둬. 여기서 not always는 항상 ~하는 것은 아니다라는 부분 부정을 나타내는 표현이야. 그리고 주격 관계대명사절 안의 동사는 앞의 선행사 everything에 수일치하여 단수 동사가 온다는 점을 꼭 기억해 둬."),
    (9, "마지막으로 4단계, 내신 서술형 영작 대비 포인트야. 역시 별표 쳐두자. 타동사 구문과 주격 관계대명사절이 결합된 형태라서 서술형으로 출제되기 아주 좋아. 관계대명사절이 선행사를 뒤에서 수식하는 어순에 유의해서 영작 연습 꼭 해봐야 해.")
]

def make_silence(duration: float, out_path: str):
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration),
        "-c:a", "libmp3lame", "-b:a", "192k",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

async def synthesize_chunk_audio(text: str, raw_path: str, timed_path: str, silence_path: str):
    # Gemini Aoede 100% 고정 합성
    print(f"  [TTS] Synthesizing Gemini Aoede: {text[:35]}...")
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

async def main():
    t_start = time.time()
    print("=" * 60)
    print(">>> 2026 고3 6월 32번: [표지 + 1번 문장] 집중 제작 시작")
    print(">>> 성우: Gemini 2.5 Studio Aoede (100% 단일 성우 보장)")
    print(">>> 판서: 직독직해/핵심포인트 바 삭제, 어법/서술형 별표(★) 표기")
    print("=" * 60)

    silence_04s = os.path.join(WORK_DIR, "silence_04s.mp3")
    silence_08s = os.path.join(WORK_DIR, "silence_08s.mp3")
    make_silence(0.4, silence_04s)
    make_silence(0.8, silence_08s)

    all_segment_files = []

    # ----------------------------------------------------
    # 1. 표지 (Intro)
    # ----------------------------------------------------
    print("\n[Step 1] 표지 (Intro) 제작")
    cover_img_path = os.path.join(WORK_DIR, "cover.png")
    if not os.path.exists(cover_img_path):
        render_cover_slide().save(cover_img_path)

    cover_raw_audio = os.path.join(WORK_DIR, "intro_raw.mp3")
    cover_timed_audio = os.path.join(WORK_DIR, "intro_timed.mp3")
    cover_seg = os.path.join(WORK_DIR, "seg_00_cover.mp4")

    if not (os.path.exists(cover_seg) and os.path.getsize(cover_seg) > 50000):
        await synthesize_chunk_audio(INTRO_SCRIPT, cover_raw_audio, cover_timed_audio, silence_08s)
        print("  [Render] seg_00_cover.mp4...")
        render_mini_segment(cover_img_path, cover_timed_audio, TEACHER_PIP_CIRCLE, PIP_MASK_CIRCLE, PIP_RING_CIRCLE, cover_seg)
    else:
        print("  [Skip] seg_00_cover.mp4 already exists.")
    all_segment_files.append(cover_seg)

    # ----------------------------------------------------
    # 2. 1번 문장 (Sentence 1: Chunks 0 ~ 9)
    # ----------------------------------------------------
    print("\n[Step 2] 1번 문장 (Sentence 1) 청크별 제작")
    for idx, (state, script) in enumerate(S1_CHUNKS):
        print(f"\n--- S1 Chunk {idx+1}/{len(S1_CHUNKS)} (State {state}) ---")
        img_path = os.path.join(WORK_DIR, f"s1_state_{state}.png")
        if not os.path.exists(img_path):
            render_s1_state(state).save(img_path)

        raw_audio = os.path.join(WORK_DIR, f"s1_chunk_{idx:02d}_raw.mp3")
        timed_audio = os.path.join(WORK_DIR, f"s1_chunk_{idx:02d}_timed.mp3")
        seg_file = os.path.join(WORK_DIR, f"s1_chunk_{idx:02d}.mp4")

        if not (os.path.exists(seg_file) and os.path.getsize(seg_file) > 10000):
            await synthesize_chunk_audio(script, raw_audio, timed_audio, silence_04s)
            print(f"  [Render] {os.path.basename(seg_file)}...")
            render_mini_segment(img_path, timed_audio, TEACHER_PIP_CIRCLE, PIP_MASK_CIRCLE, PIP_RING_CIRCLE, seg_file)
            time.sleep(1.0)
        else:
            print(f"  [Skip] {os.path.basename(seg_file)} already exists.")
        all_segment_files.append(seg_file)

    # ----------------------------------------------------
    # 3. 비디오 Concat 병합
    # ----------------------------------------------------
    print("\n[Step 3] 최종 비디오 병합")
    concat_list_file = os.path.join(WORK_DIR, "concat_list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for seg in all_segment_files:
            # ffmpeg concat demuxer format
            p = seg.replace("\\", "/")
            f.write(f"file '{p}'\n")

    final_video_path = os.path.join(OUT_VIDEO_DIR, "2026_고3_6월_32번_1문장_테스트강의.mp4")
    cmd_concat = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy",
        final_video_path
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    dur = get_audio_duration(final_video_path)
    sz = os.path.getsize(final_video_path) / (1024 * 1024)
    elapsed = time.time() - t_start

    print("=" * 60)
    print(f"★ 제작 완료! ★")
    print(f"  - 최종 영상: {final_video_path}")
    print(f"  - 총 영상 길이: {dur:.1f}초 ({dur/60:.2f}분)")
    print(f"  - 파일 크기: {sz:.2f} MB")
    print(f"  - 소요 시간: {elapsed:.1f}초 ({elapsed/60:.2f}분)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
