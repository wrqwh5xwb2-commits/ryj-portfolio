"""传统 OpenCV 文档扫描：候选四边形、单应变换、光照归一化、局部阈值。"""
import base64
from io import BytesIO
from time import perf_counter

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1800
MAX_PIXELS = 20_000_000


def decode(raw):
    try:
        with Image.open(BytesIO(raw)) as im:
            if im.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("仅支持 JPG、PNG、WebP 图片")
            if im.width * im.height > MAX_PIXELS:
                raise ValueError("图片超过2000万像素，请先缩小")
            im = ImageOps.exif_transpose(im)
            original_size = list(im.size)
            if min(im.size) < 64:
                raise ValueError("图片长宽都需要至少64像素")
            # 将透明区域合成白底，而非透明转黑。
            rgba = im.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            background.alpha_composite(rgba)
            background.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
            image = cv2.cvtColor(np.array(background.convert("RGB")), cv2.COLOR_RGB2BGR)
            return image, original_size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("无法解码图片，请换一张有效的图片") from error


def png(image):
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("图片编码失败")
    return "data:image/png;base64," + base64.b64encode(encoded).decode("ascii")


def ordered(points):
    p = np.asarray(points, dtype=np.float32).reshape(4, 2)
    center = p.mean(axis=0)
    p = p[np.argsort(np.arctan2(p[:, 1] - center[1], p[:, 0] - center[0]))]
    return np.roll(p, -int(np.argmin(p.sum(axis=1))), axis=0)


def validate(points, shape):
    p = np.asarray(points, dtype=np.float32)
    h, w = shape[:2]
    if p.shape != (4, 2) or not np.isfinite(p).all():
        raise ValueError("需要4个有限数值的角点")
    if (p < 0).any() or (p[:, 0] > w - 1).any() or (p[:, 1] > h - 1).any():
        raise ValueError("角点必须在图片范围内")
    if not cv2.isContourConvex(p.reshape(-1, 1, 2)):
        raise ValueError("四个角不能交叉或重合，请按左上、右上、右下、左下排列")
    if cv2.contourArea(p) < w * h * .01 or min(np.linalg.norm(p - np.roll(p, 1, axis=0), axis=1)) < 20:
        raise ValueError("选择区域太小，请重新调整四角")
    return p


def detect(image):
    h, w = image.shape[:2]
    scale = min(1, 1000 / max(h, w))
    small = cv2.resize(image, (round(w * scale), round(h * scale))) if scale < 1 else image
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 130)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    candidates = []
    for source in [closed, mask, cv2.bitwise_not(mask)]:
        contours, _ = cv2.findContours(source, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:30]:
            area = cv2.contourArea(contour)
            fraction = area / gray.size
            if not .12 < fraction < .94:
                continue
            perimeter = cv2.arcLength(contour, True)
            for epsilon in (.015, .025, .04):
                polygon = cv2.approxPolyDP(contour, epsilon * perimeter, True)
                if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                    continue
                points = ordered(polygon)
                touches = ((points[:, 0] < 3) | (points[:, 1] < 3) | (points[:, 0] > gray.shape[1]-4) | (points[:, 1] > gray.shape[0]-4)).sum()
                if touches > 1:
                    continue
                # 面积优先；不把这个排序分数包装成正确概率。
                fit = min(area, cv2.contourArea(points)) / max(area, cv2.contourArea(points), 1)
                candidates.append((fraction * fit, points / scale))
                break
    best = max(candidates, key=lambda item: item[0])[1] if candidates and float(gray.std()) > 8 else None
    if best is not None:
        best[:, 0] = np.clip(best[:, 0], 0, w - 1)
        best[:, 1] = np.clip(best[:, 1], 0, h - 1)
    return best, cv2.resize(edges, (w, h)), len(candidates)


def rectify(image, points, aspect="auto"):
    p = validate(points, image.shape)
    tl, tr, br, bl = p
    width = max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl))
    height = max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr))
    if aspect == "a4":
        width = height / np.sqrt(2)
    elif aspect == "a4-landscape":
        width = height * np.sqrt(2)
    factor = min(1, MAX_SIDE / max(width, height))
    width, height = max(20, round(width*factor)), max(20, round(height*factor))
    target = np.float32([[0,0], [width-1,0], [width-1,height-1], [0,height-1]])
    matrix = cv2.getPerspectiveTransform(p, target)
    output = cv2.warpPerspective(image, matrix, (width,height), flags=cv2.INTER_CUBIC)
    return output, matrix


def enhance(warped, block_size=35, c=12):
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    # 用较宽的局部背景估计压低光照渐变；不能恢复被遮住或失焦的文字。
    background = cv2.GaussianBlur(gray, (0,0), 25)
    normalized = cv2.divide(gray, np.maximum(background, 1), scale=235)
    enhanced = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8,8)).apply(normalized)
    binary = cv2.adaptiveThreshold(normalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c)
    return enhanced, binary


def process(image, points=None, aspect="auto", block_size=35, c=12):
    if aspect not in {"auto", "a4", "a4-landscape"}:
        raise ValueError("未知纸张比例")
    if block_size < 3 or block_size > 101 or block_size % 2 != 1 or not -10 <= c <= 30:
        raise ValueError("局部窗口需为3至101的奇数，偏移需在-10至30之间")
    start = perf_counter()
    detected, edges, count = detect(image)
    h, w = image.shape[:2]
    manual = points is not None
    if manual:
        normalized = np.asarray(points, dtype=np.float32)
        if normalized.shape != (4,2) or not np.isfinite(normalized).all() or (normalized < 0).any() or (normalized > 1).any():
            raise ValueError("归一化角点需要4组0至1之间的坐标")
        corners = validate(normalized * [w-1,h-1], image.shape)
    else:
        corners = detected
    info = {"source": png(image), "edges": png(edges), "working_size": [w,h], "candidate_count": count,
            "method": "manual" if manual else "automatic", "status": "ready" if corners is not None else "needs_manual", "warnings": []}
    if corners is None:
        info.update(corners=[[.08,.08],[.92,.08],[.92,.92],[.08,.92]], outputs={}, elapsed_ms=round((perf_counter()-start)*1000,1))
        info["warnings"] = ["未找到可靠四边形。当前四角只是调整起点，请拖到纸张边缘后点击应用。"]
        return info
    warped, matrix = rectify(image, corners, aspect)
    enhanced, binary = enhance(warped, block_size, c)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    area_ratio = cv2.contourArea(corners) / (h*w)
    if sharpness < 70:
        info["warnings"].append("清晰度指标偏低，可能失焦或缺少纹理；建议放大检查文字。")
    if area_ratio < .25:
        info["warnings"].append("纸张区域较小，建议靠近拍摄，以保留更多文字细节。")
    info.update(corners=(corners/[w-1,h-1]).tolist(), output_size=[warped.shape[1],warped.shape[0]],
                outputs={"color":png(warped), "enhanced":png(enhanced), "binary":png(binary)},
                sharpness=round(sharpness,1), area_ratio=round(area_ratio,3), homography=matrix.tolist(),
                parameters={"aspect":aspect,"block_size":block_size,"c":c}, elapsed_ms=round((perf_counter()-start)*1000,1))
    return info
