import os
import sys
import argparse
from sheet_loader import get_lecture_data, load_lecture_rules
from script_generator import generate_lecture_script
from audio_synthesizer import synthesize_lecture_audio
from drive_uploader import upload_video_to_gdrive, check_drive_folder_access

def run_pipeline(row_index: int = 4, auto_upload: bool = True):
    print("=" * 60)
    print(f" [AI Lecture Maker] 행 #{row_index}번 강의 자동 생성 파이프라인 시작")
    print("=" * 60)

    # 1. 시트 데이터 및 대본 규칙 로드
    print("\n[Step 1] 구글 시트 'RDB_ 교안' 데이터 및 '대본규칙' 로드 중...")
    lecture_data = get_lecture_data(row_index)
    rules_data = load_lecture_rules()
    title = lecture_data.get("title", f"Row_{row_index}")
    sentences = lecture_data.get("analysis_data", {}).get("sentences", [])
    print(f"  - 제목: {title}")
    print(f"  - 유형: {lecture_data.get('doc_type')}")
    print(f"  - 총 문장 수: {len(sentences)}개")

    # 2. Gemini API로 강의 대본 및 판서 액션 큐 생성
    print("\n[Step 2] Gemini 2.5 Flash API로 강의 대본 & 실시간 판서 큐 생성 중...")
    script_data = generate_lecture_script(lecture_data, rules_data)
    print(f"  - 대본 생성 완료! 오프닝: {script_data.get('opening', {}).get('narration')[:60]}...")

    # 3. 음성 합성 (Edge-TTS)
    safe_title = f"row_{row_index}_" + "".join(
        c for c in title if c.isalnum() or c in (" ", "_", "-")
    ).strip()
    print(f"\n[Step 3] 에이닷 강사 음성(TTS) 합성 및 타임라인 계산 중...")
    audio_package = synthesize_lecture_audio(script_data, safe_title)
    total_dur = audio_package.get("total_lecture_duration", 0)
    segments = audio_package.get("segments", [])
    print(f"  - 음성 합성 완료! 총 세그먼트: {len(segments)}개, 총 강의 시간: {total_dur}초")

    # 4. 구글 드라이브 업로드
    if auto_upload:
        print("\n[Step 4] 구글 드라이브 지정 폴더 업로드 시도 중...")
        drive_check = check_drive_folder_access()
        if not drive_check.get("success"):
            print("  ⚠️ 주의: 드라이브 폴더 접근 불가:")
            print(f"     {drive_check.get('hint')}")
        else:
            first_audio = segments[0]["audio_path"]
            res = upload_video_to_gdrive(first_audio, custom_filename=f"{title}_샘플강의.mp3")
            if res.get("success"):
                print(f"  ✅ 업로드 성공! 링크: {res.get('view_link')}")
            else:
                print(f"  ⚠️ 업로드 안내: {res.get('hint')}")

    print("\n" + "=" * 60)
    print(f" [AI Lecture Maker] 강의 생성 완료! 웹 스튜디오에서 즉시 확인 가능합니다.")
    print(f"  스튜디오 URL: http://localhost:5000/studio/{row_index}")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate AI English Lecture from Google Sheet")
    parser.add_argument("--row", type=int, default=4, help="Google Sheet row index (default: 4)")
    args = parser.parse_args()

    run_pipeline(args.row)
