import os
import re
import asyncio
import subprocess
import base64
import requests
import edge_tts
import imageio_ffmpeg
from config import AUDIO_DIR, GEMINI_API_KEY, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE, DEFAULT_TTS_VOICE

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def preprocess_teacher_text(text: str) -> str:
    """
    TTS가 기계적인 AI 안내방송처럼 읽지 않고 실제 현장 1타 강사처럼
    자연스러운 억양, 호흡, 리듬감으로 발화하도록 텍스트 전처리
    """
    t = text.replace(" / ", ", ")
    t = re.sub(r'([.?!])\s*', r'\1 ', t)
    
    # 영문 약어 자연스러운 한글 발음화
    t = t.replace("S", "에스").replace("V", "브이").replace("Vi", "브이아이").replace("Vt", "브이티")
    t = t.replace("O", "오").replace("SC", "에스씨").replace("OC", "오씨")
    
    return t.strip()

def synthesize_with_gemini(text: str, output_path: str, voice_name: str = GEMINI_TTS_VOICE) -> bool:
    """
    구글 Vids Nyla급 최고 음질의 Gemini 2.5 Flash TTS 엔진 (음성 모델: Kore)
    - 24kHz 초고음질 음성 생성 후 MP3로 초고속 변환
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name
                        }
                    }
                }
            }
        }
        resp = requests.post(url, json=payload, timeout=35)
        if resp.status_code == 200:
            data = resp.json()
            raw_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            pcm_bytes = base64.b64decode(raw_b64)

            p = subprocess.Popen([
                FFMPEG_EXE, "-y",
                "-f", "s16le", "-ar", "24000", "-ac", "1",
                "-i", "-",
                "-c:a", "libmp3lame", "-b:a", "128k",
                output_path
            ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            p.stdin.write(pcm_bytes)
            p.stdin.close()
            p.wait()
            return True
        else:
            print(f"[TTS Notice] Gemini TTS fallback code {resp.status_code}")
            return False
    except Exception as e:
        print(f"[TTS Notice] Gemini TTS fallback: {e}")
        return False

async def synthesize_speech_async(text: str, output_path: str, voice: str = DEFAULT_TTS_VOICE, use_gemini: bool = True):
    """
    Google Vids Nyla 스타일 Gemini TTS(Kore) 우선 합성, 예외 시 Edge-TTS 자동 폴백
    """
    # 캐시 재사용
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return {
            "audio_path": output_path,
            "total_duration": 4.0,
            "boundaries": []
        }

    polished_text = preprocess_teacher_text(text)

    # 1. Google Vids Nyla급 Gemini TTS 시도
    if use_gemini:
        success = synthesize_with_gemini(polished_text, output_path)
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return {
                "audio_path": output_path,
                "total_duration": 4.0,
                "boundaries": []
            }

    # 2. Edge-TTS 폴백
    comm = edge_tts.Communicate(polished_text, voice, rate="+6%", pitch="+2Hz")
    audio_bytes = bytearray()
    boundaries = []

    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
            start_sec = chunk["offset"] / 10_000_000.0
            dur_sec = chunk["duration"] / 10_000_000.0
            boundaries.append({
                "type": chunk["type"],
                "text": chunk.get("text", ""),
                "start": round(start_sec, 3),
                "duration": round(dur_sec, 3),
                "end": round(start_sec + dur_sec, 3)
            })

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    total_duration = boundaries[-1]["end"] if boundaries else 0.0

    return {
        "audio_path": output_path,
        "total_duration": total_duration,
        "boundaries": boundaries
    }

def synthesize_lecture_audio(script_data: dict, safe_title: str, voice: str = DEFAULT_TTS_VOICE) -> dict:
    """
    전체 강의 대본을 순서대로 고속 음성 합성하고 세그먼트 메타데이터를 반환합니다.
    """
    lecture_audio_dir = os.path.join(AUDIO_DIR, safe_title)
    os.makedirs(lecture_audio_dir, exist_ok=True)

    segments = []
    current_time_offset = 0.0

    async def run_all():
        nonlocal current_time_offset

        # 1. 오프닝
        opening = script_data.get("opening", {})
        if opening.get("narration"):
            op_path = os.path.join(lecture_audio_dir, "00_opening.mp3")
            res = await synthesize_speech_async(opening["narration"], op_path, voice=voice)
            segments.append({
                "segment_id": "opening",
                "step_type": "opening",
                "title": "오프닝 멘트",
                "narration": opening["narration"],
                "audio_path": op_path,
                "relative_audio_path": f"/audio/{safe_title}/00_opening.mp3",
                "start_time": current_time_offset,
                "duration": res["total_duration"],
                "end_time": current_time_offset + res["total_duration"],
                "boundaries": res["boundaries"],
                "actions": []
            })
            current_time_offset += res["total_duration"] + 0.2

        # 2. 문장별 단계
        for s_idx, sentence in enumerate(script_data.get("sentences", [])):
            s_num = sentence.get("sentence_index", s_idx + 1)
            original_text = sentence.get("original", "")

            for step in sentence.get("steps", []):
                st_type = step.get("step_type", "general")
                st_title = step.get("title", "")
                st_narration = step.get("narration", "")
                st_actions = step.get("actions", [])

                if not st_narration:
                    continue

                step_fname = f"s{s_num:02d}_{st_type}.mp3"
                step_path = os.path.join(lecture_audio_dir, step_fname)
                res = await synthesize_speech_async(st_narration, step_path, voice=voice)

                segments.append({
                    "segment_id": f"s{s_num}_{st_type}",
                    "sentence_index": s_num,
                    "original_text": original_text,
                    "step_type": st_type,
                    "title": st_title,
                    "narration": st_narration,
                    "audio_path": step_path,
                    "relative_audio_path": f"/audio/{safe_title}/{step_fname}",
                    "start_time": current_time_offset,
                    "duration": res["total_duration"],
                    "end_time": current_time_offset + res["total_duration"],
                    "boundaries": res["boundaries"],
                    "actions": st_actions
                })
                current_time_offset += res["total_duration"] + 0.2

        # 3. 요약 (Summary)
        summary = script_data.get("summary", {})
        if summary.get("narration"):
            sum_path = os.path.join(lecture_audio_dir, "98_summary.mp3")
            res = await synthesize_speech_async(summary["narration"], sum_path, voice=voice)
            segments.append({
                "segment_id": "summary",
                "step_type": "summary",
                "title": "지문 핵심 요약",
                "narration": summary["narration"],
                "audio_path": sum_path,
                "relative_audio_path": f"/audio/{safe_title}/98_summary.mp3",
                "start_time": current_time_offset,
                "duration": res["total_duration"],
                "end_time": current_time_offset + res["total_duration"],
                "boundaries": res["boundaries"],
                "actions": []
            })
            current_time_offset += res["total_duration"] + 0.2

        # 4. 클로징 (Closing)
        closing = script_data.get("closing", {})
        if closing.get("narration"):
            close_path = os.path.join(lecture_audio_dir, "99_closing.mp3")
            res = await synthesize_speech_async(closing["narration"], close_path, voice=voice)
            segments.append({
                "segment_id": "closing",
                "step_type": "closing",
                "title": "클로징 및 구두테스트 안내",
                "narration": closing["narration"],
                "audio_path": close_path,
                "relative_audio_path": f"/audio/{safe_title}/99_closing.mp3",
                "start_time": current_time_offset,
                "duration": res["total_duration"],
                "end_time": current_time_offset + res["total_duration"],
                "boundaries": res["boundaries"],
                "actions": []
            })
            current_time_offset += res["total_duration"]

    asyncio.run(run_all())

    return {
        "title": script_data.get("title", ""),
        "total_segments": len(segments),
        "total_lecture_duration": round(current_time_offset, 1),
        "segments": segments
    }
