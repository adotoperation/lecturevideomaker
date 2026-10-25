import os
import re
import json
import asyncio
import subprocess
import edge_tts
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "ko-KR-SunHiNeural" # 방송용 전문 여성 강사 톤 (안정성 및 음색 일관성 1위)

def clean_spoken_text(text: str) -> str:
    """
    TTS가 읽을 때 어색한 섹션 헤더(1단계 [구조분석 직독직해]: 등)를
    자연스러운 방송용 구어체 연결 멘트로 다듬는 전처리
    """
    t = text
    # 섹션 레이블 자연스러운 반말 구어체 연결어로 치환
    t = re.sub(r'\[제목\s*장표\s*오프닝\]:?', '', t)
    t = re.sub(r'1단계\s*\[구조분석\s*직독직해\]:?', '첫째로, 앞에서부터 끊어 읽으며 구조 분석을 함께 해보자.', t)
    t = re.sub(r'2단계\s*\[내용\s*맥락\s*설명\]:?', '이어서, 이 문장의 핵심 내용을 쉽게 정리해 볼게.', t)
    t = re.sub(r'3단계\s*\[핵심\s*문법\s*출제\s*포인트\]:?', '다음으로, 시험에 무조건 출제되는 핵심 문법 포인트를 짚어보자.', t)
    t = re.sub(r'4단계\s*\[서술형\s*영작\s*대비\s*포인트\]:?', '마지막으로, 내신 서술형 영작 대비 포인트야.', t)
    
    # 괄호 및 기호 정리
    t = t.replace(' / ', ', ')
    t = t.replace('△', '세모')
    t = re.sub(r'[\[\]\(\)]', '', t) # 대괄호, 소괄호 제거 (텍스트는 유지)
    t = re.sub(r'"{1,2}', '', t)    # 불필요한 따옴표 제거
    
    # 숫자 및 성분 기호 한글화 보정
    t = re.sub(r'32번', '삼십이 번', t)
    t = re.sub(r'1형식', '일형식', t)
    t = re.sub(r'2형식', '이형식', t)
    t = re.sub(r'3형식', '삼형식', t)
    t = re.sub(r'4형식', '사형식', t)
    t = re.sub(r'5형식', '오형식', t)
    t = re.sub(r'\bS\b', '주어 에스', t)
    t = re.sub(r'\bVt\b', '타동사 브이티', t)
    t = re.sub(r'\bVi\b', '자동사 브이아이', t)
    t = re.sub(r'\bO\b', '목적어 오', t)
    t = re.sub(r'\bSC\b', '보어 에스씨', t)
    
    # 불필요한 연속 공백 및 줄바꿈 정리
    t = re.sub(r'\n+', ' ', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()

async def synthesize_single_sentence(s_num: int, raw_script: str, out_dir: str, filename: str = None):
    spoken_text = clean_spoken_text(raw_script)
    prefix = f"s{s_num:02d}" if s_num > 0 else "intro"
    raw_path = os.path.join(out_dir, f"temp_{prefix}.mp3")
    norm_path = os.path.join(out_dir, filename if filename else f"sentence_{s_num:02d}.mp3")
    
    # 1. 독립적인 문장별 TTS 합성 (일관된 음색 유지)
    comm = edge_tts.Communicate(spoken_text, VOICE, rate="+4%", pitch="+1Hz")
    await comm.save(raw_path)
    
    # 2. EBU R128 음량 표준화 (Loudness Normalization)
    cmd = [
        FFMPEG, "-y",
        "-i", raw_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "libmp3lame", "-b:a", "192k",
        norm_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(raw_path):
        os.remove(raw_path)
        
    # 3. 정확한 재생 길이 측정
    res = subprocess.run([FFMPEG, "-i", norm_path], capture_output=True, text=True)
    dur = 0.0
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
            break
            
    tag = f"Intro Title" if s_num == 0 else f"Sentence {s_num:02d}"
    print(f"  [{tag}] 음성 생성 완료! ({os.path.basename(norm_path)}) -> 길이: {round(dur, 2)}초, 크기: {os.path.getsize(norm_path)} 바이트")
    return {
        "sentence_num": s_num,
        "filename": os.path.basename(norm_path),
        "audio_path": norm_path,
        "duration": round(dur, 2),
        "file_size": os.path.getsize(norm_path),
        "spoken_text": spoken_text
    }

async def run_all():
    json_path = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output_q32_processed.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scripts = data.get("scripts", {})
    out_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\audio\q32_sentence_tts"
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"=== [문장별 독립 TTS 음성 합성 및 EBU R128 음량 표준화 시작] ===")
    print(f" - 대상 지문: 2026년 고3 6월 모의고사 32번 (총 {len(scripts)}문장)")
    print(f" - 전담 음성 모델: {VOICE} (전문 여성 강사 톤)")
    print(f" - 출력 폴더: {out_dir}\n")
    
    results = []
    for s_idx in range(1, len(scripts) + 1):
        script_text = scripts.get(str(s_idx)) or scripts.get(s_idx)
        if not script_text:
            continue
            
        if s_idx == 1 and "[제목 장표 오프닝]" in script_text:
            parts = script_text.split("1단계 [구조분석 직독직해]")
            intro_text = parts[0].replace("[제목 장표 오프닝]", "").strip()
            rest_text = "1단계 [구조분석 직독직해]\n" + parts[1] if len(parts) > 1 else script_text
            
            # 0번: 제목 장표 10초 오프닝 인사 음성
            res_intro = await synthesize_single_sentence(0, intro_text, out_dir, filename="sentence_00_intro.mp3")
            results.append(res_intro)
            
            # 1번: 문장 1 칠판 구조 분석 음성
            res_s1 = await synthesize_single_sentence(1, rest_text, out_dir, filename="sentence_01.mp3")
            results.append(res_s1)
        else:
            res = await synthesize_single_sentence(s_idx, script_text, out_dir)
            results.append(res)
        
    # Save metadata
    meta_path = os.path.join(out_dir, "tts_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    total_time = sum(r["duration"] for r in results)
    print(f"\n=== [합성 완료] 총 {len(results)}개 음성 파일(제목 장표 오프닝 포함) 생성 완료! ===")
    print(f" - 총 강의 음성 길이: {round(total_time / 60, 1)}분 ({round(total_time, 2)}초)")
    print(f" - 메타데이터 저장: {meta_path}")

if __name__ == "__main__":
    asyncio.run(run_all())
