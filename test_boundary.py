import asyncio
from audio_synthesizer import synthesize_speech_async

async def main():
    text = "자, 먼저 이 문장의 주어부터 찾아볼까요? 주어는 our sensory systems입니다. 에스 표시하고 밑줄 칩니다! 그리고 동사는 are이네요. 브이티 두 줄 밑줄 쫙!"
    res = await synthesize_speech_async(text, "output/test_boundary.mp3")
    print("Duration:", res["total_duration"])
    word_b = [b for b in res["boundaries"] if b["type"] == "WordBoundary"]
    for wb in word_b[:15]:
        print(f"{wb['start']:5.2f}s ~ {wb['end']:5.2f}s: {wb['text']}")

if __name__ == "__main__":
    asyncio.run(main())
