import os
import sys
import time
import subprocess
import imageio_ffmpeg
from video_renderer import get_audio_duration
from config import VIDEOS_DIR

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def render_segment_circle(slide_img: str, audio_file: str, muted_circle: str, pip_mask: str, pip_ring: str, out_mp4: str):
    cmd = [
        FFMPEG_EXE, "-y",
        "-loop", "1", "-i", slide_img,
        "-stream_loop", "-1", "-i", muted_circle,
        "-loop", "1", "-i", pip_mask,
        "-loop", "1", "-i", pip_ring,
        "-i", audio_file,
        "-filter_complex", "[1:v][2:v]alphamerge[pip];[pip][3:v]overlay[pip_with_ring];[0:v][pip_with_ring]overlay=1590:760:shortest=1[v]",
        "-map", "[v]", "-map", "4:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        out_mp4
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_mp4

def main():
    start_t = time.time()
    slides_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\exact_rule_slides"
    audio_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\audio\q32_sentence_tts"
    temp_dir = os.path.join(VIDEOS_DIR, "exact_test_temp")
    os.makedirs(temp_dir, exist_ok=True)

    muted_circle = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\teacher_pip_circle.mp4"
    pip_mask = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\pip_mask_circle.png"
    pip_ring = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\pip_ring_circle.png"

    print("=== [Google Slides 양식 일치 시험 제작 비디오 렌더링 시작] ===")

    segments_info = [
        ("00_cover", os.path.join(slides_dir, "slide_00_cover.png"), os.path.join(audio_dir, "sentence_00_intro.mp3"), "시작 장표 (표지 10초 오프닝)"),
        ("01_sent1", os.path.join(slides_dir, "slide_01_sentence1.png"), os.path.join(audio_dir, "sentence_01.mp3"), "1번 문장 구조분석"),
        ("02_sent2", os.path.join(slides_dir, "slide_02_sentence2.png"), os.path.join(audio_dir, "sentence_02.mp3"), "2번 문장 구조분석"),
        ("last_summary", os.path.join(slides_dir, "slide_last_summary.png"), os.path.join(audio_dir, "sentence_last_closing.mp3"), "마지막 장표 (주제, 핵심어휘 3개, 3단 정리)")
    ]

    seg_files = []
    for tag, img, audio, desc in segments_info:
        dur = get_audio_duration(audio)
        out_mp4 = os.path.join(temp_dir, f"seg_{tag}.mp4")
        t0 = time.time()
        render_segment_circle(img, audio, muted_circle, pip_mask, pip_ring, out_mp4)
        elapsed = round(time.time() - t0, 1)
        print(f"  [OK] [{desc}] 렌더링 완료 ({round(dur, 1)}초 분량, {elapsed}초 소요) -> {os.path.basename(out_mp4)}")
        seg_files.append(out_mp4)

    # Concat
    print("\n[병합] 세그먼트 무손실 병합 중...")
    concat_txt = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for sf in seg_files:
            safe_p = sf.replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    final_mp4 = os.path.join(VIDEOS_DIR, "2026_고3_6월_32번_시험제작강의.mp4")
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
    total_elapsed = round(time.time() - start_t, 1)

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Google Slides 양식 100% 일치 AI 강의 비디오 완성!")
    print(f" - 최종 파일: {final_mp4}")
    print(f" - 총 강의 재생 시간: {round(total_dur / 60, 1)}분 ({round(total_dur, 1)}초)")
    print(f" - 파일 용량: {file_size_mb} MB")
    print(f" - 총 렌더링 소요 시간: {total_elapsed}초")
    print("=" * 60)

if __name__ == "__main__":
    main()
