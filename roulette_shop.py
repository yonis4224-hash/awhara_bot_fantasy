"""
Roulette Shop & Points Engine (roulette_shop.py)
Handles points persistence, historical ledger, items purchasing, inventory management, and Discord Shop View.
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
        "desc": "يحميك تلقائياً من أول محاولة طرد موجهة إليك ويتم استهلاكه."
    },
    "double_kick": {
        "name": "طرد ثنائي ⚡",
        "price": 20,
        "desc": "يتيح لك طرد لاعبين اثنين في نفس دورك باللعبة."
    },
    "reverse_kick": {
        "name": "طرد عكسي 🔄",
        "price": 25,
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
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
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
    if uid not in data:
        data[uid] = {
            "points": 0,
            "total_points_earned": 0,
            "total_wins": 0,
            "total_kicks": 0,
            "inventory": {"shield": 0, "double_kick": 0, "reverse_kick": 0}
        }
    
    u = data[uid]
    u["points"] = max(0, u.get("points", 0) + amount)
    if amount > 0:
        u["total_points_earned"] = u.get("total_points_earned", 0) + amount
    save_data(data)
    return u["points"]

def record_kick(user_id):
    uid = str(user_id)
    data = load_data()
    u = data.setdefault(uid, {"points": 0, "total_points_earned": 0, "total_wins": 0, "total_kicks": 0, "inventory": {}})
    u["total_kicks"] = u.get("total_kicks", 0) + 1
    save_data(data)
    return add_points(user_id, 1)

def record_win(user_id):
    uid = str(user_id)
    data = load_data()
    u = data.setdefault(uid, {"points": 0, "total_points_earned": 0, "total_wins": 0, "total_kicks": 0, "inventory": {}})
    u["total_wins"] = u.get("total_wins", 0) + 1
    save_data(data)
    return add_points(user_id, 3)

def get_points(user_id):
    u = get_user_data(user_id)
    return u.get("points", 0)

def buy_item(user_id, item_key):
    if item_key not in ITEMS:
        return False, "العنصر غير موجود بالمتجر!"

    uid = str(user_id)
    data = load_data()
    u = data.get(uid, {"points": 0, "total_points_earned": 0, "total_wins": 0, "total_kicks": 0, "inventory": {}})

    price = ITEMS[item_key]["price"]
    if u.get("points", 0) < price:
        return False, f"ليس لديك نقاط كافية! سعر العنصر **{price}** نقطة ولديك **{u.get('points', 0)}** نقطة."

    u["points"] -= price
    u["inventory"][item_key] = u["inventory"].get(item_key, 0) + 1
    data[uid] = u
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
            description=f"مرحباً <@{self.user.id}>!\n"
                        f"💰 **رصيدك الجاري:** `{pts}` نقطة | 📜 **إجمالي التاريخ:** `{total_pts}` نقطة\n"
                        f"🏆 **الانتصارات:** `{wins}` | 🎯 **الطرد الناجح:** `{kicks}`\n\n"
                        f"**طريقة كسب النقاط:**\n"
                        f"• طرد لاعب في الروليت = **+1 نقطة**\n"
                        f"• الفوز باللعبة = **+3 نقاط**\n",
            color=0xF1C40F
        )

        for key, item in ITEMS.items():
            count = inv.get(key, 0)
            embed.add_field(
                name=f"{item['name']} — 💵 السعر: {item['price']} نقطة",
                value=f"{item['desc']}\n📦 **تمتلك حالياً:** `{count}`",
                inline=False
            )

        embed.set_footer(text="اضغط على الأزرار أدناه لشراء الخواص التي تريدها.")
        return embed

    @discord.ui.button(label="شراء درع (18)", style=discord.ButtonStyle.success, emoji="🛡️")
    async def buy_shield(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذا المتجر لـ شخص آخر!", ephemeral=True)
        ok, msg = buy_item(self.user.id, "shield")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="شراء طرد ثنائي (20)", style=discord.ButtonStyle.primary, emoji="⚡")
    async def buy_double(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذا المتجر لـ شخص آخر!", ephemeral=True)
        ok, msg = buy_item(self.user.id, "double_kick")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="شراء طرد عكسي (25)", style=discord.ButtonStyle.danger, emoji="🔄")
    async def buy_reverse(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذا المتجر لـ شخص آخر!", ephemeral=True)
        ok, msg = buy_item(self.user.id, "reverse_kick")
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="تحديث 🔄", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ هذا المتجر لـ شخص آخر!", ephemeral=True)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
