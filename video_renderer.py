import os
import sys
import subprocess
import json
import math
import time
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from config import (
    VIDEOS_DIR, TEACHER_VIDEO_SOURCE,
    BOARD_BG_COLOR, WOOD_FRAME_COLOR, PILL_BG_COLOR, PILL_BORDER_COLOR,
    YELLOW_TEXT_COLOR, WHITE_TEXT_COLOR, VERB_ROSE_COLOR, SKY_BLUE_COLOR
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# Windows 표준 폰트 (말콤/콘솔라스/고딕)
FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_REG = r"C:\Windows\Fonts\malgun.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"

def get_font(size: int, bold: bool = False, mono: bool = False):
    p = FONT_MONO if mono else (FONT_BOLD if bold else FONT_REG)
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()

def get_audio_duration(audio_path: str) -> float:
    """FFmpeg를 통해 오디오 파일의 정확한 재생 길이를 초(seconds) 단위로 반환"""
    if not os.path.exists(audio_path):
        return 4.0
    cmd = [FFMPEG_EXE, '-i', audio_path]
    res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
    for line in res.stderr.splitlines():
        if 'Duration:' in line:
            try:
                parts = line.split('Duration:')[1].split(',')[0].strip().split(':')
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            except Exception:
                pass
    return 4.0

def prepare_teacher_pip_asset(output_dir: str) -> tuple:
    """
    사용자가 지정한 Downloads의 강사 영상(gemini_generated_video_24c9f37e.mp4)을
    음성 제거(-an) 및 384x216 해상도로 전처리하고 라운드 마스크를 생성합니다.
    """
    os.makedirs(output_dir, exist_ok=True)
    muted_mp4 = os.path.join(output_dir, "teacher_pip_muted.mp4")
    mask_png = os.path.join(output_dir, "pip_mask.png")

    # 1. 강사 비디오 음성 제거 및 384x216 리사이즈 (H.264 짝수 해상도 규격)
    if not os.path.exists(muted_mp4) or os.path.getsize(muted_mp4) < 1000:
        if os.path.exists(TEACHER_VIDEO_SOURCE):
            src = TEACHER_VIDEO_SOURCE
        else:
            # 기본 다운로드 폴더 재탐색
            fallback = r"C:\Users\stone\Downloads\gemini_generated_video_24c9f37e.mp4"
            src = fallback if os.path.exists(fallback) else None

        if src and os.path.exists(src):
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", src,
                "-an",
                "-vf", "scale=384:216",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                muted_mp4
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            print(f"[VideoRenderer] 강사 영상({TEACHER_VIDEO_SOURCE})을 찾지 못하여 기본 루프를 사용합니다.")

    # 2. 부드러운 라운드 사각 마스크 (반경 16px)
    if not os.path.exists(mask_png):
        mask_im = Image.new("L", (384, 216), 0)
        d = ImageDraw.Draw(mask_im)
        d.rounded_rectangle([0, 0, 383, 215], radius=16, fill=255)
        mask_im.save(mask_png)

    return muted_mp4, mask_png

def layout_sentence_tokens(tokens: list, max_width: int = 1420, start_x: int = 110, start_y: int = 240, line_height: int = 190):
    """
    구글 슬라이드 양식과 동일하게 칠판 위 영문 텍스트 및 태그 좌표 계산
    """
    dummy_im = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(dummy_im)
    font_word = get_font(36, bold=True)

    positioned_tokens = []
    cur_x = start_x
    cur_y = start_y

    for t in tokens:
        word_text = t.get("text", "")
        is_slash = (word_text == " / ")
        tb = draw.textbbox((0, 0), word_text, font=font_word)
        w = tb[2] - tb[0]
        h = tb[3] - tb[1]

        # 줄바꿈 판별 (우하단 강사 PIP 및 우측 마진 고려)
        if cur_x + w > max_width and not is_slash:
            cur_x = start_x
            cur_y += line_height

        item = dict(t)
        item["x"] = cur_x
        item["y"] = cur_y
        item["w"] = w
        item["h"] = h
        positioned_tokens.append(item)

        cur_x += w + (8 if is_slash else 16)

    return positioned_tokens

def render_google_slides_board(title: str, sentence_idx: int = 0, total_sentences: int = 0, step_title: str = "") -> Image.Image:
    """
    구글 슬라이드(1D_VcwBzmWmTjXV2cRIZUNffHxwruekiUzSTrTZrTV8A) 판서 원본과 100% 동일한
    다크 초록 칠판(#143827) + 마호가니 원목 프레임(#3E2723) 캔버스 생성
    """
    width, height = 1920, 1080
    # 1. 칠판 본체 배경
    im = Image.new("RGB", (width, height), BOARD_BG_COLOR)
    draw = ImageDraw.Draw(im)

    # 2. 클래식 다크 마호가니 원목 외곽 프레임 (두께 16px)
    frame_w = 16
    draw.rectangle([0, 0, width, frame_w], fill=WOOD_FRAME_COLOR)
    draw.rectangle([0, height - frame_w, width, height], fill=WOOD_FRAME_COLOR)
    draw.rectangle([0, 0, frame_w, height], fill=WOOD_FRAME_COLOR)
    draw.rectangle([width - frame_w, 0, width, height], fill=WOOD_FRAME_COLOR)

    # 3. 상단 헤더 영역
    # 좌측 타이틀 둥근 카드 (노란색 글씨)
    pill_font = get_font(20, bold=True)
    tb = draw.textbbox((0, 0), title, font=pill_font)
    pw = max(260, tb[2] - tb[0] + 36)
    draw.rounded_rectangle([60, 42, 60 + pw, 88], radius=10, fill=PILL_BG_COLOR, outline=PILL_BORDER_COLOR, width=1)
    draw.text((78, 52), title, fill=YELLOW_TEXT_COLOR, font=pill_font)

    # 우측 에이닷 영어학원 로고 텍스트
    right_font = get_font(22, bold=True)
    draw.text((1680, 50), "에이닷 영어학원", fill=WHITE_TEXT_COLOR, font=right_font)

    # 상단 구분선
    draw.line([(60, 106), (1860, 106)], fill=(36, 88, 62), width=1)

    return im

def render_intro_slide(title: str, topic: str = "") -> Image.Image:
    """슬라이드 1번 표지 양식 (대제목 + 주제 카드)"""
    im = render_google_slides_board(title)
    draw = ImageDraw.Draw(im)

    # 중앙 대형 제목
    center_y = 380
    title_font = get_font(52, bold=True)
    tb = draw.textbbox((0, 0), title, font=title_font)
    tw = tb[2] - tb[0]
    draw.text(((1920 - tw) // 2, center_y), title, fill=WHITE_TEXT_COLOR, font=title_font)

    # 하단 둥근 주제 카드
    if topic:
        topic_font = get_font(24, bold=True)
        tb_t = draw.textbbox((0, 0), topic, font=topic_font)
        box_w = max(900, tb_t[2] - tb_t[0] + 60)
        box_x1 = (1920 - box_w) // 2
        box_y1 = center_y + 180
        draw.rounded_rectangle([box_x1, box_y1, box_x1 + box_w, box_y1 + 90], radius=14, fill=PILL_BG_COLOR, outline=PILL_BORDER_COLOR, width=2)
        draw.text((box_x1 + (box_w - (tb_t[2] - tb_t[0])) // 2, box_y1 + 28), topic, fill=YELLOW_TEXT_COLOR, font=topic_font)

    return im

def render_summary_slide(title: str, summary_points: list) -> Image.Image:
    """슬라이드 17번 핵심 3단 요약 카드 양식"""
    im = render_google_slides_board(title)
    draw = ImageDraw.Draw(im)

    header_y = 150
    draw.text((100, header_y), "📌 지문 핵심 3단 요약 정리", fill=YELLOW_TEXT_COLOR, font=get_font(32, bold=True))

    card_w = 520
    card_h = 440
    gap = 40
    start_x = (1920 - (card_w * 3 + gap * 2)) // 2
    card_y = 230

    titles = ["1. 핵심 요인 (Key Factor)", "2. 문제점 (Challenge)", "3. 대안 및 결론 (Solution)"]

    for i in range(3):
        cx = start_x + i * (card_w + gap)
        # 카드 배경
        draw.rounded_rectangle([cx, card_y, cx + card_w, card_y + card_h], radius=16, fill=PILL_BG_COLOR, outline=PILL_BORDER_COLOR, width=2)
        # 카드 상단 소제목
        draw.text((cx + 24, card_y + 24), titles[i], fill=YELLOW_TEXT_COLOR, font=get_font(22, bold=True))
        draw.line([(cx + 24, card_y + 64), (cx + card_w - 24, card_y + 64)], fill=(40, 100, 70), width=1)
        # 카드 본문 내용
        content = summary_points[i] if i < len(summary_points) else ""
        # 텍스트 줄바꿈
        lines = []
        words = content.split(" ")
        cur_l = ""
        for w in words:
            if len(cur_l + w) > 22:
                lines.append(cur_l)
                cur_l = w + " "
            else:
                cur_l += w + " "
        if cur_l:
            lines.append(cur_l)

        cy = card_y + 85
        for l in lines:
            draw.text((cx + 24, cy), l, fill=WHITE_TEXT_COLOR, font=get_font(20, bold=False))
            cy += 36

    return im

def render_sentence_frame_with_float_in(
    base_bg: Image.Image,
    tokens: list,
    completed_tokens_indices: set,
    active_tokens_indices: set,
    anim_progress: float
) -> Image.Image:
    """
    PPT '올라오기 (Float In)' 애니메이션 렌더러
    - anim_progress: 0.0 -> 1.0 (0.35초 동안 dy: +18px -> 0px, alpha: 0% -> 100%)
    - 활성 토큰들의 밑줄 및 성분 태그(S, Vt, Vi, O, SC 등)가 아래에서 부드럽게 솟아오르며 페이드인
    """
    # 1. 베이스 칠판 복사
    frame = base_bg.copy()
    overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    font_word = get_font(36, bold=True)
    font_tag = get_font(24, bold=True)

    # PPT Float-in 이징 곡선 (Cubic Ease-Out)
    ease_out = 1.0 - (1.0 - min(1.0, max(0.0, anim_progress))) ** 3
    float_dy = int(18 * (1.0 - ease_out))
    float_alpha = int(255 * ease_out)

    for idx, t in enumerate(tokens):
        word_text = t.get("text", "")
        tx, ty, tw, th = t["x"], t["y"], t["w"], t["h"]
        sub_tag = t.get("sub_tag", "")
        underline = t.get("underline", False)
        color_key = t.get("color", "white")

        is_completed = (idx in completed_tokens_indices)
        is_active = (idx in active_tokens_indices)

        # 1. 단어 색상 결정
        # 구글 슬라이드 양식: 동사(Vi/Vt)는 로즈핑크(#F87171), 일반은 화이트(#FFFFFF)
        if (is_completed or is_active) and (sub_tag in ("Vi", "Vt") or color_key == "rose"):
            word_color = VERB_ROSE_COLOR + (255,)
        else:
            word_color = WHITE_TEXT_COLOR + (255,)

        od.text((tx, ty), word_text, fill=word_color, font=font_word)

        # 2. 밑줄 및 태그 렌더링
        if not (sub_tag or underline):
            continue

        if is_completed:
            # 이미 완료된 성분: 온전한 불투명도, dy = 0
            alpha = 255
            cur_dy = 0
        elif is_active:
            # 현재 활성화(올라오기 중): 부드럽게 상승하며 페이드인
            alpha = float_alpha
            cur_dy = float_dy
        else:
            # 아직 등장 순서가 아님
            continue

        if alpha <= 0:
            continue

        # 태그 색상 매핑
        if sub_tag in ("Vi", "Vt") or color_key == "rose":
            tag_color = VERB_ROSE_COLOR + (alpha,)
        elif sub_tag in ("S", "S1", "S2"):
            tag_color = WHITE_TEXT_COLOR + (alpha,)
        elif sub_tag in ("O", "O→", "O1", "O2"):
            tag_color = SKY_BLUE_COLOR + (alpha,)
        elif sub_tag in ("가O", "진O"):
            tag_color = YELLOW_TEXT_COLOR + (alpha,)
        else:
            tag_color = WHITE_TEXT_COLOR + (alpha,)

        # 밑줄
        if underline or sub_tag in ("S", "Vi", "Vt"):
            uy = ty + th + 6 + cur_dy
            od.line([(tx, uy), (tx + tw, uy)], fill=tag_color, width=3)
            # 본동사일 경우 2줄 밑줄
            if sub_tag in ("Vi", "Vt") and t.get("color") == "rose":
                od.line([(tx, uy + 5), (tx + tw, uy + 5)], fill=tag_color, width=2)

        # 태그 텍스트 (S, Vt, Vi, O 등)
        if sub_tag:
            tag_tb = od.textbbox((0, 0), sub_tag, font=font_tag)
            tag_w = tag_tb[2] - tag_tb[0]
            tag_x = tx + (tw - tag_w) // 2
            tag_y = ty + th + 14 + cur_dy
            od.text((tag_x, tag_y), sub_tag, fill=tag_color, font=font_tag)

    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")

def render_segment_video(
    seg_idx: int,
    seg: dict,
    title: str,
    total_sentences: int,
    tokens: list,
    completed_indices: set,
    active_indices: set,
    muted_teacher_video: str,
    pip_mask_png: str,
    output_mp4: str,
    topic: str = "",
    summary_points: list = None,
    fps: int = 25
) -> str:
    """
    개별 세그먼트 MP4 생성:
    1) 구글 슬라이드 칠판 베이스
    2) PPT 올라오기(Float In) 애니메이션 (0.35초 = 9프레임 부드러운 상승)
    3) 우하단 강사 비디오(gemini_generated_video_24c9f37e.mp4) 라운드 PIP 합성
    """
    audio_path = seg.get("audio_path")
    duration = get_audio_duration(audio_path)
    total_frames = max(12, int(duration * fps))

    s_num = seg.get("sentence_index", 0)
    step_type = seg.get("step_type", "general")

    # 1. 특수 슬라이드 (오프닝, 요약, 클로징)
    if s_num == 0 or step_type in ("opening", "summary", "closing"):
        if step_type == "opening":
            bg = render_intro_slide(title, topic)
        elif step_type == "summary":
            bg = render_summary_slide(title, summary_points or [])
        else:
            bg = render_intro_slide("수고하셨습니다! 1:1 구두테스트 준비", "배운 문장구조를 완벽히 숙지하고 테스트를 통과하세요!")

        slide_jpg = output_mp4.replace(".mp4", "_slide.jpg")
        bg.save(slide_jpg, "JPEG", quality=95)

        cmd = [
            FFMPEG_EXE, "-y",
            "-loop", "1", "-i", slide_jpg,
            "-stream_loop", "-1", "-i", muted_teacher_video,
            "-loop", "1", "-i", pip_mask_png,
            "-i", audio_path,
            "-filter_complex", "[1:v][2:v]alphamerge[pip];[0:v][pip]overlay=1490:810:shortest=1[v]",
            "-map", "[v]", "-map", "3:a",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-shortest",
            output_mp4
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(slide_jpg):
            os.remove(slide_jpg)
        return output_mp4

    # 2. 본문 문장 슬라이드
    pos_tokens = layout_sentence_tokens(tokens)
    base_bg = render_google_slides_board(title, s_num, total_sentences)

    # PPT 올라오기 지속 시간 (0.35초 = 9프레임)
    anim_frames = 9
    start_frame = int(0.2 * fps) # 음성 시작 0.2초 후 살짝 뜸들이고 올라오기

    cmd = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", "1920x1080",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-stream_loop", "-1", "-i", muted_teacher_video,
        "-loop", "1", "-i", pip_mask_png,
        "-i", audio_path,
        "-filter_complex", "[1:v][2:v]alphamerge[pip];[0:v][pip]overlay=1490:810:shortest=1[v]",
        "-map", "[v]", "-map", "3:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p", "-shortest",
        output_mp4
    ]

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cached_static_bytes = None

    for f_idx in range(total_frames):
        if f_idx < start_frame:
            # 시작 전 (이전 완료 상태 유지)
            prog = 0.0
        elif f_idx < start_frame + anim_frames:
            # 올라오는 중 (Float In 진행)
            prog = (f_idx - start_frame) / float(anim_frames)
        else:
            # 정착 완료 (100% 위치 고정)
            prog = 1.0

        if prog < 1.0 or cached_static_bytes is None:
            frame_img = render_sentence_frame_with_float_in(
                base_bg, pos_tokens, completed_indices, active_indices, prog
            )
            raw = frame_img.tobytes()
            if prog >= 1.0:
                cached_static_bytes = raw
            p.stdin.write(raw)
        else:
            # 이미 정착된 정지 프레임은 캐시에서 고속 전송
            p.stdin.write(cached_static_bytes)

    p.stdin.close()
    p.wait()

    return output_mp4

def render_lecture_to_mp4(
    script_data: dict,
    analysis_sentences: list,
    audio_package: dict,
    output_mp4_path: str,
    temp_dir: str = None
) -> str:
    """
    구글 슬라이드 판서 양식 + PPT 올라오기(Float In) 애니메이션 + 강사 영상 PIP
    최고 완성도의 고화질 1080p 강의 비디오 렌더러
    """
    title = script_data.get("title", "영어 내신 분석 강의")
    total_sentences = len(analysis_sentences)
    segments = audio_package.get("segments", [])

    if not temp_dir:
        temp_dir = os.path.join(VIDEOS_DIR, "temp_render")
    os.makedirs(temp_dir, exist_ok=True)

    # 1. 강사 비디오 PIP 전처리 (음성 제거 및 리사이즈)
    muted_teacher_video, pip_mask_png = prepare_teacher_pip_asset(VIDEOS_DIR)

    concat_list_file = os.path.join(temp_dir, "concat_list.txt")
    segment_video_files = []

    print(f"[VideoRenderer] 총 {len(segments)}개 세그먼트 (구글슬라이드 칠판 + PPT 올라오기 + 강사PIP) 렌더링 시작...")
    start_time = time.time()

    # 주제 및 요약 포인트 추출
    topic = script_data.get("topic", "")
    summary_points = script_data.get("summary_points", [
        "변화와 새로운 자극에 대한 감각 반응 원리",
        "자기 자극과 외부 자극의 처리 차이",
        "예측 가능성과 적응 메커니즘"
    ])

    current_sentence_num = -1
    completed_indices = set()

    for idx, seg in enumerate(segments):
        s_num = seg.get("sentence_index", 0)
        step_type = seg.get("step_type", "general")

        # 새 문장 진입 시 완료 인덱스 초기화
        if s_num != current_sentence_num:
            current_sentence_num = s_num
            completed_indices = set()

        # 해당 문장 토큰 추출
        tokens = []
        if s_num > 0:
            match_s = next((s for s in analysis_sentences if s.get("index") == s_num), None)
            if match_s:
                tokens = match_s.get("tokens", [])

        # 이번 단계에서 새로 올라올 토큰들 결정 (문장분석 데이터 기반 순서대로)
        active_indices = set()
        if step_type in ("syntax_analysis", "chunk_reading", "grammar_points"):
            # 미표시된 토큰 중 이번 단계에서 활성화할 항목 선별
            for i, tok in enumerate(tokens):
                if i not in completed_indices:
                    tag = tok.get("sub_tag", "")
                    u = tok.get("underline", False)
                    if step_type == "chunk_reading" and (tag or u):
                        active_indices.add(i)
                        break # 끊어읽기는 순차적으로 1개씩
                    elif step_type == "syntax_analysis" and (tag or u):
                        active_indices.add(i)
                    elif step_type == "grammar_points":
                        active_indices.add(i)

        seg_mp4 = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")

        render_segment_video(
            seg_idx=idx,
            seg=seg,
            title=title,
            total_sentences=total_sentences,
            tokens=tokens,
            completed_indices=set(completed_indices),
            active_indices=set(active_indices),
            muted_teacher_video=muted_teacher_video,
            pip_mask_png=pip_mask_png,
            output_mp4=seg_mp4,
            topic=topic,
            summary_points=summary_points,
            fps=25
        )

        segment_video_files.append(seg_mp4)

        # 활성화된 토큰들을 완료 목록으로 이전
        completed_indices.update(active_indices)

        if (idx + 1) % 5 == 0 or (idx + 1) == len(segments):
            elapsed = time.time() - start_time
            print(f"  - [{idx+1}/{len(segments)}] 세그먼트 PPT 올라오기 렌더링 완료 ({elapsed:.1f}초 경과)")

    # 3. 전체 세그먼트 무손실 병합 (FFmpeg Concat)
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for v in segment_video_files:
            safe_p = v.replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    print(f"[VideoRenderer] 최종 비디오 병합 중 -> {output_mp4_path}")
    concat_cmd = [
        FFMPEG_EXE, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy",
        output_mp4_path
    ]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    file_size_mb = os.path.getsize(output_mp4_path) / (1024 * 1024)
    total_elapsed = time.time() - start_time
    print(f"[VideoRenderer] ✅ 1080p 고도화 강의 비디오 완성! 총 소요: {total_elapsed:.1f}초, 크기: {file_size_mb:.1f} MB")

    return output_mp4_path
