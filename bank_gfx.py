"""
Bank Al-Haz Graphics Generator (bank_gfx.py)
Generates high-definition, professional board graphics using the luxury AI-generated
board template, with in-memory font & template caching for instant rendering.
"""

import os
import io
import re
import math
from functools import lru_cache
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

BG_COLOR = (15, 20, 18)
GOLD_COLOR = (245, 195, 55)
GOLD_LIGHT = (255, 230, 140)
WHITE = (255, 255, 255)
DARK_TEXT = (20, 22, 25)

PLAYER_COLORS = [
    (225, 45, 45),    # Red (P1)
    (35, 135, 245),   # Blue (P2)
    (45, 185, 75),    # Green (P3)
    (245, 175, 25)    # Yellow (P4)
]

PLAYER_EMOJIS = ['🔴', '🔵', '🟢', '🟡']

GROUP_COLORS = {
    'brown': (150, 90, 50),
    'cyan': (30, 175, 225),
    'pink': (225, 85, 155),
    'orange': (240, 125, 25),
    'red': (225, 45, 45),
    'yellow': (235, 195, 30),
    'green': (45, 175, 80),
    'blue': (25, 105, 225),
    'special': (75, 85, 95)
}

EMOJI_PATTERN = re.compile(
    '['
    '\U00010000-\U0010ffff'
    '\u2600-\u27BF'
    '\u2B50-\u2B55'
    '\u23E9-\u23FA'
    '\u25AA-\u25FE'
    '\uFE00-\uFE0F'
    '\u200D'
    ']+', flags=re.UNICODE
)

@lru_cache(maxsize=256)
def clean_arabic(text):
    """Strips emojis, markdown and unsupported symbols that cause tofu boxes in Arabic TTF fonts."""
    if not text:
        return ""
    cleaned = re.sub(r'[*_`~#]', '', str(text))
    cleaned = cleaned.replace('/', ' من ')
    cleaned = re.sub(r'[()\[\]{}+=]', ' ', cleaned)
    cleaned = EMOJI_PATTERN.sub('', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

@lru_cache(maxsize=256)
def ar(text):
    """Cleans emojis, reshapes and reorders Arabic text for flawless RTL visual rendering."""
    if not text:
        return ""
    cleaned = clean_arabic(text)
    if not cleaned:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(cleaned)
        return get_display(reshaped)
    except Exception:
        return cleaned

def _find_font(font_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "fonts", font_name),
        os.path.join("fonts", font_name),
        os.path.join(base_dir, "..", "fonts", font_name),
        font_name,
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

@lru_cache(maxsize=32)
def get_ar_font(size):
    """Prioritizes NotoSansArabic-Bold with in-memory caching."""
    p = _find_font("NotoSansArabic-Bold.ttf")
    if p:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    for sys_font in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\tahoma.ttf", "arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(sys_font, size)
        except Exception:
            pass
    return ImageFont.load_default()

@lru_cache(maxsize=32)
def get_latin_font(size):
    """Loads clean Latin/number font with in-memory caching."""
    p = _find_font("NotoSans-Bold.ttf")
    if p:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    for sys_font in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\tahoma.ttf", "arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(sys_font, size)
        except Exception:
            pass
    return ImageFont.load_default()

COL_X = [(51, 202), (226, 323), (345, 441), (464, 560), (582, 679), (701, 798), (822, 973)]
ROW_Y = [(51, 203), (227, 324), (346, 444), (465, 563), (584, 682), (702, 800), (821, 973)]

def _get_tile_rect(tile_idx):
    if tile_idx == 0:
        c, r = 6, 6
    elif 1 <= tile_idx <= 5:
        c, r = 6 - tile_idx, 6
    elif tile_idx == 6:
        c, r = 0, 6
    elif 7 <= tile_idx <= 11:
        c, r = 0, 6 - (tile_idx - 6)
    elif tile_idx == 12:
        c, r = 0, 0
    elif 13 <= tile_idx <= 17:
        c, r = tile_idx - 12, 0
    elif tile_idx == 18:
        c, r = 6, 0
    else:
        c, r = 6, tile_idx - 18

    x1, x2 = COL_X[c]
    y1, y2 = ROW_Y[r]
    return x1, y1, x2, y2, c, r

def _draw_shadow_text(draw, pos, text, font, fill=WHITE, shadow_color=(0, 0, 0, 240), shadow_offset=1):
    x, y = pos
    if shadow_offset > 0:
        for ox in range(-shadow_offset, shadow_offset + 1):
            for oy in range(-shadow_offset, shadow_offset + 1):
                if ox != 0 or oy != 0:
                    draw.text((x + ox, y + oy), text, fill=shadow_color, font=font)
    draw.text((x, y), text, fill=fill, font=font)

def _center_text(draw, cx, cy, text, font, fill=WHITE, shadow_offset=1):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    _draw_shadow_text(draw, (cx - w / 2, cy - h / 2), text, font, fill=fill, shadow_offset=shadow_offset)

def _draw_star(draw, cx, cy, r_outer=5, r_inner=2.5, fill=GOLD_COLOR):
    points = []
    for i in range(10):
        r = r_outer if i % 2 == 0 else r_inner
        ang = i * math.pi / 5 - math.pi / 2
        points.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    draw.polygon(points, fill=fill)

_CACHED_TEMPLATE = None

def _load_template():
    global _CACHED_TEMPLATE
    if _CACHED_TEMPLATE is not None:
        return _CACHED_TEMPLATE.copy()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    paths = [
        os.path.join(base_dir, "assets", "bank_board_template.jpg"),
        os.path.join(base_dir, "bank_board_template.jpg"),
        os.path.join("assets", "bank_board_template.jpg"),
        "bank_board_template.jpg",
        os.path.join(base_dir, "..", "assets", "bank_board_template.jpg"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                _CACHED_TEMPLATE = Image.open(p).convert("RGBA").resize((1024, 1024), Image.LANCZOS)
                return _CACHED_TEMPLATE.copy()
            except Exception:
                pass
    fallback = Image.new("RGBA", (1024, 1024), (20, 26, 23))
    fdraw = ImageDraw.Draw(fallback)
    fdraw.rectangle([45, 45, 979, 979], outline=GOLD_COLOR, width=4)
    fdraw.rectangle([210, 210, 814, 814], fill=(22, 45, 34), outline=(60, 95, 75), width=3)
    _CACHED_TEMPLATE = fallback
    return _CACHED_TEMPLATE.copy()

def render_board(tiles, players, current_turn_idx, last_dice=(0, 0), log_msg=""):
    board_img = _load_template()
    draw = ImageDraw.Draw(board_img, "RGBA")

    font_corner = get_ar_font(21)
    font_city_title = get_ar_font(18)
    font_city_title_small = get_ar_font(15)
    font_price = get_ar_font(16)
    font_owner_badge = get_latin_font(13)
    font_pawn = get_latin_font(14)

    font_main_title = get_ar_font(35)
    font_sub_title = get_ar_font(17)
    font_dice = get_ar_font(21)
    font_turn = get_ar_font(21)
    font_hud_header = get_ar_font(18)
    font_balance = get_ar_font(15)
    font_log = get_ar_font(14)

    for i, t in enumerate(tiles):
        x1, y1, x2, y2, c, r = _get_tile_rect(i)
        tw = x2 - x1
        th = y2 - y1
        cx = x1 + tw // 2
        cy = y1 + th // 2
        is_corner = (i in [0, 6, 12, 18])
        t_group = t.get('group', 'special')
        t_price = t.get('price', 0)
        t_name = clean_arabic(t.get('name', ''))

        if not is_corner and t_group != 'special':
            g_color = GROUP_COLORS.get(t_group, (75, 85, 95))
            banner_h = 20 if tw > th else 22
            draw.rounded_rectangle([x1 + 3, y1 + 3, x2 - 3, y1 + banner_h], radius=4, fill=g_color)
            draw.line([x1 + 3, y1 + banner_h, x2 - 3, y1 + banner_h], fill=GOLD_COLOR, width=1)

        if is_corner:
            _center_text(draw, cx, cy - 20, ar(t_name), font_corner, fill=GOLD_LIGHT, shadow_offset=2)
            if i == 0:
                _center_text(draw, cx, cy + 18, ar("مكافأة 200 جنيه"), font_price, fill=GOLD_COLOR)
            elif i == 6:
                _center_text(draw, cx, cy + 18, ar("كفالة: 50 ج"), font_price, fill=(240, 120, 120))
            elif i == 18:
                _center_text(draw, cx, cy + 18, ar("مباشرة"), font_price, fill=(255, 100, 100))
            elif i == 12:
                _center_text(draw, cx, cy + 18, ar("استراحة"), font_price, fill=(180, 230, 200))
        else:
            is_vert_slot = (th > tw)
            name_y = y1 + 38 if is_vert_slot else y1 + 30
            words = t_name.split()

            if is_vert_slot and len(words) >= 2 and len(t_name) > 8:
                w1 = ar(words[0])
                w2 = ar(" ".join(words[1:]))
                _center_text(draw, cx, name_y, w1, font_city_title_small, fill=WHITE, shadow_offset=1)
                _center_text(draw, cx, name_y + 18, w2, font_city_title_small, fill=WHITE, shadow_offset=1)
            else:
                _center_text(draw, cx, name_y, ar(t_name), font_city_title, fill=WHITE, shadow_offset=2)

            price_y = y2 - 20
            pb_w = 66
            pb_h = 22
            if t_price > 0:
                price_str = f"{t_price} ج"
                draw.rounded_rectangle([cx - pb_w // 2, price_y - pb_h // 2, cx + pb_w // 2, price_y + pb_h // 2], radius=4, fill=(15, 20, 25, 230), outline=GOLD_COLOR, width=1)
                _center_text(draw, cx, price_y, ar(price_str), font_price, fill=GOLD_COLOR, shadow_offset=1)
            elif t_group == 'special':
                if "حظ" in t_name:
                    _center_text(draw, cx, price_y, ar("فرصة"), font_price, fill=(210, 180, 255))
                elif "ضريبة" in t_name:
                    _center_text(draw, cx, price_y, ar("خصم 100 ج"), font_price, fill=(255, 130, 130))

        owner_idx = t.get('owner')
        if owner_idx is not None and 0 <= owner_idx < len(PLAYER_COLORS):
            owner_col = PLAYER_COLORS[owner_idx]
            badge_w, badge_h = 24, 18
            bx1 = x2 - badge_w - 4
            by1 = y1 + 4
            draw.rounded_rectangle([bx1, by1, bx1 + badge_w, by1 + badge_h], radius=4, fill=owner_col, outline=WHITE, width=1)
            _center_text(draw, bx1 + badge_w // 2, by1 + badge_h // 2, f"P{owner_idx+1}", font_owner_badge, fill=WHITE)

            level = t.get('level', 0)
            for s_idx in range(level):
                _draw_star(draw, x1 + 10 + s_idx * 11, y1 + 12, r_outer=4.5, r_inner=2.2, fill=GOLD_COLOR)

    tile_players = {}
    for p_idx, p in enumerate(players):
        if p.get('bankrupt', False):
            continue
        pos = p.get('position', 0)
        tile_players.setdefault(pos, []).append(p_idx)

    for pos, p_indices in tile_players.items():
        x1, y1, x2, y2, c, r = _get_tile_rect(pos)
        tw = x2 - x1
        th = y2 - y1
        cx = x1 + tw // 2
        is_corner = (pos in [0, 6, 12, 18])
        is_vert_slot = (th > tw)

        pawn_r = 11
        num_p = len(p_indices)

        for idx, p_idx in enumerate(p_indices):
            col = PLAYER_COLORS[p_idx]
            if is_corner:
                px = cx - (num_p - 1) * 14 + idx * 28
                py = y2 - 28
            elif is_vert_slot:
                px = cx - (num_p - 1) * 14 + idx * 28
                py = y1 + 92
            else:
                px = cx - (num_p - 1) * 15 + idx * 30
                py = y1 + 54

            draw.ellipse([px - pawn_r + 2, py - pawn_r + 2, px + pawn_r + 2, py + pawn_r + 2], fill=(0, 0, 0, 160))
            draw.ellipse([px - pawn_r, py - pawn_r, px + pawn_r, py + pawn_r], fill=col, outline=WHITE, width=2)
            _center_text(draw, px, py, str(p_idx + 1), font_pawn, fill=WHITE, shadow_offset=1)

    center_cx = 512

    _center_text(draw, center_cx, 260, ar("بنك الحظ الملكي"), font_main_title, fill=GOLD_COLOR, shadow_offset=3)
    _center_text(draw, center_cx, 305, ar("لعبة التجارة والاستثمار الكبرى"), font_sub_title, fill=GOLD_LIGHT, shadow_offset=1)

    cart_top = 405
    cart_bottom = 615
    cart_left = 405
    cart_right = 619

    draw.rounded_rectangle([cart_left, cart_top, cart_right, cart_bottom], radius=14, fill=(12, 22, 18, 225), outline=(218, 165, 32), width=2)

    d1, d2 = last_dice
    if d1 > 0 and d2 > 0:
        dice_text = f"النرد: {d1} و {d2} - المجموع {d1 + d2}"
    else:
        dice_text = "ارمِ النرد للانطلاق!"
    _center_text(draw, center_cx, cart_top + 45, ar(dice_text), font_dice, fill=GOLD_COLOR, shadow_offset=2)

    if 0 <= current_turn_idx < len(players):
        curr_p = players[current_turn_idx]
        p_name = curr_p.get('name', f'لاعب {current_turn_idx+1}')
        p_col = PLAYER_COLORS[current_turn_idx]

        turn_pill_w = 190
        turn_pill_h = 42
        turn_y = cart_top + 105
        draw.rounded_rectangle([center_cx - turn_pill_w // 2, turn_y - turn_pill_h // 2, center_cx + turn_pill_w // 2, turn_y + turn_pill_h // 2], radius=8, fill=(25, 35, 30), outline=p_col, width=2)
        draw.ellipse([center_cx - turn_pill_w // 2 + 10, turn_y - 8, center_cx - turn_pill_w // 2 + 26, turn_y + 8], fill=p_col, outline=WHITE)
        _center_text(draw, center_cx + 12, turn_y, ar(f"دور: {p_name[:10]}"), font_turn, fill=WHITE, shadow_offset=1)

        curr_pos = curr_p.get('position', 0)
        dest_tile = tiles[curr_pos] if curr_pos < len(tiles) else None
        if dest_tile:
            dest_name = clean_arabic(dest_tile.get('name', ''))
            _center_text(draw, center_cx, cart_top + 160, ar(f"المكان: {dest_name}"), font_sub_title, fill=GOLD_LIGHT, shadow_offset=1)

    panel_y1 = 678
    panel_y2 = 808
    panel_w = 440
    panel_x1 = center_cx - panel_w // 2
    panel_x2 = center_cx + panel_w // 2

    draw.rounded_rectangle([panel_x1, panel_y1, panel_x2, panel_y2], radius=10, fill=(14, 20, 18, 240), outline=(180, 150, 40), width=2)
    _center_text(draw, center_cx, panel_y1 + 18, ar("أرصدة المتسابقين"), font_hud_header, fill=GOLD_COLOR, shadow_offset=1)

    row1_y = panel_y1 + 46
    row2_y = panel_y1 + 72
    col1_x = panel_x1 + 115
    col2_x = panel_x1 + 325

    coords = [
        (col1_x, row1_y),
        (col2_x, row1_y),
        (col1_x, row2_y),
        (col2_x, row2_y),
    ]

    for p_idx, p in enumerate(players[:4]):
        p_name = p.get('name', f'لاعب {p_idx+1}')
        p_bal = p.get('balance', 0)
        is_bankrupt = p.get('bankrupt', False)
        is_jail = p.get('in_jail', False)
        p_col = PLAYER_COLORS[p_idx]
        px, py = coords[p_idx]

        draw.ellipse([px - 85, py - 6, px - 71, py + 8], fill=p_col, outline=WHITE)
        _center_text(draw, px - 78, py + 1, str(p_idx + 1), font_pawn, fill=WHITE)

        if is_bankrupt:
            entry_text = f"{p_name[:8]}: مفلس"
            text_col = (150, 150, 150)
        elif is_jail:
            entry_text = f"{p_name[:8]}: {p_bal} ج - سجن"
            text_col = (255, 140, 140)
        else:
            entry_text = f"{p_name[:8]}: {p_bal} جنيه"
            text_col = WHITE

        _draw_shadow_text(draw, (px - 62, py - 9), ar(entry_text), font_balance, fill=text_col)

    if log_msg:
        draw.line([panel_x1 + 15, panel_y1 + 95, panel_x2 - 15, panel_y1 + 95], fill=(60, 80, 70), width=1)
        _center_text(draw, center_cx, panel_y1 + 104, ar(f"آخر حدث: {clean_arabic(log_msg)[:44]}"), font_log, fill=GOLD_LIGHT, shadow_offset=1)

    buf = io.BytesIO()
    board_img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf