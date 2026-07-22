import os
import logging

import discord
from discord.ext import commands
from discord.ui import View, Select, Button

# إعداد الصلاحيات (Intents)
intents = discord.Intents.default()
intents.message_content = True

# إنشاء كائن البوت مع البادئة (Prefix)
bot = commands.Bot(command_prefix=['.', '!', '؟'], intents=intents, help_command=None)

# ------------------------------------------------------------------------------
# إعداد التسجيل (Logging)
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("ohara_templates")

# ------------------------------------------------------------------------------
# الروم المصرح به (البوت يشتغل في روم واحد فقط)
# ------------------------------------------------------------------------------
ALLOWED_CHANNEL_ID = 1528566822935330989

# ------------------------------------------------------------------------------
# قاموس الديباجات
# ------------------------------------------------------------------------------
TEMPLATES = {
    "1": """```
╔══════════════════════════╗
║       📖 قصة فلم/مسلسل      ║
╚══════════════════════════╝```

📌 الاسم :  

📝 القصة :  

📺 الموسم/الحلقات :  

⭐ التقييم :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "2": """```
╔══════════════════════════╗
║       📰 خبر فلم/مسلسل      ║
╚══════════════════════════╝```

📌 الاسم :  

📢 الخبر :  

📎 المصدر :  

📅 التاريخ :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "3": """```
╔══════════════════════════╗
║      📢 إعلان فلم/مسلسل     ║
╚══════════════════════════╝```

📌 الاسم :  

🎬 الإعلان :  

📅 تاريخ الإصدار :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "4": """```
╔══════════════════════════╗
║       📊 تصويت فلم/مسلسل     ║
╚══════════════════════════╝```

📌 الاسم :  

🔹 الخيار الأول :  
🔹 الخيار الثاني :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "5": """```
╔══════════════════════════╗
║      📺 مشاهدة فلم/مسلسل    ║
╚══════════════════════════╝```

📌 الاسم :  

⏰ الساعة :  

🎞️ عدد الحلقات :  

📅 اليوم :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "6": """```
╔══════════════════════════╗
║      📝 مراجعة فلم/مسلسل    ║
╚══════════════════════════╝```

📌 الاسم :  

⭐ التقييم : /10

✅ الإيجابيات :  

❌ السلبيات :  

💬 الخلاصة :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "7": """```
╔══════════════════════════╗
║       💡 توصية فلم/مسلسل    ║
╚══════════════════════════╝```

📌 الاسم :  

🏷️ النوع :  

🔥 لماذا يستحق المشاهدة :  

🎯 يناسب عشاق :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "8": """```
╔══════════════════════════╗
║      💬 سؤال نقاش          ║
╚══════════════════════════╝```

❓ السؤال :  

📖 تفاصيل أكثر :  

🗣️ ما رأيكم؟  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "9": """```
╔══════════════════════════╗
║      🧵 نظرية أو توقع       ║
╚══════════════════════════╝```

📌 العمل :  

🔮 النظرية/التوقع :  

📚 الأدلة :  

🤔 ما رأيكم بهذه النظرية؟  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "10": """```
╔══════════════════════════╗
║       ⚖️ مقارنة             ║
╚══════════════════════════╝```

🎬 العمل الأول :  

🎬 العمل الثاني :  

📊 وجه المقارنة :  

🏆 الأفضل برأيك :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "11": """```
╔══════════════════════════╗
║      🎭 شخصية اليوم         ║
╚══════════════════════════╝```

👤 اسم الشخصية :  

🎬 من العمل :  

⭐ سبب الاختيار :  

💪 أقوى صفاتها :  

💬 اقتباسها الشهير :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "12": """```
╔══════════════════════════╗
║       💬 اقتباس             ║
╚══════════════════════════╝```

📜 النص :  

🎙️ القائل :  

🎬 من العمل :  

✍️ تعليقك :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "13": """```
╔══════════════════════════╗
║     🏆 مسابقة ثقافية        ║
╚══════════════════════════╝```

❓ السؤال :  

🔹 1.  
🔹 2.  
🔹 3.  
🔹 4.  

🎁 الجائزة :  

⏳ المدة :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "14": """```
╔══════════════════════════╗
║      📋 استفتاء الموسم       ║
╚══════════════════════════╝```

📌 العمل :  

❓ السؤال :  

👍 نعم  
👎 لا  
🤷 ما عندي رأي  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",

    "15": """```
╔══════════════════════════╗
║     👥 مشاهدة جماعية        ║
╚══════════════════════════╝```

📌 العمل :  

📅 الموعد :  

📍 المكان :  

⏱️ المدة التقريبية :  

📋 التسجيلات المتاحة :  

━━━━━━━━━━━━━━━━━━━━━━━━
<@&1520098176269418647> <@&1509890356773130352>""",
}

TEMPLATE_TITLES = {
    "1": "🎬 قصة فلم / مسلسل",
    "2": "📰 خبر فلم / مسلسل",
    "3": "📢 اعلان فلم / مسلسل",
    "4": "📊 تصويت فلم / مسلسل",
    "5": "📺 مشاهدة فلم / مسلسل",
    "6": "📝 مراجعة فلم / مسلسل",
    "7": "💡 توصية",
    "8": "💬 سؤال نقاش",
    "9": "🧵 نظرية أو توقع",
    "10": "⚖️ مقارنة",
    "11": "🎭 شخصية اليوم",
    "12": "💬 اقتباس",
    "13": "🏆 مسابقة ثقافية",
    "14": "📋 استفتاء الموسم",
    "15": "👥 مشاهدة جماعية",
}

# ------------------------------------------------------------------------------
# واجهة التفاعل (UI View)
# ------------------------------------------------------------------------------
class TemplateSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 - قصة فلم / مسلسل", description="ديباجة عرض تفاصيل وقصة عمل سينمائي", emoji="🎬", value="1"),
            discord.SelectOption(label="2 - خبر فلم / مسلسل", description="ديباجة لنشر آخر الأخبار والتحديثات", emoji="📰", value="2"),
            discord.SelectOption(label="3 - اعلان فلم / مسلسل", description="ديباجة الإعلانات والتريلرات", emoji="📢", value="3"),
            discord.SelectOption(label="4 - تصويت فلم / مسلسل", description="ديباجة الاستفتائات والتصويتات", emoji="📊", value="4"),
            discord.SelectOption(label="5 - مشاهدة فلم / مسلسل", description="ديباجة مواعيد وتفاصيل العرض", emoji="📺", value="5"),
            discord.SelectOption(label="6 - مراجعة فلم / مسلسل", description="مراجعة وتقييم العمل مع الإيجابيات والسلبيات", emoji="📝", value="6"),
            discord.SelectOption(label="7 - توصية", description="اقتراح عمل يستحق المشاهدة", emoji="💡", value="7"),
            discord.SelectOption(label="8 - سؤال نقاش", description="طرح سؤال للنقاش حول عمل معين", emoji="💬", value="8"),
            discord.SelectOption(label="9 - نظرية أو توقع", description="نظرية او توقع حول احداث عمل", emoji="🧵", value="9"),
            discord.SelectOption(label="10 - مقارنة", description="مقارنة بين عملين او شخصيتين", emoji="⚖️", value="10"),
            discord.SelectOption(label="11 - شخصية اليوم", description="تسليط الضوء على شخصية مميزة", emoji="🎭", value="11"),
            discord.SelectOption(label="12 - اقتباس", description="مشاركة اقتباس من عمل مع التعليق", emoji="💬", value="12"),
            discord.SelectOption(label="13 - مسابقة ثقافية", description="مسابقة وسؤال ثقافي للجمهور", emoji="🏆", value="13"),
            discord.SelectOption(label="14 - استفتاء الموسم", description="استفتاء حول موسم او حلقة", emoji="📋", value="14"),
            discord.SelectOption(label="15 - مشاهدة جماعية", description="تنظيم مشاهدة جماعية لعمل", emoji="👥", value="15"),
        ]
        super().__init__(placeholder="اختر الديباجة المطلوبة من القائمة...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_val = self.values[0]
        template_text = TEMPLATES.get(selected_val, "غير متوفرة")
        title = TEMPLATE_TITLES.get(selected_val, "ديباجة")
        await interaction.response.send_message(
            f"**{title}**\n\nقم بنسخ النص التالي واستخدامه:\n```\n{template_text}\n```",
            ephemeral=True
        )

class TemplateView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TemplateSelect())

# ------------------------------------------------------------------------------
# أحداث البوت
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    log.info("البوت جاهز: %s (id=%s)", bot.user, bot.user.id)
    await bot.change_presence(activity=discord.Game(name=".اوامر أو الأرقام 1-15"))

@bot.check
async def channel_check(ctx):
    return ctx.channel.id == ALLOWED_CHANNEL_ID

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != ALLOWED_CHANNEL_ID:
        return
    content = message.content.strip()
    if content in TEMPLATES:
        template_text = TEMPLATES[content]
        title = TEMPLATE_TITLES[content]
        embed = discord.Embed(
            title=f"✨ {title}",
            description="انسخ النص أدناه واستخدمه:",
            color=discord.Color.gold()
        )
        embed.add_field(name="📋 النص:", value=f"```\n{template_text}\n```", inline=False)
        embed.set_footer(text=f"تم الطلب بواسطة {message.author.display_name}", icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)
        await bot.process_commands(message)
        return
    await bot.process_commands(message)

# ------------------------------------------------------------------------------
# الأوامر
# ------------------------------------------------------------------------------
@bot.command(name="اوامر", aliases=["أوامر", "ديباجات", "ديباجة", "help", "الاوامر"])
async def show_commands(ctx):
    embed = discord.Embed(
        title="🎬 قائمة ديباجات الأفلام والمسلسلات",
        description="اكتب **رقم الديباجة** (مثال: `.1` أو `1`) أو استخدم القائمة التفاعلية:",
        color=discord.Color.blue()
    )
    for key, title in TEMPLATE_TITLES.items():
        embed.add_field(name=f"الرقم: `{key}`", value=title, inline=False)
    embed.set_footer(text="اختر من القائمة بالأسفل!")
    await ctx.send(embed=embed, view=TemplateView())

def make_template_cmd(num):
    key = str(num)
    async def cmd(ctx):
        await ctx.send(f"**{TEMPLATE_TITLES[key]}**\n```\n{TEMPLATES[key]}\n```")
    return cmd

for _num in range(1, 16):
    bot.command(name=str(_num))(make_template_cmd(_num))

# ------------------------------------------------------------------------------
# تشغيل البوت
# ------------------------------------------------------------------------------
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.critical("⚠️ ضع توكن البوت في متغير البيئة DISCORD_TOKEN أو في المتغير TOKEN داخل الملف!")
        raise SystemExit(1)

    # خادم HTTP بسيط لإرضاء Render (لأنه Web Service يتطلب منفذ مفتوح)
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
