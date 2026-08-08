"""
Tarneeb Graphics Generator (tarneeb_gfx.py)
Generates dynamic PIL images for player hands and game table rendering.
"""
import io
import math
from PIL import Image, ImageDraw, ImageFont

# Define Color Palette
BG_COLOR = (20, 35, 25)         # Luxury dark felt green
TABLE_BORDER = (45, 85, 55)     # Table rim border
CARD_BG = (252, 252, 255)       # Premium bright card paper
CARD_BORDER = (210, 215, 220)   # Subtle card border
TEXT_DARK = (15, 20, 25)
COLOR_RED = (210, 35, 45)       # Vibrant red for Hearts & Diamonds
COLOR_BLACK = (25, 30, 35)      # Sleek dark navy/black for Spades & Clubs
GOLD_COLOR = (245, 190, 45)     # Accent gold for scores & active turn

SUIT_SYMBOLS = {
    'H': '♥',  # Hearts / كوبا
    'D': '♦',  # Diamonds / ديناري
    'S': '♠',  # Spades / سبيد
    'C': '♣',  # Clubs / شيريا
}

SUIT_NAMES_AR = {
    'H': 'كوبا',
    'D': 'ديناري',
    'S': 'سبيد',
    'C': 'شيريا',
}

SUIT_COLORS = {
    'H': COLOR_RED,
    'D': COLOR_RED,
    'S': COLOR_BLACK,
    'C': COLOR_BLACK,
}

RANK_NAMES = {
    14: 'A', 13: 'K', 12: 'Q', 11: 'J',
    10: '10', 9: '9', 8: '8', 7: '7',
    6: '6', 5: '5', 4: '4', 3: '3', 2: '2'
}

def get_font(size):
    """Load font safely with fallback to default font."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()

def draw_card(suit, rank_val, width=100, height=145):
    """
    Renders a single playing card image.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded card rectangle
    radius = 10
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=CARD_BG, outline=CARD_BORDER, width=2)

    color = SUIT_COLORS.get(suit, COLOR_BLACK)
    symbol = SUIT_SYMBOLS.get(suit, '')
    rank_str = RANK_NAMES.get(rank_val, str(rank_val))

    font_rank = get_font(18)
    font_symbol = get_font(26)
    font_center = get_font(38)

    # Top-Left Rank & Suit
    draw.text((8, 6), rank_str, fill=color, font=font_rank)
    draw.text((8, 26), symbol, fill=color, font=font_symbol)

    # Bottom-Right Rank & Suit (Inverted placement)
    draw.text((width - 22, height - 48), symbol, fill=color, font=font_symbol)
    draw.text((width - 24, height - 24), rank_str, fill=color, font=font_rank)

    # Center Big Symbol
    try:
        bbox = font_center.getbbox(symbol)
        w_sym = bbox[2] - bbox[0]
        h_sym = bbox[3] - bbox[1]
    except Exception:
        w_sym, h_sym = 24, 30

    cx = (width - w_sym) / 2
    cy = (height - h_sym) / 2 - 4
    draw.text((cx, cy), symbol, fill=color, font=font_center)

    return img

def render_player_hand(cards):
    """
    Renders a player's hand of cards into a single PNG byte stream.
    Cards are sorted by suit (H, S, D, C) and then rank descending.
    """
    suit_order = {'H': 0, 'S': 1, 'D': 2, 'C': 3}
    sorted_cards = sorted(cards, key=lambda c: (suit_order.get(c.suit, 4), -c.rank))

    card_w, card_h = 95, 140
    overlap = 35  # Overlap cards horizontally
    n = len(sorted_cards)
    if n == 0:
        total_w = 400
    else:
        total_w = card_w + (n - 1) * overlap + 40

    total_h = card_h + 50
    img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark background banner with rounded corners
    draw.rounded_rectangle([0, 0, total_w - 1, total_h - 1], radius=15, fill=(15, 25, 20, 230), outline=(50, 100, 70), width=2)

    font_title = get_font(18)
    draw.text((20, 12), f"🎴 أوراقك الحالية ({n} بطاقة)", fill=(240, 245, 240), font=font_title)

    x_start = 20
    y_pos = 40

    for idx, card in enumerate(sorted_cards):
        card_img = draw_card(card.suit, card.rank, width=card_w, height=card_h)
        px = x_start + idx * overlap
        img.paste(card_img, (px, y_pos), card_img)

        # Draw index badge under card
        badge_text = str(idx + 1)
        font_badge = get_font(12)
        draw.ellipse([px + card_w//2 - 10, y_pos + card_h - 22, px + card_w//2 + 10, y_pos + card_h - 2], fill=(30, 40, 45, 220), outline=GOLD_COLOR)
        draw.text((px + card_w//2 - 4, y_pos + card_h - 20), badge_text, fill=(255, 255, 255), font=font_badge)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def render_table(current_trick, tarneeb_suit, bidder_info, score_t1, score_t2, round_tricks_t1, round_tricks_t2, players_info, turn_index):
    """
    Renders the central Tarneeb game table showing 4 player seats, played cards, current score & trump suit.
    """
    W, H = 700, 520
    img = Image.new("RGBA", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw outer table border / oval felt
    draw.rounded_rectangle([15, 15, W - 15, H - 15], radius=30, fill=BG_COLOR, outline=TABLE_BORDER, width=6)
    draw.rounded_rectangle([25, 25, W - 25, H - 25], radius=25, fill=(26, 46, 32), outline=(38, 68, 48), width=3)

    # 1. Header Banner - Tarneeb Info & Scores
    font_header = get_font(20)
    font_sub = get_font(15)

    # Scoreboard Left & Right
    # Team 1 (P1 & P3)
    draw.rounded_rectangle([40, 35, 210, 95], radius=10, fill=(15, 30, 22, 230), outline=(60, 120, 85), width=2)
    draw.text((50, 42), "الفريق 1 (مضيف/شريك)", fill=(200, 230, 210), font=font_sub)
    draw.text((50, 64), f"مجموع: {score_t1} | الجولة: {round_tricks_t1}", fill=GOLD_COLOR, font=font_sub)

    # Team 2 (P2 & P4)
    draw.rounded_rectangle([W - 210, 35, W - 40, 95], radius=10, fill=(15, 30, 22, 230), outline=(60, 120, 85), width=2)
    draw.text((W - 200, 42), "الفريق 2 (المنافس)", fill=(200, 230, 210), font=font_sub)
    draw.text((W - 200, 64), f"مجموع: {score_t2} | الجولة: {round_tricks_t2}", fill=GOLD_COLOR, font=font_sub)

    # Center Badge - Tarneeb Suit & Bid info
    draw.rounded_rectangle([240, 35, W - 240, 95], radius=10, fill=(35, 20, 25, 240), outline=GOLD_COLOR, width=2)
    if tarneeb_suit:
        sym = SUIT_SYMBOLS.get(tarneeb_suit, '?')
        color = SUIT_COLORS.get(tarneeb_suit, COLOR_RED)
        sname = SUIT_NAMES_AR.get(tarneeb_suit, '')
        draw.text((255, 42), f"الحكم (الطرنيب): {sym} {sname}", fill=color, font=font_header)
        b_name = bidder_info.get('name', '') if bidder_info else ''
        b_val = bidder_info.get('bid', 7) if bidder_info else 7
        draw.text((255, 68), f"الطلب: {b_val} بواسطة {b_name[:12]}", fill=(230, 230, 230), font=font_sub)
    else:
        draw.text((270, 52), "مرحلة المزايدة...", fill=GOLD_COLOR, font=font_header)

    # 2. Player Seat Coordinates
    # 0: South (bottom), 1: West (left), 2: North (top), 3: East (right)
    seat_positions = {
        0: (W // 2, H - 55),     # South
        1: (85, H // 2 + 30),     # West
        2: (W // 2, 135),        # North
        3: (W - 85, H // 2 + 30)  # East
    }

    # Trick card positions on the table
    card_positions = {
        0: (W // 2 - 40, H // 2 + 35),   # South played card
        1: (W // 2 - 120, H // 2 - 40),  # West played card
        2: (W // 2 - 40, H // 2 - 115),  # North played card
        3: (W // 2 + 40, H // 2 - 40)    # East played card
    }

    # Render Player Names & Turn Indicators
    font_name = get_font(15)
    for seat_idx in range(4):
        pos_x, pos_y = seat_positions[seat_idx]
        p_data = players_info[seat_idx] if seat_idx < len(players_info) else {'name': f'لاعب {seat_idx+1}', 'team': (seat_idx%2)+1}
        name = p_data.get('name', f'لاعب {seat_idx+1}')
        team_num = p_data.get('team', (seat_idx % 2) + 1)

        is_turn = (seat_idx == turn_index)
        box_bg = (60, 50, 20) if is_turn else (20, 30, 25)
        border_col = GOLD_COLOR if is_turn else (70, 90, 80)

        pw, ph = 130, 34
        bx, by = pos_x - pw // 2, pos_y - ph // 2
        draw.rounded_rectangle([bx, by, bx + pw, by + ph], radius=8, fill=box_bg, outline=border_col, width=2 if is_turn else 1)
        
        turn_prefix = "👉 " if is_turn else ""
        draw.text((bx + 10, by + 7), f"{turn_prefix}{name[:10]} (ف{team_num})", fill=(255, 255, 255) if not is_turn else GOLD_COLOR, font=font_name)

    # Render Played Cards in the current trick
    card_w, card_h = 80, 115
    for seat_idx, card_obj in current_trick:
        if seat_idx in card_positions:
            cx, cy = card_positions[seat_idx]
            c_img = draw_card(card_obj.suit, card_obj.rank, width=card_w, height=card_h)
            img.paste(c_img, (cx, cy), c_img)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
