"""
Basra Card Game Engine (basra_logic.py)
Handles 52-card deck, matching logic (rank/sum match, Jack/7-Diamonds sweep), Basra detection, card scoring, and AI bot.
"""
import random

SUIT_NAMES_AR = {'H': 'كوبا ♥', 'D': 'ديناري ♦', 'S': '♠ سبيد', 'C': '♣ شيريا'}
RANK_NAMES_AR = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: '10', 9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}

class BasraCard:
    def __init__(self, suit, rank):
        self.suit = suit   # 'H', 'D', 'S', 'C'
        self.rank = rank   # 2..14 (Ace = 14)

    @property
    def value(self):
        # Numeric value for sum combinations
        if self.rank == 14: # Ace
            return 1
        elif 2 <= self.rank <= 10:
            return self.rank
        return 0  # J, Q, K have no sum value

    @property
    def code(self):
        return f"{self.suit}-{self.rank}"

    def __repr__(self):
        return f"{SUIT_NAMES_AR.get(self.suit, self.suit)} {RANK_NAMES_AR.get(self.rank, self.rank)}"

    def __eq__(self, other):
        return isinstance(other, BasraCard) and self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash((self.suit, self.rank))


class BasraDeck:
    def __init__(self):
        self.cards = [BasraCard(s, r) for s in ['H', 'D', 'S', 'C'] for r in range(2, 15)]

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, count):
        drawn = self.cards[:count]
        self.cards = self.cards[count:]
        return drawn


class BasraPlayer:
    def __init__(self, user_id, name, seat_idx, is_ai=False):
        self.user_id = str(user_id)
        self.name = name
        self.seat_idx = seat_idx
        self.is_ai = is_ai
        
        self.hand = []
        self.captured = []
        self.score = 0
        self.basra_count = 0

    def remove_card(self, card):
        for c in self.hand:
            if c == card:
                self.hand.remove(c)
                return True
        return False


class BasraGame:
    def __init__(self, channel_id, target_score=101):
        self.channel_id = channel_id
        self.target_score = target_score
        self.state = 'LOBBY'   # 'LOBBY', 'PLAYING', 'GAME_OVER'
        
        self.players = []
        self.turn_index = 0
        self.ground = []
        self.deck = BasraDeck()
        self.last_eater = None
        self.log_msg = "بدأت لعبة البصرة!"

    def add_player(self, user_id, name):
        if len(self.players) >= 2:
            return False, "طاولة البصرة مكتملة (لاعبين اثنين)!"
        if any(p.user_id == str(user_id) for p in self.players):
            return False, "أنت منضم بالفعل للعبة!"

        seat = len(self.players)
        p = BasraPlayer(user_id, name, seat, is_ai=False)
        self.players.append(p)
        return True, f"انضم **{name}** إلى البصرة (لاعب {seat + 1})"

    def fill_with_ai(self):
        while len(self.players) < 2:
            seat = len(self.players)
            p = BasraPlayer(f"AI_BASRA_{seat}_{random.randint(100,999)}", "الذكاء الاصطناعي 🤖", seat, is_ai=True)
            self.players.append(p)

    def start_game(self):
        if len(self.players) < 2:
            self.fill_with_ai()
            
        self.state = 'PLAYING'
        self.turn_index = 0
        self.deck = BasraDeck()
        self.deck.shuffle()
        
        # Initial Deal: 4 to P1, 4 to P2, 4 to Ground
        self.players[0].hand = self.deck.draw(4)
        self.players[1].hand = self.deck.draw(4)
        self.ground = self.deck.draw(4)
        self.last_eater = None
        self.log_msg = f"بدأت اللعبة! تم توزيع الكروت والأرض. دور **{self.players[0].name}**."

    def get_current_player(self):
        return self.players[self.turn_index]

    def evaluate_card_play(self, played_card):
        """
        Evaluates what cards from ground can be eaten by played_card.
        Returns:
            eaten_cards: list of BasraCard objects eaten from ground
            is_basra: boolean
        """
        # 1. Jack (J - rank 11) or 7 of Diamonds (D-7): Sweeps ALL ground!
        if played_card.rank == 11 or (played_card.suit == 'D' and played_card.rank == 7):
            if not self.ground:
                return [], False
            
            is_basra = False
            # Check Basra condition:
            # - Jack on a single Jack on ground = Basra
            # - Non-Jack (7-Diamonds) on ground = Basra
            if played_card.rank == 11:
                if len(self.ground) == 1 and self.ground[0].rank == 11:
                    is_basra = True
            else:  # 7 of Diamonds
                is_basra = True

            return list(self.ground), is_basra

        # 2. Regular Card Matching (Rank Match & Sum Match)
        if not self.ground:
            return [], False

        eaten = set()
        
        # Rank match: any card on ground with same rank
        for gc in self.ground:
            if gc.rank == played_card.rank:
                eaten.add(gc)

        # Sum match (for numeric cards A..10): find combinations summing to played_card.value
        pv = played_card.value
        if pv > 0:
            numeric_ground = [gc for gc in self.ground if gc.value > 0 and gc not in eaten]
            # Simple subset sum finder
            def find_subsets(target, candidates):
                results = []
                def backtrack(start, current_sum, path):
                    if current_sum == target:
                        results.append(list(path))
                        return
                    if current_sum > target:
                        return
                    for i in range(start, len(candidates)):
                        backtrack(i + 1, current_sum + candidates[i].value, path + [candidates[i]])
                backtrack(0, 0, [])
                return results

            subsets = find_subsets(pv, numeric_ground)
            if subsets:
                for sub in subsets:
                    for gc in sub:
                        eaten.add(gc)

        eaten_list = list(eaten)
        is_basra = False

        if eaten_list:
            # Basra check: if eaten_list clears all cards from ground
            if len(eaten_list) == len(self.ground):
                is_basra = True

        return eaten_list, is_basra

    def play_card(self, seat_idx, card):
        if self.state != 'PLAYING':
            return False, "اللعبة ليست جارية!"
        if self.turn_index != seat_idx:
            return False, "ليس دورك الآن!"

        player = self.players[seat_idx]
        if not player.remove_card(card):
            return False, "البطاقة غير موجودة بيدك!"

        eaten, is_basra = self.evaluate_card_play(card)

        if eaten:
            # Capture eaten cards + played_card
            player.captured.extend(eaten)
            player.captured.append(card)
            self.last_eater = seat_idx
            
            # Remove eaten cards from ground
            self.ground = [gc for gc in self.ground if gc not in eaten]

            if is_basra:
                player.score += 10
                player.basra_count += 1
                msg = f"🎉 **بصرة!** لعب **{player.name}** `{card}` وقش الأرض! (+10 نقاط)"
            else:
                msg = f"✨ أكل **{player.name}** {len(eaten)} كروت لعب بـ `{card}`!"
        else:
            # Drop card to ground
            self.ground.append(card)
            msg = f"رمى **{player.name}** بطاقة `{card}` على الأرض."

        # Check if hands are empty and need redeal
        if not self.players[0].hand and not self.players[1].hand:
            if self.deck.cards:
                self.players[0].hand = self.deck.draw(4)
                self.players[1].hand = self.deck.draw(4)
                msg += " (تم توزيع 4 كروت جديدة لكل لاعب)"
            else:
                # End of Game Round! Calculate Final Scores
                return self.end_game_scoring()

        # Advance Turn
        self.turn_index = (self.turn_index + 1) % 2
        self.log_msg = msg
        return True, msg

    def end_game_scoring(self):
        """Calculates final scores at the end of the deck."""
        # Remaining ground cards go to the last player who captured cards
        if self.ground and self.last_eater is not None:
            self.players[self.last_eater].captured.extend(self.ground)
            self.ground = []

        p1, p2 = self.players[0], self.players[1]
        
        # 1. Majority Cards (+3 pts)
        if len(p1.captured) > len(p2.captured):
            p1.score += 3
        elif len(p2.captured) > len(p1.captured):
            p2.score += 3

        # 2. Special Card Points
        for p in (p1, p2):
            for c in p.captured:
                if c.rank == 14: # Ace
                    p.score += 1
                elif c.suit == 'C' and c.rank == 2: # 2 of Clubs
                    p.score += 2
                elif c.suit == 'D' and c.rank == 10: # 10 of Diamonds
                    p.score += 3

        self.state = 'GAME_OVER'
        winner = p1 if p1.score > p2.score else (p2 if p2.score > p1.score else None)
        if winner:
            msg = f"🏁 **انتهت لعبة البصرة!**\n👑 **الفائز: {winner.name}** بمجموع **{winner.score}** نقطة!\n"
        else:
            msg = f"🏁 **انتهت لعبة البصرة بتعادل متعادل!** ({p1.score} - {p2.score})\n"

        msg += f"• **{p1.name}**: {p1.score} نقطة (جمع {len(p1.captured)} كرت | بصريات: {p1.basra_count})\n"
        msg += f"• **{p2.name}**: {p2.score} نقطة (جمع {len(p2.captured)} كرت | بصريات: {p2.basra_count})"
        
        self.log_msg = msg
        return True, msg

    def ai_play_turn(self):
        """Intelligent AI decision making for Basra."""
        player = self.get_current_player()
        if not player.is_ai or not player.hand or self.state != 'PLAYING':
            return

        best_card = None
        best_score = -1

        for card in player.hand:
            eaten, is_basra = self.evaluate_card_play(card)
            score = len(eaten) * 2
            if is_basra:
                score += 50
            if card.rank == 11 or (card.suit == 'D' and card.rank == 7): # Hold Jack/7D if ground empty
                if not self.ground:
                    score = -10
            if score > best_score:
                best_score = score
                best_card = card

        if not best_card:
            best_card = player.hand[0]

        self.play_card(player.seat_idx, best_card)
