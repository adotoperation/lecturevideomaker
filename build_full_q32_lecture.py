import os
import sys
import time
import asyncio
import subprocess
import edge_tts
import imageio_ffmpeg
from video_renderer import get_audio_duration
from config import (
    VIDEOS_DIR,
    SPREADSHEET_ID,
    TEACHER_PIP_CIRCLE,
    PIP_MASK_CIRCLE,
    PIP_RING_CIRCLE,
    GEMINI_TTS_VOICE,
    GOOGLE_CLOUD_TTS_VOICE
)
from tts_engine import synthesize_best_audio
from sheet_loader import get_gspread_client
from progressive_lecture_data import (
    render_sentence_state,
    render_cover_slide,
    render_summary_slide,
    LECTURE_CHUNKS
)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "Aoede"  # Gemini 2.5 Studio Aoede (여성, 명확하고 또렷한 설명형 톤)

async def synthesize_chunk_audio(text: str, raw_path: str, timed_path: str, silence_path: str):
    """
    한 개의 대본 청크를 고음질 AI TTS(Gemini 2.5 Studio Aoede)로 생성하고 끝에 1.0초 무음을 정확히 붙여 timed_path로 저장
    """
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
    """
    정지 이미지 + 오디오 + 원형 PIP 버튜버를 합성하여 단일 mini mp4 세그먼트 생성
    """
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

async def main_pipeline():
    start_time = time.time()
    base_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker"
    work_dir = os.path.join(base_dir, "output", "progressive_full_temp")
    audio_dir = os.path.join(base_dir, "output", "audio", "progressive_q32")
    states_dir = os.path.join(base_dir, "output", "progressive_states")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(states_dir, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

    muted_circle = TEACHER_PIP_CIRCLE
    pip_mask = PIP_MASK_CIRCLE
    pip_ring = PIP_RING_CIRCLE

    print("======================================================================")
    print("🚀 [2026년 고3 6월 32번 점진적 실시간 판서 AI 강의 비디오 제작 파이프라인]")
    print("   1. 대본 기호 읽기 배제 (성분 명칭 + 한글 뜻)")
    print("   2. 문장 간 1.0초 텀")
    print("   3. 주절 성분 하단 / 종속절·준동사 성분 상단")
    print("   4. 문장 넘버링 (1. ~ 8.)")
    print("   5. 마무리 요약 장표 전체 상세 설명")
    print("   6. 대본 직독직해 흐름과 1:1 완벽 일치 점진적 판서 (Progressive Reveal)")
    print("======================================================================")

    # 1. 1.0초 무음 파일 생성
    silence_1s = os.path.join(audio_dir, "silence_1s.mp3")
    subprocess.run([
        FFMPEG, "-y", "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", "1.0", "-c:a", "libmp3lame", silence_1s
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("\n[STEP 1/5] 1.0초 무음 템플릿 생성 완료!")

    # 2. 모든 판서 상태 이미지 사전 렌더링
    print("\n[STEP 2/5] 전체 문장 및 장표 판서 상태 이미지 렌더링 중...")
    cover_img_path = os.path.join(states_dir, "cover.png")
    render_cover_slide().save(cover_img_path)

    summary_img_path = os.path.join(states_dir, "summary.png")
    render_summary_slide().save(summary_img_path)

    sentence_state_imgs = {}
    for s_idx in range(1, 9):
        sentence_state_imgs[s_idx] = {}
        chunks = LECTURE_CHUNKS[s_idx]
        max_st = max(st for st, _ in chunks)
        for st in range(max_st + 1):
            p = os.path.join(states_dir, f"s{s_idx}_st{st}.png")
            render_sentence_state(s_idx, st).save(p)
            sentence_state_imgs[s_idx][st] = p
        print(f"  [OK] 문장 {s_idx}번: 총 {max_st + 1}개 판서 단계 이미지 생성")

    # 3. 비디오 세그먼트 생성 (0: 표지, 1~8: 문장별, 9: 요약)
    print("\n[STEP 3/5] 점진적 판서 동기화 세그먼트 렌더링 시작...")
    main_seg_files = []

    # Segment 0: 표지 오프닝
    t_start_seg = time.time()
    intro_chunks = LECTURE_CHUNKS[0]
    intro_audio_raw = os.path.join(audio_dir, "intro_raw.mp3")
    intro_audio_timed = os.path.join(audio_dir, "intro_timed.mp3")
    await synthesize_chunk_audio(intro_chunks[0][1], intro_audio_raw, intro_audio_timed, silence_1s)
    seg_00_mp4 = os.path.join(work_dir, "seg_00_intro.mp4")
    render_mini_segment(cover_img_path, intro_audio_timed, muted_circle, pip_mask, pip_ring, seg_00_mp4)
    dur_00 = get_audio_duration(seg_00_mp4)
    print(f"  [OK] [00. 표지 오프닝] 완성: {round(dur_00, 1)}초 분량 ({round(time.time() - t_start_seg, 1)}초 소요)")
    main_seg_files.append(seg_00_mp4)

    # Segment 1 ~ 8: 각 문장별 점진적 판서 미니 세그먼트 생성 후 병합
    for s_idx in range(1, 9):
        t_s = time.time()
        chunks = LECTURE_CHUNKS[s_idx]
        s_mini_segs = []
        s_work_dir = os.path.join(work_dir, f"s{s_idx}")
        os.makedirs(s_work_dir, exist_ok=True)

        for c_idx, (st, text) in enumerate(chunks):
            raw_a = os.path.join(s_work_dir, f"raw_{c_idx:02d}.mp3")
            timed_a = os.path.join(s_work_dir, f"timed_{c_idx:02d}.mp3")
            await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)

            img_p = sentence_state_imgs[s_idx][st]
            mini_mp4 = os.path.join(s_work_dir, f"mini_{c_idx:02d}.mp4")
            render_mini_segment(img_p, timed_a, muted_circle, pip_mask, pip_ring, mini_mp4)
            s_mini_segs.append(mini_mp4)

        # Concat sentence mini segments
        cat_file = os.path.join(s_work_dir, f"concat_s{s_idx}.txt")
        with open(cat_file, "w", encoding="utf-8") as f:
            for ms in s_mini_segs:
                f.write(f"file '{ms.replace(chr(92), '/')}'\n")

        seg_s_mp4 = os.path.join(work_dir, f"seg_{s_idx:02d}_s{s_idx}.mp4")
        subprocess.run([
            FFMPEG, "-y", "-f", "concat", "-safe", "0",
            "-i", cat_file, "-c", "copy", seg_s_mp4
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        s_dur = get_audio_duration(seg_s_mp4)
        print(f"  [OK] [{s_idx:02d}. {s_idx}번 문장 완성] ({len(chunks)}개 청크 동기화): {round(s_dur, 1)}초 분량 ({round(time.time() - t_s, 1)}초 소요)")
        main_seg_files.append(seg_s_mp4)

    # Segment 9: 마무리 요약 장표
    t_sum = time.time()
    summary_chunks = LECTURE_CHUNKS[9]
    sum_work_dir = os.path.join(work_dir, "summary")
    os.makedirs(sum_work_dir, exist_ok=True)
    sum_mini_segs = []

    for c_idx, (_, text) in enumerate(summary_chunks):
        raw_a = os.path.join(sum_work_dir, f"raw_{c_idx:02d}.mp3")
        timed_a = os.path.join(sum_work_dir, f"timed_{c_idx:02d}.mp3")
        await synthesize_chunk_audio(text, raw_a, timed_a, silence_1s)

        mini_mp4 = os.path.join(sum_work_dir, f"mini_{c_idx:02d}.mp4")
        render_mini_segment(summary_img_path, timed_a, muted_circle, pip_mask, pip_ring, mini_mp4)
        sum_mini_segs.append(mini_mp4)

    cat_sum_file = os.path.join(sum_work_dir, "concat_summary.txt")
    with open(cat_sum_file, "w", encoding="utf-8") as f:
        for ms in sum_mini_segs:
            f.write(f"file '{ms.replace(chr(92), '/')}'\n")

    seg_09_mp4 = os.path.join(work_dir, "seg_09_summary.mp4")
    subprocess.run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", cat_sum_file, "-c", "copy", seg_09_mp4
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    dur_09 = get_audio_duration(seg_09_mp4)
    print(f"  [OK] [09. 마무리 요약 장표] 완성: {round(dur_09, 1)}초 분량 ({round(time.time() - t_sum, 1)}초 소요)")
    main_seg_files.append(seg_09_mp4)

    # 4. 전체 강의 비디오 최종 병합
    print("\n[STEP 4/5] 전체 10개 세그먼트 무손실 병합 중...")
    master_concat_txt = os.path.join(work_dir, "concat_master.txt")
    with open(master_concat_txt, "w", encoding="utf-8") as f:
        for sf in main_seg_files:
            f.write(f"file '{sf.replace(chr(92), '/')}'\n")

    final_mp4 = os.path.join(VIDEOS_DIR, "2026_고3_6월_32번_완성강의.mp4")
    subprocess.run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", master_concat_txt, "-c", "copy", final_mp4
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    total_dur = get_audio_duration(final_mp4)
    file_size_mb = round(os.path.getsize(final_mp4) / (1024 * 1024), 2)
    total_elapsed = round(time.time() - start_time, 1)

    print("\n" + "=" * 70)
    print("🎉 [제작 성공] 2026년 고3 6월 32번 점진적 판서 동기화 완성 강의 비디오 완성!")
    print(f" - 최종 파일 경로: {final_mp4}")
    print(f" - 총 재생 시간: {round(total_dur / 60, 1)}분 ({round(total_dur, 1)}초)")
    print(f" - 파일 용량: {file_size_mb} MB")
    print(f" - 총 소요 시간: {total_elapsed}초 ({round(total_elapsed / 60, 1)}분)")
    print("=" * 70)

    # 5. 구글 시트 RDB_지문 Row 96~103 대본 동기화
    try:
        client = get_gspread_client()
        if client:
            print("\n[STEP 5/5] 구글 시트 RDB_지문 Row 96~103 대본 업데이트 중...")
            sh = client.open_by_key(SPREADSHEET_ID)
            ws = sh.worksheet("RDB_지문")
            script_values = []
            for s_idx in range(1, 9):
                chunks = LECTURE_CHUNKS[s_idx]
                combined_script = "\n\n".join(text for _, text in chunks)
                script_values.append([combined_script])
            ws.update(values=script_values, range_name="F96:F103")
            print("  [OK] 구글 시트 F열 대본 업데이트 완료!")
    except Exception as e:
        print(f"  [Notice] 구글 시트 업데이트 중 알림: {e}")

if __name__ == "__main__":
    asyncio.run(main_pipeline())
