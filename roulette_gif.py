"""
roulette_gif.py
Engine for rendering high-resolution, adaptive roulette wheel images for Discord.
Supports 2 to 40 players with zero text/avatar overlap and crisp typography.
"""

import io
import os
import math
import asyncio
import urllib.request
import re
from PIL import Image, ImageDraw, ImageFont

SEGMENT_COLORS = [
    (183, 28, 28), (197, 17, 98), (106, 27, 154), (69, 39, 160),
    (21, 101, 192), (2, 119, 189), (0, 131, 143), (0, 105, 92),
    (46, 125, 50), (130, 119, 23), (249, 168, 37), (239, 108, 0),
    (216, 67, 21), (121, 85, 72), (66, 66, 66), (32, 101, 158),
    (230, 81, 0), (194, 24, 91), (81, 45, 168), (0, 121, 107),
]

FONT_PATHS = [
    os.path.join("fonts", "Cairo.ttf"),
    os.path.join("fonts", "NotoSansArabic-Bold.ttf"),
    os.path.join("fonts", "Tajawal-Bold.ttf"),
]

def _get_font(size):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

def _sanitize_avatar_url(url):
    if not url:
        return None
    # Optimize: request 128px size for fast download
    if "size=" in url:
        return re.sub(r"size=\d+", "size=128", url)
    if "?" in url:
        return f"{url}&size=128"
    return f"{url}?size=128"

def _download_sync(url):
    if not url:
        return None
    try:
        req_url = _sanitize_avatar_url(url)
        req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=4) as r:
            data = r.read()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None

async def download_avatar(url):
    if not url:
        return None
    return await asyncio.to_thread(_download_sync, url)

async def download_avatars_concurrently(players):
    """Downloads missing avatars concurrently for all players."""
    async def _fetch(p):
        if "avimg" not in p or p["avimg"] is None:
            url = p.get("avatarURL") or p.get("avatar_url")
            if url:
                p["avimg"] = await download_avatar(url)

    tasks = [_fetch(p) for p in players]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

def _crop_circle(img, size):
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)
    return result

def _center(draw, cx, cy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((cx - w / 2, cy - h / 2), text, font=font, fill=fill)

def _build_frame(players, rot):
    SIZE = 520
    CX = CY = SIZE // 2
    R = 230
    n = len(players)
    if n == 0:
        return Image.new("RGB", (SIZE, SIZE), (15, 18, 26))

    img = Image.new("RGB", (SIZE, SIZE), (15, 18, 26))
    draw = ImageDraw.Draw(img, "RGBA")
    seg = 360.0 / n

    # Draw segments
    for i, p in enumerate(players):
        start = rot + i * seg
        end = start + seg
        color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
        draw.pieslice([CX - R, CY - R, CX + R, CY + R], start, end, fill=color)

    # Draw slice dividing lines
    for i in range(n):
        ang_rad = math.radians(rot + i * seg)
        lx = CX + R * math.cos(ang_rad)
        ly = CY + R * math.sin(ang_rad)
        draw.line([(CX, CY), (lx, ly)], fill=(255, 255, 255, 130), width=2)

    # Outer border ring
    draw.ellipse([CX - R, CY - R, CX + R, CY + R], outline=(255, 255, 255), width=3)

    # Adaptive sizing for avatars and font
    if n <= 4:
        av_r = 60
        font_size = 24
        r_av = R - 60
        r_num = R - 125
    elif n <= 8:
        av_r = 50
        font_size = 20
        r_av = R - 55
        r_num = R - 115
    elif n <= 16:
        av_r = 38
        font_size = 17
        r_av = R - 50
        r_num = R - 105
    elif n <= 26:
        av_r = 28
        font_size = 14
        r_av = R - 45
        r_num = R - 95
    else:
        av_r = 22
        font_size = 12
        r_av = R - 40
        r_num = R - 85

    font = _get_font(font_size)

    for i, p in enumerate(players):
        ang = math.radians(rot + i * seg + seg / 2)
        av = p.get("img") or p.get("avimg")
        avx = CX + r_av * math.cos(ang)
        avy = CY + r_av * math.sin(ang)

        if av:
            try:
                cropped = _crop_circle(av, av_r)
                ring_pad = 2
                draw.ellipse(
                    [avx - av_r / 2 - ring_pad, avy - av_r / 2 - ring_pad,
                     avx + av_r / 2 + ring_pad, avy + av_r / 2 + ring_pad],
                    outline=(255, 255, 255, 220), width=2
                )
                img.paste(cropped, (int(avx - av_r / 2), int(avy - av_r / 2)), cropped)
            except Exception:
                av = None

        if not av:
            draw.ellipse(
                [avx - av_r / 2, avy - av_r / 2, avx + av_r / 2, avy + av_r / 2],
                fill=(40, 45, 58), outline=(255, 255, 255, 160), width=1
            )

        # Draw Number
        nx = CX + r_num * math.cos(ang)
        ny = CY + r_num * math.sin(ang)
        num_str = str(p.get("number", i + 1))
        # Drop shadow for readability
        _center(draw, nx + 1, ny + 1, num_str, font, (0, 0, 0, 220))
        _center(draw, nx, ny, num_str, font, (255, 255, 255, 255))

    # Center Hub
    draw.ellipse([CX - 55, CY - 55, CX + 55, CY + 55], fill=(250, 250, 250))
    draw.ellipse([CX - 40, CY - 40, CX + 40, CY + 40], fill=(35, 40, 48))

    # Top Pointer (pointing down at 270 deg)
    draw.polygon([(CX - 24, 6), (CX + 24, 6), (CX, 52)], fill=(255, 60, 60))
    draw.polygon([(CX - 24, 6), (CX + 24, 6), (CX, 52)], outline=(0, 0, 0))

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
