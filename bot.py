import os
import logging
import asyncio
import json
import random
import math

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

@bot.check
async def channel_check(ctx):
    return ctx.channel.id in ALLOWED_CHANNELS

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id not in ALLOWED_CHANNELS:
        return

    # كلام حب ليبي
    if "نحبك" in message.content:
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
        data["users"][uid] = {"points": 0, "shield": 0, "double_kick": 0, "anti_kick": 0}
        save_data(data)
    return data["users"][uid]

def save_player(uid, pdata):
    data = load_data()
    data["users"][str(uid)] = pdata
    save_data(data)

active_roulettes = {}

ITEMS = {
    "1": {"name": "درع ضد الطرد", "price": 200, "key": "shield", "desc": "يحميك من الإقصاء لمرة واحدة"},
    "2": {"name": "طرد ثنائي", "price": 150, "key": "double_kick", "desc": "عند إقصائك تأخذ معك شخص آخر"},
    "3": {"name": "طرد مضاد", "price": 250, "key": "anti_kick", "desc": "يعكس الإقصاء على شخص آخر بدلاً منك"},
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
    items_list = f"🛡 درع: {player['shield']} | 💥 طرد ثنائي: {player['double_kick']} | 🔄 طرد مضاد: {player['anti_kick']}"
    await ctx.send(f"⭐ {ctx.author.mention} نقاطك: **{player['points']}**\n{items_list}")

# ------------------------------------------------------------------------------
# روليت متكامل: دائرة تدور + عد تنازلي 20ث + اختيار 15ث
# ------------------------------------------------------------------------------
PLAYER_COLORS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪"]
ROUND_COLORS = [
    discord.Color.red(), discord.Color.orange(), discord.Color.gold(),
    discord.Color.green(), discord.Color.blue(), discord.Color.purple(),
    discord.Color.magenta()
]

# 20 positions around a circle for up to 20 players
CIRCLE_POS = []
for _i in range(20):
    _a = (2 * math.pi * _i) / 20 - math.pi / 2
    _r = 3.5
    _cr = 4 + round(_r * math.cos(_a))
    _cc = 5 + round(_r * math.sin(_a))
    CIRCLE_POS.append((max(0, min(8, _cr)), max(0, min(10, _cc))))

def build_bar(sec):
    return "🟢" * sec + "🔴" * (20 - sec) + f" **{sec}ث**"

def col(i):
    return PLAYER_COLORS[i % len(PLAYER_COLORS)]

def make_circle(alive_ids, ptr_idx=None):
    n = len(alive_ids)
    if n == 0:
        return "```\nلا يوجد لاعبين\n```"
    g = [["   " for _ in range(11)] for _ in range(9)]
    g[4][5] = "⬤  "
    for i, uid in enumerate(alive_ids):
        if i >= len(CIRCLE_POS):
            break
        r, c = CIRCLE_POS[i]
        num = str(i + 1)
        g[r][c] = f"{col(i)}{num:2s}" if len(num) == 1 else f"{col(i)}{num}"
    if ptr_idx is not None and ptr_idx < len(CIRCLE_POS):
        pr, pc = CIRCLE_POS[ptr_idx]
        g[pr][pc] = "🎯" + (" " if pr < 5 else "")
    vis = "\n".join("".join(row) for row in g)
    leg = ""
    for i, uid in enumerate(alive_ids):
        arrow = " ◀️" if ptr_idx is not None and i == ptr_idx else ""
        leg += f"{col(i)} `{i+1}.` <@{uid}>{arrow}\n"
    return f"```\n{vis}\n```\n{leg}"

def join_embed(gid, sec):
    g = active_roulettes.get(gid)
    if not g:
        return discord.Embed(title="🎰 روليت", color=discord.Color.red())
    e = discord.Embed(
        title="🎰 روليت - انضمام",
        description=f"━━━━━━━━━━━━━━━━━━━━━━━━\n{make_circle(g['players'])}\n━━━━━━━━━━━━━━━━━━━━━━━━\n{build_bar(sec)}",
        color=discord.Color.blue()
    )
    e.add_field(name="👥 العدد", value=f"{len(g['players'])} لاعب", inline=True)
    e.set_footer(text="✅ اضغط انضمام")
    return e

class JoinView(View):
    def __init__(self, gid):
        super().__init__(timeout=30)
        self.gid = gid

    @discord.ui.button(label="🎯 انضمام", style=discord.ButtonStyle.green)
    async def join_btn(self, ia, btn):
        if self.gid not in active_roulettes:
            return await ia.response.send_message("❌ انتهت.", ephemeral=True)
        g = active_roulettes[self.gid]
        if ia.user.id in g["players"]:
            return await ia.response.send_message("✅ منضم!", ephemeral=True)
        if len(g["players"]) >= 20:
            return await ia.response.send_message("❌ اقصى عدد 20.", ephemeral=True)
        g["players"].append(ia.user.id)
        g["alive"].append(ia.user.id)
        await ia.response.defer()
        msg = g.get("message")
        if msg:
            try:
                await msg.edit(embed=join_embed(self.gid, g.get("countdown", 20)), view=self)
            except:
                pass

class KickSelect(discord.ui.Select):
    def __init__(self, gid, sid, aids):
        opts = []
        for idx, uid in enumerate(aids):
            if uid != sid:
                opts.append(discord.SelectOption(label=f"🎯 اطرد لاعب {idx+1}", value=str(uid)))
        super().__init__(placeholder="🎯 اختر...", min_values=1, max_values=1, options=opts[:25])
        self.chosen = None

    async def callback(self, ia):
        if ia.user.id != self.view.sid:
            return await ia.response.send_message("❌ مو دورك!", ephemeral=True)
        self.chosen = int(self.values[0])
        self.view.stop()
        await ia.response.defer()

class RoundView(View):
    def __init__(self, gid, sid, aids):
        super().__init__(timeout=15)
        self.sid = sid
        self.gid = gid
        self._sel = KickSelect(gid, sid, aids)
        self.add_item(self._sel)

    @property
    def chosen_id(self):
        return self._sel.chosen

async def spin_wheel(ctx, gid, aids, target, rn, color):
    n = len(aids)
    ti = aids.index(target)
    fr = 12
    msg = None
    for f in range(fr):
        if gid not in active_roulettes:
            return None
        d = 0.08 + (f / fr) * 0.35
        ptr = (ti + (fr - f) * 2) % n if f < fr - 1 else ti
        wh = make_circle(aids, ptr_idx=ptr)
        e = discord.Embed(
            title=f"🔄 جولة {rn}..." if f < fr - 1 else f"🎯 توقفت - جولة {rn}",
            description=f"━━━━━━━━━━━━━━━━━━━━━━━━\n{wh}\n━━━━━━━━━━━━━━━━━━━━━━━━",
            color=color
        )
        if f < fr - 1:
            e.set_footer(text="🔄 الروليت تدور...")
        else:
            e.add_field(name="🎲 المختار", value=f"<@{target}>", inline=False)
            e.set_footer(text="⏱️ لديك 15 ثانية")
        if msg:
            try:
                await msg.edit(embed=e)
            except:
                pass
        else:
            msg = await ctx.send(embed=e)
        await asyncio.sleep(d)
    return msg

@bot.command(name="روليت", aliases=["_روليت", "roulette"])
async def roulette_cmd(ctx):
    if ctx.channel.id != GAME_CHANNEL:
        return
    gid = ctx.channel.id
    if gid in active_roulettes:
        return await ctx.send("❌ في لعبة جارية!")

    active_roulettes[gid] = {
        "players": [ctx.author.id],
        "alive": [ctx.author.id],
        "phase": "joining",
        "creator": ctx.author.id,
        "countdown": 20
    }

    view = JoinView(gid)
    msg = await ctx.send(embed=join_embed(gid, 20), view=view)
    active_roulettes[gid]["message"] = msg

    for sec in range(20, 0, -1):
        if gid not in active_roulettes:
            return
        active_roulettes[gid]["countdown"] = sec
        try:
            await msg.edit(embed=join_embed(gid, sec), view=view)
        except:
            pass
        await asyncio.sleep(1)

    if gid not in active_roulettes:
        return

    for c in view.children:
        c.disabled = True
    try:
        await msg.edit(view=view)
    except:
        pass

    g = active_roulettes[gid]
    if len(g["players"]) < 2:
        e = discord.Embed(title="❌ ما فيه عدد كافي!", color=discord.Color.red())
        await ctx.send(embed=e)
        del active_roulettes[gid]
        return

    await run_game(ctx, gid, msg)

async def run_game(ctx, gid, start_msg):
    game = active_roulettes.get(gid)
    if not game:
        return
    alive = game["alive"][:]
    random.shuffle(alive)
    rn = 0

    e = discord.Embed(
        title="🚀 بدأت اللعبة!",
        description=f"━━━━━━━━━━━━━━━━━━━━━━━━\n{make_circle(alive)}\n━━━━━━━━━━━━━━━━━━━━━━━━\n🔥 **{len(alive)} لاعب**",
        color=discord.Color.green()
    )
    try:
        await start_msg.edit(embed=e, view=None)
    except:
        pass

    while len(alive) > 1:
        rn += 1
        sel = random.choice(alive)
        c = ROUND_COLORS[(rn - 1) % len(ROUND_COLORS)]

        await spin_wheel(ctx, gid, alive, sel, rn, c)
        if gid not in active_roulettes:
            return
        alive = [p for p in active_roulettes[gid]["alive"] if p in alive]

        if len(alive) <= 1:
            break

        if len(alive) == 2:
            other = [p for p in alive if p != sel][0]
            elim = other
            reason = f"⚔️ <@{sel}> طرد <@{other}>"
            await asyncio.sleep(2)
        else:
            view = RoundView(gid, sel, alive)
            await ctx.send("🎯 اختر لاعب:", view=view)
            await view.wait()

            if gid not in active_roulettes:
                return
            alive = [p for p in active_roulettes[gid]["alive"] if p in alive]

            if view.chosen_id is not None and view.chosen_id in alive:
                elim = view.chosen_id
                reason = f"🎯 <@{sel}> اختار <@{elim}>"
            else:
                elim = sel
                reason = f"⏱️ <@{sel}> ما اختار!"

        td = get_player(elim)
        desc = reason

        if td["shield"] > 0:
            td["shield"] -= 1
            save_player(elim, td)
            ots = [p for p in alive if p != elim]
            if ots:
                ot = random.choice(ots)
                desc += f"\n🛡️ <@{elim}> درع! <@{ot}> أُقصي!"
                alive.remove(ot)
            else:
                desc += f"\n🛡️ <@{elim}> درع! نجا!"
        elif td["anti_kick"] > 0:
            td["anti_kick"] -= 1
            save_player(elim, td)
            ots = [p for p in alive if p != elim]
            if ots:
                ot = random.choice(ots)
                desc += f"\n🔄 <@{elim}> عكس! <@{ot}> أُقصي!"
                alive.remove(ot)
        else:
            if elim in alive:
                if td["double_kick"] > 0 and len(alive) > 2:
                    td["double_kick"] -= 1
                    save_player(elim, td)
                    ots = [p for p in alive if p != elim]
                    if ots:
                        sc = random.choice(ots)
                        alive.remove(sc)
                        desc += f"\n💥 <@{elim}> ثنائي! <@{sc}> معه!"
                alive.remove(elim)
                desc += f"\n❌ <@{elim}> أُقصي!"

        if gid in active_roulettes:
            active_roulettes[gid]["alive"] = [p for p in alive]

        wh = make_circle(alive)
        re = discord.Embed(
            title=f"💀 نتيجة جولة {rn}",
            description=f"━━━━━━━━━━━━━━━━━━━━━━━━\n{desc}\n━━━━━━━━━━━━━━━━━━━━━━━━\n🔥 **المتبقي: {len(alive)}**\n{wh}",
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=re)

    if gid not in active_roulettes:
        return

    winner = alive[0]
    pts = random.choice([10, 12, 15, 18, 20, 25])
    pd = get_player(winner)
    pd["points"] += pts
    save_player(winner, pd)

    we = discord.Embed(
        title="🏆 فائز الروليت!",
        description=f"━━━━━━━━━━━━━━━━━━━━━━━━\n👑 <@{winner}>\n⭐ +**{pts}** نقطة\n━━━━━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.gold()
    )
    await ctx.send(embed=we)
    del active_roulettes[gid]

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
