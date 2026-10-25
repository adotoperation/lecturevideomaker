import os
import sys
import re
import asyncio
import subprocess
import edge_tts
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "ko-KR-SunHiNeural" # 방송용 전문 여성 강사 톤

# 1. 10초 표지 오프닝
INTRO_SCRIPT = (
    "친구들 안녕! 오늘 같이 볼 지문은 2026년 고3 6월 모의고사 삼십이 번이야. "
    "빈칸 추론 문항이니까 끝까지 집중 바짝 하고 잘 따라와야 해. "
    "자, 그럼 첫 번째 문장부터 바로 들어가 보자!"
)

# 2. 1번 문장 직독직해 (영단어 발음 배제, 순수 한글 해석 + 반말체)
S1_SCRIPT_STEPS = [
    # 1단계: 구조분석 직독직해
    "첫째로, 앞에서부터 끊어 읽으며 구조 분석을 함께 해보자. "
    "'화자는'이 주절의 주어 에스야. "
    "소괄호로 묶인 '항상은' 제이법칙 거품 걷어내기 원칙에 따라 제외하는 빈도부사 거품이야. "
    "'표현하지 않는다'가 주절의 본동사 타동사 브이티야. "
    "'모든 것을'이 본동사의 목적어 오인 삼형식 구조야. "
    "이어서 '그들에게 중요한'이 앞의 명사 '모든 것'을 뒤에서 꾸며주는 주격 관계대명사절이야. "
    "수식하니까 소괄호로 묶고 시작 괄호 밑에서 선행사 쪽으로 뻗어나가는 수식 화살표를 달아줘. "
    "관계사절 안에서 '관계대명사는' 주어 에스, '중요한'은 주격보어 에스씨인 이형식 구조야. "
    "마지막으로 전치사구 거품인 '그들에게'와 '말로'는 소괄호로 묶어서 제외하면 돼. "
    "전체 문장은 주절의 삼형식과 관계사절의 이형식이 결합된 구조야.",

    # 2단계: 내용 맥락 설명
    "이어서, 이 문장의 핵심 내용을 쉽게 정리해 볼게. "
    "화자들은 자기가 중요하다고 생각하는 모든 것을 말로 다 표현하지는 않는다는 내용이야. "
    "언어로 표현하지 않는 다른 중요한 비언어적 메시지가 있을 수 있다는 걸 암시하는 문장이지.",

    # 3단계: 핵심 문법 출제 포인트
    "다음으로, 시험에 무조건 출제되는 핵심 문법 포인트를 짚어보자. "
    "여기서 '항상 ~하는 것은 아니다'는 부분 부정을 나타내는 표현이야. 전체를 부정하면 안 돼. "
    "그리고 주격 관계대명사절 안의 동사는 앞의 선행사 '모든 것'에 수일치하여 단수 동사가 온다는 점을 꼭 기억해 둬.",

    # 4단계: 서술형 영작 대비 포인트
    "마지막으로, 내신 서술형 영작 대비 포인트야. "
    "이 문장은 타동사 구문과 주격 관계대명사절이 결합된 형태라서 서술형으로 출제되기 아주 좋아. "
    "관계대명사절이 선행사를 뒤에서 수식하는 어순에 유의해서 영작 연습 꼭 해봐야 해."
]

# 3. 2번 문장 직독직해 (준동사 상단 표시 규칙 반영, 영단어 발음 배제, 반말체)
S2_SCRIPT_STEPS = [
    # 1단계: 구조분석 직독직해
    "첫째로, 앞에서부터 끊어 읽으며 구조 분석을 함께 해보자. "
    "'매우 흔하게'는 문장 맨 앞의 부사구 거품이니까 소괄호로 묶어서 제외해. "
    "'너는'이 주절의 주어 에스야. "
    "'이해할 수 있다'가 조동사가 결합된 본동사 타동사 브이티야. "
    "'화자의 의미를'이 목적어 오인 삼형식 구조야. "
    "뒤에 오는 전치사구 거품 안에서 '관찰하는 것'은 동명사 준동사야. "
    "준동사니까 단어 상단에 작은 타동사 브이티 기호를 올려줘. "
    "'그들의 비언어적 행동들을'은 준동사의 목적어니까 마찬가지로 단어 상단에 작은 목적어 오 기호를 올려주고 전체를 대괄호로 묶어줘. "
    "뒤이어 예시를 나타내는 표현들 중, 접속사 'or'와 'and' 위에는 하늘색 세모를 쳐주면 돼. "
    "전체 문장은 주어, 본동사, 목적어를 갖춘 완전한 삼형식 문장이야.",

    # 2단계: 내용 맥락 설명
    "이어서, 이 문장의 핵심 내용을 쉽게 정리해 볼게. "
    "우리는 화자의 말이 아니라 목소리 톤이나 표정, 몸짓 같은 비언어적인 행동을 통해서 그들의 진짜 의도를 파악할 수 있다는 이야기야. "
    "말보다 비언어적 행동이 더 솔직한 경우가 많다는 거지.",

    # 3단계: 핵심 문법 출제 포인트
    "다음으로, 시험에 무조건 출제되는 핵심 문법 포인트를 짚어보자. "
    "전치사 뒤에 동명사가 온 구문은 수단과 방법을 나타내는 중요한 표현이야. "
    "그리고 뒤에 나열된 목소리 톤, 시선, 얼굴 표정, 몸짓 등이 접속사로 대등하게 병렬 연결되어 있다는 점도 놓치지 마.",

    # 4단계: 서술형 영작 대비 포인트
    "마지막으로, 내신 서술형 영작 대비 포인트야. "
    "준동사구와 접속사 병렬 구조를 활용하여 비언어적 행동의 예시를 나열하는 영작 문제가 자주 출제돼. "
    "특히 병렬 구조의 형태 일치를 신경 써서 영작 연습을 해보자."
]

# 4. 마지막 장표 멘트
CLOSING_SCRIPT = (
    "오늘 배운 삼십이 번 지문 핵심 내용을 최종 정리해보자. "
    "화자는 속마음을 말로 다 표현하지 못하기 때문에, 상대방의 비언어적 신호를 세심하게 파악하고 직접 확인하는 것이 필수적이야. "
    "오늘 짚어준 어휘와 삼단 요약을 복습하면서 완벽하게 마스터해!"
)

async def synthesize_text_with_pauses(steps: list, out_path: str, temp_dir: str):
    os.makedirs(temp_dir, exist_ok=True)
    step_files = []

    # 0.45초 문장 간 무음, 0.90초 단락 간 무음 생성
    silence_sentence = os.path.join(temp_dir, "sil_sent.mp3")
    silence_step = os.path.join(temp_dir, "sil_step.mp3")
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.45", "-c:a", "libmp3lame", silence_sentence], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.90", "-c:a", "libmp3lame", silence_step], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    concat_list = os.path.join(temp_dir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f_list:
        for step_idx, step_text in enumerate(steps):
            # 문장 단위 분할 (. ! ? 기준)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', step_text) if s.strip()]
            for sent_idx, sent in enumerate(sentences):
                sub_mp3 = os.path.join(temp_dir, f"step_{step_idx}_sent_{sent_idx}.mp3")
                comm = edge_tts.Communicate(sent, VOICE, rate="+3%", pitch="+1Hz")
                await comm.save(sub_mp3)

                ap = sub_mp3.replace("\\", "/")
                sp_sent = silence_sentence.replace("\\", "/")
                f_list.write(f"file '{ap}'\n")
                # 문장 뒤 0.45초 텀
                f_list.write(f"file '{sp_sent}'\n")

            # 단계 뒤 0.90초 텀 (단락 전환)
            sp_step = silence_step.replace("\\", "/")
            f_list.write(f"file '{sp_step}'\n")

    # 무손실 병합 후 EBU R128 표준 음량 적용
    temp_merged = os.path.join(temp_dir, "temp_merged.mp3")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", temp_merged], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    cmd_norm = [
        FFMPEG, "-y",
        "-i", temp_merged,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "libmp3lame", "-b:a", "192k",
        out_path
    ]
    subprocess.run(cmd_norm, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"  [OK] Saved: {os.path.basename(out_path)}")

async def main():
    out_dir = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\audio\q32_sentence_tts"
    temp_base = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\audio\temp_pause_build"
    os.makedirs(out_dir, exist_ok=True)

    print("=== [자연스러운 문장 간 텀 & 순수 한글 직독직해 음성 합성 시작] ===")
    
    # 0. Intro
    p0 = os.path.join(out_dir, "sentence_00_intro.mp3")
    await synthesize_text_with_pauses([INTRO_SCRIPT], p0, os.path.join(temp_base, "intro"))

    # 1. Sentence 1
    p1 = os.path.join(out_dir, "sentence_01.mp3")
    await synthesize_text_with_pauses(S1_SCRIPT_STEPS, p1, os.path.join(temp_base, "s1"))

    # 2. Sentence 2
    p2 = os.path.join(out_dir, "sentence_02.mp3")
    await synthesize_text_with_pauses(S2_SCRIPT_STEPS, p2, os.path.join(temp_base, "s2"))

    # 3. Closing
    p_last = os.path.join(out_dir, "sentence_last_closing.mp3")
    await synthesize_text_with_pauses([CLOSING_SCRIPT], p_last, os.path.join(temp_base, "closing"))

    print("\n[SUCCESS] Audio files with pauses generated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
