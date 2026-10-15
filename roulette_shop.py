"""
Roulette Shop & Points Engine (roulette_shop.py)
Handles points persistence, atomic file saving, items purchasing,
inventory management, leaderboard, and Discord Shop View.
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
        "name": "درع ضد الطرد 🛡️",
        "price": 18,
        "emoji": "🛡️",
        "desc": "يحميك تلقائياً من أول محاولة طرد موجهة إليك ويتم استهلاكه."
    },
    "double_kick": {
        "name": "طرد ثنائي ⚡",
        "price": 20,
        "emoji": "⚡",
        "desc": "يتيح لك طرد لاعبين اثنين في نفس دورك باللعبة."
    },
    "reverse_kick": {
        "name": "طرد عكسي 🔄",
        "price": 25,
        "emoji": "🔄",
        "desc": "يعكس ضربة الطرد الموجهة إليك لتطرد اللاعب المهاجم بدلاً منك!"
    }
}

def load_data():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data):
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
            "inventory": {
                "shield": 0,
                "double_kick": 0,
                "reverse_kick": 0
            }
        }
        save_data(data)

    u = data[uid]
    u.setdefault("total_points_earned", u.get("points", 0))
    u.setdefault("total_wins", 0)
    u.setdefault("total_kicks", 0)
    user_inv = u.setdefault("inventory", {})
    for k in ITEMS:
        if k not in user_inv:
            user_inv[k] = 0
    return u

def add_points(user_id, amount):
    uid = str(user_id)
    data = load_data()
    u = data.setdefault(uid, {
        "points": 0,
        "total_points_earned": 0,
        "total_wins": 0,
        "total_kicks": 0,
        "inventory": {"shield": 0, "double_kick": 0, "reverse_kick": 0}
    })

    u["points"] = max(0, u.get("points", 0) + amount)
    if amount > 0:
        u["total_points_earned"] = u.get("total_points_earned", 0) + amount
    save_data(data)
    return u["points"]

def record_kick(user_id):
    uid = str(user_id)
    data = load_data()
    u = data.setdefault(uid, {
        "points": 0,
        "total_points_earned": 0,
        "total_wins": 0,
        "total_kicks": 0,
        "inventory": {"shield": 0, "double_kick": 0, "reverse_kick": 0}
    })
    u["total_kicks"] = u.get("total_kicks", 0) + 1
    u["points"] = u.get("points", 0) + 1
    u["total_points_earned"] = u.get("total_points_earned", 0) + 1
    save_data(data)
    return u["points"]

def record_win(user_id):
    uid = str(user_id)
    data = load_data()
    u = data.setdefault(uid, {
        "points": 0,
        "total_points_earned": 0,
        "total_wins": 0,
        "total_kicks": 0,
        "inventory": {"shield": 0, "double_kick": 0, "reverse_kick": 0}
    })
    u["total_wins"] = u.get("total_wins", 0) + 1
    u["points"] = u.get("points", 0) + 3
    u["total_points_earned"] = u.get("total_points_earned", 0) + 3
    save_data(data)
    return u["points"]

def get_points(user_id):
    u = get_user_data(user_id)
    return u.get("points", 0)

def buy_item(user_id, item_key):
    if item_key not in ITEMS:
        return False, "العنصر غير موجود بالمتجر!"

    uid = str(user_id)
    data = load_data()
    u = data.setdefault(uid, {
        "points": 0,
        "total_points_earned": 0,
        "total_wins": 0,
        "total_kicks": 0,
        "inventory": {"shield": 0, "double_kick": 0, "reverse_kick": 0}
    })

    price = ITEMS[item_key]["price"]
    current_pts = u.get("points", 0)
    if current_pts < price:
        return False, f"ليس لديك نقاط كافية! سعر العنصر **{price}** نقطة ولديك **{current_pts}** نقطة."

    u["points"] = current_pts - price
    inv = u.setdefault("inventory", {})
    inv[item_key] = inv.get(item_key, 0) + 1
    save_data(data)
    item_name = ITEMS[item_key]["name"]
    return True, f"تم شراء **{item_name}** بنجاح! رصيدك المتبقي: **{u['points']}** نقطة."

def has_item(user_id, item_key):
    u = get_user_data(user_id)
    return u.get("inventory", {}).get(item_key, 0) > 0

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
    """Returns top roulette players sorted by points, wins, and kicks."""
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
        total_earned = u.get("total_points_earned", pts)
        if pts > 0 or wins > 0 or kicks > 0 or total_earned > 0:
            users.append({
                "id": user_id,
                "points": pts,
                "total_earned": total_earned,
                "wins": wins,
                "kicks": kicks,
                "score": pts * 2 + wins * 5 + kicks
            })
    users.sort(key=lambda x: (x["points"], x["wins"], x["kicks"]), reverse=True)
    return users[:limit]


class RouletteShopView(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    def build_embed(self):
        u = get_user_data(self.user.id)
        pts = u.get("points", 0)
        total_pts = u.get("total_points_earned", pts)
        wins = u.get("total_wins", 0)
        kicks = u.get("total_kicks", 0)
        inv = u.get("inventory", {})

        embed = discord.Embed(
            title="🏪 متجر وسجل خواص الروليت",
            description=f"مرحباً بك <@{self.user.id}> في متجر الروليت!\n\n"
                        f"💰 **رصيدك الحالي:** `{pts}` نقطة | 📜 **إجمالي ما جمعت:** `{total_pts}` نقطة\n"
                        f"🏆 **الانتصارات الكلية:** `{wins}` | 🎯 **طرد ناجح:** `{kicks}`\n\n"
                        f"**طريقة كسب النقاط:**\n"
                        f"• طرد لاعب في الروليت = **+1 نقطة** 🎯\n"
                        f"• الفوز باللعبة كلياً = **+3 نقاط** 👑\n",
            color=0xF1C40F
        )

        for key, item in ITEMS.items():
            count = inv.get(key, 0)
            embed.add_field(
                name=f"{item['name']} — 💵 السعر: {item['price']} نقطة",
                value=f"{item['desc']}\n📦 **مخزونك الحالي:** `{count}`",
                inline=False
            )

        embed.set_footer(text="اضغط على الأزرار أدناه لشراء الخواص المطلوبة")
        return embed

    @discord.ui.button(label="شراء درع (18)", style=discord.ButtonStyle.success, emoji="🛡️")
    async def buy_shield(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذه القائمة خاصة بمستخدم آخر!", ephemeral=True)
        ok, msg = buy_item(self.user.id, "shield")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="شراء طرد ثنائي (20)", style=discord.ButtonStyle.primary, emoji="⚡")
    async def buy_double(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذه القائمة خاصة بمستخدم آخر!", ephemeral=True)
        ok, msg = buy_item(self.user.id, "double_kick")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="شراء طرد عكسي (25)", style=discord.ButtonStyle.danger, emoji="🔄")
    async def buy_reverse(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذه القائمة خاصة بمستخدم آخر!", ephemeral=True)
        ok, msg = buy_item(self.user.id, "reverse_kick")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="تحديث 🔄", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذه القائمة خاصة بمستخدم آخر!", ephemeral=True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
