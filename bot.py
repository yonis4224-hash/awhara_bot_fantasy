import os
import logging
import asyncio
import json
import random
import math
import time

from roulette_gif import make_gif, download_avatar

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
# أحداث البوت
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    log.info("البوت جاهز: %s (id=%s)", bot.user, bot.user.id)
    await bot.change_presence(activity=discord.Game(name="_اوامر في شات التصنيف"))

ALLOWED_CHANNELS = {CHANNEL_MOVIES, CHANNEL_FOOTBALL, CHANNEL_ANIME, CHANNEL_GIRLS, CHANNEL_GAMES, GAME_CHANNEL}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # كلام حب ليبي
    if message.channel.id in ALLOWED_CHANNELS and "نحبك" in message.content:
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

@bot.command(name="اوامر", aliases=["أوامر", "ديباجات", "ديباجة", "help", "الاوامر"])
async def show_commands(ctx):
    cat = get_cat(ctx.channel.id)
    if not cat:
        return await ctx.send("❌ هذا الروم غير مخصص للديباجات.")
    embed = discord.Embed(
        title=f"🎬 قائمة ديباجات {cat['name']}",
        description=f"اكتب **رقم الديباجة** (مثال: `.{1}` أو `{1}`) أو استخدم القائمة:",
        color=discord.Color.blue()
    )
    for key, title in cat["titles"].items():
        embed.add_field(name=f"الرقم: `{key}`", value=title, inline=False)
    embed.set_footer(text="اختر من القائمة بالأسفل!")
    await ctx.send(embed=embed, view=CatView(cat))

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
# لعبة الروليت والمتجر
# ------------------------------------------------------------------------------
DATA_FILE = "game_data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_player(uid):
    data = load_data()
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"points": 0, "shield": 0, "double_kick": 0, "anti_kick": 0, "wins": 0, "games": 0, "eliminations": 0}
        save_data(data)
    return data["users"][uid]

def save_player(uid, pdata):
    data = load_data()
    data["users"][str(uid)] = pdata
    save_data(data)

active_roulettes = {}

ITEMS = {
    "1": {"name": "درع ضد الطرد", "price": 18, "key": "shield", "desc": "يحميك من الإقصاء لمرة واحدة"},
    "2": {"name": "طرد ثنائي", "price": 20, "key": "double_kick", "desc": "عند إقصائك تأخذ معك شخص آخر"},
    "3": {"name": "طرد عكسي", "price": 25, "key": "anti_kick", "desc": "يعكس الإقصاء على شخص آخر بدلاً منك"},
}

@bot.command(name="متجر", aliases=["shop", "المتجر"])
async def shop_cmd(ctx):
    if ctx.channel.id != GAME_CHANNEL:
        return
    embed = discord.Embed(title="🏪 المتجر", description="نقاطك تستطيع شراء:", color=discord.Color.green())
    for k, v in ITEMS.items():
        embed.add_field(name=f"{k}. {v['name']} - {v['price']} نقطة", value=v["desc"], inline=False)
    embed.set_footer(text="استخدم .شراء [رقم]")
    await ctx.send(embed=embed)

@bot.command(name="شراء", aliases=["buy"])
async def buy_cmd(ctx, item_num: str = None):
    if ctx.channel.id != GAME_CHANNEL:
        return
    if not item_num or item_num not in ITEMS:
        return await ctx.send("❌ استخدم `.شراء 1` أو `2` أو `3`")
    player = get_player(ctx.author.id)
    item = ITEMS[item_num]
    if player["points"] < item["price"]:
        return await ctx.send(f"❌ معاك {player['points']} نقطة, محتاج {item['price']}")
    player["points"] -= item["price"]
    player[item["key"]] += 1
    save_player(ctx.author.id, player)
    await ctx.send(f"✅ اشتريت **{item['name']}**! رصيدك: {player['points']} نقطة")

@bot.command(name="نقاطي", aliases=["points", "نقاط"])
async def points_cmd(ctx):
    if ctx.channel.id != GAME_CHANNEL:
        return
    player = get_player(ctx.author.id)
    items_list = f"🛡 درع: {player['shield']} | 💥 طرد ثنائي: {player['double_kick']} | 🔄 طرد عكسي: {player['anti_kick']}"
    await ctx.send(f"⭐ {ctx.author.mention} نقاطك: **{player['points']}**\n{items_list}")

@bot.command(name="تصنيف", aliases=["leaderboard", "top", "المتصدرين"])
async def leaderboard_cmd(ctx):
    if ctx.channel.id != GAME_CHANNEL:
        return
    data = load_data()
    users = []
    for uid, p in data["users"].items():
        users.append((uid, p["wins"], p["points"], p["eliminations"], p["games"]))
    users.sort(key=lambda x: (-x[1], -x[2]))
    e = discord.Embed(title="🏆 Leaderboard", color=C_MAIN)
    e.description = "```\n" + "─" * 22 + "```"
    for i, (uid, wins, pts, elims, games) in enumerate(users[:10]):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`{i+1:02d}`"
        e.add_field(
            name=f"{medal} <@{uid}>",
            value=f"Wins: **{wins}** | Points: **{pts}** | Elims: **{elims}** | Games: **{games}**",
            inline=False
        )
    if not users:
        e.add_field(name="No data", value="Play some games first!", inline=False)
    await ctx.send(embed=e)

@bot.command(name="احصائيات", aliases=["stats", "ستات"])
async def stats_cmd(ctx):
    if ctx.channel.id != GAME_CHANNEL:
        return
    p = get_player(ctx.author.id)
    ratio = f"{p['wins']/p['games']:.0%}" if p["games"] > 0 else "N/A"
    e = discord.Embed(title="📊 Player Stats", color=C_INFO)
    e.description = f"```\n{'─' * 18}\n STATISTICS\n{'─' * 18}```"
    e.add_field(name="Player", value=ctx.author.mention, inline=False)
    e.add_field(name="Wins", value=str(p["wins"]), inline=True)
    e.add_field(name="Games", value=str(p["games"]), inline=True)
    e.add_field(name="Win Rate", value=ratio, inline=True)
    e.add_field(name="Eliminations", value=str(p["eliminations"]), inline=True)
    e.add_field(name="Points", value=str(p["points"]), inline=True)
    e.add_field(name="Items", value=f"🛡 {p['shield']} | 💥 {p['double_kick']} | 🔄 {p['anti_kick']}", inline=False)
    await ctx.send(embed=e)

# ------------------------------------------------------------------------------
# روليت — مطابق لـ Shuruhatik roulette + نظام النقاط
# ------------------------------------------------------------------------------
C_MAIN = 0xD4A017   # amber gold
C_KILL = 0x8B0000    # dark red
C_OK = 0x2E7D32      # dark green
C_INFO = 0x1E3A5F    # deep blue
WAITING_TIME = 27
MAX_SEATS = 40
HOWTO = ("**1-** انضم في اللعبة\n"
         "**2-** ستبدأ الجولة الأولى وسيتم تدوير العجلة واختيار لاعب عشوائي\n"
         "**3-** إذا كنت اللاعب المختار ، فستختار لاعبًا من اختيارك ليتم طرده من اللعبة\n"
         "**4-** يُطرد اللاعب وتبدأ جولة جديدة ، عندما يُطرد جميع اللاعبين ويتبقى لاعبان فقط ، ستدور العجلة ويكون اللاعب المختار هو الفائز باللعبة\n"
         "**5-** كل طرد يمنحك **نقطة** واحدة. افتح 🛒 المتجر واشتري أدوات النجاة: درع (18) أو طرد ثنائي (20) أو طرد عكسي (25)")


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
        else:
            if any(p["id"] == ia.user.id for p in g["players"]):
                return await ia.response.send_message("❌ انت مشارك بالفعل لكي تغير مكانك يجب عليك الخروج من الروليت ثم الدخول مرة اخري", ephemeral=True)
            if len(g["players"]) >= MAX_SEATS:
                return await ia.response.send_message("❌ عدد المشاركين مكتمل", ephemeral=True)
            number = self.number
            if self.custom_id.startswith("join_random"):
                taken = {p["number"] for p in g["players"]}
                free = [n for n in range(1, MAX_SEATS + 1) if n not in taken]
                if not free:
                    return await ia.response.send_message("❌ عدد المشاركين مكتمل", ephemeral=True)
                number = random.choice(free)
            elif number in {p["number"] for p in g["players"]}:
                return await ia.response.send_message("❌ هذا المقعد محجوز.", ephemeral=True)
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
        others = [p for p in players if p["id"] != winner["id"]][:24]
        for i, p in enumerate(others):
            self.add_item(KickBtn(p, row=i // 5))
        self.add_item(WithdrawBtn(gid, row=len(others) // 5))


def shop_embed(uid):
    p = get_player(uid)
    owned = f"🛡 درع: {p['shield']} | 💥 ثنائي: {p['double_kick']} | 🔄 عكسي: {p['anti_kick']}"
    e = discord.Embed(title="🛒 متجر الروليت", color=C_MAIN,
                      description=f"رصيدك: **{p['points']}** نقطة\n{owned}\n\nاختر ما تريد شراءه:")
    for k, v in ITEMS.items():
        e.add_field(name=f"{k}. {v['name']} — {v['price']} نقطة", value=v["desc"], inline=False)
    return e


class ShopOpenBtn(discord.ui.Button):
    def __init__(self, gid, game_id, row=3):
        self.gid = gid
        self.game_id = game_id
        super().__init__(label="🛒 المتجر", style=discord.ButtonStyle.blurple,
                         custom_id=f"shop_roulette_{gid}_{game_id}", row=row)

    async def callback(self, ia):
        view = ShopView(ia.user.id)
        await ia.response.send_message(embed=shop_embed(ia.user.id), view=view, ephemeral=True)
        view.msg = await ia.original_response()


class ShopBtn(discord.ui.Button):
    def __init__(self, uid, key, item, row):
        self.uid = uid
        self.key = key
        self.item = item
        super().__init__(label=f"{item['name']} — {item['price']}", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, ia):
        if ia.user.id != self.uid:
            return await ia.response.send_message("❌ هذا المتجر ملك للاعب آخر.", ephemeral=True)
        p = get_player(ia.user.id)
        if p["points"] < self.item["price"]:
            return await ia.response.send_message(
                f"❌ معاك {p['points']} نقطة وتحتاج {self.item['price']} لشراء {self.item['name']}.",
                ephemeral=True)
        p["points"] -= self.item["price"]
        p[self.item["key"]] += 1
        save_player(ia.user.id, p)
        await ia.response.edit_message(embed=shop_embed(ia.user.id), view=self.view)


class ShopCloseBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(label="إغلاق المتجر", style=discord.ButtonStyle.danger, row=3)

    async def callback(self, ia):
        if ia.user.id != self.view.uid:
            return await ia.response.send_message("❌ هذا المتجر ملك للاعب آخر.", ephemeral=True)
        await ia.response.edit_message(content="🔒 أُغلق المتجر.", embed=None, view=None)


class ShopView(View):
    def __init__(self, uid):
        super().__init__(timeout=120)
        self.uid = uid
        self.msg = None
        for i, (k, v) in enumerate(ITEMS.items()):
            self.add_item(ShopBtn(uid, k, v, row=i))
        self.add_item(ShopCloseBtn())

    async def on_timeout(self):
        for b in self.children:
            b.disabled = True
        if self.msg:
            try:
                await self.msg.edit(view=self)
            except Exception:
                pass


def resolve_kick(kicker, victim, players, g):
    td = get_player(victim["id"])
    desc = ""
    removed = []
    if td["shield"] > 0:
        td["shield"] -= 1
        save_player(victim["id"], td)
        ots = [p for p in players if p["id"] != victim["id"] and p["id"] != kicker["id"]]
        if ots:
            ot = random.choice(ots)
            removed.append(ot)
            desc = f"🛡 <@{victim['id']}> استخدم **الدرع** → <@{ot['id']}> أُقصي بدلاً منه"
            g["log"].append(f"🛡 درع <@{victim['id']}> حوّل الإقصاء إلى <@{ot['id']}>")
        else:
            desc = f"🛡 <@{victim['id']}> استخدم **الدرع** ونجا من الإقصاء!"
            g["log"].append(f"🛡 درع <@{victim['id']}> منع الإقصاء")
    elif td["anti_kick"] > 0:
        td["anti_kick"] -= 1
        save_player(victim["id"], td)
        ots = [p for p in players if p["id"] != victim["id"] and p["id"] != kicker["id"]]
        if ots:
            ot = random.choice(ots)
            removed.append(ot)
            desc = f"🔄 <@{victim['id']}> استخدم **الطرد العكسي** → <@{ot['id']}> أُقصي بدلاً منه"
            g["log"].append(f"🔄 <@{victim['id']}> عكس الإقصاء إلى <@{ot['id']}>")
        else:
            desc = f"🔄 <@{victim['id']}> استخدم **الطرد العكسي** ونجا من الإقصاء!"
            g["log"].append(f"🔄 <@{victim['id']}> عكس الإقصاء")
    else:
        removed.append(victim)
        desc = f"❌ <@{victim['id']}> أُقصي من اللعبة"
        g["log"].append(f"❌ <@{victim['id']}> أُقصي")
        if td["double_kick"] > 0 and len(players) > 2:
            td["double_kick"] -= 1
            save_player(victim["id"], td)
            ots = [p for p in players if p["id"] != victim["id"] and p["id"] != kicker["id"]]
            if ots:
                sc = random.choice(ots)
                removed.append(sc)
                desc += f"\n💥 <@{victim['id']}> استخدم **الطرد الثنائي** → <@{sc['id']}> أُقصي معه"
                g["log"].append(f"💥 <@{victim['id']}> جرّ <@{sc['id']}> معه")
                ep = get_player(victim["id"])
                ep["points"] += 1
                ep["eliminations"] += 1
                save_player(victim["id"], ep)
    if removed:
        kp = get_player(kicker["id"])
        kp["points"] += len(removed)
        kp["eliminations"] += len(removed)
        save_player(kicker["id"], kp)
        g["kill_count"][kicker["id"]] = g["kill_count"].get(kicker["id"], 0) + len(removed)
    return removed, desc


@bot.command(name="روليت", aliases=["roulette", "_روليت"])
async def roulette_cmd(ctx):
    if not ctx.author.guild_permissions.manage_events:
        return await ctx.send("❌ | فقط Manga Events يمكنهم قيام بهذا الامر")
    gid = ctx.channel.id
    if gid in active_roulettes:
        return await ctx.send("❌ | يوجد جولة تعمل الان بالفعل")
    game_id = int(time.time() * 1000)
    g = {"id": game_id, "players": [], "btns": {}, "log": [], "kill_count": {}}
    active_roulettes[gid] = g

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
    v2.add_item(ShopOpenBtn(gid, game_id, row=3))
    for v in (v1, v2):
        for b in v.children:
            if b.number:
                g["btns"][b.number] = b

    m1 = await ctx.send(embed=e, view=v1)
    m2 = await ctx.send(view=v2)
    g["v1"], g["v2"], g["m1"], g["m2"] = v1, v2, m1, m2

    await asyncio.sleep(WAITING_TIME)

    if gid not in active_roulettes:
        return
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
    g["participants"] = [p["id"] for p in g["players"]]
    await ctx.send("✅ | تم توزيع الأرقام على كل لاعب. ستبدأ الجولة الأولى في بضع ثواني...")
    await run_game(ctx, gid)


@bot.command(name="توقف", aliases=["stop"])
async def stop_cmd(ctx):
    if not ctx.author.guild_permissions.manage_events:
        return await ctx.send("❌ | فقط Manga Events يمكنهم قيام بهذا الامر")
    gid = ctx.channel.id
    if gid not in active_roulettes:
        return await ctx.send("❌ لا توجد لعبة قيد التشغيل في الوقت الحالي")
    del active_roulettes[gid]
    await ctx.send(f"❌ | تم طلب إيقاف لعبة روليت من قبل <@{ctx.author.id}>")


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

    gif = await make_gif([{"number": p["number"], "img": p.get("avimg")} for p in players],
                         highlight=len(players) - 1)
    content = f"**{winner['number']}** - <@{winner['id']}>"
    if len(players) <= 2:
        content += "\n:crown: **هذه الجولة الأخيرة ! اللاعب المختار هو اللاعب الفائز في اللعبة.**"
    await ctx.send(content=content, file=discord.File(gif, filename="roulette.gif"))

    if len(players) <= 2:
        pts = random.choice([10, 12, 15, 18, 20, 25])
        pd = get_player(winner["id"])
        pd["points"] += pts
        pd["wins"] += 1
        save_player(winner["id"], pd)
        for uid in g.get("participants", [p["id"] for p in players]):
            pp = get_player(uid)
            pp["games"] += 1
            save_player(uid, pp)
        await ctx.send(f":crown: - فاز <@{winner['id']}> في اللعبة")
        log_text = "\n".join(g["log"]) if g["log"] else "لا يوجد طرد"
        kills_text = "\n".join(f"<@{uid}>: {c}" for uid, c in sorted(g["kill_count"].items(), key=lambda x: -x[1])) or "لا يوجد"
        we = discord.Embed(title="🏆 ملخص الجولة", color=C_MAIN)
        we.set_thumbnail(url=winner.get("avatarURL"))
        we.description = f"`{'─' * 22}`\n**الفائز**\n`{'─' * 22}`"
        we.add_field(name="الفائز", value=f"<@{winner['id']}>", inline=True)
        we.add_field(name="الجائزة", value=f"+{pts} نقطة", inline=True)
        we.add_field(name="اللاعبون", value=str(len(g.get("participants", g["players"]))), inline=True)
        we.add_field(name="الإقصاءات", value=kills_text, inline=False)
        we.add_field(name="سجل الجولة", value=log_text[:1024], inline=False)
        await ctx.send(embed=we)
        del active_roulettes[gid]
        return

    view = KickView(gid, winner, players)
    msg = await ctx.send(f"<@{winner['id']}> لديك **30 ثانية** لإختيار لاعب لطرده", view=view)
    await view.wait()

    if gid not in active_roulettes:
        return
    for b in view.children:
        b.disabled = True
    try:
        await msg.edit(view=view)
    except Exception:
        pass

    choice = view.choice
    if choice and choice[0] == "kick":
        victim = next((p for p in players if p["number"] == choice[1]), None)
        if not victim:
            await ctx.send(f"💣 | تم طرد <@{winner['id']}> من اللعبة لعدم تفاعله ، سيتم بدء الجولة القادمة في بضع ثواني...")
            g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
            return await run_game(ctx, gid)
        removed, desc = resolve_kick(winner, victim, players, g)
        g["players"] = [p for p in g["players"] if not any(r["id"] == p["id"] for r in removed)]
        await ctx.send(f"💣 | تم طرد <@{victim['id']}> من اللعبة ، سيتم بدء الجولة القادمة في بضع ثواني...")
        if desc:
            e = discord.Embed(title="💥 إقصاء", description=desc, color=C_KILL)
            if removed:
                e.set_footer(text=f"⚡ <@{winner['id']}> ربح {len(removed)} نقطة")
            await ctx.send(embed=e)
        await run_game(ctx, gid)
    elif choice and choice[0] == "withdraw":
        await ctx.send(f"💣 | لقد انسحب <@{winner['id']}> من اللعبة ، سيتم بدء الجولة القادمة في بضع ثواني...")
        g["players"] = [p for p in g["players"] if p["id"] != winner["id"]]
        await run_game(ctx, gid)
    else:
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
