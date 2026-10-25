import os
import json
import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from config import AUDIO_DIR, GDRIVE_TARGET_FOLDER_ID
from sheet_loader import list_available_lectures, get_lecture_data, load_lecture_rules
from script_generator import generate_lecture_script
from audio_synthesizer import synthesize_lecture_audio
from drive_uploader import upload_video_to_gdrive, check_drive_folder_access

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    """메인 대시보드: 스프레드시트의 RDB_ 교안 목록 표시"""
    try:
        lectures = list_available_lectures()
    except Exception as e:
        lectures = []
        print("Error listing lectures:", e)
    
    drive_status = check_drive_folder_access()
    return render_template(
        "index.html",
        lectures=lectures,
        drive_status=drive_status,
        folder_id=GDRIVE_TARGET_FOLDER_ID
    )

@app.route("/api/lectures", methods=["GET"])
def api_get_lectures():
    try:
        lectures = list_available_lectures()
        return jsonify({"status": "success", "data": lectures})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/studio/<int:row_index>")
def studio(row_index: int):
    """지정된 행 번호의 강의 제작 및 실시간 판서 스튜디오 뷰"""
    try:
        lecture_meta = get_lecture_data(row_index)
        drive_status = check_drive_folder_access()
        return render_template(
            "studio.html",
            row_index=row_index,
            lecture_meta=lecture_meta,
            drive_status=drive_status,
            folder_id=GDRIVE_TARGET_FOLDER_ID
        )
    except Exception as e:
        return f"강의 데이터 로드 오류: {e}", 500

@app.route("/api/generate/<int:row_index>", methods=["POST"])
def api_generate_lecture(row_index: int):
    """
    1) 구글 시트에서 문장/구문분석 데이터 로드
    2) Gemini 2.5 Flash로 강의 대본 및 판서 액션 큐 생성
    3) Edge-TTS로 음성 합성 및 타임스탬프 계산
    """
    try:
        print(f"[API] 행 {row_index}번 강의 생성 요청 시작...")
        lecture_data = get_lecture_data(row_index)
        rules_data = load_lecture_rules()

        # 1. Gemini로 강의 대본 생성
        print("[API] 1. Gemini 대본 및 판서 큐 생성 중...")
        script_data = generate_lecture_script(lecture_data, rules_data)

        # 2. 음성 합성 및 동기화 타임스탬프 생성
        print("[API] 2. 음성 합성 (TTS) 및 타임라인 싱크 계산 중...")
        safe_title = f"row_{row_index}_" + "".join(
            c for c in lecture_data["title"] if c.isalnum() or c in (" ", "_", "-")
        ).strip()
        audio_package = synthesize_lecture_audio(script_data, safe_title)

        return jsonify({
            "status": "success",
            "lecture_meta": {
                "title": lecture_data["title"],
                "row_index": row_index,
                "doc_type": lecture_data["doc_type"]
            },
            "analysis_sentences": lecture_data["analysis_data"].get("sentences", []),
            "script": script_data,
            "audio": audio_package
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    """생성된 MP3 음성 파일 제공"""
    return send_from_directory(AUDIO_DIR, filename)

@app.route("/api/upload_drive", methods=["POST"])
def api_upload_drive():
    """생성된 강의 영상을 구글 드라이브 지정 폴더에 업로드"""
    try:
        if "file" in request.files:
            file = request.files["file"]
            filename = request.form.get("filename", file.filename)
            save_path = os.path.join(AUDIO_DIR, filename)
            file.save(save_path)
            res = upload_video_to_gdrive(save_path, custom_filename=filename)
            return jsonify(res)
        else:
            local_path = request.json.get("local_path")
            custom_filename = request.json.get("filename")
            res = upload_video_to_gdrive(local_path, custom_filename=custom_filename)
            return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    print("==================================================")
    print("  AI 영어 내신 판서 강의 엔진 서버 시작")
    print("  URL: http://localhost:5000")
    print("==================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
