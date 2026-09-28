"""
Modern Profile Card Graphics Generator (profile_gfx.py)
Generates elegant, well-organized luxury profile cards (Gold, Silver, Purple, Blue)
with clean layout, glass-morphism effects, and full Arabic & English text support.
"""
import io
import math
import random
import asyncio
import unicodedata
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display


def is_arabic_char(ch):
    code = ord(ch)
    return (
        0x0600 <= code <= 0x06FF or
        0x0750 <= code <= 0x077F or
        0x08A0 <= code <= 0x08FF or
        0xFB50 <= code <= 0xFDFF or
        0xFE70 <= code <= 0xFEFF
    )

def is_emoji_or_symbol_box(ch):
    code = ord(ch)
    return (
        0x1F300 <= code <= 0x1FAFF or
        0x2600 <= code <= 0x27BF or
        0xFE00 <= code <= 0xFE0F
    )

def clean_and_format_name(text: str) -> str:
    if not text:
        return "Member"
    text = unicodedata.normalize('NFKD', str(text))
    cleaned = "".join(c for c in text if not is_emoji_or_symbol_box(c)).strip()
    if not cleaned:
        return "Member"
    has_ar = any(is_arabic_char(c) for c in cleaned)
    if has_ar:
        try:
            cfg = {'delete_harakat': False, 'support_ligatures': True, 'support_zwj': True}
            reshaper = arabic_reshaper.ArabicReshaper(configuration=cfg)
            return get_display(reshaper.reshape(cleaned))
        except Exception:
            return cleaned
    return cleaned

def ar_phrase(text: str) -> str:
    if not text:
        return ""
    try:
        cfg = {'delete_harakat': False, 'support_ligatures': True, 'support_zwj': True}
        reshaper = arabic_reshaper.ArabicReshaper(configuration=cfg)
        return get_display(reshaper.reshape(str(text).strip()))
    except Exception:
        return str(text)

def get_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/ARIALUNI.TTF",
        "C:/Windows/Fonts/tahoma.ttf"
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _download_avatar_sync(url):
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = r.read()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None

async def download_avatar_async(url):
    return await asyncio.to_thread(_download_avatar_sync, url)

def make_gradient(w, h, top_col, bot_col):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top_col[0] * (1 - ratio) + bot_col[0] * ratio)
        g = int(top_col[1] * (1 - ratio) + bot_col[1] * ratio)
        b = int(top_col[2] * (1 - ratio) + bot_col[2] * ratio)
        d.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return img

def add_grain_layer(w, h, accent_col, seed=42):
    random.seed(seed)
    grain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for _ in range(250):
        gx = random.randint(0, w - 1)
        gy = random.randint(0, h - 1)
        glen = random.randint(5, 25)
        col = (*accent_col[:3], random.randint(8, 25))
        if random.random() > 0.5:
            gd.line([(gx, gy), (gx + glen, gy)], fill=col, width=1)
        else:
            gd.line([(gx, gy), (gx, gy + glen)], fill=col, width=1)
    grain = grain.filter(ImageFilter.GaussianBlur(radius=1.0))
    return grain

def draw_rounded_panel(w, h, bg_rgba, border_color, radius=22, border_width=2):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill_col = (*bg_rgba, 180)
    d.rounded_rectangle([0, 0, w, h], radius=radius, fill=fill_col, outline=border_color, width=border_width)
    for i in range(3):
        alpha = 50 - i * 12
        r = radius - i
        if r > 0:
            d.rounded_rectangle([i + 1, i + 1, w - i - 1, h - i - 1], radius=r, outline=(*border_color[:3], alpha), width=1)
    return img

CARD_CONFIGS = {
    "gold": {
        "bg_top": (210, 170, 60),
        "bg_bottom": (140, 90, 10),
        "accent": (255, 215, 80),
        "card_bg": (255, 250, 235),
        "card_border": (255, 215, 80),
        "title_color": (180, 120, 10),
        "sub_color": (200, 150, 30),
        "info_title": (120, 80, 5),
        "info_sub": (150, 110, 30),
        "stat_label": (140, 95, 15),
        "stat_value": (90, 55, 5),
        "seal_outer": (255, 215, 80),
        "seal_inner": (200, 150, 30),
        "seal_text": (100, 70, 5),
        "tier_num": "1",
        "title_en": "GOLD",
        "title_ar": "الذهبي",
        "sub_en": "PREMIUM",
        "sub_ar": "المميز",
    },
    "silver": {
        "bg_top": (190, 200, 210),
        "bg_bottom": (110, 120, 130),
        "accent": (200, 210, 220),
        "card_bg": (250, 252, 255),
        "card_border": (200, 210, 220),
        "title_color": (60, 70, 85),
        "sub_color": (90, 100, 115),
        "info_title": (50, 60, 75),
        "info_sub": (80, 90, 105),
        "stat_label": (95, 105, 120),
        "stat_value": (55, 65, 80),
        "seal_outer": (200, 210, 220),
        "seal_inner": (140, 150, 165),
        "seal_text": (45, 55, 70),
        "tier_num": "2",
        "title_en": "SILVER",
        "title_ar": "الفضي",
        "sub_en": "ELITE",
        "sub_ar": "النخبة",
    },
    "purple": {
        "bg_top": (65, 20, 95),
        "bg_bottom": (30, 8, 50),
        "accent": (170, 80, 255),
        "card_bg": (255, 245, 255),
        "card_border": (170, 80, 255),
        "title_color": (200, 140, 255),
        "sub_color": (170, 100, 240),
        "info_title": (140, 80, 190),
        "info_sub": (160, 110, 210),
        "stat_label": (150, 100, 180),
        "stat_value": (110, 60, 150),
        "seal_outer": (180, 70, 255),
        "seal_inner": (100, 20, 160),
        "seal_text": (230, 200, 255),
        "tier_num": "3",
        "title_en": "PURPLE",
        "title_ar": "البنفسجي",
        "sub_en": "ROYAL",
        "sub_ar": "الملكية",
    },
    "blue": {
        "bg_top": (10, 55, 120),
        "bg_bottom": (5, 15, 50),
        "accent": (0, 180, 255),
        "card_bg": (250, 253, 255),
        "card_border": (0, 180, 255),
        "title_color": (0, 170, 240),
        "sub_color": (80, 170, 230),
        "info_title": (30, 90, 160),
        "info_sub": (60, 130, 190),
        "stat_label": (50, 110, 165),
        "stat_value": (20, 70, 130),
        "seal_outer": (0, 180, 255),
        "seal_inner": (0, 80, 170),
        "seal_text": (190, 230, 255),
        "tier_num": "4",
        "title_en": "BLUE",
        "title_ar": "الازرق",
        "sub_en": "CONTRIBUTOR",
        "sub_ar": "المساهم",
    },
}

def render_profile_card(avatar_img, user_data, is_admin=False):
    """
    Renders an elegant, well-organized luxury profile card.
    """
    W, H = 540, 900
    theme_key = user_data.get("theme", "blue")
    if theme_key not in CARD_CONFIGS:
        theme_key = "blue"
    cfg = CARD_CONFIGS[theme_key]

    # Background gradient
    bg = make_gradient(W, H, cfg["bg_top"], cfg["bg_bottom"])
    grain = add_grain_layer(W, H, cfg["accent"])
    bg.alpha_composite(grain)

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    corner_radius = 30
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, H], radius=corner_radius, fill=255)
    card.paste(bg, (0, 0), mask)
    draw = ImageDraw.Draw(card)

    # Inner glass panel
    panel_img = draw_rounded_panel(W - 30, H - 40, cfg["card_bg"], cfg["card_border"], radius=22, border_width=2)
    card.alpha_composite(panel_img, (15, 20))

    # Top header bar
    header_y = 25
    icon_x, icon_y = 30, header_y
    icon_size = 24
    draw.rounded_rectangle([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size], radius=6, fill=cfg["accent"])
    draw.ellipse([icon_x + 5, icon_y + 6, icon_x + 10, icon_y + 14], fill=cfg["card_bg"])
    draw.ellipse([icon_x + 15, icon_y + 6, icon_x + 20, icon_y + 14], fill=cfg["card_bg"])

    # Tier badge top right
    badge_x = W - 85
    badge_y = header_y - 5
    badge_w, badge_h = 75, 28
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=8, fill=cfg["accent"])
    f_badge = get_font(13, bold=True)
    tier_label = f"#{cfg['tier_num']}"
    bbox = draw.textbbox((0, 0), tier_label, font=f_badge)
    tw = bbox[2] - bbox[0]
    draw.text((badge_x + badge_w // 2 - tw // 2, badge_y + 5), tier_label, fill=cfg["seal_text"], font=f_badge)

    # Avatar section
    av_cy = 210
    av_cx = W // 2
    av_r = 80

    # Glow ring
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_d = ImageDraw.Draw(glow_layer)
    for i in range(8, 0, -1):
        alpha = int(60 * (i / 8))
        glow_d.ellipse([av_cx - av_r - i, av_cy - av_r - i, av_cx + av_r + i, av_cy + av_r + i],
                       outline=(*cfg["accent"][:3], alpha), width=2)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=3))
    card.alpha_composite(glow_layer)

    # Frame rings
    for i in range(4):
        r = av_r + 6 - i * 2
        alpha = 180 - i * 30
        draw.ellipse([av_cx - r, av_cy - r, av_cx + r, av_cy + r],
                     outline=(*cfg["accent"][:3], alpha), width=3)

    # Avatar image or placeholder
    if avatar_img:
        av_dia = av_r * 2
        av_resized = avatar_img.resize((av_dia, av_dia), Image.LANCZOS).convert("RGBA")
        av_mask = Image.new("L", (av_dia, av_dia), 0)
        ImageDraw.Draw(av_mask).ellipse([0, 0, av_dia, av_dia], fill=255)
        card.paste(av_resized, (av_cx - av_r, av_cy - av_r), av_mask)
    else:
        draw.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(40, 45, 60))
        f_ph = get_font(36, bold=True)
        text = (user_data.get("display_name") or "M")[:1].upper()
        bbox = draw.textbbox((0, 0), text, font=f_ph)
        tw = bbox[2] - bbox[0]
        draw.text((av_cx - tw // 2, av_cy - 18), text, fill=(200, 200, 210), font=f_ph)

    # Name section
    name_y = 320
    f_name = get_font(30, bold=True)
    name_display = clean_and_format_name(user_data.get("display_name") or user_data.get("username") or "Member")
    bbox = draw.textbbox((0, 0), name_display[:22], font=f_name)
    tw = bbox[2] - bbox[0]
    draw.text((av_cx - tw // 2, name_y), name_display[:22], fill=cfg["title_color"], font=f_name)

    # Title below name
    title_y = name_y + 40
    f_title = get_font(18, bold=True)
    title_text = f"{cfg['title_ar']} | {cfg['title_en']}"
    bbox = draw.textbbox((0, 0), title_text, font=f_title)
    tw = bbox[2] - bbox[0]
    draw.text((av_cx - tw // 2, title_y), title_text, fill=cfg["sub_color"], font=f_title)

    # Decorative line
    line_y = title_y + 35
    line_w = 200
    lx1 = av_cx - line_w // 2
    lx2 = av_cx + line_w // 2
    draw.line([(lx1, line_y), (lx2, line_y)], fill=(*cfg["accent"][:3], 80), width=2)

    # Stats section - two columns
    stats_y = line_y + 55
    f_label = get_font(14)
    f_value = get_font(18, bold=True)

    total_msgs = user_data.get("total_messages", 0)
    xp = user_data.get("xp", 0)
    rank = user_data.get("rank", 1)
    level = user_data.get("level", 1)

    s1x = 35
    s2x = W - 35 - 160

    # Row 1
    draw.text((s1x, stats_y), "Msgs", fill=cfg["stat_label"], font=f_label)
    draw.text((s1x, stats_y + 18), f"{total_msgs:,}", fill=cfg["stat_value"], font=f_value)
    draw.text((s2x, stats_y), "XP", fill=cfg["stat_label"], font=f_label)
    draw.text((s2x, stats_y + 18), f"{xp:,}", fill=cfg["stat_value"], font=f_value)

    # Row 2
    stats_y2 = stats_y + 55
    draw.text((s1x, stats_y2), "Rank", fill=cfg["stat_label"], font=f_label)
    draw.text((s1x, stats_y2 + 18), f"#{rank}", fill=cfg["stat_value"], font=f_value)
    draw.text((s2x, stats_y2), "Level", fill=cfg["stat_label"], font=f_label)
    draw.text((s2x, stats_y2 + 18), str(level), fill=cfg["stat_value"], font=f_value)

    # Arabic labels
    arabic_y = stats_y2 + 35
    draw.text((s1x, arabic_y), ar_phrase("الرسائل"), fill=cfg["info_sub"], font=get_font(12))
    draw.text((s2x, arabic_y), ar_phrase("نقاط"), fill=cfg["info_sub"], font=get_font(12))

    # Bottom footer
    footer_y = H - 40
    dec_y = footer_y - 15
    draw.line([(35, dec_y), (W - 35, dec_y)], fill=(*cfg["accent"][:3], 40), width=1)
    f_footer = get_font(13, bold=True)
    status_text = "Active" if not is_admin else "Admin"
    bbox = draw.textbbox((0, 0), status_text, font=f_footer)
    tw = bbox[2] - bbox[0]
    status_emoji = "🟢 " if not is_admin else "🛡️ "
    draw.text((av_cx - tw // 2, footer_y), status_emoji + status_text,
              fill=(*cfg["accent"][:3], 200), font=f_footer)

    # Save
    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf
