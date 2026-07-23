import os
import logging

import discord
from discord.ext import commands
from discord.ui import View, Select

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=['.', '!', '؟'], intents=intents, help_command=None)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("ohara_templates")

# ------------------------------------------------------------------------------
# الثوابت: معرفات الرومات والتاغات
# ------------------------------------------------------------------------------
CHANNEL_MOVIES = 1528554012612235374
CHANNEL_FOOTBALL = 1528793852222374140
CHANNEL_ANIME = 1528793894115086527

TAG_MOVIES = "<@&1520098176269418647> <@&1509890356773130352>"
TAG_FOOTBALL = "<@&1509890421168279645>"
TAG_ANIME = "<@&1509890302415081492>"

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━\n"

def t(title, fields, tags):
    text = f"**```{title}  ```**\n\n"
    text += "\n\n".join(f"{f} :  " for f in fields)
    text += f"\n\n{SEP}{tags}**"
    return text

def tm(title, fields):
    return t(title, fields, TAG_MOVIES)

def tf(title, fields):
    return t(title, fields, TAG_FOOTBALL)

def ta(title, fields):
    return t(title, fields, TAG_ANIME)

# ------------------------------------------------------------------------------
# ديباجات الأفلام والمسلسلات
# ------------------------------------------------------------------------------
T_MOVIES = {
    "1": tm("📖 قصة فلم/مسلسل", ["📌 الاسم", "📝 القصة", "📺 الموسم/الحلقات", "⭐ التقييم"]),
    "2": tm("📰 خبر فلم/مسلسل", ["📌 الاسم", "📢 الخبر", "📎 المصدر", "📅 التاريخ"]),
    "3": tm("📢 إعلان فلم/مسلسل", ["📌 الاسم", "🎬 الإعلان", "📅 تاريخ الإصدار"]),
    "4": tm("📊 تصويت فلم/مسلسل", ["📌 الاسم", "🔹 الخيار الأول", "🔹 الخيار الثاني"]),
    "5": tm("📺 مشاهدة فلم/مسلسل", ["📌 الاسم", "⏰ الساعة", "🎞️ عدد الحلقات", "📅 اليوم"]),
    "6": tm("📝 مراجعة فلم/مسلسل", ["📌 الاسم", "⭐ التقييم /10", "✅ الإيجابيات", "❌ السلبيات", "💬 الخلاصة"]),
    "7": tm("💡 توصية فلم/مسلسل", ["📌 الاسم", "🏷️ النوع", "🔥 لماذا يستحق المشاهدة", "🎯 يناسب عشاق"]),
    "8": tm("💬 سؤال نقاش", ["❓ السؤال", "📖 تفاصيل أكثر", "🗣️ ما رأيكم"]),
    "9": tm("🧵 نظرية أو توقع", ["📌 العمل", "🔮 النظرية/التوقع", "📚 الأدلة", "🤔 ما رأيكم بهذه النظرية"]),
    "10": tm("⚖️ مقارنة", ["🎬 العمل الأول", "🎬 العمل الثاني", "📊 وجه المقارنة", "🏆 الأفضل برأيك"]),
    "11": tm("🎭 شخصية اليوم", ["👤 اسم الشخصية", "🎬 من العمل", "⭐ سبب الاختيار", "💪 أقوى صفاتها", "💬 اقتباسها الشهير"]),
    "12": tm("💬 اقتباس", ["📜 النص", "🎙️ القائل", "🎬 من العمل", "✍️ تعليقك"]),
    "13": tm("🏆 مسابقة ثقافية", ["❓ السؤال", "🔹 1.", "🔹 2.", "🔹 3.", "🔹 4.", "🎁 الجائزة", "⏳ المدة"]),
    "14": tm("📋 استفتاء الموسم", ["📌 العمل", "❓ السؤال", "👍 نعم", "👎 لا", "🤷 ما عندي رأي"]),
    "15": tm("👥 مشاهدة جماعية", ["📌 العمل", "📅 الموعد", "📍 المكان", "⏱️ المدة التقريبية", "📋 التسجيلات المتاحة"]),
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
    "1": tf("📰 خبر مباراة", ["📌 الفريق", "📢 الخبر", "📎 المصدر", "📅 التاريخ"]),
    "2": tf("✅ نتيجة مباراة", ["🏆 الفريق الأول", "🏆 الفريق الثاني", "⚽ النتيجة", "🌟 نجم المباراة"]),
    "3": tf("📢 إعلان مباراة", ["🏆 المباراة", "📅 التاريخ", "⏰ الوقت", "📍 الملعب"]),
    "4": tf("📊 تصويت", ["📌 الموضوع", "🔹 الخيار الأول", "🔹 الخيار الثاني"]),
    "5": tf("📺 مشاهدة مباراة", ["🏆 المباراة", "📅 التاريخ", "⏰ الساعة", "📡 القناة الناقلة"]),
    "6": tf("📝 مراجعة مباراة", ["🏆 المباراة", "⭐ التقييم /10", "✅ الإيجابيات", "❌ السلبيات", "💬 الخلاصة"]),
    "7": tf("💡 توصية", ["📌 المباراة", "🏷️ البطولة", "🔥 لماذا تستحق المشاهدة", "🎯 تناسب عشاق"]),
    "8": tf("💬 سؤال نقاش", ["❓ السؤال", "📖 تفاصيل أكثر", "🗣️ ما رأيكم"]),
    "9": tf("🔮 توقع", ["🏆 المباراة", "🔮 التوقع", "📚 الأسباب", "🤔 هل تتفق"]),
    "10": tf("⚖️ مقارنة", ["👤 اللاعب الأول", "👤 اللاعب الثاني", "📊 وجه المقارنة", "🏆 الأفضل برأيك"]),
    "11": tf("🎭 لاعب اليوم", ["👤 اسم اللاعب", "🏆 النادي", "⭐ الأداء", "⚽ إحصائياته"]),
    "12": tf("💬 اقتباس", ["📜 النص", "🎙️ القائل", "🏆 المناسبة", "✍️ تعليقك"]),
    "13": tf("🏆 مسابقة", ["❓ السؤال", "🔹 1.", "🔹 2.", "🔹 3.", "🔹 4.", "🎁 الجائزة", "⏳ المدة"]),
    "14": tf("📋 استفتاء", ["📌 الموضوع", "❓ السؤال", "👍 نعم", "👎 لا", "🤷 ما عندي رأي"]),
    "15": tf("👥 مشاهدة جماعية", ["🏆 المباراة", "📅 الموعد", "📍 المكان", "⏱️ المدة", "📋 التسجيلات"]),
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
    "1": ta("📖 قصة انمي", ["📌 الاسم", "📝 القصة", "📺 عدد الحلقات", "⭐ التقييم"]),
    "2": ta("📰 خبر انمي", ["📌 الاسم", "📢 الخبر", "📎 المصدر", "📅 التاريخ"]),
    "3": ta("📢 إعلان انمي", ["📌 الاسم", "🎬 الإعلان", "📅 تاريخ الإصدار"]),
    "4": ta("📊 تصويت انمي", ["📌 الاسم", "🔹 الخيار الأول", "🔹 الخيار الثاني"]),
    "5": ta("📺 مشاهدة انمي", ["📌 الاسم", "⏰ الساعة", "🎞️ الحلقة", "📅 اليوم"]),
    "6": ta("📝 مراجعة انمي", ["📌 الاسم", "⭐ التقييم /10", "✅ الإيجابيات", "❌ السلبيات", "💬 الخلاصة"]),
    "7": ta("💡 توصية انمي", ["📌 الاسم", "🏷️ النوع", "🔥 لماذا يستحق المشاهدة", "🎯 يناسب عشاق"]),
    "8": ta("💬 سؤال نقاش", ["❓ السؤال", "📖 تفاصيل أكثر", "🗣️ ما رأيكم"]),
    "9": ta("🧵 نظرية انمي", ["📌 العمل", "🔮 النظرية/التوقع", "📚 الأدلة", "🤔 ما رأيكم بهذه النظرية"]),
    "10": ta("⚖️ مقارنة", ["🎬 الانمي الأول", "🎬 الانمي الثاني", "📊 وجه المقارنة", "🏆 الأفضل برأيك"]),
    "11": ta("🎭 شخصية اليوم", ["👤 اسم الشخصية", "🎬 من الانمي", "⭐ سبب الاختيار", "💪 أقوى صفاتها", "💬 اقتباسها الشهير"]),
    "12": ta("💬 اقتباس", ["📜 النص", "🎙️ القائل", "🎬 من العمل", "✍️ تعليقك"]),
    "13": ta("🏆 مسابقة انمي", ["❓ السؤال", "🔹 1.", "🔹 2.", "🔹 3.", "🔹 4.", "🎁 الجائزة", "⏳ المدة"]),
    "14": ta("📋 استفتاء انمي", ["📌 العمل", "❓ السؤال", "👍 نعم", "👎 لا", "🤷 ما عندي رأي"]),
    "15": ta("👥 مشاهدة جماعية", ["📌 العمل", "📅 الموعد", "📍 المكان", "⏱️ المدة التقريبية", "📋 التسجيلات"]),
}

TITLES_ANIME = {
    "1": "📖 قصة انمي", "2": "📰 خبر انمي", "3": "📢 إعلان انمي",
    "4": "📊 تصويت انمي", "5": "📺 مشاهدة انمي", "6": "📝 مراجعة انمي",
    "7": "💡 توصية", "8": "💬 سؤال نقاش", "9": "🧵 نظرية انمي",
    "10": "⚖️ مقارنة", "11": "🎭 شخصية اليوم", "12": "💬 اقتباس",
    "13": "🏆 مسابقة انمي", "14": "📋 استفتاء انمي", "15": "👥 مشاهدة جماعية",
}

# ------------------------------------------------------------------------------
# الربط بين الشات والديباجات
# ------------------------------------------------------------------------------
CHANNEL_CATS = {
    CHANNEL_MOVIES: {"name": "أفلام ومسلسلات", "templates": T_MOVIES, "titles": TITLES_MOVIES, "emoji": "🎬"},
    CHANNEL_FOOTBALL: {"name": "كورة", "templates": T_FOOTBALL, "titles": TITLES_FOOTBALL, "emoji": "⚽"},
    CHANNEL_ANIME: {"name": "انمي", "templates": T_ANIME, "titles": TITLES_ANIME, "emoji": "🎌"},
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
        await interaction.response.send_message(
            f"**{title}**\n\nقم بنسخ النص التالي واستخدامه:\n```\n{text}\n```",
            ephemeral=True
        )

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
    await bot.change_presence(activity=discord.Game(name=".اوامر في شات التصنيف"))

ALLOWED_CHANNELS = {CHANNEL_MOVIES, CHANNEL_FOOTBALL, CHANNEL_ANIME}

@bot.check
async def channel_check(ctx):
    return ctx.channel.id in ALLOWED_CHANNELS

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id not in ALLOWED_CHANNELS:
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
        embed.add_field(name="📋 النص:", value=f"```\n{template_text}\n```", inline=False)
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
        await ctx.send(f"**{cat['titles'][key]}**\n```\n{cat['templates'][key]}\n```")
    return cmd

for _num in range(1, 16):
    bot.command(name=str(_num))(make_template_cmd(_num))

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
