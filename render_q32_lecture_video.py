import os
import sys
import json
import time
import subprocess
from PIL import Image, ImageDraw
import imageio_ffmpeg

from config import (
    BOARD_BG_COLOR,
    WOOD_FRAME_COLOR,
    PILL_BG_COLOR,
    PILL_BORDER_COLOR,
    YELLOW_TEXT_COLOR,
    WHITE_TEXT_COLOR,
    VERB_ROSE_COLOR,
    SKY_BLUE_COLOR,
    OUTPUT_DIR,
    VIDEOS_DIR
)
from video_renderer import (
    get_font,
    get_audio_duration,
    layout_sentence_tokens,
    render_google_slides_board,
    render_intro_slide,
    render_summary_slide,
    render_sentence_frame_with_float_in,
    prepare_teacher_pip_asset
)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def render_sentence_slide_image(title: str, s_num: int, total_sentences: int, tokens: list, out_img_path: str):
    """
    구글 슬라이드 칠판 원본 양식으로 문장 슬라이드 고해상도(1920x1080) 정지 이미지 생성
    - 영문 단어 레이아웃
    - 본동사 로즈핑크, 주어/목적어 스카이블루, 밑줄 및 S, Vt, Vi, O, SC 태그 포함
    """
    base_bg = render_google_slides_board(title, s_num, total_sentences)
    pos_tokens = layout_sentence_tokens(tokens)
    
    # 모든 태그와 밑줄이 선명하게 표기된 완성 프레임
    all_indices = set(range(len(pos_tokens)))
    frame_img = render_sentence_frame_with_float_in(
        base_bg, pos_tokens,
        completed_tokens_indices=all_indices,
        active_tokens_indices=set(),
        anim_progress=1.0
    )
    frame_img.save(out_img_path, "JPEG", quality=95)

    return out_img_path

def render_sentence_video_segment(
    slide_img_path: str,
    audio_path: str,
    muted_teacher_video: str,
    pip_mask_png: str,
    output_mp4_path: str
):
    """
    슬라이드 이미지 + 문장 TTS 오디오 + 강사 PIP 비디오를 결합하여 고속 인코딩
    """
    cmd = [
        FFMPEG_EXE, "-y",
        "-loop", "1", "-i", slide_img_path,
        "-stream_loop", "-1", "-i", muted_teacher_video,
        "-loop", "1", "-i", pip_mask_png,
        "-i", audio_path,
        "-filter_complex", "[1:v][2:v]alphamerge[pip];[0:v][pip]overlay=1490:810:shortest=1[v]",
        "-map", "[v]", "-map", "3:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        output_mp4_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_mp4_path

def build_full_lecture_video():
    start_time = time.time()
    
    json_path = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output_q32_processed.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    analysis_data = data.get("analysis_data", {})
    title = analysis_data.get("title", "2026년 고3 6월 모의고사 32번")
    summary_info = analysis_data.get("summary_info", {})
    subject = summary_info.get("subject", "비언어적 소통의 중요성과 올바른 해석")
    summary_points = summary_info.get("summary", [])
    sentences = analysis_data.get("sentences", [])
    total_sentences = len(sentences)
    
    tts_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\audio\q32_sentence_tts"
    temp_dir = os.path.join(VIDEOS_DIR, "q32_render_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    print("=" * 60)
    print(f" [AI Lecture Maker] {title} 전체 강의 비디오 렌더링 시작")
    print(f" - 총 문장 수: {total_sentences}개 문장")
    print(f" - 문장별 독립 TTS 오디오: {tts_dir}")
    print("=" * 60)
    
    # 1. 강사 비디오 PIP 에셋 준비
    print("\n[Step 1] 우하단 강사 비디오 PIP 마스크 및 무음 클립 준비...")
    muted_teacher_video, pip_mask_png = prepare_teacher_pip_asset(VIDEOS_DIR)
    
    segment_mp4s = []
    
    # 2-0. 제목 장표 (Cover Slide / Slide 0) 10초 오프닝 렌더링
    intro_audio = os.path.join(tts_dir, "sentence_00_intro.mp3")
    if os.path.exists(intro_audio):
        print("\n[Step 2-0] 제목 장표 (Cover Slide) 10초 오프닝 렌더링 중...")
        intro_dur = get_audio_duration(intro_audio)
        intro_slide_img = os.path.join(temp_dir, "slide_00_intro.jpg")
        intro_seg_mp4 = os.path.join(temp_dir, "seg_00_intro.mp4")
        
        # 구글 슬라이드 1번 표지 양식 (대제목 + 주제 카드) 렌더링
        intro_img = render_intro_slide(title, subject)
        intro_img.save(intro_slide_img, "JPEG", quality=95)
        
        t0 = time.time()
        render_sentence_video_segment(
            intro_slide_img, intro_audio, muted_teacher_video, pip_mask_png, intro_seg_mp4
        )
        elapsed = round(time.time() - t0, 1)
        print(f"  ✅ [제목 장표 표지] 렌더링 완료 ({round(intro_dur, 1)}초 분량, 렌더링 {elapsed}초) -> {os.path.basename(intro_seg_mp4)}")
        segment_mp4s.append(intro_seg_mp4)
    
    # 2. 문장별 슬라이드 + TTS 오디오 결합 렌더링
    print("\n[Step 2] 문장별 1080p 칠판 판서 + 강사 PIP 비디오 렌더링 중...")
    for idx, s in enumerate(sentences):
        s_num = idx + 1
        tokens = s.get("tokens", [])
        audio_file = os.path.join(tts_dir, f"sentence_{s_num:02d}.mp3")
        
        if not os.path.exists(audio_file):
            print(f"  ⚠️ 오디오 파일 없음: {audio_file}, 건너뜁니다.")
            continue
            
        dur = get_audio_duration(audio_file)
        slide_img = os.path.join(temp_dir, f"slide_{s_num:02d}.jpg")
        seg_mp4 = os.path.join(temp_dir, f"seg_{s_num:02d}.mp4")
        
        # 슬라이드 이미지 생성
        render_sentence_slide_image(title, s_num, total_sentences, tokens, slide_img)
        
        # 비디오 세그먼트 인코딩
        t0 = time.time()
        render_sentence_video_segment(
            slide_img, audio_file, muted_teacher_video, pip_mask_png, seg_mp4
        )
        elapsed = round(time.time() - t0, 1)
        print(f"  ✅ [문장 {s_num:02d}] 렌더링 완료 ({round(dur, 1)}초 분량, 렌더링 {elapsed}초) -> {os.path.basename(seg_mp4)}")
        segment_mp4s.append(seg_mp4)
        
    # 3. 전체 세그먼트 무손실 병합 (Concat)
    print("\n[Step 3] 문장별 세그먼트 무손실 병합 중...")
    concat_txt = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for mp4 in segment_mp4s:
            # Escape path for ffmpeg concat demuxer
            safe_p = mp4.replace("\\", "/")
            f.write(f"file '{safe_p}'\n")
            
    final_mp4 = os.path.join(VIDEOS_DIR, "2026_고3_6월_32번_완성강의.mp4")
    cmd_concat = [
        FFMPEG_EXE, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-c", "copy",
        final_mp4
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    total_dur = get_audio_duration(final_mp4)
    file_size_mb = round(os.path.getsize(final_mp4) / (1024 * 1024), 2)
    total_elapsed = round(time.time() - start_time, 1)
    
    print("\n" + "=" * 60)
    print(f"🎉 [렌더링 대성공] 최종 AI 강의 비디오 제작 완료!")
    print(f" - 최종 파일: {final_mp4}")
    print(f" - 총 강의 재생 시간: {round(total_dur / 60, 1)}분 ({round(total_dur, 1)}초)")
    print(f" - 파일 용량: {file_size_mb} MB")
    print(f" - 총 렌더링 소요 시간: {total_elapsed}초")
    print("=" * 60)
    
    return final_mp4

if __name__ == "__main__":
    build_full_lecture_video()
