import os
import sys
import time
import json
import argparse
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


from config import VIDEOS_DIR
from sheet_loader import list_available_lectures, get_lecture_data, load_lecture_rules
from script_generator import generate_lecture_script
from audio_synthesizer import synthesize_lecture_audio
from video_renderer import render_lecture_to_mp4
from drive_uploader import upload_video_to_gdrive, check_drive_folder_access

def process_lecture_by_row(row_index: int, auto_upload: bool = True) -> dict:
    """
    단일 행 번호(row_index)에 대해 [구글시트 읽기 -> 대본 생성 -> 음성 합성 -> 영상 렌더링 -> 드라이브 업로드]를
    완전 자동화하여 초고속으로 수행합니다.
    """
    t_start = time.time()
    print("\n" + "=" * 70)
    print(f" 🚀 [Batch Worker] 행 #{row_index}번 강의 자동 제작 파이프라인 시작")
    print("=" * 70)

    # 1. 시트 데이터 로드
    t0 = time.time()
    lecture_data = get_lecture_data(row_index)
    rules_data = load_lecture_rules()
    title = lecture_data["title"]
    analysis_sentences = lecture_data["analysis_data"].get("sentences", [])
    print(f"[1/5] 구글 시트 로드 완료 ({time.time()-t0:.1f}s) - 제목: {title} (총 {len(analysis_sentences)}문장)")

    # 2. Gemini 대본 생성 (캐시 확인)
    t0 = time.time()
    safe_title = f"row_{row_index}_" + "".join(
        c for c in title if c.isalnum() or c in (" ", "_", "-")
    ).strip()
    script_cache_path = os.path.join(os.path.dirname(__file__), "output", "scripts", f"{safe_title}_script.json")
    alt_cache_path = os.path.join(os.path.dirname(__file__), "output", "scripts", f"{title}_script.json")
    if not os.path.exists(script_cache_path) and os.path.exists(alt_cache_path):
        script_cache_path = alt_cache_path
    
    if os.path.exists(script_cache_path):
        print(f"[2/5] 기존 생성된 대본 캐시 사용 ({script_cache_path})")
        with open(script_cache_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
    else:
        print("[2/5] Gemini 2.5 Flash API로 강의 대본 및 판서 큐 생성 중...")
        script_data = generate_lecture_script(lecture_data, rules_data)
        print(f"      대본 생성 완료 ({time.time()-t0:.1f}s)")

    # 3. 음성 합성 (Edge-TTS)
    t0 = time.time()
    print("[3/5] 에이닷 강사 음성(TTS) 고속 합성 및 타임스탬프 계산 중...")
    audio_package = synthesize_lecture_audio(script_data, safe_title)
    total_dur = audio_package.get("total_lecture_duration", 0)
    print(f"      음성 합성 완료 ({time.time()-t0:.1f}s) - 총 세그먼트: {len(audio_package.get('segments', []))}개 ({total_dur}초 분량)")

    # 4. 1080p 고화질 비디오 초고속 렌더링 (Pillow + FFmpeg)
    t0 = time.time()
    print("[4/5] 1080p 고화질 판서 비디오 초고속 렌더링 중...")
    output_mp4_path = os.path.join(VIDEOS_DIR, f"{safe_title}.mp4")
    render_lecture_to_mp4(
        script_data=script_data,
        analysis_sentences=analysis_sentences,
        audio_package=audio_package,
        output_mp4_path=output_mp4_path
    )
    print(f"      비디오 렌더링 완료 ({time.time()-t0:.1f}s) -> {output_mp4_path}")

    # 5. 구글 드라이브 업로드
    drive_result = None
    if auto_upload:
        t0 = time.time()
        print("[5/5] 구글 드라이브 지정 폴더(1ACmmG-77ycbPwLXgu8vrK3bSOaeNKHtO) 업로드 중...")
        drive_result = upload_video_to_gdrive(
            local_file_path=output_mp4_path,
            custom_filename=f"{title}_AI판서강의.mp4"
        )
        if drive_result.get("success"):
            print(f"      ✅ 구글 드라이브 업로드 완료 ({time.time()-t0:.1f}s)!")
            print(f"      🔗 영상 링크: {drive_result.get('view_link')}")
        else:
            print(f"      ⚠️ 드라이브 안내: {drive_result.get('hint')}")

    total_elapsed = time.time() - t_start
    print("=" * 70)
    print(f" ✨ 행 #{row_index}번 [{title}] 제작 완료! (총 소요 시간: {total_elapsed:.1f}초)")
    print("=" * 70)

    return {
        "row_index": row_index,
        "title": title,
        "video_path": output_mp4_path,
        "drive_result": drive_result,
        "total_elapsed_sec": round(total_elapsed, 1)
    }

def batch_process_all(max_workers: int = 1, auto_upload: bool = True):
    """구글 시트 RDB_ 교안의 모든 교안을 순회하여 일괄 대량 생성"""
    lectures = list_available_lectures()
    # 강의용 교안 우선 필터링
    target_lectures = [l for l in lectures if "강의용" in l["doc_type"] or "교안" in l["doc_type"]]
    if not target_lectures:
        target_lectures = lectures

    print(f"\n[Batch] 총 {len(target_lectures)}개 교안 대량 생성 작업을 시작합니다.")
    results = []

    for item in target_lectures:
        try:
            res = process_lecture_by_row(item["row_index"], auto_upload=auto_upload)
            results.append(res)
        except Exception as e:
            print(f"❌ 행 #{item['row_index']}번 처리 중 오류: {e}")

    print("\n" + "=" * 70)
    print(f" 🏁 전체 대량 생성 완료: 총 {len(results)}/{len(target_lectures)}개 성공")
    for r in results:
        link = r.get("drive_result", {}).get("view_link", "로컬 저장됨")
        print(f" - #{r['row_index']} {r['title']}: {link} ({r['total_elapsed_sec']}s)")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI English Lecture Bulk Video Batch Generator")
    parser.add_argument("--row", type=int, default=None, help="Process single row index (e.g. --row 4)")
    parser.add_argument("--all", action="store_true", help="Process all available lecture rows in sheet")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")
    args = parser.parse_args()

    if args.row:
        process_lecture_by_row(args.row, auto_upload=not args.no_upload)
    elif args.all:
        batch_process_all(auto_upload=not args.no_upload)
    else:
        # 기본: 4번 행 테스트 실행
        process_lecture_by_row(4, auto_upload=not args.no_upload)
