import os
import sys
import math
import subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SOURCE_AVATAR_PATH = r"C:\Users\stone\Downloads\Gemini_Generated_Image_vfue9qvfue9qvfue.png"

def create_base_avatar(size: int = 280) -> Image.Image:
    """
    원본 강사 일러스트에서 얼굴과 상반신을 정밀 크롭
    - 원본 해상도: 1856 x 2272
    - 얼굴 중심: (928, 800)
    - 280x280 정방형 아바타 생성 (정확한 눈, 코, 입 해부학적 위치 고정)
    """
    if not os.path.exists(SOURCE_AVATAR_PATH):
        raise FileNotFoundError(f"강사 이미지를 찾을 수 없습니다: {SOURCE_AVATAR_PATH}")

    im = Image.open(SOURCE_AVATAR_PATH).convert("RGBA")
    w, h = im.size

    # 정밀 두경부(Head & Shoulders) 크롭
    crop_w, crop_h = 1400, 1400
    crop_x1 = max(0, 928 - crop_w // 2)
    crop_y1 = max(0, 850 - int(crop_h * 0.45))
    cropped = im.crop((crop_x1, crop_y1, crop_x1 + crop_w, crop_y1 + crop_h))

    resized = cropped.resize((size, size), Image.Resampling.LANCZOS)
    return resized

def generate_mouth_variants(base_avatar: Image.Image) -> list:
    """
    280x280 베이스 아바타의 실제 입 위치(x: 105..172, y: 105..135, 중심 139, 120)에 대해
    자연스러운 발화(Lip-sync) 입모양 변형(Warping) 4단계를 생성합니다.
    - 0: 자연스러운 미소 (기본)
    - 1: 약한 개폐 (모음 이/에)
    - 2: 중간 개폐 (모음 아/어)
    - 3: 원형 오므림 (모음 오/우)
    """
    # 입 영역 크롭 (67 x 30)
    mouth_crop = base_avatar.crop((105, 105, 172, 135))
    mouth_np = cv2.cvtColor(np.array(mouth_crop), cv2.COLOR_RGBA2BGRA)
    h, w = mouth_np.shape[:2]

    variants = [mouth_crop] # 0번은 기본 원본

    # 1. 약한 개폐 (shift=2)
    # 2. 중간 개폐 (shift=4)
    # 3. 큰 개폐 (shift=6)
    for shift in [2, 4, 5]:
        map_x = np.zeros((h, w), dtype=np.float32)
        map_y = np.zeros((h, w), dtype=np.float32)

        for y in range(h):
            for x in range(w):
                nx = (x - 34) / 18.0
                if y >= 14:
                    weight_y = min(1.0, (y - 14) / 3.0) * max(0.0, 1.0 - (y - 18) / 10.0)
                    weight_x = np.exp(-nx**2 * 1.8)
                    dy = -shift * weight_x * weight_y
                else:
                    dy = 0.0

                map_x[y, x] = x
                map_y[y, x] = y + dy

        warped = cv2.remap(mouth_np, map_x, map_y, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        
        # 입술 안쪽 자연스러운 구강 음영 (어두운 장미빛)과 윗니 보존
        pts = np.array([
            [22, 14], [46, 14], 
            [44, 14 + shift], [24, 14 + shift]
        ], np.int32)
        cv2.fillPoly(warped, [pts], (45, 20, 28, 255))
        cv2.line(warped, (23, 14), (45, 14), (240, 240, 240, 255), 1)

        warped_pil = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGRA2RGBA))
        variants.append(warped_pil)

    return variants

def generate_talking_avatar_frames(num_frames: int = 36, size: int = 280) -> list:
    """
    완벽한 인체 해부학적 위치 기반 버츄얼 휴먼 강사 립싱크 & 모션 생성
    - 정확한 입 위치(중심 139, 120)에서의 자연스러운 발화 개폐
    - 자연스러운 호흡 모션 및 미세 고개 끄덕임(±0.8도)
    - 칠판 다크 배경(#16181F) 안티앨리어싱 원형 마스킹
    - 네온 시안 프리미엄 링 테두리 + "AI Grace 쌤" 명찰
    """
    base_img = create_base_avatar(size)
    mouth_variants = generate_mouth_variants(base_img)

    frames = []

    # 36프레임 (12fps 기준 3초 주기 끊김없는 루프)
    # 발화 패턴 시퀀스 (음절 강약 시뮬레이션)
    mouth_pattern = [0, 1, 2, 3, 2, 1, 0, 1, 3, 2, 1, 0,
                     1, 2, 2, 3, 1, 0, 1, 2, 3, 2, 1, 0,
                     0, 1, 2, 3, 2, 1, 1, 2, 1, 0, 0, 0]

    for i in range(num_frames):
        t = i / float(num_frames)
        frame = base_img.copy()

        # 1. 입모양 합성 (정확한 위치 105, 105에 장착)
        m_idx = mouth_pattern[i % len(mouth_pattern)]
        mouth_frame = mouth_variants[m_idx]
        frame.paste(mouth_frame, (105, 105))

        # 2. 미세 고개 끄덕임 (자연스러운 발화 제스처, ±0.7도)
        tilt = math.sin(t * math.pi * 2) * 0.7
        # 미세 상하 호흡 바운스 (±1.2 픽셀)
        bounce_y = int(math.sin(t * math.pi * 4) * 1.5)

        rotated = frame.rotate(tilt, resample=Image.Resampling.BICUBIC, center=(140, 240))

        # 3. 칠판 배경(#16181F = 22, 24, 31) 결합 원형 마스크
        final_frame = Image.new("RGB", (size, size), (22, 24, 31))

        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([8, 8, size - 8, size - 8], fill=255)

        final_frame.paste(rotated, (0, bounce_y), mask)

        # 4. 프리미엄 네온 시안 테두리 링
        f_draw = ImageDraw.Draw(final_frame)
        f_draw.ellipse([8, 8, size - 8, size - 8], outline=(56, 189, 248), width=4)

        # 5. 하단 명찰 배지
        bx1, by1 = int(size * 0.18), size - 26
        bx2, by2 = int(size * 0.82), size - 4
        f_draw.rounded_rectangle([bx1, by1, bx2, by2], radius=10, fill=(15, 23, 42), outline=(56, 189, 248), width=1)
        try:
            b_font = ImageFont.truetype(r"C:\Windows\Fonts\malgunbd.ttf", 13)
        except Exception:
            b_font = ImageFont.load_default()
        b_text = "AI Grace 쌤"
        tb = f_draw.textbbox((0, 0), b_text, font=b_font)
        tw = tb[2] - tb[0]
        f_draw.text(((size - tw) // 2, size - 23), b_text, fill=(241, 245, 249), font=b_font)

        frames.append(final_frame)

    return frames

def build_avatar_video_loop(output_path: str, size: int = 280, fps: int = 12) -> str:
    """
    버츄얼 인간 립싱크 루프 비디오(MP4)를 생성하여 반환합니다.
    """
    temp_dir = os.path.join(os.path.dirname(output_path), "avatar_frames_temp")
    os.makedirs(temp_dir, exist_ok=True)

    frames = generate_talking_avatar_frames(num_frames=36, size=size)
    for i, f in enumerate(frames):
        f.save(os.path.join(temp_dir, f"frame_{i:02d}.png"))

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-framerate", str(fps),
        "-i", os.path.join(temp_dir, "frame_%02d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path

if __name__ == "__main__":
    out_video = r"c:\Users\stone\Desktop\workspace\ai_lecture_maker\output\avatar_talking_loop.mp4"
    build_avatar_video_loop(out_video)
    print("Avatar video loop created successfully:", out_video)
