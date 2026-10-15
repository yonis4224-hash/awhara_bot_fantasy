import os
import logging
import asyncio
import random
import math
import time

from roulette_cog import RouletteCog

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
from profile_cog import ProfileCog
from admin_cog import AdminCog

# سجل مركزي لجميع الألعاب النشطة (channel_id -> game_type)
active_all_games = {}

GAME_NAMES_AR = {
    "roulette": "الروليت 🎡",
    "tarneeb": "الطرنيب 🎴",
    "bank": "بنك الحظ 🏰",
    "basra": "البصرة 🃏",
    "scopa": "البصرة / الشكوبا 🃏"
}

def is_admin_or_mod(ctx):
    """التحقق مما إذا كان المستخدم يملك صلاحيات إدارية أو إشرافية في السيرفر"""
    if not ctx.guild:
        return True
    p = ctx.author.guild_permissions
    return (
        p.administrator
        or p.manage_guild
        or p.manage_events
        or p.manage_messages
        or ctx.author.id == ctx.guild.owner_id
    )

def find_active_game(channel_id):
    """يبحث عن أي لعبة نشطة في القناة من جميع السجلات ويعيد نوعها (أو None)."""
    t = active_all_games.get(channel_id)
    if t:
        return t
    cog = bot.get_cog("RouletteCog")
    if cog and cog.is_game_active(channel_id):
        return "roulette"
    try:
        from basra_cog import active_basra_games
        if channel_id in active_basra_games:
            return "basra"
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
    """الحصول على نوع اللعبة النشطة في القناة بالاسم العربي"""
    gt = find_active_game(channel_id)
    if gt:
        return GAME_NAMES_AR.get(gt, gt)
    return None

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
    await bot.add_cog(ProfileCog(bot))
    log.info("✅ تم تحميل إضافة البطاقات التعريفية ونظام التفاعل (ProfileCog) بنجاح!")
    await bot.add_cog(AdminCog(bot))
    log.info("✅ تم تحميل إضافة القرارات والإعلانات الإدارية (AdminCog) بنجاح!")
    await bot.add_cog(RouletteCog(bot))
    log.info("✅ تم تحميل إضافة لعبة الروليت (RouletteCog) بنجاح!")

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
                          "• `توقف` أو `انهاء` - إيقاف اللعبة بواسطة المشرف\n"
                          "• `نقاطي` أو `points` - عرض نقاطك ومخزونك\n"
                          "• `توب_الروليت` - قائمة متصدري الروليت بالسيرفر",
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
    embed.add_field(name="🛡️ أوامر الإدارة",
                    value="• `_اداره` أو `_إدارة` - فتح لوحة القرارات والإعلانات الإدارية والفعاليات (15 قرار إداري)",
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



@bot.command(name="توقف", aliases=["stop", "_توقف"])
async def stop_cmd(ctx):
    if not is_admin_or_mod(ctx):
        return await ctx.send("❌ | فقط المسؤولين (Admins) يمكنهم إيقاف اللعبة")
    return await end_any_game(ctx)


@bot.command(name="انهاء", aliases=["_انهاء", "إنهاء", "_إنهاء", "end", "stop_all", "توقف_الكل", "انهاء_اللعبه", "_انهاء_اللعبه", "stop_game", "ايقاف", "_ايقاف"])
async def end_any_game(ctx):
    """إنهاء أي لعبة نشطة في هذا الروم بواسطة الأدمن"""
    if not is_admin_or_mod(ctx):
        return await ctx.send("❌ فقط الإدمن والمسؤولين (Administrator / Manage Events) يمكنهم إنهاء اللعبة!")

    cid = ctx.channel.id
    game_type = find_active_game(cid)

    if not game_type:
        return await ctx.send("❌ لا توجد أي لعبة نشطة قيد التشغيل حالياً في هذا الروم!")

    # 1. إلغاء أي مؤقتات نشطة وتنظيف كائنات الألعاب
    try:
        from tarneeb_cog import active_games as active_tarneeb
        if cid in active_tarneeb:
            t_game = active_tarneeb.get(cid)
            cog = bot.get_cog("TarneebCog")
            if cog and t_game:
                t_game.state = 'GAME_OVER'  # <-- Added
                cog.cancel_turn_timer(t_game)
    except Exception:
        pass

    try:
        from basra_cog import active_basra_games
        if cid in active_basra_games:
            b_game = active_basra_games.get(cid)
            cog = bot.get_cog("BasraCog")
            if cog and b_game:
                b_game.state = 'GAME_OVER'  # <-- Added
                cog.cancel_turn_timer(b_game)
    except Exception:
        pass

    try:
        r_cog = bot.get_cog("RouletteCog")
        if r_cog and r_cog.is_game_active(cid):
            await r_cog.stop_game(cid, ctx.author)
    except Exception:
        pass

    # 2. تنظيف جميع السجلات لضمان إزالة اللعبة نهائياً
    active_all_games.pop(cid, None)
    try:
        from basra_cog import active_basra_games
        active_basra_games.pop(cid, None)
    except Exception:
        pass
    try:
        from bank_cog import active_bank_games
        active_bank_games.pop(cid, None)
    except Exception:
        pass
    try:
        from tarneeb_cog import active_games as active_tarneeb
        active_tarneeb.pop(cid, None)
    except Exception:
        pass

    gname = GAME_NAMES_AR.get(game_type, game_type)
    await ctx.send(f"⏹️ تم إنهاء لعبة **{gname}** في هذا الروم بنجاح بواسطة <@{ctx.author.id}>!")


@bot.command(name="العاب", aliases=["ألعاب", "الألعاب", "الالعاب", "games"])
async def games_cmd(ctx):
    """عرض قائمة جميع الألعاب التفاعلية والأوامر الخاصة بها"""
    embed = discord.Embed(
        title="🎮 دليل الألعاب التفاعلية في البوت",
        description="جميع الألعاب منفصلة ولها أوامر مختلفة ومستقلة.\n*(ملاحظة: لا يمكن تشغيل أكثر من لعبة في نفس الروم في آنٍ واحد)*",
        color=0x00FFAA
    )
    embed.add_field(
        name="🎡 1. لعبة الروليت (Roulette)",
        value="• أمر البدء: `.روليت` أو `!روليت`\n• المتجر: `.متجر` | رصيد النقاط: `.نقاطي`\n• إيقاف: `.انهاء`",
        inline=False
    )
    embed.add_field(
        name="🎴 2. لعبة الطرنيب (Tarneeb - 4 لاعبين)",
        value="• أمر البدء: `.طرنيب` أو `!طرنيب`\n• ميزة المؤقت: 20 ثانية لكل دور (لعب تلقائي عند التأخر)\n• إيقاف الأدمن: `.انهاء` أو `_انهاء_الطرنيب`",
        inline=False
    )
    embed.add_field(
        name="🏰 3. لعبة بنك الحظ (Bank Al-Haz / Monopoly)",
        value="• أمر البدء: `.بنك` أو `.بنك_الحظ` أو `!bank`\n• رقعة بالصور ورسم البيادق وشراء وتطوير المدن\n• إيقاف الأدمن: `.انهاء`",
        inline=False
    )
    embed.add_field(
        name="🃏 4. لعبة البصرة / الشكوبا (Basra / Scopa)",
        value="• أمر البدء: `.بصرة` أو `!بصرة` أو `.شكوبا`\n• ميزة المؤقت: 20 ثانية لكل دور (لعب تلقائي عند التأخر)\n• إيقاف الأدمن: `.انهاء` أو `_انهاء_البصرة`",
        inline=False
    )
    embed.add_field(
        name="💳 5. البطاقات التعريفية والتفاعل (Profile & Rank Cards)",
        value="• عرض بطاقتك: `.بروفايل` أو `.id` أو `!profile` أو `.بطاقتي`\n• توب المتفاعلين: `.توب` أو `!top`\n• متصدري الأسبوع: `.توب_الاسبوع` أو `!weekly`",
        inline=False
    )
    embed.add_field(
        name="🛡️ أوامر الإدارة والإيقاف:",
        value="• لأي أدمن لإنهاء وحذف أي لعبة نشطة فوراً: `.انهاء` أو `_انهاء` أو `!stop`",
        inline=False
    )
    embed.set_footer(text="استمتعوا باللعب والتنافس! 🎲")
    await ctx.send(embed=embed)


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
