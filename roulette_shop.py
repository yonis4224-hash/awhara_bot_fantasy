"""
Roulette Shop & Points Engine (roulette_shop.py)
واجهة متجر نظيفة ومخفية (Ephemeral) لا تظهر إلا لصاحبها.
"""
import os
import json
import discord
from discord.ui import View, Button

DATA_PATH = os.path.join("src", "data", "roulette_shop.json")
if not os.path.exists(os.path.dirname(DATA_PATH)):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

ITEMS = {
    "shield": {
        "name": "درع ضد الطرد",
        "price": 18,
        "emoji": "🛡️",
        "desc": "يحميك تلقائياً لمرة واحدة من الطرد."
    },
    "reverse_kick": {
        "name": "طرد عكسي",
        "price": 22,
        "emoji": "🔄",
        "desc": "يعكس الطرد على المهاجم ويمنحك نقطة."
    },
    "double_kick": {
        "name": "طرد ثنائي",
        "price": 25,
        "emoji": "⚡",
        "desc": "يطرد لاعبين اثنين في دورك."
    }
}

_CACHE = None

def load_data():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not os.path.exists(DATA_PATH):
        _CACHE = {}
        return _CACHE
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
            return _CACHE
    except Exception:
        _CACHE = {}
        return _CACHE

def save_data(data):
    global _CACHE
    _CACHE = data
    try:
        temp_path = DATA_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, DATA_PATH)
    except Exception as e:
        print(f"Error saving roulette_shop data: {e}")

def get_user_data(user_id):
    uid = str(user_id)
    data = load_data()
    if uid not in data:
        data[uid] = {
            "points": 0,
            "total_points_earned": 0,
            "total_wins": 0,
            "total_kicks": 0,
            "inventory": {"shield": 0, "double_kick": 0, "reverse_kick": 0}
        }
        save_data(data)

    u = data[uid]
    u.setdefault("total_points_earned", u.get("points", 0))
    u.setdefault("total_wins", 0)
    u.setdefault("total_kicks", 0)
    user_inv = u.setdefault("inventory", {})
    for k in ITEMS:
        user_inv.setdefault(k, 0)
    return u

def add_points(user_id, amount):
    uid = str(user_id)
    data = load_data()
    u = get_user_data(uid)
    u["points"] = max(0, u.get("points", 0) + amount)
    if amount > 0:
        u["total_points_earned"] = u.get("total_points_earned", 0) + amount
    save_data(data)
    return u["points"]

def record_kick(user_id):
    uid = str(user_id)
    data = load_data()
    u = get_user_data(uid)
    u["total_kicks"] = u.get("total_kicks", 0) + 1
    u["points"] = u.get("points", 0) + 1
    u["total_points_earned"] = u.get("total_points_earned", 0) + 1
    save_data(data)
    return u["points"]

def record_win(user_id):
    uid = str(user_id)
    data = load_data()
    u = get_user_data(uid)
    u["total_wins"] = u.get("total_wins", 0) + 1
    u["points"] = u.get("points", 0) + 3
    u["total_points_earned"] = u.get("total_points_earned", 0) + 3
    save_data(data)
    return u["points"]

def get_points(user_id):
    return get_user_data(user_id).get("points", 0)

def buy_item(user_id, item_key):
    if item_key not in ITEMS:
        return False, "❌ العنصر غير موجود."

    uid = str(user_id)
    data = load_data()
    u = get_user_data(uid)
    price = ITEMS[item_key]["price"]
    current_pts = u.get("points", 0)

    if current_pts < price:
        return False, f"❌ رصيدك غير كافٍ (`{current_pts}/{price}` نقطة)."

    u["points"] = current_pts - price
    inv = u.setdefault("inventory", {})
    inv[item_key] = inv.get(item_key, 0) + 1
    save_data(data)
    return True, f"✅ اشتريت **{ITEMS[item_key]['name']}**! رصيدك المتبقي: `{u['points']}` نقطة."

def has_item(user_id, item_key):
    return get_user_data(user_id).get("inventory", {}).get(item_key, 0) > 0

def use_item(user_id, item_key):
    uid = str(user_id)
    data = load_data()
    if uid in data:
        inv = data[uid].get("inventory", {})
        if inv.get(item_key, 0) > 0:
            inv[item_key] -= 1
            save_data(data)
            return True
    return False

def get_leaderboard(limit=10):
    data = load_data()
    users = []
    for uid, u in data.items():
        try:
            user_id = int(uid)
        except ValueError:
            continue
        pts = u.get("points", 0)
        wins = u.get("total_wins", 0)
        kicks = u.get("total_kicks", 0)
        if pts > 0 or wins > 0 or kicks > 0:
            users.append({"id": user_id, "points": pts, "wins": wins, "kicks": kicks})
    users.sort(key=lambda x: (x["wins"], x["kicks"], x["points"]), reverse=True)
    return users[:limit]


class RouletteShopView(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    def build_embed(self):
        u = get_user_data(self.user.id)
        pts = u.get("points", 0)
        wins = u.get("total_wins", 0)
        kicks = u.get("total_kicks", 0)
        inv = u.get("inventory", {})

        desc = (
            f"💰 **رصيدك:** `{pts}` نقطة  |  🏆 **الفوز:** `{wins}`  |  🎯 **الطرد:** `{kicks}`\n"
            f"────────────────────────\n"
            f"🛡️ **درع ضد الطرد (18)** — تملك: `{inv.get('shield', 0)}`\n"
            f"🔄 **طرد عكسي (22)** — تملك: `{inv.get('reverse_kick', 0)}`\n"
            f"⚡ **طرد ثنائي (25)** — تملك: `{inv.get('double_kick', 0)}`"
        )
        return discord.Embed(title="🏪 متجر وحقيبة الروليت (خاص بك)", description=desc, color=0xF1C40F)

    @discord.ui.button(label="درع (18)", style=discord.ButtonStyle.success, emoji="🛡️")
    async def buy_shield(self, interaction: discord.Interaction, button: Button):
        ok, msg = buy_item(interaction.user.id, "shield")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="عكسي (22)", style=discord.ButtonStyle.danger, emoji="🔄")
    async def buy_reverse(self, interaction: discord.Interaction, button: Button):
        ok, msg = buy_item(interaction.user.id, "reverse_kick")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="ثنائي (25)", style=discord.ButtonStyle.primary, emoji="⚡")
    async def buy_double(self, interaction: discord.Interaction, button: Button):
        ok, msg = buy_item(interaction.user.id, "double_kick")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)