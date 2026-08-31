"""
Modern Profile Card Graphics Generator (profile_gfx.py)
Generates high-resolution, modern glassmorphism ID/Rank cards for members and admins
with dynamic Gold, Purple, and Dark themes.
"""
import io
import math
import asyncio
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def ar(text):
    """Reshapes and applies bidirectional algorithm for Arabic text rendering."""
    if not text:
        return ""
    # Remove emoji characters that might render as missing glyph boxes in standard TTF fonts
    clean_text = ""
    for ch in str(text):
        # Keep Arabic, ASCII, numbers, punctuation, common symbols
        if ord(ch) < 0x1F000 and ch not in ['🛡', '👑', '🥈', '✨', '💬', '📅', '⚡', '🏆', '⭐', '💎', '🔥', '🌱']:
            clean_text += ch
    clean_text = clean_text.strip()
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(clean_text)
        return get_display(reshaped)
    except Exception:
        return clean_text

def get_font(size, bold=False):
    fonts_to_try = [
        "arialbd.ttf" if bold else "arial.ttf",
        "seguisym.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "tahoma.ttf",
        "arial.ttf"
    ]
    for font_name in fonts_to_try:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
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

def _crop_circular_avatar(img, size=150):
    """Crops an image into a smooth, high-quality circular avatar."""
    if not img:
        img = Image.new("RGBA", (size, size), (40, 50, 65))
        d = ImageDraw.Draw(img)
        d.text((size // 3, size // 3), "?", fill=(200, 210, 225), font=get_font(size // 2))

    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 2, size * 2), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size * 2, size * 2), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)

    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    return output

THEMES = {
    "gold": {
        "bg_base": (18, 14, 7),
        "bg_gradient_end": (42, 32, 12),
        "border_outer": (255, 205, 55),
        "border_inner": (130, 100, 25),
        "accent_primary": (255, 210, 65),
        "accent_secondary": (230, 160, 30),
        "box_bg": (32, 25, 12, 225),
        "box_border": (185, 145, 35, 190),
        "badge_bg": (230, 170, 25),
        "badge_text": (18, 14, 5),
        "bar_fill": (255, 215, 60),
        "text_title": (255, 225, 110),
        "rank_color": (255, 215, 60),
    },
    "purple": {
        "bg_base": (16, 9, 26),
        "bg_gradient_end": (38, 16, 58),
        "border_outer": (190, 85, 255),
        "border_inner": (100, 40, 140),
        "accent_primary": (210, 110, 255),
        "accent_secondary": (160, 60, 245),
        "box_bg": (30, 15, 48, 225),
        "box_border": (160, 75, 225, 190),
        "badge_bg": (185, 75, 255),
        "badge_text": (255, 255, 255),
        "bar_fill": (205, 100, 255),
        "text_title": (230, 170, 255),
        "rank_color": (215, 125, 255),
    },
    "dark": {
        "bg_base": (14, 18, 25),
        "bg_gradient_end": (22, 30, 42),
        "border_outer": (0, 195, 235),
        "border_inner": (25, 75, 100),
        "accent_primary": (0, 210, 255),
        "accent_secondary": (0, 150, 215),
        "box_bg": (20, 28, 38, 225),
        "box_border": (45, 110, 145, 190),
        "badge_bg": (0, 175, 215),
        "badge_text": (10, 15, 22),
        "bar_fill": (0, 215, 255),
        "text_title": (130, 225, 255),
        "rank_color": (0, 210, 255),
    }
}

def render_profile_card(avatar_img, user_data, is_admin=False):
    """
    Renders a modern Profile ID / Rank card.
    """
    W, H = 880, 360
    theme_key = user_data.get("theme", "dark")
    cfg = THEMES.get(theme_key, THEMES["dark"])

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # 1. Background with sleek gradient
    bg_img = Image.new("RGBA", (W, H), cfg["bg_base"])
    bg_draw = ImageDraw.Draw(bg_img)
    
    for y in range(H):
        ratio = y / H
        r = int(cfg["bg_base"][0] * (1 - ratio) + cfg["bg_gradient_end"][0] * ratio)
        g = int(cfg["bg_base"][1] * (1 - ratio) + cfg["bg_gradient_end"][1] * ratio)
        b = int(cfg["bg_base"][2] * (1 - ratio) + cfg["bg_gradient_end"][2] * ratio)
        bg_draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    card.paste(bg_img, (0, 0))
    
    # Outer Rounded Card Outline
    pad = 12
    draw.rounded_rectangle(
        [pad, pad, W - pad, H - pad],
        radius=24,
        fill=None,
        outline=cfg["border_outer"],
        width=3
    )
    draw.rounded_rectangle(
        [pad + 3, pad + 3, W - pad - 3, H - pad - 3],
        radius=21,
        fill=None,
        outline=cfg["border_inner"],
        width=1
    )

    # 2. Avatar with glowing double-ring
    av_size = 140
    av_x = 42
    av_y = 48
    
    # Glowing avatar outer circle
    draw.ellipse(
        [av_x - 6, av_y - 6, av_x + av_size + 6, av_y + av_size + 6],
        fill=None,
        outline=cfg["accent_primary"],
        width=4
    )
    draw.ellipse(
        [av_x - 11, av_y - 11, av_x + av_size + 11, av_y + av_size + 11],
        fill=None,
        outline=(*cfg["accent_secondary"][:3], 100),
        width=2
    )

    # Crop and paste avatar
    circular_av = _crop_circular_avatar(avatar_img, size=av_size)
    card.paste(circular_av, (av_x, av_y), circular_av)

    # 3. User Info Header
    info_x = 210
    display_name = str(user_data.get("display_name", "Member"))
    username = str(user_data.get("username", ""))
    user_id = str(user_data.get("user_id", ""))
    
    f_name = get_font(28, bold=True)
    f_user = get_font(15)
    f_badge = get_font(15, bold=True)
    f_stat_title = get_font(14)
    f_stat_val = get_font(21, bold=True)
    f_rank_large = get_font(34, bold=True)
    f_lvl = get_font(16, bold=True)

    # Display Name
    draw.text((info_x, 38), ar(display_name[:18]), fill=(255, 255, 255), font=f_name)
    
    # Username tag
    user_sub = f"@{username}" if username else f"ID: {user_id}"
    draw.text((info_x, 72), user_sub[:24], fill=(165, 180, 195), font=f_user)

    # Badges Row (Admin Badge + Custom Title Badge)
    badge_y = 98
    curr_badge_x = info_x

    # Admin Badge (if staff)
    if is_admin:
        admin_text = ar("إدارة السيرفر")
        abox = draw.textbbox((curr_badge_x, badge_y), admin_text, font=f_badge)
        aw = max(100, abox[2] - abox[0] + 20)
        ah = 28
        draw.rounded_rectangle(
            [curr_badge_x, badge_y, curr_badge_x + aw, badge_y + ah],
            radius=14,
            fill=(220, 45, 45, 230),
            outline=(255, 90, 90),
            width=1
        )
        draw.text((curr_badge_x + 10, badge_y + 4), admin_text, fill=(255, 255, 255), font=f_badge)
        curr_badge_x += aw + 12

    # Title Badge (ملك التفاعل / متفاعل دائم / متفاعل...)
    title_raw = user_data.get("title", "عضو نشيط")
    title_text = ar(title_raw)
    tbox = draw.textbbox((curr_badge_x, badge_y), title_text, font=f_badge)
    tw = max(95, tbox[2] - tbox[0] + 22)
    th = 28
    draw.rounded_rectangle(
        [curr_badge_x, badge_y, curr_badge_x + tw, badge_y + th],
        radius=14,
        fill=cfg["badge_bg"],
        outline=cfg["border_outer"],
        width=1
    )
    draw.text((curr_badge_x + 11, badge_y + 4), title_text, fill=cfg["badge_text"], font=f_badge)

    # 4. Rank Badge on Top Right
    rank_num = user_data.get("rank", 1)
    rank_box_w = 175
    rank_box_h = 75
    rank_box_x = W - pad - rank_box_w - 20
    rank_box_y = 35

    draw.rounded_rectangle(
        [rank_box_x, rank_box_y, rank_box_x + rank_box_w, rank_box_y + rank_box_h],
        radius=16,
        fill=cfg["box_bg"],
        outline=cfg["border_outer"],
        width=2
    )
    draw.text((rank_box_x + 16, rank_box_y + 8), ar("الترتيب العام"), fill=(175, 195, 210), font=f_stat_title)
    rank_display_str = f"#{rank_num}"
    draw.text((rank_box_x + 16, rank_box_y + 28), rank_display_str, fill=cfg["rank_color"], font=f_rank_large)

    # 5. Level & XP Progress Bar
    level = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    
    next_level_xp = int((level ** 2) * 30)
    prev_level_xp = int(((level - 1) ** 2) * 30)
    current_level_progress = max(0, xp - prev_level_xp)
    level_xp_needed = max(1, next_level_xp - prev_level_xp)
    progress_ratio = min(1.0, max(0.05, current_level_progress / level_xp_needed))

    bar_x = info_x
    bar_y = 156
    bar_w = W - pad - bar_x - 30
    bar_h = 14

    # Level Text
    draw.text((bar_x, bar_y - 22), ar(f"المستوى {level}"), fill=cfg["text_title"], font=f_lvl)
    draw.text((bar_x + bar_w - 110, bar_y - 20), f"{xp} / {next_level_xp} XP", fill=(160, 180, 195), font=f_stat_title)

    # Bar background
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=7, fill=(25, 35, 45, 200), outline=(50, 70, 90), width=1)
    
    # Bar fill
    fill_w = int(bar_w * progress_ratio)
    if fill_w > 8:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=7, fill=cfg["bar_fill"])

    # 6. Three Stats Cards at Bottom Grid
    stat_box_y = 195
    stat_box_h = 125
    available_w = W - 2 * (pad + 15)
    box_w = (available_w - 24) // 3

    tot_msgs = user_data.get('total_messages', 0)
    wk_msgs = user_data.get('weekly_messages', 0)
    tot_xp = user_data.get('xp', 0)

    stats = [
        {"title": ar("إجمالي الرسائل"), "val": ar(f"{tot_msgs:,} رسالة"), "col": (255, 255, 255)},
        {"title": ar("رسائل هذا الأسبوع"), "val": ar(f"{wk_msgs:,} رسالة"), "col": cfg["accent_primary"]},
        {"title": ar("نقاط التفاعل"), "val": ar(f"{tot_xp:,} نقطة"), "col": cfg["text_title"]},
    ]

    for idx, st in enumerate(stats):
        bx = pad + 15 + idx * (box_w + 12)
        draw.rounded_rectangle(
            [bx, stat_box_y, bx + box_w, stat_box_y + stat_box_h],
            radius=16,
            fill=cfg["box_bg"],
            outline=cfg["box_border"],
            width=1
        )
        
        # Stat Title
        draw.text((bx + 16, stat_box_y + 16), st["title"], fill=(180, 200, 215), font=f_stat_title)
        
        # Stat Value
        draw.text((bx + 16, stat_box_y + 48), st["val"], fill=st["col"], font=f_stat_val)

        # Bottom accent indicator line
        draw.rounded_rectangle(
            [bx + 16, stat_box_y + stat_box_h - 10, bx + 65, stat_box_y + stat_box_h - 6],
            radius=2,
            fill=cfg["accent_primary"]
        )

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    buf.seek(0)
    return buf
