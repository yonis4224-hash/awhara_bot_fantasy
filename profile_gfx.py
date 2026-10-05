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

_BASE = os.path.dirname(os.path.abspath(__file__))
_F = os.path.join(_BASE, 'fonts')
ARABIC_FONT = os.path.join(_F, 'NotoSansArabic-Bold.ttf')   # full Arabic presentation forms
LATIN_FONT = os.path.join(_F, 'NotoSans-Bold.ttf')          # Latin, digits, symbols
EXTRA_FONTS = ['C:/Windows/Fonts/segoeuib.ttf', os.path.join(_F, 'Tajawal-Bold.ttf')]

_font_cache = {}
def _load(path, size):
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.BASIC)
        except Exception:
            _font_cache[key] = None
    return _font_cache[key]

def get_font(name, size):
    for p in (LATIN_FONT, ARABIC_FONT, *EXTRA_FONTS):
        f = _load(p, size)
        if f:
            return f
    return ImageFont.load_default()

def _render_bytes(font, ch):
    im = Image.new('L', (96, 96), 0)
    ImageDraw.Draw(im).text((10, 10), ch, font=font, fill=255)
    return im.tobytes()

_notdef = {}
_glyph_cache = {}
def _has_glyph(path, ch):
    if ch.isspace():
        return True
    key = (path, ch)
    if key in _glyph_cache:
        return _glyph_cache[key]
    f = _load(path, 40)
    ok = False
    if f:
        if path not in _notdef:
            _notdef[path] = _render_bytes(f, chr(0x10FFFF))
        b = _render_bytes(f, ch)
        ok = any(b) and b != _notdef[path]
    _glyph_cache[key] = ok
    return ok

def pick_font_path(ch):
    order = [ARABIC_FONT, LATIN_FONT] if is_arabic_char(ch) else [LATIN_FONT, ARABIC_FONT]
    for p in order + EXTRA_FONTS:
        if _has_glyph(p, ch):
            return p
    return None

def safe_name(text):
    text = unicodedata.normalize('NFKD', unicodedata.normalize('NFKC', str(text or '')))
    out = []
    for c in text:
        if unicodedata.combining(c) and not is_arabic_char(c):
            continue
        if is_emoji(c) or c in '\u200d\u200b\u200e\u200f\u202a\u202b\u202c\u2066\u2067\u2068\u2069':
            continue
        if pick_font_path(c) is None and not is_arabic_char(c):
            continue
        out.append(c)
    return ' '.join(''.join(out).split()) or 'Member'

def shape(text):
    return ar(text) if any(is_arabic_char(c) for c in text) else text

def _runs(text, size):
    runs = []
    for ch in text:
        p = pick_font_path(ch)
        f = _load(p, size) if p else None
        if f is None:
            continue
        if runs and runs[-1][1] is f:
            runs[-1][0] += ch
        else:
            runs.append([ch, f])
    return runs

_tmp = ImageDraw.Draw(Image.new('RGB', (1, 1)))
def text_w(text, size):
    return sum(_tmp.textlength(t, font=f) for t, f in _runs(text, size))

SHADOW = [(0, 0, 0)]
def draw_text(draw, x, y, text, size, fill):
    # y is the baseline; text is already in visual (display) order
    for t, f in _runs(text, size):
        draw.text((x + 2, y + 2), t, fill=SHADOW[0], font=f, anchor='ls')
        draw.text((x, y), t, fill=fill, font=f, anchor='ls')
        x += _tmp.textlength(t, font=f)
    return x

def draw_line(draw, x, base, max_w, segments, start, gap=14, minimum=20):
    size = start
    while size > minimum and sum(text_w(t, size) for t, _ in segments) + gap * (len(segments) - 1) > max_w:
        size -= 2
    for t, col in segments:
        x = draw_text(draw, x, base, t, size, col) + gap

def draw_stat(draw, x_left, x_right, base, label, value, lcol, vcol, start, minimum=18):
    # label on the left edge, value right-aligned on the right edge
    size = start
    while size > minimum and text_w(label, size) + text_w(value, size) + 14 > (x_right - x_left):
        size -= 2
    draw_text(draw, x_left, base, label, size, lcol)
    draw_text(draw, x_right - text_w(value, size), base, value, size, vcol)

def draw_mini(draw, x_left, x_right, base_label, base_value, label, value, lcol, vcol, lsize, vsize):
    # small centred column: label on top, value underneath
    width = x_right - x_left
    while vsize > 16 and text_w(value, vsize) > width:
        vsize -= 2
    while lsize > 14 and text_w(label, lsize) > width:
        lsize -= 2
    cx = (x_left + x_right) / 2
    draw_text(draw, cx - text_w(label, lsize) / 2, base_label, label, lsize, lcol)
    draw_text(draw, cx - text_w(value, vsize) / 2, base_value, value, vsize, vcol)

CROP = (250, 170, 1126, 598)   # card area (+ small margin) inside the 1376x768 template
SCALE = 1.7                    # upscale so the card is large inside Discord

def render_profile_card(avatar_img, user_data, is_admin=False):
    theme_key = user_data.get('theme', 'default')
    if theme_key not in ('default', 'gold', 'silver', 'purple'):
        theme_key = 'default'
    bg_path = os.path.join(_BASE, 'assets', f'clean_{theme_key}.jpg')
    try:
        card = Image.open(bg_path).convert('RGBA')
    except Exception:
        card = Image.new('RGBA', (1376, 768), (30, 30, 30, 255))
    card = card.crop(CROP)
    W, H = int(card.width * SCALE), int(card.height * SCALE)
    card = card.resize((W, H), Image.LANCZOS)
    draw = ImageDraw.Draw(card)

    def X(x):
        return int((x - CROP[0]) * SCALE)
    def Y(y):
        return int((y - CROP[1]) * SCALE)
    def S(v):
        return int(v * SCALE)

    cx, cy, av_r = X(456), Y(384), S(118)
    if avatar_img:
        try:
            d = av_r * 2
            av = avatar_img.resize((d, d), Image.LANCZOS).convert('RGBA')
            mask = Image.new('L', (d * 4, d * 4), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
            mask = mask.resize((d, d), Image.LANCZOS)
            card.paste(av, (cx - av_r, cy - av_r), mask)
        except Exception:
            pass

    x0, x1 = X(662), X(662 + 375)
    max_w = x1 - x0
    white = (255, 255, 255)
    hl = {'gold': (255, 215, 80), 'purple': (225, 150, 255)}.get(theme_key, (90, 235, 255))
    SHADOW[0] = (0, 0, 0)
    if theme_key == 'silver':
        white, hl = (14, 22, 36), (20, 62, 125)
        SHADOW[0] = (235, 240, 248)

    name = safe_name(user_data.get('display_name') or user_data.get('username'))
    xp = user_data.get('xp', 0)
    msgs = user_data.get('total_messages', 0)
    rank = user_data.get('rank', 1)
    level = user_data.get('level', 1)

    draw_line(draw, x0, Y(316), max_w, [(shape(name), white)], S(62), minimum=S(26))
    draw_stat(draw, x0, x1, Y(376), ar('النقاط'), f'{xp:,}', hl, white, S(44))
    draw_stat(draw, x0, x1, Y(420), ar('المستوى'), str(level), hl, white, S(44))
    draw_mini(draw, X(662), X(662 + 175), Y(472), Y(509), ar('الترتيب'), f'#{rank}', hl, white, S(27), S(38))
    draw_mini(draw, X(662 + 200), x1, Y(472), Y(509), ar('الرسائل'), f'{msgs:,}', hl, white, S(27), S(38))

    buf = io.BytesIO()
    card.convert('RGB').save(buf, format='PNG')
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
        open(f'final_{theme}_v3.png', 'wb').write(buf.read())
        print(f'final_{theme}_v3.png generated!')
