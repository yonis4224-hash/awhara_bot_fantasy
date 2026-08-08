import io
import math
import asyncio
import urllib.request
from PIL import Image, ImageDraw, ImageFont

SEGMENT_COLORS = [
    (183, 28, 28), (197, 17, 98), (106, 27, 154), (69, 39, 160),
    (21, 101, 192), (2, 119, 189), (0, 131, 143), (0, 105, 92),
    (46, 125, 50), (130, 119, 23), (249, 168, 37), (239, 108, 0),
    (216, 67, 21), (121, 85, 72), (66, 66, 66), (32, 101, 158),
    (230, 81, 0), (194, 24, 91), (81, 45, 168), (0, 121, 107),
]

def _get_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

async def download_avatar(url):
    if not url:
        return None
    return await asyncio.to_thread(_download_sync, url)

def _download_sync(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None

def _crop_circle(img, size):
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img

def _center(draw, cx, cy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((cx - w / 2, cy - h / 2), text, font=font, fill=fill)

def _build_frame(players, rot):
    SIZE = 480
    CX = CY = SIZE // 2
    R = 220
    n = len(players)
    img = Image.new("RGB", (SIZE, SIZE), (18, 22, 28))
    draw = ImageDraw.Draw(img, "RGBA")
    seg = 360.0 / n
    for i, p in enumerate(players):
        start = rot + i * seg
        draw.pieslice([CX - R, CY - R, CX + R, CY + R], start, start + seg,
                      fill=SEGMENT_COLORS[i % len(SEGMENT_COLORS)])
    draw.ellipse([CX - R, CY - R, CX + R, CY + R], outline=(255, 255, 255), width=3)
    draw.ellipse([CX - 55, CY - 55, CX + 55, CY + 55], fill=(250, 250, 250))
    draw.ellipse([CX - 40, CY - 40, CX + 40, CY + 40], fill=(35, 40, 48))
    draw.polygon([(CX - 24, 6), (CX + 24, 6), (CX, 52)], fill=(255, 60, 60))
    draw.polygon([(CX - 24, 6), (CX + 24, 6), (CX, 52)], outline=(0, 0, 0))
    font = _get_font(22)
    av_r = int(max(26, min(66, (R - 75) * math.tan(math.pi / n))))
    for i, p in enumerate(players):
        ang = math.radians(rot + i * seg + seg / 2)
        av = p.get("img")
        if av:
            avx = CX + (R - 75) * math.cos(ang)
            avy = CY + (R - 75) * math.sin(ang)
            av = _crop_circle(av, av_r)
            img.paste(av, (int(avx - av_r / 2), int(avy - av_r / 2)), av)
        nx = CX + (R - 115) * math.cos(ang)
        ny = CY + (R - 115) * math.sin(ang)
        _center(draw, nx, ny, str(p["number"]), font, (255, 255, 255))
    return img

def make_image_sync(players, highlight=None):
    n = len(players)
    if n > 0:
        seg = 360.0 / n
        if highlight is not None:
            end_rot = 270 - (highlight + 0.5) * seg
        else:
            end_rot = 0
    else:
        end_rot = 0

    img = _build_frame(players, end_rot)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def make_image(players, highlight=None):
    return await asyncio.to_thread(make_image_sync, players, highlight)

# Backward compatibility alias
make_gif = make_image
