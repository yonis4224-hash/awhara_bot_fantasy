import os
import logging
import asyncio
import random
import math
import time

from roulette_gif import make_gif, download_avatar
from roulette_shop import (
    RouletteShopView, get_user_data, add_points, get_points,
    buy_item, has_item, use_item, ITEMS, record_kick, record_win
)

import discord
from discord.ext import commands
from discord.ui import View, Select

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['.', '!', '؟', '_'], intents=intents, help_command=None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("ohara_templates")

# ------------------------------------------------------------------------------
# الثوابت: معرفات الرومات والتاغات
# ------------------------------------------------------------------------------
CHANNEL_MOVIES = 1528554012612235374
CHANNEL_FOOTBALL = 1528793852222374140
CHANNEL_ANIME = 1528793894115086527
CHANNEL_GIRLS = 1532091198960042044
CHANNEL_GAMES = 1532091509812236420
GAME_CHANNEL = 1528566822935330989

TAG_MOVIES = "<@&1520098176269418647> <@&1509890356773130352>"
TAG_FOOTBALL = "<@&1509890421168279645>"
TAG_ANIME = "<@&1509890302415081492>"
TAG_GIRLS = ""
TAG_GAMES = ""

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━\n"

def t(title, fields, tags):
    text = f"**```{title}  ```**\n\n"
    text += "\n\n".join(f"{f} :  " for f in fields)
    if tags:
        text += f"\n\n{SEP}{tags}**"
    else:
        text += f"\n\n{SEP}"
    return text

def tm(title, fields):
    return t(title, fields, TAG_MOVIES)

def tf(title, fields):
    return t(title, fields, TAG_FOOTBALL)

def ta(title, fields):
    return t(title, fields, TAG_ANIME)

def tgirl(title, fields):
    return t(title, fields, TAG_GIRLS)

def tgame(title, fields):
    return t(title, fields, TAG_GAMES)

# ------------------------------------------------------------------------------
# ديباجات الأفلام والمسلسلات
# ------------------------------------------------------------------------------
T_MOVIES = {
    "1": tm("📖 قصة فلم/مسلسل", ["الاسم", "القصة", "الموسم/الحلقات", "التقييم"]),
    "2": tm("📰 خبر فلم/مسلسل", ["الاسم", "الخبر", "المصدر", "التاريخ"]),
    "3": tm("📢 إعلان فلم/مسلسل", ["الاسم", "الإعلان", "تاريخ الإصدار"]),
    "4": tm("📊 تصويت فلم/مسلسل", ["الاسم", "الخيار الأول", "الخيار الثاني"]),
    "5": tm("📺 مشاهدة فلم/مسلسل", ["الاسم", "الساعة", "عدد الحلقات", "اليوم"]),
    "6": tm("📝 مراجعة فلم/مسلسل", ["الاسم", "التقييم /10", "الإيجابيات", "السلبيات", "الخلاصة"]),
    "7": tm("💡 توصية فلم/مسلسل", ["الاسم", "النوع", "لماذا يستحق المشاهدة", "يناسب عشاق"]),
    "8": tm("💬 سؤال نقاش", ["السؤال", "تفاصيل أكثر", "ما رأيكم"]),
    "9": tm("🧵 نظرية أو توقع", ["العمل", "النظرية/التوقع", "الأدلة", "ما رأيكم بهذه النظرية"]),
    "10": tm("⚖️ مقارنة", ["العمل الأول", "العمل الثاني", "وجه المقارنة", "الأفضل برأيك"]),
    "11": tm("🎭 شخصية اليوم", ["اسم الشخصية", "من العمل", "سبب الاختيار", "أقوى صفاتها", "اقتباسها الشهير"]),
    "12": tm("💬 اقتباس", ["النص", "القائل", "من العمل", "تعليقك"]),
    "13": tm("🏆 مسابقة ثقافية", ["السؤال", "1.", "2.", "3.", "4.", "الجائزة", "المدة"]),
    "14": tm("📋 استفتاء الموسم", ["العمل", "السؤال", "نعم", "لا", "ما عندي رأي"]),
    "15": tm("👥 مشاهدة جماعية", ["العمل", "الموعد", "المكان", "المدة التقريبية", "التسجيلات المتاحة"]),
}

TITLES_MOVIES = {
    "1": "📖 قصة فلم/مسلسل", "2": "📰 خبر فلم/مسلسل", "3": "📢 إعلان فلم/مسلسل",
    "4": "📊 تصويت فلم/مسلسل", "5": "📺 مشاهدة فلم/مسلسل", "6": "📝 مراجعة فلم/مسلسل",
    "7": "💡 توصية", "8": "💬 سؤال نقاش", "9": "🧵 نظرية أو توقع",
    "10": "⚖️ مقارنة", "11": "🎭 شخصية اليوم", "12": "💬 اقتباس",
    "13": "🏆 مسابقة ثقافية", "14": "📋 استفتاء الموسم", "15": "👥 مشاهدة جماعية",
}

# ------------------------------------------------------------------------------
# ديباجات الكورة
# ------------------------------------------------------------------------------
T_FOOTBALL = {
    "1": tf("📰 خبر مباراة", ["الفريق", "الخبر", "المصدر", "التاريخ"]),
    "2": tf("✅ نتيجة مباراة", ["الفريق الأول", "الفريق الثاني", "النتيجة", "نجم المباراة"]),
    "3": tf("📢 إعلان مباراة", ["المباراة", "التاريخ", "الوقت", "الملعب"]),
    "4": tf("📊 تصويت", ["الموضوع", "الخيار الأول", "الخيار الثاني"]),
    "5": tf("📺 مشاهدة مباراة", ["المباراة", "التاريخ", "الساعة", "القناة الناقلة"]),
    "6": tf("📝 مراجعة مباراة", ["المباراة", "التقييم /10", "الإيجابيات", "السلبيات", "الخلاصة"]),
    "7": tf("💡 توصية", ["المباراة", "البطولة", "لماذا تستحق المشاهدة", "تناسب عشاق"]),
    "8": tf("💬 سؤال نقاش", ["السؤال", "تفاصيل أكثر", "ما رأيكم"]),
    "9": tf("🔮 توقع", ["المباراة", "التوقع", "الأسباب", "هل تتفق"]),
    "10": tf("⚖️ مقارنة", ["اللاعب الأول", "اللاعب الثاني", "وجه المقارنة", "الأفضل برأيك"]),
    "11": tf("🎭 لاعب اليوم", ["اسم اللاعب", "النادي", "الأداء", "إحصائياته"]),
    "12": tf("💬 اقتباس", ["النص", "القائل", "المناسبة", "تعليقك"]),
    "13": tf("🏆 مسابقة", ["السؤال", "1.", "2.", "3.", "4.", "الجائزة", "المدة"]),
    "14": tf("📋 استفتاء", ["الموضوع", "السؤال", "نعم", "لا", "ما عندي رأي"]),
    "15": tf("👥 مشاهدة جماعية", ["المباراة", "الموعد", "المكان", "المدة", "التسجيلات"]),
}

TITLES_FOOTBALL = {
    "1": "📰 خبر مباراة", "2": "✅ نتيجة مباراة", "3": "📢 إعلان مباراة",
    "4": "📊 تصويت", "5": "📺 مشاهدة مباراة", "6": "📝 مراجعة مباراة",
    "7": "💡 توصية", "8": "💬 سؤال نقاش", "9": "🔮 توقع",
    "10": "⚖️ مقارنة", "11": "🎭 لاعب اليوم", "12": "💬 اقتباس",
    "13": "🏆 مسابقة", "14": "📋 استفتاء", "15": "👥 مشاهدة جماعية",
}

# ------------------------------------------------------------------------------
# ديباجات الانمي
# ------------------------------------------------------------------------------
T_ANIME = {
    "1": ta("📖 قصة انمي", ["الاسم", "القصة", "عدد الحلقات", "التقييم"]),
    "2": ta("📰 خبر انمي", ["الاسم", "الخبر", "المصدر", "التاريخ"]),
    "3": ta("📢 إعلان انمي", ["الاسم", "الإعلان", "تاريخ الإصدار"]),
    "4": ta("📊 تصويت انمي", ["الاسم", "الخيار الأول", "الخيار الثاني"]),
    "5": ta("📺 مشاهدة انمي", ["الاسم", "الساعة", "الحلقة", "اليوم"]),
    "6": ta("📝 مراجعة انمي", ["الاسم", "التقييم /10", "الإيجابيات", "السلبيات", "الخلاصة"]),
    "7": ta("💡 توصية انمي", ["الاسم", "النوع", "لماذا يستحق المشاهدة", "يناسب عشاق"]),
    "8": ta("💬 سؤال نقاش", ["السؤال", "تفاصيل أكثر", "ما رأيكم"]),
    "9": ta("🧵 نظرية انمي", ["العمل", "النظرية/التوقع", "الأدلة", "ما رأيكم بهذه النظرية"]),
    "10": ta("⚖️ مقارنة", ["الانمي الأول", "الانمي الثاني", "وجه المقارنة", "الأفضل برأيك"]),
    "11": ta("🎭 شخصية اليوم", ["اسم الشخصية", "من الانمي", "سبب الاختيار", "أقوى صفاتها", "اقتباسها الشهير"]),
    "12": ta("💬 اقتباس", ["النص", "القائل", "من العمل", "تعليقك"]),
    "13": ta("🏆 مسابقة انمي", ["السؤال", "1.", "2.", "3.", "4.", "الجائزة", "المدة"]),
    "14": ta("📋 استفتاء انمي", ["العمل", "السؤال", "نعم", "لا", "ما عندي رأي"]),
    "15": ta("👥 مشاهدة جماعية", ["العمل", "الموعد", "المكان", "المدة التقريبية", "التسجيلات"]),
}

TITLES_ANIME = {
    "1": "📖 قصة انمي", "2": "📰 خبر انمي", "3": "📢 إعلان انمي",
    "4": "📊 تصويت انمي", "5": "📺 مشاهدة انمي", "6": "📝 مراجعة انمي",
    "7": "💡 توصية", "8": "💬 سؤال نقاش", "9": "🧵 نظرية انمي",
    "10": "⚖️ مقارنة", "11": "🎭 شخصية اليوم", "12": "💬 اقتباس",
    "13": "🏆 مسابقة انمي", "14": "📋 استفتاء انمي", "15": "👥 مشاهدة جماعية",
}

# ------------------------------------------------------------------------------
# ديباجات الفتيات
# ------------------------------------------------------------------------------
T_GIRLS = {
    "1": tgirl("📰 خبر بنات", ["العنوان", "الخبر", "المصدر", "التاريخ"]),
    "2": tgirl("🎉 فعالية", ["اسم الفعالية", "التاريخ", "الوقت", "المكان", "التفاصيل"]),
    "3": tgirl("📢 إعلان", ["العنوان", "الإعلان", "تاريخ الإصدار"]),
    "4": tgirl("📊 تصويت", ["الموضوع", "الخيار الأول", "الخيار الثاني"]),
    "5": tgirl("🎯 نشاط", ["اسم النشاط", "الوقت", "المكان", "الشروط"]),
    "6": tgirl("🏆 مسابقة", ["السؤال", "1.", "2.", "3.", "4.", "الجائزة", "المدة"]),
    "7": tgirl("💡 توصية", ["العنوان", "لماذا نوصي به", "يناسب"]),
    "8": tgirl("💬 سؤال نقاش", ["السؤال", "تفاصيل أكثر", "ما رأيكم"]),
    "9": tgirl("💡 اقتراح", ["الاقتراح", "الفكرة", "فوائده"]),
    "10": tgirl("📋 استفتاء", ["الموضوع", "نعم", "لا", "ما عندي رأي"]),
    "11": tgirl("👑 عضوة الأسبوع", ["الاسم", "سبب الاختيار", "إنجازاتها", "كلمة لها"]),
    "12": tgirl("💬 اقتباس", ["النص", "القائل", "التعليق"]),
    "13": tgirl("📌 تحديث", ["العنوان", "التفاصيل", "آخر المستجدات"]),
    "14": tgirl("🎤 فقرة", ["اسم الفقرة", "الوقت", "المقدمة", "الموعد"]),
    "15": tgirl("📅 موعد", ["المناسبة", "التاريخ", "الوقت", "المكان", "ملاحظات"]),
}

TITLES_GIRLS = {
    "1": "📰 خبر بنات", "2": "🎉 فعالية", "3": "📢 إعلان",
    "4": "📊 تصويت", "5": "🎯 نشاط", "6": "🏆 مسابقة",
    "7": "💡 توصية", "8": "💬 سؤال نقاش", "9": "💡 اقتراح",
    "10": "📋 استفتاء", "11": "👑 عضوة الأسبوع", "12": "💬 اقتباس",
    "13": "📌 تحديث", "14": "🎤 فقرة", "15": "📅 موعد",
}

# ------------------------------------------------------------------------------
# ديباجات الألعاب
# ------------------------------------------------------------------------------
T_GAMES = {
    "1": tgame("📰 خبر لعبة", ["اللعبة", "الخبر", "المصدر", "التاريخ"]),
    "2": tgame("📝 مراجعة لعبة", ["اللعبة", "التقييم /10", "الإيجابيات", "السلبيات", "الخلاصة"]),
    "3": tgame("📢 إعلان لعبة", ["اللعبة", "المطور", "تاريخ الإصدار", "المنصات"]),
    "4": tgame("📊 تصويت", ["الموضوع", "الخيار الأول", "الخيار الثاني"]),
    "5": tgame("📌 تحديث لعبة", ["اللعبة", "التحديث", "التفاصيل", "حجم التحديث"]),
    "6": tgame("⚖️ مقارنة", ["اللعبة الأولى", "اللعبة الثانية", "وجه المقارنة", "الأفضل برأيك"]),
    "7": tgame("💡 توصية لعبة", ["اللعبة", "النوع", "لماذا تستحق التجربة", "منصات التشغيل"]),
    "8": tgame("💬 سؤال نقاش", ["السؤال", "تفاصيل أكثر", "ما رأيكم"]),
    "9": tgame("🔮 توقع", ["اللعبة", "التوقع", "الأسباب", "هل تتفق"]),
    "10": tgame("🏆 إنجاز", ["اللاعب", "اللعبة", "الإنجاز", "الصعوبة"]),
    "11": tgame("🎭 شخصية اللعبة", ["الشخصية", "من اللعبة", "سبب التميز", "أقوى مهاراتها"]),
    "12": tgame("💬 اقتباس", ["النص", "القائل", "اللعبة", "تعليقك"]),
    "13": tgame("🏆 مسابقة", ["السؤال", "1.", "2.", "3.", "4.", "الجائزة", "المدة"]),
    "14": tgame("📋 استفتاء", ["الموضوع", "السؤال", "نعم", "لا", "ما عندي رأي"]),
    "15": tgame("📺 بث مباشر", ["اللعبة", "الناقل", "الوقت", "المنصة", "الرابط"]),
}

TITLES_GAMES = {
    "1": "📰 خبر لعبة", "2": "📝 مراجعة لعبة", "3": "📢 إعلان لعبة",
    "4": "📊 تصويت", "5": "📌 تحديث لعبة", "6": "⚖️ مقارنة",
    "7": "💡 توصية لعبة", "8": "💬 سؤال نقاش", "9": "🔮 توقع",
    "10": "🏆 إنجاز", "11": "🎭 شخصية اللعبة", "12": "💬 اقتباس",
    "13": "🏆 مسابقة", "14": "📋 استفتاء", "15": "📺 بث مباشر",
}

# ------------------------------------------------------------------------------
# الربط بين الشات والديباجات
# ------------------------------------------------------------------------------
CHANNEL_CATS = {
    CHANNEL_MOVIES: {"name": "أفلام ومسلسلات", "templates": T_MOVIES, "titles": TITLES_MOVIES, "emoji": "🎬"},
    CHANNEL_FOOTBALL: {"name": "كورة", "templates": T_FOOTBALL, "titles": TITLES_FOOTBALL, "emoji": "⚽"},
    CHANNEL_ANIME: {"name": "انمي", "templates": T_ANIME, "titles": TITLES_ANIME, "emoji": "🎌"},
    CHANNEL_GIRLS: {"name": "إدارة الفتيات", "templates": T_GIRLS, "titles": TITLES_GIRLS, "emoji": "👧"},
    CHANNEL_GAMES: {"name": "إدارة الألعاب", "templates": T_GAMES, "titles": TITLES_GAMES, "emoji": "🎮"},
}

def get_cat(channel_id):
    return CHANNEL_CATS.get(channel_id)

# ------------------------------------------------------------------------------
# واجهة التفاعل
# ------------------------------------------------------------------------------
class CatSelect(Select):
    def __init__(self, cat):
        super().__init__(placeholder=f"اختر الديباجة لـ {cat['name']}...", min_values=1, max_values=1,
            options=[
                discord.SelectOption(
                    label=f"{num} - {title}",
                    description=f"ديباجة {cat['name']}",
                    emoji=cat['emoji'],
                    value=num
                )
                for num, title in cat["titles"].items()
            ])

    async def callback(self, interaction):
        cat = get_cat(interaction.channel_id)
        if not cat:
            return await interaction.response.send_message("❌ هذا الروم غير مخصص للديباجات.", ephemeral=True)
        val = self.values[0]
        text = cat["templates"][val]
        title = cat["titles"][val]
        await interaction.response.send_message(text, ephemeral=True)

class CatView(View):
    def __init__(self, cat):
        super().__init__(timeout=None)
        self.add_item(CatSelect(cat))

# ------------------------------------------------------------------------------
# أحداث البوت وإضافات الألعاب
# ------------------------------------------------------------------------------
from tarneeb_cog import TarneebCog
from bank_cog import BankCog
from basra_cog import BasraCog

# سجل مركزي لجميع الألعاب النشطة (channel_id -> game_type)
active_all_games = {}

def find_active_game(channel_id):
    """يبحث عن أي لعبة نشطة في القناة من جميع السجلات ويعيد نوعها (أو None).
    يفحص السجل المركزي أولاً ثم سجلات كل لعبة مباشرة حتى لا تختفي لعبة
    حقيقية بسبب عدم تزامن السجلات."""
    t = active_all_games.get(channel_id)
    if t:
        return t
    if channel_id in active_roulettes:
        return "roulette"
    try:
        from basra_cog import active_basra_games
        if channel_id in active_basra_games:
            return "scopa"
    except Exception:
        pass
    try:
        from bank_cog import active_bank_games
        if channel_id in active_bank_games:
            return "bank"
    except Exception:
        pass
    try:
        from tarneeb_cog import active_games as active_tarneeb
        if channel_id in active_tarneeb:
            return "tarneeb"
    except Exception:
        pass
    return None

def register_game(channel_id, game_type):
    """تسجيل لعبة جديدة في القناة"""
    active_all_games[channel_id] = game_type

def unregister_game(channel_id):
    """إلغاء تسجيل لعبة من القناة"""
    active_all_games.pop(channel_id, None)

def get_active_game(channel_id):
    """الحصول على نوع اللعبة النشطة في القناة"""
    return find_active_game(channel_id)

def has_active_game(channel_id):
    """التحقق من وجود لعبة نشطة في القناة"""
    return find_active_game(channel_id) is not None

async def setup_hook():
    await bot.add_cog(TarneebCog(bot))
    log.info("✅ تم تحميل إضافة لعبة الطرنيب (TarneebCog) بنجاح!")
    await bot.add_cog(BankCog(bot))
    log.info("✅ تم تحميل إضافة لعبة بنك الحظ (BankCog) بنجاح!")
    await bot.add_cog(BasraCog(bot))
    log.info("✅ تم تحميل إضافة لعبة الشكوبا (BasraCog) بنجاح!")

bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    log.info("البوت جاهز: %s (id=%s)", bot.user, bot.user.id)
    await bot.change_presence(activity=discord.Game(name="_اوامر في شات التصنيف"))

ALLOWED_CHANNELS = {CHANNEL_MOVIES, CHANNEL_FOOTBALL, CHANNEL_ANIME, CHANNEL_GIRLS, CHANNEL_GAMES, GAME_CHANNEL}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # كلام حب ليبي - فقط إذا كتب "نحبك" بالضبط
    if message.content.strip() == "نحبك":
        ردود_حب = [
            "يا بعد عيني و قلبي, تسلملي يالغالي.",
            "وانا بعد نحبك قد الدنيا يارب.",
            "يا روح امي و ابويا, كلامك عسل.",
            "تسلملي ياحبيبي, نورت الدنيا.",
            "ياما بعييييد, انت الغالي والله.",
            "الله يخليك ليا ولا يحرمني منك.",
            "يا بعد كل الاحباب, انا هنا جنبك.",
            "عيوني فداك, تحبني و انا اموت فيك.",
            "بتمنى تبقي معايا طول العمر يارب.",
            "انت اغلى ما في الدنيا والله.",
            "الحب كله ليك و العمر كله معاك.",
            "يا غالي و عزيز, كلامك يدوب القلب.",
            "والله نحبك و نتمني نشوفك دايمًا مبسوط.",
            "انت الروح و القلب و العقل يا حبيب قلبي.",
            "تسلملي على كلامك الجميل يا بعدهم كلهم.",
            "يا زينة الايام, كلامك عسل و سكر.",
            "ادامك الله في حياتي يا غالي.",
            "والله لو تعرف قد ايش نحبك تتمني تبقي معانا دايمًا.",
            "يا عسل و سكر, انت احلى ما في الدنيا.",
            "سلملي على قلبك اللي ما يعرف الا الخير.",
            "انت الدنيا و كل اللي فيها يا حبيبي.",
            "حبي الكبير و قلبي الصغير كلهم ليك.",
            "يا رب يديم المحبة بينا و لا يفرقنا.",
            "كلامك يدوب القلب بجد تسلملي.",
            "انت الروح و يا ريت تفضل دايمًا بخير.",
            "روحي و قلبي و عقلي فداك و الله.",
            "ساعات و ضحكاتك تخليني انسى الدنيا كلها.",
            "انت الغالي يا اغلى من الذهب و الماس.",
            "ياما انت جميل في كلامك و في قلبك الابيض.",
            "كلمة نحبك منك تكفيني و تخليني اسعد انسان.",
        ]
        await message.channel.send(f"{message.author.mention} {random.choice(ردود_حب)}")
        await bot.process_commands(message)
        return

    # شات الألعاب - لا توجد ديباجات هنا
    if message.channel.id == GAME_CHANNEL:
        await bot.process_commands(message)
        return

    cat = get_cat(message.channel.id)
    if not cat:
        await bot.process_commands(message)
        return
    content = message.content.strip()
    if content in cat["templates"]:
        template_text = cat["templates"][content]
        title = cat["titles"][content]
        embed = discord.Embed(
            title=f"✨ {title}",
            description=f"ديباجة {cat['name']}",
            color=discord.Color.gold()
        )
        embed.add_field(name="📋 النص:", value=f"{template_text}", inline=False)
        embed.set_footer(text=f"تم الطلب بواسطة {message.author.display_name}", icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)
        await bot.process_commands(message)
        return
    await bot.process_commands(message)

@bot.command(name="اوامر", aliases=["أوامر", "ديباجات", "ديباجة", "help", "الاوامر", "commands"])
async def show_commands(ctx):
    embed = discord.Embed(
        title="📋 قائمة أوامر البوت",
        description="إليك جميع أوامر البوت المتاحة:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎬 ديباجات التصنيف",
                    value="اكتب **رقم الديباجة** (1-15) في روم التصنيف المناسب:\n"
                          "• `1` قصة • `2` خبر • `3` إعلان • `4` تصويت • `5` مشاهدة\n"
                          "• `6` مراجعة • `7` توصية • `8` سؤال • `9` نظرية/توقع\n"
                          "• `10` مقارنة • `11` شخصية/لاعب اليوم • `12` اقتباس\n"
                          "• `13` مسابقة • `14` استفتاء • `15` مشاهدة جماعية\n"
                          f"أو استخدم `.{1}` إلى `.{15}`",
                    inline=False)
    embed.add_field(name="🎰 لعبة الروليت",
                    value="• `روليت` أو `roulette` - بدء لعبة الروليت\n"
                          "• `توقف` أو `stop` - إيقاف الروليت\n"
                          "• `نقاطي` أو `points` - عرض نقاطك ومخزونك",
                    inline=False)
    embed.add_field(name="🏪 متجر الخواص",
                    value="• `متجر` أو `shop` - فتح متجر خواص الروليت\n"
                          "• 🛡️ درع ضد الطرد (18 نقطة)\n"
                          "• ⚡ طرد ثنائي (20 نقطة)\n"
                          "• 🔄 طرد عكسي (25 نقطة)",
                    inline=False)
    embed.add_field(name="💖 تفاعلات",
                    value="اكتب **نحبك** في أي مكان وسيرد البوت بكلام غزل ليبي 😉",
                    inline=False)
    cat = get_cat(ctx.channel.id)
    if cat:
        embed.add_field(name=f"🎬 ديباجات {cat['name']} في هذا الروم",
                        value="يمكنك استخدام القائمة بالأسفل للاختيار مباشرة:",
                        inline=False)
        await ctx.send(embed=embed, view=CatView(cat))
    else:
        embed.set_footer(text="هذا الروم غير مخصص للديباجات، لكن باقي الأوامر تعمل هنا.")
        await ctx.send(embed=embed)

def make_template_cmd(num):
    key = str(num)
    async def cmd(ctx):
        cat = get_cat(ctx.channel.id)
        if not cat:
            return await ctx.send("❌ هذا الروم غير مخصص للديباجات.")
        await ctx.send(cat['templates'][key])
    return cmd

for _num in range(1, 16):
    bot.command(name=str(_num))(make_template_cmd(_num))

# ------------------------------------------------------------------------------
# لعبة الروليت
# ------------------------------------------------------------------------------
active_roulettes = {}

# ------------------------------------------------------------------------------
# روليت — مطابق لبوت Shuruhatik المرجعي (طبق الأصل)
# ------------------------------------------------------------------------------
WAITING_TIME = 27
MAX_SEATS = 40
HOWTO = ("**1-** انضم في اللعبة\n"
         "**2-** ستبدأ الجولة الأولى وسيتم تدوير العجلة واختيار لاعب عشوائي\n"
         "**3-** إذا كنت اللاعب المختار ، فستختار لاعبًا من اختيارك ليتم طرده من اللعبة\n"
         "**4-** يُطرد اللاعب وتبدأ جولة جديدة ، عندما يُطرد جميع اللاعبين ويتبقى لاعبان فقط ، ستدور العجلة ويكون اللاعب المختار هو الفائز باللعبة")


def roulette_players_text(players):
    if not players:
        return "لا يوجد لاعبين مشاركين باللعبة"
    return "\n".join(
        f"`{p['number']:02d}`: <@{p['id']}>"
        for p in sorted(players, key=lambda x: x["number"])
    )


class JoinBtn(discord.ui.Button):
    def __init__(self, gid, game_id, number=None, is_random=False, is_leave=False, row=0):
        self.gid = gid
        self.game_id = game_id
        self.number = number
        if is_random:
            super().__init__(label="دخول عشوائي", style=discord.ButtonStyle.success,
                             custom_id=f"join_random_roulette_{gid}_{game_id}", row=row)
        elif is_leave:
            super().__init__(label="اخرج من اللعبة", style=discord.ButtonStyle.danger,
                             custom_id=f"leave_roulette_{gid}_{game_id}", row=row)
        else:
            super().__init__(label=str(number), style=discord.ButtonStyle.secondary,
                             custom_id=f"join_{number}_roulette_{gid}_{game_id}", row=row)

    async def callback(self, ia):
        g = active_roulettes.get(self.gid)
        if not g:
            return await ia.response.send_message("❌ انتهت الجولة.", ephemeral=True)
        if self.custom_id.startswith("leave"):
            pl = next((p for p in g["players"] if p["id"] == ia.user.id), None)
            if not pl:
                return await ia.response.send_message("❌ انت غير مشارك بالفعل", ephemeral=True)
            g["players"] = [p for p in g["players"] if p["id"] != ia.user.id]
            btn = g["btns"].get(pl["number"])
            if btn:
                btn.disabled = False
                btn.label = str(pl["number"])
            await self._refresh(g)
            return await ia.response.send_message("✅ | تم إزالتك من اللعبة", ephemeral=True)
        if any(p["id"] == ia.user.id for p in g["players"]):
            return await ia.response.send_message("انت مشارك بالفعل لكي تغير مكانك يجب عليك الخروج من الروليت ثم الدخول مرة اخري", ephemeral=True)
        if len(g["players"]) >= MAX_SEATS:
            return await ia.response.send_message("عدد المشاركين مكتمل", ephemeral=True)
        number = self.number
        if self.custom_id.startswith("join_random"):
            taken = {p["number"] for p in g["players"]}
            free = [n for n in range(1, MAX_SEATS + 1) if n not in taken]
            if not free:
                return await ia.response.send_message("عدد المشاركين مكتمل", ephemeral=True)
            number = random.choice(free)
        elif number in {p["number"] for p in g["players"]}:
            return await ia.response.send_message("عدد المشاركين مكتمل", ephemeral=True)
        g["players"].append({
            "number": number,
            "id": ia.user.id,
            "username": ia.user.display_name,
            "avatarURL": ia.user.display_avatar.url,
        })
        btn = g["btns"].get(number)
        if btn:
            btn.disabled = True
            btn.label = f"{number}. {ia.user.display_name}"[:80]
        await ia.response.defer()
        await self._refresh(g)

    async def _refresh(self, g):
        e = g["embed"]
        e.description = f"__**اللاعبين:**__\n{roulette_players_text(g['players'])}"
        try:
            await g["m1"].edit(embed=e, view=g["v1"])
        except Exception:
            pass
        try:
            await g["m2"].edit(view=g["v2"])
        except Exception:
            pass


class JoinView(View):
    def __init__(self, gid, game_id, start, end):
        super().__init__(timeout=None)
        for num in range(start, end + 1):
            self.add_item(JoinBtn(gid, game_id, number=num, row=((num - start) // 5)))


class ShopOpenBtn(discord.ui.Button):
    def __init__(self, row=3):
        super().__init__(label="متجر الخواص 🏪", style=discord.ButtonStyle.primary,
                         custom_id="open_roulette_shop_btn", row=row)
        self.number = None

    async def callback(self, ia):
        view = RouletteShopView(ia.user)
        embed = view.build_embed()
        await ia.response.send_message(embed=embed, view=view, ephemeral=True)


class KickBtn(discord.ui.Button):
    def __init__(self, player, row):
        super().__init__(label=f"{player['number']}. {player['username']}"[:80],
                         style=discord.ButtonStyle.secondary,
                         custom_id=f"kick_{player['number']}", row=row)
        self.player = player

    async def callback(self, ia):
        if ia.user.id != self.view.winner["id"]:
            return await ia.response.send_message("❌ | فقط الشخص الذي لديه الدور يمكنه الاختيار", ephemeral=True)
        self.view.choice = ("kick", self.player["number"])
        self.view.stop()
        await ia.response.defer()


class RandomKickBtn(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="🎲 طرد عشوائي", style=discord.ButtonStyle.primary,
                         custom_id="random_kick_btn", row=row)

    async def callback(self, ia):
        if ia.user.id != self.view.winner["id"]:
            return await ia.response.send_message("❌ | فقط الشخص الذي لديه الدور يمكنه الاختيار", ephemeral=True)
        self.view.choice = ("random_kick", None)
        self.view.stop()
        await ia.response.defer()


class DoubleKickSelect(discord.ui.Select):
    """قائمة اختيار لاعبين اثنين للطرد الثنائي"""
    def __init__(self, others):
        options = [
            discord.SelectOption(
                label=f"{p['number']}. {p['username']}"[:100],
                value=str(p["number"]),
                description=f"طرد اللاعب رقم {p['number']}"
            )
            for p in others[:25]
        ]
        super().__init__(
            placeholder="🎯 اختر لاعبين لطردهم بالطرد الثنائي...",
            min_values=1,
            max_values=min(2, len(options)),
            options=options
        )

    async def callback(self, ia):
        if ia.user.id != self.view.winner["id"]:
            return await ia.response.send_message("❌ | فقط الشخص الذي لديه الدور يمكنه الاختيار", ephemeral=True)
        nums = [int(v) for v in self.values]
        self.view.kick_view.choice = ("double_kick_select", nums)
        self.view.kick_view.stop()
        self.view.stop()
        await ia.response.defer()


class DoubleKickSelectView(View):
    """واجهة خاصة بقائمة الطرد الثنائي"""
    def __init__(self, winner, others, kick_view):
        super().__init__(timeout=30)
        self.winner = winner
        self.kick_view = kick_view
        self.add_item(DoubleKickSelect(others))

    @discord.ui.button(label="إلغاء الطرد الثنائي ↩️", style=discord.ButtonStyle.secondary, row=1)
    async def cancel_btn(self, ia, button):
        if ia.user.id != self.winner["id"]:
            return await ia.response.send_message("❌ | فقط الشخص الذي لديه الدور يمكنه الاختيار", ephemeral=True)
        self.stop()
        await ia.response.defer()


class DoubleKickBtn(discord.ui.Button):
    def __init__(self, winner, others):
        super().__init__(label="⚡ طرد ثنائي", style=discord.ButtonStyle.success,
                         custom_id="double_kick_btn", row=4)
        self.winner = winner
        self.others = others

    async def callback(self, ia):
        if ia.user.id != self.view.winner["id"]:
            return await ia.response.send_message("❌ | فقط الشخص الذي لديه الدور يمكنه الاختيار", ephemeral=True)
        # Open the double kick selection menu as ephemeral so only the winner sees it
        dk_view = DoubleKickSelectView(self.winner, self.others, self.view)
        await ia.response.send_message(
            f"⚡ **طرد ثنائي** | اختر لاعباً أو لاعبين من القائمة أدناه لطردهم:",
            view=dk_view,
            ephemeral=True
        )
        await dk_view.wait()


class WithdrawBtn(discord.ui.Button):
    def __init__(self, gid, row):
        super().__init__(label="انسحاب", style=discord.ButtonStyle.danger,
                         custom_id=f"withdraw_groulette_{gid}", row=row)
        self.gid = gid

    async def callback(self, ia):
        if ia.user.id != self.view.winner["id"]:
            return await ia.response.send_message("❌ | فقط الشخص الذي لديه الدور يمكنه الاختيار", ephemeral=True)
        self.view.choice = ("withdraw", None)
        self.view.stop()
        await ia.response.defer()


class KickView(View):
    def __init__(self, gid, winner, players):
        super().__init__(timeout=30)
        self.gid = gid
        self.winner = winner
        self.choice = None

        others = [p for p in players if p["id"] != winner["id"]]

        # Player buttons — rows 0..3 (max 20 players = 4 rows × 5)
        for i, p in enumerate(others[:20]):
            self.add_item(KickBtn(p, row=min(i // 5, 3)))

        # Action buttons always in row 4 (bottom row)
        self.add_item(RandomKickBtn(row=4))
        self.add_item(WithdrawBtn(gid, row=4))

        # Double kick button shown only if winner owns the item
        if has_item(winner["id"], "double_kick"):
            self.add_item(DoubleKickBtn(winner, others))



@bot.command(name="متجر", aliases=["shop", "المتجر"])
async def shop_cmd(ctx):
    """فتح متجر خواص الروليت"""
    view = RouletteShopView(ctx.author)
    embed = view.build_embed()
    await ctx.send(embed=embed, view=view)


@bot.command(name="نقاطي", aliases=["points", "النقاط", "تاريخي", "سجلي"])
async def points_cmd(ctx):
    """عرض نقاطك ومخزون الخواص والتاريخ الدائم لديك"""
    u = get_user_data(ctx.author.id)
    pts = u.get("points", 0)
    total_pts = u.get("total_points_earned", pts)
    wins = u.get("total_wins", 0)
    kicks = u.get("total_kicks", 0)
    inv = u.get("inventory", {})
    text = (f"💰 **رصيد النقاط الجاري:** `{pts}` نقطة | 📜 **إجمالي التاريخ:** `{total_pts}` نقطة\n"
            f"🏆 **الانتصارات الكلية:** `{wins}` | 🎯 **حالات الطرد:** `{kicks}`\n\n"
            f"📦 **الخواص بالمخزون:**\n"
            f"• درع ضد الطرد 🛡️: `{inv.get('shield', 0)}`\n"
            f"• طرد ثنائي ⚡: `{inv.get('double_kick', 0)}`\n"
            f"• طرد عكسي 🔄: `{inv.get('reverse_kick', 0)}`")
    await ctx.send(text)


@bot.command(name="روليت", aliases=["roulette"])
async def roulette_cmd(ctx):
    if not ctx.author.guild_permissions.manage_events:
        return await ctx.send("❌ | فقط Manga Events يمكنهم قيام بهذا الامر")
    gid = ctx.channel.id
    if gid in active_roulettes:
        old = active_roulettes.get(gid)
        # تنظيف الجولات العالقة (بدون مشرف تنتهي مهلتها تلقائياً)
        if old and (time.time() - (old.get("created_at") or 0)) > 600:
            del active_roulettes[gid]
        else:
            return await ctx.send("❌ يوجد جولة تعمل الان بالفعل")
    if has_active_game(gid):
        return await ctx.send(f"❌ يوجد لعبة **{get_active_game(gid)}** تعمل في هذا الروم بالفعل!")
    game_id = int(time.time() * 1000)
    g = {"id": game_id, "players": [], "btns": {}, "created_at": time.time()}
    active_roulettes[gid] = g
    register_game(gid, "roulette")

    e = discord.Embed(title="روليت", color=0xE4F000,
                      description=f"__**اللاعبين:**__\n{roulette_players_text([])}")
    e.add_field(name="__طريقة اللاعب:__", value=HOWTO)
    e.add_field(name="__ستبدأ اللعبة خلال__:",
                value=f"**<t:{int(time.time() + WAITING_TIME)}:R>**")
    g["embed"] = e

    v1 = JoinView(gid, game_id, 1, 25)
    v2 = JoinView(gid, game_id, 26, 40)
    v2.add_item(JoinBtn(gid, game_id, is_random=True, row=3))
    v2.add_item(JoinBtn(gid, game_id, is_leave=True, row=3))
    v2.add_item(ShopOpenBtn(row=3))
    for v in (v1, v2):
        for b in v.children:
            if getattr(b, "number", None) is not None:
                g["btns"][b.number] = b

    m1 = await ctx.send(embed=e, view=v1)
    m2 = await ctx.send(view=v2)
    g["v1"], g["v2"], g["m1"], g["m2"] = v1, v2, m1, m2

    end_time = time.time() + WAITING_TIME
    while time.time() < end_time:
        if gid not in active_roulettes:
            return await ctx.send("❌ | تم إيقاف الجولة بواسطة المسؤولين")
        remaining = int(end_time - time.time())
        e.set_field_at(1, name="__ستبدأ اللعبة خلال__:", value=f"**{remaining} ثانية**")
        try:
            await m1.edit(embed=e)
        except Exception:
            pass
        await asyncio.sleep(1)

    if gid not in active_roulettes:
        return await ctx.send("❌ | تم إيقاف الجولة بواسطة المسؤولين")
    for v in (v1, v2):
        for b in v.children:
            b.disabled = True
    e.color = 0x0FF000
    e.clear_fields()
    e.add_field(name="__طريقة اللاعب:__", value=HOWTO)
    try:
        await m1.edit(embed=e, view=v1)
        await m2.edit(view=v2)
    except Exception:
        pass

    if len(g["players"]) < 3:
        await ctx.send("🚫 | تم إلغاء اللعبة لعدم وجود 3 لاعبين على الأقل")
        del active_roulettes[gid]
        return
    await ctx.send("✅ | تم توزيع الأرقام على كل لاعب. ستبدأ الجولة الأولى في بضع ثواني...")
    try:
        await run_game(ctx, gid)
    finally:
        # ضمان تنظيف حالة اللعبة حتى لو حدث خطأ
        active_roulettes.pop(gid, None)
        unregister_game(gid)


@bot.command(name="توقف", aliases=["stop"])
async def stop_cmd(ctx):
    if not ctx.author.guild_permissions.manage_events:
        return await ctx.send("❌ | فقط Manga Events يمكنهم قيام بهذا الامر")
    gid = ctx.channel.id
    if gid not in active_roulettes:
        return await ctx.send("❌ لا توجد لعبة قيد التشغيل في الوقت الحالي")
    del active_roulettes[gid]
    unregister_game(gid)
    await ctx.send(f"❌ | تم طلب إيقاف لعبة روليت من قبل <@{ctx.author.id}>")


@bot.command(name="انهاء", aliases=["end", "إنهاء", "stop_all", "توقف_الكل"])
async def end_any_game(ctx):
    """إنهاء أي لعبة نشطة في هذا الروم"""
    cid = ctx.channel.id
    game_type = find_active_game(cid)

    if not game_type:
        return await ctx.send("❌ لا توجد لعبة قيد التشغيل في هذا الروم!")

    # تنظيف جميع السجلات لضمان إزالة اللعبة نهائياً مهما كان مصدرها
    active_all_games.pop(cid, None)
    active_roulettes.pop(cid, None)
    from basra_cog import active_basra_games
    active_basra_games.pop(cid, None)
    from bank_cog import active_bank_games
    active_bank_games.pop(cid, None)
    from tarneeb_cog import active_games as active_tarneeb
    active_tarneeb.pop(cid, None)

    await ctx.send(f"✅ تم إنهاء لعبة **{game_type}** في هذا الروم بواسطة <@{ctx.author.id}>!")


async def run_game(ctx, gid):
    if gid not in active_roulettes:
        return await ctx.send("❌ | تم إيقاف الجولة بواسطة المسؤولين")
    g = active_roulettes[gid]
    players = sorted(g["players"], key=lambda p: p["number"])
    random.shuffle(players)
    winner = players[-1]

    for p in players:
        if "avimg" not in p:
            p["avimg"] = await download_avatar(p.get("avatarURL"))

    img_file = await make_gif([{"number": p["number"], "img": p.get("avimg")} for p in players],
                             highlight=len(players) - 1)
    content = f"**{winner['number']}** - <@{winner['id']}>"
    if len(players) <= 2:
        content += "\n:crown: **هذه الجولة الأخيرة ! اللاعب المختار هو اللاعب الفائز في اللعبة.**"
    await ctx.send(content=content, file=discord.File(img_file, filename="roulette.png"))

    if len(players) <= 2:
        winner_pts = record_win(winner["id"])
        await ctx.send(f":crown: - **فاز <@{winner['id']}> في اللعبة وحصل على 3 نقاط! 🎉 (إجمالي نقاطه: {winner_pts})**")
        del active_roulettes[gid]
        return

    view = KickView(gid, winner, players)
    msg = await ctx.send(f"<@{winner['id']}> لديك **30 ثانية** لإختيار لاعب لطرده", view=view)
    await view.wait()

    if gid not in active_roulettes:
        return await ctx.send("❌ | تم إيقاف الجولة بواسطة المسؤولين")
    for b in view.children:
        b.disabled = True
    try:
        await msg.edit(view=view)
    except Exception:
        pass

    choice = view.choice
    others = [p for p in players if p["id"] != winner["id"]]

    if choice:
        c_type, c_val = choice
        if c_type in ("kick", "random_kick"):
            if c_type == "kick":
                victim = next((p for p in players if p["number"] == c_val), None)
            else:
                victim = random.choice(others) if others else None

            if not victim:
                await ctx.send(f"💣 | تم طرد <@{winner['id']}> من اللعبة لعدم تفاعله ، سيتم بدء الجولة القادمة في بضع ثواني...")
                g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
                return await run_game(ctx, gid)

            # Check Target for Reverse Kick
            if use_item(victim["id"], "reverse_kick"):
                v_pts = record_kick(victim["id"])
                await ctx.send(f"🔄 **طرد عكسي!** حاول <@{winner['id']}> طرد <@{victim['id']}>، لكن <@{victim['id']}> يمتلك خاصية **الطرد العكسي 🔄**!\n"
                               f"انعكست الضربة وطُرد المعتدي <@{winner['id']}> من اللعبة! وحصل <@{victim['id']}> على **+1 نقطة** 🎯 (نقاطه: {v_pts})")
                g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
                return await run_game(ctx, gid)

            # Check Target for Shield
            elif use_item(victim["id"], "shield"):
                await ctx.send(f"🛡️ **درع ضد الطرد!** حاول <@{winner['id']}> طرد <@{victim['id']}>، لكن **الدرع 🛡️** حمى <@{victim['id']}> وتم تدمير الدرع!\n"
                               f"نجا <@{victim['id']}> وتستمر اللعبة بدون أي طرد هذه الجولة.")
                return await run_game(ctx, gid)

            else:
                kicker_pts = record_kick(winner["id"])
                await ctx.send(f"💣 | تم طرد <@{victim['id']}> من اللعبة وحصل <@{winner['id']}> على **+1 نقطة** 🎯 (نقاطه: {kicker_pts}) ، سيتم بدء الجولة القادمة في بضع ثواني...")
                g["players"] = [p for p in g["players"] if p["id"] != victim["id"]]
                return await run_game(ctx, gid)

        elif c_type in ("double_kick", "double_kick_select"):
            if use_item(winner["id"], "double_kick"):
                # double_kick_select = user manually chose targets (list of numbers)
                # double_kick = fallback (shouldn't happen anymore but kept for safety)
                if c_type == "double_kick_select" and c_val:
                    targets = [p for p in players if p["number"] in c_val]
                else:
                    targets = random.sample(others, min(2, len(others))) if others else []

                kicked_names = []
                pts_earned = 0
                for victim in targets:
                    # Check reverse kick first
                    if use_item(victim["id"], "reverse_kick"):
                        v_pts = add_points(victim["id"], 1)
                        kicked_names.append(f"<@{victim['id']}> (🔄 ردّ الضربة!)")
                        g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
                        await ctx.send(
                            f"🔄 **طرد عكسي!** حاول <@{winner['id']}> طرد <@{victim['id']}> بالطرد الثنائي، "
                            f"لكن **الطرد العكسي 🔄** أنقذه وطرد المهاجم بدلاً منه! وحصل <@{victim['id']}> على **+1 نقطة** (نقاطه: {v_pts})"
                        )
                        return await run_game(ctx, gid)
                    # Check shield
                    elif use_item(victim["id"], "shield"):
                        kicked_names.append(f"<@{victim['id']}> (نجا بالدرع 🛡️)")
                    else:
                        g["players"] = [p for p in g["players"] if p["id"] != victim["id"]]
                        kicked_names.append(f"<@{victim['id']}>")
                        pts_earned += 1

                kicker_pts = add_points(winner["id"], pts_earned)
                t_str = " و ".join(kicked_names) if kicked_names else "لا أحد"
                await ctx.send(
                    f"⚡ **طرد ثنائي!** استخدم <@{winner['id']}> خاصية الطرد الثنائي واستهدف: {t_str}!\n"
                    f"حصل <@{winner['id']}> على **+{pts_earned} نقاط** 🎯 (إجمالي نقاطه: {kicker_pts})."
                )
                return await run_game(ctx, gid)


        elif c_type == "withdraw":
            await ctx.send(f"💣 | لقد انسحب <@{winner['id']}> من اللعبة ، سيتم بدء الجولة القادمة في بضع ثواني...")
            g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
            return await run_game(ctx, gid)

    await ctx.send(f"💣 | تم طرد <@{winner['id']}> من اللعبة لعدم تفاعله ، سيتم بدء الجولة القادمة في بضع ثواني...")
    g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
    await run_game(ctx, gid)

# ------------------------------------------------------------------------------
# تشغيل البوت
# ------------------------------------------------------------------------------
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.critical("⚠️ ضع توكن البوت في متغير البيئة DISCORD_TOKEN!")
        raise SystemExit(1)

    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, format, *args):
            pass
    def run_http():
        port = int(os.getenv("PORT", 10000))
        HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
    threading.Thread(target=run_http, daemon=True).start()
    log.info("HTTP health check server running on port %s", os.getenv("PORT", 10000))

    bot.run(TOKEN, log_handler=None)
