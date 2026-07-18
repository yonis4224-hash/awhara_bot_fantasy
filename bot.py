import os
import asyncio
import traceback
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord
from discord.ext import commands
from discord import app_commands

import db
import engine
import game_data
import views


# ---------------------------------------------------------------------------
# Health server (for Render free‑tier)
# ---------------------------------------------------------------------------
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ohara bot is running")

    def log_message(self, *args):
        pass


def _start_web_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    server.serve_forever()


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,  # we use our own help
    activity=discord.Game(name="!مساعدة"),
)

TOKEN = os.getenv("DISCORD_TOKEN")

POS_ARABIC = {"GK": "حارس", "DEF": "دفاع", "MID": "وسط", "ATT": "هجوم"}
POS_EMOJI = {"GK": "🧤", "DEF": "🛡️", "MID": "🎽", "ATT": "⚽"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_state(user):
    coach = db.get_coach(str(user.id))
    if not coach or not coach["team_id"]:
        return None, None
    team = db.get_team(coach["team_id"])
    players = db.team_players(team["id"])
    return team, players


def team_embed(team, players):
    e = discord.Embed(
        title=f"⚽ {team['name']}",
        color=discord.Color.green(),
    )
    e.add_field(name="💰 الميزانية", value=f"{team['budget']}م", inline=True)
    e.add_field(name="🟢 الخبرة", value=f"{team['xp']} نقطة", inline=True)
    e.add_field(name="📐 التشكيل", value=team["formation"], inline=True)
    e.add_field(name="🎯 الخطة", value=team["tactic"], inline=True)
    e.add_field(
        name="🏋️ التدريب",
        value=f"{team['training_invest']} نقطة",
        inline=True,
    )

    if players:
        lines = []
        for p in players:
            pos = POS_ARABIC.get(p["position"], p["position"])
            lines.append(f"`{p['id']}` **{p['name']}** — {pos} | ريت {p['rating']} | {p['price']}م")
        e.add_field(name="اللاعبون", value="\n".join(lines), inline=False)
    else:
        e.add_field(name="اللاعبون", value="لا توجد لاعبين بعد.", inline=False)

    return e


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
@bot.event
async def on_ready():
    db.init_db()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name="⚽ أوهارا فانتزب")
    )
    print(f"✅ أوهارا المدرب الأفضل جاهز: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")


@bot.event
async def on_guild_join(guild):
    embed = discord.Embed(
        title="⚽ أهلاً بك في أوهارا فانتزب!",
        description=(
            "أقوى بوت لإدارة فرق كرة القدم في ديسكورد.\n\n"
            "**البداية السريعة:**\n"
            "1️⃣ اكتب `!انشاء` لإنشاء فريق أساسي (11 لاعباً)\n"
            "2️⃣ اكتب `!فريقي` لفتح لوحة التحكم بالأزرار\n"
            "3️⃣ اكتب `!دوري_جديد انجليزي` لإنشاء دوري، و`!انضمام <رقم>` لزملائك\n\n"
            "اكتب `!مساعدة` لعرض كل الأوامر."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="أوهارا فانتزب — مدربك الرقمي الأفضل")
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            await ch.send(embed=embed)
            break


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏱️ تهدأ شوي!",
            description=f"انتظر {error.retry_after:.0f} ثانية قبل ما تستخدم الأمر مرة ثانية.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ ناقص معلومة!",
            description=f"استخدام الأمر: `!{ctx.command.name} {ctx.command.signature}`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ خطأ في الإدخال!",
            description="تأكد من صحة الأرقام والقيم المدخلة.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        embed = discord.Embed(
            title="❌ خطأ غير متوقع",
            description=str(error)[:1000],
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        traceback.print_exception(type(error), error, error.__traceback__)


# ---------------------------------------------------------------------------
# TEAM commands
# ---------------------------------------------------------------------------
@bot.command(name="انشاء", description="إنشاء فريق باختيار نادٍ حقيقي")
@commands.cooldown(1, 10, commands.BucketType.user)
async def create_team(ctx):
    if db.get_coach(str(ctx.author.id)):
        embed = discord.Embed(
            title="❌ لديك فريق بالفعل!",
            description="استخدم `!فريقي` لعرض فريقك.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🏟️ إنشاء فريقك",
        description="اختر الدوري الحقيقي ثم النادي لتحصل على تشكيلته الحقيقية. الأندية الأضعف تحصل على ميزانية أكبر.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed, view=views.CreateTeamView(ctx.author.id))


@bot.command(name="فريقي", description="عرض فريقك")
@commands.cooldown(1, 5, commands.BucketType.user)
async def my_team(ctx):
    team, players = get_state(ctx.author)
    if not team:
        embed = discord.Embed(
            title="❌ لا تملك فريقاً!",
            description="أنشئ فريقاً بـ `!انشاء`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return
    await ctx.send(embed=views.team_embed(team, players), view=views.TeamPanel(ctx.author.id), ephemeral=True)


# ---------------------------------------------------------------------------
# MARKET commands
# ---------------------------------------------------------------------------
@bot.command(name="سوق", description="فتح سوق الانتقالات بالقوائم")
@commands.cooldown(1, 5, commands.BucketType.user)
async def market(ctx):
    view = views.MarketView(ctx.author.id)
    embed = discord.Embed(
        title="🛒 سوق الانتقالات",
        description="اختر الدوري ثم النادي لعرض اللاعبين المتاحين.",
        color=discord.Color.blue(),
    )
    embed.set_footer(text="استخدم الأزرار للتنقل — الصفحة تظهر لك فقط")
    await ctx.send(embed=embed, view=view, ephemeral=True)


@bot.command(name="اشتري", description="شراء لاعب من السوق")
@commands.cooldown(1, 5, commands.BucketType.user)
async def buy(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(
            title="❌ أنشئ فريقاً أولاً!",
            description="استخدم `!انشاء`",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    p = db.get_player(pid)
    if not p or p["team_id"] is not None:
        embed = discord.Embed(
            title="❌ اللاعب غير متاح!",
            description="هذا اللاعب ليس في السوق.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    if team["budget"] < p["price"]:
        embed = discord.Embed(
            title="❌ ميزانية غير كافية!",
            description=f"ميزانيتك: **{team['budget']}م** | سعر اللاعب: **{p['price']}م**",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.buy_player(pid, team["id"], p["price"], str(ctx.author.id))

    embed = discord.Embed(
        title="✅ تم الشراء!",
        description=f"اشتريت **{p['name']}** مقابل **{p['price']}م**",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 الميزانية المتبقية",
        value=f"{team['budget'] - p['price']}م",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command(name="بيع", description="بيع لاعب من فريقك")
@commands.cooldown(1, 5, commands.BucketType.user)
async def sell(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(
            title="❌ أنشئ فريقاً أولاً!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    p = db.get_player(pid)
    if not p or p["team_id"] != team["id"]:
        embed = discord.Embed(
            title="❌ هذا اللاعب ليس في فريقك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.sell_player(pid, p["price"], str(ctx.author.id))

    embed = discord.Embed(
        title="✅ تم البيع!",
        description=f"بعت **{p['name']}** مقابل **{p['price']}م**",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="💰 الميزانية الجديدة",
        value=f"{team['budget'] + p['price']}م",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command(name="لاعب", description="عرض تفاصيل لاعب")
@commands.cooldown(1, 3, commands.BucketType.user)
async def player_info(ctx, pid: int):
    p = db.get_player(pid)
    if not p:
        embed = discord.Embed(
            title="❌ اللاعب غير موجود!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    pos = POS_ARABIC.get(p["position"], p["position"])
    status = "في فريق ⚽" if p["team_id"] else "في السوق 🛒"

    e = views.player_card_embed(p)
    if p["club_id"]:
        club = db.get_club(p["club_id"])
        if club:
            e.add_field(name="النادي", value=club["name"], inline=True)
    await ctx.send(embed=e)


@bot.command(name="سجل", description="عرض سجل تاريخ اللاعب")
@commands.cooldown(1, 3, commands.BucketType.user)
async def player_history(ctx, pid: int):
    p = db.get_player(pid)
    if not p:
        embed = discord.Embed(title="❌ اللاعب غير موجود!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    history = db.get_history(pid)
    e = discord.Embed(title=f"📜 سجل {p['name']}", color=discord.Color.purple())
    if not history:
        e.description = "لا يوجد سجل لهذا اللاعب بعد."
    else:
        lines = []
        for h in history:
            amount = f" ({h['amount']}م)" if h["amount"] else ""
            lines.append(f"▫️ **{h['event']}**{amount}\n   🕐 {h['time']}")
        e.description = "\n".join(lines)
    e.set_footer(text="كل عملية على اللاعب تُسجل هنا تلقائياً")
    await ctx.send(embed=e)


# ---------------------------------------------------------------------------
# DEVELOPMENT commands
# ---------------------------------------------------------------------------
@bot.command(name="لاعب_تطوير", description="عرض مستويات تطوير لاعب")
@commands.cooldown(1, 3, commands.BucketType.user)
async def dev_view(ctx, pid: int):
    p = db.get_player(pid)
    if not p:
        embed = discord.Embed(title="❌ اللاعب غير موجود!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    team, _ = get_state(ctx.author)
    owned = team and p["team_id"] == team["id"]

    embed = discord.Embed(
        title=f"🔧 تطوير {p['name']} (ريت {p['rating']})",
        color=discord.Color.purple(),
    )

    lines = []
    for d in game_data.DEV_LEVELS:
        own = "" if owned else " ❌ ليس بفريقك"
        lines.append(
            f"**المستوى {d['level']}**: +{d['gain']} ريت | {d['xp']} خبرة | {d['money']}م{own}"
        )

    embed.description = "\n".join(lines)
    embed.set_footer(text="للتطوير: !طور <رقم> <المستوى>")
    await ctx.send(embed=embed)


@bot.command(name="طور", description="تطوير لاعب")
@commands.cooldown(1, 5, commands.BucketType.user)
async def develop(ctx, pid: int, level: int):
    team, _ = get_state(ctx.author)
    p = db.get_player(pid)

    if not team or not p or p["team_id"] != team["id"]:
        embed = discord.Embed(
            title="❌ اللاعب ليس في فريقك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    d = next((x for x in game_data.DEV_LEVELS if x["level"] == level), None)
    if not d:
        embed = discord.Embed(
            title="❌ مستوى غير صحيح!",
            description="اختر مستوى من 1 إلى 4.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    if team["xp"] < d["xp"] or team["budget"] < d["money"]:
        embed = discord.Embed(
            title="❌ موارد غير كافية!",
            description=f"تحتاج: {d['xp']} خبرة + {d['money']}م\nلديك: {team['xp']} خبرة + {team['budget']}م",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    new_rating = min(99, p["rating"] + d["gain"])
    new_price = p["price"] + d["gain"] * game_data.CONFIG["PRICE_PER_RATING"]
    db.develop_player(pid, new_rating, new_price)
    db.update_team(team["id"], xp=team["xp"] - d["xp"], budget=team["budget"] - d["money"])

    embed = discord.Embed(
        title="✅ تم التطوير!",
        description=f"**{p['name']}** تطور من ريت {p['rating']} إلى **{new_rating}** (+{d['gain']})",
        color=discord.Color.green(),
    )
    embed.add_field(name="السعر الجديد", value=f"{new_price}م", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="تدريب", description="تخصيص خبرة للتدريب قبل المباراة")
@commands.cooldown(1, 5, commands.BucketType.user)
async def train(ctx, amount: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    amount = max(0, min(amount, game_data.CONFIG["TRAIN_MAX_XP"]))
    if team["xp"] < amount:
        embed = discord.Embed(
            title="❌ خبرة غير كافية!",
            description=f"لديك: **{team['xp']}** نقطة | طلبت: **{amount}**",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.update_team(team["id"], training_invest=amount, xp=team["xp"] - amount)

    embed = discord.Embed(
        title="🏋️ تم التدريب!",
        description=f"خصصت **{amount}** نقطة خبرة للتدريب قبل المباراة القادمة.",
        color=discord.Color.green(),
    )
    embed.set_footer(text="⚠️ التدريب يظهر للخصم في !مباراتي")
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# TACTICS commands
# ---------------------------------------------------------------------------
@bot.command(name="تشكيل", description="ضبط التشكيل (مخفي حتى المباراة)")
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_formation(ctx, formation):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if formation not in game_data.FORMATIONS:
        embed = discord.Embed(
            title="❌ تشكيل غير صحيح!",
            description="التشكيلات المتاحة: " + " | ".join(game_data.FORMATIONS.keys()),
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.update_team(team["id"], formation=formation)

    embed = discord.Embed(
        title="📐 تم ضبط التشكيل!",
        description=f"التشكيل الجديد: **{formation}**\n🔒 مخفي حتى المباراة.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="خطة", description="ضبط الخطة التكتيكية (مخفي حتى المباراة)")
@commands.cooldown(1, 5, commands.BucketType.user)
async def set_tactic(ctx, tactic):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    if tactic not in game_data.TACTICS:
        embed = discord.Embed(
            title="❌ خطة غير صحيحة!",
            description="الخطط المتاحة: هجومي | متوازن | دفاعي",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.update_team(team["id"], tactic=tactic)

    mod = game_data.TACTICS[tactic]
    embed = discord.Embed(
        title="🎯 تم ضبط الخطة!",
        description=f"الخطة: **{tactic}**\n💡 {mod['key']}\n🔒 مخفي حتى المباراة.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="خطتي", description="عرض خطتك السرية")
@commands.cooldown(1, 3, commands.BucketType.user)
async def my_plan(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🔒 خطتك السرية",
        color=discord.Color.gold(),
    )
    embed.add_field(name="📐 التشكيل", value=team["formation"], inline=True)
    embed.add_field(name="🎯 الخطة", value=team["tactic"], inline=True)
    embed.add_field(
        name="🏋️ التدريب",
        value=f"{team['training_invest']} نقطة",
        inline=True,
    )
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# LEAGUE commands
# ---------------------------------------------------------------------------
def parse_real_league(arg):
    if arg is None:
        return None
    arg = str(arg).strip()
    if arg.isdigit():
        for l in market_data.LEAGUES:
            if l["id"] == int(arg):
                return l
    for l in market_data.LEAGUES:
        if arg in l["name"] or l["name"] in arg:
            return l
    return None


@bot.command(name="دوري_جديد", description="إنشاء دوري مرتبط بدوري حقيقي")
@commands.cooldown(1, 10, commands.BucketType.user)
async def new_league(ctx, *, arg=None):
    owner = str(ctx.author.id)
    team = db.get_team_by_owner(owner)
    if not team:
        tid = db.create_team(f"فريق {ctx.author.display_name}", owner)
        db.create_coach(owner, str(ctx.author), tid)
        team = db.get_team(tid)
    if arg:
        rl = parse_real_league(arg)
        if not rl:
            await ctx.send(embed=discord.Embed(title="❌ الدوري غير معروف!",
                                               description="الدوريات: " + " | ".join(l["name"] for l in market_data.LEAGUES),
                                               color=discord.Color.red()))
            return
        if team and team["real_league_id"] == rl["id"]:
            lid = db.create_league(f"دوري {rl['name']}", str(ctx.author.id), rl["id"])
            db.update_team(team["id"], league_id=lid)
            await ctx.send(embed=discord.Embed(title="🏆 تم إنشاء الدوري!",
                                               description=f"**دوري {rl['name']}** (رقم {lid})\nانضم زملاؤك بـ `!انضمام {lid}` واختاروا أنديتهم.",
                                               color=discord.Color.gold()))
            return
        view = views.OwnedView(ctx.author.id)
        view.add_item(views.ClubSelect(ctx.author.id, rl["id"], "leaguecreate"))
        e = discord.Embed(title=f"🏆 اختر ناديك في {rl['name']} لإنشاء الدوري",
                          description="ستنشئ الدوري وتنضم إليه بهذا النادي. زملاؤك سينضمون بأنديتهم.",
                          color=discord.Color.gold())
        await ctx.send(embed=e, view=view, ephemeral=True)
        return
    view = views.OwnedView(ctx.author.id)
    view.add_item(views.RealLeagueSelect(ctx.author.id, "leaguecreate"))
    e = discord.Embed(title="🏆 اختر الدوري الحقيقي للمسابقة", color=discord.Color.gold())
    e.description = "ستنشئ دوريًا تنافس فيه أنت وزملاؤك بأنديتكم الحقيقية."
    await ctx.send(embed=e, view=view, ephemeral=True)


@bot.command(name="انضمام", description="الانضمام إلى دوري واختيار نادٍ")
@commands.cooldown(1, 10, commands.BucketType.user)
async def join_l(ctx, lid: int):
    league = db.get_league(lid)
    if not league:
        await ctx.send(embed=discord.Embed(title="❌ الدوري غير موجود!", color=discord.Color.red()))
        return
    owner = str(ctx.author.id)
    team = db.get_team_by_owner(owner)
    if not team:
        tid = db.create_team(f"فريق {ctx.author.display_name}", owner)
        db.create_coach(owner, str(ctx.author), tid)
    rl = league["real_league_id"]
    view = views.OwnedView(ctx.author.id)
    view.add_item(views.ClubSelect(ctx.author.id, rl, "join", league_id=lid))
    e = discord.Embed(title=f"🏟️ اختر ناديك في دوري #{lid}", color=discord.Color.green())
    e.description = "اختر نادياً متاحاً (لم يأخذه أحد بعد):"
    await ctx.send(embed=e, view=view, ephemeral=True)


@bot.command(name="دوريات", description="عرض جميع الدوريات")
@commands.cooldown(1, 5, commands.BucketType.user)
async def list_leagues(ctx):
    leagues = db.get_leagues()
    if not leagues:
        embed = discord.Embed(
            title="🏆 لا توجد دوريات!",
            description="أنشئ دوري بـ `!دوري_جديد <اسم>`",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title="🏆 الدوريات", color=discord.Color.gold())
    for l in leagues:
        m = len(json.loads(l["members"]))
        rl = db.get_real_league(l["real_league_id"])
        rl_name = f" ({rl['name']})" if rl else ""
        embed.add_field(
            name=f"#{l['id']} - {l['name']}{rl_name}",
            value=f"الأعضاء: {m}",
            inline=True,
        )
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# MATCH commands
# ---------------------------------------------------------------------------
@bot.command(name="تحدي", description="تحدي لاعب آخر لمباراة")
@commands.cooldown(1, 30, commands.BucketType.user)
async def challenge_cmd(ctx, opponent: discord.Member):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    opp_team = db.get_team_by_owner(str(opponent.id))
    if not opp_team:
        embed = discord.Embed(
            title="❌ الخصم لا يملك فريقاً!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    if opponent.id == ctx.author.id:
        embed = discord.Embed(
            title="❌ لا يمكنك تحدي نفسك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    pid = db.challenge(str(ctx.author.id), str(opponent.id))

    embed = discord.Embed(
        title="⚔️ تم التحدي!",
        description=f"تحديت **{opponent.display_name}**!\nمباراة رقم: **{pid}**",
        color=discord.Color.red(),
    )
    embed.add_field(
        name="الخطوات",
        value=(
            f"1. كلاهما يضبط خطته بـ `!خطة` و `!تشكيل`\n"
            f"2. كلاهما يكتب `!جاهز {pid}`\n"
            f"3. المباراة تبدأ تلقائياً!"
        ),
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="مباراتي", description="عرض مبارياتك المعلقة")
@commands.cooldown(1, 5, commands.BucketType.user)
async def my_matches(ctx):
    pendings = db.get_pending_for(str(ctx.author.id))
    if not pendings:
        embed = discord.Embed(
            title="⚔️ لا توجد مباريات معلقة!",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(title="⚔️ مبارياتك المعلقة", color=discord.Color.red())
    for pm in pendings:
        opp_id = pm["opponent_id"] if pm["challenger_id"] == str(ctx.author.id) else pm["challenger_id"]
        opp = db.get_team_by_owner(opp_id)
        opp_name = opp["name"] if opp else "؟"
        opp_train = opp["training_invest"] if opp else 0

        my_ready = (
            (pm["challenger_id"] == str(ctx.author.id) and pm["challenger_ready"])
            or (pm["opponent_id"] == str(ctx.author.id) and pm["opponent_ready"])
        )
        status = "✅ جاهز" if my_ready else "❌ غير جاهز"

        embed.add_field(
            name=f"#{pm['id']} ضد {opp_name}",
            value=f"تدريب الخصم: {opp_train} نقطة\nحالة جاهزيتك: {status}",
            inline=False,
        )
    embed.set_footer(text="اكتب !جاهز <رقم> للتأكيد")
    await ctx.send(embed=embed)


@bot.command(name="جاهز", description="تأكيد الجاهزية للمباراة")
@commands.cooldown(1, 5, commands.BucketType.user)
async def ready(ctx, pid: int):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    pm = db.get_pending(pid)
    if not pm or (pm["challenger_id"] != str(ctx.author.id) and pm["opponent_id"] != str(ctx.author.id)):
        embed = discord.Embed(
            title="❌ هذه المباراة غير مخصصة لك!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    db.set_ready(pid, str(ctx.author.id))
    pm = db.get_pending(pid)

    if pm["challenger_ready"] and pm["opponent_ready"]:
        await run_match(ctx, pm)
    else:
        embed = discord.Embed(
            title="✅ تم التأكيد!",
            description=f"أنت جاهز للمباراة **#{pid}**.\nبانتظار الخصم...",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)


async def run_match(ctx, pm):
    c_team = db.get_team_by_owner(pm["challenger_id"])
    o_team = db.get_team_by_owner(pm["opponent_id"])

    challenger = {
        "players": db.team_players(c_team["id"]),
        "formation": c_team["formation"],
        "tactic": c_team["tactic"],
        "training": c_team["training_invest"],
        "tactics": c_team,
    }
    opponent = {
        "players": db.team_players(o_team["id"]),
        "formation": o_team["formation"],
        "tactic": o_team["tactic"],
        "training": o_team["training_invest"],
        "tactics": o_team,
    }

    ga, gb, result, notes = engine.simulate(challenger, opponent)

    db.reduce_condition(c_team["id"], game_data.CONFIG["MATCH_CONDITION_COST"])
    db.reduce_condition(o_team["id"], game_data.CONFIG["MATCH_CONDITION_COST"])
    db.update_team(c_team["id"], training_invest=0)
    db.update_team(o_team["id"], training_invest=0)

    if result == "فوز":
        winner = c_team["name"]; loser = o_team["name"]
    elif result == "خسارة":
        winner = o_team["name"]; loser = c_team["name"]
    else:
        winner = None; loser = None

    lc_up, lc_lvl = db.record_result(c_team["id"], result)
    lo_up, lo_lvl = db.record_result(o_team["id"], "خسارة" if result == "فوز" else ("فوز" if result == "خسارة" else "تعادل"))

    embed = discord.Embed(
        title=f"⚽ نتيجة المباراة #{pm['id']}",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name="النتيجة",
        value=f"**{c_team['name']}** {ga} - {gb} **{o_team['name']}**",
        inline=False,
    )

    if winner:
        embed.add_field(name="🏆 الفائز", value=f"**{winner}**", inline=False)
    else:
        embed.add_field(name="🤝 النتيجة", value="**تعادل!**", inline=False)

    plans = (
        f"• **{c_team['name']}**: {c_team['formation']} / {c_team['tactic']} / "
        f"تمرير {c_team['passing']} / ضغط {c_team['pressing']} / رقابة {c_team['marking']} / إيقاع {c_team['tempo']}\n"
        f"• **{o_team['name']}**: {o_team['formation']} / {o_team['tactic']} / "
        f"تمرير {o_team['passing']} / ضغط {o_team['pressing']} / رقابة {o_team['marking']} / إيقاع {o_team['tempo']}"
    )
    embed.add_field(name="📋 الخطط المكشوفة", value=plans, inline=False)

    extra = []
    if lc_up:
        extra.append(f"⬆️ **{c_team['name']}** وصل للمستوى {lc_lvl}!")
    if lo_up:
        extra.append(f"⬆️ **{o_team['name']}** وصل للمستوى {lo_lvl}!")
    if extra:
        embed.add_field(name="✨ ترقية", value="\n".join(extra), inline=False)

    if notes:
        embed.add_field(name="📝 ملاحظات", value="\n".join(notes), inline=False)

    db.delete_pending(pm["id"])
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# NEW SYSTEMS (borrowed from Top Eleven / Manager Evolution)
# ---------------------------------------------------------------------------
@bot.command(name="تكتيك", description="ضبط التكتيك الكامل (تمرير/ضغط/رقابة/إيقاع/مرتد/تسلل)")
@commands.cooldown(1, 5, commands.BucketType.user)
async def full_tactics_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await ctx.send(embed=views.tactics_embed(team), view=views.FullTacticsView(ctx.author.id))


@bot.command(name="راحة", description="استعادة جاهزية اللاعبين عبر المركز الطبي")
@commands.cooldown(1, 30, commands.BucketType.user)
async def rest_cmd(ctx):
    team, players = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    before = round(sum(p["condition"] for p in players) / len(players)) if players else 0
    recover = db.rest_team(team["id"])
    after = db.team_players(team["id"])
    after_avg = round(sum(p["condition"] for p in after) / len(after)) if after else 0
    embed = discord.Embed(
        title="💤 راحة الفريق",
        description=f"🔋 الجاهزية: {before}% ← **{after_avg}%** (مركز طبي +{recover})",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="منشأة", description="عرض وترقية منشآت النادي")
@commands.cooldown(1, 5, commands.BucketType.user)
async def facilities_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    await ctx.send(embed=views.facilities_embed(team), view=views.FacilitiesView(ctx.author.id))


@bot.command(name="كشاف", description="استقدام لاعب حر مباشرة لفريقك (10 رموز)")
@commands.cooldown(1, 30, commands.BucketType.user)
async def scout_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    if not db.spend_tokens(team["id"], 10):
        embed = discord.Embed(
            title="❌ رموز غير كافية!",
            description=f"رموزك: **{team['tokens']}** | مطلوب: 10 رمز",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return
    p = db.scout_player(team["id"])
    db.update_player(p["id"], team_id=team["id"])
    db.add_history(p["id"], "كشافة", 0, str(ctx.author.id), str(team["id"]))
    e = views.player_card_embed(p)
    e.title = "🌟 لاعب جديد من الكشافة!"
    e.description = f"انضم **{p['name']}** مباشرة إلى فريقك!"
    await ctx.send(embed=e)


@bot.command(name="موسم", description="بدء موسم دوري لفريقك")
@commands.cooldown(1, 15, commands.BucketType.user)
async def season_start_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    if not team["league_id"]:
        embed = discord.Embed(
            title="❌ فريقك ليس في دوري!",
            description="انضم لدوري عبر `!دوريات` أولاً.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return
    rounds = db.create_season(team["league_id"])
    if not rounds:
        embed = discord.Embed(
            title="❌ لا يمكن بدء الموسم!",
            description="الدوري يحتاج عضوين على الأقل.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(
        title="🏆 انطلق الموسم!",
        description=f"تم جدولة **{rounds}** جولات. قدّم الجولات بـ `!تقدم` وشاهد الترتيب بـ `!ترتيب`.",
        color=discord.Color.gold(),
    )
    await ctx.send(embed=embed)


@bot.command(name="ترتيب", description="عرض ترتيب دوريك")
@commands.cooldown(1, 5, commands.BucketType.user)
async def standings_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team or not team["league_id"]:
        embed = discord.Embed(title="❌ أنت لست في دوري!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    season = db.get_season(team["league_id"])
    if not season or season["status"] != "active":
        embed = discord.Embed(title="❌ لا يوجد موسم نشط!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    standings = json.loads(season["standings"])
    teams = {t["id"]: t for t in db.get_league_teams(team["league_id"])}
    rows = []
    for tid, s in sorted(standings.items(), key=lambda kv: (kv[1]["Pts"], kv[1]["GF"] - kv[1]["GA"]), reverse=True):
        name = teams.get(int(tid), {}).get("name", f"فريق {tid}")
        rows.append(f"`{len(rows)+1}.` **{name}** — {s['Pts']}ن | {s['W']}ف/{s['D']}ت/{s['L']}خ | {s['GF']}-{s['GA']}")
    e = discord.Embed(title=f"🏆 ترتيب الدوري (جولة {season['round']}/{season['total_rounds']})", color=discord.Color.gold())
    e.description = "\n".join(rows) if rows else "لا يوجد"
    await ctx.send(embed=e)


@bot.command(name="تقدم", description="تقديم جولة في موسم الدوري")
@commands.cooldown(1, 20, commands.BucketType.user)
async def advance_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team or not team["league_id"]:
        embed = discord.Embed(title="❌ أنت لست في دوري!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    res = db.advance_season(team["league_id"])
    if res is None:
        embed = discord.Embed(title="❌ لا يوجد موسم نشط!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    if res == "انتهى":
        await ctx.send("🏁 انتهى الموسم! البطل توج باللقب 🏆")
        return
    teams = {t["id"]: t for t in db.get_league_teams(team["league_id"])}
    lines = []
    for a, b, ga, gb in res:
        na = teams.get(a, {}).get("name", f"فريق {a}")
        nb = teams.get(b, {}).get("name", f"فريق {b}")
        lines.append(f"⚽ {na} **{ga}** - **{gb}** {nb}")
    e = discord.Embed(title="⚽ نتائج الجولة", color=discord.Color.green())
    e.description = "\n".join(lines)
    await ctx.send(embed=e)


@bot.command(name="مستواي", description="عرض ملف المدرب (مستوى/سمعة/رموز/ألقاب)")
@commands.cooldown(1, 5, commands.BucketType.user)
async def profile_cmd(ctx):
    team, _ = get_state(ctx.author)
    if not team:
        embed = discord.Embed(title="❌ أنشئ فريقاً أولاً!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    e = discord.Embed(title=f"👤 ملف {team['name']}", color=discord.Color.blue())
    e.add_field(name="⭐ المستوى", value=f"{team['level']}", inline=True)
    e.add_field(name="🪙 الرموز", value=f"{team['tokens']}", inline=True)
    e.add_field(name="📊 السمعة", value=f"{team['reputation']}", inline=True)
    e.add_field(name="🏆 الألقاب", value=f"{team['titles']}", inline=True)
    e.add_field(name="📈 السجل", value=f"{team['wins']}ف / {team['draws']}ت / {team['losses']}خ", inline=True)
    e.add_field(name="💰 الميزانية", value=f"{team['budget']}م", inline=True)
    await ctx.send(embed=e)


# ---------------------------------------------------------------------------
# TIPS & HELP
# ---------------------------------------------------------------------------
@bot.command(name="نصائح", description="نصائح للعب بشكل أفضل")
@commands.cooldown(1, 10, commands.BucketType.user)
async def tips(ctx):
    embed = discord.Embed(
        title="💡 نصائح أوهارا",
        color=discord.Color.blue(),
    )
    tips_list = [
        "🎯 طابق خطتك لهوية فريقك: فريق هجومي → خطة هجومية، وإلا تُعاقب.",
        "👀 راجع تدريب الخصم في `!مباراتي` قبل `!جاهز`.",
        "⚔️ الهجوم يكسر الدفاعي، الدفاع يكسر المتوازن، المتوازن يكسر الهجومي.",
        "🌟 فريق متوسط بخطط صحيحة وتدريب مكثف قد يفوز على فريق نجوم!",
        "🔧 طور لاعبيك بـ `!طور` لرفع الريت والسعر.",
    ]
    embed.description = "\n".join(tips_list)
    await ctx.send(embed=embed)


@bot.command(name="مساعدة", description="عرض جميع الأوامر")
@commands.cooldown(1, 5, commands.BucketType.user)
async def help_cmd(ctx):
    embed = discord.Embed(
        title="📘 أوامر أوهارا المدرب الأفضل",
        description=(
            "نظام كرة قدم افتراضي كامل — أنشئ فريقك، تعاقد مع نجوم، وتقدم في الدوريات!\n\n"
            "✨ **الطريقة الأسهل:** اكتب `!انشاء` ثم `!فريقي` "
            "وستظهر لك **قائمة أزرار** لكل شيء (شراء، تطوير، تشكيل، خطة، بيع، طرد، استقالة...) "
            "بدون الحاجة لكتابة الأوامر!"
        ),
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="⚽ إنشاء الفريق",
        value=(
            "`!انشاء` — 🎮 إنشاء فريق أساسي (11 لاعباً، بدون نادٍ)\n"
            "`!فريقي` — 🎮 لوحة التحكم بالأزرار (خاصة بك وحدك، لا يراها غيرك)"
        ),
        inline=False,
    )

    embed.add_field(
        name="🛒 سوق الانتقالات",
        value=(
            "`!سوق` — 🎮 سوق بالقوائم: اختر الدوري ← النادي ← اللاعب\n"
            "`!لاعب <رقم>` — تفاصيل لاعب\n"
            "`!سجل <رقم>` — سجل تاريخ اللاعب\n"
            "`!بيع <رقم>` — بيع لاعب"
        ),
        inline=False,
    )

    embed.add_field(
        name="🔧 تطوير اللاعبين",
        value=(
            "`!لاعب_تطوير <رقم>` — مستويات التطوير\n"
            "`!طور <رقم> <مستوى>` — تطوير لاعب (1-4)\n"
            "`!تدريب <نقاط>` — تدريب قبل المباراة"
        ),
        inline=False,
    )

    embed.add_field(
        name="🎯 التكتيكات",
        value=(
            "`!تشكيل <4-3-3>` — ضبط التشكيل\n"
            "`!خطة <هجومي/متوازن/دفاعي>` — ضبط الخطة العامة\n"
            "`!تكتيك` — 🎮 التكتيك الكامل (تمرير/ضغط/رقابة/إيقاع/مرتد/تسلل)\n"
            "`!خطتي` — عرض خطتك السرية"
        ),
        inline=False,
    )

    embed.add_field(
        name="🏗️ المنشآت والكشافة",
        value=(
            "`!منشأة` — 🎮 الملعب/التدريب/الطبي/الشباب\n"
            "`!كشاف` — استقدام لاعب حر (10 رموز)\n"
            "`!راحة` — استعادة جاهزية اللاعبين"
        ),
        inline=False,
    )

    embed.add_field(
        name="🏆 الدوريات والمواسم",
        value=(
            "`!دوري_جديد <دوري>` — إنشاء دوري حقيقي (مثال: انجليزي/ايطالي/الماني)\n"
            "`!انضمام <رقم>` — الانضمام لدوري واختيار نادٍ\n"
            "`!دوريات` — قائمة الدوريات\n"
            "`!موسم` — بدء موسم لدوريك\n"
            "`!تقدم` — تقديم جولة\n"
            "`!ترتيب` — ترتيب الدوري"
        ),
        inline=False,
    )

    embed.add_field(
        name="👤 المدرب",
        value=(
            "`!مستواي` — ملف المدرب (مستوى/سمعة/رموز/ألقاب)\n"
            "`!لاعب <رقم>` — بطاقة اللاعب (الخصائص الست)"
        ),
        inline=False,
    )

    embed.add_field(
        name="⚔️ المباريات",
        value=(
            "`!تحدي @خصم` — تحدي لاعب\n"
            "`!مباراتي` — مبارياتك المعلقة\n"
            "`!جاهز <رقم>` — تأكيد الجاهزية"
        ),
        inline=False,
    )

    embed.add_field(
        name="💡 أخرى",
        value=(
            "`!نصائح` — نصائح للعب\n"
            "`!مساعدة` — عرض هذه القائمة"
        ),
        inline=False,
    )

    embed.set_footer(text="أوهارا فانتزب — مدربك الرقمي الأفضل ⚽")
    await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
threading.Thread(target=_start_web_server, daemon=True).start()
bot.run(TOKEN)
