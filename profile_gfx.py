"""
Modern Profile Card Graphics Generator (profile_gfx.py)
Generates high-resolution, luxury brushed-metal VIP cards (Gold, Silver, Purple, Blue)
inspired by modern Discord VIP membership passes, with full Arabic & decorated unicode text support.
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
    # Filter out emoji ranges that render as empty boxes in standard text fonts
    return (
        0x1F300 <= code <= 0x1FAFF or  # Miscellaneous Symbols and Pictographs, Emoticons, Transport, Supplemental
        0x2600 <= code <= 0x27BF or    # Misc symbols, Dingbats
        0xFE00 <= code <= 0xFE0F       # Variation Selectors
    )

def clean_and_format_name(text: str) -> str:
    """
    Normalizes decorated unicode characters (like 𝓕 -> F, 𝕶 -> K)
    while preserving Arabic letters, numbers, spaces, and punctuation.
    """
    if not text:
        return "Member"
    # 1. Normalize fancy mathematical/alphabetical unicode
    text = unicodedata.normalize('NFKD', str(text))
    # 2. Filter out emoji/dingbat characters that cause empty boxes
    cleaned = "".join(c for c in text if not is_emoji_or_symbol_box(c)).strip()
    if not cleaned:
        return "Member"
    
    # 3. Reshape and apply BiDi if Arabic is present
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
    """Properly reshapes pure Arabic phrases for centered/RTL rendering."""
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

CARD_CONFIGS = {
    "gold": {
        "bg_top": (240, 198, 85),
        "bg_bottom": (155, 105, 18),
        "grain_light": (255, 230, 140, 30),
        "grain_dark": (110, 75, 10, 30),
        "border_outer": (255, 225, 115),
        "border_inner": (135, 90, 15),
        "glow": None,
        "medallion_ring": (255, 225, 120),
        "medallion_bevel": (120, 85, 20),
        "title_color": (95, 62, 12),
        "sub_color": (125, 88, 22),
        "desc_color": (145, 105, 30),
        "info_title": (85, 55, 10),
        "info_sub": (110, 80, 25),
        "seal_outer": (255, 230, 130),
        "seal_inner": (180, 130, 35),
        "seal_text": (75, 48, 8),
        "tier_num": "1",
        "title_en": "GOLD",
        "title_ar": "الذهبي",
        "sub_en": "PREMIUM ACCESS",
        "sub_ar": "الوصول المميز",
    },
    "silver": {
        "bg_top": (230, 235, 240),
        "bg_bottom": (155, 165, 175),
        "grain_light": (255, 255, 255, 35),
        "grain_dark": (110, 120, 130, 30),
        "border_outer": (250, 252, 255),
        "border_inner": (130, 140, 150),
        "glow": None,
        "medallion_ring": (245, 248, 252),
        "medallion_bevel": (120, 130, 140),
        "title_color": (60, 70, 80),
        "sub_color": (85, 95, 105),
        "desc_color": (105, 115, 125),
        "info_title": (55, 65, 75),
        "info_sub": (80, 90, 100),
        "seal_outer": (245, 248, 252),
        "seal_inner": (160, 170, 180),
        "seal_text": (50, 60, 70),
        "tier_num": "2",
        "title_en": "SILVER",
        "title_ar": "الفضي",
        "sub_en": "ELITE MEMBER",
        "sub_ar": "عضو نخبة",
    },
    "purple": {
        "bg_top": (42, 14, 62),
        "bg_bottom": (15, 6, 24),
        "grain_light": (180, 90, 255, 25),
        "grain_dark": (0, 0, 0, 45),
        "border_outer": (195, 75, 255),
        "border_inner": (100, 30, 140),
        "glow": (180, 60, 255, 180),
        "medallion_ring": (220, 110, 255),
        "medallion_bevel": (80, 20, 120),
        "title_color": (230, 170, 255),
        "sub_color": (195, 130, 245),
        "desc_color": (170, 110, 220),
        "info_title": (220, 160, 255),
        "info_sub": (160, 120, 195),
        "seal_outer": (210, 95, 255),
        "seal_inner": (65, 20, 95),
        "seal_text": (245, 210, 255),
        "tier_num": "3",
        "title_en": "PURPLE",
        "title_ar": "البنفسجي",
        "sub_en": "ROYAL SUBSCRIBER",
        "sub_ar": "مشترك ملكي",
    },
    "blue": {
        "bg_top": (8, 48, 105),
        "bg_bottom": (4, 16, 40),
        "grain_light": (0, 170, 255, 25),
        "grain_dark": (0, 0, 0, 45),
        "border_outer": (0, 180, 255),
        "border_inner": (0, 80, 140),
        "glow": (0, 160, 255, 180),
        "medallion_ring": (0, 200, 255),
        "medallion_bevel": (0, 60, 120),
        "title_color": (0, 200, 255),
        "sub_color": (120, 210, 255),
        "desc_color": (90, 180, 235),
        "info_title": (140, 220, 255),
        "info_sub": (90, 160, 210),
        "seal_outer": (0, 200, 255),
        "seal_inner": (5, 45, 95),
        "seal_text": (200, 240, 255),
        "tier_num": "4",
        "title_en": "BLUE",
        "title_ar": "الازرق",
        "sub_en": "SPECIAL CONTRIBUTOR",
        "sub_ar": "مساهم خاص",
    },
}

def draw_brushed_metal(w, h, top_col, bot_col, light_col, dark_col):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        ratio = y / h
        r = int(top_col[0] * (1 - ratio) + bot_col[0] * ratio)
        g = int(top_col[1] * (1 - ratio) + bot_col[1] * ratio)
        b = int(top_col[2] * (1 - ratio) + bot_col[2] * ratio)
        d.line([(0, y), (w, y)], fill=(r, g, b, 255))
    
    random.seed(42)
    grain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for _ in range(400):
        gx = random.randint(0, w - 1)
        gy = random.randint(0, h // 2)
        glen = random.randint(h // 3, h)
        col = light_col if random.random() > 0.45 else dark_col
        gd.line([(gx, gy), (gx, min(h, gy + glen))], fill=col, width=random.choice([1, 2]))
    
    grain = grain.filter(ImageFilter.GaussianBlur(radius=0.7))
    img.alpha_composite(grain)
    return img

def render_profile_card(avatar_img, user_data, is_admin=False):
    """
    Renders a vertical luxury brushed-metal VIP card (matching the reference design).
    """
    W, H = 540, 900
    theme_key = user_data.get("theme", "blue")
    if theme_key not in CARD_CONFIGS:
        theme_key = "blue"
    cfg = CARD_CONFIGS[theme_key]

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bg = draw_brushed_metal(W, H, cfg["bg_top"], cfg["bg_bottom"], cfg["grain_light"], cfg["grain_dark"])
    
    corner_radius = 42
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, H], radius=corner_radius, fill=255)
    card.paste(bg, (0, 0), mask)
    
    draw = ImageDraw.Draw(card)

    # 1. Outer Glow / Border
    if cfg.get("glow"):
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        for offset, alpha in [(4, 70), (3, 110), (2, 160), (1, 220)]:
            col = (*cfg["glow"][:3], alpha)
            gd.rounded_rectangle([offset, offset, W - offset, H - offset], radius=corner_radius, outline=col, width=2)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=1.5))
        card.alpha_composite(glow_layer)
    else:
        draw.rounded_rectangle([2, 2, W - 2, H - 2], radius=corner_radius, outline=cfg["border_outer"], width=3)
        draw.rounded_rectangle([5, 5, W - 5, H - 5], radius=corner_radius - 3, outline=cfg["border_inner"], width=1)

    # 2. Top Left Discord Icon
    disco_x, disco_y = 38, 38
    disco_w, disco_h = 36, 26
    draw.rounded_rectangle([disco_x, disco_y, disco_x + disco_w, disco_y + disco_h], radius=10, fill=(*cfg["title_color"], 220))
    eye_col = cfg["bg_top"]
    draw.ellipse([disco_x + 8, disco_y + 8, disco_x + 15, disco_y + 17], fill=eye_col)
    draw.ellipse([disco_x + 21, disco_y + 8, disco_x + 28, disco_y + 17], fill=eye_col)

    # 3. Center 3D Medallion (Avatar Frame)
    med_cx = W // 2
    med_cy = 230
    med_r = 95
    av_r = 75

    ring_thick = med_r - av_r
    for r_idx in range(ring_thick):
        curr_r = av_r + r_idx
        frac = r_idx / ring_thick
        ring_col = (
            int(cfg["medallion_bevel"][0] * (1 - frac) + cfg["medallion_ring"][0] * frac),
            int(cfg["medallion_bevel"][1] * (1 - frac) + cfg["medallion_ring"][1] * frac),
            int(cfg["medallion_bevel"][2] * (1 - frac) + cfg["medallion_ring"][2] * frac),
        )
        draw.ellipse([med_cx - curr_r, med_cy - curr_r, med_cx + curr_r, med_cy + curr_r], outline=ring_col, width=2)

    if cfg.get("glow"):
        for glow_r in range(med_r, med_r + 8):
            alpha = int(120 * (1 - (glow_r - med_r) / 8))
            draw.ellipse([med_cx - glow_r, med_cy - glow_r, med_cx + glow_r, med_cy + glow_r], outline=(*cfg["glow"][:3], alpha), width=1)

    draw.ellipse([med_cx - av_r - 2, med_cy - av_r - 2, med_cx + av_r + 2, med_cy + av_r + 2], outline=(0, 0, 0, 140), width=3)

    if avatar_img:
        av_dia = av_r * 2
        av_resized = avatar_img.resize((av_dia, av_dia), Image.LANCZOS).convert("RGBA")
        av_mask = Image.new("L", (av_dia, av_dia), 0)
        ImageDraw.Draw(av_mask).ellipse([0, 0, av_dia, av_dia], fill=255)
        card.paste(av_resized, (med_cx - av_r, med_cy - av_r), av_mask)
    else:
        draw.ellipse([med_cx - av_r, med_cy - av_r, med_cx + av_r, med_cy + av_r], fill=(30, 35, 45))

    # 4. Center Typography (Matching Image Exactly)
    f_title_en = get_font(42, bold=True)
    f_title_ar = get_font(34, bold=True)
    f_sub_en = get_font(18, bold=True)
    f_sub_ar = get_font(24, bold=True)

    text_y = 360
    
    t_en = cfg["title_en"]
    bbox = draw.textbbox((0, 0), t_en, font=f_title_en)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, text_y), t_en, fill=cfg["title_color"], font=f_title_en)
    text_y += 48

    t_ar = ar_phrase(cfg["title_ar"])
    bbox = draw.textbbox((0, 0), t_ar, font=f_title_ar)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, text_y), t_ar, fill=cfg["title_color"], font=f_title_ar)
    text_y += 58

    s_en = cfg["sub_en"]
    bbox = draw.textbbox((0, 0), s_en, font=f_sub_en)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, text_y), s_en, fill=cfg["sub_color"], font=f_sub_en)
    text_y += 34

    s_ar = ar_phrase(cfg["sub_ar"])
    bbox = draw.textbbox((0, 0), s_ar, font=f_sub_ar)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, text_y), s_ar, fill=cfg["desc_color"], font=f_sub_ar)
    text_y += 65

    line_w = 360
    lx1 = (W - line_w) // 2
    lx2 = lx1 + line_w
    draw.line([(lx1, text_y), (lx2, text_y)], fill=(*cfg["sub_color"][:3], 90), width=1)

    # 5. Bottom Details & 3D Tier Seal
    bot_y = 705
    info_x = 42

    f_name = get_font(24, bold=True)
    f_stat = get_font(17, bold=True)
    f_stat_sub = get_font(15)

    display_name = str(user_data.get("display_name") or user_data.get("username") or "Member")
    username = str(user_data.get("username", ""))
    total_msgs = user_data.get("total_messages", 0)
    xp = user_data.get("xp", 0)
    rank = user_data.get("rank", 1)
    level = user_data.get("level", 1)

    # Line 1: User display name with full Arabic & decorated text support!
    name_display = clean_and_format_name(display_name[:24])
    draw.text((info_x, bot_y), name_display, fill=cfg["info_title"], font=f_name)

    # Line 2: @username / handle
    user_handle = f"@{username}" if username else f"ID: {user_data.get('user_id', '')}"
    draw.text((info_x, bot_y + 32), user_handle[:25], fill=cfg["info_sub"], font=f_stat_sub)

    # Line 3: Points & Messages
    stat_pts = ar_phrase("النقاط") + f": {xp:,} XP  •  " + ar_phrase("الرسائل") + f": {total_msgs:,}"
    draw.text((info_x, bot_y + 64), stat_pts, fill=cfg["info_sub"], font=f_stat)

    # Line 4: Level & Server Rank
    stat_rnk = ar_phrase("الترتيب") + f": #{rank}  •  " + ar_phrase("المستوى") + f": {level}"
    draw.text((info_x, bot_y + 92), stat_rnk, fill=cfg["info_sub"], font=f_stat)

    # 6. Bottom Right: 3D Metallic Seal Badge
    seal_cx = W - 78
    seal_cy = bot_y + 55
    seal_r = 44

    for sr in range(seal_r - 8, seal_r + 1):
        s_ratio = (sr - (seal_r - 8)) / 8
        s_col = (
            int(cfg["seal_inner"][0] * (1 - s_ratio) + cfg["seal_outer"][0] * s_ratio),
            int(cfg["seal_inner"][1] * (1 - s_ratio) + cfg["seal_outer"][1] * s_ratio),
            int(cfg["seal_inner"][2] * (1 - s_ratio) + cfg["seal_outer"][2] * s_ratio),
        )
        draw.ellipse([seal_cx - sr, seal_cy - sr, seal_cx + sr, seal_cy + sr], outline=s_col, width=2)

    draw.ellipse([seal_cx - (seal_r - 8), seal_cy - (seal_r - 8), seal_cx + (seal_r - 8), seal_cy + (seal_r - 8)], fill=cfg["seal_inner"])

    f_seal_lbl = get_font(12, bold=True)
    f_seal_num = get_font(28, bold=True)

    tier_label = "TIER"
    bbox = draw.textbbox((0, 0), tier_label, font=f_seal_lbl)
    tw = bbox[2] - bbox[0]
    draw.text((seal_cx - tw // 2, seal_cy - 20), tier_label, fill=cfg["seal_text"], font=f_seal_lbl)

    tier_val = cfg["tier_num"]
    bbox = draw.textbbox((0, 0), tier_val, font=f_seal_num)
    tw = bbox[2] - bbox[0]
    draw.text((seal_cx - tw // 2, seal_cy - 3), tier_val, fill=cfg["seal_text"], font=f_seal_num)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf
