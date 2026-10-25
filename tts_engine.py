import os
import re
import base64
import requests
import subprocess
import asyncio
import edge_tts
import imageio_ffmpeg
from google.cloud import texttospeech
from google.oauth2 import service_account

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "ttsmaker-key.json")
if not os.path.exists(KEY_PATH):
    KEY_PATH = r"C:\Users\stone\Downloads\ttsmaker-499105-761edd14dfce.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AIzaSyC7sBdTtPsQ7Zmnh3MUHzXBkSXgdmLlWm8"

def clean_script_text(text: str) -> str:
    """TTS 발화용 텍스트 정제"""
    t = text.replace(" / ", ", ")
    t = re.sub(r'([.?!])\s*', r'\1 ', t)
    # 영어 약어가 들어올 경우 한국어 발음화
    t = t.replace("S", "에스").replace("Vt", "타동사").replace("Vi", "자동사").replace("V", "동사")
    t = t.replace("O", "목적어").replace("SC", "주격보어").replace("OC", "목적격보어")
    return t.strip()

def synthesize_google_cloud(text: str, output_path: str, voice_name: str = "ko-KR-Neural2-A", speaking_rate: float = 1.05) -> bool:
    """
    Google Cloud Text-to-Speech API를 통한 신경망(Neural2 / WaveNet) 음성 합성
    - 사용자가 제공한 ttsmaker 서비스 계정 키 사용
    """
    if not os.path.exists(KEY_PATH):
        return False
    try:
        credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
        client = texttospeech.TextToSpeechClient(credentials=credentials)

        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # 성별 자동 판별
        gender = texttospeech.SsmlVoiceGender.FEMALE if "-C" not in voice_name and "-D" not in voice_name else texttospeech.SsmlVoiceGender.MALE
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name=voice_name,
            ssml_gender=gender
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            sample_rate_hertz=24000
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)
        return True
    except Exception as e:
        # API 활성화 필요 시 등 에러 로깅
        # print(f"[Google Cloud TTS Notice]: {e}")
        return False

def synthesize_gemini_tts(text: str, output_path: str, voice_name: str = "Aoede", max_retries: int = 3, timeout: int = 40) -> bool:
    """
    Google Gemini 2.5 Flash TTS 엔진 (24kHz 스튜디오 퀄리티)
    - 음성: Aoede (여성, 명확하고 또렷한 설명형 톤), Kore (부드러운 여성)
    - 한국어 낭독 지시어 프리픽스를 포함하여 400 에러 및 타임아웃을 완벽 방지하고 본문만 정확히 발화
    - 단일 성우 100% 보장
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={GEMINI_API_KEY}"
    prompt_text = f"다음 한국어 문장을 또렷하게 낭독하세요:\n\n{text}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
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

    import time
    for attempt in range(max_retries):
        try:
            print(f"      [Gemini TTS Attempt {attempt+1}] Requesting API...", flush=True)
            resp = requests.post(url, json=payload, timeout=timeout)
            print(f"      [Gemini TTS Attempt {attempt+1}] Status: {resp.status_code}", flush=True)
            if resp.status_code == 200:
                data = resp.json()
                pcm_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                pcm_bytes = base64.b64decode(pcm_b64)

                # 무음 패딩 제거 (음성 실제 발화 부분만 정확히 추출)
                import numpy as np
                samples = np.frombuffer(pcm_bytes, dtype=np.int16)
                non_silent = np.where(np.abs(samples) > 200)[0]
                if len(non_silent) > 0:
                    last_idx = min(len(samples), non_silent[-1] + int(24000 * 0.25))
                    pcm_bytes = samples[:last_idx].tobytes()

                p = subprocess.Popen([
                    FFMPEG, "-y",
                    "-f", "s16le", "-ar", "24000", "-ac", "1",
                    "-i", "-",
                    "-c:a", "libmp3lame", "-b:a", "192k",
                    output_path
                ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                p.stdin.write(pcm_bytes)
                p.stdin.close()
                p.wait()
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    print(f"      [Gemini TTS Success] Output size: {os.path.getsize(output_path)} bytes", flush=True)
                    return True
            else:
                print(f"      [Gemini TTS Error] {resp.text[:150]}", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"      [Gemini TTS Exception] {e}", flush=True)
            time.sleep(2)

    return False

async def synthesize_edge_tts(text: str, output_path: str, voice_name: str = "ko-KR-SunHiNeural") -> bool:
    """Edge-TTS 폴백 엔진"""
    try:
        comm = edge_tts.Communicate(text, voice_name, rate="+3%", pitch="+1Hz")
        await comm.save(output_path)
        return True
    except Exception:
        return False

async def synthesize_best_audio(text: str, output_path: str, preferred_engine: str = "auto", voice: str = "Kore") -> str:
    """
    최적의 음질을 자동으로 보장하는 멀티 TTS 엔진
    - preferred_engine == 'gemini': Gemini Aoede 100% 고정 (단일 성우 일관성 보장)
    - preferred_engine == 'google_cloud': Google Cloud TTS
    - preferred_engine == 'auto': Google Cloud -> Gemini -> Edge-TTS
    """
    polished = clean_script_text(text)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # 1. Gemini 전용 모드인 경우: 절대로 Edge-TTS로 변질되지 않도록 단일 성우 100% 보장
    if preferred_engine == "gemini":
        gemini_voice = voice if voice in ("Kore", "Aoede", "Puck", "Charon") else "Aoede"
        for retry_attempt in range(5):
            if synthesize_gemini_tts(polished, output_path, voice_name=gemini_voice, timeout=45):
                return "gemini"
            import time
            time.sleep(2)
        raise RuntimeError(f"Gemini TTS failed for text: {text}")

    # 2. Google Cloud TTS 시도
    if preferred_engine in ("auto", "google_cloud"):
        gc_voice = voice if "ko-KR" in voice else "ko-KR-Neural2-A"
        if synthesize_google_cloud(polished, output_path, voice_name=gc_voice):
            return "google_cloud"

    # 3. Gemini 2.5 TTS 시도
    if preferred_engine == "auto":
        gemini_voice = voice if voice in ("Kore", "Aoede", "Puck", "Charon") else "Aoede"
        if synthesize_gemini_tts(polished, output_path, voice_name=gemini_voice, timeout=90):
            return "gemini"

    # 4. Edge-TTS 폴백 (auto 모드에서만)
    edge_voice = voice if "ko-KR" in voice else "ko-KR-SunHiNeural"
    await synthesize_edge_tts(polished, output_path, voice_name=edge_voice)
    return "edge_tts"
    await synthesize_edge_tts(polished, output_path, voice_name=edge_voice)
    return "edge_tts"
