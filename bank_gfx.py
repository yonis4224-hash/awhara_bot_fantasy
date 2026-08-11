"""
Bank Al-Haz Graphics Generator (bank_gfx.py)
Generates dynamic PIL images for Bank Al-Haz (Monopoly) game board and status displays.
"""
import io
import math
from PIL import Image, ImageDraw, ImageFont

# Board Color Palette
BG_COLOR = (24, 32, 28)          # Dark sleek felt background
BOARD_BG = (235, 240, 232)        # Cream light board surface
BORDER_COLOR = (40, 50, 45)      # Dark tile borders
TEXT_COLOR = (20, 25, 22)
GOLD_COLOR = (245, 190, 45)

PLAYER_COLORS = [
    (220, 40, 40),    # Red (P1)
    (30, 120, 220),   # Blue (P2)
    (40, 180, 70),    # Green (P3)
    (230, 160, 20)    # Yellow (P4)
]

PLAYER_EMOJIS = ['🔴', '🔵', '🟢', '🟡']

GROUP_COLORS = {
    'brown': (140, 80, 40),
    'cyan': (100, 200, 230),
    'pink': (220, 100, 170),
    'orange': (240, 140, 30),
    'red': (220, 50, 50),
    'yellow': (240, 210, 40),
    'green': (50, 160, 70),
    'blue': (40, 90, 200),
    'special': (180, 190, 195)
}

def get_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()

def _get_tile_rect(tile_idx, W=750, H=750, pad=30):
    """
    Computes coordinates for 24 perimeter tiles around a 7x7 grid.
    0: Bottom-Right corner
    1..5: Bottom edge (Right to Left)
    6: Bottom-Left corner
    7..11: Left edge (Bottom to Top)
    12: Top-Left corner
    13..17: Top edge (Left to Right)
    18: Top-Right corner
    19..23: Right edge (Top to Bottom)
    """
    grid_w = (W - 2 * pad) // 7
    grid_h = (H - 2 * pad) // 7

    # Calculate (col, row) on 7x7 grid (0..6, 0..6)
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
    else:  # 19..23
        c, r = 6, tile_idx - 18

    x1 = pad + c * grid_w
    y1 = pad + r * grid_h
    x2 = x1 + grid_w
    y2 = y1 + grid_h
    return x1, y1, x2, y2

def render_board(tiles, players, current_turn_idx, last_dice=(0, 0), log_msg=""):
    """
    Renders full game board image with player positions, owned properties, houses, and status box.
    """
    W, H = 760, 760
    img = Image.new("RGBA", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    pad = 30
    grid_w = (W - 2 * pad) // 7
    grid_h = (H - 2 * pad) // 7

    # Draw Center Board Felt Background
    center_x1 = pad + grid_w
    center_y1 = pad + grid_h
    center_x2 = pad + 6 * grid_w
    center_y2 = pad + 6 * grid_h
    draw.rectangle([center_x1, center_y1, center_x2, center_y2], fill=(30, 42, 35), outline=(50, 75, 60), width=3)

    font_tile_title = get_font(12)
    font_sub = get_font(10)
    font_center_title = get_font(22)
    font_center_body = get_font(14)

    # 1. Render All 24 Perimeter Tiles
    for i, t in enumerate(tiles):
        x1, y1, x2, y2 = _get_tile_rect(i, W, H, pad)
        tw = x2 - x1
        th = y2 - y1

        # Tile Background
        is_corner = (i in [0, 6, 12, 18])
        bg = (245, 248, 240) if not is_corner else (225, 235, 220)
        draw.rectangle([x1, y1, x2, y2], fill=bg, outline=BORDER_COLOR, width=2)

        # Property Color Header Banner (if city)
        group_col = GROUP_COLORS.get(t.get('group', 'special'), (180, 190, 195))
        if not is_corner and t.get('group') != 'special':
            header_h = 22
            # Determine header position depending on board edge
            if y1 < center_y1:  # Top edge
                draw.rectangle([x1 + 1, y2 - header_h, x2 - 1, y2 - 1], fill=group_col)
            elif y2 > center_y2:  # Bottom edge
                draw.rectangle([x1 + 1, y1 + 1, x2 - 1, y1 + header_h], fill=group_col)
            elif x1 < center_x1:  # Left edge
                draw.rectangle([x2 - header_h, y1 + 1, x2 - 1, y2 - 1], fill=group_col)
            else:  # Right edge
                draw.rectangle([x1 + 1, y1 + 1, x1 + header_h, y2 - 1], fill=group_col)

        # Tile Name & Price
        tname = t.get('name', '')
        tprice = t.get('price', 0)
        draw.text((x1 + 6, y1 + 6), tname[:10], fill=TEXT_COLOR, font=font_tile_title)
        if tprice > 0:
            draw.text((x1 + 6, y1 + 24), f"{tprice}ج", fill=(80, 90, 85), font=font_sub)

        # Owner Indicator Badge
        owner_idx = t.get('owner')
        if owner_idx is not None and 0 <= owner_idx < len(PLAYER_COLORS):
            owner_col = PLAYER_COLORS[owner_idx]
            draw.rectangle([x1 + tw - 16, y1 + 4, x1 + tw - 4, y1 + 16], fill=owner_col, outline=(255, 255, 255))
            level = t.get('level', 0)
            if level > 0:
                draw.text((x1 + tw - 14, y1 + 4), f"{level}", fill=(255, 255, 255), font=font_sub)

    # 2. Render Player Tokens on Tiles
    # Group players by position
    tile_players = {}
    for p_idx, p in enumerate(players):
        if p.get('bankrupt', False):
            continue
        pos = p.get('position', 0)
        tile_players.setdefault(pos, []).append(p_idx)

    for pos, p_indices in tile_players.items():
        x1, y1, x2, y2 = _get_tile_rect(pos, W, H, pad)
        tw = x2 - x1
        th = y2 - y1

        for idx_in_tile, p_idx in enumerate(p_indices):
            col = PLAYER_COLORS[p_idx]
            # Offset tokens nicely if multiple players are on the same tile
            ox = (idx_in_tile % 2) * 18 + 10
            oy = (idx_in_tile // 2) * 18 + (th - 28)
            px = x1 + ox
            py = y1 + oy

            draw.ellipse([px, py, px + 16, py + 16], fill=col, outline=(255, 255, 255), width=2)
            draw.text((px + 4, py + 2), str(p_idx + 1), fill=(255, 255, 255), font=font_sub)

    # 3. Center Status Panel (Dice, Turn, Balances)
    cx_start = center_x1 + 15
    cy_start = center_y1 + 15
    cx_w = (center_x2 - center_x1) - 30
    cy_h = (center_y2 - center_y1) - 30

    # Title
    draw.text((cx_start + 110, cy_start + 10), "🏰 بنك الحظ", fill=GOLD_COLOR, font=font_center_title)

    # Last Dice Roll
    d1, d2 = last_dice
    dice_str = f"🎲 النرد: {d1} + {d2} = {d1 + d2}" if (d1 > 0 and d2 > 0) else "🎲 ارمِ النرد لبدء الجولة"
    draw.text((cx_start + 90, cy_start + 45), dice_str, fill=(230, 240, 235), font=font_center_body)

    # Turn Indicator
    if 0 <= current_turn_idx < len(players):
        curr_p = players[current_turn_idx]
        p_name = curr_p.get('name', f'لاعب {current_turn_idx+1}')
        p_col = PLAYER_COLORS[current_turn_idx]
        draw.rounded_rectangle([cx_start + 30, cy_start + 75, cx_start + cx_w - 30, cy_start + 110], radius=8, fill=(40, 60, 50), outline=p_col, width=2)
        draw.text((cx_start + 45, cy_start + 83), f"👉 دور: {p_name[:14]}", fill=GOLD_COLOR, font=font_center_body)

    # Player Balances Table
    bal_y = cy_start + 125
    draw.line([cx_start + 20, bal_y, cx_start + cx_w - 20, bal_y], fill=(70, 95, 80), width=1)
    bal_y += 10
    draw.text((cx_start + 20, bal_y), "💰 أرصدة اللاعبين:", fill=(200, 220, 210), font=get_font(13))
    bal_y += 22

    for p_idx, p in enumerate(players):
        p_name = p.get('name', f'لاعب {p_idx+1}')
        p_bal = p.get('balance', 0)
        is_bankrupt = p.get('bankrupt', False)
        is_jail = p.get('in_jail', False)

        p_col = PLAYER_COLORS[p_idx]
        status = " (مفلس)" if is_bankrupt else (" (في السجن 🚓)" if is_jail else "")
        bal_text = f"P{p_idx+1}: {p_name[:10]} ➔ {p_bal}ج{status}"
        
        draw.ellipse([cx_start + 20, bal_y + 3, cx_start + 30, bal_y + 13], fill=p_col)
        draw.text((cx_start + 36, bal_y), bal_text, fill=(240, 245, 240) if not is_bankrupt else (160, 160, 160), font=font_sub)
        bal_y += 20

    # Recent Log Banner
    if log_msg:
        draw.rounded_rectangle([cx_start + 15, cy_start + cy_h - 45, cx_start + cx_w - 15, cy_start + cy_h - 10], radius=6, fill=(15, 25, 20, 230), outline=GOLD_COLOR, width=1)
        draw.text((cx_start + 25, cy_start + cy_h - 38), f"📢 {log_msg[:38]}", fill=(255, 255, 255), font=font_sub)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
