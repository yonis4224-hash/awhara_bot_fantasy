"""
Basra Card Game Graphics Generator (basra_gfx.py)
Generates PIL images for Basra game table, ground cards, player hands, and scoreboards.
"""
import io
from PIL import Image, ImageDraw, ImageFont

BG_COLOR = (18, 38, 25)           # Luxury dark felt green
TABLE_BORDER = (45, 85, 55)
CARD_BG = (252, 252, 255)
CARD_BORDER = (210, 215, 220)
COLOR_RED = (210, 35, 45)
COLOR_BLACK = (25, 30, 35)
GOLD_COLOR = (245, 190, 45)

SUIT_SYMBOLS = {'H': '♥', 'D': '♦', 'S': '♠', 'C': '♣'}
SUIT_COLORS = {'H': COLOR_RED, 'D': COLOR_RED, 'S': COLOR_BLACK, 'C': COLOR_BLACK}
RANK_NAMES = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: '10', 9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}

def get_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()

def draw_single_card(suit, rank, width=80, height=115):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=8, fill=CARD_BG, outline=CARD_BORDER, width=2)
    color = SUIT_COLORS.get(suit, COLOR_BLACK)
    symbol = SUIT_SYMBOLS.get(suit, '')
    rank_str = RANK_NAMES.get(rank, str(rank))

    f_rank = get_font(14)
    f_sym = get_font(20)
    f_center = get_font(30)

    draw.text((6, 4), rank_str, fill=color, font=f_rank)
    draw.text((6, 20), symbol, fill=color, font=f_sym)

    try:
        bbox = f_center.getbbox(symbol)
        w_sym = bbox[2] - bbox[0]
        h_sym = bbox[3] - bbox[1]
    except Exception:
        w_sym, h_sym = 20, 24

    cx = (width - w_sym) / 2
    cy = (height - h_sym) / 2 - 2
    draw.text((cx, cy), symbol, fill=color, font=f_center)
    return img

def render_basra_table(ground_cards, p1_info, p2_info, current_turn_idx, log_msg=""):
    """
    Renders the central Basra table graphic showing:
    - Ground cards face up on the table
    - Scoreboard & Captured Cards count
    - Turn banner
    """
    W, H = 720, 480
    img = Image.new("RGBA", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Outer table border
    draw.rounded_rectangle([15, 15, W - 15, H - 15], radius=25, fill=BG_COLOR, outline=TABLE_BORDER, width=5)
    draw.rounded_rectangle([25, 25, W - 25, H - 25], radius=20, fill=(24, 46, 32), outline=(38, 68, 48), width=2)

    font_title = get_font(20)
    font_sub = get_font(14)
    font_header = get_font(16)

    # 1. Header Scoreboard Box
    draw.rounded_rectangle([40, 35, W - 40, 95], radius=12, fill=(15, 30, 22, 230), outline=(60, 120, 85), width=2)

    # Player 1 Info
    p1_name = p1_info.get('name', 'لاعب 1')
    p1_score = p1_info.get('score', 0)
    p1_captured = p1_info.get('captured_count', 0)
    draw.text((55, 42), f"👤 {p1_name[:12]}", fill=(240, 245, 240), font=font_header)
    draw.text((55, 66), f"النقاط: {p1_score} | كروت مجمعة: {p1_captured}", fill=GOLD_COLOR, font=font_sub)

    # Center Title
    draw.text((W // 2 - 45, 42), "🃏 لعبة الشكوبا", fill=GOLD_COLOR, font=font_title)

    # Player 2 Info
    p2_name = p2_info.get('name', 'لاعب 2')
    p2_score = p2_info.get('score', 0)
    p2_captured = p2_info.get('captured_count', 0)
    draw.text((W - 220, 42), f"👤 {p2_name[:12]}", fill=(240, 245, 240), font=font_header)
    draw.text((W - 220, 66), f"النقاط: {p2_score} | كروت مجمعة: {p2_captured}", fill=GOLD_COLOR, font=font_sub)

    # 2. Ground Cards Area (الأرض)
    draw.rounded_rectangle([40, 115, W - 40, 360], radius=15, fill=(18, 35, 24, 200), outline=(50, 90, 65), width=2)
    draw.text((55, 125), f"🌱 كروت الأرض (الميدان) — العدد: {len(ground_cards)}", fill=(200, 225, 210), font=font_sub)

    card_w, card_h = 75, 108
    margin_x = 12
    margin_y = 12
    start_x = 55
    start_y = 150

    # Display ground cards in neat rows
    for idx, card in enumerate(ground_cards):
        row = idx // 7
        col = idx % 7
        px = start_x + col * (card_w + margin_x)
        py = start_y + row * (card_h + margin_y)

        c_img = draw_single_card(card.suit, card.rank, width=card_w, height=card_h)
        img.paste(c_img, (px, py), c_img)

    # 3. Turn & Log Banner
    curr_name = p1_name if current_turn_idx == 0 else p2_name
    draw.rounded_rectangle([40, 380, W - 40, 450], radius=10, fill=(35, 22, 28, 240), outline=GOLD_COLOR, width=2)
    draw.text((55, 390), f"👉 الدور الحالي: {curr_name[:15]}", fill=GOLD_COLOR, font=font_header)
    if log_msg:
        draw.text((55, 418), f"📢 {log_msg[:50]}", fill=(230, 235, 230), font=font_sub)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
