"""
Bank Al-Haz (Monopoly) Game Engine (bank_logic.py)
Handles board tiles definitions, player state, movement, property purchases, rent, chance cards, jail, and AI decisions.
"""
import random

INITIAL_BALANCE = 1500
START_BONUS = 200
JAIL_TILE = 6
GO_TO_JAIL_TILE = 18
JAIL_BAIL = 50

CHANCE_CARDS = [
    {"desc": "🎉 ربحت جائزة يانصيب! احصل على +150 جنيه", "type": "money", "val": 150},
    {"desc": "🔧 دفعت رسوم صيانة: خصم -50 جنيه", "type": "money", "val": -50},
    {"desc": "🎂 عيد ميلادك! احصل على +100 جنيه من البنك", "type": "money", "val": 100},
    {"desc": "🚔 غرامة مخالفة مرورية: خصم -70 جنيه", "type": "money", "val": -70},
    {"desc": "🏃 تقدم 3 خطوات للأمام!", "type": "move", "val": 3},
    {"desc": "↩️ ارجع خطوتين للخلف!", "type": "move", "val": -2},
]

DEFAULT_TILES = [
    {"id": 0, "name": "🏁 البداية", "type": "start", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 1, "name": "الجيزة", "type": "city", "price": 60, "base_rent": 10, "group": "brown", "owner": None, "level": 0},
    {"id": 2, "name": "🎲 كارت حظ", "type": "chance", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 3, "name": "مصر الجديدة", "type": "city", "price": 80, "base_rent": 15, "group": "brown", "owner": None, "level": 0},
    {"id": 4, "name": "💸 ضريبة دخل", "type": "tax", "price": 100, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 5, "name": "محطة القطار", "type": "utility", "price": 150, "base_rent": 30, "group": "special", "owner": None, "level": 0},
    {"id": 6, "name": "🚓 السجن", "type": "jail", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 7, "name": "طنطا", "type": "city", "price": 100, "base_rent": 20, "group": "cyan", "owner": None, "level": 0},
    {"id": 8, "name": "المنصورة", "type": "city", "price": 120, "base_rent": 25, "group": "cyan", "owner": None, "level": 0},
    {"id": 9, "name": "شركة الكهرباء", "type": "utility", "price": 150, "base_rent": 30, "group": "special", "owner": None, "level": 0},
    {"id": 10, "name": "الزقازيق", "type": "city", "price": 140, "base_rent": 30, "group": "pink", "owner": None, "level": 0},
    {"id": 11, "name": "شبين الكوم", "type": "city", "price": 160, "base_rent": 35, "group": "pink", "owner": None, "level": 0},
    {"id": 12, "name": "🅿️ موقف مجاني", "type": "rest", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 13, "name": "الإسكندرية", "type": "city", "price": 180, "base_rent": 40, "group": "orange", "owner": None, "level": 0},
    {"id": 14, "name": "🎲 كارت حظ", "type": "chance", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 15, "name": "مرسى مطروح", "type": "city", "price": 200, "base_rent": 45, "group": "orange", "owner": None, "level": 0},
    {"id": 16, "name": "بورسعيد", "type": "city", "price": 220, "base_rent": 50, "group": "red", "owner": None, "level": 0},
    {"id": 17, "name": "شركة المياه", "type": "utility", "price": 150, "base_rent": 30, "group": "special", "owner": None, "level": 0},
    {"id": 18, "name": "🚨 اذهب للسجن", "type": "go_jail", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 19, "name": "القاهرة", "type": "city", "price": 260, "base_rent": 60, "group": "green", "owner": None, "level": 0},
    {"id": 20, "name": "خان الخليلي", "type": "city", "price": 280, "base_rent": 65, "group": "green", "owner": None, "level": 0},
    {"id": 21, "name": "🎲 كارت حظ", "type": "chance", "price": 0, "base_rent": 0, "group": "special", "owner": None, "level": 0},
    {"id": 22, "name": "أسوان", "type": "city", "price": 350, "base_rent": 80, "group": "blue", "owner": None, "level": 0},
    {"id": 23, "name": "الأقصر", "type": "city", "price": 400, "base_rent": 100, "group": "blue", "owner": None, "level": 0},
]


class BankPlayer:
    def __init__(self, user_id, name, seat_idx, is_ai=False):
        self.user_id = str(user_id)
        self.name = name
        self.seat_idx = seat_idx
        self.is_ai = is_ai
        
        self.balance = INITIAL_BALANCE
        self.position = 0
        self.in_jail = False
        self.jail_turns = 0
        self.bankrupt = False

    def add_money(self, amount):
        self.balance += amount
        if self.balance < 0:
            self.balance = 0
            self.bankrupt = True

    def deduct_money(self, amount):
        self.balance -= amount
        if self.balance < 0:
            self.bankrupt = True


class BankGame:
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.state = 'LOBBY'   # 'LOBBY', 'PLAYING', 'GAME_OVER'
        
        self.players = []
        self.turn_index = 0
        self.tiles = [dict(t) for t in DEFAULT_TILES]
        
        self.last_dice = (0, 0)
        self.log_msg = "بدأت اللعبة! انضم وانطلق لجمع الثروة."
        self.can_roll = True
        self.can_buy = False
        self.can_build = False

    def add_player(self, user_id, name):
        if len(self.players) >= 4:
            return False, "طاولة بنك الحظ مكتملة (4 لاعبين)!"
        if any(p.user_id == str(user_id) for p in self.players):
            return False, "أنت منضم بالفعل للعبة!"

        seat = len(self.players)
        p = BankPlayer(user_id, name, seat, is_ai=False)
        self.players.append(p)
        return True, f"انضم **{name}** إلى بنk الحظ (لاعب {seat + 1})"

    def fill_with_ai(self):
        ai_count = 1
        while len(self.players) < 4:
            seat = len(self.players)
            p = BankPlayer(f"AI_BANK_{seat}_{random.randint(100,999)}", f"تاجر آل {ai_count}", seat, is_ai=True)
            self.players.append(p)
            ai_count += 1

    def replace_with_ai(self, user_id):
        """تسجيل مغادرة لاعب أثناء اللعب واستبداله ببوت AI (يحافظ على مقعده وماله وعقاراته)"""
        uid = str(user_id)
        target = next((p for p in self.players if p.user_id == uid), None)
        if not target:
            return False, "أنت لست لاعباً في هذه الطاولة!"
        if target.is_ai:
            return False, "هذا المقعد بوت بالفعل!"

        old_name = target.name
        was_current = self.get_current_player() is target
        target.is_ai = True
        target.name = f"بوت (بديل {old_name[:8]})"
        target.user_id = f"AI_BANK_LEAVE_{random.randint(100, 999)}"

        msg = f"🚪 غادر **{old_name}** وتم استبداله بـ AI لمواصلة اللعب!"
        # If the leaving player was mid-turn and bankrupt, advance to the next active player
        if was_current and target.bankrupt:
            self.end_turn()
        if self.state == 'PLAYING':
            self.log_msg = msg
        return True, msg

    def start_game(self):
        if len(self.players) < 2:
            self.fill_with_ai()
        self.state = 'PLAYING'
        self.turn_index = 0
        self.can_roll = True
        self.can_buy = False
        self.can_build = False
        self.log_msg = f"بدأت اللعبة! دور **{self.players[0].name}** لرمي النرد."

    def get_current_player(self):
        return self.players[self.turn_index]

    def roll_dice(self):
        player = self.get_current_player()
        if not self.can_roll:
            return False, "لقد رميت النرد بالفعل في هذا الدور!"

        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.last_dice = (d1, d2)
        total_steps = d1 + d2

        # Check Jail state
        if player.in_jail:
            if d1 == d2:
                player.in_jail = False
                player.jail_turns = 0
                self.log_msg = f"🎉 **{player.name}** حصل على رمية مضاعفة ({d1},{d2}) وخرج من السجن!"
            else:
                player.jail_turns += 1
                if player.jail_turns >= 3:
                    player.deduct_money(JAIL_BAIL)
                    player.in_jail = False
                    player.jail_turns = 0
                    self.log_msg = f"🚓 **{player.name}** قضى 3 أدوار ودفع كفالة 50ج واستعاد حريته!"
                else:
                    self.can_roll = False
                    self.log_msg = f"🔒 **{player.name}** لم يحصل على مضاعف وما زال في السجن ({player.jail_turns}/3)."
                    return True, self.log_msg

        # Move Player
        old_pos = player.position
        new_pos = (old_pos + total_steps) % len(self.tiles)
        player.position = new_pos

        # Check Pass START bonus (+200 EGP)
        passed_start = (old_pos + total_steps) >= len(self.tiles)
        if passed_start:
            player.add_money(START_BONUS)
            start_txt = " مر بالبداية وحصل على +200ج!"
        else:
            start_txt = ""

        self.can_roll = False
        tile = self.tiles[new_pos]

        # Handle Tile Effects
        msg = self.handle_tile_landing(player, tile, start_txt)
        return True, msg

    def handle_tile_landing(self, player, tile, start_txt=""):
        t_type = tile["type"]
        t_name = tile["name"]

        if t_type == "city" or t_type == "utility":
            owner_idx = tile["owner"]
            if owner_idx is None:
                self.can_buy = (player.balance >= tile["price"])
                return f"وصل **{player.name}** إلى **{t_name}**{start_txt}. يمكن شراؤها بـ {tile['price']}ج!"
            elif owner_idx == player.seat_idx:
                upgrade_cost = int(tile["price"] * 0.5)
                self.can_build = (player.balance >= upgrade_cost and tile["level"] < 4)
                return f"وصل **{player.name}** إلى مدينته **{t_name}**{start_txt}."
            else:
                # Pay Rent to Owner
                owner = self.players[owner_idx]
                rent = tile["base_rent"] * (1 + tile["level"] * 1.5)
                rent = int(rent)
                player.deduct_money(rent)
                owner.add_money(rent)
                self.check_bankruptcy(player)
                return f"وصل **{player.name}** إلى **{t_name}** ملك **{owner.name}**{start_txt}. دفع إيجار {rent}ج!"

        elif t_type == "chance":
            card = random.choice(CHANCE_CARDS)
            if card["type"] == "money":
                if card["val"] > 0:
                    player.add_money(card["val"])
                else:
                    player.deduct_money(abs(card["val"]))
                    self.check_bankruptcy(player)
            elif card["type"] == "move":
                player.position = (player.position + card["val"]) % len(self.tiles)
            return f"🎲 كارت حظ لـ **{player.name}**: {card['desc']}{start_txt}"

        elif t_type == "tax":
            player.deduct_money(tile["price"])
            self.check_bankruptcy(player)
            return f"💸 دفع **{player.name}** ضريبة بقيمة {tile['price']}ج{start_txt}."

        elif t_type == "go_jail":
            player.position = JAIL_TILE
            player.in_jail = True
            player.jail_turns = 0
            return f"🚨 اذهب للسجن! تم نقل **{player.name}** للمحبس."

        return f"وصل **{player.name}** إلى **{t_name}**{start_txt}."

    def buy_current_property(self):
        player = self.get_current_player()
        tile = self.tiles[player.position]

        if not self.can_buy or tile["owner"] is not None:
            return False, "لا يمكن شراء هذا العقار!"

        if player.balance < tile["price"]:
            return False, "ليس لديك رصيد كافٍ!"

        player.deduct_money(tile["price"])
        tile["owner"] = player.seat_idx
        self.can_buy = False
        self.log_msg = f"🏠 اشترى **{player.name}** عقار **{tile['name']}** بسعر {tile['price']}ج!"
        return True, self.log_msg

    def upgrade_current_property(self):
        player = self.get_current_player()
        tile = self.tiles[player.position]

        if tile["owner"] != player.seat_idx or tile["level"] >= 4:
            return False, "لا يمكن تطوير هذا العقار!"

        cost = int(tile["price"] * 0.5)
        if player.balance < cost:
            return False, "ليس لديك رصيد كافٍ للبناء!"

        player.deduct_money(cost)
        tile["level"] += 1
        self.can_build = False
        self.log_msg = f"🏗️ طور **{player.name}** عقار **{tile['name']}** إلى المستوى {tile['level']} (تكلفة {cost}ج)!"
        return True, self.log_msg

    def pay_jail_bail(self):
        player = self.get_current_player()
        if not player.in_jail:
            return False, "أنت لست في السجن!"

        if player.balance < JAIL_BAIL:
            return False, "ليس لديك رصيد كافٍ لدف الكفالة (50ج)!"

        player.deduct_money(JAIL_BAIL)
        player.in_jail = False
        player.jail_turns = 0
        self.log_msg = f"💵 دفع **{player.name}** كفالة 50ج وخرج من السجن!"
        return True, self.log_msg

    def check_bankruptcy(self, player):
        if player.balance <= 0:
            player.bankrupt = True
            # Release player's properties
            for t in self.tiles:
                if t["owner"] == player.seat_idx:
                    t["owner"] = None
                    t["level"] = 0

            # Check remaining active players
            active = [p for p in self.players if not p.bankrupt]
            if len(active) == 1:
                self.state = 'GAME_OVER'
                self.log_msg = f"👑 **أفلس جميع اللاعبين وفاز {active[0].name} بـ بنك الحظ!** 👑"

    def end_turn(self):
        active_players = [p for p in self.players if not p.bankrupt]
        if len(active_players) <= 1:
            self.state = 'GAME_OVER'
            return

        # Move to next non-bankrupt player
        while True:
            self.turn_index = (self.turn_index + 1) % len(self.players)
            if not self.players[self.turn_index].bankrupt:
                break

        self.can_roll = True
        self.can_buy = False
        self.can_build = False
        self.log_msg = f"الدور الآن على **{self.players[self.turn_index].name}**"

    # AI Turn Decision
    def ai_play_turn(self):
        player = self.get_current_player()
        if not player.is_ai or player.bankrupt:
            return

        if player.in_jail and player.balance >= JAIL_BAIL + 100:
            self.pay_jail_bail()

        if self.can_roll:
            self.roll_dice()

        tile = self.tiles[player.position]
        if self.can_buy and player.balance >= tile["price"] + 150:
            self.buy_current_property()
        elif self.can_build and player.balance >= int(tile["price"] * 0.5) + 100:
            self.upgrade_current_property()

        self.end_turn()
