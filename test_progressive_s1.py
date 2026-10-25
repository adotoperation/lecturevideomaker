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

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "ko-KR-SunHiNeural"

FONT_CONSOLAS_BOLD = r"C:\Windows\Fonts\consolab.ttf"
FONT_MALGUN_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_MALGUN_REG = r"C:\Windows\Fonts\malgun.ttf"

def get_mono_font(size: int):
    return ImageFont.truetype(FONT_CONSOLAS_BOLD, size)

def get_kr_font(size: int, bold: bool = True):
    p = FONT_MALGUN_BOLD if bold else FONT_MALGUN_REG
    return ImageFont.truetype(p, size)

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

def render_board_base():
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
    draw.text((114, 73), "2026년 고3 6월 32번", fill=COLOR_YELLOW, font=font_pill)

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

def render_s1_state(state: int) -> Image.Image:
    """
    Sentence 1 점진적 판서 상태 렌더링
    state 0: 기본 원문만 표시
    state 1: 주어 Speakers [S 하단 + 파란 밑줄]
    state 2: 빈도부사 (don't always) 소괄호
    state 3: 본동사 put [Vt 하단 + 로즈핑크 이중밑줄]
    state 4: 목적어 everything [O 하단 + 에메랄드 밑줄]
    state 5: 관계대명사절 (that's important) 소괄호 + [상단 S, SC] + 수식 화살표 ↖
    state 6: 전치사구 (to them)) (into words). 소괄호 완성
    """
    im = render_board_base()
    draw = ImageDraw.Draw(im)

    font_mono = get_mono_font(46)
    font_tag_main = get_mono_font(30)
    font_tag_dep = get_mono_font(21)

    char_w = 25.0
    start_x = 120
    y1 = 360
    y2 = 540

    # 텍스트 형태 (state에 따라 괄호 점진적 등장)
    # state 0~1: 괄호 없음
    # state 2: (don't always)
    # state 5: (that's important
    # state 6: (to them)) (into words).
    if state < 2:
        l1_text = "1. Speakers don't always put everything that's important"
        l2_text = "   to them into words."
        col_s = (3, 11)       # Speakers
        col_v = (25, 28)      # put
        col_o = (29, 39)      # everything
        col_that = (40, 46)   # that's
        col_imp = (47, 56)    # important
    else:
        l1_text = "1. Speakers (don't always) put everything (that's important" if state >= 5 else "1. Speakers (don't always) put everything that's important"
        l2_text = "   (to them)) (into words)." if state >= 6 else "   to them into words."
        col_s = (3, 11)       # Speakers
        col_v = (27, 30)      # put
        col_o = (31, 41)      # everything
        col_that = (43, 49)   # that's
        col_imp = (50, 59)    # important

    draw.text((start_x, y1), l1_text, fill=COLOR_WHITE, font=font_mono)
    draw.text((start_x, y2), l2_text, fill=COLOR_WHITE, font=font_mono)

    # State 1+: 주절 주어 S (하단)
    if state >= 1:
        tx1 = start_x + int(col_s[0] * char_w)
        tx2 = start_x + int(col_s[1] * char_w)
        draw.line([(tx1, y1 + 48), (tx2, y1 + 48)], fill=COLOR_S_BLUE, width=3)
        draw.text((tx1 + (tx2 - tx1 - 18) // 2, y1 + 54), "S", fill=COLOR_S_BLUE, font=font_tag_main)

    # State 3+: 주절 본동사 Vt (하단 이중밑줄)
    if state >= 3:
        tx1 = start_x + int(col_v[0] * char_w)
        tx2 = start_x + int(col_v[1] * char_w)
        draw.line([(tx1, y1 + 48), (tx2, y1 + 48)], fill=COLOR_V_ROSE, width=3)
        draw.line([(tx1, y1 + 54), (tx2, y1 + 54)], fill=COLOR_V_ROSE, width=2)
        draw.text((tx1 + (tx2 - tx1 - 36) // 2, y1 + 60), "Vt", fill=COLOR_V_ROSE, font=font_tag_main)

    # State 4+: 주절 목적어 O (하단)
    if state >= 4:
        tx1 = start_x + int(col_o[0] * char_w)
        tx2 = start_x + int(col_o[1] * char_w)
        draw.line([(tx1, y1 + 48), (tx2, y1 + 48)], fill=COLOR_O_EMERALD, width=3)
        draw.text((tx1 + (tx2 - tx1 - 18) // 2, y1 + 54), "O", fill=COLOR_O_EMERALD, font=font_tag_main)

    # State 5+: 종속절 S, SC (상단) + 수식 화살표 ↖
    if state >= 5:
        # that's S (상단)
        tx1 = start_x + int(col_that[0] * char_w)
        tx2 = start_x + int(col_that[1] * char_w)
        draw.text((tx1 + (tx2 - tx1 - 12) // 2, y1 - 28), "S", fill=COLOR_S_BLUE, font=font_tag_dep)
        # important SC (상단)
        tx1 = start_x + int(col_imp[0] * char_w)
        tx2 = start_x + int(col_imp[1] * char_w)
        draw.text((tx1 + (tx2 - tx1 - 24) // 2, y1 - 28), "SC", fill=COLOR_SC_INDIGO, font=font_tag_dep)
        # Arrow from '(' at col 42 to 'everything' at col 41
        sx = start_x + int(42 * char_w) + 12
        sy = y1 + 56
        ex = start_x + int(col_o[1] * char_w) + 8
        ey = y1 + 48
        draw_modifier_arrow_safe(draw, sx, sy, ex, ey)

    return im

# S1 나레이션 청크 (기호 읽지 않기, 1.0초 텀, 반말체)
S1_CHUNKS = [
    # Chunk 0 -> State 0
    (0, "첫째로, 앞에서부터 끊어 읽으며 구조 분석을 함께 해보자."),
    # Chunk 1 -> State 1
    (1, "주절의 주어인 '화자들은'"),
    # Chunk 2 -> State 2
    (2, "빈도부사인 '항상은' 거품 걷어내기 원칙에 따라 소괄호로 묶어서 제외해."),
    # Chunk 3 -> State 3
    (3, "주절의 본동사인 '표현하지 않는다'는 타동사야."),
    # Chunk 4 -> State 4
    (4, "목적어인 '모든 것을'"),
    # Chunk 5 -> State 5
    (5, "앞의 명사 '모든 것'을 뒤에서 꾸며주는 관계대명사절인 '그들에게 중요한'은 소괄호로 묶고 수식 화살표를 달아줘. 관계사절 안에서 주어인 '관계대명사'와 보어인 '중요한'은 단어 위에 표시해."),
    # Chunk 6 -> State 6
    (6, "마지막으로 전치사구 거품인 '그들에게'와 '말로'는 소괄호로 묶어주면 돼. 전체 문장은 주절의 3형식과 관계사절의 2형식이 결합된 구조야."),
    # Chunk 7 (2단계 내용 맥락) -> State 6
    (6, "이어서, 이 문장의 핵심 내용을 쉽게 정리해 볼게. 화자들은 자기가 중요하다고 생각하는 모든 것을 말로 다 표현하지는 않는다는 내용이야. 언어로 표현하지 않는 다른 중요한 비언어적 메시지가 있을 수 있다는 걸 암시하는 문장이지."),
    # Chunk 8 (3단계 문법 포인트) -> State 6
    (6, "다음으로, 시험에 무조건 출제되는 핵심 문법 포인트를 짚어보자. 여기서 '항상 ~하는 것은 아니다'는 부분 부정을 나타내는 표현이야. 전체를 부정하면 안 돼. 그리고 주격 관계대명사절 안의 동사는 앞의 선행사 '모든 것'에 수일치하여 단수 동사가 온다는 점을 꼭 기억해 둬."),
    # Chunk 9 (4단계 서술형 영작) -> State 6
    (6, "마지막으로, 내신 서술형 영작 대비 포인트야. 이 문장은 타동사 구문과 주격 관계대명사절이 결합된 형태라서 서술형으로 출제되기 아주 좋아. 관계대명사절이 선행사를 뒤에서 수식하는 어순에 유의해서 영작 연습 꼭 해봐야 해.")
]

async def test_s1_pipeline():
    out_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\test_s1_progressive"
    os.makedirs(out_dir, exist_ok=True)

    print("=== [S1 대본-판서 1:1 동기화 테스트 시작] ===")
    
    # 1. 1.0초 무음 파일 생성
    silence_1s = os.path.join(out_dir, "silence_1s.mp3")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "1.0", "-c:a", "libmp3lame", silence_1s], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. 이미지 상태 생성 (State 0 ~ 6)
    state_imgs = {}
    for st in range(7):
        p = os.path.join(out_dir, f"state_{st}.png")
        render_s1_state(st).save(p)
        state_imgs[st] = p
    print("  [OK] 7개 판서 상태 이미지 생성 완료!")

    # 3. 각 청크별 TTS 음성 합성 및 1.0초 텀 추가
    muted_circle = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\teacher_pip_circle.mp4"
    pip_mask = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\pip_mask_circle.png"
    pip_ring = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\pip_ring_circle.png"

    mini_segs = []
    for idx, (st, text) in enumerate(S1_CHUNKS):
        sub_audio = os.path.join(out_dir, f"raw_audio_{idx}.mp3")
        comm = edge_tts.Communicate(text, VOICE, rate="+3%", pitch="+1Hz")
        await comm.save(sub_audio)

        # 1.0s 텀 병합
        cat_txt = os.path.join(out_dir, f"cat_{idx}.txt")
        with open(cat_txt, "w", encoding="utf-8") as f:
            f.write(f"file '{sub_audio.replace(chr(92), '/')}'\n")
            f.write(f"file '{silence_1s.replace(chr(92), '/')}'\n")
        
        timed_audio = os.path.join(out_dir, f"timed_audio_{idx}.mp3")
        subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", cat_txt, "-c", "copy", timed_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # 비디오 세그먼트 렌더링
        img_p = state_imgs[st]
        out_seg = os.path.join(out_dir, f"mini_seg_{idx:02d}.mp4")
        dur = get_audio_duration(timed_audio)

        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-i", img_p,
            "-stream_loop", "-1", "-i", muted_circle,
            "-loop", "1", "-i", pip_mask,
            "-loop", "1", "-i", pip_ring,
            "-i", timed_audio,
            "-filter_complex", "[1:v][2:v]alphamerge[pip];[pip][3:v]overlay[pip_with_ring];[0:v][pip_with_ring]overlay=1590:760:shortest=1[v]",
            "-map", "[v]", "-map", "4:a",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest",
            out_seg
        ]
        t0 = time.time()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"  [OK] Chunk {idx} (State {st}): {round(dur, 1)}초 분량 ({round(time.time() - t0, 1)}초 소요)")
        mini_segs.append(out_seg)

    # 4. Concat all mini segments
    concat_txt = os.path.join(out_dir, "concat_s1.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for ms in mini_segs:
            f.write(f"file '{ms.replace(chr(92), '/')}'\n")

    final_s1 = os.path.join(out_dir, "test_s1_progressive_sync.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", final_s1], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    total_dur = get_audio_duration(final_s1)
    print(f"\n🎉 [성공] S1 점진적 판서 동기화 비디오 완성!")
    print(f" - 파일: {final_s1}")
    print(f" - 재생 시간: {round(total_dur, 1)}초")

if __name__ == "__main__":
    asyncio.run(test_s1_pipeline())
