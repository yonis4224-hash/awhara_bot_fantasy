# coding: utf-8
import io, math, random, unicodedata, os, urllib.request, asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

def ar(text):
    if not text:
        return ''
    cfg = {'delete_harakat': False, 'support_ligatures': True, 'support_zwj': True}
    reshaper = arabic_reshaper.ArabicReshaper(configuration=cfg)
    return get_display(reshaper.reshape(str(text).strip()))

def is_arabic_char(ch):
    c = ord(ch)
    return (0x0600 <= c <= 0x06FF or 0x0750 <= c <= 0x077F or 0x08A0 <= c <= 0x08FF or 0xFB50 <= c <= 0xFDFF or 0xFE70 <= c <= 0xFEFF)

def is_emoji(ch):
    c = ord(ch)
    return (
        0x1F300 <= c <= 0x1FAFF or
        0x2600 <= c <= 0x27BF or
        0xFE00 <= c <= 0xFE0F or
        0x1F900 <= c <= 0x1F9FF or
        0x1F600 <= c <= 0x1F64F or
        0x1F680 <= c <= 0x1F6FF
    )

def clean_display_name(text: str) -> str:
    if not text:
        return 'Member'
    text = unicodedata.normalize('NFKD', str(text))
    cleaned = ''.join(c for c in text if not is_emoji(c)).strip()
    if not cleaned:
        return 'Member'
    if any(is_arabic_char(c) for c in cleaned):
        cfg = {'delete_harakat': False, 'support_ligatures': True, 'support_zwj': True}
        reshaper = arabic_reshaper.ArabicReshaper(configuration=cfg)
        return get_display(reshaper.reshape(cleaned))
    return cleaned

def get_font(name, size):
    paths = {
        'cinzel': 'fonts/Cinzel.ttf',
        'bold': 'C:/Windows/Fonts/segoeuib.ttf',
        'regular': 'C:/Windows/Fonts/segoeui.ttf',
        'tahoma': 'C:/Windows/Fonts/tahomabd.ttf',
    }
    path = paths.get(name, 'C:/Windows/Fonts/segoeuib.ttf')
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

THEMES = {
    'gold': {
        'tier': '1',
        'title_en': 'GOLD',
        'title_ar': 'الذهبي',
        'sub_en': 'PREMIUM ACCESS',
        'sub_ar': 'الوصول المميز',
        'bg_top': (250, 222, 120),
        'bg_mid': (226, 182, 70),
        'bg_bot': (160, 112, 22),
        'grain_hi': (255, 242, 180, 35),
        'grain_lo': (125, 82, 12, 28),
        'border_outer': (255, 240, 150),
        'border_inner': (145, 100, 20),
        'glow': None,
        'ring_outer': (255, 235, 140),
        'ring_inner': (140, 95, 20),
        'shadow': (70, 45, 8),
        'title_col': (55, 30, 4),
        'sub_col': (95, 62, 12),
        'desc_col': (120, 80, 20),
        'line_col': (120, 80, 18, 90),
        'info_name': (45, 25, 4),
        'info_user': (105, 72, 16),
        'info_stat': (75, 45, 8),
        'seal_outer': (255, 235, 135),
        'seal_inner': (160, 110, 22),
        'seal_fill': (195, 145, 35),
        'seal_text': (55, 30, 4),
    },
    'silver': {
        'tier': '2',
        'title_en': 'SILVER',
        'title_ar': 'الفضي',
        'sub_en': 'ELITE MEMBER',
        'sub_ar': 'عضو نخبة',
        'bg_top': (242, 246, 250),
        'bg_mid': (205, 214, 224),
        'bg_bot': (155, 168, 182),
        'grain_hi': (255, 255, 255, 45),
        'grain_lo': (110, 125, 140, 32),
        'border_outer': (252, 254, 255),
        'border_inner': (135, 148, 162),
        'glow': None,
        'ring_outer': (250, 253, 255),
        'ring_inner': (125, 140, 155),
        'shadow': (65, 75, 90),
        'title_col': (26, 38, 52),
        'sub_col': (60, 75, 92),
        'desc_col': (80, 96, 115),
        'line_col': (80, 95, 115, 90),
        'info_name': (22, 32, 45),
        'info_user': (65, 80, 98),
        'info_stat': (45, 60, 75),
        'seal_outer': (248, 252, 255),
        'seal_inner': (135, 150, 168),
        'seal_fill': (175, 188, 202),
        'seal_text': (26, 38, 52),
    },
    'purple': {
        'tier': '3',
        'title_en': 'PURPLE',
        'title_ar': 'البنفسجي',
        'sub_en': 'ROYAL SUBSCRIBER',
        'sub_ar': 'مشترك ملكي',
        'bg_top': (46, 12, 72),
        'bg_mid': (26, 7, 44),
        'bg_bot': (12, 3, 22),
        'grain_hi': (200, 100, 255, 28),
        'grain_lo': (0, 0, 0, 50),
        'border_outer': (215, 90, 255),
        'border_inner': (110, 30, 160),
        'glow': (190, 60, 255),
        'ring_outer': (235, 130, 255),
        'ring_inner': (90, 20, 140),
        'shadow': (180, 50, 255),
        'title_col': (255, 245, 255),
        'sub_col': (220, 160, 255),
        'desc_col': (190, 130, 235),
        'line_col': (190, 110, 255, 100),
        'info_name': (255, 250, 255),
        'info_user': (195, 145, 235),
        'info_stat': (235, 195, 255),
        'seal_outer': (230, 120, 255),
        'seal_inner': (95, 25, 145),
        'seal_fill': (65, 15, 100),
        'seal_text': (255, 235, 255),
    },
    'blue': {
        'tier': '4',
        'title_en': 'BLUE',
        'title_ar': 'الازرق',
        'sub_en': 'SPECIAL CONTRIBUTOR',
        'sub_ar': 'مساهم خاص',
        'bg_top': (8, 48, 110),
        'bg_mid': (5, 26, 68),
        'bg_bot': (2, 10, 32),
        'grain_hi': (0, 190, 255, 28),
        'grain_lo': (0, 0, 0, 50),
        'border_outer': (0, 205, 255),
        'border_inner': (0, 95, 165),
        'glow': (0, 180, 255),
        'ring_outer': (0, 225, 255),
        'ring_inner': (0, 75, 145),
        'shadow': (0, 180, 255),
        'title_col': (245, 252, 255),
        'sub_col': (140, 225, 255),
        'desc_col': (100, 195, 245),
        'line_col': (0, 185, 255, 100),
        'info_name': (255, 255, 255),
        'info_user': (120, 200, 245),
        'info_stat': (175, 235, 255),
        'seal_outer': (0, 220, 255),
        'seal_inner': (0, 85, 155),
        'seal_fill': (6, 45, 95),
        'seal_text': (220, 250, 255),
    },
}

def render_profile_card(avatar_img, user_data, is_admin=False):
    W, H = 640, 1020
    theme_key = user_data.get('theme', 'blue')
    if theme_key not in THEMES:
        theme_key = 'blue'
    t = THEMES[theme_key]
    is_dark = theme_key in ('purple', 'blue')
    corner_r = 50

    card = Image.new('RGBA', (W, H), (0, 0, 0, 0))

    # 1. Background Gradient
    bg = Image.new('RGBA', (W, H))
    dbg = ImageDraw.Draw(bg)
    top, mid, bot = t['bg_top'], t['bg_mid'], t['bg_bot']
    half = H // 2
    for y in range(half):
        f = y / half
        r = int(top[0] * (1 - f) + mid[0] * f)
        g = int(top[1] * (1 - f) + mid[1] * f)
        b = int(top[2] * (1 - f) + mid[2] * f)
        dbg.line([(0, y), (W, y)], fill=(r, g, b, 255))
    for y in range(half, H):
        f = (y - half) / (H - half)
        r = int(mid[0] * (1 - f) + bot[0] * f)
        g = int(mid[1] * (1 - f) + bot[1] * f)
        b = int(mid[2] * (1 - f) + bot[2] * f)
        dbg.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Diagonal Sheen
    sheen = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sheen)
    sheen_alpha = 15 if is_dark else 25
    for i in range(-W, W * 2, 4):
        ds.line([(i, 0), (i + 450, H)], fill=(255, 255, 255, sheen_alpha), width=2)
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=10))
    bg.alpha_composite(sheen)

    # Brushed Grain
    grain = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grain)
    random.seed(42)
    for _ in range(550):
        gx = random.randint(0, W - 1)
        gy = random.randint(0, H // 3)
        glen = random.randint(H // 2, H)
        col = t['grain_hi'] if random.random() > 0.45 else t['grain_lo']
        dg.line([(gx, gy), (gx, min(H, gy + glen))], fill=col, width=random.choice([1, 1, 2]))
    grain = grain.filter(ImageFilter.GaussianBlur(radius=0.7))
    bg.alpha_composite(grain)

    # Mask rounded
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, H], radius=corner_r, fill=255)
    card.paste(bg, (0, 0), mask)

    draw = ImageDraw.Draw(card)

    # 2. Border & Glow
    if is_dark:
        glow_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gld = ImageDraw.Draw(glow_layer)
        gc = t['glow']
        for off, a in [(10, 30), (7, 60), (4, 110), (2, 180), (1, 255)]:
            gld.rounded_rectangle([off, off, W - off, H - off], radius=corner_r, outline=(*gc, a), width=2)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=2.5))
        card.alpha_composite(glow_layer)
        draw.rounded_rectangle([2, 2, W - 2, H - 2], radius=corner_r, outline=t['border_outer'], width=3)
    else:
        draw.rounded_rectangle([2, 2, W - 2, H - 2], radius=corner_r, outline=t['border_outer'], width=4)
        draw.rounded_rectangle([7, 7, W - 7, H - 7], radius=corner_r - 5, outline=t['border_inner'], width=2)

    # 3. Discord Logo (Top Left)
    if os.path.exists('fonts/discord_logo.png'):
        try:
            d_icon = Image.open('fonts/discord_logo.png').convert('RGBA')
            ico_w, ico_h = 52, 40
            d_res = d_icon.resize((ico_w, ico_h), Image.LANCZOS)
            tint_color = t['title_col'] if not is_dark else (255, 255, 255)
            tinted = Image.new('RGBA', (ico_w, ico_h), (*tint_color[:3], 230))
            card.paste(tinted, (42, 42), d_res.split()[3])
        except:
            pass

    # 4. Avatar Medallion (Center)
    cx = W // 2
    cy = 270
    outer_r = 120
    av_r = 94

    if is_dark:
        halo = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        gc = t['glow']
        for gr in range(outer_r + 30, outer_r, -1):
            a = int(120 * (outer_r + 30 - gr) / 30)
            hd.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], outline=(*gc, a), width=2)
        halo = halo.filter(ImageFilter.GaussianBlur(radius=4.0))
        card.alpha_composite(halo)

    steps = 24
    for s in range(steps):
        frac = s / steps
        r = int(av_r + (outer_r - av_r) * frac)
        col = (
            int(t['ring_inner'][0] * (1 - frac) + t['ring_outer'][0] * frac),
            int(t['ring_inner'][1] * (1 - frac) + t['ring_outer'][1] * frac),
            int(t['ring_inner'][2] * (1 - frac) + t['ring_outer'][2] * frac),
        )
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*col, 255), width=2)

    draw.ellipse([cx - av_r - 2, cy - av_r - 2, cx + av_r + 2, cy + av_r + 2], outline=(0, 0, 0, 160), width=4)

    if avatar_img:
        av_dia = av_r * 2
        av_res = avatar_img.resize((av_dia, av_dia), Image.LANCZOS).convert('RGBA')
        av_mask = Image.new('L', (av_dia, av_dia), 0)
        ImageDraw.Draw(av_mask).ellipse([0, 0, av_dia, av_dia], fill=255)
        card.paste(av_res, (cx - av_r, cy - av_r), av_mask)
    else:
        av_fallback_col = (24, 20, 12) if not is_dark else (15, 10, 24)
        draw.ellipse([cx - av_r, cy - av_r, cx + av_r, cy + av_r], fill=av_fallback_col)
        if os.path.exists('fonts/discord_logo.png'):
            try:
                d_icon = Image.open('fonts/discord_logo.png').convert('RGBA')
                ico_w, ico_h = 96, 74
                d_res2 = d_icon.resize((ico_w, ico_h), Image.LANCZOS)
                tinted2 = Image.new('RGBA', (ico_w, ico_h), (*t['ring_outer'][:3], 210))
                card.paste(tinted2, (cx - ico_w // 2, cy - ico_h // 2), d_res2.split()[3])
            except:
                pass

    # 5. Center Typography
    f_title_en = get_font('cinzel', 58)
    f_title_ar = get_font('bold', 44)
    f_sub_en = get_font('bold', 20)
    f_sub_ar = get_font('bold', 26)

    ty = cy + outer_r + 35

    # English Title: 'GOLD', 'SILVER', etc.
    t_en = t['title_en']
    bbox = draw.textbbox((0, 0), t_en, font=f_title_en)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, ty), t_en, fill=t['title_col'], font=f_title_en, stroke_width=1, stroke_fill=t['title_col'])
    ty += 70

    # Arabic Title: 'الذهبي'
    t_ar = ar(t['title_ar'])
    bbox = draw.textbbox((0, 0), t_ar, font=f_title_ar)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, ty), t_ar, fill=t['title_col'], font=f_title_ar)
    ty += 72

    # Subtitle English: 'PREMIUM ACCESS'
    s_en = t['sub_en']
    bbox = draw.textbbox((0, 0), s_en, font=f_sub_en)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, ty), s_en, fill=t['sub_col'], font=f_sub_en)
    ty += 38

    # Subtitle Arabic: 'الوصول المميز'
    s_ar = ar(t['sub_ar'])
    bbox = draw.textbbox((0, 0), s_ar, font=f_sub_ar)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, ty), s_ar, fill=t['desc_col'], font=f_sub_ar)
    ty += 58

    # Divider line
    line_w = 420
    lx1 = (W - line_w) // 2
    draw.line([(lx1, ty), (lx1 + line_w, ty)], fill=t['line_col'], width=1)

    # 6. Bottom Information Section
    info_x = 45
    bot_y = H - 215

    f_name = get_font('bold', 30)
    f_handle = get_font('bold', 18)
    f_stat = get_font('bold', 20)

    display_name = str(user_data.get('display_name') or user_data.get('username') or 'Member')
    username = str(user_data.get('username', ''))
    total_msgs = user_data.get('total_messages', 0)
    xp = user_data.get('xp', 0)
    rank = user_data.get('rank', 1)
    level = user_data.get('level', 1)

    # Line 1: User Display Name
    name_text = clean_display_name(display_name[:26])
    draw.text((info_x, bot_y), name_text, fill=t['info_name'], font=f_name)

    # Line 2: @username
    if username:
        draw.text((info_x, bot_y + 42), f'@{username}', fill=t['info_user'], font=f_handle)

    # Stats lines (Perfect Arabic RTL & numbers order)
    stat_1 = ar('النقاط:') + f' {xp:,} XP'
    draw.text((info_x, bot_y + 76), stat_1, fill=t['info_stat'], font=f_stat)

    stat_2 = ar('الرسائل:') + f' {total_msgs:,}'
    draw.text((info_x, bot_y + 108), stat_2, fill=t['info_stat'], font=f_stat)

    stat_3 = ar('الترتيب:') + f' #{rank}   •   ' + ar('المستوى:') + f' {level}'
    draw.text((info_x, bot_y + 140), stat_3, fill=t['info_stat'], font=f_stat)

    # 7. Bottom Right Tier Badge (3D Embossed Medal)
    seal_cx = W - 92
    seal_cy = bot_y + 85
    seal_r = 54

    if is_dark:
        gc = t['glow']
        for gr in range(seal_r + 14, seal_r, -1):
            a = int(90 * (seal_r + 14 - gr) / 14)
            draw.ellipse([seal_cx - gr, seal_cy - gr, seal_cx + gr, seal_cy + gr], outline=(*gc, a), width=2)

    steps = 14
    for s in range(steps):
        frac = s / steps
        r = int(seal_r - 12 + 12 * frac)
        col = (
            int(t['seal_inner'][0] * (1 - frac) + t['seal_outer'][0] * frac),
            int(t['seal_inner'][1] * (1 - frac) + t['seal_outer'][1] * frac),
            int(t['seal_inner'][2] * (1 - frac) + t['seal_outer'][2] * frac),
        )
        draw.ellipse([seal_cx - r, seal_cy - r, seal_cx + r, seal_cy + r], outline=(*col, 255), width=2)

    draw.ellipse([seal_cx - seal_r + 12, seal_cy - seal_r + 12, seal_cx + seal_r - 12, seal_cy + seal_r - 12], fill=t['seal_fill'])

    f_seal_lbl = get_font('cinzel', 14)
    f_seal_num = get_font('cinzel', 38)

    lbl = 'TIER'
    bbox = draw.textbbox((0, 0), lbl, font=f_seal_lbl)
    tw = bbox[2] - bbox[0]
    draw.text((seal_cx - tw // 2, seal_cy - 28), lbl, fill=t['seal_text'], font=f_seal_lbl)

    num = t['tier']
    bbox = draw.textbbox((0, 0), num, font=f_seal_num)
    tw = bbox[2] - bbox[0]
    draw.text((seal_cx - tw // 2, seal_cy - 8), num, fill=t['seal_text'], font=f_seal_num)

    buf = io.BytesIO()
    card.save(buf, format='PNG')
    buf.seek(0)
    return buf

def _download_avatar_sync(url):
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = r.read()
        return Image.open(io.BytesIO(data)).convert('RGBA')
    except Exception:
        return None

async def download_avatar_async(url):
    return await asyncio.to_thread(_download_avatar_sync, url)

# Generate test cards
test_cases = [
    ('gold', '👑 𝓕𝓪𝓻𝓲𝓼 | فارس 👑', 'f1_g', 4820, 1240, 1, 12),
    ('silver', '★ سارة ★', 'sara_9', 2100, 870, 2, 8),
    ('purple', '𝕶𝖎𝖓𝖌 | الملك', 'king_dark', 980, 500, 5, 5),
    ('blue', 'منـ♥ـشن | 𝓓𝓮𝓿', 'dev_special', 300, 200, 15, 3),
]
for theme, name, user, xp, msgs, rank, lvl in test_cases:
    buf = render_profile_card(None, {'theme': theme, 'display_name': name, 'username': user, 'xp': xp, 'total_messages': msgs, 'rank': rank, 'level': lvl})
    open(f'final_{theme}.png', 'wb').write(buf.read())
    print(f'final_{theme}.png generated!')
