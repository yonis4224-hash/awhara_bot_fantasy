# coding: utf-8
import io, os, unicodedata, urllib.request, asyncio
from PIL import Image, ImageDraw, ImageFont
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
        'bold': 'C:/Windows/Fonts/segoeuib.ttf',
        'regular': 'C:/Windows/Fonts/segoeui.ttf',
        'tahoma': 'C:/Windows/Fonts/tahomabd.ttf',
    }
    path = paths.get(name, 'C:/Windows/Fonts/segoeuib.ttf')
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def render_profile_card(avatar_img, user_data, is_admin=False):
    theme_key = user_data.get('theme', 'default')
    valid_themes = {'default', 'gold', 'silver', 'purple'}
    if theme_key not in valid_themes:
        if theme_key == 'blue':
            theme_key = 'default'
        else:
            theme_key = 'default'
    
    bg_path = f'assets/clean_{theme_key}.jpg'
    
    if not os.path.exists(bg_path):
        bg_path = 'assets/clean_default.jpg'
        
    try:
        card = Image.open(bg_path).convert('RGBA')
    except Exception as e:
        card = Image.new('RGBA', (1376, 768), (30, 30, 30, 255))
        
    draw = ImageDraw.Draw(card)
    
    cx, cy, av_r = 456, 384, 118
    
    if avatar_img:
        av_dia = av_r * 2
        try:
            av_res = avatar_img.resize((av_dia, av_dia), Image.LANCZOS).convert('RGBA')
            av_mask = Image.new('L', (av_dia, av_dia), 0)
            ImageDraw.Draw(av_mask).ellipse([0, 0, av_dia, av_dia], fill=255)
            card.paste(av_res, (cx - av_r, cy - av_r), av_mask)
        except:
            pass
    
    start_x = 655
    text_color = (255, 255, 255)
    
    f_name = get_font('bold', 42)
    f_user = get_font('regular', 26)
    f_stat = get_font('bold', 32)
    f_stat_val = get_font('bold', 32)
    
    display_name = str(user_data.get('display_name') or user_data.get('username') or 'Member')
    username = str(user_data.get('username', ''))
    total_msgs = user_data.get('total_messages', 0)
    xp = user_data.get('xp', 0)
    rank = user_data.get('rank', 1)
    level = user_data.get('level', 1)
    
    name_clean = clean_display_name(display_name[:26])
    
    # Row 1
    draw.text((start_x, 295), name_clean, fill=text_color, font=f_name)
    bbox = draw.textbbox((0, 0), name_clean, font=f_name)
    name_w = bbox[2] - bbox[0]
    draw.text((start_x + name_w + 15, 312), f"@{username}", fill=(200, 200, 200), font=f_user)
    
    # Row 2
    xp_lbl = ar('النقاط:')
    xp_val = f" {xp:,} XP "
    lvl_lbl = ar('المستوى:')
    lvl_val = f" {level}"
    
    highlight = (255, 215, 0) if theme_key == 'gold' else (180, 220, 255) if theme_key in ['default', 'silver'] else (230, 160, 255)
    
    draw.text((start_x, 370), xp_lbl, fill=highlight, font=f_stat)
    lbl_w = draw.textbbox((0, 0), xp_lbl, font=f_stat)[2]
    draw.text((start_x + lbl_w + 5, 370), xp_val, fill=text_color, font=f_stat_val)
    
    val_w = draw.textbbox((0, 0), xp_val, font=f_stat_val)[2]
    
    draw.text((start_x + lbl_w + val_w + 35, 370), lvl_lbl, fill=highlight, font=f_stat)
    lbl2_w = draw.textbbox((0, 0), lvl_lbl, font=f_stat)[2]
    draw.text((start_x + lbl_w + val_w + 35 + lbl2_w + 5, 370), lvl_val, fill=text_color, font=f_stat_val)

    # Row 3
    rnk_lbl = ar('الترتيب:')
    rnk_val = f" #{rank} "
    msg_lbl = ar('الرسائل:')
    msg_val = f" {total_msgs:,}"
    
    draw.text((start_x, 435), rnk_lbl, fill=highlight, font=f_stat)
    rlbl_w = draw.textbbox((0, 0), rnk_lbl, font=f_stat)[2]
    draw.text((start_x + rlbl_w + 5, 435), rnk_val, fill=text_color, font=f_stat_val)
    
    rval_w = draw.textbbox((0, 0), rnk_val, font=f_stat_val)[2]
    
    draw.text((start_x + rlbl_w + rval_w + 35, 435), msg_lbl, fill=highlight, font=f_stat)
    mlbl_w = draw.textbbox((0, 0), msg_lbl, font=f_stat)[2]
    draw.text((start_x + rlbl_w + rval_w + 35 + mlbl_w + 5, 435), msg_val, fill=text_color, font=f_stat_val)

    buf = io.BytesIO()
    card.convert('RGB').save(buf, format='JPEG', quality=95)
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

if __name__ == '__main__':
    test_cases = [
        ('default', '👑 𝓕𝓪𝓻𝓲𝓼 | فارس 👑', 'f1_g', 4820, 1240, 1, 12),
        ('silver', '★ سارة ★', 'sara_9', 2100, 870, 2, 8),
        ('purple', '𝕶𝖎𝖓𝖌 | الملك', 'king_dark', 980, 500, 5, 5),
        ('gold', 'منـ♥ـشن | 𝓓𝓮𝓿', 'dev_special', 300, 200, 15, 3),
    ]
    for theme, name, user, xp, msgs, rank, lvl in test_cases:
        buf = render_profile_card(None, {'theme': theme, 'display_name': name, 'username': user, 'xp': xp, 'total_messages': msgs, 'rank': rank, 'level': lvl})
        open(f'final_{theme}_v2.jpg', 'wb').write(buf.read())
        print(f'final_{theme}_v2.jpg generated!')
