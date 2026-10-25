import math
from PIL import Image, ImageDraw, ImageFont

# 폰트 경로 (Windows 표준)
FONT_PATH_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_PATH_REG = r"C:\Windows\Fonts\malgun.ttf"

def get_font(size: int, bold: bool = False):
    p = FONT_PATH_BOLD if bold else FONT_PATH_REG
    try:
        return ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.load_default()

def smooth_polyline(pts, num_subdivisions=4):
    """Chaikin 알고리즘을 이용한 부드러운 손글씨 분필 곡선 생성"""
    cur = pts
    for _ in range(num_subdivisions):
        new_pts = []
        for i in range(len(cur) - 1):
            p0 = cur[i]
            p1 = cur[i+1]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_pts.extend([q, r])
        cur = new_pts
    return cur

# 정규화된(0.0 ~ 1.0) 필기 기호 궤적 데이터
BASE_PATHS = {
    'S': smooth_polyline([
        (0.80, 0.14), (0.65, 0.06), (0.35, 0.06), (0.20, 0.20),
        (0.24, 0.38), (0.45, 0.48), (0.68, 0.54), (0.82, 0.66),
        (0.85, 0.82), (0.70, 0.94), (0.35, 0.95), (0.18, 0.84)
    ]),
    'V': [
        (0.18, 0.12), (0.50, 0.90), (0.82, 0.12)
    ],
    'O': [
        (0.50 + 0.36 * math.cos(math.radians(a)), 0.50 + 0.42 * math.sin(math.radians(a)))
        for a in range(-90, 275, 12)
    ],
    'C': [
        (0.50 + 0.36 * math.cos(math.radians(a)), 0.50 + 0.42 * math.sin(math.radians(a)))
        for a in range(45, 315, 12)
    ],
    'triangle': [
        (0.15, 0.92), (0.50, 0.10), (0.85, 0.92), (0.15, 0.92)
    ],
    'slash': [
        (0.85, 0.08), (0.15, 0.92)
    ],
    'bracket_left': [
        (0.50 + 0.35 * math.cos(math.radians(a)), 0.50 + 0.45 * math.sin(math.radians(a)))
        for a in range(120, 245, 12)
    ],
    'bracket_right': [
        (0.50 + 0.35 * math.cos(math.radians(a)), 0.50 + 0.45 * math.sin(math.radians(a)))
        for a in range(-60, 65, 12)
    ]
}

def draw_stroke_progressive(
    draw: ImageDraw.ImageDraw,
    path_type: str,
    bbox: tuple,
    progress: float,
    color: tuple = (56, 189, 248),
    width: int = 3,
    show_stylus: bool = True
):
    """
    정규화된 경로를 실시간으로 써내려가는 필기 스트로크 렌더러
    - progress: 0.0 (시작 안함) ~ 1.0 (완성)
    - show_stylus: 필기 중일 때(progress < 1.0) 펜촉 빛(Stylus Tip) 표시
    """
    if progress <= 0.0:
        return None

    path_points = BASE_PATHS.get(path_type)
    if not path_points:
        return None

    bx1, by1, bx2, by2 = bbox
    bw = bx2 - bx1
    bh = by2 - by1

    # 절대 좌표 변환
    pts = [(bx1 + px * bw, by1 + py * bh) for px, py in path_points]

    lengths = []
    total_len = 0.0
    for i in range(len(pts) - 1):
        dist = math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1])
        lengths.append(dist)
        total_len += dist

    if total_len == 0:
        return None

    target_dist = total_len * min(1.0, progress)
    accum = 0.0
    current_pts = [pts[0]]
    tip_pt = pts[0]

    for i in range(len(pts) - 1):
        seg_len = lengths[i]
        if accum + seg_len < target_dist:
            current_pts.append(pts[i+1])
            accum += seg_len
            tip_pt = pts[i+1]
        else:
            remain = target_dist - accum
            ratio = remain / seg_len if seg_len > 0 else 0
            interp_x = pts[i][0] + (pts[i+1][0] - pts[i][0]) * ratio
            interp_y = pts[i][1] + (pts[i+1][1] - pts[i][1]) * ratio
            tip_pt = (interp_x, interp_y)
            current_pts.append(tip_pt)
            break

    # 선 긋기
    if len(current_pts) >= 2:
        draw.line(current_pts, fill=color, width=width, joint='curve')

    # 필기 진행 중일 때만 분필/스타일러스 발광 펜촉 표시
    if show_stylus and progress < 0.98:
        tx, ty = int(tip_pt[0]), int(tip_pt[1])
        # 외곽 네온 글로우
        draw.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], fill=(color[0], color[1], color[2]))
        # 중심 밝은 화이트 코어
        draw.ellipse([tx - 2, ty - 2, tx + 2, ty + 2], fill=(255, 255, 255))

    return tip_pt

def draw_underline_progressive(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y: int,
    x2: int,
    progress: float,
    color: tuple = (56, 189, 248),
    double: bool = False,
    width: int = 3,
    show_stylus: bool = True
):
    """단어/구문 아래로 쫙 그어지는 실시간 밑줄 애니메이션"""
    if progress <= 0.0:
        return

    cur_x = x1 + (x2 - x1) * min(1.0, progress)

    # 1줄 밑줄
    draw.line([(x1, y), (cur_x, y)], fill=color, width=width)
    if double:
        # 본동사 2줄 밑줄
        draw.line([(x1, y + 6), (cur_x, y + 6)], fill=color, width=width)

    if show_stylus and progress < 0.98:
        tx, ty = int(cur_x), int(y + (3 if double else 0))
        draw.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], fill=(color[0], color[1], color[2]))
        draw.ellipse([tx - 2, ty - 2, tx + 2, ty + 2], fill=(255, 255, 255))

def draw_highlighter_progressive(
    draw: ImageDraw.ImageDraw,
    rect: list,
    progress: float,
    color: tuple = (234, 179, 8),
    alpha: int = 70
):
    """단어 위로 칠해지는 실시간 노란색 형광펜 하이라이트 효과"""
    if progress <= 0.0:
        return

    x1, y1, x2, y2 = rect
    cur_x = x1 + (x2 - x1) * min(1.0, progress)

    # 반투명 칠판 오버레이
    hl_color = (95, 85, 25) # 다크 차콜 칠판(#16181F) 위에서 산뜻하게 발색되는 형광펜 색상
    draw.rectangle([x1, y1, cur_x, y2], fill=hl_color)
