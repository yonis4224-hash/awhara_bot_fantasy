import os
import logging
import asyncio
import json
import random

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
        data["users"][uid] = {"points": 0, "shield": 0, "double_kick": 0, "anti_kick": 0, "extra_life": 0}
        save_data(data)
    return data["users"][uid]

def save_player(uid, pdata):
    data = load_data()
    data["users"][str(uid)] = pdata
    save_data(data)

active_roulettes = {}
next_roulette_id = 0

ITEMS = {
    "1": {"name": "🛡️ درع", "price": 200, "key": "shield", "desc": "يعكس الإقصاء على المهاجم"},
    "2": {"name": "🔥 طرد مزدوج", "price": 150, "key": "double_kick", "desc": "يطرد شخصين بدلاً من واحد"},
    "3": {"name": "🔄 طرد مضاد", "price": 250, "key": "anti_kick", "desc": "يعكس الطرد على شخص آخر غيرك"},
    "4": {"name": "💖 حياة إضافية", "price": 130, "key": "extra_life", "desc": "يعيدك للحياة بعد الإقصاء مرة"},
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
        return await ctx.send("❌ استخدم `.شراء 1` أو `2` أو `3` أو `4`")
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
    items_list = f"🛡 درع: {player['shield']} | 💥 طرد مزدوج: {player['double_kick']} | 🔄 طرد مضاد: {player['anti_kick']} | 💖 حياة: {player['extra_life']}"
    await ctx.send(f"⭐ {ctx.author.mention} نقاطك: **{player['points']}**\n{items_list}")

# ------------------------------------------------------------------------------
# روليت على نمط Fizbo - دائرة ملونة + 15 ثانية للاختيار
# ------------------------------------------------------------------------------
import math

PLAYER_COLORS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚪", "🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬜", "❤️", "🧡", "💛", "💚"]

def assign_colors(player_ids):
    return {uid: PLAYER_COLORS[i % len(PLAYER_COLORS)] for i, uid in enumerate(player_ids)}

def build_circle_display(players, colors):
    n = len(players)
    if n == 0:
        return "لا يوجد لاعبين"
    positions = []
    for i, uid in enumerate(players):
        angle = (2 * math.pi * i) / n - math.pi / 2
        r = 3
        x = round(r * math.cos(angle))
        y = round(r * math.sin(angle))
        positions.append((x, y, uid, colors.get(uid, "⚪"), i + 1))
    size = 7
    grid = [["   " for _ in range(size)] for _ in range(size)]
    for x, y, uid, color, num in positions:
        cx = y + 3
        cy = x + 3
        if 0 <= cx < size and 0 <= cy < size:
            grid[cy][cx] = f"{color}{num}".ljust(3)
    lines = ["╔══════════════════╗"]
    for row in grid:
        lines.append("║ " + "".join(row) + " ║")
    lines.append("╚══════════════════╝")
    return "```\n" + "\n".join(lines) + "\n```"

def build_player_list_colored(players, colors):
    lines = []
    for i, uid in enumerate(players):
        lines.append(f"{colors.get(uid, '⚪')} `{i+1}` <@{uid}>")
    return "\n".join(lines)

def build_countdown_bar(seconds_left, total=20):
    filled = seconds_left
    empty = total - seconds_left
    bar = "▓" * filled + "░" * empty
    return f"```{bar}```⏱️ **{seconds_left}ث**"

class RouletteView(View):
    def __init__(self, gid, creator_id):
        super().__init__(timeout=180)
        self.gid = gid
        self.creator_id = creator_id

    def build_lobby_embed(self, game):
        players = game["players"]
        colors = game["colors"]
        circle = build_circle_display(players, colors)
        player_list = build_player_list_colored(players, colors)
        embed = discord.Embed(title="🎰 روليت - لعبة الإقصاء", color=discord.Color.dark_purple())
        embed.add_field(name="🎡 دائرة اللاعبين", value=circle, inline=False)
        embed.add_field(name=f"👥 اللاعبون ({len(players)})", value=player_list, inline=False)
        embed.set_footer(text="🎯 اضغط انضمام | المنشئ يضغط بدء")
        return embed

    async def update_lobby(self, interaction):
        if self.gid not in active_roulettes:
            return
        await interaction.response.edit_message(embed=self.build_lobby_embed(active_roulettes[self.gid]), view=self)

    @discord.ui.button(label="🎯 انضمام", style=discord.ButtonStyle.green)
    async def join_btn(self, interaction, button):
        if self.gid not in active_roulettes:
            return await interaction.response.send_message("❌ اللعبة انتهت.", ephemeral=True)
        game = active_roulettes[self.gid]
        if game["phase"] != "joining":
            return await interaction.response.send_message("❌ اللعبة بدأت!", ephemeral=True)
        uid = interaction.user.id
        if uid in game["players"]:
            return await interaction.response.send_message("✅ أنت منضم!", ephemeral=True)
        if len(game["players"]) >= 20:
            return await interaction.response.send_message("❌ اكتمل العدد (20).", ephemeral=True)
        num = len(game["players"])
        game["players"].append(uid)
        game["alive"].append(uid)
        game["colors"][uid] = PLAYER_COLORS[num % len(PLAYER_COLORS)]
        await self.update_lobby(interaction)

    @discord.ui.button(label="▶️ بدء", style=discord.ButtonStyle.blurple)
    async def start_btn(self, interaction, button):
        if self.gid not in active_roulettes:
            return await interaction.response.send_message("❌ لا توجد لعبة.", ephemeral=True)
        game = active_roulettes[self.gid]
        if game["phase"] != "joining":
            return await interaction.response.send_message("❌ اللعبة بدأت!", ephemeral=True)
        if interaction.user.id != game["creator"]:
            return await interaction.response.send_message("❌ فقط المنشئ يبدأ.", ephemeral=True)
        if len(game["players"]) < 2:
            return await interaction.response.send_message("❌ لازم لاعبين.", ephemeral=True)
        game["phase"] = "countdown"
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=self.build_lobby_embed(game), view=self)
        await run_countdown(interaction.channel, self.gid)

    @discord.ui.button(label="⏹ إلغاء", style=discord.ButtonStyle.red)
    async def cancel_btn(self, interaction, button):
        if self.gid not in active_roulettes:
            return await interaction.response.send_message("❌ لا توجد لعبة.", ephemeral=True)
        game = active_roulettes[self.gid]
        if game["phase"] != "joining":
            return await interaction.response.send_message("❌ اللعبة بدأت!", ephemeral=True)
        if interaction.user.id != game["creator"]:
            return await interaction.response.send_message("❌ فقط المنشئ يلغي.", ephemeral=True)
        del active_roulettes[self.gid]
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=discord.Embed(title="⏹ أُلغيت", color=discord.Color.red()), view=self)

class EliminateView(View):
    def __init__(self, gid, attacker_id, targets, colors):
        super().__init__(timeout=15)
        self.gid = gid
        self.attacker_id = attacker_id
        self.chosen = None
        self.msg = None
        for i, uid in enumerate(targets):
            color = colors.get(uid, "⚪")
            btn = discord.ui.Button(label=f"{color} {i+1}", style=discord.ButtonStyle.secondary, custom_id=str(uid))
            btn.callback = self.make_callback(uid)
            self.add_item(btn)

    def make_callback(self, uid):
        async def callback(interaction):
            if interaction.user.id != self.attacker_id:
                return await interaction.response.send_message("❌ ما دورك!", ephemeral=True)
            game = active_roulettes.get(self.gid)
            if not game or game["phase"] != "playing":
                return await interaction.response.send_message("❌ اللعبة انتهت.", ephemeral=True)
            self.chosen = uid
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
        return callback

    async def on_timeout(self):
        self.chosen = None
        for child in self.children:
            child.disabled = True
        self.stop()

@bot.command(name="روليت", aliases=["_روليت", "roulette"])
async def roulette_cmd(ctx):
    if ctx.channel.id != GAME_CHANNEL:
        return
    global next_roulette_id
    gid = ctx.channel.id
    if gid in active_roulettes:
        return await ctx.send("❌ في لعبة جارية! اضغط انضمام.")
    colors = {ctx.author.id: PLAYER_COLORS[0]}
    active_roulettes[gid] = {
        "players": [ctx.author.id], "alive": [ctx.author.id],
        "colors": colors, "phase": "joining", "creator": ctx.author.id,
        "round_num": 0, "rid": next_roulette_id
    }
    next_roulette_id += 1
    view = RouletteView(gid, ctx.author.id)
    msg = await ctx.send(embed=view.build_lobby_embed(active_roulettes[gid]), view=view)
    active_roulettes[gid]["message"] = msg

async def run_countdown(channel, gid):
    game = active_roulettes.get(gid)
    if not game:
        return
    msg = game["message"]
    players = game["players"][:]
    colors = game["colors"]
    for sec in range(20, 0, -1):
        if gid not in active_roulettes:
            return
        circle = build_circle_display(players, colors)
        plist = build_player_list_colored(players, colors)
        embed = discord.Embed(title=f"⏱️ {sec} | 🎰 روليت", color=discord.Color.dark_purple())
        embed.add_field(name="🎡 دائرة اللاعبين", value=circle, inline=False)
        embed.add_field(name=f"👥 اللاعبون ({len(players)})", value=plist, inline=False)
        embed.add_field(name="⏳ العد التنازلي", value=build_countdown_bar(sec), inline=False)
        embed.set_footer(text="🚀 اللعبة ستبدأ قريباً")
        try:
            await msg.edit(embed=embed)
        except:
            pass
        await asyncio.sleep(1)
    if gid not in active_roulettes:
        return
    await run_roulette(channel, gid)

async def run_roulette(channel, gid):
    game = active_roulettes.get(gid)
    if not game:
        return
    game["phase"] = "playing"
    alive = game["alive"][:]
    colors = game["colors"]
    rid = game["rid"]
    msg = game["message"]
    round_num = 0
    while len(alive) > 1:
        round_num += 1
        game["round_num"] = round_num
        await asyncio.sleep(2)
        random.shuffle(alive)
        attacker = random.choice(alive)
        targets = [p for p in alive if p != attacker]
        attacker_color = colors.get(attacker, "⚪")
        circle = build_circle_display(alive, colors)
        plist = build_player_list_colored(alive, colors)
        embed = discord.Embed(title=f"🎯 الجولة {round_num}", color=discord.Color.orange())
        embed.add_field(name="🎡 دائرة اللاعبين", value=circle, inline=False)
        embed.add_field(name=f"👥 اللاعبون ({len(alive)})", value=plist, inline=False)
        embed.set_footer(text=f"اختر ضحيتك خلال 15 ثانية")
        msg2 = f"🔄 {attacker_color} <@{attacker}> **, اختر من تريد إقصاءه!** (⏱️ 15 ثانية)"
        await channel.send(msg2)
        elim_view = EliminateView(gid, attacker, targets, colors)
        elim_msg = await channel.send(embed=embed, view=elim_view)
        elim_view.msg = elim_msg
        await elim_view.wait()
        if gid not in active_roulettes:
            return
        try:
            await elim_msg.edit(view=elim_view)
        except:
            pass
        if elim_view.chosen is None:
            victim = random.choice(targets)
            await channel.send(f"⏱️ انتهى الوقت! <@{victim}> أُقصي عشوائياً!")
        else:
            victim = elim_view.chosen
        attacker_data = get_player(attacker)
        victim_data = get_player(victim)
        dead_this_round = []
        if victim_data["extra_life"] > 0:
            dead_this_round.append(victim)
            victim_data["extra_life"] -= 1
            save_player(victim, victim_data)
            await channel.send(f"💖 <@{victim}> استخدم **الحياة الإضافية**! عاد للحياة!")
            dead_this_round.remove(victim)
        elif victim_data["shield"] > 0:
            victim_data["shield"] -= 1
            save_player(victim, victim_data)
            dead_this_round.append(attacker)
            await channel.send(f"🛡️ <@{victim}> استخدم **الدرع**! انعكس الإقصاء على <@{attacker}>!")
        elif victim_data["anti_kick"] > 0:
            victim_data["anti_kick"] -= 1
            save_player(victim, victim_data)
            others = [p for p in alive if p != victim and p != attacker]
            if others:
                other = random.choice(others)
                dead_this_round.append(other)
                await channel.send(f"🔄 <@{victim}> استخدم **الطرد المضاد**! <@{other}> أُقصي بدلاً عنه!")
            else:
                dead_this_round.append(victim)
                await channel.send(f"❌ <@{victim}> أُقصي!")
        else:
            dead_this_round.append(victim)
            await channel.send(f"❌ <@{victim}> أُقصي!")
        attacker_still_alive = attacker not in dead_this_round
        if attacker_still_alive and attacker_data["double_kick"] > 0 and len(alive) > 2:
            others_left = [p for p in alive if p not in dead_this_round and p != attacker]
            if others_left:
                extra_victim = random.choice(others_left)
                attacker_data["double_kick"] -= 1
                save_player(attacker, attacker_data)
                dead_this_round.append(extra_victim)
                await channel.send(f"🔥 <@{attacker}> استخدم **الطرد المزدوج**! <@{extra_victim}> أُقصي معه!")
        for uid in dead_this_round:
            if uid in alive:
                alive.remove(uid)
        game["alive"] = alive[:]
        circle = build_circle_display(alive, colors)
        plist = build_player_list_colored(alive, colors)
        embed = discord.Embed(title=f"💀 بعد الجولة {round_num} — المتبقي {len(alive)}", color=discord.Color.dark_red())
        embed.add_field(name="🎡 دائرة اللاعبين", value=circle, inline=False)
        embed.add_field(name=f"👥 المتبقون ({len(alive)})", value=plist, inline=False)
        embed.set_footer(text=f"جولة {round_num}")
        await channel.send(embed=embed)
    winner = alive[0]
    points = random.choice([10, 12, 15, 18, 20, 25])
    pdata = get_player(winner)
    pdata["points"] += points
    save_player(winner, pdata)
    winner_color = colors.get(winner, "⚪")
    embed = discord.Embed(
        title="🏆 فائز الروليت!",
        description=f"━━━━━━━━━━━━━━━━━━━━━━━━\n{winner_color} 👑 <@{winner}>\n⭐ +**{points}** نقطة\n━━━━━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.gold()
    )
    await channel.send(embed=embed)
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
