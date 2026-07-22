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
# قاموس الديباجات
# ------------------------------------------------------------------------------
TEMPLATES = {
    "1": """<@&1520098176269418647>
<@&1509890356773130352>** ``` قصة فلم/مسلسل ``` 

 الاسم :   

القصه : 

لمواسم/الحلقات :  

لتقيم : **""",

    "2": """<@&1520098176269418647> 
<@&1509890356773130352>** ``` خبر فلم/مسلسل ``` 

 الاسم :   

الخبر : 

لمصدر :  

تاريخ : **""",

    "3": """<@&1520098176269418647> 
<@&1509890356773130352>** ``` اعلان فلم/مسلسل ``` 

 الاسم :   

الاعلان : 

تاريخ : **""",

    "4": """<@&1520098176269418647> 
<@&1509890356773130352>** ``` تصويت فلم/مسلسل ``` 
[ الاول ] • [ الثاني ]

الاول :33: 
الثاني :33: 

 **""",

    "5": """<@&1520098176269418647> 
<@&1509890356773130352>** ``` مشاهدة فلم/مسلسل ``` 

 الاسم :   

لساعه : 

عدد لحلقات :  

يوم : **""",
}

TEMPLATE_TITLES = {
    "1": "🎬 قصة فلم / مسلسل",
    "2": "📰 خبر فلم / مسلسل",
    "3": "📢 اعلان فلم / مسلسل",
    "4": "📊 تصويت فلم / مسلسل",
    "5": "📺 مشاهدة فلم / مسلسل",
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
    await bot.change_presence(activity=discord.Game(name=".اوامر أو الأرقام 1-5"))

@bot.event
async def on_message(message):
    if message.author.bot:
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

@bot.command(name="1")
async def cmd_1(ctx):
    await ctx.send(f"**🎬 {TEMPLATE_TITLES['1']}**\n```\n{TEMPLATES['1']}\n```")

@bot.command(name="2")
async def cmd_2(ctx):
    await ctx.send(f"**📰 {TEMPLATE_TITLES['2']}**\n```\n{TEMPLATES['2']}\n```")

@bot.command(name="3")
async def cmd_3(ctx):
    await ctx.send(f"**📢 {TEMPLATE_TITLES['3']}**\n```\n{TEMPLATES['3']}\n```")

@bot.command(name="4")
async def cmd_4(ctx):
    await ctx.send(f"**📊 {TEMPLATE_TITLES['4']}**\n```\n{TEMPLATES['4']}\n```")

@bot.command(name="5")
async def cmd_5(ctx):
    await ctx.send(f"**📺 {TEMPLATE_TITLES['5']}**\n```\n{TEMPLATES['5']}\n```")

# ------------------------------------------------------------------------------
# تشغيل البوت
# ------------------------------------------------------------------------------
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.critical("⚠️ ضع توكن البوت في متغير البيئة DISCORD_TOKEN أو في المتغير TOKEN داخل الملف!")
        raise SystemExit(1)
    bot.run(TOKEN, log_handler=None)
