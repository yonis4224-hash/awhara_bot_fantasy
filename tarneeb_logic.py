"""
Tarneeb Game Logic Engine (tarneeb_logic.py)
Handles cards deck, game state machine, bidding, rules validation, trick resolution, score calculation, and AI bot decision logic.
"""
import random

SUIT_NAMES_AR = {'H': 'كوبا ♥', 'D': 'ديناري ♦', 'S': 'سبيد ♠', 'C': 'شيريا ♣'}
RANK_NAMES_AR = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: '10', 9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}

class Card:
    def __init__(self, suit, rank):
        self.suit = suit   # 'H', 'D', 'S', 'C'
        self.rank = rank   # 2..14

    @property
    def code(self):
        return f"{self.suit}-{self.rank}"

    def __repr__(self):
        return f"{SUIT_NAMES_AR.get(self.suit, self.suit)} {RANK_NAMES_AR.get(self.rank, self.rank)}"

    def __eq__(self, other):
        return isinstance(other, Card) and self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash((self.suit, self.rank))


class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in ['H', 'D', 'S', 'C'] for r in range(2, 15)]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal_four_hands(self):
        self.shuffle()
        return [
            self.cards[0:13],
            self.cards[13:26],
            self.cards[26:39],
            self.cards[39:52]
        ]


class Player:
    def __init__(self, user_id, name, seat, is_ai=False):
        self.user_id = str(user_id)
        self.name = name
        self.seat = seat      # 0: South, 1: West, 2: North, 3: East
        self.team = 1 if seat in (0, 2) else 2
        self.is_ai = is_ai
        self.hand = []
        self.is_passed_bidding = False

    def remove_card(self, card):
        for c in self.hand:
            if c == card:
                self.hand.remove(c)
                return True
        return False


class TarneebGame:
    def __init__(self, channel_id, target_score=31):
        self.channel_id = channel_id
        self.target_score = target_score
        self.state = 'LOBBY'   # 'LOBBY', 'BIDDING', 'SELECT_TRUMP', 'PLAYING', 'ROUND_END', 'GAME_OVER'
        
        self.players = []       # list of 4 Player instances
        self.score_t1 = 0
        self.score_t2 = 0
        self.dealer_index = 0
        
        # Round specific attributes
        self.tarneeb_suit = None
        self.current_bid = 0
        self.highest_bidder = None
        self.round_tricks_t1 = 0
        self.round_tricks_t2 = 0
        self.current_trick = []   # list of (seat_idx, Card)
        self.lead_suit = None
        self.turn_index = 0
        self.bidding_turn = 0
        self.last_round_msg = ""

    def add_player(self, user_id, name):
        if len(self.players) >= 4:
            return False, "الطاولة مكتملة بالفعل!"
        if any(p.user_id == str(user_id) for p in self.players):
            return False, "أنت منضم بالفعل للطاولة!"

        seat = len(self.players)
        p = Player(user_id, name, seat, is_ai=False)
        self.players.append(p)
        return True, f"انضم **{name}** للطاولة (مقعد {seat + 1} - فريق {p.team})"

    def fill_with_ai(self):
        ai_count = 1
        while len(self.players) < 4:
            seat = len(self.players)
            ai_name = f"بوت زكي {ai_count}"
            p = Player(f"AI_{seat}_{random.randint(100,999)}", ai_name, seat, is_ai=True)
            self.players.append(p)
            ai_count += 1

    def start_game(self):
        if len(self.players) < 4:
            self.fill_with_ai()
        
        self.score_t1 = 0
        self.score_t2 = 0
        self.dealer_index = random.randint(0, 3)
        self.start_new_round()

    def start_new_round(self):
        deck = Deck()
        hands = deck.deal_four_hands()

        for idx, p in enumerate(self.players):
            p.hand = sorted(hands[idx], key=lambda c: ({'H':0,'S':1,'D':2,'C':3}[c.suit], -c.rank))
            p.is_passed_bidding = False

        self.tarneeb_suit = None
        self.current_bid = 0
        self.highest_bidder = None
        self.round_tricks_t1 = 0
        self.round_tricks_t2 = 0
        self.current_trick = []
        self.lead_suit = None

        self.bidding_turn = (self.dealer_index + 1) % 4
        self.turn_index = self.bidding_turn
        self.state = 'BIDDING'

    def process_bid(self, seat, bid_val):
        """
        bid_val = 0 means PASS.
        bid_val = 7..13 means Bidding.
        """
        if self.state != 'BIDDING' or self.bidding_turn != seat:
            return False, "ليس دورك في المزايدة!"

        player = self.players[seat]

        if bid_val == 0:
            player.is_passed_bidding = True
            msg = f"🚫 **{player.name}** اختار (تمرير / بس)"
        else:
            if bid_val <= self.current_bid or bid_val < 7 or bid_val > 13:
                return False, f"يجب أن تكون المزايدة أكبر من الطلب الحالي ({self.current_bid}) وتتراوح بين 7 و 13"
            self.current_bid = bid_val
            self.highest_bidder = seat
            msg = f"📢 **{player.name}** طلَب **{bid_val}**!"

        # Check remaining active bidders
        active_bidders = [p for p in self.players if not p.is_passed_bidding]

        if len(active_bidders) == 1 and self.highest_bidder is not None:
            # Bidding finished! Highest bidder chooses Trump
            self.state = 'SELECT_TRUMP'
            self.turn_index = self.highest_bidder
            bidder_name = self.players[self.highest_bidder].name
            return True, f"{msg}\n🎉 فاز **{bidder_name}** بالطلب ({self.current_bid})! جاري اختيار الحكم (الطرنيب)..."
        elif len(active_bidders) == 0:
            # Everyone passed without a bid -> redeal or auto-assign 7 to dealer+1
            self.highest_bidder = (self.dealer_index + 1) % 4
            self.current_bid = 7
            self.state = 'SELECT_TRUMP'
            self.turn_index = self.highest_bidder
            bidder_name = self.players[self.highest_bidder].name
            return True, f"مرر الجميع! تم تعيين الطلب تلقائياً على 7 لـ **{bidder_name}**. جاري اختيار الحكم..."

        # Advance to next non-passed player
        next_turn = (self.bidding_turn + 1) % 4
        while self.players[next_turn].is_passed_bidding:
            next_turn = (next_turn + 1) % 4
        self.bidding_turn = next_turn
        self.turn_index = next_turn

        return True, msg

    def set_tarneeb_suit(self, suit):
        if self.state != 'SELECT_TRUMP':
            return False, "ليست مرحلة اختيار الطرنيب!"
        if suit not in ['H', 'D', 'S', 'C']:
            return False, "نوع طرنيب غير صالح!"

        self.tarneeb_suit = suit
        self.state = 'PLAYING'
        self.turn_index = self.highest_bidder  # Highest bidder leads 1st card
        sname = SUIT_NAMES_AR.get(suit, suit)
        return True, f"🔥 تم اختيار **{sname}** كحُكم (طرنيب) لهذه الجولة! سيبدأ اللعب **{self.players[self.turn_index].name}**."

    def get_legal_cards(self, seat):
        player = self.players[seat]
        if not self.current_trick or self.lead_suit is None:
            return player.hand.copy()

        # Follow suit rule
        same_suit_cards = [c for c in player.hand if c.suit == self.lead_suit]
        if same_suit_cards:
            return same_suit_cards
        else:
            return player.hand.copy()

    def play_card(self, seat, card):
        if self.state != 'PLAYING':
            return False, "اللعبة ليست في مرحلة اللعب!"
        if self.turn_index != seat:
            return False, "ليس دورك الآن!"

        player = self.players[seat]
        legal_cards = self.get_legal_cards(seat)

        if card not in legal_cards:
            return False, f"حركة غير قانونية! يجب عليك التقيّد بنفس اللون الملعوب ({SUIT_NAMES_AR.get(self.lead_suit, '')}) إذا كان لديك."

        # Execute Card Play
        player.remove_card(card)
        if len(self.current_trick) == 0:
            self.lead_suit = card.suit

        self.current_trick.append((seat, card))

        # Check if trick completed (4 cards)
        if len(self.current_trick) == 4:
            winner_seat = self.evaluate_trick_winner()
            winner_player = self.players[winner_seat]
            if winner_player.team == 1:
                self.round_tricks_t1 += 1
            else:
                self.round_tricks_t2 += 1

            self.turn_index = winner_seat
            self.current_trick = []
            self.lead_suit = None

            # Check if round completed (all 13 cards played)
            if len(self.players[0].hand) == 0:
                return self.evaluate_round_end(winner_player)

            return True, f"✨ أكل الجولة **{winner_player.name}** (فريق {winner_player.team})! دروه الآن للعب البطاقة التالية."

        # Advance to next turn
        self.turn_index = (self.turn_index + 1) % 4
        return True, f"لعب **{player.name}** بطاقة: `{card}`"

    def evaluate_trick_winner(self):
        """
        Determines the seat index of the player who won the 4-card trick.
        """
        winning_seat, winning_card = self.current_trick[0]

        for seat, card in self.current_trick[1:]:
            # Tarneeb (Trump) beats non-Tarneeb
            if card.suit == self.tarneeb_suit and winning_card.suit != self.tarneeb_suit:
                winning_seat, winning_card = seat, card
            elif card.suit == winning_card.suit and card.rank > winning_card.rank:
                winning_seat, winning_card = seat, card

        return winning_seat

    def evaluate_round_end(self, last_winner):
        bidder_team = self.players[self.highest_bidder].team
        tricks_won_bidder = self.round_tricks_t1 if bidder_team == 1 else self.round_tricks_t2
        tricks_won_opp = self.round_tricks_2 if bidder_team == 1 else self.round_tricks_t1

        bid_target = self.current_bid
        bidder_name = self.players[self.highest_bidder].name

        res_msg = f"🏁 **انتهت الجولة الـ 13!**\n"
        res_msg += f"الفريق الطالب (فريق {bidder_team} - {bidder_name}): جمع **{tricks_won_bidder}** أكلات من أصل **{bid_target}** المطلوبة.\n"

        if tricks_won_bidder >= bid_target:
            # Made bid
            pts_bidder = tricks_won_bidder if bid_target < 13 else 26
            pts_opp = (13 - tricks_won_bidder)
            
            if bidder_team == 1:
                self.score_t1 += pts_bidder
                self.score_t2 += pts_opp
            else:
                self.score_t2 += pts_bidder
                self.score_t1 += pts_opp
            res_msg += f"🎉 **نجح الفريق الطالب!** حصل على {pts_bidder} نقطة.\n"
        else:
            # Failed bid (Kabbah/Khassarah)
            penalty = bid_target if bid_target < 13 else 26
            pts_opp = (13 - tricks_won_bidder)
            
            if bidder_team == 1:
                self.score_t1 -= penalty
                self.score_t2 += pts_opp
            else:
                self.score_t2 -= penalty
                self.score_t1 += pts_opp
            res_msg += f"💥 **فشل الفريق الطالب!** خسر {penalty} نقطة.\n"

        res_msg += f"\n🏆 **النتيجة الكلية:**\nالفريق 1: **{self.score_t1}** نقطة | الفريق 2: **{self.score_t2}** نقطة"

        # Check for game winner (target score 31)
        if self.score_t1 >= self.target_score or self.score_t2 >= self.target_score:
            self.state = 'GAME_OVER'
            win_team = 1 if self.score_t1 >= self.target_score else 2
            res_msg += f"\n\n👑 👑 **مبروك! فاز باللعبة الفريق {win_team} بعد الوصول لـ {self.target_score} نقطة!** 👑 👑"
        else:
            self.state = 'ROUND_END'
            self.dealer_index = (self.dealer_index + 1) % 4

        self.last_round_msg = res_msg
        return True, res_msg

    # --------------------------------------------------------------------------
    # AI Decision Making Logic
    # --------------------------------------------------------------------------
    def ai_make_bid(self, seat):
        player = self.players[seat]
        # Evaluate hand strength
        suit_counts = {'H': 0, 'D': 0, 'S': 0, 'C': 0}
        high_card_points = 0
        for c in player.hand:
            suit_counts[c.suit] += 1
            if c.rank >= 13: # Ace or King
                high_card_points += 1

        best_suit_count = max(suit_counts.values())
        estimated_bid = 6 + (best_suit_count // 3) + (high_card_points // 2)

        if estimated_bid > self.current_bid and estimated_bid >= 7:
            return min(estimated_bid, 13)
        return 0  # Pass

    def ai_choose_trump(self, seat):
        player = self.players[seat]
        suit_counts = {'H': 0, 'D': 0, 'S': 0, 'C': 0}
        for c in player.hand:
            suit_counts[c.suit] += 1
        return max(suit_counts, key=suit_counts.get)

    def ai_play_card(self, seat):
        legal = self.get_legal_cards(seat)
        if not legal:
            return player.hand[0]

        # Basic strategy: if starting trick, play high card or tarneeb
        if len(self.current_trick) == 0:
            # Play highest card in hand
            return max(legal, key=lambda c: (c.suit == self.tarneeb_suit, c.rank))
        else:
            # Try to win trick with lowest winning card, or drop lowest useless card
            return min(legal, key=lambda c: c.rank)
